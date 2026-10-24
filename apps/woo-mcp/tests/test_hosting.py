"""Real Uvicorn child process; synthetic files outside repo, zero Woo requests."""

import asyncio
import multiprocessing
import os
import socket
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import httpx
import uvicorn

from woo_mcp.config import Config
from woo_mcp.server import create_app
from hosting_checks import discover


def serve(sock, stop, environment, log_path):
    """Child-process runner with a portable, graceful stop signal (no app wrapper)."""
    os.environ.update(environment)
    with open(log_path, "w", encoding="utf-8") as log, redirect_stdout(log), redirect_stderr(log):
        server = uvicorn.Server(uvicorn.Config("woo_mcp.server:create_app", factory=True,
            lifespan="on", access_log=False, proxy_headers=False, timeout_graceful_shutdown=5))
        async def run():
            async def shutdown():
                while not stop.is_set():
                    await asyncio.sleep(0.05)
                server.should_exit = True
            task = asyncio.create_task(shutdown())
            try:
                await server.serve(sockets=[sock])
            finally:
                task.cancel()
        asyncio.run(run())


class HostingConfigTests(unittest.TestCase):
    def test_environment_uses_existing_config_fields(self):
        env = {"WOO_CONNECTION_ORIGIN": "http://internal.test", "WOO_CANONICAL_ORIGIN": "http://store.test:8080",
               "WOO_SECRET_DIRECTORY": "/run/secrets/test", "WOO_DEADLINE_SECONDS": "4",
               "WOO_CURRENCY": "INR", "WOO_STORE_TIMEZONE": "Asia/Kolkata",
               "WOO_MCP_ALLOWED_HOSTS": "urumi-woo-mcp,urumi-woo-mcp:8000"}
        with patch.dict(os.environ, env, clear=True):
            config = Config.from_environment()
        self.assertEqual(config.connection_origin, "http://internal.test")
        self.assertEqual(config.host, "store.test:8080")
        self.assertEqual(config.secret_directory, Path("/run/secrets/test"))
        self.assertEqual(config.deadline_seconds, 4)
        self.assertEqual(config.allowed_hosts, ("urumi-woo-mcp", "urumi-woo-mcp:8000"))

    def test_bad_environment_fails_without_values(self):
        for name, value in (("WOO_DEADLINE_SECONDS", "PRIVATE"), ("WOO_DEADLINE_SECONDS", "nan"),
                            ("WOO_CURRENCY", "PRIVATE"), ("WOO_SECRET_DIRECTORY", ""),
                            ("WOO_CANONICAL_ORIGIN", "http://host:PRIVATE"),
                            ("WOO_STORE_TIMEZONE", "PRIVATE"), ("WOO_MCP_ALLOWED_HOSTS", "*"),
                            ("WOO_MCP_ALLOWED_HOSTS", "a,a"), ("WOO_MCP_ALLOWED_HOSTS", "a:65536"),
                            ("WOO_MCP_ALLOWED_HOSTS", "http://a"), ("WOO_MCP_ALLOWED_HOSTS", "")):
            with patch.dict(os.environ, {name: value}, clear=True), self.assertRaisesRegex(
                    ValueError, "^Invalid Woo MCP runtime configuration.$"):
                Config.from_environment()

    def test_import_factory_does_not_load_credentials(self):
        with patch.dict(os.environ, {}, clear=True), patch(
                "woo_mcp.server.Credentials.from_directory", side_effect=AssertionError("read before lifespan")):
            app = create_app()
            self.assertIsNotNone(app.router.lifespan_context)

    def test_host_origin_checks_use_sdk(self):
        from mcp.server.transport_security import TransportSecurityMiddleware, TransportSecuritySettings
        hosts = tuple(h + port for h in ("urumi-woo-mcp", "urumi-woo-mcp.urumi",
            "urumi-woo-mcp.urumi.svc", "urumi-woo-mcp.urumi.svc.cluster.local") for port in ("", ":8000"))
        with patch.dict(os.environ, {"WOO_MCP_ALLOWED_HOSTS": ",".join(hosts)}, clear=True), patch(
                "woo_mcp.server.create_server") as factory:
            create_app()
            security = factory.return_value.streamable_http_app.call_args.kwargs["transport_security"]
        self.assertIsInstance(security, TransportSecuritySettings)
        self.assertTrue(security.enable_dns_rebinding_protection)
        self.assertEqual(security.allowed_origins, [])
        middleware = TransportSecurityMiddleware(security)
        with patch("mcp.server.transport_security.logger"):
            for host in hosts:
                self.assertTrue(middleware._validate_host(host))
            for host in ("evil.invalid", "urumi-woo-mcp:9999", "urumi-woo-mcp.evil.invalid", None):
                self.assertFalse(middleware._validate_host(host))
            self.assertTrue(middleware._validate_origin(None))
            self.assertFalse(middleware._validate_origin("http://localhost:8000"))

    def test_missing_files_fail_startup(self):
        with tempfile.TemporaryDirectory(prefix="urumi-missing-") as directory:
            with patch.dict(os.environ, {"WOO_SECRET_DIRECTORY": directory}, clear=True):
                app = create_app()
                async def start():
                    async with app.router.lifespan_context(app):
                        self.fail("Started without credentials")
                with self.assertRaisesRegex(ValueError, "Required credential files"):
                    asyncio.run(start())

    def test_real_tcp_discovery_and_graceful_shutdown(self):
        requests = []
        class Trap(BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append(self.command)
                self.send_response(503)
                self.end_headers()
            do_POST = do_PUT = do_GET
            def log_message(self, *args):
                pass
        trap = ThreadingHTTPServer(("127.0.0.1", 0), Trap)
        thread = threading.Thread(target=trap.serve_forever, daemon=True)
        thread.start()
        ctx = multiprocessing.get_context("spawn")
        stop = ctx.Event()
        process = None
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        try:
            with tempfile.TemporaryDirectory(prefix="urumi-tcp-") as directory:
                for name, dummy in (("consumer-key", "TEST-ONLY-KEY"), ("consumer-secret", "TEST-ONLY-SECRET")):
                    (Path(directory) / name).write_text(dummy, encoding="utf-8")
                log_path = str(Path(directory) / "server.log")
                environment = {"WOO_SECRET_DIRECTORY": directory,
                    "WOO_CONNECTION_ORIGIN": f"http://127.0.0.1:{trap.server_port}",
                    "WOO_CANONICAL_ORIGIN": "http://discovery.invalid",
                    "WOO_MCP_ALLOWED_HOSTS": f"127.0.0.1:{port}", "PYTHONDONTWRITEBYTECODE": "1"}
                process = ctx.Process(target=serve, args=(sock, stop, environment, log_path))
                process.start()
                sock.close()
                deadline = time.monotonic() + 20
                while True:
                    try:
                        with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                            break
                    except OSError:
                        if not process.is_alive() or time.monotonic() >= deadline:
                            self.fail("Uvicorn did not start")
                        time.sleep(0.05)
                self.assertEqual(len(asyncio.run(discover(f"http://127.0.0.1:{port}/mcp"))), 5)
                with httpx.Client(trust_env=False, timeout=3) as http:
                    self.assertEqual(http.get(f"http://127.0.0.1:{port}/mcp", headers={"Host": "evil.invalid"}).status_code, 421)
                    response = http.get(f"http://127.0.0.1:{port}/mcp", headers={"Origin": "http://browser.invalid"})
                    self.assertEqual(response.status_code, 403)
                    self.assertNotIn("access-control-allow-origin", response.headers)
                stop.set()
                process.join(10)
                self.assertFalse(process.is_alive())
                self.assertEqual(process.exitcode, 0)
                logs = Path(log_path).read_text(encoding="utf-8")
                self.assertIn("Application shutdown complete", logs)
                for forbidden in ("TEST-ONLY-KEY", "TEST-ONLY-SECRET", "Authorization", "oauth_signature"):
                    self.assertNotIn(forbidden, logs)
                self.assertEqual(requests, [])
        finally:
            stop.set()
            if process is not None:
                process.join(2)
                if process.is_alive():
                    process.terminate()
                    process.join(5)
                process.close()
            sock.close()
            trap.shutdown()
            trap.server_close()
            thread.join(2)

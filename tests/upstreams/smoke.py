"""Explicit real-TCP / Docker acceptance for either stateless Stage 6 upstream.

Run with either app's locked Python environment. No Kubernetes or store access.
"""
import argparse
import asyncio
from contextlib import redirect_stdout, redirect_stderr
import json
import multiprocessing
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import uuid
import httpx2
import uvicorn
from mcp.client import Client
from mcp.client.streamable_http import streamable_http_client

ROOT = Path(__file__).resolve().parents[2]
PROFILES = {
    "arithmetic-mcp": ("arithmetic_mcp", "sum_amounts", {"amounts": ["1.25", "2.75"], "currency": "INR"}, "total", "4"),
    "store-policy-mcp": ("store_policy_mcp", "get_policy", {"key": "cod"}, "title", "Cash on Delivery"),
}


async def accept(url, app, host=None):
    _, name, arguments, key, expected = PROFILES[app]
    async with asyncio.timeout(20):
        async with httpx2.AsyncClient(trust_env=False, timeout=5, headers={"Host": host} if host else {}) as http:
            async with Client(streamable_http_client(url, http_client=http), cache=None) as client:
                tools = (await client.list_tools()).tools
                assert [t.name for t in tools] == [name]
                assert tools[0].input_schema["additionalProperties"] is False
                assert tools[0].output_schema["type"] == "object"
                assert tools[0].annotations.read_only_hint
                result = await client.session.call_tool(name, arguments)
                assert not result.is_error and result.structured_content[key] == expected
            assert (await http.get(url, headers={"Host": "evil.invalid"})).status_code == 421
            response = await http.get(url, headers={"Origin": "http://browser.invalid"})
            assert response.status_code == 403 and "access-control-allow-origin" not in response.headers
    return {"tool": name, "structured_call": "PASS", "host_rejected": True, "origin_rejected": True}


def serve(app, sock, stop, logpath):
    sys.path.insert(0, str(ROOT / "apps" / app / "src"))
    os.environ["MCP_ALLOWED_HOSTS"] = "127.0.0.1:" + str(sock.getsockname()[1])
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    with open(logpath, "w", encoding="utf-8") as log, redirect_stdout(log), redirect_stderr(log):
        server = uvicorn.Server(uvicorn.Config(PROFILES[app][0] + ".server:create_app", factory=True,
            lifespan="on", access_log=False, proxy_headers=False, timeout_graceful_shutdown=5))
        async def run():
            async def shutdown():
                while not stop.is_set():
                    await asyncio.sleep(.05)
                server.should_exit = True
            task = asyncio.create_task(shutdown())
            try:
                await server.serve(sockets=[sock])
            finally:
                task.cancel()
        asyncio.run(run())


def tcp(app):
    ctx = multiprocessing.get_context("spawn")
    stop = ctx.Event()
    with socket.socket() as sock, tempfile.TemporaryDirectory(prefix="urumi-stateless-tcp-") as tmp:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        logpath = str(Path(tmp) / "server.log")
        process = ctx.Process(target=serve, args=(app, sock, stop, logpath))
        process.start()
        try:
            deadline = time.monotonic() + 25
            while True:
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=.2):
                        break
                except OSError:
                    if not process.is_alive() or time.monotonic() > deadline:
                        raise RuntimeError("TCP startup failed")
                    time.sleep(.05)
            result = asyncio.run(accept(f"http://127.0.0.1:{port}/mcp", app))
            stop.set()
            process.join(10)
            assert not process.is_alive() and process.exitcode == 0
            assert "Application shutdown complete" in Path(logpath).read_text()
        finally:
            stop.set()
            process.join(2)
            if process.is_alive():
                process.terminate()
                process.join(5)
            process.close()
    return dict(result, mode="listening TCP", clean_shutdown=True)


def docker(*args):
    result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=45)
    if result.returncode:
        raise RuntimeError("Docker smoke failed: " + args[0])
    return result.stdout


def container(app, image):
    name = "urumi-stage61-smoke-" + uuid.uuid4().hex[:8]
    started = False
    try:
        docker("run", "-d", "--name", name, "--read-only", "--cap-drop=ALL",
            "--security-opt=no-new-privileges:true", "--memory=128m", "--cpus=0.25",
            "--pids-limit=64", "--publish", "127.0.0.1::8000", image)
        started = True
        port = docker("port", name, "8000/tcp").strip().rsplit(":", 1)[1]
        # Use the explicit internal Host accepted by the server. Network remains loopback.
        # Recreate no container: runtime Host is localhost:8000, unlike mapped test port.
        deadline = time.monotonic() + 45
        while True:
            log = subprocess.run(["docker", "logs", name], capture_output=True, text=True, timeout=5)
            if "Application startup complete" in log.stdout + log.stderr:
                break
            if time.monotonic() > deadline:
                raise RuntimeError("Container startup timeout")
            time.sleep(.1)
        result = asyncio.run(accept(f"http://127.0.0.1:{port}/mcp", app, host="localhost:8000"))
        details = json.loads(docker("inspect", name))[0]
        host = details["HostConfig"]
        assert details["Config"]["User"] == "10001:10001" and not details["Mounts"]
        assert host["ReadonlyRootfs"] and host["CapDrop"] == ["ALL"]
        assert "no-new-privileges:true" in host["SecurityOpt"]
        check = """import os, errno, json
from pathlib import Path
assert os.getuid() == os.getgid() == 10001
assert not Path('/app/tests').exists() and not Path('/app/.git').exists()
assert not list(Path('/app').rglob('__pycache__'))
try:
    Path('/tmp/write-check').write_text('non-sensitive')
except OSError as e:
    assert e.errno == errno.EROFS
else:
    raise AssertionError('Writable root filesystem')
status = dict(line.split(':',1) for line in Path('/proc/1/status').read_text().splitlines() if ':' in line)
assert status['NoNewPrivs'].strip() == '1'
assert int(status['CapEff'].strip(),16) == 0
assert status['Seccomp'].strip() == '2'
print('PASS uid/gid=10001:10001; read-only; CapEff=0; NoNewPrivs=1; seccomp=2')
"""
        security = docker("exec", name, "python", "-c", check).strip()
        assert "No broken requirements" in docker("exec", name, "python", "-m", "pip", "check")
        docker("stop", "--time", "20", name)
        state = json.loads(docker("inspect", name))[0]["State"]
        assert state["ExitCode"] == 0 and not state["OOMKilled"]
        logs = subprocess.run(["docker", "logs", name], capture_output=True, text=True, timeout=5)
        assert "Application shutdown complete" in logs.stdout + logs.stderr
        assert "Authorization" not in logs.stdout + logs.stderr
        info = json.loads(docker("image", "inspect", image))[0]
        assert info["Architecture"] == "amd64" and info["Os"] == "linux"
        return dict(result, mode="Docker TCP", image=image, image_id=info["Id"], image_bytes=info["Size"],
            security=security, clean_shutdown=True, oom_killed=False)
    finally:
        if started:
            docker("stop", "--time", "20", name)
            docker("rm", name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("app", choices=PROFILES)
    parser.add_argument("--image")
    args = parser.parse_args()
    evidence = container(args.app, args.image) if args.image else tcp(args.app)
    print(json.dumps(dict(evidence, temporary_resources_removed=True)))

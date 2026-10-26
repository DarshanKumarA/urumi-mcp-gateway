"""Offline Docker integration with synthetic files. No Kubernetes/live business calls."""
import asyncio
import json
from pathlib import Path
import re
import subprocess
import tempfile
import time
from uuid import uuid4

import httpx2
from mcp.client import Client
from mcp.client.streamable_http import streamable_http_client

PG = "postgres:18.6-bookworm@sha256:6b38fe68f2c02cafffbbce7496f76d110d8a947c039bd22c067e9a43c2250240"
GATEWAY = "urumi-gateway:stage8.0"
TOKEN = "SYNTHETIC-SERVICE-TOKEN-" + "x" * 40
PASSWORD = "Synthetic-fixture-only-Password-80!"


def run(*args, check=True):
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", timeout=180)
    if check and r.returncode:
        raise RuntimeError("Fixture operation failed: " + args[0])
    return r.stdout.strip()


def security(name, uid):
    spec = json.loads(run("docker", "inspect", name))[0]
    assert spec["HostConfig"]["ReadonlyRootfs"]
    assert spec["HostConfig"]["CapDrop"] == ["ALL"]
    s = run("docker", "exec", name, "cat", "/proc/1/status")
    assert re.search(r"Uid:\s+" + str(uid) + r"\s+" + str(uid), s)
    assert re.search(r"Gid:\s+" + str(uid) + r"\s+" + str(uid), s)
    for pattern in (r"CapEff:\s+0000000000000000", r"NoNewPrivs:\s+1", r"Seccomp:\s+2"):
        assert re.search(pattern, s)


async def acceptance(base):
    async with httpx2.AsyncClient(base_url=base, trust_env=False, timeout=10) as http:
        for _ in range(60):
            try:
                if (await http.get("/health/ready")).status_code == 200:
                    break
            except httpx2.TransportError:
                pass
            await asyncio.sleep(.5)
        else:
            raise RuntimeError("Gateway not ready")
        assert (await http.get("/api/me")).status_code == 401
        assert (await http.post("/mcp", json={})).status_code == 401
        r = await http.post("/api/auth/login", headers={"Origin": base},
                           json={"username": "fixture_admin", "password": PASSWORD})
        assert r.status_code == 200
        r = await http.post("/api/keys", headers={"Origin": base}, json={"label": "offline fixture"})
        assert r.status_code == 201
        body = r.json()
        # Match the established one-time API DTO; never print it.
        key = body["raw_key"]
    for mode in ("2026-07-28", "legacy"):
        async with httpx2.AsyncClient(trust_env=False, headers={"Authorization": "Bearer " + key}) as http:
            async with Client(streamable_http_client(base + "/mcp", http_client=http), mode=mode, cache=None) as client:
                tools = (await client.list_tools()).tools
                assert len(tools) == 7
                assert {t.name for t in tools} >= {"woocommerce__list_products", "arithmetic__sum_amounts", "store_policy__get_policy"}
                assert TOKEN not in str(tools) and key not in str(tools)
    print("PASS gateway authenticated current/legacy discovery: seven tools, three seeded peers; zero tool calls")


async def dashboard_acceptance(base):
    async with httpx2.AsyncClient(trust_env=False, timeout=5) as http:
        for _ in range(30):
            try:
                if (await http.get(base)).status_code == 200:
                    break
            except httpx2.TransportError:
                pass
            await asyncio.sleep(.2)
        root = await http.get(base)
        spa = await http.get(base + "/servers")
        assert root.status_code == spa.status_code == 200 and root.text == spa.text
        assert (await http.get(base + "/api/me")).status_code == 404
        assert "content-security-policy" in root.headers
    print("PASS unchanged dashboard image: HTTP/SPA fallback; /api is not swallowed")


def main():
    network = "urumi-stage80-" + uuid4().hex[:10]
    names = []
    common = ["--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges:true"]
    with tempfile.TemporaryDirectory(prefix="urumi-stage80-") as folder:
        root = Path(folder)
        def file(name, value):
            p = root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(value, encoding="utf-8")
            return p
        def mount(source, target):
            return ["--mount", f"type=bind,source={source},target={target},readonly"]
        file("postgres/password", PASSWORD)
        file("postgres/database-url", "postgresql+psycopg://urumi_gateway:" + PASSWORD + "@postgres:5432/urumi_gateway")
        file("admin/username", "fixture_admin")
        file("admin/password", PASSWORD)
        file("woo-auth/token", TOKEN)
        file("gemini/api-key", "SYNTHETIC-NOT-A-REAL-PROVIDER-KEY")
        file("rest/consumer-key", "TEST-ONLY-KEY")
        file("rest/consumer-secret", "TEST-ONLY-SECRET")
        dbmount = mount(root / "postgres/database-url", "/run/config/database-url")
        dbenv = ["-e", "URUMI_DATABASE_URL_FILE=/run/config/database-url"]
        def start(alias, image, args):
            name = network + "-" + alias
            run("docker", "run", "-d", "--name", name, "--network", network,
                "--network-alias", alias, *common, *args, image)
            names.append(name)
            return name
        def job(args, mode):
            name = network + "-" + mode + "-" + uuid4().hex[:6]
            names.append(name)
            run("docker", "run", "--rm", "--name", name, "--network", network,
                *common, *args, GATEWAY, "python", "-m", "urumi_gateway.deployment", mode)
        try:
            run("docker", "network", "create", network)
            pg = start("postgres", PG, ["--user", "999:999", "--memory=512m",
                "--tmpfs", "/var/lib/postgresql:uid=999,gid=999,mode=0700",
                "--tmpfs", "/var/run/postgresql:uid=999,gid=999", "--tmpfs", "/tmp:uid=999,gid=999",
                *mount(root / "postgres/password", "/run/secrets/password"),
                "-e", "POSTGRES_USER=urumi_gateway", "-e", "POSTGRES_DB=urumi_gateway",
                "-e", "POSTGRES_PASSWORD_FILE=/run/secrets/password"])
            # Deployment command performs the bounded database wait; no schema startup shortcut.
            job([*dbmount, *dbenv], "migrate")
            bootstrap_args = [*dbmount, *dbenv, *mount(root / "admin", "/run/admin"),
                *mount(root / "woo-auth", "/run/woo-auth"),
                "-e", "URUMI_BOOTSTRAP_USERNAME_FILE=/run/admin/username",
                "-e", "URUMI_BOOTSTRAP_PASSWORD_FILE=/run/admin/password",
                "-e", "URUMI_WOO_MCP_TOKEN_FILE=/run/woo-auth/token",
                "-e", "URUMI_WOO_MCP_URL=http://woo:8000/mcp",
                "-e", "URUMI_ARITHMETIC_MCP_URL=http://arithmetic:8000/mcp",
                "-e", "URUMI_STORE_POLICY_MCP_URL=http://policy:8000/mcp"]
            for _ in range(2):
                job(bootstrap_args, "bootstrap")
            job([*dbmount, *dbenv], "wait-ready")
            security(pg, 999)
            print("PASS PostgreSQL 18.6 non-root/read-only/security; empty DB migrations; bootstrap twice; schema/receipt gate")
            start("woo", "urumi-woo-mcp:stage8.0", ["--memory=256m", *mount(root / "rest", "/run/secrets/woocommerce-rest"),
                *mount(root / "woo-auth", "/run/auth"), "-e", "WOO_MCP_AUTH_TOKEN_FILE=/run/auth/token",
                "-e", "WOO_MCP_ALLOWED_HOSTS=woo:8000", "-e", "WOO_CONNECTION_ORIGIN=http://127.0.0.1:9"])
            for alias, image in (("arithmetic", "urumi-arithmetic-mcp:stage6.1"), ("policy", "urumi-store-policy-mcp:stage6.1")):
                start(alias, image, ["--memory=128m", "-e", "MCP_ALLOWED_HOSTS=" + alias + ":8000"])
            # Reserve a loopback port for the canonical Host/Origin used by this fixture.
            import socket
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
            base = f"http://127.0.0.1:{port}"
            gw = start("gateway", GATEWAY, ["--memory=512m", "-p", f"127.0.0.1:{port}:8000",
                *dbmount, *dbenv, *mount(root / "gemini", "/run/gemini"),
                "-e", "URUMI_GEMINI_API_KEY_FILE=/run/gemini/api-key", "-e", "URUMI_ENVIRONMENT=local",
                "-e", "URUMI_COOKIE_SECURE=false", "-e", "URUMI_BROWSER_ORIGIN=" + base])
            asyncio.run(acceptance(base))
            security(gw, 10001)
            dashboard = start("dashboard", "urumi-dashboard:stage7.1", ["--memory=128m",
                "--tmpfs", "/tmp:uid=10001,gid=10001,mode=1770,size=33554432", "-p", "127.0.0.1::8080"])
            published = json.loads(run("docker", "inspect", dashboard))[0]["NetworkSettings"]["Ports"]["8080/tcp"][0]["HostPort"]
            asyncio.run(dashboard_acceptance("http://127.0.0.1:" + published))
            live = [name for name in names if json.loads(run("docker", "inspect", name, check=False) or "[]")]
            for name in live[1:]:
                security(name, 10001)
            for name in live:
                r = subprocess.run(["docker", "logs", name], capture_output=True, text=True)
                assert all(value not in r.stdout + r.stderr for value in (TOKEN, PASSWORD, "TEST-ONLY-SECRET", "SYNTHETIC-NOT-A-REAL-PROVIDER-KEY"))
            print("PASS security and credential log exclusion; fixtures make no Woo/provider business requests")
        finally:
            for name in reversed(names):
                run("docker", "stop", "--time", "15", name, check=False)
                run("docker", "rm", name, check=False)
            run("docker", "network", "rm", network, check=False)
    print("PASS disposable containers/network/files removed")


if __name__ == "__main__":
    main()

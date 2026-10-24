"""Explicit Docker acceptance, never part of ordinary unit discovery. Dummy files only."""

import asyncio
import json
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

from hosting_checks import discover


def docker(*args, timeout=30):
    result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        # Do not forward child stderr, command representations or container logs.
        raise RuntimeError("Docker smoke operation failed: " + args[0])
    return result.stdout


def main(image):
    name = "urumi-woo-mcp-smoke-" + uuid.uuid4().hex[:8]
    started = False
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix="urumi-docker-") as directory:
        for filename, value in (("consumer-key", "TEST-ONLY-KEY"), ("consumer-secret", "TEST-ONLY-SECRET")):
            path = Path(directory) / filename
            path.write_text(value, encoding="utf-8")
            path.chmod(0o444)
        try:
            docker("run", "-d", "--name", name, "--read-only", "--cap-drop=ALL",
                   "--security-opt=no-new-privileges:true", "--memory=256m", "--cpus=0.5",
                   "--pids-limit=64", "--publish", f"127.0.0.1:{port}:8000",
                   "--mount", f"type=bind,source={directory},target=/run/secrets/woocommerce-rest,readonly",
                   "--env", "WOO_CONNECTION_ORIGIN=http://127.0.0.1:9",
                   "--env", "WOO_CANONICAL_ORIGIN=http://discovery.invalid",
                   "--env", f"WOO_MCP_ALLOWED_HOSTS=127.0.0.1:{port}", image)
            started = True
            deadline = time.monotonic() + 30
            while True:
                # Published TCP can exist before Uvicorn is ready, so inspect safe startup text.
                # Uvicorn normally logs to stderr: capture both without displaying either.
                log_result = subprocess.run(["docker", "logs", name], capture_output=True, text=True, timeout=5)
                logs = log_result.stdout + log_result.stderr
                if "Application startup complete" in logs:
                    break
                if time.monotonic() >= deadline:
                    raise RuntimeError("Container startup timed out")
                state = json.loads(docker("inspect", name))[0]["State"]
                if not state["Running"]:
                    raise RuntimeError("Container exited before startup")
                time.sleep(0.2)
            tools = asyncio.run(discover(f"http://127.0.0.1:{port}/mcp"))
            details = json.loads(docker("inspect", name))[0]
            host = details["HostConfig"]
            assert details["Config"]["User"] == "10001:10001"
            assert host["ReadonlyRootfs"] and host["CapDrop"] == ["ALL"]
            assert "no-new-privileges:true" in host["SecurityOpt"]
            assert len(details["Mounts"]) == 1 and details["Mounts"][0]["RW"] is False
            assert host["PortBindings"]["8000/tcp"][0]["HostIp"] == "127.0.0.1"
            check = '''import errno, json, os
from pathlib import Path
assert os.getuid() == os.getgid() == 10001
assert not Path('/app/tests').exists() and not Path('/app/.git').exists()
assert not Path('/app/src/woo_mcp/connectivity.py').exists()
assert not list(Path('/app').rglob('__pycache__'))
try:
    Path('/tmp/urumi-write-check').write_text('non-sensitive')
except OSError as error:
    assert error.errno == errno.EROFS
else:
    raise AssertionError('root filesystem was writable')
status = dict(line.split(':', 1) for line in Path('/proc/1/status').read_text().splitlines() if ':' in line)
assert status['NoNewPrivs'].strip() == '1'
assert int(status['CapEff'].strip(), 16) == 0
assert status['Seccomp'].strip() == '2'
print(json.dumps({'uid': os.getuid(), 'gid': os.getgid(), 'read_only_write_rejected': True,
                  'no_new_privileges': True, 'effective_capabilities': 0, 'seccomp_filter': True}))
'''
            security = json.loads(docker("exec", name, "python", "-c", check))
            assert "No broken requirements" in docker("exec", name, "python", "-m", "pip", "check")
            docker("stop", "--time", "20", name)
            state = json.loads(docker("inspect", name))[0]["State"]
            assert not state["Running"] and state["ExitCode"] == 0 and not state["OOMKilled"]
            log_result = subprocess.run(["docker", "logs", name], capture_output=True, text=True, timeout=5)
            logs = log_result.stdout + log_result.stderr
            assert "Application shutdown complete" in logs
            for forbidden in ("TEST-ONLY-KEY", "TEST-ONLY-SECRET", "Authorization", "oauth_signature"):
                assert forbidden not in logs
            image_info = json.loads(docker("image", "inspect", image))[0]
            evidence = {"result": "PASS", "image": image, "image_id": image_info["Id"],
                        "image_bytes": image_info["Size"], "tools": tools, "security": security,
                        "shutdown_exit": 0, "oom_killed": False, "business_calls": 0,
                        "credential_log_scan": "PASS"}
        finally:
            if started:
                docker("stop", "--time", "20", name)
                docker("rm", name)
            # Restore writable dummy files for Windows TemporaryDirectory cleanup.
            for path in Path(directory).iterdir():
                path.chmod(0o600)
    evidence["temporary_container_and_files_removed"] = True
    print(json.dumps(evidence))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) == 2 else "urumi-woo-mcp:stage4.8")

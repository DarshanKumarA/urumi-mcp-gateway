"""Create/check local gateway Secrets without credential files or command-line values."""
import argparse
import base64
import getpass
import json
import secrets
import subprocess
from urllib.parse import quote

CONTEXT = "k3d-urumi-local"
CONTRACTS = {
    "urumi-postgres-auth": {"password", "database-url"},
    "urumi-admin-bootstrap": {"username", "password"},
    "urumi-openrouter": {"api-key"},
    "urumi-woo-mcp-auth": {"token"},
}

def kubectl(*args, body=None):
    result = subprocess.run(["kubectl", "--context", CONTEXT, "-n", "urumi", *args],
        input=body, text=True, encoding="utf-8", capture_output=True, timeout=30)
    if result.returncode:
        raise RuntimeError("Kubernetes operation failed; check context, access and resource names. Details suppressed.")
    if args[0] == "create":
        return None
    return json.loads(result.stdout) if result.stdout.strip() else None

def valid_text(value):
    return isinstance(value, str) and bool(value.strip()) and value == value.strip() and not any(c in value for c in "\r\n\x00")

def check_existing(name, obj):
    if obj.get("type") != "Opaque" or obj.get("metadata", {}).get("deletionTimestamp"):
        raise ValueError("Existing Secret type/state conflict: " + name)
    data = obj.get("data", {})
    if set(data) != CONTRACTS[name]:
        raise ValueError("Existing Secret key-name conflict: " + name)
    for value in data.values():
        if not valid_text(base64.b64decode(value, validate=True).decode("utf-8")):
            raise ValueError("Existing Secret contains empty/invalid text: " + name)

def values_for(name):
    if name == "urumi-postgres-auth":
        password = secrets.token_urlsafe(32)
        return {"password": password, "database-url":
            "postgresql+psycopg://urumi_gateway:" + quote(password, safe="") +
            "@urumi-postgres.urumi.svc.cluster.local:5432/urumi_gateway"}
    if name == "urumi-woo-mcp-auth":
        return {"token": secrets.token_urlsafe(32)}
    if name == "urumi-admin-bootstrap":
        username = input("Gateway admin username (for example urumiadmin): ").strip()
        import re
        if not re.fullmatch(r"[a-z][a-z0-9_-]{2,63}", username):
            raise ValueError("Use 3-64 lowercase letters, numbers, dash or underscore, starting with a letter.")
        password = getpass.getpass("Gateway admin password (12-128 characters): ")
        if not 12 <= len(password) <= 128 or password != getpass.getpass("Confirm gateway admin password: "):
            raise ValueError("Password length or confirmation failed.")
        return {"username": username, "password": password}
    return {"api-key": getpass.getpass("OpenRouter API key: ")}

def run(mode):
    namespace = kubectl("get", "namespace", "urumi", "-o", "json")
    if namespace.get("status", {}).get("phase") != "Active":
        raise ValueError("Namespace urumi must already be Active.")
    # Inspect every existing object before creating any missing object.
    missing = []
    for name in CONTRACTS:
        existing = kubectl("get", "secret", name, "--ignore-not-found", "-o", "json")
        if existing:
            check_existing(name, existing)
            print(name + ": existing contract valid; preserved")
        else:
            missing.append(name)
    if mode == "check":
        for name in missing:
            print(name + ": missing")
        return int(bool(missing))
    for name in missing:
        values = values_for(name)
        if not all(valid_text(v) for v in values.values()):
            raise ValueError("Credential must be nonempty single-line text without edge whitespace.")
        body = json.dumps({"apiVersion":"v1", "kind":"Secret", "type":"Opaque",
            "metadata":{"name":name,"namespace":"urumi"}, "stringData":values})
        # create, never apply/replace. Races fail closed instead of overwriting.
        kubectl("create", "-f", "-", "-o", "name", body=body)
        values, body = None, None
        print(name + ": created")
    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["check", "create"])
    args = parser.parse_args()
    try:
        raise SystemExit(run(args.mode))
    except (Exception, KeyboardInterrupt) as error:
        # Never print subprocess, parser or credential-bearing exception contents.
        print("Setup stopped (" + type(error).__name__ + "). Existing Secrets were not replaced.")
        raise SystemExit(1)

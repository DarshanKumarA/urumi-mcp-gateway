"""Collect fixture/offline checks with dated logs. Never deploys or reads live Secrets."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def utc():
    return datetime.now(timezone.utc).isoformat()


def clean(text):
    # Defense in depth, not a guarantee that arbitrary output is safe to publish.
    text = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+(?=\n|$)", "", text)
    text = re.sub(r"\n{2,}\Z", "\n", text)
    for folder, label in ((ROOT, "<REPO>"), (Path.home(), "<USER>")):
        for spelling in (str(folder), folder.as_posix()):
            text = text.replace(spelling, label)
    return re.sub(r"(?:urumi_key_[A-Za-z0-9_-]{43}|sk-or-v1-[A-Za-z0-9_-]+|"
                  r"AIza[A-Za-z0-9_-]{35}|\b(?:ck|cs)_[a-fA-F0-9]{40}\b|"
                  r"Bearer [A-Za-z0-9_.-]{24,})", "[REDACTED]", text)


def app_python(app):
    folder = ROOT / "apps" / app / ".venv"
    return str(folder / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="New/empty directory; default .test-results/<UTC timestamp>")
    parser.add_argument("--schema-file", type=Path, help="Kubernetes v1.35.5 OpenAPI v2 JSON; omitted check is SKIPPED")
    args = parser.parse_args()
    output = (args.output or ROOT / ".test-results" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")).resolve()
    if output.exists() and any(output.iterdir()):
        parser.error("Output directory must be empty; retained runs are never overwritten.")
    output.mkdir(parents=True, exist_ok=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    tracked_dirty = bool(subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT))
    report = {"format_version": 1, "started_utc": utc(), "source_commit": head,
              "tracked_changes_present": tracked_dirty,
              "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "scope": "Fixture tests, localhost TCP, offline helpers, builds and static chart/repository checks. No live store/provider/Kubernetes calls.",
              "log_policy": "Combined stdout/stderr; ANSI removed, LF line endings, trailing spaces removed, local home/repository paths normalized, common key patterns redacted. Review before sharing.",
              "checks": []}
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("URUMI_", "WOO_", "OPENROUTER_", "GEMINI_", "GOOGLE_API_KEY"))}
    env.pop("FORCE_COLOR", None)
    env.update(NO_COLOR="1", CI="true", PYTHONUTF8="1")

    def save():
        (output / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8", newline="\n")

    def check(name, command, *, cwd=ROOT, pythonpath=None, skip=None, timeout=300):
        record = {"id": name, "command": [clean(str(x)) for x in command],
                  "cwd": cwd.relative_to(ROOT).as_posix(), "started_utc": utc()}
        print("RUN " + name, flush=True)
        start = time.monotonic()
        if skip:
            record.update(status="SKIPPED", reason=skip, exit_code=None)
        else:
            child_env = dict(env)
            if pythonpath is not None:
                child_env["PYTHONPATH"] = str(pythonpath)
            try:
                p = subprocess.run(command, cwd=cwd, env=child_env, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   timeout=timeout, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                raw, code = p.stdout, p.returncode
            except subprocess.TimeoutExpired as error:
                raw, code = (error.stdout or b"") + b"\nRUNNER: timeout; check process cleanup before retrying.\n", 124
            except OSError:
                raw, code = b"RUNNER: executable unavailable; install prerequisites from the testing guide.\n", 127
            text = clean(raw.decode("utf-8", errors="replace"))
            log = output / (name + ".txt")
            log.write_text(text, encoding="utf-8", newline="\n")
            record.update(status="PASS" if code == 0 else "FAIL", exit_code=code,
                          log=log.name, sha256=hashlib.sha256(log.read_bytes()).hexdigest())
            counts = re.findall(r"Ran (\d+) tests? in", text)
            if not counts and name == "dashboard-tests":
                counts = re.findall(r"Tests\s+(\d+) passed", text)
            if counts:
                record["test_count"] = int(counts[-1])
        record.update(finished_utc=utc(), duration_seconds=round(time.monotonic()-start, 3))
        report["checks"].append(record)
        save()
        print(record["status"] + " " + name, flush=True)

    for app in ("gateway", "woo-mcp", "arithmetic-mcp", "store-policy-mcp"):
        check(app + "-tests", [app_python(app), "-m", "unittest", "discover", "-s", "tests", "-v"],
              cwd=ROOT / "apps" / app, pythonpath="src")
    check("platform-secret-helper", [sys.executable, "-m", "unittest", "discover", "-s", "tests/integration", "-p", "test_platform_secret_setup.py", "-v"])
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm") or "npm"
    check("dashboard-tests", [npm, "test", "--", "--reporter=verbose"], cwd=ROOT / "apps/dashboard")
    check("dashboard-build", [npm, "run", "build"], cwd=ROOT / "apps/dashboard")
    for helper in ("setup-store-secrets", "setup-woocommerce-rest-secret"):
        check(helper, ["pwsh", "-NoProfile", "-File", "scripts/"+helper+".ps1", "-Mode", "Validate"])
    for app in ("arithmetic-mcp", "store-policy-mcp"):
        check(app + "-tcp", [app_python(app), "tests/upstreams/smoke.py", app], pythonpath=ROOT / "apps" / app / "src")
    for overlay in ("local", "prod"):
        check("helm-"+overlay, ["helm", "lint", "charts/urumi", "-f", "charts/urumi/values-"+overlay+".yaml"])
    if args.schema_file:
        schema = args.schema_file.resolve()
        if schema.is_file():
            report["schema_sha256"] = hashlib.sha256(schema.read_bytes()).hexdigest()
        check("chart-schema", [sys.executable, "tests/integration/validate_chart.py", str(schema)])
    else:
        check("chart-schema", [], skip="Supply --schema-file with Kubernetes v1.35.5 OpenAPI v2 JSON.")
    check("repository", [sys.executable, "tests/integration/repository_checks.py", "--tracked-only"])
    check("git-whitespace", ["git", "diff", "--check"])
    report["finished_utc"] = utc()
    report["totals"] = {s: sum(c["status"] == s for c in report["checks"]) for s in ("PASS", "FAIL", "SKIPPED")}
    report["passed_test_count"] = sum(c.get("test_count", 0) for c in report["checks"] if c["status"] == "PASS")
    save()
    print(json.dumps({"output": str(output), "totals": report["totals"], "passed_tests": report["passed_test_count"]}), flush=True)
    return int(report["totals"]["FAIL"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())

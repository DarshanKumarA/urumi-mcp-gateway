"""Offline source/lock/documentation checks; heuristic scans are not a secret detector guarantee."""
import json
from pathlib import Path
import re
import subprocess
import tomllib
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]


def files():
    result = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT)
    return sorted({ROOT / s.decode() for s in result.split(b"\0") if s})


def anchors(text):
    found = set()
    counts = {}
    for line in text.splitlines():
        if not re.match(r"^#{1,6} ", line):
            continue
        name = re.sub(r"[^\w\- ]", "", re.sub(r"^#+ ", "", line).strip().lower()).replace(" ", "-")
        occurrence = counts.get(name, 0)
        found.add(name + ("-" + str(occurrence) if occurrence else ""))
        counts[name] = occurrence + 1
    return found


def docs(paths):
    errors = []
    count = 0
    for path in paths:
        if path.suffix != ".md":
            continue
        text = path.read_text(encoding="utf-8")
        text = re.sub(r"```.*?```", "", text, flags=re.S)
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
            if re.match(r"\w+:", target) or target.startswith("//"):
                continue
            dest, _, fragment = unquote(target.strip("<>")).partition("#")
            resolved = (path.parent / dest).resolve() if dest else path
            if not resolved.exists():
                errors.append((str(path.relative_to(ROOT)), "missing link", target))
            elif fragment and resolved.suffix == ".md" and fragment not in anchors(resolved.read_text(encoding="utf-8")):
                errors.append((str(path.relative_to(ROOT)), "missing anchor", target))
            count += 1
        expected = None
        for number, line in enumerate(text.splitlines(), 1):
            if line.startswith("|"):
                columns = len(re.findall(r"(?<!\\)\|", re.sub(r"`[^`]*`", "CODE", line)))
                if expected is None:
                    expected = columns
                elif columns != expected:
                    errors.append((str(path.relative_to(ROOT)), "table columns", number))
            else:
                expected = None
    if errors:
        print(json.dumps(errors, indent=2))
        raise AssertionError("Documentation checks failed")
    print("PASS documentation relative links/anchors/tables:", count, "links")


def scan(paths):
    patterns = {
        "Woo credential": r"\b(?:ck|cs)_[a-fA-F0-9]{40}\b",
        "Google key": r"\bAIza[A-Za-z0-9_-]{35}\b",
        "private key": r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        "live gateway key": r"urumi_key_[A-Za-z0-9_-]{43}",
        "literal bearer": r"Bearer [A-Za-z0-9_-]{32,}",
        "contact": r"\b[A-Za-z0-9._%+-]+@(?![^\s@]*(?:example\.|\.invalid\b|\.test\b))[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    }
    hits = []
    for path in paths:
        if not path.is_file() or path.suffix in {".docx", ".png", ".jpg", ".zip", ".pdf"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeError:
            continue
        for label, pattern in patterns.items():
            for match in re.finditer(pattern, text):
                # Explicit synthetic test tokens are non-sensitive fixtures.
                if "SYNTHETIC" in match.group() or "TEST-ONLY" in match.group():
                    continue
                hits.append((str(path.relative_to(ROOT)), label, text.count("\n", 0, match.start()) + 1))
    if hits:
        print(json.dumps(hits, indent=2))  # Locations only, never matched material.
        raise AssertionError("Scan findings need review")
    print("PASS heuristic credential/contact scan, including built dashboard assets")


def locks():
    for app in ("gateway", "woo-mcp", "arithmetic-mcp", "store-policy-mcp"):
        folder = ROOT / "apps" / app
        project = tomllib.loads((folder / "pyproject.toml").read_text())
        content = (folder / "requirements.lock").read_text().replace("\\\n", " ")
        pins = {}
        for line in content.splitlines():
            if not line or line.startswith("#"):
                continue
            match = re.match(r"([\w.-]+)==([^ ;]+)", line)
            assert match and re.search(r"--hash=sha256:[a-f0-9]{64}(?:\s|$)", line)
            name, version = match.groups()
            pins[name.lower().replace("_", "-")] = version
        for direct in project["project"]["dependencies"]:
            name, version = direct.split("==")
            name = re.sub(r"\[.*\]", "", name).lower().replace("_", "-")
            assert pins[name] == version
        python = folder / ".venv/Scripts/python.exe"
        installed = json.loads(subprocess.check_output([str(python), "-c",
            "import importlib.metadata as m,json; print(json.dumps({d.metadata['Name'].lower().replace('_','-'):d.version for d in m.distributions()}))"], text=True))
        for name, version in pins.items():
            assert installed.get(name) == version, app + " installed/lock mismatch: " + name
        subprocess.run([str(python), "-m", "pip", "check"], check=True, capture_output=True)
        print("PASS", app, "direct pins/hash-lock/installed consistency:", len(pins), "packages")
    folder = ROOT / "apps/dashboard"
    package = json.loads((folder / "package.json").read_text())
    lock = json.loads((folder / "package-lock.json").read_text())
    for kind in ("dependencies", "devDependencies"):
        assert lock["packages"][""][kind] == package[kind]
        for name, version in package[kind].items():
            assert lock["packages"]["node_modules/" + name]["version"] == version
    assert all("integrity" in p and p.get("resolved", "").startswith("https://")
               for name, p in lock["packages"].items() if name)
    print("PASS npm manifest/lock pins and artifact integrity metadata")


if __name__ == "__main__":
    paths = files()
    locks()
    docs(paths)
    scan(paths + list((ROOT / "apps/dashboard/dist").rglob("*")))

"""Full-stack static validation, including historical r4 source comparison; no cluster access."""
import argparse
import copy
import importlib.util
import json
import re
from pathlib import Path
import shutil
import subprocess
import tempfile

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("aux_checks", ROOT / "tests/upstreams/validate_chart.py")
aux = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aux)


def render(chart, env, revision):
    # Helm template fixes Revision=1; substitute only in an isolated temporary chart.
    with tempfile.TemporaryDirectory(prefix="urumi-render-") as directory:
        target = Path(directory) / "chart"
        shutil.copytree(chart, target)
        for path in (target / "templates").glob("*"):
            text = path.read_text(encoding="utf-8").replace("$.Release.Revision", str(revision)).replace(".Release.Revision", str(revision))
            path.write_text(text, encoding="utf-8")
        r = subprocess.run(["helm", "template", "urumi", str(target), "--namespace", "urumi", "--is-upgrade",
                            "-f", str(target / ("values-" + env + ".yaml"))], capture_output=True, text=True, check=True)
        return [o for o in yaml.load_all(r.stdout, Loader=aux.UniqueLoader) if o]


def historical_chart(destination, ref):
    files = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", ref, "charts/urumi"], text=True).splitlines()
    for name in files:
        p = destination / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(subprocess.check_output(["git", "show", ref + ":" + name]))
    return destination / "charts/urumi"


def validate(schema):
    defs = json.loads(schema.read_text(encoding="utf-8"))["definitions"]
    aux.adapt(defs)
    chart = ROOT / "charts/urumi"
    for path in chart.glob("*.yaml"):
        list(yaml.load_all(path.read_text(), Loader=aux.UniqueLoader))
    with tempfile.TemporaryDirectory(prefix="urumi-approved-chart-") as directory:
        old = historical_chart(Path(directory) / "r4", "88e5cae")
        previous = historical_chart(Path(directory) / "stage7", "f793e62")
        for env in ("local", "prod"):
            objects = render(chart, env, 5)
            current = {(o["kind"], o["metadata"]["name"]): o for o in objects}
            assert len(objects) == len(current) == 27
            for o in objects:
                assert len(o["metadata"]["name"]) <= 63
                group, _, version = o["apiVersion"].rpartition("/")
                group, version = group or "", version or o["apiVersion"]
                names = [n for n, d in defs.items() if {"group": group, "version": version, "kind": o["kind"]}
                         in d.get("x-kubernetes-group-version-kind", [])]
                assert len(names) == 1
                jsonschema.Draft4Validator({"$ref": "#/definitions/" + names[0], "definitions": defs}).validate(o)
            assert not any(o["kind"] in {"Secret", "Namespace", "PersistentVolume"} for o in objects)
            serialized = json.dumps(objects)
            for pattern in (r"\b(?:ck|cs)_[a-f0-9]{40}\b", r"\bAIza[A-Za-z0-9_-]{35}\b",
                            r"Bearer [A-Za-z0-9_-]{32,}", r"-----BEGIN .*PRIVATE KEY", r'"stringData"'):
                assert not re.search(pattern, serialized), "Rendered credential-pattern finding"
            # Original eight store objects equal historical source, after r4 -> r5 names only.
            store = [o for o in render(old, env, 4) if "woo-mcp" not in o["metadata"]["name"]]
            assert len(store) == 8
            for o in store:
                normalized = json.loads(json.dumps(o).replace("urumi-store-bootstrap-r4", "urumi-store-bootstrap-r5").replace("urumi-store-assets-r4", "urumi-store-assets-r5"))
                key = normalized["kind"], normalized["metadata"]["name"]
                assert current[key] == normalized, "Unapproved store delta: " + str(key)
            for o in render(previous, env, 5):
                if any(c in o["metadata"]["name"] for c in ("arithmetic-mcp", "store-policy-mcp")):
                    assert current[o["kind"], o["metadata"]["name"]] == o
            pods = {o["metadata"]["name"]: o["spec"]["template"] for o in objects if o["kind"] in {"Deployment", "StatefulSet", "Job"}}
            for o in objects:
                if o["kind"] != "Service":
                    continue
                assert o["spec"]["type"] == "ClusterIP" and not o["spec"].get("externalIPs")
                matched = [p for p in pods.values() if all(p["metadata"]["labels"].get(k) == v for k, v in o["spec"]["selector"].items())]
                assert matched
                for port in o["spec"]["ports"]:
                    assert any(port["targetPort"] == cp["name"] or port["targetPort"] == cp["containerPort"]
                               for p in matched for c in p["spec"]["containers"] for cp in c.get("ports", []))
            refs = {}
            for name, pod in pods.items():
                if name in {"urumi-wordpress", "urumi-mariadb"} or "store-bootstrap" in name:
                    continue
                ps = pod["spec"]
                assert ps["automountServiceAccountToken"] is False
                assert ps["securityContext"]["runAsNonRoot"] and ps["securityContext"]["seccompProfile"]["type"] == "RuntimeDefault"
                refs[name] = {v["secret"]["secretName"]: {i["key"] for i in v["secret"]["items"]}
                              for v in ps.get("volumes", []) if "secret" in v}
                for c in ps["containers"] + ps.get("initContainers", []):
                    assert c["securityContext"] == {"allowPrivilegeEscalation": False,
                        "readOnlyRootFilesystem": True, "capabilities": {"drop": ["ALL"]}}
                    assert set(c["resources"]) == {"requests", "limits"}
                    for m in c.get("volumeMounts", []):
                        if any(v["name"] == m["name"] and "secret" in v for v in ps.get("volumes", [])):
                            assert m["readOnly"]
                if not "gateway-migrate" in name and not "gateway-bootstrap" in name:
                    for probe in ("startupProbe", "readinessProbe", "livenessProbe"):
                        assert probe in ps["containers"][0]
            assert refs["urumi-dashboard"] == {}
            assert refs["urumi-gateway"] == {"urumi-postgres-auth": {"database-url"}, "urumi-gemini": {"api-key"}}
            assert refs["urumi-gateway-migrate-r5"] == {"urumi-postgres-auth": {"database-url"}}
            assert refs["urumi-gateway-bootstrap-r5"] == {"urumi-postgres-auth": {"database-url"},
                "urumi-admin-bootstrap": {"username", "password"}, "urumi-woo-mcp-auth": {"token"}}
            assert refs["urumi-woo-mcp"] == {"urumi-woocommerce-rest": {"consumer-key", "consumer-secret"}, "urumi-woo-mcp-auth": {"token"}}
            assert refs["urumi-postgres"] == {"urumi-postgres-auth": {"password"}}
            policies = [o for o in objects if o["kind"] == "NetworkPolicy"]
            assert len(policies) == 4
            for policy in policies:
                ps = policy["spec"]
                assert ps["policyTypes"] == ["Ingress"] and "egress" not in ps
                component = ps["podSelector"]["matchLabels"]["app.kubernetes.io/component"]
                selected = [p for p in pods.values() if all(p["metadata"]["labels"].get(k) == v for k, v in ps["podSelector"]["matchLabels"].items())]
                assert len(selected) == 1
                rule = ps["ingress"][0]
                assert rule["ports"] == [{"protocol": "TCP", "port": 5432 if component == "postgres" else 8000}]
                selector = rule["from"][0]["podSelector"]
                assert selector["matchLabels"] == {"app.kubernetes.io/name": "urumi", "app.kubernetes.io/instance": "urumi"}
                assert selector["matchExpressions"][0]["values"] == (["gateway", "gateway-migrate", "gateway-bootstrap"] if component == "postgres" else ["gateway"])
            ingresses = [o for o in objects if o["kind"] == "Ingress"]
            assert len(ingresses) == 2
            app = current["Ingress", "urumi-application"]
            paths = app["spec"]["rules"][0]["http"]["paths"]
            assert [(p["path"], p["pathType"], p["backend"]["service"]["name"]) for p in paths] == [
                ("/api", "Prefix", "urumi-gateway"), ("/mcp", "Prefix", "urumi-gateway"), ("/", "Prefix", "urumi-dashboard")]
            assert bool(app["spec"].get("tls")) == (env == "prod")
            pg = current["StatefulSet", "urumi-postgres"]["spec"]
            assert pg["persistentVolumeClaimRetentionPolicy"] == {"whenScaled": "Retain", "whenDeleted": "Retain"}
            claim = pg["volumeClaimTemplates"][0]
            assert claim["metadata"]["name"] == "data" and claim["spec"]["resources"]["requests"]["storage"] == "2Gi"
            gw = pods["urumi-gateway"]["spec"]
            assert gw["initContainers"][0]["command"][-1] == "wait-ready"
            container = gw["containers"][0]
            assert container["readinessProbe"]["httpGet"]["path"] == "/health/ready"
            assert container["livenessProbe"]["tcpSocket"]["port"] == "http"
            envs = {e["name"]: e["value"] for e in container["env"]}
            assert envs["URUMI_COOKIE_SECURE"] == ("true" if env == "prod" else "false")
            assert "AUTHORIZATION" not in json.dumps(objects).upper()
            print("PASS", env, "27 objects; v1.35.5 schema/unique keys/names/selectors/ports/probes/security/Secret contracts/NetworkPolicies/Ingress/storage")
            print("PASS eight r4 store objects identical except bootstrap r4->r5 names; four auxiliary objects identical")
            print("Inventory:", ", ".join(k + "/" + n for k, n in current))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("schema", type=Path)
    validate(parser.parse_args().schema)

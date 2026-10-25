"""Offline Helm checks. Supply official Kubernetes v1.35.5 swagger.json on disk.

Uses workstation PyYAML/jsonschema, not either application's runtime dependencies.
No kubectl, cluster connection, apply or install. Renders stay in memory.
"""
import argparse
import json
from pathlib import Path
import subprocess
import yaml
import jsonschema


class UniqueLoader(yaml.SafeLoader):
    pass


def mapping(loader, node, deep=False):
    keys = [loader.construct_object(k, deep=deep) for k, v in node.value]
    assert len(keys) == len(set(keys)), "Duplicate YAML keys"
    return yaml.SafeLoader.construct_mapping(loader, node, deep)


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)


def adapt(value):
    if isinstance(value, dict):
        if value.get("format") == "int-or-string":
            value.pop("type", None)
            value.pop("format", None)
            value["anyOf"] = [{"type": "integer"}, {"type": "string"}]
        if value.get("type") == "object" and "properties" in value and "additionalProperties" not in value:
            value["additionalProperties"] = False
        for item in value.values():
            adapt(item)
    elif isinstance(value, list):
        for item in value:
            adapt(item)


def render(chart, values=None, release="urumi", namespace="urumi"):
    args = ["helm", "template", release, str(chart), "--namespace", namespace]
    if values:
        args += ["-f", str(chart / values)]
    result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", check=True)
    return [o for o in yaml.load_all(result.stdout, Loader=UniqueLoader) if o]


def validate(schema, chart, baseline=None):
    defs = json.loads(schema.read_text(encoding="utf-8"))["definitions"]
    adapt(defs)
    for path in chart.glob("*.yaml"):
        list(yaml.load_all(path.read_text(encoding="utf-8"), Loader=UniqueLoader))
    for env in ("local", "prod"):
        objects = render(chart, "values-" + env + ".yaml")
        current = {(o["kind"], o["metadata"]["name"]): o for o in objects}
        assert len(objects) == len(current) == 14
        if baseline:
            previous = {(o["kind"], o["metadata"]["name"]): o for o in render(baseline, "values-" + env + ".yaml")}
            assert all(current[k] == v for k, v in previous.items()), "Existing resource changed"
            assert set(current) - set(previous) == {(kind, "urumi-" + c) for kind in ("Deployment", "Service")
                for c in ("arithmetic-mcp", "store-policy-mcp")}
        for o in objects:
            group, _, version = o["apiVersion"].rpartition("/")
            group, version = group or "", version or o["apiVersion"]
            names = [n for n, d in defs.items() if {"group": group, "version": version, "kind": o["kind"]}
                     in d.get("x-kubernetes-group-version-kind", [])]
            assert len(names) == 1
            jsonschema.Draft4Validator({"$ref": "#/definitions/" + names[0], "definitions": defs}).validate(o)
        assert not any(o["kind"] in {"Secret", "Namespace", "PersistentVolume"} for o in objects)
        for comp in ("arithmetic-mcp", "store-policy-mcp"):
            d = current["Deployment", "urumi-" + comp]
            svc = current["Service", "urumi-" + comp]
            pod = d["spec"]["template"]
            spec, container = pod["spec"], pod["spec"]["containers"][0]
            assert d["spec"]["replicas"] == 1 and svc["spec"]["type"] == "ClusterIP"
            assert not svc["spec"].get("externalIPs")
            assert svc["spec"]["selector"] == d["spec"]["selector"]["matchLabels"]
            assert all(pod["metadata"]["labels"][k] == v for k, v in svc["spec"]["selector"].items())
            assert container["ports"] == [{"name": "http", "containerPort": 8000}]
            assert svc["spec"]["ports"] == [{"name": "http", "port": 8000, "targetPort": "http"}]
            assert spec["automountServiceAccountToken"] is False
            assert not spec.get("volumes") and not container.get("volumeMounts") and not container.get("envFrom")
            assert spec["securityContext"] == {"runAsNonRoot": True, "runAsUser": 10001,
                "runAsGroup": 10001, "seccompProfile": {"type": "RuntimeDefault"}}
            assert container["securityContext"] == {"allowPrivilegeEscalation": False,
                "readOnlyRootFilesystem": True, "capabilities": {"drop": ["ALL"]}}
            assert container["resources"] == {"requests": {"cpu": "25m", "memory": "64Mi"},
                                               "limits": {"cpu": "250m", "memory": "128Mi"}}
            for probe in ("startupProbe", "livenessProbe", "readinessProbe"):
                assert container[probe]["tcpSocket"]["port"] == "http"
            assert {e["name"] for e in container["env"]} == {"MCP_ALLOWED_HOSTS", "PYTHONDONTWRITEBYTECODE"}
            hosts = next(e["value"] for e in container["env"] if e["name"] == "MCP_ALLOWED_HOSTS").split(",")
            assert "urumi-" + comp + ".urumi.svc.cluster.local:8000" in hosts
            assert "*" not in "".join(hosts)
            assert container["imagePullPolicy"] == ("Never" if env == "local" else "IfNotPresent")
            assert not any(o["kind"] in {"Ingress", "PersistentVolumeClaim", "Secret"} and comp in json.dumps(o) for o in objects)
        print("PASS", env, "14 objects; v1.35.5 schema; unique keys; selectors/ports/probes/resources/security/hosts; ClusterIP only")
    assert len(render(chart)) == 8
    # Respect the existing revision-specific store Job's stricter name bound.
    long = render(chart, "values-local.yaml", release="r" * 40, namespace="fixture")
    auxiliaries = [o for o in long if o["metadata"].get("labels", {}).get("app.kubernetes.io/component") in {"arithmetic-mcp", "store-policy-mcp"}]
    assert len(auxiliaries) == 4 and all(len(o["metadata"]["name"]) <= 63 for o in auxiliaries)
    print("PASS default 8 resources; long-release names bounded; existing resources unchanged" if baseline else "PASS default and long-release renders")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("schema", type=Path)
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    validate(args.schema, Path(__file__).resolve().parents[2] / "charts/urumi", args.baseline)

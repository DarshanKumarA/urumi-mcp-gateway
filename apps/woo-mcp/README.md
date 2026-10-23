# WooCommerce REST connectivity slice

Stage 4.3 implements credential-file loading, a pooled asynchronous read client and
one acceptance command. There is no MCP server, tool layer, write method, Dockerfile
or Helm workload here. Runtime execution requires separate authorization; do not
run this command repeatedly against the store to troubleshoot authentication.

## Dependencies and offline checks

Use Python 3.13. Direct pins are [HTTPX 0.28.1](https://pypi.org/project/httpx/0.28.1/)
(async HTTP, connection pooling, timeouts, mock transport) and
[OAuthLib 4.0.0](https://pypi.org/project/oauthlib/4.0.0/) (OAuth 1.0a signing,
including HMAC-SHA256). OAuthLib is transport-independent; signing the canonical
URL before handing headers to HTTPX makes the two origins explicit. No manual
cryptography or additional OAuth integration framework is needed. HTTPX's stable
0.28.1 release is used rather than a 1.0 development release. The hash-locked
universal wheels in requirements.lock include all resolved runtime dependencies.
Tests use the standard library unittest and HTTPX MockTransport.

From the repository root in PowerShell:

```powershell
py -3.13 -m venv apps/woo-mcp/.venv
apps/woo-mcp/.venv/Scripts/python -m pip install --require-hashes --only-binary=:all: -r apps/woo-mcp/requirements.lock
$env:PYTHONPATH = (Join-Path $PWD 'apps/woo-mcp/src')
apps/woo-mcp/.venv/Scripts/python -m unittest discover -s apps/woo-mcp/tests -v
```

The virtual environment/caches are ignored. Fixtures contain only TEST-ONLY
credentials and never contact Kubernetes or the store. The signature fixture uses
OAuthLib with fixed dummy nonce/time to check canonical-origin integration; it is
not an independent cryptographic validation of OAuthLib.

## Connection contract

| Setting | Value |
| --- | --- |
| Network origin | http://urumi-wordpress.urumi.svc.cluster.local |
| Canonical signing origin | http://store.urumi.test:8080 |
| Host header | store.urumi.test:8080 |
| Request | GET /wp-json/wc/v3/products with SKU, per_page=2 and allowlisted _fields |
| Authentication | OAuth 1.0a HMAC-SHA256 in Authorization only |
| Secret files | /run/secrets/woocommerce-rest/consumer-key and consumer-secret |
| Timeouts | Connect 2s; read/write 5s; pool 1s; whole REST call 8s; DNS precheck 3s |
| Bounds | 64 KiB decoded response; no redirects; no retries; at most two returned products |

The same URL-encoded query is used for signing and transport. Environment proxies
and netrc are disabled. This slice deliberately supports the accepted HTTP OAuth
path only; future HTTPS/Basic support requires a separate implementation and test.
HTTP OAuth is not TLS confidentiality. Config origins are deployment settings,
never user/tool inputs. No public endpoint or Kubernetes API access is needed.

The diagnostic entrypoint is `python -m woo_mcp.connectivity`. It performs one
SKU lookup for URUMI-DEMO-001 and only emits the exact expected public product
11. Failure output contains fixed codes/status/origins, not upstream bodies,
redirect destinations, headers or exceptions. It disables Python logging, including
signer/HTTP debug logs. Future embedding must preserve this no-wire-debug policy.
Credential objects suppress repr; Python/library immutable strings cannot be
reliably erased. Do not attach debuggers, enable tracing, or dump request objects.

## Disposable in-cluster acceptance

Use only the separately authorized diagnostic Pod urumi-rest-connectivity and a
same-named source ConfigMap in namespace urumi. No Helm changes. The ConfigMap
contains these Python sources and requirements.lock, never credentials. Mount it
at /app/woo_mcp; mount only the existing urumi-woocommerce-rest Secret as read-only
files at the path above, mode 0440. Disable service-account token mounting. Use
nonroot UID/GID/fsGroup 1000, read-only root filesystem, dropped capabilities,
RuntimeDefault seccomp, and a 64Mi emptyDir at /tmp.

Diagnostic image: official python:3.13-slim-bookworm, Linux/amd64 digest
sha256:4cea12ab7d78a3312c85f8cab19b6971d4fe9704da25443986c0bc20a6678850.
This is a test runner, not the future application image. Request 50m CPU/128Mi;
limit 500m/256Mi. restartPolicy Never and activeDeadlineSeconds 600 bound the
Pod. Install hash-verified binary wheels into /tmp/deps from PyPI with pip output
suppressed; exit with a fixed message on setup failure. PYTHONPATH=/app:/tmp/deps
and PYTHONDONTWRITEBYTECODE=1 are non-secret settings. Readiness checks the
dependency-ready file; this finite diagnostic is not a service with application
readiness/liveness endpoints. The idle process is bounded and does not run the
business read automatically or retry it.

Once setup succeeds, invoke exactly once:

```powershell
kubectl --context k3d-urumi-local -n urumi exec urumi-rest-connectivity -- python -m woo_mcp.connectivity
```

A successful HTTP response proves DNS/TCP/Host/auth behavior together; no packet
capture or Authorization echo is needed. It does not prove write permission by
exercise, the five MCP tools, or gateway-only access. Read/Write issuance is the
user's administrative evidence. Stop on auth/network/redirect failure; do not
change credentials/origins/store settings or run the read again without review.
After success, remove only this diagnostic Pod and source ConfigMap. Never remove
the REST Secret or store resources. See [progress](../../docs/progress.md) for the
actual result and any remaining limitations.

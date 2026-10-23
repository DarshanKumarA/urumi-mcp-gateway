# WooCommerce MCP: first read-only tool

Stage 4.4 adds the official SDK ASGI server and exactly one tool, list_products.
Stage 4.3's credential loading, OAuth transport and acceptance command remain.
There are no other tools, write methods, Dockerfile or Helm workload here.
Runtime store execution requires separate authorization; offline tests use dummy
credentials and mocked REST exclusively. Do not repeat the live diagnostic merely
to test MCP. Gateway caller authentication and Kubernetes hosting remain future work.

## Dependencies and offline checks

Use Python 3.13. Direct pins are [HTTPX 0.28.1](https://pypi.org/project/httpx/0.28.1/)
(async HTTP, connection pooling, timeouts, mock transport) and
[OAuthLib 4.0.0](https://pypi.org/project/oauthlib/4.0.0/) (OAuth 1.0a signing,
including HMAC-SHA256). OAuthLib is transport-independent; signing the canonical
URL before handing headers to HTTPX makes the two origins explicit. No manual
cryptography or additional OAuth integration framework is needed. HTTPX's stable
0.28.1 release is used rather than a 1.0 development release. The hash-locked
wheels in requirements.lock include all resolved runtime dependencies.
Stage 4.4 adds [MCP 2.3.0](https://pypi.org/project/mcp/2.3.0/) and
Pydantic 2.14.1 for strict typed input/output. Test dependency httpx2==2.16.0
is also an SDK dependency; it carries the official client's Streamable HTTP
requests through ASGITransport, while the proven Woo transport keeps HTTPX 0.28.1.
No FastAPI or third-party FastMCP package. The SDK brings Starlette, Uvicorn and
other transitive dependencies; their presence does not implement gateway auth.
Tests use standard-library unittest and HTTPX MockTransport.

The lock retains all eight Stage 4.3 versions and pins 33 packages, with pywin32
restricted to Windows. Hashes cover Python 3.13 Windows amd64 and Linux glibc
x86_64 wheels, including compiled SDK dependencies. To reproduce the environment,
install the entire lock with --require-hashes as below. Lock updates must resolve
from the direct pyproject pins while constraining existing versions, pin the full
closure, obtain wheel SHA-256 values from each exact PyPI release, and verify fresh
downloads for both target platforms. Never regenerate it from unrelated global packages.

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

## MCP and list_products

`woo_mcp.server:create_app` is an ASGI factory. It calls MCPServer.streamable_http_app
with /mcp, json_response=True and stateless_http=True; subscriptions are disabled.
The SDK implements all protocol parsing, discovery, output conversion and legacy
compatibility. No JSON-RPC implementation lives here. Default SDK Host/Origin
protection remains enabled for loopback hosting; deployment host allowlists need
explicit configuration at the later Kubernetes stage. No server is started by import.

The SDK lifespan creates one WooClient, reads mounted credentials only at startup,
shares that client across tool calls and closes it on shutdown. Tests inject a client
factory with dummy credentials and mocked HTTP; they exercise the ASGI lifespan too.
No credential loading or network operation is needed to import the factory.

| Input | Contract |
| --- | --- |
| page | Strict integer >=1, default 1; bool/string/float coercion rejected |
| per_page | Strict integer 1-50, default 20 |
| search | Optional trimmed nonblank string, 1-100 chars |
| sku | Optional trimmed nonblank string, 1-64 chars; mutually exclusive with search |
| status | Optional publish/draft/pending/private |
| Extra fields | Rejected; no URL or arbitrary REST parameter |

The pinned SDK's generated argument model normally ignores extra fields and
pre-parses JSON-looking strings. ProductArguments binds the strict input model via
Tool.fn_metadata and publishes its schema via Tool.parameters. It bypasses that
coercion and sanitizes validation errors before the SDK turns them into tool errors.
This small SDK metadata integration is version-coupled and covered by protocol tests;
do not upgrade the SDK without running them. Function return annotations retain SDK
structured-output validation. Unknown fields and rejected values never enter errors.

Output is ProductCollection: items, page, per_page, total, total_pages, has_more,
currency. Product fields are id, name, sku, type, price, regular_price, currency,
status, stock_status and permalink. Currency is the configured store contract (INR),
not inferred from a products response or fetched with another call. Empty decimal
price strings are retained for unpriced drafts; money is never converted to float.
All other upstream fields are discarded. Names/text remain untrusted upstream data.

One bounded GET supplies only approved filters and _fields. X-WP-Total and
X-WP-TotalPages must each occur once, be nonnegative integers and agree with page
size and item count; inconsistent metadata fails safely. Concurrent store changes
can invalidate pagination consistency; this is not a snapshot or an all-pages fetch.
Duplicate product IDs and malformed DTOs fail. The existing 64KiB/deadline/no-retry
transport is shared with the Stage 4.3 single-product diagnostic.

SDK ToolError carries a fixed code: VALIDATION_ERROR, WOO_UNREACHABLE,
WOO_AUTH_FAILED, WOO_FORBIDDEN, WOO_TIMEOUT, NOT_FOUND, WOO_REQUEST_REJECTED,
WOO_UPSTREAM_ERROR, WOO_INVALID_RESPONSE, WOO_CONFIGURATION_ERROR,
WOO_RESPONSE_TOO_LARGE or generic WOO_INTERNAL_ERROR. Failures have is_error=True
and no structured success result. No upstream body/header/request repr is returned.
The factory suppresses signer/HTTP debug levels; hosting must not enable wire logging.

Protocol tests use the official Client and streamable_http_client over an HTTPX2
ASGI transport at http://127.0.0.1:8000/mcp, not handcrafted JSON-RPC. They verify
auto discovery, explicit 2026-07-28 and legacy 2025-11-25, schema, calls, errors,
no Mcp-Session-Id and pooled client lifecycle. No listening TCP socket, real REST
request, Secret access or Kubernetes operation is involved. Network/container
hosting and the other four tools remain unimplemented/unvalidated.

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

# Store Policy MCP

A deterministic internal reference upstream with exactly one tool, `get_policy`.
The committed immutable dataset in `policies.py` is operational demo guidance, not
legal/refund terms. It never fetches orders, updates status or decides fulfillment.

## Contract and dataset

Input: strict object containing only key, one of `cod`, `dispatch`, `cancellation`.
Unknown keys/types, whitespace/case changes and extra fields yield a sanitized MCP
VALIDATION_ERROR. Keys are an enum, never file paths, URLs or executable expressions.
Output contains only key, title and guidance (bounded to 100/500 characters).

| Key | Operational meaning |
| --- | --- |
| cod | Collect payment on delivery; do not treat COD as prepaid |
| dispatch | Review processing orders; hold on-hold orders until an operator reviews/releases them |
| cancellation | Review fulfillment/payment before action; status changes are not refund operations |

No tool changes the dataset or store. Read-only/idempotent annotations describe
behavior; they do not enforce authorization. Dataset edits require a source/image
change and review, rather than remote fetches or runtime files supplied by callers.

## Intended composition

Prompt: **For today's COD orders, what handling policy applies?**

Future chat: `woocommerce__list_orders` -> `store_policy__get_policy(key="cod")`.
The orchestrator resolves today's store date, handles pagination, selects returned
COD orders and asks for the reference. This service receives no customer information
and never retrieves order data. Returned policy text is still upstream content, not
privileged system instructions. No chat agent or gateway registration is added here.

## Hosting and boundaries

Python 3.13, official `mcp==2.3.0`, `pydantic==2.14.1` for strict DTOs and
`uvicorn==0.54.0` for direct SDK ASGI hosting. No FastAPI, database, credential,
store client or outbound business request. The required SDK dependency closure is
hash-locked at reviewed versions (29 Windows packages, 28 Linux packages); libraries
such as HTTPX2 are SDK dependencies, not an outgoing business client. No third-party
FastMCP package or handwritten protocol. The strict argument adapter follows the
pinned SDK pattern and must be regression-tested on SDK upgrades.

`MCP_ALLOWED_HOSTS` is the only application setting: comma-separated exact hosts,
no wildcards or origins. Default loopback forms are 127.0.0.1/localhost, bare and
:8000. Helm derives short Service, namespace-qualified, .svc and .svc.cluster.local
forms, bare and :8000, plus loopback. SDK DNS-rebinding protection stays enabled;
browser Origins are rejected and no permissive CORS is provided.

Docker uses official Python Linux/amd64:
`python:3.13.17-slim-bookworm@sha256:4cea12ab7d78a3312c85f8cab19b6971d4fe9704da25443986c0bc20a6678850`.
Only source and runtime lock are copied; no tests, caches, .git or credential files.
Uvicorn binds 0.0.0.0:8000, one worker, lifespan on, no proxy-header trust/access log.
UID/GID 10001:10001, PYTHONDONTWRITEBYTECODE=1, read-only root, no privilege escalation,
dropped capabilities and RuntimeDefault seccomp work in local Docker acceptance.

Helm adds one replica and internal ClusterIP port 8000, named target port http;
no Ingress/NodePort/LoadBalancer, PVC, Secret or API token. All three probes check the
local TCP listener. Ready means listener availability, not full protocol/business
validation. Starting budgets per app: request 25m CPU / 64Mi memory, limit 250m /
128Mi. They suit a small stateless process but remain hypotheses for sustained load
and full-cluster capacity. Existing WordPress/MariaDB/Woo budgets are unchanged.
Local values use urumi-store-policy-mcp:stage6.1 with Never pull policy for later explicit import; production
uses registry.example.invalid placeholders with IfNotPresent. Replace/pin the reviewed
published image before production. Same templates; no production runtime claim.

No caller credential is required in this slice. Internal ClusterIP/Host validation
is not gateway-only authorization: other cluster Pods could call it. Gateway labels,
caller-boundary controls and targeted NetworkPolicy remain future deployment work.
No Kubernetes operation or gateway registration occurs in Stage 6.1.

## Reproduce validation

From repository root in PowerShell (these commands do not start Kubernetes):

```powershell
py -3.13 -m venv apps/store-policy-mcp/.venv
apps/store-policy-mcp/.venv/Scripts/python -m pip install --require-hashes --only-binary=:all: -r apps/store-policy-mcp/requirements.lock
$env:PYTHONPATH = 'apps/store-policy-mcp/src'
apps/store-policy-mcp/.venv/Scripts/python -m unittest discover -s apps/store-policy-mcp/tests -q
apps/store-policy-mcp/.venv/Scripts/python -m compileall -q apps/store-policy-mcp/src apps/store-policy-mcp/tests
apps/store-policy-mcp/.venv/Scripts/python -m pip check
apps/store-policy-mcp/.venv/Scripts/python tests/upstreams/smoke.py store-policy-mcp
docker build --platform linux/amd64 -t urumi-store-policy-mcp:stage6.1 apps/store-policy-mcp
apps/store-policy-mcp/.venv/Scripts/python tests/upstreams/smoke.py store-policy-mcp --image urumi-store-policy-mcp:stage6.1
```

The shared [smoke runner](../../tests/upstreams/smoke.py) uses official clients over
real TCP, checks the one-tool catalog/schema and a synthetic structured call, rejects
bad Host/Origin, then gracefully closes and removes the temporary process/container.
Docker mode verifies effective UID/GID, read-only enforcement, capabilities, seccomp,
no-new-privileges, pip consistency and no OOM. It mounts no credentials or other files.
The synthetic call changes no state and contacts no store. Test-harness subprocess/file
operations are outside the application tool implementation.

Helm checks use [validate_chart.py](../../tests/upstreams/validate_chart.py) with a
local copy of the official Kubernetes v1.35.5 OpenAPI swagger.json. Existing workstation
PyYAML 6.0.2/jsonschema 4.25.0 perform duplicate-key/schema checks; they are not runtime
image dependencies. IntOrString is adapted and unknown structured fields rejected.
This is static validation, not API admission or Pod scheduling. Both local/prod render
14 objects; defaults leave auxiliaries/Woo disabled and render 8 store objects.

Evidence: 15 application/protocol tests pass, covering current 2026-07-28 and
legacy clients. Listening TCP and Docker discovery/call/security/shutdown pass.
Image urumi-store-policy-mcp:stage6.1 is 223699516 bytes (approximately 213.34 MiB), uncompressed Docker-reported size;
shared layers mean the sum of image sizes is not incremental disk use.
Kubernetes deployment, actual gateway registration/three-upstream composition,
production TLS and final chat/external-client demonstrations remain untested.

# Arithmetic MCP

A deterministic internal upstream with exactly one tool, `sum_amounts`.
It aggregates caller-provided values and never fetches WooCommerce data.

## Contract

Input is a strict object with unknown fields rejected:

- amounts: required array, 1–100 decimal strings, each at most 18 integer and 6
  fractional digits. Optional minus sign supports negative adjustments. No whitespace,
  leading plus/leading zero padding, exponent syntax, NaN, infinity, numbers/booleans,
  expressions or arbitrary URLs. Zero and integer-like strings are valid.
- currency: optional three uppercase ASCII letters. It is a caller-provided label,
  not exchange conversion or proof of a valid ISO currency or homogeneous inputs.

Output fields: count, total, average, minimum, maximum and currency (null if omitted).
Values use Python Decimal with a local precision of 40, enough for exact bounded sums.
Total/min/max are exact; average is rounded to six fractional places using ROUND_HALF_EVEN.
Strings have no exponent or unnecessary trailing zeros; negative zero normalizes to 0.
For ["499", "599"] / INR: count=2, total="1098", average="549", min="499", max="599".
All tool annotations are read-only/idempotent and are descriptive, not authorization.

## Intended composition

Prompt: **What orders came in today, and what is their total and average order value?**

Future chat: `woocommerce__list_orders` -> `arithmetic__sum_amounts`.
The orchestrator resolves the store date once, follows bounded pagination explicitly,
uses one currency, and passes only order totals. A page alone is not a whole-day total.
For zero orders it reports no orders/undefined average without calling the nonempty
aggregator. More than 100 totals requires a separately tested batching/weighted-average
strategy or an explicit limited-scope answer; do not average batch averages blindly.
This is the sum of selected order totals, not a cash-received/revenue-accounting claim;
COD, cancellations/refunds/status selection must be explained. No refund logic here.
The final multi-server prompt and chat loop are not implemented by this app.

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
Local values use urumi-arithmetic-mcp:stage6.1 with Never pull policy for later explicit import; production
uses registry.example.invalid placeholders with IfNotPresent. Replace/pin the reviewed
published image before production. Same templates; no production runtime claim.

No caller credential is required in this slice. Internal ClusterIP/Host validation
is not gateway-only authorization: other cluster Pods could call it. Gateway labels,
caller-boundary controls and targeted NetworkPolicy remain future deployment work.
No Kubernetes operation or gateway registration occurs in Stage 6.1.

## Reproduce validation

From repository root in PowerShell (these commands do not start Kubernetes):

```powershell
py -3.13 -m venv apps/arithmetic-mcp/.venv
apps/arithmetic-mcp/.venv/Scripts/python -m pip install --require-hashes --only-binary=:all: -r apps/arithmetic-mcp/requirements.lock
$env:PYTHONPATH = 'apps/arithmetic-mcp/src'
apps/arithmetic-mcp/.venv/Scripts/python -m unittest discover -s apps/arithmetic-mcp/tests -q
apps/arithmetic-mcp/.venv/Scripts/python -m compileall -q apps/arithmetic-mcp/src apps/arithmetic-mcp/tests
apps/arithmetic-mcp/.venv/Scripts/python -m pip check
apps/arithmetic-mcp/.venv/Scripts/python tests/upstreams/smoke.py arithmetic-mcp
docker build --platform linux/amd64 -t urumi-arithmetic-mcp:stage6.1 apps/arithmetic-mcp
apps/arithmetic-mcp/.venv/Scripts/python tests/upstreams/smoke.py arithmetic-mcp --image urumi-arithmetic-mcp:stage6.1
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

Evidence: 21 application/protocol tests pass, covering current 2026-07-28 and
legacy clients. Listening TCP and Docker discovery/call/security/shutdown pass.
Image urumi-arithmetic-mcp:stage6.1 is 223695465 bytes (approximately 213.33 MiB), uncompressed Docker-reported size;
shared layers mean the sum of image sizes is not incremental disk use.
Kubernetes deployment, actual gateway registration/three-upstream composition,
production TLS and final chat/external-client demonstrations remain untested.

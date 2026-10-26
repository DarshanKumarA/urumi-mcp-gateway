# WooCommerce MCP: five product and order tools

## Stage 8.0 gateway caller boundary

Image urumi-woo-mcp:stage8.0 supersedes stage4.8 for integrated hosting. Business tools,
REST transport and OAuth stay unchanged. ASGI factory requires WOO_MCP_AUTH_TOKEN_FILE
(chart: /run/secrets/woo-mcp-auth/token), external urumi-woo-mcp-auth/token. Provision
at least 256 random bits as base64url. Every HTTP request requires one matching Bearer
header; missing/invalid/duplicate values return safe 401. Constant-time compare;
header stripped before SDK; no token output. TCP probes, Host and Origin protections stay.

Token loads once per process. Gateway bootstrap stores the matching value in its
existing static-credential model; rotation requires coordinated review. Woo REST
files remain separate and only Woo consumes them. NetworkPolicy permits gateway-labelled
Pods only; actual enforcement is Stage 8.1 work. Existing smoke uses synthetic caller
auth. All prior 116 plus four auth tests pass (120), including authenticated current/
legacy discovery and invalid headers. No live Woo business request occurred.

All five required business contracts exist with offline tests. Stage 4.8 adds real
TCP hosting, a Docker image and rendered internal Helm workload definitions without
changing those contracts. Stage 4.3's credential loading/OAuth transport remain.
Kubernetes installation, full live tool acceptance and gateway caller enforcement
remain incomplete. Hosting acceptance uses synthetic files and discovery only;
business tests use mocked REST. Do not repeat the live diagnostic merely to test MCP.

## Dependencies and offline checks

Use Python 3.13. Direct pins are [HTTPX 0.28.1](https://pypi.org/project/httpx/0.28.1/)
(async HTTP, connection pooling, timeouts, mock transport) and
[OAuthLib 4.0.0](https://pypi.org/project/oauthlib/4.0.0/) (OAuth 1.0a signing,
including HMAC-SHA256). OAuthLib is transport-independent; signing the canonical
URL before handing headers to HTTPX makes the two origins explicit. No manual
cryptography or additional OAuth integration framework is needed. HTTPX's stable
0.28.1 release is used rather than a 1.0 development release. The hash-locked
wheels in requirements.lock include all resolved runtime dependencies.
Stage 4.4 added [MCP 2.3.0](https://pypi.org/project/mcp/2.3.0/) and
Pydantic 2.14.1 for strict typed input/output. Test dependency httpx2==2.16.0
is also an SDK dependency; it carries the official client's Streamable HTTP
requests through ASGITransport, while the proven Woo transport keeps HTTPX 0.28.1.
Stage 4.8 promotes [Uvicorn 0.54.0](https://pypi.org/project/uvicorn/0.54.0/) from
the existing lock to an explicit runtime dependency; no locked version/hash changes.
No FastAPI or third-party FastMCP package. SDK dependencies include Starlette and
httpx2; their presence does not implement gateway auth.
Tests use standard-library unittest and HTTPX MockTransport.

The lock retains all eight Stage 4.3 versions and pins 34 packages, with pywin32
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

## Process container and Helm hosting

Uvicorn calls the existing `woo_mcp.server:create_app` factory directly, with one
worker, `--lifespan on`, no access logging and no proxy-header trust. It serves
the SDK-generated Streamable HTTP application at `/mcp`; no wrapper or FastAPI
application replaces the SDK session-manager/lifespan startup. Missing credential
files fail startup. The same lifespan owns one pooled Woo client and closes it
on graceful shutdown. Discovery does not contact WooCommerce.

`Config.from_environment()` maps these non-secret settings onto existing fields:

| Environment name | Local Helm value / behavior |
| --- | --- |
| WOO_CONNECTION_ORIGIN | http://urumi-wordpress.urumi.svc.cluster.local |
| WOO_CANONICAL_ORIGIN | http://store.urumi.test:8080; its authority supplies the outgoing Woo Host header |
| WOO_SECRET_DIRECTORY | /run/secrets/woocommerce-rest |
| WOO_DEADLINE_SECONDS | 8; positive and at most 8 |
| WOO_CURRENCY | INR |
| WOO_STORE_TIMEZONE | Asia/Kolkata |
| WOO_MCP_ALLOWED_HOSTS | Comma-separated exact incoming Host values, no wildcard/URL/whitespace |

REST prefix remains `/wp-json/wc/v3`; redirects and automatic retries remain
disabled in the existing client. Incoming MCP Host validation and outgoing Woo
Host/signing configuration are separate boundaries. Invalid environment values
fail with a fixed error that does not interpolate their contents.

For release/namespace `urumi`, Helm generates these accepted incoming hosts, each
both bare and with `:8000`: `urumi-woo-mcp`, `urumi-woo-mcp.urumi`,
`urumi-woo-mcp.urumi.svc`, `urumi-woo-mcp.urumi.svc.cluster.local`,
`127.0.0.1`, `localhost`. There are 12 exact forms. Loopback supports future
operator forwarding; a different forwarded port must be explicitly configured.
The standalone default accepts only the four loopback forms. SDK DNS-rebinding
protection remains on, `allowed_origins=[]`, and no CORS middleware is added.
Clients without Origin are accepted; browser Origin requests are rejected.
Host checks are not caller authentication or network isolation.

The [Dockerfile](Dockerfile) pins official
`python:3.13.17-slim-bookworm@sha256:4cea12ab7d78a3312c85f8cab19b6971d4fe9704da25443986c0bc20a6678850`
(Linux/amd64 manifest). It installs the hash-locked runtime closure with binary
wheels, without pip cache/bytecode, then copies only application modules. The
deny-by-default [.dockerignore](.dockerignore) excludes tests, connectivity CLI,
caches, `.git` and unrelated files. httpx2 remains in the image because MCP itself
requires it; no test extra is installed. `PYTHONDONTWRITEBYTECODE=1` avoids writes.
The runtime user/group is fixed `10001:10001`, with no home or login shell.
The container command binds `0.0.0.0:8000` and allows 15 seconds for shutdown.

Explicit Docker acceptance, from the repository root with Docker available and
k3d stopped (synthetic files only, no business tool call):

```powershell
docker build --platform linux/amd64 -t urumi-woo-mcp:stage4.8 apps/woo-mcp
$env:PYTHONPATH = (Join-Path $PWD 'apps/woo-mcp/src')
apps/woo-mcp/.venv/Scripts/python apps/woo-mcp/tests/smoke_docker.py urumi-woo-mcp:stage4.8
```

The smoke uses temporary files outside Git, a loopback-only published port,
read-only root/mount, all capabilities dropped, no-new-privileges, default seccomp
and a 256Mi memory limit. It calls only official-client discovery, inspects UID/GID,
rejects a filesystem write, checks shutdown/logs and removes its container/files.
It never uses the real REST Secret. Ordinary unittest discovery also starts a real
localhost Uvicorn child process, verifies five schemas, rejects an invalid Host
(421) and browser Origin (403), observes zero requests at a synthetic Woo trap,
and verifies graceful shutdown. These tests supplement the existing current/legacy
in-process protocol calls; they do not prove live business-tool behavior.

The same [Helm chart](../../charts/urumi/Chart.yaml) adds a one-replica
`urumi-woo-mcp` Deployment and ClusterIP Service, port 8000 to named `http`.
Future endpoint: `http://urumi-woo-mcp.urumi.svc.cluster.local:8000/mcp`.
There is no Woo MCP Ingress, public Service, PVC or generated Secret.
The externally managed `urumi-woocommerce-rest` projects exactly `consumer-key`
and `consumer-secret` under `/run/secrets/woocommerce-rest/`, read-only mode 0440.
Pod fsGroup/runAsGroup 10001 supplies group access; actual Kubernetes projection
permissions remain a Stage 4.9 acceptance check. No store database/admin/salt Secret
is mounted. Service-account token automount is false. Pod seccomp is RuntimeDefault;
container root is read-only, privilege escalation false, capabilities drop ALL.
Linux/amd64 node selectors match the pinned image architecture.

| Probe | Target | Period / timeout / failure threshold | Meaning |
| --- | --- | --- | --- |
| Startup | TCP named http (8000) | 2s / 1s / 30 | Approximately 60s listener-start budget |
| Liveness | TCP named http | 20s / 2s / 3 | Local listener availability only |
| Readiness | TCP named http | 5s / 1s / 3 | MCP listener can accept TCP connections |

`Ready` does not prove Woo reachability, an authenticated REST call or complete MCP
responsiveness. A TCP probe is deliberately weaker than a protocol/tool check.
Woo failures stay tool errors while MCP remains discoverable. Requests 50m/128Mi
and limits 500m/256Mi are starting hypotheses; Docker discovery under that limit is
not tool-load sizing or full-stack capacity evidence. Default Deployment rolling
updates can temporarily need a second Pod; assess capacity before later upgrades.

Base values disable Woo MCP; local and production overlays enable the same two
templates. Local uses `urumi-woo-mcp:stage4.8`, pull policy Never, requiring a later
explicit k3d image import. Production uses the unpushed placeholder
`registry.example.invalid/urumi/woo-mcp:stage4.8`, IfNotPresent. Production connection
DNS derives from release/namespace; signing origin is `http://store.example.invalid`
for the internal HTTP hop, even though the public store URL uses HTTPS. Pinned
[Woo authentication](https://raw.githubusercontent.com/woocommerce/woocommerce/11.2.1/plugins/woocommerce/includes/class-wc-rest-authentication.php)
selects the signing scheme from the request's TLS state. This preserves HTTP OAuth,
not Basic over HTTP; deployment-specific proxy/redirect/signing behavior still needs
VPS proof. Public TLS alone does not encrypt the internal hop. No production image,
credential or deployment is claimed validated.

Stage 4.8 evidence: 116 tests pass (110 previous plus six hosting tests); real TCP
and Linux Docker discovery each return exactly five tools with zero business calls.
Fresh image dependency installation/pip check succeeds. Image size is 229,000,063
bytes (approximately 218.4 MiB); runtime UID/GID, read-only filesystem, zero effective
capabilities, no-new-privileges, seccomp and exit-0 shutdown pass. Initial image
inspection caught copied bytecode caches; the ignore rules were corrected and the
rebuilt image passed. Both overlays lint/render ten resources (previous eight plus
two), pass Kubernetes v1.35.5 schemas and static boundaries; existing eight store
objects are unchanged at the same render revision. Disabling Woo MCP renders eight.

No chart was installed. The existing k3d containers were unexpectedly running at
preflight and were controlled-stopped with `k3d cluster stop urumi-local`; they were
not restarted or recreated. Temporary smoke resources were removed; the local
image remains. No real Secret access or live Woo call/mutation occurred.
Gateway-only enforcement still requires `urumi-woo-mcp-auth`, caller checks and
targeted NetworkPolicy during gateway integration. ClusterIP is not that enforcement.
Before a future Helm upgrade, preview all release changes: revision-specific store
assets/bootstrap Job and WordPress replacement can accompany this new workload.
Observe the established no-concurrent-bootstrap-writers rule; do not treat the
upgrade as creating only two objects or automatically roll back persisted state.

## MCP and list_products

`woo_mcp.server:create_app` is an ASGI factory. It calls MCPServer.streamable_http_app
with /mcp, json_response=True and stateless_http=True; subscriptions are disabled.
The SDK implements all protocol parsing, discovery, output conversion and legacy
compatibility. No JSON-RPC implementation lives here. SDK Host/Origin protection
remains enabled with explicit allowed hosts and no allowed browser Origins.
No server is started by import; the hosting configuration is described above.

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
pre-parses JSON-looking strings. StrictArguments binds each strict input model via
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
no Mcp-Session-Id and pooled client lifecycle. Those protocol tests remain in-process
with mocked REST. Stage 4.8 separately adds listening-TCP and Docker discovery
acceptance; neither makes a Woo request or uses a real Secret.

## Order tools and store dates

The three read tools available after Stage 4.5 remain read-only: list_products,
get_order and list_orders.
The same lifespan client, OAuth signer, strict SDK argument adapter, 8-second REST
deadline, 64KiB response bound, redirect rejection and zero-retry policy apply.
The pagination validator is shared with list_products; no all-pages fetch.

| Tool | Inputs | REST mapping | Structured result |
| --- | --- | --- | --- |
| get_order | Required strict positive integer order_id; no extras | GET /wp-json/wc/v3/orders/{order_id} | OrderDetail |
| list_orders | page >=1/default 1; per_page 1-50/default 20; optional status and date; strict types/no extras | GET /wp-json/wc/v3/orders | items, page, per_page, total, total_pages, has_more, date_window |

Order status accepts pending, processing, on-hold, completed, cancelled, refunded,
failed. Date accepts only today or a valid YYYY-MM-DD. Omitted date sends no date
filter and returns date_window=null. No arbitrary URL/parameter passthrough.
OrderSummary contains id/status/created_at/currency/total/payment_method.
OrderDetail adds line_items/shipping_lines/shipping_total/tax_total.
Line items allow only product_id/variation_id/name/sku/quantity/unit_price/subtotal/total;
shipping lines only method_id/method_title/total. Zero variation_id becomes null;
Woo's null SKU for a deleted product is retained, and product_id=0 is allowed.

Money is a decimal string. Woo line price is the net line total divided by quantity,
not the original undiscounted catalog price. JSON decimal numbers are parsed with
Decimal before normalization, with bounded price formatting; subtotal/total remain
Woo strings. created_at uses date_created_gmt as an aware UTC timestamp. Order
currency comes from that order; product currency remains configured INR.

The Config store_timezone defaults to Asia/Kolkata. Python zoneinfo required an
additional hash-pinned tzdata==2026.5 dependency on Windows, where no IANA database
was available. Existing pins remain unchanged. No Windows/caller timezone or naive
UTC date is used. today reads the UTC clock exactly once before the REST request,
then converts to store-local date. Explicit dates do not read the clock.

The returned date_window contains date, timezone, start_inclusive and end_exclusive
as offset-bearing UTC timestamps. For 2026-10-23 the intended window is
[2026-10-22T18:30:00Z, 2026-10-23T18:30:00Z). Requests set dates_are_gmt=true,
after=2026-10-22T18:29:59Z and before=2026-10-23T18:30:00Z. This implements the
accepted strict second-resolution boundary mapping, including start midnight and
excluding next midnight. Use the returned explicit date on later pages, not today
again after midnight. Returned rows outside the intended window fail validation;
records are not silently filtered away, which would misrepresent pagination.

Source review: [pinned Woo REST date query](https://raw.githubusercontent.com/woocommerce/woocommerce/11.2.1/plugins/woocommerce/includes/rest-api/Controllers/Version3/class-wc-rest-crud-controller.php)
selects GMT columns without an inclusive override;
[HPOS query implementation](https://raw.githubusercontent.com/woocommerce/woocommerce/11.2.1/plugins/woocommerce/src/Internal/DataStores/Orders/OrdersTableQuery.php)
maps the columns and uses [WP_Date_Query](https://developer.wordpress.org/reference/classes/wp_date_query/).
Fixtures model those strict comparisons. Actual active-store boundary behavior is
still a later runtime acceptance obligation, not proved by a mocked response.

REST _fields minimizes requested fields; independent nested allowlists discard
billing, addresses, names/contact fields, customer ID, notes, order key and metadata.
Tests include explicitly synthetic customer-shaped payloads and verify absence from
both MCP structured/text results and errors. This is field minimization, not a
redactor for personal text maliciously embedded in an allowed product/method name.
Allowed strings remain untrusted content. No real customer or credential data is used.

The existing fixed tool-error codes apply, including NOT_FOUND for 404. Invalid
calendar dates/unrepresentable UTC bounds fail with VALIDATION_ERROR; invalid
upstream rows/date windows/pagination fail with WOO_INVALID_RESPONSE. No raw bodies,
headers or exception representations are forwarded. Unknown custom order statuses
and fractional quantities are outside this initial contract and fail validation.

Offline evidence: 59 tests pass, including all 31 prior tests (discovery updated to
three tools), current/legacy official-client order calls, timezone/midnight/boundary
fixtures, decimal precision, nested privacy and failures. Protocol tests remain
in-process ASGI with mocked REST, not listening TCP or live order acceptance.
Kubernetes hosting and gateway caller authentication remain incomplete.

## Product creation and uncertain writes

The fourth tool is create_product. The other three tools retain read-only hints;
create_product has read_only_hint=false, idempotent_hint=false and a conservative
destructive_hint=true. These hints describe behavior, not authorization enforcement.
The existing SDK strict argument adapter, lifecycle and pooled WooClient are reused.
No dependency change, second HTTP client or business framework was added.

| Input | Contract |
| --- | --- |
| name | Required strict string, trimmed, 1-200 characters |
| price | Required nonnegative decimal string, at most two fractional digits, maximum 999999999.99; no float/coercion/exponent notation |
| sku | Optional trimmed string, 1-64 characters; omitted/null sends no SKU |
| status | publish (default) or draft |
| stock_status | instock (default) or outofstock |
| Extra fields | Rejected, including description, metadata, images, variations, URLs and REST parameters |

The POST path is /wp-json/wc/v3/products. JSON contains only name, type=simple,
regular_price (mapped from price), status, stock_status and sku when supplied.
No optional null/empty field is emitted. Leading zeros in valid price strings are
accepted; validation/comparison uses Decimal and serialization retains the string.

If supplied, SKU first uses one existing list_products request with page=1,
per_page=1, no status filter. A match produces DUPLICATE_SKU with zero POSTs.
Lookup failure stops too. This precheck is advisory and races other creators;
WooCommerce create-time uniqueness remains authoritative. No SKU means no precheck
and weaker later reconciliation. There is no update-existing or idempotent-success path.

Pinned Woo 11.2.1 emits product_invalid_sku for SKU conflict; only that exact code in
a bounded 400/409 response maps to DUPLICATE_SKU. No localized message matching or
raw error forwarding. Sources: [product setter](https://raw.githubusercontent.com/woocommerce/woocommerce/11.2.1/plugins/woocommerce/includes/abstracts/abstract-wc-product.php),
[creation controller](https://raw.githubusercontent.com/woocommerce/woocommerce/11.2.1/plugins/woocommerce/includes/rest-api/Controllers/Version3/class-wc-rest-crud-controller.php).
A concurrent data-store failure can instead appear as generic 5xx: it stays unknown,
not guessed to be a duplicate. Successful creation requires HTTP 201 and a valid
allowlisted Product, including matching simple type, regular price, status, stock
status and supplied SKU. Return {product: Product, created: true}; no raw JSON.

The shared request helper now handles GET and POST, retaining OAuthLib HMAC-SHA256,
canonical signing origin, Service-DNS destination, Host, disabled redirects and
HTTP retries=0. JSON is sent as application/json, not form parameters in the OAuth
signature. This preserves the accepted HTTP OAuth design; it does not provide TLS
confidentiality or JSON-body integrity. The signer receives the actual POST method.
Each REST request retains its 8-second deadline/64KiB bound. At most one precheck
and one POST occur; there are no automatic post-failure reconciliation requests.

| Failure point | MCP result / write semantics |
| --- | --- |
| Input or SKU precheck failure | Safe existing error; no POST attempted |
| Matching SKU or recognized create-time SKU conflict | DUPLICATE_SKU; not success/update |
| HTTP 401/403/404 or other rejected 4xx | Existing auth/forbidden/not-found/request-rejected code; no retry or blanket claim that hooks had no side effects |
| POST timeout/network failure, 408 or 5xx | Existing code plus write_outcome=unknown; retry_safe=false |
| POST redirect, unexpected 2xx, oversized/malformed response or invalid Product | Existing code plus write_outcome=unknown; retry_safe=false |
| Unexpected transport exception after attempt begins | WOO_INTERNAL_ERROR plus unknown/unsafe-to-retry semantics |

These are SDK tool errors (is_error=true), with no structured success result. Only
fixed codes and fixed outcome labels are exposed, never body/header/request/exception
representations. Connection failures are conservatively unknown once sending is
attempted, even if no bytes ultimately reached the store. Cancellation propagates
without replay; a cancelled caller may receive no result and must assume an unknown
outcome. Unknown never means non-creation or rollback. If SKU was supplied, a later
separately requested lookup can inform an operator's decision; do not blindly retry.
The tool does not implement durable idempotency or stop a caller explicitly invoking
it twice. That is distinct from its own no-automatic-retry guarantee.

Stage 4.6 offline evidence: 83 tests pass, including all previous 59, 21 create tests
and 3 added official-client protocol tests. Tests count zero/one POST attempts,
exercise a simulated committed write with lost response, and verify no follow-up
read/retry. Current and legacy clients discover exactly four tools, validate schemas,
return normalized success and receive sanitized duplicate/validation/unknown errors.
No live write has occurred; runtime proof waits for deployment and separate approval.

## Guarded order status updates

update_order_status is the fifth business tool. The three read tools remain
read-only; both write tools have read_only_hint=false, idempotent_hint=false and
destructive_hint=true. Hints describe behavior, not authorization enforcement.

| Required input | Contract |
| --- | --- |
| order_id | Strict positive integer; no bool/string/float coercion |
| status | pending, processing, on-hold, completed, cancelled or failed |
| expected_status | Previously observed status; the six targets above plus refunded |
| Extra fields | Rejected; no arbitrary properties, metadata, URLs or refund operation |

One GET /wp-json/wc/v3/orders/{order_id}?_fields=id%2Cstatus precedes any write.
Only identity and status are normalized, regardless of extra upstream fields.
Malformed/mismatched identity or unknown status fails before PUT. Missing order
is NOT_FOUND. If the observed status differs from expected_status, STATE_CONFLICT
includes only the validated expected/observed status enums; zero PUTs occur.
This guard runs before checking for a no-op: stale expectations do not become success
just because the current status already equals the requested target.

If expected/current/target agree, return order_id, observed_before_status,
after_status and changed=false, with no PUT. Otherwise send exactly one
PUT /wp-json/wc/v3/orders/{order_id} with only {"status":"<requested-status>"}.
HTTP 200 must contain the same strict order ID and requested status. The normalized
result has the same four fields and changed=true. This reports the response at
that moment, not a guarantee another process cannot subsequently change the order.
No full order, customer fields, raw response, headers or request representation is returned.

The transport reuses OAuthLib with the actual PUT method, pooled HTTPX, canonical
signing origin, Service-DNS connection/Host, disabled redirects/retries, 8-second
per-request deadline and 64KiB decoded response bound. At most one GET and one PUT;
no automatic reconciliation read, second PUT, rollback or custom transition matrix.
Two sequential REST requests can consume up to two REST deadlines.

| Failure phase | Result |
| --- | --- |
| Initial GET or normalization | Existing read errors; no mutation attempted, no unknown-write label |
| Expected-status mismatch | STATE_CONFLICT with safe expected/observed statuses; zero PUTs |
| Explicit status-enum rejection | INVALID_TRANSITION for the narrow structured evidence below |
| Other clear 4xx rejection | Existing auth/forbidden/not-found/request-rejected code; no raw message |
| Attempted PUT timeout/network/408/5xx/redirect | Existing safe code plus write_outcome=unknown; retry_safe=false |
| PUT unusable/malformed/oversized success, wrong ID/status or unexpected 2xx | Safe error plus unknown/unsafe-to-retry semantics |

Recognized INVALID_TRANSITION evidence is HTTP 400, code=rest_invalid_param,
data.status=400, data.params naming only status, and
data.details.status.code=rest_not_in_enum. It means the upstream rejected the target
status parameter, not that we have inferred a fulfillment workflow. Woo's standard
enum normally admits all six tool targets; altered upstream validation may reject
one. Generic/plugin errors remain WOO_REQUEST_REJECTED unless separately reviewed
structured evidence supports a narrower mapping. No message matching or invented
universal Woo transition code. Malformed/oversized rejection bodies are conservative
unknown writes. A clear rejection does not imply every possible plugin hook had no
side effect. Sources: [Woo v3 order update](https://developer.woocommerce.com/docs/apis/rest-api/v3/orders/),
[Woo 11.2.1 status schema](https://raw.githubusercontent.com/woocommerce/woocommerce/11.2.1/plugins/woocommerce/includes/rest-api/Controllers/Version2/class-wc-rest-orders-v2-controller.php),
[WordPress 7.1.3 validation envelope](https://raw.githubusercontent.com/WordPress/WordPress/7.1.3/wp-includes/rest-api/class-wp-rest-request.php)
and [enum error code](https://raw.githubusercontent.com/WordPress/WordPress/7.1.3/wp-includes/rest-api.php).

The expected-status guard is NOT atomic compare-and-swap. Another administrator or
process can change the order between GET and PUT. No locks, direct SQL or custom
Woo plugin is introduced. WooCommerce remains authoritative and normal status
changes can trigger hooks, notifications, fulfillment or stock-related behavior.
The tool sets only the status field; it does not control those downstream effects.
refunded is readable for the guard but never a target: changing a label is not a
refund. Trash, checkout drafts and custom target statuses are also excluded.

Unknown outcome never means the order stayed unchanged. Do not retry blindly;
later separately requested inspection is an operator decision, not an automatic
step here. Cancellation propagates without replay and may leave no tool response.
The non-idempotent annotation remains conservative even though same-state calls
can no-op. No live order mutation occurred, including order 12.

Stage 4.7 evidence: 110 tests pass (previous 83 plus 24 focused update tests and
3 official-client protocol tests). Mocks explicitly count GET/PUT attempts, simulate
an intervening administrator write and a committed PUT with lost response, and
prove customer-shaped fields and dummy credentials do not escape in results/errors.
Auto/current 2026-07-28/legacy 2025-11-25 client coverage is green. Protocol evidence
remains in-process ASGI with mocked REST; no listening TCP, live order transition,
Linux execution, container/Kubernetes hosting or gateway authentication is proved.
No dependency changes. The SDK 2.3.0 adapter coupling, configured INR and earlier
runtime date-boundary limitations remain.

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

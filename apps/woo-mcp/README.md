# WooCommerce MCP: three reads and product creation

Stage 4.6 adds create_product alongside list_products, get_order and list_orders.
Stage 4.3's credential loading, OAuth transport and acceptance command remain.
update_order_status, Dockerfile and Helm workloads remain absent.
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
Stage 4.4 added [MCP 2.3.0](https://pypi.org/project/mcp/2.3.0/) and
Pydantic 2.14.1 for strict typed input/output. Test dependency httpx2==2.16.0
is also an SDK dependency; it carries the official client's Streamable HTTP
requests through ASGITransport, while the proven Woo transport keeps HTTPX 0.28.1.
No FastAPI or third-party FastMCP package. The SDK brings Starlette, Uvicorn and
other transitive dependencies; their presence does not implement gateway auth.
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
no Mcp-Session-Id and pooled client lifecycle. No listening TCP socket, real REST
request, Secret access or Kubernetes operation is involved. Network/container
hosting and update_order_status remain unimplemented/unvalidated.

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

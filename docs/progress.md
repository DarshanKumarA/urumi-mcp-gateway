# Project progress

## Current milestone

**2026-10-25 - Stage 5.4 authenticated MCP and attributed audit implemented for review.** Stage 5.3 is committed as a3816e0. Every external MCP HTTP request now verifies its gateway key; request-local identity enters one shared audited invocation service. Explicit 0003_audit commits START before upstream dispatch and retains interrupted/unknown records. Admin-only audit listing is implemented. 160 tests, including all prior 130, and real PostgreSQL migration/history smoke pass. Woo/Helm unchanged, k3d stopped; no staging/commit or public deployment.

**2026-10-25 - Stage 5.3 identity and protected REST implemented for review.** Stage 5.2 is committed as 05509a7. Explicit 0002_identity adds users and hash-only sessions/invitations/API keys; Argon2id, deliberate bootstrap and same-origin admin/member guards protect REST. 130 tests and real PostgreSQL smoke pass. External /mcp authentication and audit remain Stage 5.4; no public deployment. Woo/Helm unchanged, k3d stopped, nothing staged/committed.

**2026-10-25 - Stage 5.2 persistent registry and management API implemented for review.** Stage 5.1 was committed as 8245873. PostgreSQL repository, explicit migration, insert-only Woo seed and safe FastAPI REST DTOs now share the existing gateway core. 80 offline tests and a separate real PostgreSQL smoke pass. Identity/roles/audit and public deployment remain incomplete. Woo/Helm are unchanged; k3d stayed stopped. Nothing staged or committed.

**2026-10-25 - Stage 5.1 gateway protocol core implemented for offline review.** Woo MCP runtime checkpoint fef1b8c remains frozen. A separate apps/gateway package provides SDK Streamable HTTP discovery/routing, immutable registration namespaces, bounded upstream clients, isolated failure/health and synthetic static credentials. PostgreSQL remains the selected future store; only an in-memory repository exists. There is no user authentication, audit persistence, management REST, chat or gateway deployment. Existing k3d containers remain stopped. No staging or commit.

**2026-10-24 - Stage 4.9B PASS: controlled live writes complete Woo MCP business/runtime acceptance.** Stage 4.9A was approved and committed as 88e5cae. One create_product invocation created product 16 / URUMI-MCP-LIVE-20261024-01 / 599 INR. One guarded update_order_status invocation deliberately changed order 12 from processing to on-hold; its other operational fields stayed unchanged. Independent access-log counts confirm exactly one POST and one PUT, with zero automatic retries. The product and on-hold order are retained. Release remains revision 4/deployed; all workloads Ready, original storage unchanged, final available RAM 3.954 GiB. The temporary client is removed. All five tool contracts now have local live acceptance; gateway-only caller authentication/NetworkPolicy and the wider assignment remain incomplete. Nothing staged or committed.

**2026-10-21 — Stage 3.8 PASS: controlled Pod replacement, retained storage and database-dependency loss validated.** Stage 3.7 was approved and committed as af7bb37. Separate WordPress and MariaDB Pod deletions recovered in approximately 7.8s and 7.9s. A retention-checked MariaDB scale-down made WordPress NotReady while its TCP listener and container stayed healthy; restoring one database replica recovered both workloads in approximately 9s. Product 11, Processing order 12, marker 3, WooCommerce 11.2.1, selected webroot files and both claim/PV bindings persisted. Release urumi remains revision 3/deployed; no bootstrap rerun, extra order, OOMKilled or MemoryPressure was observed. Final application Pods have zero restarts. Node-loss protection, backup/restore, production behavior and full-stack capacity are not established by these tests.

**2026-10-22 — Existing environment recovered; local Stage 3 store foundation COMPLETE.** The initial read-only review found Kubernetes API EOF errors and empty store replies. Subsequent authorized diagnosis found K3s shutting down during networking initialization; one controlled k3d stop/start restored the existing cluster. Release revision 3, system/workload readiness, original storage bindings, product 11/order 12, marker 3 and anonymous storefront content are freshly verified. No Stage 3.8 experiment was repeated. Available host RAM is now 3.016 GiB: this recovery does not authorize adding workloads or establish full-stack capacity. The initial gap remains recorded in the [review](#stage-38-final-review-and-local-stage-3-assessment), followed by the [recovery evidence](#stage-38-recovery-of-the-existing-local-environment).

Stage 0 governance was committed as **51f27b2 — docs: establish project governance and assignment baseline** on main. Architecture v1 and its journey were committed as **db49836 — docs: define architecture v1 and project journey**. The reviewed preflight/k3d documentation was committed as **1f2aec9 — docs: select k3d after environment preflight**. Stage 2.2A was reviewed, approved, and committed as **84395d5 — docs: record validated Docker runtime**. Stage 2.2B was reviewed, approved, and committed as **248f13c — docs: record Kubernetes CLI toolchain**. Stage 2.3 was approved and committed as **78d3915 — docs: record validated local Kubernetes cluster**. The approved lab manifests were committed as **de2e69d — labs: add Kubernetes fundamentals workload** before Stage 2.4A began from a clean working tree.

A1–A13 remain accepted as DEC-004 through DEC-016. DEC-017 replaces the proposed local Minikube/Docker driver with k3d and Docker Desktop as the intended runtime. The assignment still permits Kind, k3d, or Minikube; its requirements have not changed.

Stage 2.4A's healthy workload observations were approved and committed as **fc1c38c — docs: record Kubernetes workload baseline**. Stage 2.4B was approved and committed as **89d9084 — docs: record Kubernetes self-healing experiment**. Stage 2.4C was approved and committed as **341d83a — docs: record Kubernetes declarative reconciliation experiment**. Stage 2.4D began from that clean documentation checkpoint.

During the completed local acceptance run, the committed store chart operated with finite bootstrap, external Secret references, persistent claims and dependency-aware readiness. Product 11 was published, in stock and anonymously purchasable; exactly one matching SKU and one stored checkout order were verified. Manual guest checkout/admin visibility are user-confirmed, and the order was independently verified. Stages 3.7 and 3.8 provide local business-flow, Pod-replacement persistence and database-loss probe evidence; no broader assignment completion or current availability is implied. See [journey](project-journey.md) and [decisions](decisions.md).

## Current documentation change

Record Stage 5.4 per-request identity, shared audited invocation, durable history and validation while preserving earlier milestones. Only gateway source/tests/migration/package description and appropriate governance docs change; dependencies and old migrations stay unchanged. No Woo/Helm changes, staging or commit.

## Stage 5.4 authenticated MCP and durable attributed audit

| Area | Implementation/evidence |
| --- | --- |
| Baseline | Clean main at a3816e0; validated Woo untouched; k3d remains stopped |
| HTTP auth | Every SDK transport request verifies Bearer through existing key service; absent/malformed/unknown/revoked/disabled denied with 401 challenge; DB verifier outage 503 |
| Identity | Frozen safe principal in copied request state; Authorization stripped before SDK; concurrent users remain separately attributed |
| Revocation | Admin revokes B via existing REST; same connected official client next request gets 401, zero additional upstream contact |
| Shared invocation | Existing core reused; future session-derived chat seam tested, no chat implementation |
| Audit START | Initial transaction committed before upstream work; failure means zero dispatch; exact original mapping committed before business call |
| Outcomes | UTC timestamps, monotonic duration, succeeded/failed and allowlisted codes; rejected routed calls also audited |
| Interrupted/finalization | Cancellation leaves started; forced finalization failure leaves durable START after exactly one invocation, reports unknown/unsafe retry; no replay |
| History | 0003_audit after unchanged 0001/0002; user/key restrictive references, immutable snapshots, historical server ID/slug survives removal |
| Privacy | No args/results/key/hash/header/credential/PII columns; unknown caller names use unresolved sentinel; malicious error content becomes fixed code |
| Audit API | Admin-only GET /api/audits; default 20/max 100 per page, user/server/tool/outcome filters; member 403, anonymous 401 |
| Protocol/regressions | 160 tests = previous 130 plus 30 auth/audit tests; all 80 Stage 5.2 and 51 Stage 5.1 regressions retained; modern/legacy SDK clients |
| PostgreSQL | Disposable 18.0: empty 0001 -> 0002 -> 0003, schema parity, durable START/finalization/reconnect, deletion/revocation history, immutable constraints; container removed |
| Runtime boundary | Synthetic ASGI fixtures only; no listening TCP acceptance, real upstream business request or Kubernetes action |

Initial audit failure and route-binding failure prevent business execution. Finalization
can fail after a remote mutation, or its commit acknowledgement can be lost: started
means interrupted/unknown and must not trigger automatic retries. There is no distributed
exactly-once guarantee. Discovery/auth failures are not tool-call events; malformed
transport rejected before the handler is outside normal invocation auditing.

Dependencies remain unchanged and hash-locked; compilation, pip check, Windows/Linux
closure (41/39 packages), hash-enforced Windows wheel resolution, credential/contact
scan, 103 local documentation links/anchors, 75 tables and git diff --check pass.
Linux dependency closure is metadata validation, not Linux runtime execution. Audit retention/backup/operational repair, rate limiting, comprehensive
SSRF and upstream application encryption remain unimplemented. Management REST and
external MCP are now authenticated in fixture acceptance; deployment is still pending.
Additional two real upstreams, React dashboard, chat, gateway hosting, gateway-to-Woo
caller authentication/NetworkPolicy and final demo remain incomplete. Proposed next
reviewed slice: dashboard management UI for the existing identity/server/team/key/audit
APIs, with chat and deployment separately scoped. See [audit contract](../apps/gateway/README.md#stage-54-authenticated-mcp-and-attributed-audit)
and [decision](decisions.md#dec-032-stage-54-request-identity-and-durable-invocation-audit).

## Stage 5.3 identity and protected REST management

| Area | Implementation/evidence |
| --- | --- |
| Schema | Explicit 0002_identity after unchanged 0001_registry; users/sessions/invitations/api_keys, restrictive user references; no startup DDL |
| Passwords | Argon2id, independent salts, 64 MiB defaults; generic unknown/wrong/disabled login failure |
| Sessions | Hash-only opaque tokens, 8-hour default, HttpOnly/Lax/Path=/; production Secure/HTTPS; expiry/logout/disabled checks |
| Request protection | Shared admin guard on every server route; exact Origin on unsafe REST; no permissive CORS |
| Bootstrap | Separate protected-file command; transactional receipt; idempotent, no password overwrite, conflict refusal |
| Invitations | Admin member-only, intended username, 24-hour default, hash-only, atomic single use and revocation |
| API keys | Own issuance once; safe prefix/metadata; SHA-256 of random 256-bit token; reusable verifier |
| Team control | Admin identifies/revokes user B's key; same raw key immediately fails subsequent verification |
| Regressions | 130 tests including all prior 80; REST fixtures now use real admin login; 51 Stage 5.1 protocol tests unchanged |
| PostgreSQL | Empty migrations/schema, concurrent bootstrap/acceptance, hash persistence, reconnect and revocation pass; fixture removed |
| Boundary | External /mcp still unauthenticated; audit/UI/chat/deployment/gateway-only upstream enforcement incomplete |

Only synthetic fixtures used; no real users/credentials, Woo requests, cluster start
or Kubernetes changes. Lock adds argon2-cffi 25.1.0/bindings 26.1.0, preserving existing
pins. Username login refines the prior email-login wording under current instruction.
Cookie/Origin controls do not prove XSS defense, rate limiting, public TLS or capacity.
Upstream encryption and comprehensive SSRF remain absent. See the [identity contract](../apps/gateway/README.md#stage-53-identity-and-authorization)
and [security boundary](threat-model.md#stage-53-identity-and-rest-enforcement).

## Stage 5.2 persistent registry and management API

Started from clean main at 8245873. Adds SQLAlchemy/Psycopg PostgreSQL persistence
behind the existing repository interface, explicit Alembic migration, one-time
Woo pre-registration and FastAPI /api management in the same SDK /mcp backend.
No live Woo call, store mutation, Kubernetes action, fake identity or application
credential issuance. The validated Woo package is untouched.

| Area | Evidence and boundary |
| --- | --- |
| Persistence | Immutable UUID/unique slug enforced in app and DB; timestamps/revision, configuration, health and JSON tool cache; no arbitrary results |
| Seed | woocommerce / WooCommerce / internal Woo MCP URL, no credential; concurrent-safe receipt; preserves admin edits and intentional removal |
| API | List/detail/create/edit/enable/disable/remove/refresh; strict input and safe read DTOs; no authentication yet |
| Credential lifecycle | Omitted PATCH preserves; explicit object replaces; null clears; no read value; plaintext server-side DB baseline is a documented limitation |
| Discovery | Shared core, bounded refresh, separate enabled/health; last-good metadata remains stale for management on failure, excluded from live MCP |
| Tests | 80 tests including all 51 Stage 5.1 regressions; SQLite file persistence, REST/MCP ASGI, privacy and validation checks |
| PostgreSQL | Separate real 18.0 smoke passed migration/schema, identity/uniqueness, CRUD/reconnect, credential lifecycle, health/cache, seed and deletion; not merely SQLite evidence |
| Runtime boundary | Temporary official postgres:18.0-alpine Docker fixture only, loopback random port, synthetic data, 256Mi cap, approximately 80Mi observed; removed afterward; existing k3d containers stayed stopped |
| Remaining | No login/roles/sessions/invitations/user keys/audit/dashboard/chat; no public deployment or final gateway-only enforcement |

Dependencies are pinned and hash-locked: FastAPI 0.162.0, SQLAlchemy 2.0.55,
Psycopg binary 3.3.6, Alembic 1.20.1, Pydantic 2.14.1; MCP remains 2.3.0.
The runtime lock contains 39 packages. Compilation, dependency closure/pip check,
hash-verified wheel resolution, migration SQL/schema, credential/contact scan,
97 documentation links/anchors, 71 Markdown tables and git diff --check pass. SQLite does not establish PostgreSQL
behavior; the separate smoke supplies that limited evidence. Neither test proves
production capacity, backup, HA or Kubernetes hosting.

Validation found a test-fixture lifecycle issue: unittest setup/teardown entered and
exited SDK cancel scopes in different tasks. The fixture now uses a single lifespan
owner task, matching ASGI. Review also tightened the SQL credential consistency
constraint against SQL NULL semantics, and suppressed SQL result logging as well as
bound parameters. No gateway routing redesign or Woo source change was needed. The failed first
harness left disposable synthetic SQLite fixture directories in OS temporary
storage; a later cleanup request was blocked by automatic policy review. Successful
final fixtures clean themselves up, and the PostgreSQL container was removed.
No diagnostic files or databases were added to the repository.

The database bootstrap/migration lifecycle and [REST contract](../apps/gateway/README.md#management-rest-contract)
are documented in the gateway README. DEC-030 records the explicit Stage 5.2
credential-storage refinement and outstanding final Kubernetes Secret boundary.
Next proposed Stage 5.3: identity/session/admin-member authorization before exposure.

## Stage 5.1 offline gateway protocol core

Started from clean main at fef1b8c on 2026-10-25. Docker read-only inspection found both urumi-local containers stopped; they remain stopped. No Kubernetes API or live Woo request, credential access, image build, store mutation or Woo-source change.

| Area | Implemented evidence and boundary |
| --- | --- |
| SDK / backend | Python 3.13, official mcp 2.3.0 low-level Server handlers and Streamable HTTP /mcp; a module of the accepted single backend, no handwritten protocol or separate FastAPI service |
| Repository | Async registration/observation interface plus MemoryRepository; immutable UUID/unique slug, mutable display/URL/enabled/credential; PostgreSQL persistence remains future work |
| Namespacing | server_a__shared_name and server_b__shared_name coexist; exact registered slug plus authoritative stored original-name mapping; content-derived SHA-256 suffix shortens only overlong names; exact original mapping is retained |
| Enabled vs health | Disabled servers receive no new contact; connected/unreachable/unknown never overwrite enabled; late observation/configuration races are rejected |
| Aggregation | Concurrent discovery of enabled servers; healthy peers survive dead/slow peers; last-good metadata retained internally, unavailable tools excluded from current listings per Stage 5.1 instruction |
| Timeout / invocation | 5s discovery/connect, 30s call; operation-scoped SDK sessions; original tool name forwarded; no automatic retries, redirects or reconciliation; attempted-call failure reports unknown write outcome / unsafe retry |
| Schemas / results | Input/output schemas, descriptions, titles and annotations preserved; supported content/structured result normalized; local refs work and remote refs are not fetched; arbitrary top-level extension metadata/icons/task hints not proxied |
| Credentials / untrusted content | Synthetic bearer/static headers scoped per upstream; caller headers not forwarded, literal credential reflection refused, fixed errors and wire-log suppression; descriptions/results remain untrusted data, not instructions or authorization |
| Test boundary | Official client -> gateway ASGI -> official SDK upstream ASGI fixtures; current/legacy clients and a legacy upstream; no real listening TCP, Linux execution or live upstream acceptance |

Validation: 51 unittest tests pass, including independent same-name routing, exact original names, structured schemas/results, disabled/removed peers, dead/slow peers, bounded pagination, cancellation cleanup, configuration races and a single mutating call despite HeaderMismatch. The last suite ran in the isolated gateway environment; no fixture contacts the store. Python compilation, pip check and extras-aware direct dependency/lock closure checks pass: 29 exact packages, hash-verified installation, no Woo dependency changes. No formatter/linter is configured in this repository, so no formatting-tool result is claimed. Final collision review confirmed the existing digest hashes the complete unshortened name, not its length. Six added tests cover the 128-character boundary, safe characters, deterministic full-content hashing, equal-length/common-prefix distinction, separate slugs, exact original routing and forced-collision rejection before catalog publication; existing shared-name/current/legacy regressions remain green.

Validation corrections: initial lock extraction missed PyJWT's crypto extra; hash installation failed safely before accepting that incomplete closure. Corrected extra traversal produced the 29-package lock. An early test command ran before installation finished and failed imports; the final isolated run passed. First protocol fixtures incorrectly constructed an SDK error and a remote-ref schema; corrected them so tests exercise the intended behavior. Concurrent-call review fixed safe error preservation through exception groups and added a pre-dispatch configuration check. A 120ms concurrency fixture budget also timed out healthy SDK setup under debug scheduling; it now uses a 500ms test budget against a 2s slow upstream, leaving the real 5s/30s defaults unchanged. Final review passed for 79 local documentation links/anchors, 69 tables, credential/contact patterns and LF/whitespace. The complete tracked and new-file diffs were reviewed; only the planned package and four documents changed.

The source implementation advances REQ-GW-01 through REQ-GW-05 only at the protocol-core level. Mandatory admin APIs, PostgreSQL durability, users/roles/hashed revocable keys, audit, three real upstreams, gateway-to-Woo caller authentication/NetworkPolicy and client refresh/demo behavior remain incomplete. No fake identity or authorization is installed. Proposed Stage 5.2: review persistent registry and identity/auth/audit contracts, then implement them in small slices before deployment. See [gateway README](../apps/gateway/README.md), [architecture](architecture.md#stage-51-gateway-protocol-core) and [threat boundaries](threat-model.md#stage-51-gateway-protocol-boundary).

## Stage 4.9B controlled live-write acceptance

Started from clean main at 88e5cae. Initial available host RAM was 3.942 GiB;
immediately before the diagnostic client it was 3.921 GiB, above the approximately
3.5 GiB floor. Node Ready/MemoryPressure=False, all three application Pods Ready
with zero restarts, release urumi revision 4/deployed and original storage bindings
passed. With the user's explicit exception for this otherwise unexposed setting,
one read-only WordPress option check confirmed country IN. All product/order
access used the deployed MCP tools; no direct REST/SQL business operation.

One temporary credential-free client Pod used the official SDK through
http://urumi-woo-mcp.urumi.svc.cluster.local:8000/mcp. It had no Secret volumes,
literal credential environment or service-account token. Before either write,
list_products found zero matches for URUMI-MCP-LIVE-20261024-01 and get_order
verified order 12 was processing with its original items/499 INR/COD/free shipping.
The client enforced at most one invocation and one outgoing MCP request per write.

| Controlled operation | Exact input / observed result |
| --- | --- |
| create_product | name Urumi MCP Live Test Product; price string 599; SKU URUMI-MCP-LIVE-20261024-01; status publish; stock_status instock |
| Created result | created=true; product ID 16; simple; matching name/SKU; price and regular_price 599 INR; publish/instock |
| Exact-SKU verification | One matching product, ID 16, after creation and again after the order update; no duplicate or implicit update |
| Public product | http://store.urumi.test:8080/product/urumi-mcp-live-test-product/ returned 200 anonymously with name, 599 and Add to cart; shop also displayed it |
| Immediate order reread | get_order(12) immediately before mutation still processing; full normalized operational result matched the initial read |
| update_order_status | order_id=12, expected_status=processing, status=on-hold; result order_id=12, observed_before_status=processing, after_status=on-hold, changed=true |
| Post-write order | One get_order verification returned on-hold; every other normalized field matched, including product 11/SKU, quantity 1, unit price 499, total 499.00 INR, COD, free_shipping and zero shipping/tax totals |

The expected-status guard prevents proceeding from an observed mismatch but is
not atomic compare-and-swap; a concurrent writer can race between GET and PUT.
Normal Woo status hooks/notifications/stock behavior remain possible. Only the
status field was requested; no refund, second transition or reset to processing.
No claim is made that every internal Woo side effect was inspected.

| Write audit | Observed count/evidence |
| --- | --- |
| create_product tool invocation / outgoing MCP write request | 1 / 1 |
| Product POST /wp-json/wc/v3/products | Exactly 1; HTTP 201 |
| update_order_status tool invocation / outgoing MCP write request | 1 / 1 |
| Order PUT /wp-json/wc/v3/orders/12 | Exactly 1; HTTP 200 |
| Automatic retries | 0 |

POST/PUT evidence came from captured WordPress Apache access logs, bounded from
the diagnostic start (2026-10-24T15:35:10.657641Z) and filtered to the Woo MCP Pod
source IP. Only method/path/count/status projections were displayed, not raw log
lines, Authorization headers or credential material. Client counters agreed.
The client made three list_products and three get_order calls in total. There
was no ambiguous write response; emergency read-only reconciliation was not
needed. The exact-SKU checks above are normal post-success verification. No
second write attempt was made, and the application retry policy was unchanged.

Strict JSON-mode DTO validation and text/structured-result equality checks passed;
no billing/contact/address/customer fields, raw Woo response or credentials were
emitted. A captured Woo MCP log credential-pattern scan passed. The client exited
0 with zero restarts and was deleted; no ConfigMap or diagnostic repository file
was created. No image rebuild, Helm operation or persistent Kubernetes
configuration change occurred.

Final release remained revision 4/deployed. WordPress, MariaDB and Woo MCP kept
their Pod UIDs, were Ready and had zero restarts. No OOMKilled termination or
namespace OOM event was observed; MemoryPressure=False. Both original PVC/PV
names and UIDs remained Bound. Anonymous shop, new product and original product
pages returned 200 with real content. Final Windows RAM was 15.726 GiB total /
11.772 used / 3.954 available; node usage 1228Mi, WordPress 189Mi, MariaDB 121Mi,
Woo MCP 75Mi. These samples do not establish full-stack capacity.

Product 16 is intentionally retained as durable demo evidence. Order 12 is
intentionally left on-hold as the Stage 4.9B acceptance transition. Together with
Stage 4.9A, local Woo MCP business/runtime acceptance is complete for the five
implemented tools. Gateway-only caller authentication and targeted NetworkPolicy
remain pending; this is not overall assignment completion. Nothing staged or
committed; stop for review.

## Stage 4.9A cluster start and memory-gated stop

Started from clean main at b715fbe. Initial Windows RAM was 15.726 GiB total,
11.995 GiB used and 3.731 GiB available; the immediate pre-start measurement was
3.748 GiB available. Docker was reachable/Linux, context k3d-urumi-local, existing
cluster stopped. This was above the user's approximately 3.5 GiB floor, though
below the preferred approximately 4 GiB. `k3d cluster start urumi-local` started
only the existing cluster; no Docker/WSL restart or cluster recreation.

After startup, host available RAM was 2.739 GiB, materially below the floor.
Stopped before importing/deploying Woo MCP. A final read-only snapshot at
09:26 UTC on 24 October measured 15.726 GiB total, 13.009 GiB used and 2.717 GiB
available. No resource budget, probe, persistence or application configuration
was changed to fit. No user applications were closed automatically.

| Check | Actual observation |
| --- | --- |
| Cluster/system | k3d-urumi-local; node Ready, MemoryPressure=False; CoreDNS, Traefik, metrics-server and local-path-provisioner each 1/1 Ready |
| Helm/bootstrap | urumi revision 3/deployed; urumi-store-bootstrap-r3 Complete, succeeded=1, active=0 |
| WordPress | urumi-wordpress-886bfd79c-8w584, UID 31cb5902-52a2-4fb4-a8fe-c710d9892b89; Ready, zero restarts, no recorded prior termination |
| MariaDB | urumi-mariadb-0, UID 77f54305-a813-4207-aec8-897425f72595; Ready, zero restarts, no recorded prior termination |
| WordPress storage | urumi-wordpress remains Bound to pvc-864a302a-0a39-4880-b522-558a4c830845; original claim UID unchanged |
| Database storage | data-urumi-mariadb-0 remains Bound to pvc-d3e6142a-b6b9-4e67-8880-a564f41ba331; original claim UID unchanged |
| Anonymous HTTP | /shop/ and /product/urumi-demo-mug/ both 200; visible Urumi Demo Mug text after excluding scripts/styles; no Coming Soon presentation |
| REST Secret Check | urumi-woocommerce-rest present, Opaque, exact consumer-key/consumer-secret key contract PASS; values not printed/decoded; object preserved |
| Node/Pod memory | Allocatable 6064264Ki (~5.78 GiB); sampled node usage 883Mi after startup, then 968Mi; final MariaDB 124Mi, WordPress 84Mi |
| Reviewed image | Local urumi-woo-mcp:stage4.8 exists, Linux/amd64; image ID sha256:a51a9aa791b6788a1c252f7185e48890434ed888947fab3dca7bbd5b3dfc09c4; no rebuild/import |

WordPress and metrics-server were initially not Ready and recovered within the
bounded startup waits; no corrective application action was taken. Current Pod
status shows no OOMKilled termination. Node MemoryPressure=False does not override
the Windows host-memory gate or prove capacity for another component.

**Stage 4.9A is incomplete.** Full direct deterministic option/product/order checks
were not performed after the gate failed; HTTP/readiness are not a replacement for
the required preservation checks. No simulated revision-4 delta, live upgrade,
Woo MCP Pod/Service/security inspection, discovery or business read occurred.
Neither mutating tool was called. No temporary diagnostic resources were created,
so none required deletion. Existing cluster/store remain running at revision 3.
Resume from fresh memory and complete store preflight once sufficient host headroom
is available; preserve the mandatory server-side upgrade preview and serialization
boundary. Gateway authentication/NetworkPolicy remain future work. Nothing staged
or committed; stop for review.

## Stage 4.9A resumed preflight and country-drift stop

The user requested continuation. Fresh host available RAM measured 3.800 GiB;
Docker/Linux and existing urumi-local were already running in context
k3d-urumi-local. No second cluster start or infrastructure restart. The initially
requested platform checks passed: marker 3, active WooCommerce 11.2.1, postname
permalinks, both Live options no, INR and Asia/Kolkata. Read-only Woo APIs found
unique product 11 / URUMI-DEMO-001 / Urumi Demo Mug / 499 / publish / instock,
and exactly one stored order: 12, processing, quantity 1 of product 11, total
499.00 INR, COD and free shipping. No customer contact/address fields were selected.
Original claim/PV identities, four system Deployments, store readiness and both
anonymous HTML routes passed. REST helper Check again passed Opaque/exact key names.

Imported the existing reviewed image with:

```text
k3d image import urumi-woo-mcp:stage4.8 --cluster urumi-local
```

Node containerd lists docker.io/library/urumi-woo-mcp:stage4.8 with image/config ID
sha256:d0f34be3481a9707a3e33b5f2ec3f740ef18795583dfa1837619237f8533eb32,
matching the reviewed build's config digest. The local Docker OCI index remains
sha256:a51a9aa791b6788a1c252f7185e48890434ed888947fab3dca7bbd5b3dfc09c4.
No image rebuild. The node exposes crictl directly; an initial k3s crictl inspection
was unsupported and corrected without changing the runtime. Import's temporary
archive/tools helper was removed by k3d.

Server-side previews used this command, capturing output in memory and comparing
only the rendered resources to the live release-3 manifest:

```text
helm upgrade urumi charts/urumi --namespace urumi --kube-context k3d-urumi-local --values charts/urumi/values-local.yaml --dry-run=server --hide-secret --output json --timeout 3m
```

| Simulated revision-4 delta | Actual preview result |
| --- | --- |
| New Woo MCP resources | Deployment/urumi-woo-mcp and ClusterIP Service/urumi-woo-mcp |
| Revision-specific resources | ConfigMap urumi-store-assets-r3 becomes r4; Job urumi-store-bootstrap-r3 becomes r4, with its assets volume reference updated |
| Bootstrap implementation | ConfigMap scripts and all other Job settings identical to revision 3 |
| WordPress Deployment | Entire definition/Pod template unchanged; no Recreate rollout expected for this upgrade |
| MariaDB StatefulSet | Entire definition, claim template and retention unchanged |
| Existing Services/PVC/Ingress | Identical; no PVC/PV deletion/recreation proposed |
| Secret/Namespace/PV objects | None rendered; ten total chart objects |
| Actual release after preview | Still revision 3/deployed; previews did not apply resources |

An initial comparison incorrectly expected WordPress to reference the revisioned
ConfigMap. Inspection showed only the Job mounts it; corrected comparison confirmed
WordPress is unchanged. This corrects the preview expectation, not application code.

Before upgrade, a deeper read-only comparison checked persisted ownership and every
target in urumi_bootstrap_settings. **v3 ownership and marker match, but
woocommerce_default_country is IN:KA while its persisted target is IN.** Every
other checkpointed setting matches. Although both values denote India, this is an
exact deterministic-contract mismatch. The initiating actor/trigger/time is unknown.
No admin/configuration action was taken to fix or adopt it.

The unchanged bootstrap refuses to overwrite completed-store settings that differ
from their checkpoint. Therefore its r4 Job would reject this state, and Stage 4.9A
stopped before the actual upgrade. WordPress readiness does not test the country
checkpoint, so Ready/HTTP 200 did not establish full bootstrap-rerun safety.
No bootstrap execution, marker edit, Secret change or product/order mutation.

Final available host RAM was 3.835 GiB (15.726 total / 11.891 used). Node Ready,
MemoryPressure=False; node usage 1076Mi, WordPress 153Mi, MariaDB 119Mi. Both store
Pods retain the identities above and zero restarts; bootstrap r3 is still Complete,
and both original claims/PVs remain Bound. These are sampled readings, not peak
measurements. Existing cluster/store and imported image remain; no temporary
diagnostic workload was created. MCP discovery/list_products/get_order/list_orders
were not attempted, and neither mutating tool was invoked. Stage 4.9A remains
incomplete. Resolve the country-contract discrepancy through a separately reviewed
decision before retrying the fresh preflight/preview; do not silently reset or adopt
it. No staged changes or commit.

### Country repair report and fresh verification stop

The user approved retaining exactly IN as the deterministic source of truth:
IN:KA is syntactically valid WooCommerce country/state configuration, but is not
the accepted Stage 3 baseline. Bootstrap must not accept both values or weaken
ownership/marker checks. The user reported intentionally restoring IN through
the WordPress option API. **This resume could not verify that repair:** fresh
WordPress option reads from the existing Deployment still returned IN:KA, with
persisted target IN. Every other entry in urumi_bootstrap_settings matched its
target, and marker remained 3. No conclusion can be drawn about whether the
reported repair persisted or whether something subsequently changed the value;
the cause remains unknown. No option, ownership, marker or bootstrap code was
changed by this run.

| Fresh read-only check | Actual result |
| --- | --- |
| Windows RAM total / used / available | Initially 15.726 / 12.319 / 3.408 GiB, below the floor; subsequent user-requested recheck 15.726 / 12.105 / 3.622 GiB, passing the approximately 3.5 GiB floor cautiously |
| Runtime and context | Docker reachable/Linux; existing urumi-local running; k3d-urumi-local |
| Node/system | Node Ready, MemoryPressure=False; four required system Deployments each 1/1 Ready |
| Helm/bootstrap | urumi revision 3/deployed; r3 Complete, succeeded=1, active=0; no bootstrap Pod present |
| Store Pods | Same WordPress/MariaDB names and UIDs recorded above; both Ready, zero restarts and no OOMKilled termination in current/last container status |
| Storage | Both original claim UIDs, PV names and PV UIDs unchanged and Bound; reclaim policy remains Delete if a PVC is deleted |
| Node/Pod memory | Node 1096Mi, allocatable 6064264Ki; WordPress 153Mi, MariaDB 120Mi; sampled values, not peaks |

The subsequent user-requested recheck still returned IN:KA against IN, with marker
3 and no other checkpointed option mismatch. Memory now passes the cautious floor,
but the configuration gate remains blocked. Full deterministic
preflight, fresh product/order/HTTP/Secret checks, imported-image reinspection and
the repeated server-side preview were not completed on this resume. Earlier
observations remain historical evidence, not substituted fresh checks. No cluster
restart, image rebuild/import, Helm upgrade, diagnostic resource, MCP call or
business-data mutation occurred; no cleanup was needed. Resume requires fresh
proof of IN, the remaining deterministic checks and sufficient memory before
the mandatory preview. Stage 4.9A remains incomplete; nothing staged or committed.

## Stage 4.9A verified repair deployment and read-only acceptance

The user supplied the repair evidence: raw persisted country was IN:KA;
update_option to IN returned true; immediate raw DB and WordPress reads returned
IN; an independent reread several seconds later returned IN through both paths.
This establishes persisted drift and controlled restoration, not its initiating
cause. This run independently verified get_option returned IN before and after
deployment, with no other checkpointed option mismatch. The source of truth stays
IN; no bootstrap code, ownership or marker semantics were relaxed. No country
write or additional raw DB investigation was performed by this run.

The minimal pre-apply gate passed: existing node and store Ready, MemoryPressure
False, zero current store restarts/OOM termination evidence, marker 3, WooCommerce
11.2.1, postname/Live configuration, unique product 11, unchanged Processing order
12, and original claim/PV identities. The REST helper Check passed Opaque and the
exact consumer-key/consumer-secret contract without revealing values. Available
RAM was initially 3.686 GiB, then 3.859 GiB immediately before the upgrade.

The repeated server-side preview matched the earlier reviewed delta exactly:
ten objects, two new Woo MCP resources, r3-to-r4 ConfigMap/Job naming/reference
changes only, identical scripts and other Job settings. WordPress, MariaDB,
existing Services/PVC/Ingress were unchanged. No Secret/Namespace/PV rendered or
storage recreation was proposed. The r4 Job expects IN and bootstrap version 3,
matching the restored checkpoint. Node image/config digest remained
sha256:d0f34be3481a9707a3e33b5f2ec3f740ef18795583dfa1837619237f8533eb32;
the reviewed stage4.8 image was reused without rebuild or reimport.

Executed exactly one actual upgrade, with no atomic removal or automatic rollback:

```text
helm upgrade urumi charts/urumi --namespace urumi --kube-context k3d-urumi-local --values charts/urumi/values-local.yaml --wait=watcher --wait-for-jobs --timeout 15m
```

| Deployment/runtime check | Observed result |
| --- | --- |
| Helm | urumi revision 4, deployed; Upgrade complete |
| Bootstrap | urumi-store-bootstrap-r4 Complete in 10 seconds; safe log checks confirmed existing WordPress/users/passwords preserved and successful verification |
| Bootstrap behavior | Completed v3 configuration verified; existing hard rewrite flush performed by unchanged orchestration; country IN/marker 3 remained intact; business snapshots unchanged |
| Woo MCP Pod | urumi-woo-mcp-fc54684f8-s4bw5, UID cf1fe46b-e6e3-4402-833c-a640b57e6c63; Ready, zero restarts; reviewed image/config digest matches |
| Service/endpoints | urumi-woo-mcp ClusterIP 10.43.21.125, port 8000 to named http port; one ready EndpointSlice address 10.42.0.112 |
| Store continuity | Original WordPress and MariaDB Pod UIDs unchanged; both Ready with zero restarts; r4 bootstrap Pod also zero restarts |
| Storage | Both original claim UIDs, PV names and PV UIDs unchanged and Bound; no PVC/PV deletion/recreation |
| Security | UID/GID 10001; non-root; read-only root filesystem; CapEff zero; NoNewPrivs=1; seccomp=2 with RuntimeDefault; privilege escalation disabled; all capabilities dropped |
| Credential boundary | No service-account token automount or token file; only external urumi-woocommerce-rest mounted read-only; both expected files mode 0440/readable on read-only mount; metadata checked, contents never read/displayed by inspection |
| Probes/resources | Listener-local TCP probes remain; requests 50m/128Mi, limits 500m/256Mi unchanged |
| Exposure | ClusterIP only, no NodePort/LoadBalancer/external IP and no Ingress backend targeting Woo MCP; gateway-only caller enforcement still pending |

A disposable in-cluster official SDK client used the reviewed image with no
credential volumes, environment values or service-account token. Service DNS
resolved to 10.43.21.125; /mcp accepted the FQDN Host and discovered exactly five
tools with input/output schemas. Protocol 2026-07-28 succeeded without a session-ID
header. The client had no Woo REST credentials or Authorization header; only the
server consumed its mounted REST pair. Neither mutating tool was called.

| Approved read | Actual normalized evidence |
| --- | --- |
| list_products(sku=URUMI-DEMO-001) | Exactly product 11, Urumi Demo Mug, simple, 499 INR, publish, instock; total 1, no further page |
| get_order(order_id=12) | Processing, created 2026-10-21T02:24:15Z, 499.00 INR, COD; product 11/SKU, quantity 1, unit price 499; free_shipping, shipping/tax totals 0; no customer/contact/address fields |
| list_orders(date=today,page=1,per_page=5) | Resolved 2026-10-24 in Asia/Kolkata; UTC interval [2026-10-23T18:30:00Z, 2026-10-24T18:30:00Z); count/total 0, as expected for the earlier order |

The first diagnostic client passed discovery/products but rejected the order's
JSON timestamp using strict Python-mode DTO validation. Offline reproduction
isolated this to the disposable harness; JSON-mode validation passed. Corrected
only that client, then repeated get_order and ran list_orders. Total MCP business
calls were one list_products, two get_order and one list_orders, all read-only;
this was an explicit diagnostic repeat, not automatic REST/write retry. The
corrected client exited 0. Order text and structured results matched the strict
operational DTO allowlist. No raw upstream body, credential or customer PII was
displayed; captured Woo MCP log credential-pattern scan passed. The application,
image, authentication and Helm configuration were not changed for this correction.

Post-read store and storage snapshots exactly matched pre-upgrade evidence:
country IN, no owned-option mismatch, marker 3, WooCommerce 11.2.1, unique unchanged
product 11 and exactly one unchanged order 12. Anonymous shop/product pages each
returned 200 with visible demo-product content and no Coming Soon presentation.
All three workloads were Ready, release 4/deployed, MemoryPressure=False, no
current/last OOMKilled termination or namespace OOM event observed. Both temporary
client instances were deleted; no diagnostic ConfigMap or repository artifact was
created. Deployed MCP, store, Secrets, storage and release remain running/intact.

| Memory sample | Available host RAM | Node / WordPress / MariaDB / Woo MCP |
| --- | --- | --- |
| Immediately before upgrade | 3.859 GiB | Not sampled at that instant |
| Immediate rollout | 3.746 GiB | 1219Mi / 156Mi / 120Mi / 57Mi |
| Final, after client cleanup | 3.942 GiB (15.726 total / 11.785 used) | 1207Mi / 171Mi / 120Mi / 74Mi |

These are samples, not continuous peaks or full-stack capacity proof. Stage 4.9A
passes deployed read-only integration only. Live create/status-update acceptance
remains separately authorized future work. Internal Kubernetes exposure does not
enforce gateway-only callers; gateway authentication and targeted NetworkPolicy
remain incomplete. No broader assignment signoff, staging or commit.

## Stage 4.8 process Docker and internal Helm hosting

The existing SDK ASGI factory/lifespan now reads non-secret environment settings
and explicit SDK Host allowlists. Uvicorn 0.54.0 is a direct runtime pin, promoted
from the existing hash lock without changing any package version/hash. No FastAPI,
transport wrapper or business-client replacement. All five tools remain unchanged.
See the [hosting contract](../apps/woo-mcp/README.md#process-container-and-helm-hosting)
for exact configuration, accepted Host forms, probes and reproduction commands.

| Acceptance | Observed result |
| --- | --- |
| Python tests | 116 pass: previous 110 plus six hosting tests; current/legacy mocked tool coverage retained |
| Listening TCP | Actual Uvicorn child process; official MCP discovery exposes five schemas; invalid Host 421, browser Origin 403; synthetic Woo trap observes zero requests; graceful shutdown |
| Runtime dependency installation | Fresh Linux image installs 33 hash-locked runtime packages; pip check passes; Windows direct-pin resolution matches all 34 locked packages/hashes (Windows-only pywin32) |
| Image | Official Python 3.13.17 slim-bookworm Linux/amd64 manifest pinned; local urumi-woo-mcp:stage4.8, 229,000,063 bytes (~218.4 MiB) |
| Docker acceptance | Official TCP discovery returns five tools; UID/GID 10001, read-only filesystem, capabilities zero, no-new-privileges and seccomp verified; clean exit 0, no OOM; synthetic credential/log checks pass |
| Helm/static | Local and production lint/render pass; ten resources each, including new Deployment/ClusterIP Service; strict Kubernetes v1.35.5 schema and duplicate-key checks pass |
| Existing store | Eight rendered store objects match HEAD at the same revision; no budget, probe, storage or business configuration change; disabled Woo MCP renders eight |
| Isolation/config | No Woo MCP Ingress/public Service/PVC; no Secret/Namespace object; exact external REST Secret file reference, no service-account token; selectors/ports/mounts/probes/resources/security checked |
| Repository | Compilation, dependency consistency, credential/contact, documentation and whitespace checks pass; unstaged/uncommitted |

The first Docker smoke caught copied bytecode caches; `.dockerignore` was tightened
and the rebuilt image passed. A Windows validator initially decoded pip's UTF-8
report with the default encoding; explicitly reading UTF-8 fixed that checker,
and dependency resolution/hash comparisons passed. Neither issue changed business code.

The image binds 0.0.0.0:8000; temporary acceptance publishes only on loopback and
mounts synthetic files outside Git. Temporary process/container/files are removed;
the image remains for later reviewed import. Initial Docker inspection showed k3d
running, so `k3d cluster stop urumi-local` was used once. No cluster recreation,
Kubernetes API mutation, Helm install/upgrade, real Secret retrieval or Woo request.

TCP probes check the local MCP listener only, not Woo availability or business
health. Requests 50m CPU/128Mi and limits 500m/256Mi remain hypotheses for Stage 4.9;
default rolling updates can need temporary extra capacity. Mounted Secret mode
0440/fsGroup 10001 and Kubernetes probes still need runtime acceptance. Production
registry/domain values are placeholders; internal HTTP OAuth signing uses an HTTP
origin even when public Ingress uses HTTPS, with VPS behavior still unproven.

Gateway-only enforcement is not complete: ClusterIP/Host checks do not authenticate
callers. Service credential urumi-woo-mcp-auth and targeted NetworkPolicy remain
deferred to gateway integration. No optional security bonus is declared complete.
Stage 4.9 is a proposed separately reviewed runtime slice: fresh memory/store gates,
image import, exact Helm preview (including revision-specific bootstrap and WordPress
replacement), serialized release operation and internal discovery/probe/security/resource
measurement. Live business writes require separate authorization. Stop for review.

## Stage 4.7 guarded order status updates

Implemented exactly update_order_status as the fifth tool, reusing strict SDK inputs,
lifespan/client, OAuth signing, normalized outputs and sanitized error taxonomy.
The three reads remain read-only; both writes are mutating/non-idempotent. Annotations
are descriptive and do not implement gateway authorization.

The [status-update contract](../apps/woo-mcp/README.md#guarded-order-status-updates)
requires strict positive order_id, six allowed target statuses and expected_status
from the seven readable standard statuses. One GET requests/normalizes only id/status.
STATE_CONFLICT includes safe expected/observed enums and prevents PUT; the guard runs
before the same-status no-op. Otherwise one PUT sends only status. Valid HTTP 200,
matching ID and target status produce the four-field changed=true result. Bad/mismatched
write responses remain unknown, never successful unchanged-state claims.

Initial GET failures retain normal read semantics; once PUT is attempted,
timeout/network/5xx/redirect/unusable response carries write_outcome=unknown and
retry_safe=false. No automatic retry, reconciliation or rollback. INVALID_TRANSITION
is limited to a structured WordPress status-enum rejection, confirmed against the
pinned source; generic/plugin 4xx remains WOO_REQUEST_REJECTED. No invented workflow
or message matching. The GET/compare/PUT sequence races other writers, and Woo hooks
may affect notifications/fulfillment/stock. Refund operations and refunded targets
are excluded; refunded is allowed only as an observed expected state.

| Validation | Result / boundary |
| --- | --- |
| Full suite | 110 tests passed: prior 83 plus 24 update tests and 3 protocol tests |
| Write safety | Explicit GET/PUT counts; conflict/no-op/read failure zero PUTs; writes at most one; committed-write/lost-response and intervening-writer fixtures |
| REST/privacy | Exact status-only PUT, canonical PUT signing/Host, strict identity/status normalization; no customer fields, credentials, headers or raw error bodies in results |
| Protocol | Official auto/current/legacy clients discover five tools; schema, structured success/no-op and sanitized conflict/rejection/ambiguity pass |
| Repository | Compilation, installed dependency/unchanged lock consistency, credential/contact scan, documentation links/anchors/tables and git diff --check passed |
| Runtime | Offline mocks/in-process ASGI only; no live order update, listening TCP acceptance, container or Kubernetes work |

All five mandatory tool contracts now exist, but the full Woo MCP requirements are
not complete. No real store state was read or changed in Stage 4.7; product 11/order 12
were not touched. Previous store evidence is historical, not a fresh health check.
No formatter/linter is established; none added. No dependency/architecture change.
SDK adapter coupling, configured INR, HTTP transport limits and runtime date-boundary
acceptance remain as documented.

Proposed Stage 4.8 boundary: review container/Helm hosting design and perform a local
listening-TCP MCP smoke test against mocked Woo REST before separately authorized
container/Kubernetes deployment and live writes. This proposal does not authorize
starting the cluster or mutating the store. Nothing staged or committed; stop for review.

## Stage 4.6 first mutating tool

Started clean on main at c975ede. Extended models/server/client and protocol tests; added test_create_product.py. The private GET helper now delegates to a shared GET/POST request path with the same OAuth signer, HTTP client, deadlines, response cap and zero retries. Read behavior/regressions are retained. Product allowlist normalization is shared between listing and creation. No dependency changes or new service layer.

The [create contract](../apps/woo-mcp/README.md#product-creation-and-uncertain-writes) accepts name/price, optional SKU and limited status/stock enums only. It always POSTs type=simple and maps price to regular_price, omitting absent SKU. One bounded SKU lookup can reject DUPLICATE_SKU before any POST. Precheck is race-prone; pinned Woo create-time product_invalid_sku is recognized without exposing raw messages. Generic race-related 5xx remains unknown. No update-existing or successful-reuse behavior.

WooError retains its safe taxonomy and adds fixed write_outcome=unknown/retry_safe=false semantics for attempted writes with timeout/network/5xx, redirects, unexpected success status, malformed/oversized response or failed Product verification. SDK errors retain is_error=true, not an error-shaped success. No automatic reconciliation read. A caller may explicitly invoke the tool again; there is no durable idempotency guarantee. Cancellation propagates without replay and can leave the caller without a response. Do not infer non-creation. HTTP OAuth still does not encrypt or integrity-protect the JSON body.

| Validation | Result / boundary |
| --- | --- |
| Full suite | 83 tests passed: previous 59 (catalog now four), 21 create tests, 3 added protocol tests |
| Input/payload | Strict bounds/types/extras; exact POST path and approved JSON keys; canonical POST signing/Host; null SKU omitted |
| Duplicates/retries | Precheck match/failure yields zero POSTs; empty precheck and create-time conflict yield at most one; no retry/reconciliation, including lost response after a mock committed write |
| Protocol/privacy | Official current/legacy clients discover four tools, preserve three read hints and mark create mutating/non-idempotent; normalized success and sanitized errors; no auth/body/customer leakage |
| Repository | Compilation, pip/dependency/hash-lock consistency, credential/contact scan, documentation links/anchors/tables and git diff --check passed |
| Runtime | No live create/read, listening TCP acceptance, Linux execution or Kubernetes hosting |

The first 82-test run passed; review added a stronger committed-write/lost-response fixture, bringing the suite to 83. No formatter/linter is established, none added. Resource/Secret/store state unchanged. The known SDK 2.3.0 adapter coupling, configured product INR and runtime date/transport limitations remain. update_order_status is absent; full Woo MCP requirements are not complete.

Proposed Stage 4.7: update_order_status only, with strict expected_status guard, read-before-write/no-op semantics, one PUT and unknown-outcome/no-retry behavior, tested offline before a separately authorized live change. No such implementation is authorized by this proposal. Stop for review; nothing staged or committed.

## Stage 4.5 read-only order tools

Started clean on main at 68b2840. Added orders.py for UTC window resolution/nested normalization and test_orders.py; extended models/config/client/server and official-client tests. Generalized the pinned SDK strict argument adapter across three tools and extracted shared pagination validation without replacing OAuth, lifecycle or transport. Updated package descriptions and added only tzdata==2026.5 to the exact hash lock (34 packages); the first Windows zoneinfo check failed because IANA data was absent. The first-party timezone package resolves that actual dependency. No other existing pin changed.

Contracts and source links are in [the package README](../apps/woo-mcp/README.md#order-tools-and-store-dates). get_order requires a strict positive ID, GETs one order and returns only operational detail. list_orders accepts strict bounded pagination, seven standard statuses and today/explicit date, returning summaries and pagination/window metadata. _fields reduces upstream disclosure; nested allowlists independently omit billing/shipping address/customer/contact/note/key/metadata. Woo JSON price numbers use Decimal; GMT creation times become offset-bearing UTC timestamps. No direct SQL or write path.

Date semantics preserve the accepted design: resolve today once in configured Asia/Kolkata; UTC start-inclusive/end-exclusive; dates_are_gmt=true; after=start minus one second; before=end. The pinned 11.2.1 REST/HPOS source and WordPress date-query semantics support this strict-second mapping. Fixtures include just before/start/last second/next midnight, Kolkata midnight, leap day/year rollover and explicit date reuse. Returned out-of-window rows fail instead of silently altering counts. This does not prove live active-datastore boundary behavior.

| Validation | Result / boundary |
| --- | --- |
| Full offline suite | 59 tests passed: prior 31 retained (catalog assertion now three), 25 order tests, 3 added protocol tests; parameterized cases cover additional statuses/failures |
| Official MCP clients | Auto/explicit 2026-07-28 and legacy 2025-11-25 discover exactly three read-only tools and return typed order results; strict argument errors remain sanitized |
| Privacy/errors | Synthetic customer-shaped payloads absent from normalized structured/text output and errors; 404 maps to NOT_FOUND; transport/auth/forbidden/timeout/rejection/5xx/redirect/size/malformed checks pass |
| Dependencies/static | Compilation, pip check, direct/installed/hash-lock consistency, credential/contact scan, local documentation links/anchors/tables and git diff --check passed |
| Runtime boundary | No real Woo order requests, listening TCP server acceptance, Linux execution or Kubernetes hosting tested |

Review tightened rejection of malformed line/shipping containers and unrepresentable UTC date windows. No test failure required a design change. No configured formatter/linter exists, none added. Pagination remains non-snapshot; whole-body cap may reject large orders/pages. Allowed names are untrusted text, not a universal PII-redaction guarantee. Custom order statuses/fractional quantities remain outside this initial contract. SDK metadata integration remains coupled to MCP 2.3.0; product currency remains configured INR, order currency comes from Woo. Both write tools remain absent; full Woo MCP requirements are not complete.

Proposed Stage 4.6: separately review and implement create_product only, with strict inputs, SKU conflict handling, one write/no automatic retry, sanitized ambiguous-write outcomes and offline/protocol tests. No live write authorized by this proposal. Stop for review; nothing staged or committed.

## Stage 4.4 first MCP tool and offline protocol acceptance

Started from clean main at 01e4b77. The [package](../apps/woo-mcp/README.md) adds models.py, server.py and product/protocol tests; updates metadata, the dependency lock, configured currency, shared REST code and package documentation. No new service framework, Dockerfile, deployment resource or runtime diagnostic is introduced.

Reuse: the established origins, credential-file reader, OAuthLib HMAC-SHA256 header signing, Host, redirect rejection, deadlines, response-byte bound and no-retry HTTP behavior remain. The original single-product diagnostic and 13 tests still pass. Its GET body was extracted into a shared method for both diagnostic and list_products; the OAuth implementation was not replaced. Inspection also found the explicit transport needed its own connection-limit configuration, so the intended 4 connections/2 keepalive limits now reach that transport when the lifespan holds it persistently.

Direct pins added: mcp==2.3.0 and pydantic==2.14.1; httpx==0.28.1/oauthlib==4.0.0 stay unchanged. Test extra pins httpx2==2.16.0, already required by the official SDK, for its ASGI HTTP client. The SDK's HTTPX2 transport and Woo's proven HTTPX transport coexist. All eight Stage 4.3 versions remain; the new hash lock contains 33 packages (pywin32 Windows-only), including SDK-required Starlette/Uvicorn/crypto/telemetry libraries, not application auth/audit implementations. No third-party FastMCP or FastAPI. Initial pip resolution with hash-bearing constraints failed closed; resolution then used version-only constraints in a temporary file and the resulting full lock was independently hash-checked.

MCPServer from mcp.server owns the server and Streamable HTTP app. streamable_http_app uses /mcp, JSON responses and stateless_http=True; subscriptions disabled. Modern 2026-07-28 is inherently stateless; the setting makes the legacy path sessionless too. SDK lifespan opens one WooClient at startup and closes it on shutdown, without network/credential work on import. Tests inject only a mock HTTP transport/dummy credential factory. Default SDK Host/Origin protections remain enabled; future Kubernetes host allowlists still need configuration.

Strict flat list_products input: page integer >=1/default 1, per_page integer 1-50/default 20, optional trimmed nonblank search 1-100 or sku 1-64 (mutually exclusive), optional publish/draft/pending/private status. Extra fields and numeric coercion (including bool) fail. No arbitrary REST URL/parameter passthrough. Pydantic Product/Collection return annotations expose and validate structured output. Products include exactly id/name/sku/type/price/regular_price/currency/status/stock_status/permalink; collection includes items/page/per_page/total/total_pages/has_more/currency. Currency comes from the configured INR store contract, not another REST lookup; empty price strings for unpriced drafts remain valid.

One products GET requests allowlisted fields and filters only. Each pagination header must occur exactly once and contain a bounded nonnegative integer; totals/page count/item count must agree. No silent all-page fetch, inferred count or retry. Inconsistent concurrent-pagination results fail rather than claim a snapshot. Normalization drops other fields and rejects malformed products/URLs/duplicates. The shared transport preserves bounded/sanitized HTTP errors; ToolError is used for operational failures, not successful error-shaped output.

Implementation finding: the SDK's default function argument model ignores unknown fields and pre-parses JSON-looking strings. The pinned Tool/FuncMetadata integration binds ListProductsInput, publishes its strict schema and removes rejected names/values from validation exceptions. SDK validation expects Pydantic ValidationError at that boundary and converts it into an is_error tool result; raising ToolError there initially produced the generic crash message. The test caught this and the adapter now raises sanitized ValidationError there, with ToolError in the actual tool handler. No JSON-RPC parsing was added. This metadata hook is SDK-version-coupled and must be regression-tested on upgrades.

| Stage 4.4 validation | Result / boundary |
| --- | --- |
| Full suite | 31 unittest tests passed: 13 preserved connectivity, 13 input/client and 5 protocol tests; parameterized cases cover additional failures |
| Modern protocol | Official Client auto discovery and explicit 2026-07-28 over streamable_http_client + HTTPX2 ASGITransport at /mcp passed |
| Legacy protocol | Official Client mode=legacy negotiated 2025-11-25 and passed; no custom legacy logic |
| Discovery/output | Exactly list_products; strict schema/defaults/bounds/read-only annotation; typed output schema and normalized structured result |
| Lifecycle/session | Two calls reuse one client; lifespan closes it; no Mcp-Session-Id request/response in modern or configured legacy mode |
| Validation/security | Unknown/invalid arguments are safe MCP tool errors, no REST request; auth failure is is_error with no structured success; fixtures/raw bodies/credentials absent from results |
| REST failure coverage | Connection, timeout/deadline, 401/403/404/other 4xx/5xx, malformed JSON/DTO/pagination, oversized body and redirect refusal; no retry |
| Dependencies | pip check passed; 33 Windows wheels freshly hash-verified with dependency resolution; 32 Linux glibc x86_64 wheels hash-verified/available, not executed |
| Repository checks | Python compilation, credential/contact scan, documentation links/anchors/tables and git diff --check passed; no established formatter/linter configuration, none added |

The first HTTP protocol run correctly rejected a portless loopback Host with 421. The test URL was corrected to explicit port 8000; protections were not disabled. Protocol requests traversed the SDK's actual ASGI HTTP path in-process, not a listening TCP server/container. All Woo business responses were mocked. No claim is made about live pagination, Linux runtime, deployed MCP, gateway-only access or complete Woo requirements. No cluster was started or inspected and no Stage 4.3 read was repeated.

Proposed Stage 4.5 boundary: add only get_order with the approved operational/PII-minimized DTO and ID validation, using the shared REST client and deterministic unit/protocol tests. Keep writes, list_orders timezone work, container/Kubernetes hosting and gateway authentication in separately reviewed steps. Stop for review; nothing staged or committed.

## Stage 4.3 authenticated REST connectivity acceptance

Repository gate: main was clean with 95a2387 (approved Stage 4.2) at HEAD. An earlier attempt stopped because the helper and direct identity lookup found the REST Secret absent. The user subsequently completed masked helper entry and reported one manually issued Read/Write key named Urumi Woo MCP Local associated with the existing administrator. No second key was generated by this work; the helper Check now passes before and after the diagnostic.

| Preflight on 2026-10-23 | Observed evidence |
| --- | --- |
| Cluster/runtime | Docker Linux; urumi-local 1/1 server; context k3d-urumi-local; node Ready, MemoryPressure=False |
| Store/release | urumi revision 3/deployed; WordPress and MariaDB 1/1 Ready, zero restarts; bootstrap r3 Complete/11s |
| Storage | Both existing PVCs Bound to original PVs; no storage operation |
| Canonical state | Hostname resolves to 127.0.0.1; marker 3; /%postname%/; coming_soon=no; store_pages_only=no; WooCommerce 11.2.1 |
| Anonymous pages | Shop and product HTTP 200, mug/Add to cart present, no Coming Soon presentation |
| Secret identity | urumi-woocommerce-rest, Opaque, exactly consumer-key and consumer-secret; no extras/mis-cased keys; contract PASS |
| Host memory | 4.627 GiB available initially; 4.724 GiB immediately before diagnostic Pod creation |

The [client slice](../apps/woo-mcp/README.md) pins httpx==0.28.1 and oauthlib==4.0.0 on Python 3.13. requirements.lock pins eight universal-wheel dependencies with SHA-256 hashes. HTTPX supplies pooling/async transport/mock tests; OAuthLib supplies all signing cryptography. Standard-library configuration/normalization/tests avoid an extra framework. Config, credential-file reader, pooled client and one-read entrypoint are reusable; the expected-product acceptance assertion is kept outside the client. No MCP dependency, endpoint, tools, writes, Dockerfile, Deployment or Service was created.

Temporary Pod urumi-rest-connectivity mounted the existing Secret read-only, projected only its two files and had no service-account token. Its same-named source ConfigMap contained only code/lock. The pinned official Linux/amd64 Python image ran Python 3.13.17; nonroot/read-only-root execution used /tmp for dependencies. The Pod had 50m/128Mi requests, 500m/256Mi limits, Never restart and 600s deadline. Initial registry EOF/ImagePullBackOff recovered before client execution; Docker also fetched the same digest successfully, but no image import or changed image was needed. The Pod installed hash-verified wheels and became Ready before the single manual exec of python -m woo_mcp.connectivity. No business read was in a startup/retry loop.

| Transport/auth acceptance | Actual result |
| --- | --- |
| Secret files | Client loaded mounted files; neither credential entered arguments, environment, source or output |
| Service DNS | Explicit in-Pod getaddrinfo succeeded for urumi-wordpress.urumi.svc.cluster.local |
| TCP/HTTP | One GET /wp-json/wc/v3/products to the internal HTTP Service returned 200 |
| Canonical origin/Host | Signed http://store.urumi.test:8080 with identical encoded path/query; Host store.urumi.test:8080 accepted |
| Authentication | OAuthLib HMAC-SHA256 Authorization header supplied; authenticated response supports header delivery/signature acceptance without inspecting the header |
| Redirects/retries | None; following disabled; one intended authenticated business request, no automatic retries |
| Normalized result | id 11; Urumi Demo Mug; SKU URUMI-DEMO-001; price 499; status publish; stock_status instock |

The successful read authenticates the issued credential; it does not exercise write permission. Read/Write scope is user-reported issuance evidence. No raw REST body, OAuth header, credential, customer contact/address or Secret value was displayed. Debug logging is disabled by the diagnostic; the reusable client emits no logs. Immutable Python/library strings cannot be reliably erased. Host configuration/Secret names are not credentials. HTTP/OAuth still does not provide TLS-equivalent confidentiality.

Validation: 13 offline unittest tests passed, covering canonical/query construction, exact library signature integration, Host, required files, no credentials in URLs, redirect rejection, errors/no retries, transport and absolute timeouts, bounds, normalization, malformed responses and sanitized entrypoint errors. Local pip check passed and the Linux Pod installed from the hash lock. Documentation links/anchors/tables, credential/contact-pattern scan and git diff --check passed. These are connectivity checks, not MCP protocol/tool tests.

Post-read supported WordPress/Woo APIs (not additional REST requests) confirmed unique product 11 still published/in stock/499, order 12 still Processing/quantity 1/product 11/499 INR/COD/free_shipping, marker 3, Live options and WooCommerce 11.2.1. Both anonymous pages again returned real content/200. WordPress and MariaDB remained Ready with zero restarts and no visible OOMKilled; MemoryPressure=False. Both PVCs retained original PVs. Diagnostic Pod/ConfigMap were deleted; Secret remained contract-valid, bootstrap unchanged and release still revision 3.

Memory samples: 4.430 GiB host available during the test Pod, node 1251Mi; diagnostic Pod 10Mi, MariaDB 126Mi, WordPress 292Mi at that sample (not peaks). After cleanup: total/used/available host RAM 15.726/11.150/4.577 GiB; node 1242Mi (metrics may lag). This is no full-stack capacity claim.

Next proposed Stage 4.4: implement the accepted five MCP tool schemas/DTOs and SDK /mcp server around this client, including bounded pagination, order PII filtering/date handling, sanitized errors and no automatic write retry; unit/mock/protocol tests first. Real product creation/status updates require separate runtime authorization. Gateway service credential/middleware remain deferred. No staging or commit in Stage 4.3.

## Stage 4.2 accepted Woo MCP design and offline REST Secret helper

The user accepted Stage 4.1 with explicit deferral of gateway-to-upstream service authentication. DEC-026 through DEC-029 and the [architecture contract](architecture.md#accepted-woocommerce-mcp-design) record mcp==2.3.0/Python 3.13/current stateless MCP at /mcp, exactly five tools, normalized PII-minimized DTOs, bounded errors/timeouts/no write replay, and HTTP OAuth via separate Service connection/canonical signing origins. That route is source-informed but not runtime-proven. No application implementation or requirement completion is inferred.

The [dedicated helper](../scripts/setup-woocommerce-rest-secret.ps1) fixes context k3d-urumi-local, namespace urumi, Secret urumi-woocommerce-rest, Opaque type and exact case-sensitive consumer-key/consumer-secret keys. Default Validate is offline. Future Check requires the existing context/Active namespace and projects only object identity/type/lifecycle/key names. Future Create preserves valid existing objects without prompting, or masks each user-supplied Woo-issued value separately and submits a memory-only payload with create -f -. It cannot issue keys, create namespaces or overwrite/rotate/delete Secrets.

Security review: a single bounded ProcessStartInfo wrapper uses non-secret ArgumentList entries, no shell and stdin only for the payload. API timeout 15s, stdin write 10s, process exit 30s and pipe drain 1s are bounded waits, not a single 30s end-to-end deadline. All child stderr and create stdout are discarded; reads expose only the selected projections. Failures print a fixed operation/object message and return nonzero. Real API Secret bytes still reach kubectl internally; no special metadata-only RBAC is claimed. Mutable UTF-8/BSTR buffers are cleared and SecureStrings disposed, but managed plaintext/base64/JSON strings cannot be guaranteed erased. Use an untraced/non-debugged/non-transcribed trusted local terminal.

Offline fixtures exercise parser/manifest generation and the same preparation workflow with fake subprocess/prompt callbacks: missing/present Check, preserved existing Create, absent Create, conflicting contract, failed read, failed create/name race, failed postcheck, missing context/unavailable namespace and invalid first/second input. Manifest fixtures reject wrong identity/API/kind/type, termination, missing/extra/mis-cased/duplicate keys; input-shape fixtures reject blank/NUL/newlines/edge whitespace/oversize text. The real subprocess wrapper's Validate guard is also exercised before process creation. Existing Check deliberately does not decode or verify credential contents/authentication.

| Offline validation on 2026-10-23 | Result |
| --- | --- |
| PowerShell parser | Passed, no syntax errors |
| Default and explicit Validate mode | Both passed 128 assertions; no executable/prompt/cluster access |
| Invalid mode | Rejected with nonzero exit (1) |
| Subprocess/credential-flow review | One ProcessStartInfo wrapper, non-secret arguments, payload only on stdin, suppressed child/error content |
| Credential/contact scan | Seven complete changed/new files; no matching credential/contact material |
| Documentation validation | 10 Markdown files, 108 local links/anchors, 65 tables passed |
| Whitespace and scope | git diff --check clean; new helper whitespace checked separately; exactly seven authorized files, original store helper byte-identical to HEAD |
| PSScriptAnalyzer | Unavailable; not run or installed |

The complete tracked diff and new-file diff were reviewed. Real prompts, Go-template rendering against kubectl, child-process pipe behavior under runtime failure, Secret submission and OAuth connectivity remain untested. A pattern scan cannot prove absence of every possible secret. No runtime completion is claimed.

### Proposed Stage 4.3 operational sequence

1. Obtain separate runtime authorization and fresh host-memory/cluster/store preflight; start the existing cluster only if authorized/needed. Preserve release/PVCs/Secrets/product 11/order 12; do not repeat Stage 3.8.
2. Confirm urumi Active and the existing store healthy, canonical URL unchanged. Run the helper Check; do not dump Secret data.
3. If absent, the user logs into WooCommerce and manually issues one named Read/Write key for the accepted owner. Initial administrator association has broad authority; no service user is silently added.
4. In the user's trusted PowerShell 7 terminal, run pwsh -NoProfile -File scripts/setup-woocommerce-rest-secret.ps1 -Mode Create. Enter consumer key and secret only in its two masked prompts. Do not put them in chat, arguments, environment variables or files.
5. Run Check again; report name/Opaque/exact keys only. Failure/uncertain creation stops for read-only inspection, never deletion/replacement/retry without review.
6. Prepare/review the smallest pinned, bounded authenticated-read harness before execution. Use the accepted internal connection/canonical signing origin and Authorization header, no redirects or key queries; return only non-sensitive product identity/status. A shape-valid Secret alone does not authenticate. Stage 4.2 adds no such harness or Python package.
7. Prove one authenticated read, or stop on signing/redirect/header/connectivity failure before full MCP implementation. No product/order writes or gateway service credential creation belong to that connectivity check. Record sanitized evidence and stop for review.

## Stage 3 store design outcome

Store Architecture v1 is accepted, not implemented. One urumi namespace and one application chart/release will use our own minimal templates and standard images. WordPress is a one-replica Recreate Deployment with a 2 GiB full-webroot PVC at /var/www/html; MariaDB is a one-replica StatefulSet with a separate 5 GiB data PVC at /var/lib/mysql. The store uses ClusterIP/Traefik and store.urumi.test:8080; MariaDB remains internal. External Secrets, a finite idempotent WP-CLI Job, COD checkout, independent liveness/dependency-aware readiness, exact version pins, PVC retention and measured resource budgets are accepted. Exact contracts and digests live in [architecture](architecture.md#accepted-store-architecture-v1).

The design-stage source/registry checks support the selected WordPress 7.1.3/PHP 8.3, WP-CLI 2.12.0, MariaDB 11.4.13 and WooCommerce 11.2.1 set; no image execution, installation, bootstrap, persistence or checkout test has occurred. WordPress core/plugin files persist independently of image changes. One database replica is not HA; retained volumes are not backups or node-loss protection; rollback does not rewind data/files. Namespace deletion is destructive and must not follow the disposable lab's cleanup pattern.

**Memory: PASS for initial Stage 3 deployment attempt; full-stack capacity still unproven.** User-reported accepted figures on 2026-10-12: approximately 15.7 GiB total, 11.6 GiB used and 4.1 GiB available Windows RAM. This narrowly passes the approximately 4 GiB gate and supersedes the stale ~1 GiB blocking conclusion. No fresh measurement was taken for this documentation change.

| Workload | CPU request / limit | Memory request / limit |
| --- | --- | --- |
| WordPress | 250m / 1000m | 512Mi / 1Gi |
| MariaDB | 100m / 500m | 256Mi / 512Mi |
| Bootstrap Job | 100m / 500m | 128Mi / 512Mi |

Keep these starting budgets unchanged. Recheck host memory and Docker/WSL/node capacity immediately before first Helm install. Measure host/node/workload memory during MariaDB startup, WordPress startup, Job execution, normal storefront/admin use and checkout. Stop and tune on OOM kills, unexplained restarts, severe host pressure or insufficient scheduling capacity before adding further Urumi components. A passing gate permits cautious planning for an initial attempt; this step still authorizes documentation only.

Documentation validation: 68 local links/anchors across 10 Markdown files resolve; changed tables, UTF-8/LF, final newlines and Git whitespace checks pass. All requirement/demo matrix rows, the original DOCX checksum, lab manifests and other tracked files are unchanged. Only the five authorized existing Markdown files differ; no staged/untracked files or credential-pattern matches were found. These checks provide no new runtime evidence.

## Stage 3.2 initial Helm chart static validation

Created Chart.yaml, three values files, _helpers.tpl and six resource templates under charts/urumi. No chart dependency, sidecar, custom image, ConfigMap, Namespace, Secret, bootstrap Job or bootstrap script was added. Each environment renders the same six objects in namespace urumi: PersistentVolumeClaim urumi-wordpress; Services urumi-wordpress and urumi-mariadb; Deployment urumi-wordpress; StatefulSet urumi-mariadb; Ingress urumi-wordpress. The future database claim is data-urumi-mariadb-0, generated by the StatefulSet controller rather than Helm rendering.

Shared defaults pin the two approved Linux/amd64 image references, 2 GiB/5 GiB storage, the unchanged CPU/memory budgets and external Secret names. Local values set local-path and store.urumi.test; canonicalUrl is http://store.urumi.test:8080 and remains a value for later bootstrap. Production values use the reserved store.example.invalid hostname, HTTPS, a replace-with-production-tls-secret reference and replace-with-production-storage-class placeholders. They demonstrate configuration structure and are not ready for deployment. Namespace comes from --namespace; the chart does not own/create it.

WordPress uses Recreate with one replica, full-webroot persistence, Secret-file references, startup/liveness TCP checks and an explicitly interim TCP readiness probe. **Replace readiness with the accepted dependency-aware check before installation.** MariaDB uses one replica, a headless internal Service, retained StatefulSet claims, Secret-file references and official healthcheck.sh connection/InnoDB probes. No readiness check or storage behavior was executed.

| Static check | Result and limit |
| --- | --- |
| YAML parsing | Chart/values and all rendered documents parse; duplicate keys rejected. Helm templates are parsed after rendering, not as raw YAML |
| Helm lint | Helm 4.3.0 strict lint passes for shared/local/production values; only informational icon recommendation |
| Helm template | Local and production each render six resources with --namespace urumi --kube-version 1.35.5; no server access |
| Kubernetes schema | Passed against official Kubernetes v1.35.5 OpenAPI definitions, matching the last validated cluster version. Local JSON Schema validation adapts Kubernetes IntOrString format and rejects unknown structured fields; it is not API admission validation |
| Resource relationships | Checked names/namespace, stable selectors versus Pod labels, named Service target ports, Ingress backend, storage mounts/sizes/classes, exact image pins, resource budgets and probes |
| Credential/exposure checks | All sensitive env settings reference projected Secret files, root credentials are DB-only, auth keys are WordPress-only; no Secret objects, plaintext credential env values, public DB Service/Ingress, hostPort or hostNetwork |
| Configuration branches | Alternate release/namespace and DB port render consistently; existingClaim removes the WordPress PVC and reuses the supplied name; enabling TLS without a Secret name correctly fails rendering |

Representative commands (already executed as local/static checks; rendered YAML was held in memory):

```powershell
helm lint charts/urumi --strict --kube-version 1.35.5 -f charts/urumi/values-local.yaml
helm lint charts/urumi --strict --kube-version 1.35.5 -f charts/urumi/values-prod.yaml
helm template urumi charts/urumi --namespace urumi --kube-version 1.35.5 -f charts/urumi/values-local.yaml
helm template urumi charts/urumi --namespace urumi --kube-version 1.35.5 -f charts/urumi/values-prod.yaml
```

The schema source is the [official versioned Kubernetes OpenAPI file](https://github.com/kubernetes/kubernetes/blob/v1.35.5/api/openapi-spec/swagger.json). The [pinned WordPress configuration source](https://github.com/docker-library/wordpress/blob/5ec12a3ef21493a12f3d211e0d69d0c6a30a9794/wp-config-docker.php) and [MariaDB healthcheck source](https://github.com/MariaDB/mariadb-docker/blob/bdfe641466a5312bb97d06a1a4e1fb411c49e6b6/11.4/healthcheck.sh) support the selected file references/probe commands, not runtime success.

Before deployment: implement/review bootstrap and final readiness; prepare the namespace and external Secrets through a separately authorized step; configure the local hosts mapping or real production DNS/TLS/storage; recheck image availability and host/node memory. No memory measurement was taken here; the accepted user-reported ~4.1 GiB gate passes only for an initial attempt, not full-stack capacity. No helm install/upgrade, Kubernetes apply/server dry-run, cluster inspection, image execution or hosts-file edit occurred.

Repository validation passed for all 70 local links/anchors, Markdown tables, UTF-8/LF and whitespace. Exactly eleven requested chart files are new; the index is empty, and no generated render/schema files were saved. Credential-pattern checks of tracked files (including source DOCX text) and new/rendered chart content found no credential values. Nine requirement rows record partial template progress only; obligation text, IDs, source/classification, verification/demo fields and every demo row remain unchanged. Source DOCX checksum and lab files are preserved. The pre-existing decision-register edit is unchanged by Stage 3.2.

## Stage 3.3 bootstrap and readiness static validation

Created store-configmap.yaml, store-bootstrap-job.yaml, bootstrap-wordpress.sh and configure-woocommerce.php. Modified only the WordPress Deployment and shared/local/production values among existing chart files. No Secret helper, public health file, new image, dependency or test scaffold was added. The ConfigMap packages two non-secret files via .Files; the Job consumes the existing WordPress claim and three scoped Secrets. Startup/liveness remain TCP; readiness uses PHP/database/loaded WooCommerce/marker checks with failure-default shutdown and a 5-second kubelet timeout.

The user accepted India (IN), Asia/Kolkata, INR and unrestricted free shipping with COD. The finite Job uses the pinned CLI image, 33:33 filesystem identity, required affinity to WordPress, 120-second separate dependency waits and command bounds, 5-second DB connection/read timeouts, one worker/completion, backoffLimit 1 and a 600-second overall deadline. Requests/limits remain the approved starting budgets. Owner/setting checkpoints distinguish known partial configuration from conflicting/unclaimed stores; no products/orders are created, no users/passwords reset, and mismatched plugin/contracts fail.

| Check | Result and limit |
| --- | --- |
| Shell syntax | Git for Windows Bash -n passed; no bootstrap execution |
| PHP / ShellCheck | Neither executable is available in Windows PATH or Git Bash; PHP syntax (script and inline readiness) and ShellCheck were not run |
| Helm | 4.3.0 strict lint passes for shared/local/production values; informational icon recommendation only |
| Rendering | Local and production each render eight objects: the previous six plus ConfigMap urumi-store-assets-r1 and Job urumi-store-bootstrap-r1; all in namespace urumi |
| YAML/schema | Duplicate-key rejection and offline official Kubernetes v1.35.5 schema validation passed; not API admission testing |
| Static semantics | Selectors/ports/retention/pins/budgets, ConfigMap file equality, Secret projections, Job affinity/shared claim/33:33 identity, bounded waits and positive readiness checks passed |
| Configuration cases | Alternate release/namespace/DB port, existing WordPress claim reuse and missing TLS reference rejection passed |
| Pins | Registry metadata resolved all three approved tags to the accepted Linux/amd64 digests; WooCommerce 11.2.1 archive downloaded in memory and matched its approved SHA-256/header; no image layers pulled/executed |
| Safety | No Secret objects/public DB or Job endpoint; credential-pattern scan passed. Reviewed no xtrace, broad deletion, direct SQL mutation, resets, automatic version changes or product/order creation |
| Helm lifecycle | Reviewed pinned Helm upgrade/client/rollback source: new revision targets precede obsolete-resource deletion; rollback reuses historical manifests. No install/upgrade/rollback was executed |

The script uses only read-only SELECT 1 / SHOW TABLES for dependency/freshness checks; state changes use WordPress/WooCommerce APIs. Admin password is read by WP-CLI from the mounted Secret through stdin. Raw command output from sensitive install/activation steps is hidden, but nonzero status and named phase errors remain visible. PHP actions must return an explicit success acknowledgement; readiness defaults to nonzero even if WordPress exits zero early.

Limits: a crash after initial core installation but before the ownership option, partially installed core/plugin files, an unclaimed store or changed contract requires deliberate review; no destructive automatic repair. Complete/stop the previous Job before another release operation because revision naming is not a lock. Rollback may recreate a missing historical Job or preserve a terminal one, and never restores data/files. The [architecture](architecture.md#helm-job-upgrade-and-rollback-contract) records evidence and recovery boundaries.

Before deployment: obtain PHP syntax evidence, review non-secret admin/configuration placeholders, create the external namespace/Secrets via a later authorized step, configure hosts or real DNS/TLS/storage and recheck RAM/node capacity. Runtime work still includes fresh/partial/completed reruns, ownership/permissions, dependency-loss/readiness, Job timeout/failure, checkout, Pod replacement, retention and upgrade/rollback. Measure host/node/workload memory through startup, bootstrap and use. No new RAM measurement or full-stack capacity claim is made.

## Stage 3.4 local store Secret helper validation

Created [setup-store-secrets.ps1](../scripts/setup-store-secrets.ps1), requiring installed PowerShell 7. Validate defaults to offline fixtures/disposable RNG samples; Check reads the fixed context/namespace/Secret contracts; Create is explicit and creates missing objects only after full preflight. Only Validate/default and in-memory substituted workflows were exercised. No real project credential was generated or retained, and no actual kubectl/Helm command was run.

| Check | Result and limit |
| --- | --- |
| Syntax and entrypoint | PowerShell 7.6.5 parser, default Validate, explicit Validate and invalid-mode rejection pass |
| Offline contracts | Four valid manifest fixtures, 28 invalid Secret fixtures and six invalid text inputs; disposable 32/64-byte RNG samples pass |
| Mocked workflows | 12 cases pass: Check present/absent, Create preservation/creation, missing context/namespace, terminating namespace, invalid final Secret, lookup/JSON failure, concurrent create and partial creation failure |
| Subprocess boundary | Harmless local PowerShell child echoes a non-secret fixture to both streams; create-path output is suppressed for success/failure, read output stays captured. Fixed kubectl argument separation checked independently |
| Chart alignment | Exactly four names and eleven keys match the existing chart projections; chart not modified or rendered |
| Repository safety | Credential-pattern scan including original DOCX text and new script passes; whitespace checks pass; no payload/temp/test files added |
| Static analyzer | PSScriptAnalyzer unavailable; not installed or run |

Validation found and corrected strict-mode access to an absent optional field, fixed-flag concatenation and an unintended .NET task result in the output pipeline. All listed cases pass after correction. Mock evidence is not API, RBAC, interactive-password or runtime Secret evidence.

Existing Secrets are preserved; inconsistent keys/type/text require explicit repair. Random generation occurs only for absent DB/auth values in future Create execution; the admin password uses masked input. JSON/base64 data stay in process memory and stdin, never command arguments or files; child stderr and exception payloads are suppressed. Creation is not transactional across four objects: failures may leave already-created Secrets, and retries must inspect/preserve them. Managed strings cannot be guaranteed erased; retained-data credentials must be recovered rather than regenerated blindly.

Next boundary: review this helper before separately authorizing namespace preparation, read-only Check and interactive creation. WooCommerce REST credentials remain deferred until WooCommerce is live. PHP syntax checking, memory recheck, deployment and every store runtime demonstration remain incomplete.

## Stage 3.5 local environment preparation

### Initial preparation and manual handoff

Fresh preflight on 2026-10-20 began from clean main at 0cee761. The user revised the host operating gate: approximately 4 GiB available preferred; approximately 3.8 GiB accepted for a cautious initial deployment path; 3.5–3.8 GiB permits only preparation that does not materially increase memory usage; below approximately 3.5 GiB stops preparation. Recheck before application deployment. Resource budgets, probes, persistence and required system components remain unchanged. Earlier design-stage RAM readings above are historical, not current capacity evidence.

| Observation | Actual result |
| --- | --- |
| Windows RAM | Initial total/used/available: 15.726 / 12.193 / 3.533 GiB; final: 15.726 / 12.048 / 3.678 GiB. Preparation-only band; no application deployment |
| Docker and k3d | Engine 29.9.1 reachable in Linux mode, desktop-linux context; urumi-local server 1/1 with load balancer |
| Kubernetes | Explicit/current context k3d-urumi-local; node k3d-urumi-local-server-0 Ready, v1.35.5+k3s1, MemoryPressure False |
| Node memory | Allocatable 6064276Ki (about 5.78 GiB); usage 602Mi initially, 606Mi finally (10%). Allocatable differs from the prior run; this step did not change runtime limits |
| System health and ports | Traefik, CoreDNS, metrics-server and local-path-provisioner each 1/1 Ready at both checks; load balancer maps host 8080 to 80, 8443 to 443, and 127.0.0.1:6550 to 6443 |
| Namespace | urumi was absent; created directly with kubectl and verified Active. Outside Helm ownership; no application resources added |
| Hostname | No active hosts entry and Windows resolver could not resolve store.urumi.test. Append attempt denied by Windows permissions; file unchanged. Handed off for manual elevated edit |
| Secret Check | Committed helper Check completed against the live cluster: urumi-mariadb-root, urumi-store-db, urumi-wordpress-admin and urumi-wordpress-auth all absent. Type/key verification deferred until creation |
| Release/workload boundary | No Ingress objects or Urumi application workloads. Only system traefik and traefik-crd Helm releases exist |

The initial run stopped before Create because this tool session does not provide a user-controlled masked password prompt. The user was given the committed helper command for a local PowerShell 7 terminal, with admin input only at its masked prompt, and the exact hosts entry `127.0.0.1 store.urumi.test`. No project credential generation or Secret submission occurred in that agent run.

### Post-create verification

The user reported completing the hosts edit and the committed helper's Create followed by Check from their own PowerShell 7 terminal using masked admin-password entry. The resumed agent run made no environment or Secret changes. It did not rerun helper Check, which internally retrieves and decodes credential text; instead, kubectl Go-template output was restricted to Secret identity, type, lifecycle and key names. No full Secret YAML/JSON, encoded values, plaintext credentials or stdin payloads were output or decoded.

| Secret | Type | Required key-name verification |
| --- | --- | --- |
| urumi-mariadb-root | Opaque | Exact one-key set: root-password |
| urumi-store-db | Opaque | Exact one-key set: password |
| urumi-wordpress-admin | Opaque | Exact one-key set: admin-password |
| urumi-wordpress-auth | Opaque | Exact eight-key set: auth-key, secure-auth-key, logged-in-key, nonce-key, auth-salt, secure-auth-salt, logged-in-salt, nonce-salt |

All four objects exist in urumi, are not terminating, and have no extra or mis-cased keys. These independent checks verify structure only; the user's local helper Check is the reported evidence for credential-text validation. Authentication and workload consumption remain untested.

Windows resolves store.urumi.test to exactly 127.0.0.1 and namespace urumi remains Active. Docker 29.9.1/Linux, urumi-local and context k3d-urumi-local are healthy. Node k3d-urumi-local-server-0 is Ready on v1.35.5+k3s1 with MemoryPressure False, 6064276Ki allocatable (about 5.78 GiB) and 612Mi current usage (10%). Traefik, CoreDNS, metrics-server and local-path-provisioner each remain 1/1 Ready; ports 8080/8443/6550 retain their mappings.

Fresh Windows total/used/available RAM is **15.726 / 12.354 / 3.372 GiB**. Environment preparation is verified, but this reading is below the approximately 3.5 GiB deployment floor: **do not deploy**. Recheck headroom before any later application deployment; keep approved budgets, probes, persistence and required infrastructure unchanged.

Only system traefik and traefik-crd Helm releases exist; no Ingress objects or WordPress/MariaDB/Urumi application workloads exist. No Helm install, Secret recreation/modification, hosts edit or WooCommerce REST credential creation occurred in this verification run. Stop for review. PHP syntax and all store runtime requirements remain unverified.

## Stage 3.6 first live store deployment

Started from clean main at 11b24f2 on 2026-10-20. The chart, helper, image pins and resource budgets were unchanged. Initial sandbox access to Windows CIM/local Kubernetes was denied; approved escalation allowed the authorized checks and deployment. No infrastructure-health conclusion was drawn from sandbox errors.

Preflight confirmed Docker 29.9.1/Linux, urumi-local, current/explicit context k3d-urumi-local, Ready v1.35.5+k3s1 node with MemoryPressure False, all four required system Deployments healthy, urumi Active, correct hostname/ports and four exact Opaque Secret key sets. No project release, workloads, Ingress or PVCs existed. Secret output contained only identity/type/key names. local-path uses WaitForFirstConsumer and Delete reclaim policy.

Helm 4.3.0 strict local lint passed (informational icon recommendation only). The exact local rendering passed duplicate-key, inventory, namespace, selector/port, retention, pinned-image, unchanged-budget, probe, Job-affinity/deadline and ConfigMap-asset checks. API-server strict dry-run accepted all eight objects without persisting them. No Namespace or Secret object rendered; MariaDB had no public exposure.

```powershell
helm template urumi charts/urumi --namespace urumi --kube-context k3d-urumi-local --kube-version 1.35.5 --values charts/urumi/values-local.yaml
helm install urumi charts/urumi --namespace urumi --kube-context k3d-urumi-local --values charts/urumi/values-local.yaml --wait=watcher --wait-for-jobs --timeout 15m
```

Installation was conditional on an immediate fresh memory check: total/used/available 15.726 / 11.728 / 3.998 GiB, passing the accepted approximately 3.8 GiB attempt threshold. Helm waited in an observed background process; no atomic/rollback-on-failure flag was used. It exited successfully with release urumi, namespace urumi, revision 1, status deployed. No upgrade, rollback or uninstall occurred.

| Rendered resource | Live result |
| --- | --- |
| ConfigMap urumi-store-assets-r1 | Immutable, two authored script assets |
| Job urumi-store-bootstrap-r1 | Complete, 1/1, duration 2m38s; 600-second deadline and backoffLimit 1 |
| Deployment urumi-wordpress | One desired/current/ready replica, Recreate |
| StatefulSet urumi-mariadb | One desired/current/ready replica; generated data-urumi-mariadb-0 |
| Service urumi-wordpress | ClusterIP 10.43.241.167, port 80; ready backend 10.42.0.59 |
| Service urumi-mariadb | Headless ClusterIP, port 3306; backend 10.42.0.60; no external IP, NodePort or host network |
| PVC urumi-wordpress | Bound, 2Gi RWO/local-path; Helm keep annotation present |
| Ingress urumi-wordpress | Traefik, store.urumi.test, path / to WordPress Service port 80 |

| Pod | Observed final state |
| --- | --- |
| urumi-wordpress-7cfddbc665-rnlxl | Running, 1/1 Ready, started, zero restarts |
| urumi-mariadb-0 | Running, 1/1 Ready, started, zero restarts |
| urumi-store-bootstrap-r1-wkff8 | Succeeded/Completed, exit 0, zero restarts; 0/1 Ready is normal for the finished Job |

Both claims are Bound: urumi-wordpress maps to PV pvc-864a302a-0a39-4880-b522-558a4c830845 (2Gi), and controller-generated data-urumi-mariadb-0 maps to PV pvc-d3e6142a-b6b9-4e67-8880-a564f41ba331 (5Gi). Both PVs have Delete reclaim policy. StatefulSet whenDeleted/whenScaled remain Retain; WordPress retains its Helm keep annotation. Binding and configuration do not prove backup, deletion safety or node-loss durability; no persistence deletion test was performed.

Observed sequence: PVCs waited for consumers, provisioned/bound, and all three Pods scheduled on k3d-urumi-local-server-0. Initial image pulls hit Docker image-CDN EOF errors and ImagePullBackOff; normal Kubernetes retries recovered without image changes or manual pull workarounds. MariaDB became Ready first. Its two early startup-probe socket failures resolved during initialization, without restart. WordPress readiness initially failed before bootstrap completion, then passed. One AlreadyMountedVolume warning reported requested fsGroup 33 versus existing volume GID 0 on the shared WordPress claim; the Job nevertheless completed, and no permissions were changed. The warning remains an observation, not proof of portability across other storage/node setups.

Live images, probes and resource quantities match the committed chart. An initial exact-string resource comparison failed because Kubernetes canonicalized WordPress CPU limit 1000m to 1; numeric quantity comparison passed, with no chart/resource change. MariaDB uses official healthcheck.sh startup/readiness (--connect --innodb_initialized) and liveness (--connect). WordPress startup/liveness remain TCP-only and database-independent by configuration; database-loss fault injection was not performed. WordPress final PHP readiness passed with installed WordPress, successful database access, active/loaded WooCommerce 11.2.1 and bootstrap marker 1.

Bootstrap logs were captured through an exact allowlist of authored non-secret messages. They showed authenticated DB access, confirmed empty database, WordPress installation, exact WooCommerce archive download/verification, configuration verification, and ended with `Bootstrap verified successfully.` No unrecognized lines were present. Together with Job Complete and WordPress Ready, this supports the pinned WooCommerce activation/version, completion marker and verified IN/Asia-Kolkata/INR/free-shipping/COD configuration. No admin password, database credential, salt or Secret payload was displayed.

PHP syntax validation used the already deployed pinned WordPress container:

```text
kubectl --context=k3d-urumi-local --namespace=urumi --request-timeout=15s exec -i deployment/urumi-wordpress -c wordpress -- php -l /dev/stdin
```

Python supplied the exact local configure-woocommerce.php bytes on stdin; a second invocation supplied the rendered inline readiness PHP with an opening PHP tag. Both exited 0 with `No syntax errors detected in /dev/stdin`. This parsed code without executing it or writing persistent files. No Windows PHP installation occurred. Syntax evidence was obtained after deployment as authorized for Stage 3.6; it was not available at the earlier static milestones.

Basic unauthenticated HTTP requests returned 200 for http://store.urumi.test:8080/ and /shop/, both with title Urumi Demo Store and WordPress/WooCommerce HTML. /wp-admin/ redirected to wp-login.php and returned the login form with HTTP 200. No admin login or password entry occurred. Only WordPress has an Ingress; MariaDB remains internal.

| Runtime snapshot | Windows available RAM | Node current memory |
| --- | --- | --- |
| Initial preflight | 4.033 GiB | 624Mi (10%) |
| Immediately before install | 3.998 GiB | Not resampled at this instant |
| Resources scheduled/image pulls | 3.821 GiB | 677Mi (11%) |
| MariaDB Ready, other images retrying | 3.052 GiB | 856Mi (14%) |
| WordPress/bootstrap containers Running | 1.797 GiB | 902Mi (15%) |
| Job Complete, WordPress Ready | 2.309 GiB | 1016Mi (17%) |
| Subsequent ready-state sample | 2.283 GiB | 1104Mi (18%) |
| After basic HTTP checks | 3.966 GiB | 937Mi (15%) |

Final Windows total/used/available was 15.726 / 11.761 / 3.966 GiB; node allocatable remained 6064276Ki (about 5.78 GiB). Final workload samples were MariaDB 100Mi and WordPress 58Mi. The fast bootstrap's individual Pod memory was not captured before completion; snapshots are not measured peaks. Application restarts stayed zero, no OOMKilled termination was observed, MemoryPressure stayed False, and required system Deployments remained 1/1 Ready. The transient host-memory dip does not establish full-stack capacity: retain budgets and remeasure before additional runtime work/components.

Remaining runtime work: manual admin login, approved demo products/checkout/order verification, memory during admin use/checkout, persistence across Pod replacement, dependency-failure probe behavior, safe bootstrap rerun/recovery and retained-claim reuse. Any later upgrade/rollback exercise needs separate review and release serialization; none occurred here. No demo product/order or WooCommerce REST credential was created, and MCP implementation has not begun. Stop at this successful first-deployment boundary; leave release and persistent state running/intact.

## Stage 3.7 business-flow acceptance — awaiting manual checkout

Started on 2026-10-20 from clean main at 5ef62e0. No Helm values, release, Kubernetes resources, Secrets or persistent claims were changed. The only intended application-data mutation was the requested demo product, using WooCommerce CRUD in the existing WordPress PHP container.

Preflight confirmed context k3d-urumi-local, Helm urumi revision 1 deployed, WordPress/MariaDB 1/1 Ready, bootstrap Job Complete (recorded duration 2m38s), zero container restarts, Ready node and MemoryPressure False. Homepage and /shop/ returned HTTP 200; the stronger catalog-content check below subsequently failed.

Non-sensitive PHP inspection loaded WordPress with cron spawning disabled, suppressed raw diagnostics and returned only selected business fields. It verified active WooCommerce 11.2.1, currency INR, country IN, timezone Asia/Kolkata, taxes disabled and guest checkout enabled. COD is enabled with no shipping-method restriction. There are no custom shipping zones; fallback zone 0 has exactly one enabled free_shipping method (instance 1) with no minimum/coupon requirement. Shipping is unrestricted under the accepted demo baseline.

Before creation, wc_get_product_id_by_sku and wc_get_products found no URUMI-DEMO-001. A second lookup immediately before saving again guarded against duplicates. WC_Product_Simple setters and save created exactly one product; a subsequent SKU query returned only ID 11. No direct SQL mutation, REST credential or admin login was used.

| Product field | Observed value |
| --- | --- |
| ID / name | 11 / Urumi Demo Mug |
| SKU / type | URUMI-DEMO-001 / simple |
| Regular and current price | 499 INR |
| Status / stock | publish / instock |
| Catalog visibility / purchasable | visible / true |
| Physical shipping | Required |
| Public URL | http://store.urumi.test:8080/?product=urumi-demo-mug |

The product page returned 200 and contained the name, SKU, ₹499.00 and Add to cart control. The public WooCommerce Store API returned product 11 with is_purchasable=true, is_in_stock=true, INR and price 49900 with two minor digits (₹499.00). The generated product archive at http://store.urumi.test:8080/?post_type=product returned 200 and displayed the single demo product, its price and Add to cart. These are HTTP/HTML/API observations, not a rendered-browser or completed cart/checkout test.

**Failed acceptance check:** http://store.urumi.test:8080/shop/ returned 200 but showed the WordPress blog/Hello world post, without the product, price or Add to cart. Inspection found an empty permalink_structure (plain permalinks), published shop page 5 with slug shop, generated shop URL http://store.urumi.test:8080/?page_id=5 and the working query-string archive above. The bootstrap does not establish pretty permalinks. This explains why the requested /shop/ route is not a validated catalog; its earlier Stage 3.6 HTTP 200 observation remains true but was insufficient evidence. No permalink/rewrite/bootstrap change was made. The initial content assertion correctly failed; a separate Windows console Unicode-output failure was resolved by escaping display output, without changing the store.

The WooCommerce order baseline at 16:09:11 +05:30 was zero orders across registered order statuses and zero checkout drafts. After product creation, a read-only order query still returned zero. No cart submission or order was created by the agent. The user must complete one guest checkout through the verified product page using synthetic details, quantity 1, free shipping and COD, then privately log in and inspect WooCommerce > Orders. Expected total is ₹499.00; the expected physical-product COD status is Processing, which is not yet observed. Report only the order ID and success/failure, without customer details, credentials or an order URL containing its access key. Verify the new order through supported WooCommerce APIs after that handoff and recheck health/memory during/after checkout. The /shop/ routing acceptance issue remains open independently.

| Memory snapshot | Windows total / used / available GiB | Node usage | MariaDB / WordPress |
| --- | --- | --- | --- |
| Preflight | 15.726 / 11.985 / 3.741 | 1020Mi (17%) | 101Mi / 128Mi |
| After product creation | 15.726 / 11.997 / 3.729 | 1032Mi (17%) | 101Mi / 139Mi |
| Before manual checkout handoff | 15.726 / 11.986 / 3.740 | 1066Mi (18%) | 102Mi / 173Mi |

Node allocatable remained 6064276Ki (about 5.78 GiB). At handoff both application Pods were Ready, all three Pod restart counts were zero, no OOMKilled/previous termination appeared in container status, bootstrap remained Complete and MemoryPressure was False. Homepage and /shop/ still returned 200, with the known /shop/ content failure. These samples precede checkout and do not demonstrate checkout peaks or full-stack capacity.

Stage 3.7 is not complete: /shop/ catalog routing, browser checkout, one-order verification, admin visibility and post-checkout health remain pending. Persistence deletion/recovery and dependency-loss testing remain incomplete. No Helm operation, Pod/PVC deletion, Secret mutation, WooCommerce REST credentials, MCP implementation, staging or commit occurred. Only progress/journey documentation changes accompany this partial runtime evidence.

### Stage 3.7 permalink correction — static review only

The user paused checkout to repair the source of truth instead of changing only live options. The previous progress/journey edits remain in the worktree. Current deployed data still includes product 11 and zero placed orders; this step does not perform application configuration or business mutations.

The old code accepted only an exact contract and marker match. A new Helm Job with unchanged version 1 would verify existing settings, not add permalinks; changing only the expected version would fail preflight. Version 2 now explicitly recognizes a matching completed version-1 store, validates all existing settings, applies /%postname%/ with the official WP-CLI hard flush, and verifies persisted shop/product routing and Apache directives before advancing ownership and marker. Interrupted old/target states are recognized; unrelated settings/versions are rejected. No WordPress/WooCommerce reinstall, product creation, credential reset or volume replacement is part of the migration.

Source changes are limited to bootstrap-wordpress.sh (Apache CLI context and bounded rewrite/finalize sequence), configure-woocommerce.php (migration guards, verification and marker-last completion), shared values.yaml (bootstrap version 2) and WordPress readiness (target permalink check). Job/ConfigMap templates and both environment values files remain unchanged. The new tests/store/bootstrap-migration.php fixture checks actual function declarations with stubbed WordPress APIs and options in memory; it never executes the bootstrap entrypoint or loads WordPress/database state.

Read-only inspection of the existing pinned Apache container confirmed rewrite_module, AllowOverride All and shared-PVC webroot/.htaccess permissions 33:33 with modes 755/644. The Job's existing identity can support the planned writes. PHP syntax was checked by sending source to php -n -l /dev/stdin in that existing container; shell syntax used sh -n on stdin. The isolated fixture also ran there without loading WordPress or writing files/options. This is validation process execution, not a bootstrap rerun or live migration.

| Validation | Result / limit |
| --- | --- |
| Shell syntax | Passed sh -n; orchestrator not executed |
| PHP syntax | Configurator, fixture and local/production inline readiness passed php -n -l |
| Isolated migration fixtures | 50 assertions passed: preserved settings/data sentinels, idempotency, drift/refusal, missing DB/rules, failed Apache persistence, interrupted completion, fresh-v2 completion and product-structure normalization |
| Helm | Strict local/production lint passed; icon recommendation is informational |
| Render/schema | Eight expected resources per environment; all 16 validated against upstream Kubernetes v1.35.5 OpenAPI schemas |
| Structural checks | Duplicate keys, selectors, named ports, mounts, affinity, bounds, retention and exact Secret references checked; no Secret/Namespace object or public MariaDB |
| Repository checks | Credential scans of changed/new files and renders passed; 51 local links/anchors, 30 Markdown tables and git diff --check passed; index empty |
| Runtime boundary | No Helm install/upgrade/rollback, bootstrap execution, permalink change, checkout, Secret mutation or resource deletion; migration HTTP behavior remains untested |

Final source review found WordPress's internal product structure may omit a leading slash. The verifier now normalizes boundary slashes and fixtures cover both representations plus rejection of another product base. PHP/fixture validation and both lint/render/schema checks passed again after that correction.

Future reviewed upgrade: recheck memory/health and terminal old Jobs, serialize release operations, then upgrade urumi using the same chart/local values and bounded watcher/Job wait without automatic rollback. Revision 2 creates r2 Job/assets and replaces the Recreate WordPress Pod using its current claim; new readiness waits for marker 2. The bootstrap Job can run while WordPress is unready because affinity uses labels/node, not readiness. Verify Job success, marker/readiness, unchanged product 11/SKU, real /shop/ content and /product/urumi-demo-mug/ before resuming checkout. Preserve both claims and database throughout.

If migration fails, retain diagnostics/data and inspect the old/target option/file states before retrying. Contract and marker writes are ordered but not atomic with rewrite persistence. After marker 2, the old revision's marker-1 readiness will fail; Helm rollback cannot rewind persisted options/.htaccess and must not be automatic. See [DEC-024](decisions.md#dec-024-deterministic-permalinks-and-a-recognized-bootstrap-migration) and the [migration lifecycle](architecture.md#stage-37-deterministic-permalinks-and-explicit-v1-to-v2-migration). Stop for source/static review; no runtime migration is authorized in this step.

### Stage 3.7B controlled migration — initial memory-gate stop

Attempted on 2026-10-20 from clean main at b87d9cf. The approved source and static checks are committed; runtime execution remains gated by fresh host headroom.

| Pre-upgrade check | Actual observation |
| --- | --- |
| Windows total / used / available RAM | 15.726 / 12.763 / 2.963 GiB; below the approximately 3.5 GiB stop threshold |
| Docker / k3d / context | Engine 29.9.1, Linux; urumi-local server 1/1 and load balancer present; current context k3d-urumi-local |
| Kubernetes node | Ready=True, MemoryPressure=False; allocatable 6064276Ki, usage 1078Mi (18%) |
| System Deployments | Traefik, CoreDNS, metrics-server and local-path-provisioner each 1/1 Ready |
| Helm / applications | urumi revision 1 deployed; WordPress Deployment and MariaDB StatefulSet each 1/1 Ready |
| Bootstrap serialization | urumi-store-bootstrap-r1 Complete, 1/1, recorded duration 2m38s; its only Pod Succeeded, with no deletion timestamp; no running or terminating bootstrap Pod |
| Restarts / termination state | Zero restarts across the two application Pods and completed bootstrap Pod; no OOMKilled or previous termination reason visible |
| Persistent claims | urumi-wordpress 2Gi and data-urumi-mariadb-0 5Gi both Bound on local-path |
| Hostname | store.urumi.test resolved to 127.0.0.1 |

Stopped before release preview or Helm upgrade. No application PHP inspection, product/order recount, marker/ownership verification, HTTP routing acceptance or idempotency runtime check was performed after the failed memory gate. Product 11 and the zero-order baseline remain prior evidence; preservation through migration is not yet tested. No Secret values were retrieved, and no resources, credentials or persistent application state were changed.

Recover host headroom, then repeat the complete pre-upgrade gate immediately before the authorized command. Keep resource budgets, probes and persistence unchanged. Runtime work must still verify the recognized v1-to-v2 migration, product preservation, real catalog/product contents, marker/readiness and health before checkout resumes. Revision-1 rollback cannot restore persisted options/files and is not an automatic recovery path after marker 2. Checkout, persistence and dependency-loss tests remain incomplete.

### Stage 3.7B resumed migration — runtime acceptance passed

Resumed on 2026-10-20 after the user recovered host memory. The preceding stopped attempt remains historical evidence. Only its two operational documentation files were dirty; chart/test source still matched b87d9cf.

**Gate and preview:** Windows total/used/available RAM was 15.726 / 11.556 / 4.170 GiB. Docker/Linux, k3d, context, node, four system Deployments, hostname and both application workloads passed again. The revision-1 bootstrap Job was terminal, with no Running or Terminating bootstrap Pod. Read-only WooCommerce inspection confirmed exact matching v1 ownership/settings, marker 1, Plain permalinks, active WooCommerce 11.2.1, the sole matching product 11 at 499 INR and zero orders/checkout drafts. User identity/registration metadata was captured without password fields.

The server dry-run rendered revision 2 without persisting it. Its eight resources were ConfigMap urumi-store-assets-r2, Job urumi-store-bootstrap-r2, Deployment urumi-wordpress, StatefulSet urumi-mariadb, Services urumi-wordpress/urumi-mariadb, PVC urumi-wordpress and Ingress urumi-wordpress. Manifest comparison found only approved asset content, revision-specific names/references, expected bootstrap version 2 and the permalink readiness condition changed. StatefulSet, both Services, Ingress and explicit PVC were identical. Both retention policies remained present; no Secret/Namespace object or public MariaDB exposure appeared. Product/order/user data is not represented as a Helm resource.

Fresh RAM immediately before execution was 4.149 GiB available. Ran exactly once, without automatic rollback:

```powershell
helm upgrade urumi charts/urumi --namespace urumi --kube-context k3d-urumi-local --values charts/urumi/values-local.yaml --wait=watcher --wait-for-jobs --timeout 15m
```

Helm returned exit 0, revision 2, deployed, at 21:31:51 +05:30. The Pod watch captured the old WordPress Pod terminating; the r2 bootstrap Pod becoming Pending, scheduled, ContainerCreating and Running; and the replacement WordPress Pod becoming Pending, ContainerCreating, Running/unready, then Ready. The Job reached Complete in 11s with exit 0. Events recorded one readiness failure without diagnostic output during startup; it resolved, with no liveness failure reported for the replacement Pod. MariaDB's Pod UID stayed unchanged and it remained Ready.

Allowlisted Job logs confirmed the existing-installation preserve-users/passwords branch, deterministic permalink/hard-flush step and final "Bootstrap verified successfully." No install/reset/download branch was reported. WordPress changed from urumi-wordpress-7cfddbc665-rnlxl to urumi-wordpress-5cbc5bb6b8-l4zcs. The completed Job Pod is urumi-store-bootstrap-r2-x8wgm; the old revision-specific Job/assets were removed by Helm reconciliation. Both existing claims stayed Bound to the same PVs (2Gi WordPress, 5Gi MariaDB); PV reclaim policy remains Delete, so retention is still not backup or protection against direct deletion.

| Runtime acceptance | Observed result |
| --- | --- |
| /shop/ | HTTP 200; title Shop - Urumi Demo Store; WooCommerce product-archive/shop body classes; Urumi Demo Mug, INR price and Add to cart; no Hello world blog content |
| /product/urumi-demo-mug/ | HTTP 200; single-product/postid-11 page, correct SKU, 499 INR and Add to cart |
| Query-style product URL | Still HTTP 200 with product 11; normal path is now independently verified |
| Product preservation | ID 11, URUMI-DEMO-001, regular/current price 499 INR, publish, instock; exactly one SKU match |
| Orders | Zero registered-status orders and zero checkout drafts before and after; no checkout performed |
| Users/passwords | Same sole user ID and registration timestamp; preserve branch and source contain no password-reset operation on this path. No password/hash field inspected and no login test performed |
| WooCommerce | 11.2.1 active |
| Completed bootstrap | Exact v2 ownership, marker 2 and /%postname%/; existing settings, persisted shop/product rewrite rules and Apache managed block verified |
| Final readiness | Exact live WordPress readiness command exited 0; WordPress/MariaDB each 1/1 Ready |

Completed-state verification loaded the committed function declarations without the bootstrap entrypoint, required exact owner/marker 2 first, then used the completed-settings verification branch and rewrite verifier. It did not call finalize, completion writes, rewrite flush or the full bootstrap. Together with the previously passing 50 isolated assertions, this shows completed v2 is recognized and verifies; it is not a second live Job/rerun or exhaustive failure-recovery test.

| Memory snapshot | Windows total / used / available GiB | Node usage | MariaDB / WordPress |
| --- | --- | --- | --- |
| Resumed preflight | 15.726 / 11.556 / 4.170 | 1068Mi (18%) | Not sampled |
| Immediately before upgrade | 15.726 / 11.577 / 4.149 | Not resampled | Not sampled |
| After fast Job completion | 15.726 / 11.682 / 4.045 | 1021Mi (17%) | 101Mi / 16Mi |
| After acceptance checks | 15.726 / 11.771 / 3.955 | 1030Mi (17%) | 102Mi / 115Mi |

Node allocatable remained 6064276Ki. All observed application/Job restart counts were zero; no OOMKilled/previous termination was visible and MemoryPressure stayed False. The 11-second Job finished before a per-Job memory sample was captured; these snapshots are not peaks or full-stack capacity proof.

The Plain-permalink defect was corrected through committed bootstrap migration, not manual live settings. Checkout, user-controlled admin/order visibility, checkout memory and deliberate persistence/dependency-loss tests remain pending. Do not automatically roll back: revision-1 readiness expects marker 1, while Helm rollback cannot restore current database options or persisted .htaccess. No Secrets, passwords, product/order data or resource budgets were changed by the agent outside the approved migration. Stop for runtime review; no further upgrade, checkout, staging or commit.

### Stage 3.7 order verification — business flow passed, public visibility pending

Verified on 2026-10-21 from clean main at 5670cd3 after the user reported exactly one manual guest checkout with synthetic details and personally confirmed the order in WooCommerce administration. The agent did not log in, submit another checkout, alter the order or use REST credentials.

Supported wc_get_orders, WC_Order and order-item getters returned only selected non-sensitive evidence. There is exactly one shop order across registered statuses/trash and zero checkout drafts. Guest checkout is confirmed by the guest account association; no customer identity/contact fields were emitted. Product 11 remains the sole URUMI-DEMO-001 match, published, in stock, catalog-visible and purchasable.

| Order evidence | Observed value |
| --- | --- |
| Order ID | 12 |
| Created, store timezone | 2026-10-21 07:54:15 +05:30 (Asia/Kolkata) |
| Created, UTC | 2026-10-21 02:24:15Z |
| Actual WooCommerce status | processing (Processing); checkout submission is complete, not the order's fulfillment status |
| Payment | cod (Cash on Delivery) |
| Product / SKU | 11 / URUMI-DEMO-001 |
| Quantity / unit price | 1 / 499 INR |
| Line total / order total | 499 INR / 499.00 INR |
| Shipping | free_shipping, instance 1, charge 0 INR |
| Admin visibility | User personally confirmed WooCommerce > Orders; no agent admin login |

The initial inspection used WC_DateTime::date('c'), which formats an offset-adjusted timestamp with gmdate and misleadingly labels it +00:00. Rechecking the native date format and timestamp converted through wp_timezone confirmed 07:54:15 +05:30 / 02:24:15Z above. No stored timestamp was changed.

**Current presentation failure:** Homepage, /shop/ and /product/urumi-demo-mug/ return HTTP 200. Shop/product body classes still identify the correct WooCommerce routes, so this is not evidence that Plain permalinks returned. But anonymous visible body text on both store routes says the store is in the works and will launch soon; no product listing or usable Add to cart appears there. Read-only options are woocommerce_coming_soon=yes and woocommerce_store_pages_only=yes. Product 11 remains available through the public Store API and supported product getters. These visibility options are not managed by the current chart/bootstrap; their change time/cause is not established. Do not attribute them to checkout or a user action without evidence.

The shop content assertion failed. A weaker product string assertion initially passed because embedded script data contained the product details; parsing visible body text with scripts/styles excluded exposed the same pre-launch presentation. This reinforces that HTTP status, page classes, metadata and backend purchasability alone do not prove visitor-facing storefront acceptance. Historical Stage 3.7B observations remain recorded; this is the current stronger content check. No live setting or source repair was attempted in this verification step.

| Stage 3.7 criterion | Result / evidence |
| --- | --- |
| Deterministic business settings | Pass: WooCommerce 11.2.1 active, IN, Asia/Kolkata, INR, taxes off, guest checkout/COD on, unrestricted fallback free-shipping method 1 |
| Permalink route resolution | Pass: marker 2, /%postname%/, shop product-archive and product-11 route classes |
| Demo product creation/preservation | Pass: exactly one published/in-stock product 11 with the agreed SKU and price |
| Anonymous catalog/product visibility | Fail: coming-soon presentation hides the storefront; resolve before final acceptance |
| Guest checkout, free shipping, COD | Pass: user performed once; supported APIs verify the resulting guest order and line/shipping/payment data |
| Stored order and admin visibility | Pass: one stored order 12; admin visibility personally confirmed by user |
| Post-checkout service health | Currently healthy; restart and host-memory qualifications below |
| Overall Stage 3.7 | Not complete until public storefront visibility passes; do not place another order to resolve this presentation check |
| Stage 3.8 persistence-under-Pod-replacement | Not tested; storing/reading order 12 does not satisfy this experiment |

Helm urumi remains revision 2/deployed. WordPress/MariaDB are 1/1 Ready; the r2 Job remains Complete (11s) with zero Job restarts. Each application container now has one restart, stable across this inspection, with prior reason Unknown and exit 255 at 02:20:30Z. Both restarted at 02:20:37Z. A node Rebooted event at 02:20:35Z and the k3d node-container start at 02:20:27Z correlate these restarts with a node/runtime restart about four minutes before the order. Node Ready returned at 02:20:46Z. The trigger for the reboot is not established; no OOMKilled termination is visible, the node container reports OOMKilled=false, and MemoryPressure is False. This is not a claim of zero historical restarts or a substitute for controlled persistence testing. Required system Deployments are all 1/1 Ready.

| Post-checkout memory snapshot | Windows total / used / available GiB | Node usage | MariaDB / WordPress |
| --- | --- | --- | --- |
| Start of verification | 15.726 / 13.824 / 1.903 | 1207Mi (20%) | 129Mi / 269Mi |
| After read-only inspection | 15.726 / 13.694 / 2.033 | 1270Mi (21%) | 129Mi / 291Mi |

Node allocatable is 6064280Ki (about 5.78 GiB). These are after-checkout samples; memory during the manual checkout was not measured. Host headroom is below the operating floor for new deployment/runtime experiments, despite current node health. Recover/recheck memory before Stage 3.8. Next: separately review a reproducible public-visibility correction, preserve order 12, then validate anonymous catalog/product content. Stage 3.8 must separately demonstrate persistent data and claim reuse across controlled Pod replacement; no Pod/PVC deletion, Helm change, automatic rollback, password/Secret change, REST credential creation, staging or commit occurred here.

### Stage 3.7C deterministic Live visibility — source/static review only

Implemented on 2026-10-21 from clean main at cd93a43. The successful manual transaction does not establish anonymous storefront visibility: Coming Soon protected both shop/product presentation. The existing v2 bootstrap verifies its previous settings and rewrites but ignores those two visibility options; changing only the expected version fails shell/PHP target and ownership guards.

The user now explicitly requires bootstrap to finish in public Live state. Contract v3 adds coming_soon=no and store_pages_only=no, preserving the previous fields and business-setting checkpoint. Matching completed v2 may transition through yes/yes -> no/yes -> no/no. Owned fresh/partial v3 accepts the same bounded pairs; v3 ownership with marker 2 or 3 requires no/no already. Unknown ownership/versions, missing/mistyped options, yes/no, completed permalink drift and unrelated setting conflicts fail. Direct v1-to-v3 upgrade is not adopted; v1 first needs the reviewed v2 migration.

Completed-store configuration and DB/Apache rewrites are checked before visibility changes. The finite shell retains its configure/hard-rewrite sequence, then make-live uses supported option APIs for the two intentional writes. A separate finalize process verifies the persisted no/no state and all previous invariants before ownership v3 and marker 3 last; finalization cannot repair a lost visibility write. Readiness adds both Live checks without frontend HTTP. TCP startup/liveness, pins, resources, Secret references, Job bounds/affinity and storage remain unchanged. See [DEC-025](decisions.md#dec-025-public-live-store-contract-and-v2-to-v3-migration) and the [state table](architecture.md#stage-37c-public-live-visibility-and-explicit-v2-to-v3-migration).

| Static check | Result / boundary |
| --- | --- |
| Shell syntax | Passed sh -n through LF stdin; script not executed. The first checker attempt converted input to CRLF on Windows and failed; binary LF transport corrected the checker without a source change |
| PHP syntax | Configurator, fixture and both rendered readiness programs passed php -n -l in the existing pinned WordPress container; no files/options written |
| Regression fixture | 95 assertions passed using function declarations and in-memory WordPress stubs only; no live database/WordPress loading |
| Fixture coverage | v2 migration, product 11/order 12/user sentinels, completed v3, fresh/partial v3, interrupted visibility/ownership/marker writes, marker-last ordering, stale/missing rules, inactive WooCommerce and invalid ownership/settings/visibility refusals |
| Helm | Strict local/production lint passed; chart icon suggestion informational |
| Rendering/schema | Exactly eight objects per environment; all 16 validated against official Kubernetes v1.35.5 OpenAPI definitions; duplicate keys rejected |
| Structural/security | Selectors/ports/mounts/affinity/deadlines, exact Secret key references, retained claims, image pins, unchanged budgets, independent probes and rendered credential scans passed; no Secret/Namespace object or public MariaDB |
| Runtime boundary | No Helm operation that persists changes, no apply/server dry-run, bootstrap entrypoint, live option write, checkout/order edit, credential creation or deletion test |

Local helm template uses revision 1 by default, so preview asset/Job names have r1; expected bootstrap version is 3 independently. Future live revision 3 would render r3 names. Inventory remains one ConfigMap, one Job, WordPress Deployment, MariaDB StatefulSet, two Services, WordPress PVC and WordPress Ingress; the StatefulSet creates its separate database claim at runtime.

Read-only pinned-source inspection confirmed WooCommerce 11.2.1's fresh installation code adds yes/yes defaults, consistent with official visibility documentation. This is a code-path finding, not proof of when the current database values were set. No manual admin toggle or arbitrary option reset substitutes for source-controlled configuration. The fixture proves selected code paths in isolation, not real option-hook, cache, concurrency or storefront behavior.

Future authorized runtime work must recover/recheck host headroom, confirm terminal previous Jobs and serialize one upgrade. Preserve product 11 and Processing order 12, inspect migration/readiness and anonymous visible-body output excluding scripts, and confirm the single order is unchanged without placing another. Completed v3 drift fails rather than being silently repaired. After marker 3, historical marker-2 readiness fails and Helm rollback cannot rewind persisted database/files. Stop for source/static review; runtime visibility acceptance, Stage 3.7 completion and Stage 3.8 persistence/dependency-loss tests remain pending.

### Stage 3.7D Live migration — accepted at revision 3

On 2026-10-21 the first attempt from 44a16df stopped before preview/upgrade: Windows total/used/available RAM was 15.726/13.051/2.675 GiB, below the approximately 3.5 GiB floor. Infrastructure was healthy but no business-state query or migration ran. The user later resumed after recovering headroom; the complete gate was repeated rather than reusing that measurement. Only the two operational documents were already modified; chart/fixture source remained committed and unchanged.

The resumed gate found 4.060 GiB available, Docker Linux/k3d healthy, context k3d-urumi-local, node Ready and MemoryPressure=False. Traefik/CoreDNS/metrics-server/local-path-provisioner were each 1/1 Ready. Release urumi remained revision 2/deployed, WordPress/MariaDB Ready with one existing restart each, and r2 bootstrap Complete (11s) with no Running/Terminating bootstrap Pod. Both claims were Bound and the hostname resolved to 127.0.0.1. Read-only APIs freshly verified product 11, exactly one SKU/order, Processing order 12, marker/ownership 2, postname permalinks and yes/yes visibility. Anonymous shop/product requests returned 200 but their visible bodies contained the pre-launch messages, not the product name.

The read-only Helm client dry-run preview rendered revision 3 and eight resources. Comparison against the released r2 manifest found changes only to approved ConfigMap scripts/name, Job name/assets reference/bootstrap version and WordPress bootstrap environment/readiness. MariaDB StatefulSet/Service and WordPress PVC/Service/Ingress were semantically unchanged; retention remained configured, MariaDB internal, no Secret/Namespace object and no product/order state managed by Helm.

After another RAM measurement (3.982 GiB available), this exact live command ran once:

```text
helm upgrade urumi charts/urumi --namespace urumi --kube-context k3d-urumi-local --values charts/urumi/values-local.yaml --wait=watcher --wait-for-jobs --timeout 15m
```

Helm returned success at revision 3/deployed. Observed old WordPress terminating, then replacement urumi-wordpress-886bfd79c-h5f79 Running but initially unready, r3 bootstrap ContainerCreating -> Running -> Succeeded, and final WordPress Ready. The Job urumi-store-bootstrap-r3 ran from 15:40:09Z to 15:40:20Z (21:10:09 to 21:10:20 +05:30), **11 seconds**, with zero failures/restarts. Its approved log messages confirmed installed WordPress preservation, configuration/rewrite checks, Live migration and successful bootstrap. Two readiness-failure events at 15:40:16–17Z preceded completion; their diagnostic bodies were intentionally empty. An inspection assertion initially expected an exit-code string, then was corrected after checking the actual event format; no runtime/source fix was needed. The live readiness command subsequently exited 0. TCP startup/liveness stayed unchanged.

Fresh API reads verified exact ownership matching the rendered v3 contract, marker 3, coming_soon=no, store_pages_only=no, /%postname%/, active WooCommerce 11.2.1 and every stored business-setting checkpoint. Marker-last ordering is established by the reviewed implementation/fixtures and successful final verification, not separate runtime observation of each database write. Private before/after comparisons of user IDs/stored credential state and product/order object state matched; neither credential values, customer details nor comparison digests were displayed or recorded here.

| Preservation check | Actual result |
| --- | --- |
| Product | ID 11, SKU URUMI-DEMO-001, exactly one match, published, in stock, price 499 INR; unchanged |
| Order | Exactly one order, ID 12, Processing; product 11, quantity 1, subtotal/total 499 INR, COD, guest, free_shipping instance 1 at zero cost; unchanged |
| MariaDB continuity | Same Pod UID ff2ac162-040f-4137-8fb7-6fb54011db64; Ready; one pre-existing restart remained one |
| WordPress replacement | Old UID ee09b388-aa2a-418e-ad2c-8c2c41d42293 replaced by 1634ae34-194a-4dd4-8854-88c0739d4c24 through Recreate; Ready with zero restarts |
| WordPress storage | Same claim UID 864a302a-0a39-4880-b522-558a4c830845 and PV pvc-864a302a-0a39-4880-b522-558a4c830845, Bound |
| MariaDB storage | Same claim UID d3e6142a-b6b9-4e67-8880-a564f41ba331 and PV pvc-d3e6142a-b6b9-4e67-8880-a564f41ba331, Bound |

Anonymous HTTP clients sent no cookies/authentication and parsed visible HTML body text excluding scripts/styles/templates/noscript. /shop/ returned 200 with Shop heading, WooCommerce catalog classes, visible Urumi Demo Mug, INR price and product link. /product/urumi-demo-mug/ returned 200 with the product heading, postid-11/published/in-stock/purchasable metadata, visible 499 INR and enabled Add to cart button value 11. Neither showed Coming Soon or the prior pre-launch messages. Homepage remained 200 with its unchanged Blog heading; /shop/ is the catalog. This is HTML/content/control evidence, not a browser screenshot or another checkout.

| Memory sample | Windows total / used / available GiB | Node usage |
| --- | --- | --- |
| Resumed preflight | 15.726 / 11.666 / 4.060 | 1241Mi (20%) |
| Immediately before live upgrade | 15.726 / 11.744 / 3.982 | Not resampled at this exact instant |
| Lowest sampled available during upgrade | 15.726 / 12.080 / 3.647 | 1242Mi (20%) |
| After migration/acceptance | 15.726 / 11.901 / 3.826 | 1087Mi (18%) |

Node allocatable remained 6064280Ki (about 5.78 GiB); final MariaDB/WordPress usage was 129/116Mi. No OOMKilled appeared in sampled container states, no new unexpected restart occurred and MemoryPressure stayed False. These samples do not prove the absolute peak or full-stack capacity.

| Stage 3.7 acceptance criterion | Result / evidence |
| --- | --- |
| Deterministic configuration | Pass: IN, Asia/Kolkata, INR, taxes off, guest/COD enabled, unrestricted free shipping, exact v3 ownership/settings |
| Permalink routing | Pass: /%postname%/ preserved; normal shop/product routes work |
| Demo product | Pass: product 11 and unique SKU preserved, published/in stock at 499 INR |
| Guest checkout | Pass: prior single manual checkout plus preserved guest order 12; no new order placed |
| COD | Pass: enabled and payment method cod on order 12 |
| Free shipping | Pass: enabled unrestricted method; order shipping free_shipping, zero cost |
| Stored order | Pass: one Processing order 12 with product 11, quantity 1 and total 499 INR |
| Admin visibility | Pass: user's earlier personal confirmation retained; no automated login |
| Anonymous shop visibility | Pass: actual catalog/product text visible, no Coming Soon presentation |
| Anonymous product visibility | Pass: product 11, price and enabled Add to cart visible without authentication |
| Post-migration health | Pass: revision 3/deployed, WordPress/MariaDB Ready, r3 Complete, stable storage and no new restart/OOM/MemoryPressure |

**Stage 3.7 is complete.** Stage 3.8 must separately validate controlled WordPress/MariaDB Pod-replacement persistence and database-dependency-loss behavior; this upgrade does not substitute for those experiments. No Secret modification, REST credential creation, extra checkout, order edit, uninstall, rollback, deliberate persistence test, staging or commit occurred. Existing PV reclaim policy remains Delete: retention is not permission to delete claims/namespaces and is not backup. Automatic Helm rollback remains unsafe because it does not rewind persisted database/files and older readiness expects marker 2.

### Stage 3.8 controlled persistence and dependency-loss validation

Run on 2026-10-21 from clean main at af7bb37. All mutations were limited to deleting the current WordPress Pod, deleting the current MariaDB Pod, and temporarily scaling the MariaDB StatefulSet 1 -> 0 -> 1. No force deletion, Helm operation that changes the release, controller replacement, PVC/PV/namespace/Secret deletion, bootstrap invocation or business-data edit occurred.

Baseline: urumi revision 3/deployed; WordPress/MariaDB 1/1 Ready; r3 bootstrap Complete with its original 11s timestamps; node Ready and MemoryPressure=False. WordPress had zero restarts; MariaDB had one previously recorded restart. Both anonymous routes passed visible-body checks. Supported WooCommerce reads verified product 11/unique SKU URUMI-DEMO-001/published/in stock/499 INR and exactly one Processing guest order 12/quantity 1/499 INR/COD/free shipping. Marker/ownership 3, Live options no/no, postname permalinks, active WooCommerce 11.2.1 and existing business-setting checkpoints all passed. Actual readiness and liveness-equivalent checks succeeded for both workloads before disruption.

| Identity | Before | After WordPress deletion | After MariaDB deletion | Final, after dependency-loss restoration |
| --- | --- | --- | --- | --- |
| WordPress Pod name | urumi-wordpress-886bfd79c-h5f79 | urumi-wordpress-886bfd79c-hvdsc | Same hvdsc | Same hvdsc |
| WordPress Pod UID | 1634ae34-194a-4dd4-8854-88c0739d4c24 | 77779167-94e6-4cc0-9f51-b32c786fc7a4 | Same | Same |
| MariaDB Pod name | urumi-mariadb-0 | Same | Same ordinal 0 | Same ordinal 0 |
| MariaDB Pod UID | ff2ac162-040f-4137-8fb7-6fb54011db64 | Same | 53864740-55b9-44d7-aff5-8a4df03ab7f5 | 43a3b149-155d-470a-af31-db0165df8aab |

Deployment UID 74f85e90-dc5e-430f-9905-62c6719eba8b, ReplicaSet urumi-wordpress-886bfd79c/UID 7112bdd4-4d70-4d68-977a-d1bc5f10383b and StatefulSet UID ca9dd6b3-4662-4924-a16d-ba7270303827 remained unchanged. The completed bootstrap Job UID fb9bb7e2-2fda-4b39-bdda-c4caf9bc1688, its Pod and start/completion timestamps remained unchanged throughout: ordinary application Pod replacement did not rerun bootstrap.

**WordPress replacement:** Deleted only h5f79 with normal graceful deletion. Observed the old Pod terminating, then hvdsc Running but not yet started/Ready, then Ready at approximately 7.8s from the deletion request. Same controller/claim, zero replacement-container restarts. Hashes of the persisted .htaccess, wp-includes/version.php and WooCommerce main plugin file matched baseline. Product/order/user-state comparisons, marker/version and both anonymous pages passed after recovery. This establishes selected application-file persistence and Deployment reconciliation; the still-running database at this point does not itself prove database restart durability.

**MariaDB replacement:** Deleted only ordinal 0. Observed old UID terminating, then the new ordinal-0 UID Running/unready, then Ready at approximately 7.9s. The same StatefulSet and data claim/PV were reused; the new container had zero restarts. WordPress stayed Ready in sampled states during this short interruption, although one bounded readiness-timeout event was recorded. All records/options and anonymous content passed after recovery with no duplicates. This independently demonstrates database persistence across a database Pod replacement.

**Deliberate dependency loss:** Before scale-down, the live StatefulSet explicitly had whenDeleted=Retain and whenScaled=Retain; the existing claim was Bound, had no ownerReferences/deletionTimestamp, and the PV claimRef matched its UID. The volume template/data mount still referenced data-urumi-mariadb-0. These observed settings match [Kubernetes v1.35 retention semantics](https://v1-35.docs.kubernetes.io/docs/concepts/workloads/controllers/statefulset/#persistentvolumeclaim-retention). The PV reclaim policy is Delete, but no claim deletion was performed or authorized.

Used explicit-context kubectl scale with current-replica guards (1 -> 0, then 0 -> 1), not Helm. From the scale-down request: MariaDB Pod absent at about 4.1s; WordPress Ready became False at 33.7s; /shop/ returned HTTP 503. TCP connections to the WordPress Pod's configured port 80 succeeded repeatedly while the database Pod was absent. WordPress retained its Pod UID/container ID and zero restarts, so no manual/liveness restart supplied recovery. Both claims remained Bound with unchanged identities throughout. Restoration was issued at 35.2s; MariaDB and WordPress were Ready at 44.2s, approximately 9s after restoration. The database was not left down for another experiment. Replica drift was removed: both the live StatefulSet and released manifest again declare one replica.

The replacement WordPress Pod's subsequent kubelet probe counters showed 15 successful liveness probes and no failed-liveness series, five failed readiness probes and 26 successful readiness probes. These are cumulative Pod-lifetime counters, not per-test timing. Events included readiness execution errors on old terminating Pods, one readiness timeout during fast MariaDB replacement and four readiness failures during deliberate loss; no liveness failure or OOMKilled was observed. Final direct probe checks passed. Recovery timings are polling observations, not exact outage-duration guarantees.

| Persistent binding | Claim UID, unchanged through all experiments | PV name, unchanged and Bound |
| --- | --- | --- |
| urumi-wordpress | 864a302a-0a39-4880-b522-558a4c830845 | pvc-864a302a-0a39-4880-b522-558a4c830845 |
| data-urumi-mariadb-0 | d3e6142a-b6b9-4e67-8880-a564f41ba331 | pvc-d3e6142a-b6b9-4e67-8880-a564f41ba331 |

After each recovery, read-only APIs and private before/after comparisons verified unchanged product/order object data and user credential state; no customer/credential values or comparison digests were displayed or documented. Product 11 remained unique, published, in stock and 499 INR; order 12 remained the only order, Processing, quantity 1, total 499 INR, COD, guest and free_shipping instance 1 at zero cost. Marker 3, WooCommerce 11.2.1, Live settings and permalink configuration persisted. Anonymous /shop/ and product responses returned 200 with real product/price text, no Coming Soon presentation and an enabled product-11 Add to cart control. No cart action or new checkout was submitted.

| Memory observation | Available Windows RAM (GiB) | Node usage |
| --- | --- | --- |
| Baseline capture | 3.636 | 1088Mi |
| Immediately before WordPress deletion | 3.719 | 1102Mi |
| After WordPress verification | 3.773 | 1034Mi |
| Immediately before MariaDB deletion | 3.767 | 1106Mi |
| After MariaDB verification | 3.464 | 1097Mi |
| Retention check / fresh headroom recheck | 3.631 | 1066Mi |
| Immediately before dependency-loss injection | 3.653 | 1092Mi |
| During deliberate database absence | 3.846 | 998Mi |
| Final application/HTTP verification | 3.744 | 1097Mi |

Windows total remained 15.726 GiB (final used 11.982 GiB); node allocatable remained 6064280Ki, about 5.78 GiB. A later workload sample showed MariaDB 95Mi and WordPress 135Mi. The brief 3.464 GiB dip was reported; fresh headroom recovered before the next disruption. No budgets were lowered. Node stayed Ready/MemoryPressure=False, and new application Pods ended with zero restarts. Samples do not establish a memory peak or full-stack capacity.

**Stage 3.8 passes for this local single-node store.** Application-file and database Pod-replacement durability, scale-down claim retention, readiness dependency behavior and automatic recovery are observed. This does not prove zero downtime, high availability, node-loss survival, backup/restore, uninstall/reinstall retention, production behavior or every possible bootstrap failure path. Further store integration remains separately scoped: review/checkpoint this evidence, then authorize WooCommerce REST credential preparation/custom MCP integration when appropriate. No such credentials or MCP implementation were created here. No architecture redesign or decision change was required; architecture/requirement evidence is corrected only where the previous unverified claims are now outdated.

### Stage 3.8 final review and local Stage 3 assessment

On 2026-10-22 the review resumed without repeating any runtime experiment. Git contained exactly four unstaged documentation changes: progress, journey, architecture and requirements. The completed 21 October results above remain the experiment evidence; they are not substituted for a fresh health measurement.

| Read-only final check | Actual 22 October result |
| --- | --- |
| Context / host mapping | k3d-urumi-local; store.urumi.test resolves to 127.0.0.1 |
| Docker / cluster containers | Linux engine reachable; server and load-balancer containers running; mappings remain 8080 -> 80, 8443 -> 443 and 127.0.0.1:6550 -> 6443 |
| Kubernetes API / Helm release read | API at 127.0.0.1:6550 returns EOF, including a bounded /readyz request; Helm cannot retrieve release status |
| Workloads, data and storage | Current Ready/restart counts, bootstrap status, product 11, order 12, marker/version, PVC bindings and node MemoryPressure cannot be freshly verified while the API is unreachable |
| Anonymous shop / product URLs | Both return an empty reply (curl exit 52 / status 000), not a valid HTTP status or accepted storefront body |
| Host RAM / node memory | Windows total 15.726 GiB, used 11.986 GiB, available 3.740 GiB; current node memory unavailable |

At this initial review boundary, the cause of the later availability gap had not been established. No cluster restart, configuration change, Pod deletion, scale change, Helm mutation, bootstrap or checkout was attempted. There was no fresh evidence of data loss, but also no basis to report the store healthy. Final health sign-off remained open pending restored API/store access and read-only verification; the subsequently authorized recovery is recorded below.

**Local Stage 3 scope assessment before recovery:** The planned local store foundation had demonstrated Helm deployment, deterministic bootstrap and migrations, stable Ingress routing, guest COD/free-shipping checkout and admin visibility, anonymous catalog/product visibility, WordPress and MariaDB Pod-replacement persistence, retained StatefulSet claim reuse, and dependency-aware readiness with independent liveness and automatic recovery. Those implementation/acceptance objectives were complete on the 21 October evidence, but the blocked current-health check prevented final healthy-state sign-off at this boundary.

Remaining work outside that local foundation includes WooCommerce REST credential issuance; the custom WooCommerce MCP server; gateway and two additional MCP upstreams; team/authentication/API keys/auditing; dashboard/chat; external MCP client acceptance; VPS/k3s deployment work and configuration/deployability validation; and the final demo/video. Mandatory VPS deployability/documentation remains distinct from optional live VPS deployment under OPEN-01. These tests do not prove disk-loss recovery, node-loss durability, production HA, multi-node storage behavior, disaster recovery or full-stack memory capacity. PVC/PV persistence across Pod replacement is not backup: the current PV reclaim policy is Delete if its PVC is deleted.

The initial documentation review passed: 45 local file/anchor links, 45 Markdown tables (420 rows), credential/contact-pattern scan and git diff --check. Review found no customer PII, credential/Secret values, generated cluster dumps or unrelated changes in the four changed documents. Those repository checks did not resolve runtime availability. Nothing was staged or committed.

### Stage 3.8 recovery of the existing local environment

On 2026-10-22 the user authorized diagnosis and minimal recovery of the existing cluster, preserving the passed 21 October experiments. Read-only checks found Docker Desktop's Linux engine reachable on desktop-linux, WSL2 docker-desktop Running, k3d listing urumi-local with one server and its load balancer, and the expected 6550/8080/8443 mappings. Context and endpoint were k3d-urumi-local and https://127.0.0.1:6550. TCP connected, but the API returned EOF; load-balancer logs showed connection refused to the server's port 6443 (also port 80).

**Diagnosis:** The running server container contained only its entrypoint/retry process, not K3s/containerd, and had no API listener. Sanitized startup logs recorded repeated K3s shutdown requests: failed to start networking because network-policy initialization failed to find an interface with the specified node IP. The entrypoint continued retrying an API-dependent uncordon operation. This establishes the immediate failure layer; the initiating trigger for the node-IP/interface condition is unproven. Docker reported server restart count 3 and OOMKilled=False before recovery; inspected logs did not establish a certificate failure or OOM cause. The existing K3s datastore file and both expected local-path storage directories were present before any restart.

**Recovery:** Performed exactly one successful stop/start pair, with a bounded start wait:

```powershell
k3d cluster stop urumi-local
k3d cluster start urumi-local --wait --timeout 180s
```

Stop returned successfully in approximately 4s; start reported success in approximately 13s. Normal k3d startup refreshed its CoreDNS host-alias records. No cluster recreation, Docker/WSL restart, Helm mutation, application reinstallation, Secret change, marker edit, Pod-deletion experiment, scale-to-zero test, bootstrap invocation or new business record was used. The server's Docker volume mounted at /var/lib/rancher/k3s remained the same. Recovery is verified by the following checks, not solely by the start command's exit status.

| Recovered component | Observed evidence |
| --- | --- |
| API / node | /readyz returns ok; Kubernetes v1.35.5+k3s1; k3d-urumi-local context; node Ready with MemoryPressure=False, DiskPressure=False and PIDPressure=False |
| System / namespace | CoreDNS, Traefik, metrics-server and local-path-provisioner each 1/1 Ready; urumi Active |
| Helm / controllers | urumi revision 3/deployed; original Deployment/StatefulSet UIDs; both desired/ready 1/1; database retention still Retain/Retain |
| Bootstrap | Same r3 Job UID and completed Pod; original 15:40:09Z -> 15:40:20Z timestamps on 21 October; Complete, zero restarts; no rerun |
| Store contract | WooCommerce 11.2.1 active; marker 3; /%postname%/; both visibility options no; INR/IN/Asia-Kolkata, taxes off and guest checkout enabled |
| Product | ID 11; exactly one matching URUMI-DEMO-001; published/in stock/purchasable; regular/current price 499 INR |
| Order | ID 12; exactly one order; Processing; guest; product 11 quantity 1/subtotal 499; total 499 INR; COD; free_shipping instance 1 at zero cost |
| Anonymous HTTP | /shop/ and /product/urumi-demo-mug/ return 200 with visible Urumi Demo Mug/rupee price and no Coming Soon presentation; product page has enabled Add to cart for ID 11 |

Business verification used supported read-only WooCommerce getters inside the existing WordPress container, with WP-Cron disabled and unexpected output suppressed. No customer name/contact/address, credential values, full order objects or raw cluster dumps were emitted or saved. Anonymous checks used fresh requests without login cookies and verified visible content rather than script data; no cart action or checkout was submitted.

| Pod | UID, unchanged from the 21 October final state | Final state / container restarts |
| --- | --- | --- |
| urumi-wordpress-886bfd79c-hvdsc | 77779167-94e6-4cc0-9f51-b32c786fc7a4 | Running/Ready; 2 |
| urumi-mariadb-0 | 43a3b149-155d-470a-af31-db0165df8aab | Running/Ready; 2 |
| urumi-store-bootstrap-r3-m57c8 | 095b1ad0-8d5a-4ebe-b0bd-d35a696029b6 | Succeeded; 0 |

Application restart counts stayed at 2 across post-recovery samples roughly three minutes apart. Their last recorded termination reason was Unknown, so individual restart causes are not attributed beyond the available evidence. This differs from the zero counts at the end of the 21 October experiments. No OOMKilled termination was visible in current container status, no OOM event was returned in the available namespace events, and Docker's server OOMKilled flag was false. Node MemoryPressure remained False in post-recovery samples.

| Retained PVC | Original PV, still Bound | Claim UID, unchanged |
| --- | --- | --- |
| urumi-wordpress | pvc-864a302a-0a39-4880-b522-558a4c830845 | 864a302a-0a39-4880-b522-558a4c830845 |
| data-urumi-mariadb-0 | pvc-d3e6142a-b6b9-4e67-8880-a564f41ba331 | d3e6142a-b6b9-4e67-8880-a564f41ba331 |

Both PV UIDs also match the earlier final state; claimRef UIDs match their claims. Reclaim policy remains Delete if the PVC is deleted. Existing cluster recovery is not a disk-loss restore or proof of backup, node-loss protection, HA or multi-node durability.

Windows total RAM was 15.726 GiB. Available RAM was 3.751 GiB before recovery, 3.020 GiB at the first healthy sample and 3.016 GiB finally (12.711 GiB used). Node memory was 826Mi initially after recovery and 913Mi finally, with 6064276Ki allocatable. Existing workloads recovered without budget/probe/storage changes, but host headroom is below the approximately 3.5 GiB floor for adding application workloads. Recheck and recover headroom before subsequent deployment work; full-stack capacity remains unproven.

**The transient availability incident did not destroy the persisted Stage 3 store state.** Local Stage 3 foundation and its final health verification can now be signed off. Stage 4 has not started; REST credentials, custom MCP/gateway/additional upstreams, team/auth/keys/audit, dashboard/chat, external-client acceptance, VPS/k3s work and the final demo/video remain outside this completed local foundation. No new design decision or implementation change was needed; only the four existing documentation changes are retained for review, unstaged and uncommitted.

Recovery documentation review passed: 50 local links/anchors, 48 Markdown tables (439 rows), credential/contact-pattern scan and git diff --check. The four-document diff preserves the prior experiment and outage evidence; no generated cluster files, customer PII, credential/Secret values or unrelated file changes were found.

## Docker setup outcome

Initial rechecks found no Docker CLI, Desktop executable/install record, Docker process/service, or engine pipe. WinGet 1.29.380 identified Docker.DockerDesktop 4.94.0 from Docker Inc., hosted on desktop.docker.com. WSL 2.5.9 and its required Windows features were already present. The intended setup was WSL2 with Linux containers and Docker Desktop's built-in Kubernetes disabled and unused.

The initial plan used the official installer's supported per-user mode with `--backend=wsl-2` and `--no-windows-containers`, leaving agreement acceptance for first launch. WinGet's manifest specifies an all-users installation; the per-user path was chosen before execution to avoid unnecessary elevation. The tool rejected the combined download/verification/install command before execution with **"blocked by policy"**, giving no more specific reason. Nothing was downloaded or installed by that attempt, and its planned checksum/signature checks did not run. Codex did not attempt an alternate installation route after the rejection.

The user subsequently installed Docker Desktop manually, started it, and authorized resuming validation. The per-user installation reports Desktop 4.94.0 and Docker CLI/Engine 29.8.2. Codex's existing process had inherited the old PATH; the installer had already added Docker's CLI directory to the persistent user PATH. Validation commands refreshed only their process-local PATH, without changing persistent settings or the Docker context.

| Required check | Actual result |
| --- | --- |
| `docker --version` | Docker CLI 29.8.2, build 7fc2dff; command succeeds |
| `docker version` | Client 29.8.2 on windows/amd64 and Server Engine 29.8.2 on linux/amd64, Docker Desktop 4.94.0; exit 0 |
| `docker info` / engine reachability | Exit 0; Docker Desktop engine responds. Output review limited to non-sensitive runtime fields |
| Active Docker context | desktop-linux, using the local named pipe npipe:////./pipe/dockerDesktopLinuxEngine; context unchanged |
| `docker info --format '{{.OSType}}'` | linux; exit 0 |
| WSL2 backend | docker-desktop distribution Running with WSL version 2; engine kernel 6.6.87.2-microsoft-standard-WSL2 |
| Docker Desktop Kubernetes | `docker desktop kubernetes status` reports disabled and "Kubernetes is stopped"; not enabled or used |
| `docker run --rm hello-world` | Image initially absent; pulled from Docker Hub, printed "Hello from Docker!", exited 0 |
| Cleanup and image cache | Zero hello-world containers, including stopped containers; zero total containers afterward. linux/amd64 image remains cached with one filesystem layer and command /hello |
| Ready for k3d | Docker runtime prerequisite passed in Stage 2.2A; subsequent tool installation and cluster validation are recorded below. Full-system resource sizing remains future work |

The single disposable container was the only container created in Stage 2.2A. That step did not install k3d/kubectl/Helm or create Kubernetes resources, project containers, Dockerfiles, or application directories. Docker Desktop's disabled Kubernetes integration is not the selected project cluster; k3d remains the accepted local cluster tool.

## Kubernetes CLI toolchain outcome

Stage 2.2B first checked availability. Refreshing only the command process's PATH from the existing Windows configuration exposed Docker Desktop's bundled kubectl v1.36.1. It already passed client validation, so no duplicate kubectl installation was needed. Kubernetes documents this bundled CLI and the separate Kubernetes.kubectl WinGet option in its [Windows installation guide](https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/).

Installed k3d.k3d 5.9.0 and Helm.Helm 4.3.0 sequentially through WinGet, with exact IDs/versions, the winget source, user scope, and prompts disabled. The manifests point directly to the [official k3d release](https://github.com/k3d-io/k3d/releases/tag/v5.9.0) and get.helm.sh respectively; WinGet verified each installer hash. These package-manager manifests are community-maintained, while the downloaded binaries come from the upstream projects. [Helm's installation guide](https://helm.sh/docs/intro/install/) documents its WinGet option. No policy block or user interaction occurred for these installations; WinGet added command aliases and PATH entries outside the repository.

| Tool | Role in our architecture | Installed version | Validation result |
| --- | --- | --- | --- |
| kubectl | Inspect/manage Kubernetes resources through the future cluster API | v1.36.1, already supplied by Docker Desktop | `kubectl version --client` exit 0; retained existing binary |
| k3d | Create/manage local K3s cluster nodes as Docker containers | v5.9.0 | `k3d version` exit 0; reports default K3s v1.35.5-k3s1, not a running cluster |
| Helm | Render charts and manage application releases using local/VPS values | v4.3.0 | `helm version` exit 0; no chart or release created |

At the Stage 2.2B checkpoint, `kubectl config get-contexts` and `k3d cluster list` both returned empty listings. No default kubeconfig existed and no KUBECONFIG override was set. The initial `kubectl config current-context` returned "current-context is not set" (exit 1), the expected unconfigured state rather than a tool-installation failure. No context was created or changed. Docker Desktop Kubernetes reported disabled/stopped, and Docker had zero containers. No cluster, Kubernetes resources, application files/directories, Dockerfiles, or Helm charts were created in that step.

K3s is the Kubernetes distribution; k3d manages its local Docker-based cluster lifecycle. kubectl works with individual resources and operational details such as pod status, logs, and events. Helm manages chart-based releases; it complements kubectl rather than replacing that operational interface. Installing these CLIs provides executables, not a control plane or deployed workloads. At Stage 2.2B, cluster version and resource/Ingress design remained for review. kubectl must be within one minor version of the chosen Kubernetes server; the v1.36 client is within that range of k3d's v1.35 default. Stage 2.3 below records the first live cluster validation.

## First local Kubernetes cluster outcome

Prechecks reconfirmed Docker Engine 29.8.2 reachable in Linux mode, no k3d clusters or kubectl contexts, and Docker Desktop Kubernetes disabled/stopped. TCP ports 6550, 8080, and 8443 had no existing bindings or Windows exclusions; temporary bind-and-release checks succeeded. Windows had approximately 2.79 GiB available of 15.73 GiB RAM immediately before creation. The Docker WSL environment separately reported about 6.93 GiB available within its virtual memory capacity; these figures are not additive. Headroom was judged sufficient for this infrastructure-only step against the [K3s server baseline](https://docs.k3s.io/installation/requirements) of 2 GB RAM, excluding application workloads.

The user selected one server, no additional agents, the three host ports, and retained K3s defaults. Installed k3d v5.9.0 supported the following command without a syntax substitution. The API uses loopback; HTTP/HTTPS mappings use Docker's default host interfaces.

```powershell
k3d cluster create urumi-local --servers 1 --agents 0 --api-port 127.0.0.1:6550 --port "8080:80@loadbalancer" --port "8443:443@loadbalancer" --wait --timeout 5m
```

Creation completed successfully in about 54 seconds, using k3d's default rancher/k3s:v1.35.5-k3s1 image. k3d created infrastructure containers, the k3d-urumi-local Docker network and image volume, and the personal kubeconfig outside the repository. It selected the new context; kubeconfig credentials were not printed or copied into documentation.

| Check / component | Observed result |
| --- | --- |
| Cluster and context | urumi-local: servers 1/1, agents 0/0, load balancer enabled; only context is k3d-urumi-local, selected |
| API | https://127.0.0.1:6550 responds; `/readyz` returns ok |
| Node and runtime | k3d-urumi-local-server-0, Ready, control-plane role, Kubernetes/K3s v1.35.5+k3s1; containerd 2.2.3-k3s1; no memory/disk pressure or scheduling taints observed |
| Namespaces | default, kube-system, kube-public, kube-node-lease; all Active; no project namespace |
| CoreDNS | Deployment available, Pod 1/1 Running; kube-dns ClusterIP Service present |
| Traefik | Deployment available, Pod 1/1 Running; ServiceLB DaemonSet ready 1/1 with a 2/2 Running Pod; LoadBalancer Service exposes 80/443 |
| Metrics-server | Deployment available, Pod 1/1 Running; metrics API works through `kubectl top nodes` |
| Storage | local-path is the default StorageClass, provisioner rancher.io/local-path, Delete reclaim policy, WaitForFirstConsumer binding; provisioner Pod 1/1 Running. No PVC or persistence test created |
| Infrastructure containers | k3d-urumi-local-server-0 (K3s), k3d-urumi-local-serverlb (k3d-proxy 5.9.0), and k3d-urumi-local-tools (k3d-tools 5.9.0) all running; tools helper is not a Kubernetes node |
| Host mappings | serverlb publishes 127.0.0.1:6550 to 6443, host 8080 to 80, and host 8443 to 443; HTTP/HTTPS bindings appear on IPv4/IPv6 wildcard interfaces |
| HTTP observation | http://127.0.0.1:8080/ returns expected Traefik 404 with no application Ingress route; HTTPS certificates/routing were not validated |
| Desktop Kubernetes | Still disabled/stopped; this cluster is managed by k3d |

Validation ran the requested cluster, Docker container, context, cluster-info, node, namespace, Pod, Service, and StorageClass listings. It additionally waited for node Ready, all four system Deployments Available, and both Traefik bootstrap Jobs Complete; inspected the ServiceLB DaemonSet and API readiness; and retrieved node metrics. Early Flannel subnet initialization warnings and a metrics-server image download EOF cleared through automatic retries without configuration changes. The Traefik installation Job completed after one container restart; its CRD Job also completed. Completed bootstrap Pods correctly show 0/1 Ready because their work has ended; all continuing system Pods were ready with zero restarts at the final check.

Windows available RAM was about 1.28 GiB after startup. The node metrics snapshot showed about 727 MiB memory usage and no memory pressure was observed, but this is not total Windows/Docker overhead or an application capacity budget. Reassess host memory before expanding the environment. No project workload, nginx learning workload, application directory, Dockerfile, Helm chart, or additional CNI/NetworkPolicy tooling was created. k3d's nginx-based infrastructure proxy and K3s's automatic Traefik Helm Jobs are cluster internals, not project scaffolding. Stable application URLs, real persistent-volume behavior, TLS, and VPS compatibility remain unverified.

## Stage 2.4A learning workload outcome

Prechecks passed with current/target context k3d-urumi-local, a Ready node, healthy system components, no lab namespace/Ingress conflict, approximately 3.14 GiB available host RAM, and the pinned nginx tag active for Linux/amd64. A fresh external request confirmed the pre-apply Traefik 404. Namespace apply, server dry-run of the remaining manifests, apply, and rollout succeeded. An initial registry-download EOF recovered through Kubernetes image-pull retries without changing the manifests.

The Deployment has one desired/current/ready replica; inspected owner references connect it to its generated ReplicaSet and Ready Pod. Matching app=nginx-lab selectors connect the Service to that Pod, and its EndpointSlice records one ready backend. The approved in-cluster DNS/Service request returned nginx HTML; Windows localhost:8080 returned HTTP 200 with Server: nginx/1.30.5 and the welcome page through the existing Traefik route. Live resource requests/limits and both probes match the manifest; nginx logs show successful probe requests and the Pod has zero restarts. Detailed identities, addresses, ownership, and evidence are in the [lab's actual observations](../labs/kubernetes-basics/README.md#actual-observations).

The one-replica lab remains running. No Pod deletion, scaling, drift/reconciliation experiment, probe failure injection, cleanup, or HTTPS test was performed. Healthy operation is observed; application capacity and failure handling remain unverified. No Urumi application or Helm resources were created, and this step does not complete an assignment requirement.

## Stage 2.4B controller reconciliation outcome

The baseline was healthy: Deployment and ReplicaSet desired/current/ready 1/1/1, one Ready Pod, one ready Service backend, and external HTTP 200. After capturing identities and starting Pod/EndpointSlice watches, deleted only the captured nginx Pod. The same ReplicaSet created a replacement, which was scheduled on the same node, started from the cached image, and became Ready with zero restarts. The Pod UID changed and its IP changed from 10.42.0.9 to 10.42.0.10; Deployment/ReplicaSet UIDs, desired count, Service identity/ClusterIP, and Ingress identity/spec remained unchanged.

Watches observed termination, replacement Pending/ContainerCreating/Running/Ready states, and the EndpointSlice moving from the old terminating backend through an empty endpoint list to the new ready backend. Events confirmed creation, scheduling, cached image availability, and container startup. Both in-cluster Service DNS access and localhost:8080 returned HTTP 200 afterward. Final Deployment/ReplicaSet counts are 1/1/1. The [lab's actual observations](../labs/kubernetes-basics/README.md#actual-observations) preserve the identity comparison and observed sequence.

The empty-backend interval demonstrates why self-healing is not zero downtime. HTTP was not continuously sampled, so no outage duration or intermediate HTTP status is claimed. No manifests, replica counts, Service/Ingress configuration, or other workloads were changed. The replacement remains running; scaling, manifest/live-state drift, cleanup, and deliberate probe failures await later authorization.

## Stage 2.4C scaling and declarative reconciliation outcome

Verified the one-replica baseline, one Ready Pod/backend, correct context, external HTTP 200, and committed replicas: 1 before changing live state. Imperative scale to 2 produced Deployment and the same ReplicaSet at 2/2/2. Existing Pod bj9sz (10.42.0.10) and added Pod n5jjc (10.42.0.11) were Ready with zero restarts on the same node; the Service had two ready backend addresses. Service ClusterIP 10.43.133.91 and Service/Ingress identities/specs stayed unchanged; external HTTP returned 200.

kubectl diff exited 1 and showed live replicas: 2 versus the file's replicas: 1, plus the predicted server-managed generation increment. Re-applying the byte-identical committed Deployment file restored live desired replicas to 1. A watch showed n5jjc terminating/completing, and the ReplicaSet recorded SuccessfulDelete. A readiness connection-refused warning coincided with that Pod's shutdown; the retained bj9sz Pod remained Ready with zero restarts. Final Deployment/ReplicaSet counts were 1/1/1 with only 10.42.0.10 as a ready backend, external HTTP 200, and an empty kubectl diff (exit 0). Detailed identities and evidence are in the lab's actual observations.

Kubernetes follows the live API object's desired state, not the Git file automatically. Re-applying YAML restored our committed intent. Two Pods on one node offer Pod-level redundancy but no node-failure protection; no availability guarantee or distribution test is claimed. Helm's future values/templates will render manifests expressing intent, and manual live changes can similarly diverge. No Helm files or releases were created, no YAML/Service/Ingress was changed, and no cleanup or extra workload was performed. The one-replica lab remains running; this checkpoint is uncommitted for review.

## Stage 2.4D cleanup and final validation outcome

The pre-cleanup baseline passed: correct current/target context, Ready node, Active lab namespace, Deployment/ReplicaSet 1/1/1, one Ready Pod/backend, existing Ingress, and external HTTP 200. Captured all six relevant namespaced resource types and their ownership. Deleted only namespace kubernetes-basics with an explicit context and bounded wait; a watch observed Active then Terminating. Deletion completed successfully without forced cleanup or child-resource deletion commands.

Subsequent listings confirmed namespace absence and no lab Deployment, ReplicaSet, Pod, Service, EndpointSlice, or Ingress across the cluster. urumi-local remains listed with servers 1/1 and its load balancer enabled. The node is Ready; Traefik, CoreDNS, metrics-server, and local-path-provisioner Deployments are each desired/ready/available 1/1/1 with Ready running Pods. The Traefik ServiceLB Pod is 2/2, and the cluster-scoped IngressClass remains. With no Ingress objects left, localhost:8080 returned HTTP 404 and `404 page not found`, matching the original no-route state.

The fundamentals lab is complete: controller ownership, labels/selectors, Service/EndpointSlice discovery, internal/external routing, probes/resources, Pod replacement, scaling, declarative drift restoration, and namespace lifecycle have been observed. Namespace grouping enabled cleanup but does not itself enforce network isolation. Live objects are gone while all learning manifests remain available for an authorized repeat. No application requirement/demo status changes, Helm chart, new workload, or application deployment are implied. Detailed cleanup evidence is in the lab README; prior outcome sections retain their historical checkpoint state.

## Validation and review record

Stage 0's completed checks included exact transcription of 169 nonempty paragraphs, 119 list entries, and 29 heading depths; 40 local links/anchors; ignore rules; formatting; and complete governance diff review. Architecture v1's documentation checks passed on 2026-10-10: 56 local links across 9 Markdown files, consistent tracking IDs, unchanged assignment/source classifications, source checksum preservation, formatting, and complete diff review. These are historical checks, not evidence of working software.

Stage 2 preflight was read-only. Existing Git/Python/Node/npm and WSL were detected; the cluster toolchain was not. Approximately 24 logical CPUs and 110 GiB free disk supported initial planning, but only 2.6–2.8 GiB of 15.7 GiB RAM was available. Docker startup/container mode were untested at that point; Stage 2.2A verified them. Stage 2.3 now verifies the empty cluster and HTTP forwarding to Traefik; application Ingress and a full-system resource budget remain untested. Detailed engineering findings are in the journey.

The preceding k3d documentation checkpoint's checks passed on 2026-10-11 using inline Python and read-only Git commands. The table below records that historical checkpoint. No validation scripts or scaffolding were added.

| Check | Result |
| --- | --- |
| Links and tracking | All 58 local links/anchors resolve across 9 Markdown files; 44 requirements, 11 demos, 6 video groups, 10 optional items, 7 interpretation IDs, 17 decisions, 13 Architecture v1 IDs, and 4 threat topics remain consistent. The three new official technical reference pages were opened successfully |
| Scope and status fidelity | Only REQ-K8S-01's implementation plan changes in the tracking tables; source wording, mandatory/optional classifications, verification/demo fields, and all statuses remain unchanged |
| Source and checkpoint preservation | Original DOCX SHA-256 remains e9f7e797d72c331ab508d75135490644c99b9bf2c172f36225ad861926d02f92; protected files unchanged; both prior journey edits recording db49836 retained |
| Formatting | Markdown table widths, UTF-8 without BOM, LF endings, final newlines, trailing whitespace, and Git whitespace checks pass |
| Change boundary | Six existing Markdown files modified; no new files/directories or application/generated files. Added-text credential-pattern scan is clean; the complete diff is reviewed before staging |

Stage 2.2A documentation checks also passed: 58 local links across 9 Markdown files, table/encoding/whitespace checks, unchanged protected files and original DOCX checksum, and exactly two modified documentation files with no additions or staged changes. The full diff was reviewed; no credentials or application/generated files were introduced. No commit was created.

The runtime evidence for Stage 2.2A is the Docker validation table above, including the actual hello-world run and cleanup; its documentation was subsequently committed as 84395d5. Stage 2.2B adds successful CLI version checks and empty cluster/context listings. Neither checkpoint proves a working k3d/Ingress deployment or satisfies the assignment's application demos.

Stage 2.2B documentation validation passed: 58 local links across 9 Markdown files, Markdown tables/encoding/whitespace, unchanged assignment and requirement/demo statuses, and the original DOCX checksum. Only progress and the journey changed, with one new Stage 2.2B entry and the preceding commit reference recorded; no repository files/directories were added. The full diff was reviewed, and the user subsequently approved commit 248f13c. No credentials or application/generated files were introduced.

Stage 2.3 documentation checks passed for all 58 local links/anchors across 9 Markdown files, table widths, UTF-8/LF/final-newline/whitespace, and the original DOCX checksum. Only progress and the journey changed; the index is empty and no untracked files were introduced. Assignment, requirement/demo statuses, and other tracked files are unchanged. Added-text credential-pattern checks passed; the complete diff is shown for review. No commit is created in this step.

## Open and provisional work

- Docker/Linux and the single-server K3s v1.35.5+k3s1 cluster remained healthy through Stage 3.6. API port 6550 and Ingress mappings 8080/8443 are established; observed node allocatable memory is about 5.78 GiB. Fresh host RAM passed the first-install gate, then dipped and recovered during startup. Recheck before additional runtime work/components and measure use; full-stack capacity remains unproven.
- Vite and k3s for the production-like VPS remain proposed baseline selections.
- Woo SDK/protocol/runtime pins and five tool contracts are implemented. Stage 4.3 proved signing-origin connectivity; mocked modern/legacy calls and real TCP/Docker discovery pass. Active-store date boundaries, full live tool acceptance and Kubernetes hosting still need validation. Gateway client refresh/lifecycle/health remain future work.
- Stage 5.3 implements REST identity/session/invitation/key algorithms and bootstrap with fixture evidence. External MCP enforcement, audit persistence/denial/redaction/retention, runtime Secrets and deployment remain future validation.
- LLM/provider, auxiliary tool schemas, revenue-demo semantics, user A/B roles, and Claude Code versus Cursor need selection/validation. Woo contracts are implemented but full runtime acceptance remains incomplete; Inspector is selected for diagnostics.
- Local store business-flow/persistence/dependency-loss acceptance and later recovery are complete at 96757e7. Production identity/TLS, non-store components, VPS compatibility, node/disk-loss protection, backup and full-stack capacity remain unproven.

OPEN-01 through OPEN-07 in [architecture.md](architecture.md#unresolved-assignment-interpretations) have reviewed approaches under A13, with remaining validation noted. Stage 4.8 selects narrow custom-container controls without completing the optional hardening bonus. NetworkPolicy is deferred to gateway integration; the mandatory gateway-only requirement remains. Upgrade/rollback documentation and explanation are mandatory walkthrough material; executing live rollback is optional unless later evidence changes the interpretation.

## Review boundary

Stage 5.3 implementation and validation stop for review. Only apps/gateway and architecture/decisions/security/progress/journey documentation changed. Woo MCP and Helm unchanged; k3d stopped. Nothing staged/committed. External MCP authentication, audit and runtime integration remain future milestones.

The assignment gives a two-week window but no actual start/due date. No submission deadline has been inferred or scheduled.

# Architecture v1 and assignment boundaries

Status: **A1–A13 approved by the user on 2026-10-10; documentation update awaiting review; no application implemented.** The [original assignment](source/urumi-mcp-gateway-assignment.docx), transcribed in [assignment.md](assignment.md), controls scope. [requirements.md](requirements.md) maps obligations to verification. Design approval does not authorize implementation or prove a requirement works.

## Assignment constraints

The assignment requires one WordPress + WooCommerce store, our own WooCommerce MCP server with all five required product/order tools, a React dashboard with a gateway/backend, and a dashboard chat agent. The backend is an MCP client to upstreams and an MCP server at one endpoint. Both chat and external clients reach upstreams through the gateway only.

The custom WooCommerce server and supported upstream connections use Streamable HTTP. Admins register, edit, disable, and remove servers by URL, optionally with a static header or bearer credential. The gateway aggregates every enabled server's tools, handles name collisions, and isolates slow/dead servers with timeouts and clear errors. At least three upstreams are required; WooCommerce is already registered as the first.

Admin/member roles, invitations, admin key issuance/revocation, member key generation, hashed/revocable per-user keys, and a dashboard audit log are mandatory. Every tool call records user, server, tool, timestamp, duration, and outcome. Chat uses an LLM, displays tool calls, and acts as the logged-in user. Upstream credentials remain server-side. Granular tool permissions and OAuth are optional.

All core workloads run in local Kubernetes. Helm is mandatory; the same charts must support a production-like VPS through values changes. Store database and WordPress content need persistent storage; storefront/dashboard need Ingress and stable URLs; every workload needs readiness/liveness checks and requests/limits. Credentials live in Kubernetes Secrets. WooCommerce MCP is internal-only and callable only by the gateway. These outcomes remain required regardless of the selected implementation.

Actual VPS deployment is stand-out work. VPS deployability, setup documentation, and the video's production explanation remain mandatory, including DNS, Ingress, storage, secrets, and Helm upgrade/rollback. See OPEN-01 for the reviewed interpretation of that overlap.

## Approved Architecture v1 decisions

The left column preserves the user's review IDs. These are project choices within the constraints above, not additional assignment wording. Rationale and alternatives are recorded as DEC-004 through DEC-016 in [decisions.md](decisions.md).

| Review ID | Approved choice | Requirement trace |
| --- | --- | --- |
| A1 | One deployable Python/FastAPI backend, with separate internal modules for authentication, management REST APIs, MCP gateway behavior, auditing, and chat orchestration | REQ-GW-01, REQ-GW-02, REQ-TEAM-01, REQ-AUD-01, REQ-CHAT-01 |
| A2 | Same-origin browser REST under `/api`; external MCP clients use `/mcp`; the browser need not be an MCP client | REQ-UI-01, REQ-TEAM-06, REQ-CHAT-01 |
| A3 | Official Python MCP SDK and Streamable HTTP between gateway and upstreams; validate connection/session lifecycle in a later MCP prototype | REQ-WOO-02, REQ-GW-01, REQ-GW-02 |
| A4 | Expose `<immutable_server_slug>__<tool_name>`; route by an authoritative stored mapping, never by parsing the exposed name; add a deterministic suffix only for real normalization/length collisions | REQ-GW-02, REQ-GW-03 |
| A5 | Separate enabled/disabled configuration from connected/unreachable health; retain stale tool metadata for enabled unreachable servers; isolate failures; configurable timeouts; no automatic retry of ambiguous writes | REQ-GW-02, REQ-GW-04, REQ-UI-01 |
| A6 | Email/password and server-side dashboard sessions; admin/member roles; individual Bearer MCP API keys, shown once and stored only as an appropriate verifier/hash; check revocation on requests | REQ-TEAM-01, REQ-TEAM-03, REQ-TEAM-04, REQ-TEAM-05, REQ-TEAM-06 |
| A7 | Actual recoverable service credential values in Kubernetes Secrets; PostgreSQL holds metadata/references. Scope WooCommerce REST credentials to WooCommerce MCP and LLM credentials to backend chat. Never return upstream credentials from read APIs | REQ-SEC-01, REQ-GW-05, REQ-WOO-09 |
| A8 | Initial PostgreSQL entities: users, sessions, invitations, api_keys, mcp_servers, mcp_tools, audit_events | REQ-GW-01, REQ-GW-02, REQ-TEAM-01, REQ-TEAM-02, REQ-TEAM-03, REQ-AUD-01 |
| A9 | Chat derives identity from the session and uses the same internal gateway authorization, routing, timeout, and auditing path as `/mcp`; show called tools | REQ-GW-07, REQ-CHAT-01, REQ-CHAT-02, REQ-AUD-01 |
| A10 | One application namespace. Public storefront/dashboard/MCP gateway; internal PostgreSQL, MariaDB, and all upstreams. Internal upstreams use ClusterIP and gateway-held authentication. No Calico/custom NetworkPolicy prerequisite for the first core | REQ-K8S-03, REQ-K8S-05, REQ-WOO-08, REQ-GW-07 |
| A11 | One application Helm chart/release with local/production values, without duplicated manifests; chart dependencies and WordPress/MariaDB packaging deferred to the Kubernetes/store design | REQ-K8S-02, REQ-DEL-03, REQ-DEL-04 |
| A12 | Arithmetic and store policy/reference MCP servers, deterministic and without external services, alongside WooCommerce | REQ-GW-06, REQ-DEMO-01; DEMO-07 |
| A13 | Store timezone for today; immediate disabled-server filtering/denial; safe revoked-key attribution; observable pod failure/recovery; manually shared expiring invitations; Inspector diagnostics and later interactive-client validation; mandatory rollback explanation with optional live execution | REQ-WOO-05, REQ-GW-01, REQ-GW-04, REQ-TEAM-02, REQ-TEAM-03, REQ-TEAM-06, REQ-AUD-01, REQ-DEL-04 |

## Component and interface contracts

```text
Dashboard browser -> same-origin /api -> session authentication
                                      -> management and audit APIs -> PostgreSQL
                                      -> chat orchestration as session user
                                           -> shared gateway path

External MCP client -> /mcp -> individual Bearer key authentication
                            -> shared gateway path

Shared gateway path: user authorization -> stored tool mapping
                    -> upstream call with timeout -> audit outcome
  -> WooCommerce MCP -> WooCommerce REST interface -> WordPress/WooCommerce -> MariaDB
  -> arithmetic MCP
  -> store policy/reference MCP

Shopper -> storefront Ingress -> WordPress/WooCommerce
```

A1/A2/A9 place management, authentication, auditing, and chat in one backend while keeping responsibilities separate. Login, invitations, registry management, key management, audit queries, and chat use REST. MCP handles tool discovery/invocation for external consumers and upstream connections. These are logical boundaries, not application directories or implemented API contracts.

Chat obtains the usable catalog through the shared gateway path and dispatches model-requested calls through that path under the session's user identity. It must not trust a browser-supplied user ID or call an upstream directly. External requests resolve an individual key to a user before entering the same path. Basic roles control management authority; optional per-tool member restrictions have not been selected.

A3 fixes the SDK and upstream transport, not a permanent pool, per-request connection, or persistent-session strategy. Initialization, discovery refresh, connection reuse/cleanup, cancellation, and tool-list notifications need prototype validation. Verify current SDK/protocol compatibility and pin exact package versions at implementation time; moving library defaults are not architectural facts. Gateway transport/client interoperability also needs validation before claiming an external client works.

## Tool catalog and failure behavior

A4 uses a unique immutable registration slug as the namespace. Store `exposed_name -> server_id -> exact_original_tool_name` in the authoritative tool mapping. For illustration, `woo__list_orders` maps to the WooCommerce registration and its exact `list_orders` tool; these names are examples, not finalized tool schemas. Routing looks up that record and checks current configuration. It never splits or reconstructs an upstream tool name from the exposed name.

Validate actual name syntax/length against the selected SDK/protocol and clients. Introduce an additional deterministic suffix only if real normalization/length collisions require it, preserving the exact upstream name in storage. An always-present hash suffix is not approved.

A5 keeps administrator configuration separate from observed health. The dashboard presents Disabled when disabled, otherwise Connected or Unreachable from runtime observation. For an enabled server that becomes unreachable, retain its last successfully discovered tools, mark their metadata stale/unreachable, and return a clear error on attempted invocation. A server with no successful discovery has no last-known catalog to retain. Healthy listings/calls must continue independently.

Disabled servers disappear immediately from the gateway's available catalog for new requests, and calls using stale names are rejected by a current-state check. This differs from retaining the catalog of an enabled but unreachable server. Validate notification/refresh mechanics so both chat and the external client's displayed tools reflect disabling; do not assume a client has already discarded its local cache.

Connection/discovery and tool-call timeouts remain configurable defaults, not architectural constants. Values, health-check cadence, and startup observation behavior remain to be validated. Do not automatically retry ambiguous writes such as product creation after timeout: the operation may already have succeeded. Exact error shapes and audit behavior after process interruption still need design.

## Identity credentials and persistence

A6 requires server-side dashboard sessions and request-time external key validation, including revocation during an existing MCP session. Raw generated API keys are shown once and never recoverably stored. Key identifiers, generation format, hash/verifier algorithm, session/password details, and expiry defaults must be specified and validated before authentication implementation.

A7 separates user credential verifiers from recoverable service credentials. PostgreSQL holds user/key verification data, metadata, and Secret references; actual service credentials live in Kubernetes Secrets. WooCommerce REST credentials belong only to WooCommerce MCP, LLM provider credentials only to backend chat orchestration, and upstream credentials to the gateway for the intended upstream. No upstream credential value is returned by a read API or sent to a browser/external client. Gateway client tokens are never forwarded as upstream credentials. Runtime Secret creation/update/access and injection remain unvalidated; no Kubernetes API permission model has been selected.

A8 is an entity inventory, not a schema. No SQL, ORM models, migration tooling, or additional role/credential tables are authorized here.

| Entity | Responsibility | Details still to design |
| --- | --- | --- |
| users | Team identity, password verifier, admin/member role | Role representation, account lifecycle, initial admin bootstrap |
| sessions | Server-side dashboard session ownership and lifecycle | Identifier/verifier, cookie/CSRF settings, expiry and invalidation |
| invitations | Admin-created single-use expiring links; recipient sets password | Token verification, expiry defaults, atomic redemption |
| api_keys | Per-user key identification/verifier, issuance and revocation | Key format, secure generation/hash, lookup and verification |
| mcp_servers | URL, immutable slug, enabled configuration, credential metadata/Secret references, observed health | Static-header/bearer representation, Secret lifecycle, removal semantics |
| mcp_tools | Last successfully discovered metadata and authoritative exposed/server/original-name mapping | Schema representation, refresh, stale markers and invalidation |
| audit_events | Required user/server/tool/time/duration/outcome and denied-call evidence | Denial fields, redaction, retention, persistence-failure handling |

Invitations are manually shared; no email delivery service is required initially. Known revoked keys may produce an attributed denied audit event; unknown invalid credentials must never be falsely attributed. The demo's known revoked-key attempt needs evidence without retaining its raw key. Audit writes and failure handling still need validation; the entity inventory is not proof of complete logging.

## Kubernetes and Helm boundaries

A10 starts with one application namespace for the mandatory single store. Public Ingress routes provide the storefront, dashboard, same-origin `/api`, and gateway `/mcp`. Internal Services connect PostgreSQL, MariaDB, WooCommerce MCP, arithmetic MCP, and store policy/reference MCP. Upstreams use ClusterIP without public Ingress, NodePort, or LoadBalancer exposure. Ingress controller, hosts, TLS approach, and detailed routing remain to be selected.

Gateway-held upstream authentication adds a caller boundary to internal addressing. ClusterIP alone does not isolate callers inside the cluster. Validate successful gateway calls, rejection without the gateway-held credential, and lack of external upstream exposure; do not claim packet-level gateway-only isolation without evidence. Calico and custom NetworkPolicy setup are not prerequisites for the first working core. NetworkPolicy may be considered after the mandatory flow works, if time allows or needed to strengthen the documented gateway-only boundary. The assignment's gateway-only outcome is not waived; residual exposure belongs in the [threat model](threat-model.md).

Persist WordPress content and MariaDB data as required by the assignment. The selected PostgreSQL state also needs persistent storage so users/keys/registry/audit data survive workload replacement. Storage classes, sizes, packaging, Secret access/injection, probes, and resource amounts are deployment-design details. Do not commit actual credential values in Helm values or other files.

A11 uses one application chart/release and environment values for domains, Ingress, storage classes, resource sizing, image versions, and Secret references as applicable. Do not duplicate local/production manifests. Decide chart dependencies and WordPress/MariaDB packaging at the Kubernetes/store milestone. The production walkthrough must explain Helm upgrade/rollback and its data/compatibility limits; live rollback remains optional under OPEN-01.

## Additional upstreams and cross-server demonstration

A12 selects arithmetic and store policy/reference servers for deterministic behavior, no external services, and an easily explained demo. Exact tool schemas and policy content remain to be designed. A harmless overlapping tool name on two servers may be introduced deliberately to demonstrate A4; no particular overlap tool is committed yet.

The planned prompt is: “Using today's WooCommerce orders, calculate today's total revenue and average order value.” WooCommerce supplies the orders and arithmetic performs the calculation. Define order inclusion, pagination, currency/rounding, refunds, and empty-order behavior when designing the tool/demo contract so the result is explainable; the assignment itself does not prescribe a revenue accounting definition.

## Unresolved assignment interpretations

These stable OPEN IDs preserve the original questions and links. A13 records reviewed approaches below; they are no longer all unanswered. Remaining implementation/client validation is explicit. The assignment wording is unchanged.

| ID | Assignment wording / uncertainty | Reviewed approach and remaining validation |
| --- | --- | --- |
| OPEN-01 | Optional stand-out upgrade/rollback overlaps mandatory video item 6 | Mandatory: document and explain the Helm production upgrade/rollback story. Live rollback execution remains optional unless later evidence changes the interpretation; OPT-09 is not selected |
| OPEN-02 | Member invitations are required; delivery/enrollment unspecified | Admin creates a single-use expiring link, manually shares it, and recipient sets a password. No initial email service; expiry/token details remain open |
| OPEN-03 | Disabled tools disappear in chat and external client; refresh timing unspecified | Immediately filter the gateway catalog for new requests and reject stale direct calls. Prototype must validate client notification/refresh and both displayed catalogs |
| OPEN-04 | Revoked key's next call is rejected and demo calls are correctly attributed | Known revoked keys may produce an attributed denied event; unknown invalid credentials must not be attributed to a guessed user. Validate demo evidence and denial fields without retaining raw keys |
| OPEN-05 | Kill an upstream pod and show Unreachable despite Kubernetes restart | Remove/stop an upstream, observe Unreachable, show healthy servers working, observe Kubernetes recovery, and return to Connected. Temporary scale-to-zero only if replacement is too quick to observe; restore the workload and verify recovery |
| OPEN-06 | Named clients include Inspector, but one prompt must use two upstreams | MCP Inspector for development/protocol diagnostics. Validate Claude Code or Cursor later for the interactive demo; architecture must not depend on either |
| OPEN-07 | Today's orders has no specified timezone | WooCommerce/store-configured timezone is authoritative. Local demo may use Asia/Kolkata; do not permanently hardcode it. Validate date-boundary conversion against the store API |

## Open and provisional decisions

- Vite, Docker, Minikube with Docker driver, and k3s remain proposed baseline selections. React, Kubernetes, and Helm are assignment constraints; Python/FastAPI, the SDK, PostgreSQL, MariaDB, and the boundaries above are accepted project choices. No versions are pinned or packages installed.
- Validate SDK/protocol versions, gateway/client interoperability, connection/session lifecycle, catalog notifications/refresh, tool-name limits, timeout defaults, and health observation in a later prototype.
- Specify authentication algorithms/formats, session/cookie/CSRF and invitation details, role representation, initial admin/WooCommerce registration, runtime Secret management, audit failure/denial/redaction/retention contracts, and schema constraints before affected implementation.
- Select the LLM/provider, chat-loop integration and response transport, exact WooCommerce REST/tool contracts, auxiliary tool schemas, and final interactive client. Define revenue demo data semantics and user A/B roles.
- Design WordPress/MariaDB packaging, chart dependencies, Ingress/DNS/TLS, storage, Secret injection/access, probes, and resources at the Kubernetes/store milestone. NetworkPolicy is deferred, not a first-core prerequisite.

No bonus or stand-out item is selected by this approval. [progress.md](progress.md) records current evidence; [project-journey.md](project-journey.md) records how the design evolved. Stop at documentation review before any application/prototype work.

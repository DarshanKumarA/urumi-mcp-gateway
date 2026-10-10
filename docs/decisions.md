# Decision register

This register explains project decisions; it does not override the [original assignment](source/urumi-mcp-gateway-assignment.docx) or [assignment.md](assignment.md). Assignment obligations are constraints, not choices attributed to us. “Accepted” means explicitly agreed, not implemented or verified. Architecture v1 approval is not authorization to begin application work.

## DEC-001 Governance before application implementation

- **Status:** Accepted, 2026-10-10. Stage 0 documents reviewed and committed as 51f27b2; current documentation extension awaits review.
- **Problem and decision:** Future sessions need durable scope and the user must understand each meaningful change. Begin with the nine governance files and preserve understand → plan → identify files → implement small change → review diff → validate → document → verify understanding.
- **Alternatives and rationale:** Starting code or a full scaffold would cross the user's milestone boundary. A small documentation baseline makes scope and proposals reviewable first.
- **Consequences:** Implementation and commits require the applicable authorization. The user later authorized the first governance commit separately. After meaningful steps, now check the chronological [project journey](project-journey.md), alongside current progress and individual decisions; preserve engineering reasoning rather than a terminal log.
- **Related scope:** Assignment / AI usage; all later requirements and milestones.

## DEC-002 Original assignment and separate traceability

- **Status:** Accepted, 2026-10-10; reviewed transcription and matrices committed in 51f27b2.
- **Problem and decision:** Informal summaries can omit requirements or promote optional features. Keep the DOCX authoritative, a faithful Markdown reading copy, and separate requirement/demo tracking and interpretations. Separate required threat analysis from optional hardening.
- **Alternatives and rationale:** DOCX alone is less convenient for future sessions; replacing it with an interpreted specification loses fidelity. Separate source and tracking preserve both meaning and verifiability.
- **Consequences:** Reconcile source changes explicitly. Keep interpretations visible and record implementation evidence separately from document approval.
- **Related requirements:** REQ-DEMO-01, REQ-DEL-04, REQ-DEL-05, REQ-DEL-07.

## DEC-003 Initial proposed technology baseline

- **Status:** Historical proposal, partially superseded by accepted Architecture v1 decisions DEC-004 through DEC-016 on 2026-10-10. Governance approval alone did not accept this baseline.
- **Original proposal:** React + Vite, Python + FastAPI, official Python MCP SDK, Python upstreams if authored here, PostgreSQL, WordPress + WooCommerce + MariaDB, Docker, Minikube with Docker driver, Helm, and k3s.
- **Assignment constraints:** React, WordPress/WooCommerce, Kubernetes, Helm rather than Kustomize, Kubernetes Secrets, and Streamable HTTP for custom server/supported upstreams. Local cluster alternatives and k3s are allowed examples, not mandated selections.
- **Alternatives and rationale:** Other backend/database choices and Kind/k3d were possible. The user's baseline gave a starting point for focused comparison, not proof of compatibility or necessity.
- **Current disposition:** Python/FastAPI, the official SDK, PostgreSQL, MariaDB, and the reviewed boundaries are accepted below. Vite, Docker, Minikube/Docker driver, and k3s remain proposed. Model/provider and exact versions remain open.
- **Consequences:** Verify SDK/protocol compatibility at implementation time and pin exact package versions. No dependencies are installed and no moving library default is a permanent contract.
- **Related requirements:** REQ-K8S-01, REQ-K8S-02, REQ-WOO-01, REQ-WOO-02, REQ-GW-02, REQ-UI-01, REQ-CHAT-01.

## Architecture v1 accepted decisions

All entries below were approved by the user on 2026-10-10. A1–A13 are the user's review IDs; DEC IDs are durable register IDs. Their documentation is under review and every runtime verification remains pending. [Architecture v1](architecture.md) records the shared contracts and open details.

### DEC-004 A1 One deployable backend

- **Constraint/problem:** Gateway management, MCP, authentication, auditing, and chat must cooperate; the assignment does not demand separate services.
- **Decision:** One Python/FastAPI backend with distinct internal modules for those responsibilities.
- **Alternatives and rationale:** Separate services introduce deployment and identity handoffs before the core needs them. Internal separation keeps responsibilities understandable with fewer deployable units.
- **Consequences/verification:** Validate framework/SDK integration and shared call behavior later; worker/replica counts are not fixed here.
- **Requirements:** REQ-GW-01, REQ-GW-02, REQ-TEAM-01, REQ-AUD-01, REQ-CHAT-01.

### DEC-005 A2 REST for dashboard MCP for tool clients

- **Constraint/problem:** A React dashboard and one external MCP endpoint are required; browser management transport is unspecified.
- **Decision:** Same-origin REST under `/api` for browser operations, `/mcp` for external MCP clients. Browser does not need to implement MCP.
- **Alternatives and rationale:** Making the browser an MCP client adds protocol/session work to ordinary management and chat interactions without solving a required need.
- **Consequences/verification:** Keep user identity and shared gateway behavior consistent across both entry paths; validate routing and client interoperability.
- **Requirements:** REQ-UI-01, REQ-TEAM-06, REQ-CHAT-01.

### DEC-006 A3 Official SDK with validated connection lifecycle

- **Constraint/problem:** Our custom server and upstream connections must use Streamable HTTP.
- **Decision:** Use the official Python MCP SDK. Defer permanent connection-pool/session strategy until an MCP prototype validates lifecycle behavior.
- **Alternatives and rationale:** Hand-writing the protocol increases maintenance; selecting per-call or long-lived connections without evidence would prematurely constrain the design.
- **Consequences/verification:** Verify compatible SDK/protocol/package versions and pin them at implementation time. Validate discovery, invocation, cleanup, refresh, and failure behavior; no library default is assumed permanent.
- **Requirements:** REQ-WOO-02, REQ-GW-01, REQ-GW-02.

### DEC-007 A4 Simple names with authoritative mapping

- **Constraint/problem:** Different servers may expose the same tool name; routing must remain unambiguous.
- **Decision:** Start with `<immutable_server_slug>__<tool_name>`. Store `exposed_name -> server_id -> exact_original_tool_name`; route by lookup, never parsing/reconstructing the upstream name.
- **Alternatives and rationale:** An always-present hash suffix obscures ordinary names. Parsing names couples routing to normalization. The simple prefix is understandable and the stored mapping preserves the exact destination.
- **Consequences/verification:** Validate name limits/normalization against actual clients. Add a deterministic suffix only for real normalization/length collisions; test overlapping names and exact routing.
- **Requirements:** REQ-GW-02, REQ-GW-03.

### DEC-008 A5 Configuration health and stale catalogs

- **Constraint/problem:** Dashboard statuses, complete enabled catalogs, failure isolation, and bounded calls are mandatory.
- **Decision:** Separate enabled/disabled configuration from connected/unreachable health. Retain last successful metadata for enabled unreachable servers, mark it stale, and fail calls clearly. Healthy servers continue independently.
- **Alternatives and rationale:** Dropping tools on transient failure hides the configured catalog; conflating disabled with unreachable obscures administrator intent.
- **Consequences/verification:** Timeouts are configurable defaults, not constants. Never automatically retry an ambiguous write after timeout. Validate stale metadata, healthy calls during failure, and error/timeout behavior.
- **Requirements:** REQ-GW-02, REQ-GW-04, REQ-UI-01.

### DEC-009 A6 Sessions roles and per-user keys

- **Constraint/problem:** Admin/member boundaries and hashed, revocable per-user MCP keys are required; dashboard login design is unspecified.
- **Decision:** Email/password with server-side sessions; individual Bearer MCP API keys shown once, never recoverably stored, verified with an appropriate hash/verifier. Check revocation on requests.
- **Alternatives and rationale:** Server-side sessions give dashboard lifecycle control without adding a separate identity service. OAuth is optional; self-contained tokens would still need revocation handling for the required next-call denial.
- **Consequences/verification:** Key identifiers/formats, password and key algorithms, session protection/expiry remain to be designed. Test revocation on an existing MCP session as well as a new request.
- **Requirements:** REQ-TEAM-01, REQ-TEAM-03, REQ-TEAM-04, REQ-TEAM-05, REQ-TEAM-06.

### DEC-010 A7 Credential ownership and Secret references

- **Constraint/problem:** Credentials must live in Kubernetes Secrets and upstream values must never reach browser/MCP clients.
- **Decision:** Recoverable service values in Secrets, metadata/references in PostgreSQL. WooCommerce REST credentials only in WooCommerce MCP; LLM credentials only in backend chat orchestration. Upstream read APIs never return credential values.
- **Alternatives and rationale:** Storing recoverable service values in ordinary database records or exposing them in read responses would violate the agreed boundary. Gateway keys identify users and are not forwarded upstream.
- **Consequences/verification:** Runtime Secret management, injection, rotation, and Kubernetes access mechanism remain subject to implementation validation; no controller or RBAC arrangement is selected. Validate response/log paths and workload credential access.
- **Requirements:** REQ-SEC-01, REQ-GW-05, REQ-WOO-09.

### DEC-011 A8 Minimal persistence inventory

- **Constraint/problem:** Users, access lifecycle, registrations, routing metadata, and audit history need durable state; the assignment does not prescribe tables or database technology.
- **Decision:** PostgreSQL with users, sessions, invitations, api_keys, mcp_servers, mcp_tools, audit_events as the initial entity inventory.
- **Alternatives and rationale:** Memory-only control state loses identities/history across restarts. Persisted tools support the accepted last-known catalog and exact routing mapping. Additional role/credential tables are not needed as an architectural commitment.
- **Consequences/verification:** This is not an ORM/schema. Role representation, fields, constraints, relationships, and data lifecycle remain to be designed; validate state survival and mapping consistency later.
- **Requirements:** REQ-GW-01, REQ-GW-02, REQ-TEAM-01, REQ-TEAM-02, REQ-TEAM-03, REQ-AUD-01.

### DEC-012 A9 Shared gateway path for chat

- **Constraint/problem:** Chat must use the gateway as the logged-in user, display tools, and produce correctly attributed audit events.
- **Decision:** Derive identity from the server-side session. Chat uses the same internal authorization, routing, timeout, and auditing path as the external MCP endpoint; never call upstreams directly.
- **Alternatives and rationale:** Direct upstream calls bypass required controls; a separate chat routing stack risks inconsistent behavior. Internal reuse within one backend avoids needing a second user credential or loopback transport.
- **Consequences/verification:** Discover usable tools through that path and display invoked tools. Validate identical authorization/failure/audit behavior and correct session-user attribution. LLM/provider and loop details remain open.
- **Requirements:** REQ-GW-07, REQ-CHAT-01, REQ-CHAT-02, REQ-AUD-01.

### DEC-013 A10 One namespace with internal upstreams

- **Constraint/problem:** Core workloads run in Kubernetes; WooCommerce MCP must be internal and gateway-only. Namespace count/network implementation are unspecified for the single-store core.
- **Decision:** One application namespace. Public storefront/dashboard/gateway MCP; internal PostgreSQL, MariaDB, and upstreams. Upstreams use ClusterIP with no public Ingress/NodePort/LoadBalancer, plus gateway-held upstream authentication.
- **Alternatives and rationale:** Multiple namespaces or Calico/custom NetworkPolicy prerequisites add work before the core flow. Defer NetworkPolicy until the mandatory flow works, if time allows or the documented boundary needs strengthening.
- **Consequences/verification:** ClusterIP alone does not prevent other cluster workloads reaching an address. Validate credential enforcement and external non-exposure; report residual risks honestly. Mandatory gateway-only behavior is not downgraded; no packet-level isolation is claimed.
- **Requirements:** REQ-K8S-03, REQ-K8S-05, REQ-WOO-08, REQ-GW-07.

### DEC-014 A11 One chart with environment values

- **Constraint/problem:** Helm and the same charts with local/production configuration changes are mandatory.
- **Decision:** Start with one application chart/release and separate local/production values.
- **Alternatives and rationale:** Multiple releases can later support independent lifecycle needs, but the first core benefits from one deployment boundary. Duplicated environment manifests drift and conflict with the agreed approach.
- **Consequences/verification:** WordPress/MariaDB packaging and exact chart dependencies await the Kubernetes/store milestone. Later render/validate both values configurations and document production changes.
- **Requirements:** REQ-K8S-02, REQ-DEL-03, REQ-DEL-04.

### DEC-015 A12 Deterministic auxiliary upstreams

- **Constraint/problem:** Three upstreams and one prompt using two servers are mandatory; the other servers are our choice.
- **Decision:** Add arithmetic and store policy/reference MCP servers requiring no external services. WooCommerce orders plus arithmetic support today's revenue and average-order-value prompt.
- **Alternatives and rationale:** Weather/search or other remote services add availability, credentials, and demo variability. Small deterministic servers are faster to explain and make the aggregation behavior visible.
- **Consequences/verification:** Exact tools/policy content and revenue input semantics remain to be designed. A harmless overlapping tool name may demonstrate namespacing. Validate real calls to both upstreams, not only a model-written answer.
- **Requirements:** REQ-GW-06, REQ-DEMO-01; DEMO-07.

### DEC-016 A13 Reviewed assignment interpretations

- **Constraint/problem:** The assignment specifies live outcomes but leaves timezone, refresh, enrollment, denied-call attribution, failure observation, and client mechanics unspecified; rollback wording overlaps optional and mandatory sections.
- **Decision:** Store-configured timezone defines today; Asia/Kolkata is only a possible local setting. Disabled servers are immediately absent for new gateway catalog requests and stale calls are rejected. Known revoked keys may yield attributed denials; unknown invalid credentials must not be falsely attributed.
- **Decision continued:** Use manually shared single-use expiring invitations with password enrollment. Demonstrate upstream removal/stop, Unreachable, healthy peers, Kubernetes recovery, and Connected; scale-to-zero is a fallback only when replacement is too fast to observe. Use Inspector for diagnostics and validate Claude Code or Cursor later for the interactive demo without client-specific architecture.
- **Scope decision:** Document/explain Helm upgrade/rollback as mandatory walkthrough material; live rollback execution remains optional unless later evidence changes that interpretation.
- **Alternatives and rationale:** Hardcoded timezone, an email delivery dependency, guessed audit identities, or equating a disabled server with a dead pod would obscure or unnecessarily expand the required outcomes. Client validation is needed because protocol diagnostics alone do not prove the two-upstream prompt works.
- **Consequences/verification:** OPEN-01 through OPEN-07 retain their IDs in [architecture.md](architecture.md#unresolved-assignment-interpretations), now with reviewed approaches and explicit remaining checks. No optional upgrade/security feature is promoted into core implementation.
- **Requirements:** REQ-WOO-05, REQ-GW-01, REQ-GW-02, REQ-GW-04, REQ-TEAM-02, REQ-TEAM-03, REQ-TEAM-06, REQ-AUD-01, REQ-DEL-04; DEMO-04 through DEMO-11, VID-06.

## Recording future decisions

Use a new stable DEC ID with status/date, problem, source constraints and requirement IDs, choice, alternatives, rationale, consequences, and validation needs. Explicitly supersede old entries rather than rewriting history. Record chronological evolution in [project-journey.md](project-journey.md) and current evidence in [progress.md](progress.md). Unvalidated details remain open even when their surrounding architecture is accepted.

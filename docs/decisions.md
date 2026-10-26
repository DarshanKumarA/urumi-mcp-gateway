# Decision register

### DEC-034 Stage 8 explicit ordering and caller isolation

- **Status:** Implemented for static review, 26 October 2026; no cluster start/deployment.
- **Choice:** Normal revisioned migration and admin/three-peer bootstrap Jobs with bounded dependency waits; gateway init/readiness require exact schema plus durable receipts. This supports fresh PostgreSQL in one release without pre-install hooks or startup DDL. Existing migrations are unchanged.
- **Persistence:** Official PostgreSQL 18.6-bookworm pinned amd64; retained 2-GiB StatefulSet claim independent of store storage. Insert-once receipts preserve edits/removal and admin passwords. Backup/node-loss durability remains distinct.
- **Isolation:** External Woo service token checked every MCP request and carried by existing gateway credential/routing model. Three targeted MCP ingress policies permit gateway only; PG permits gateway and DB jobs. No broad egress lockdown or business redesign.
- **Configuration:** Separate same-origin application Ingress; exact Origin-derived SDK Host allowance; production HTTPS/Secure cookies via values. Only Woo/gateway images change to stage8.0. Exact nine-Secret contract is in root README.
- **Limits:** Upstream values remain unencrypted at application level; initial PG account is owner/superuser. Rotation requires coordinated operator review. NetworkPolicy depends on enforcing CNI and trustworthy Pod-label permissions. Full-stack RAM, TLS and Kubernetes isolation remain unproven.

This register explains project decisions; it does not override the [original assignment](source/urumi-mcp-gateway-assignment.docx) or [assignment.md](assignment.md). Assignment obligations are constraints, not choices attributed to us. “Accepted” means explicitly agreed, not implemented or verified. Architecture v1 approval is not authorization to begin application work.

## DEC-001 Governance before application implementation

- **Status:** Accepted, 2026-10-10. Stage 0 documents reviewed and committed as 51f27b2; Architecture v1 documentation and the journey subsequently reviewed and committed as db49836.
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

- **Status:** Historical proposal, partially superseded by accepted Architecture v1 decisions DEC-004 through DEC-016 on 2026-10-10, and the local cluster choice in DEC-017 on 2026-10-11. Governance approval alone did not accept this baseline.
- **Original proposal:** React + Vite, Python + FastAPI, official Python MCP SDK, Python upstreams if authored here, PostgreSQL, WordPress + WooCommerce + MariaDB, Docker, Minikube with Docker driver, Helm, and k3s.
- **Assignment constraints:** React, WordPress/WooCommerce, Kubernetes, Helm rather than Kustomize, Kubernetes Secrets, and Streamable HTTP for custom server/supported upstreams. Local cluster alternatives and k3s are allowed examples, not mandated selections.
- **Alternatives and rationale:** Other backend/database choices and Kind/k3d were possible. The user's baseline gave a starting point for focused comparison, not proof of compatibility or necessity.
- **Current disposition:** Python/FastAPI, the official SDK, PostgreSQL, MariaDB, and the reviewed boundaries are accepted below. DEC-017 replaces the Minikube/Docker-driver proposal with k3d, using Docker Desktop as the intended runtime. Vite and k3s for the production-like VPS remain proposed. Model/provider and exact versions remain open.
- **Consequences:** Verify SDK/protocol compatibility at implementation time and pin exact package versions. No dependencies are installed and no moving library default is a permanent contract.
- **Related requirements:** REQ-K8S-01, REQ-K8S-02, REQ-WOO-01, REQ-WOO-02, REQ-GW-02, REQ-UI-01, REQ-CHAT-01.

## Architecture v1 accepted decisions

DEC-004 through DEC-016 were approved by the user on 2026-10-10 and their documentation committed as db49836. A1–A13 are the user's review IDs; DEC IDs are durable register IDs. Every runtime verification remains pending. [Architecture v1](architecture.md) records the shared contracts and open details.

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

## DEC-017 Local k3d after environment preflight

- **Status:** Accepted by the user, 2026-10-11, after review of the Stage 2 preflight. Supersedes only DEC-003's proposed local Minikube/Docker-driver selection; no software installed or cluster created.
- **Constraint/problem:** The assignment permits Kind, k3d, or Minikube and requires stable storefront/dashboard URLs through Ingress. Our Windows environment needs a practical host-to-Ingress access path with Docker Desktop as the intended runtime.
- **Decision:** Select k3d for local Kubernetes. k3s for the production-like VPS remains proposed; neither k3d nor k3s is an assignment mandate.
- **Alternatives and rationale:** Minikube remains permitted, but its Docker-driver node IP is not directly reachable from Windows/WSL2 hosts, adding access setup to our stable-URL plan. k3d exposes Ingress through explicit Docker host port mappings and runs k3s in Docker, aligning the local distribution with the proposed VPS distribution. Kind also remains valid, but does not provide that k3s alignment. This is a project-specific choice, not a claim that Minikube cannot work.
- **Consequences:** Keep A10's namespace/public/internal boundaries and A11's one-chart/environment-values approach. Sharing k3s does not prove VPS compatibility. Defer exact tool/image versions, node count, resource budget, ports, hostnames, Ingress controller, and storage details to the next reviewed design step. Recheck available RAM before cluster creation.
- **Evidence and limits:** Read-only preflight found existing developer tools and WSL, missing Docker/kubectl/Helm, sufficient CPU/disk for initial planning, and tight available RAM. A supplemental read-only check did not detect k3d. No Docker engine, cluster connectivity, Ingress, Helm deployment, or workload resource behavior has been validated. The [journey](project-journey.md#stage-2--environment-preflight-and-local-cluster-selection) preserves the concise findings.
- **Technical references:** Reviewed the official [Minikube Docker-driver limitations](https://minikube.sigs.k8s.io/docs/drivers/docker/), [k3d overview](https://k3d.io/stable/), and [k3d Ingress port-mapping guide](https://k3d.io/stable/usage/exposing_services/). These support the design rationale, not evidence of successful operation on this machine.
- **Requirements:** REQ-K8S-01, REQ-K8S-02, REQ-K8S-05, REQ-DEL-04; VID-02, VID-06. Requirement statuses and mandatory/optional classifications do not change.

## Store Architecture v1 accepted decisions

DEC-018–DEC-021 were accepted on 2026-10-12, including the corrected RAM conclusion. They resolve the store details deferred by DEC-013/DEC-014; those earlier entries remain historical. Full contracts and selected digests are in [Store Architecture v1](architecture.md#accepted-store-architecture-v1). Accepted means designed, not implemented or runtime-verified.

### DEC-018 Store packaging and exposure

- **Problem/constraints:** The mandatory store needs persistent Kubernetes workloads, stable Ingress access and one Helm deployment supporting local/production values.
- **Decision:** One urumi application namespace and one application chart/release, using our own minimal templates and standard upstream images. WordPress is a one-replica Deployment with Recreate; MariaDB is a one-replica StatefulSet. WordPress uses ClusterIP plus existing Traefik, with local URL http://store.urumi.test:8080 and documented hosts mapping. MariaDB uses only an internal Kubernetes Service. COD supplies the checkout demo; business dates follow the store timezone.
- **Alternatives/rationale:** A third-party WordPress chart or custom image adds behavior to learn and maintain before the required flow. Multiple releases are unnecessary for the initial core. A StatefulSet provides database identity/storage continuity, not replication or high availability; internal addressing is not network isolation.
- **Consequences/validation:** Production host/TLS/storage differences belong in values. Validate rendered configurations, browser access, checkout and admin order visibility later; exact initial store settings and production TLS provisioning remain open. No chart, namespace or workload is created by this record.
- **Requirements:** REQ-STORE-01, REQ-K8S-02, REQ-K8S-03, REQ-K8S-05, REQ-DEL-03; DEMO-01/02.

### DEC-019 Finite bootstrap and independent health checks

- **Problem/constraints:** Reproducible initial installation must not erase an existing store, and dependency failure must not cause healthy web processes to restart repeatedly.
- **Decision:** A finite idempotent official WP-CLI Job waits for authenticated database access and initialized webroot files. Install only if absent, verify/install pinned WooCommerce, activate as needed, complete initial COD/demo configuration, verify and finish. Preserve passwords, users, products and orders. A different installed version requires an explicit upgrade plan. Use release-revision Job names, bounded retries/deadline and Helm workload/Job waiting; keep current status/logs until a later release operation/uninstall. Co-locate Job and WordPress on one node for their shared RWO claim and verify filesystem identities.
- **Alternatives/rationale:** This supersedes the proposed pre-Apache init-container bootstrap. A pre-install hook lacks ordinary resource dependencies; a post-install hook with Helm --wait can deadlock against WooCommerce-dependent WordPress readiness. A normal Job can run while WordPress is Unready; revision naming avoids immutable Job-template updates.
- **Health decision:** WordPress TCP startup/liveness independent of MariaDB; bounded inline PHP readiness checks loaded database state, active WooCommerce and initial bootstrap completion. No custom public health files. MariaDB uses its image-supplied connection/InnoDB health checks. The finite Job is observed through completion, deadline and retry status.
- **Consequences/validation:** TCP liveness does not prove PHP request correctness. Test startup, safe/partial reruns, permissions, failure behavior and checkout. Do not mistake a DB connection failure for an uninstalled store. Pod restart does not automatically rerun a completed Job; rollback is not data restoration.
- **Requirements:** REQ-STORE-01, REQ-K8S-04, REQ-K8S-06; DEMO-01/02, VID-02/06.

### DEC-020 Persistent webroot retention and external Secrets

- **Problem/constraints:** Persistent store data and Kubernetes Secrets are required. An ordinary Helm uninstall should not silently destroy store data.
- **Decision:** WordPress uses a 2 GiB RWO claim for all /var/www/html; MariaDB uses a separate 5 GiB RWO claim at /var/lib/mysql. Retain the WordPress claim with helm.sh/resource-policy: keep; explicitly retain StatefulSet claims on deletion/scaling. Keep namespace and Secrets outside release ownership. Reuse retained claims and original credentials deliberately on reinstall.
- **Alternatives/rationale:** Full-webroot persistence replaces the proposed wp-content-only PVC plus emptyDir/core preparation, using the standard image's empty-webroot initialization. It simplifies the first implementation, but image changes do not automatically replace persisted WordPress core/plugins. Retention is selected over automatic deletion to reduce accidental data loss.
- **Credential decision:** External Secrets separate root DB, application DB, initial WordPress admin, and WordPress auth keys/salts. The future WooCommerce REST Secret belongs only to the custom MCP server. Chart values hold references only. The future PowerShell helper uses masked input/secure generation and in-memory stdin submission; it preserves existing values and avoids plaintext files, Helm --set credentials and payload logs. See the exact object/key contract in architecture.
- **Consequences/validation:** Two volumes provide Pod-replacement durability only, not node-loss protection or backup. Helm rollback does not rewind database contents or persisted files. Namespace deletion can destroy retained claims and Secrets: never reuse the disposable Stage 2 cleanup procedure for urumi. Validate retention/reuse and credential scoping later. Backup requires recoverable copies outside the failure boundary and restore verification; no automatic backup tooling is selected here.
- **Requirements:** REQ-K8S-04, REQ-SEC-01, REQ-DEL-04; VID-02/04/06.

### DEC-021 Version baseline and measured capacity gate

- **Problem/constraints:** The store needs compatible, reproducible components with resource requests/limits; sufficient memory for a first attempt is not evidence of full-system capacity.
- **Decision:** Accept WordPress 7.1.3/PHP 8.3 Apache, WP-CLI 2.12.0/PHP 8.3, MariaDB 11.4.13 and WooCommerce 11.2.1 with the reviewed Linux/amd64 digests/archive checksum recorded in architecture. Reconfirm pins before deployment and handle application upgrades explicitly. Keep reviewed requests/limits as starting budgets to measure, not allocations increased because more RAM is available.
- **Alternatives/rationale:** Floating tags are not reproducible. WooCommerce 11.2.1 supersedes the 11.2.0 candidate for its checkout fixes. Official metadata/source checks support the set but do not establish runtime compatibility; the stale plugin readme Stable tag and configuration-blob request failures are recorded in architecture.
- **RAM correction:** The user's accepted 2026-10-12 report is approximately 15.7 GiB total, 11.6 GiB used, 4.1 GiB available. It supersedes the earlier ~1 GiB blocking conclusion: **PASS for initial Stage 3 deployment attempt; full-stack capacity still unproven.** This is not a fresh Codex measurement or deployment authorization.
- **Consequences/validation:** Recheck memory immediately before first Helm install, including node scheduling headroom. Measure host/node/workload memory during MariaDB startup, WordPress startup, bootstrap, storefront/admin use and checkout. Stop and tune on OOM kills, unexplained restarts, severe host pressure or insufficient scheduling capacity before adding further components.
- **Requirements:** REQ-STORE-01, REQ-K8S-07, REQ-DEL-04; DEMO-01/02, VID-02/06.

### DEC-022 Bootstrap ownership, versioned assets and readiness implementation

- **Status:** Stage 3.3 implemented for static review on 2026-10-12; no runtime evidence. The user explicitly accepted India/Asia-Kolkata/INR and unrestricted free shipping with COD as demo defaults.
- **Problem/constraints:** Finish DEC-019's finite, nondestructive bootstrap and dependency-aware readiness without exposing secrets or public health endpoints.
- **Implementation choice:** Revision-specific immutable script ConfigMap via Helm .Files, paired with a normal revision-named Job; UID/GID 33, shared RWO PVC and required same-node WordPress affinity. Separate file/DB waits, bounded commands/deadline, stdin initial admin password and exact archive checksum. Persistent ownership/settings checkpoints permit known partial configuration to resume and make completed runs verification-only. Record completion only after successful checks; require a positive script acknowledgement.
- **Alternatives/trade-offs:** Refuse automatic adoption/repair of an unknown or partial store rather than infer that DB errors mean a fresh install. The core-install-to-ownership crash window requires manual review. Full WordPress loading in readiness costs more than TCP but checks the required application state; the kubelet deadline bounds it, and startup/liveness retain the independent listener check.
- **Upgrade/rollback:** Helm creates new targets before deleting obsolete resources; serialize releases and finish/stop the prior Job before another operation. Rollback reuses historical rendered names, so a missing Job can rerun while an existing terminal Job need not. No automatic migration, database restoration or rollback of webroot files is implied. Versioned assets prevent live script changes in older Jobs.
- **Security:** Scripts/configuration are non-secret ConfigMap data; mounted Secrets supply app DB, initial admin and auth material. No root/REST credential in the Job, no Kubernetes API token needed, no password in command arguments. Disable unattended core/plugin updates to preserve the pin; manually review security updates. Error messages are bounded/sanitized, without claiming defense against arbitrary malicious PHP.
- **Validation/limits:** Shell syntax, lint/renders, schemas, static relationships/safety and registry/archive pins pass; PHP syntax checking is unavailable and must precede deployment. Runtime permissions, dependency failures, idempotency, scheduling, checkout and resource consumption remain unverified. See [implementation contract](architecture.md#stage-33-bootstrap-and-readiness-implementation) and [validation](progress.md#stage-33-bootstrap-and-readiness-static-validation).
- **Requirements:** REQ-STORE-01, REQ-K8S-02 through REQ-K8S-07, REQ-SEC-01, REQ-DEL-03/04; DEMO-01/02, VID-02/06. Static implementation is not completion.

### DEC-023 Local store Secret helper modes and create-only submission

- **Status:** Implemented for static/offline review on 2026-10-13; no real Secret or cluster action. Completes the helper implementation portion of DEC-020, not runtime verification.
- **Problem/constraints:** Prepare exactly four externally owned store Secrets without plaintext files/arguments/output, automatic rotation or namespace creation. WooCommerce REST credentials remain deferred until WooCommerce is live.
- **Choice:** PowerShell 7 helper defaults to offline Validate; Check is read-only; explicit Create checks fixed context/active namespace and all existing Secrets before creating absent objects. Exact keys and nonempty UTF-8 credential text are verified; existing values are preserved. .NET RNG supplies 256-bit DB passwords and 512-bit auth values; the admin chooses a password through a masked prompt.
- **Alternatives/trade-offs:** In-memory JSON on kubectl stdin avoids literal command arguments and temporary files. Use create rather than apply: a concurrent creator must fail, not replace another value. Redirect/drain child streams and emit sanitized operation errors; detailed raw kubectl diagnostics are deliberately unavailable. Partial writes are possible; read current state on retry. Immutable managed strings cannot be reliably erased. No automatic rotation or retained-volume credential recovery is added.
- **Validation/limits:** PowerShell parser/default/Validate and argument rejection passed. Twelve mocked workflows cover preservation, absent objects, preflight failures, create races and partial failure; a local child-process fixture checks output suppression/capture. Static chart contract checks and credential scan pass. Strict-mode optional fields, flag separation and stray task-result output were corrected during validation. PSScriptAnalyzer is unavailable; actual interactive input, Kubernetes behavior and workload credential consumption remain unverified. See [helper contract](architecture.md#local-store-secret-preparation).
- **Requirements:** REQ-SEC-01, REQ-DEL-01/04/05; VID-02/04/06. No runtime requirement is complete.

### DEC-024 Deterministic permalinks and a recognized bootstrap migration

- **Status:** Implemented for static review on 2026-10-20 following the user's Stage 3.7 correction request. No live setting change, upgrade, bootstrap execution or checkout. Supersedes DEC-022's lack of a migration path only for this explicit v1-to-v2 transition.
- **Problem:** /shop/ returned the blog with HTTP 200 because the original bootstrap left Plain permalinks. Query-string product access worked, and product 11 already existed. Manually saving Settings > Permalinks would leave deployment source incomplete.
- **Choice:** Fixed /%postname%/ in bootstrap contract v2; preserve every prior contract field and business-setting checkpoint. Accept completed v1, fresh/resumable v2 and the precise interrupted-finalization state; reject other versions, ownership or setting drift. Use supported WP-CLI structure/hard-flush APIs with Apache module configuration in temporary Job storage. Verify persisted DB routes and the managed .htaccess block before ownership/marker advancement; readiness checks the new marker and structure.
- **Alternatives/trade-offs:** Keeping marker 1 would allow old readiness to report success without the new routing contract. A bare version bump is rejected by old owner/marker checks. Direct SQL, blanket settings resets and manual browser configuration do not provide the required reproducible lifecycle. A soft flush alone does not verify Apache persistence; the hard flush preserves outside-block directives. Existing files/data remain, except the intentional WordPress rewrite-block update.
- **Failure/rollback:** Operations across DB and shared files are not transactional. Retries accept only old/target states and reverify before completion. No automatic downgrade is defined; revision-1 readiness cannot accept marker 2 after migration. Serialize release operations, stop on failure and preserve data. Single-replica Recreate implies an upgrade availability gap.
- **Evidence/limits:** Pinned Apache read-only inspection supports mod_rewrite, AllowOverride and UID/PVC permissions. PHP/shell syntax, 50 isolated fixture assertions, Helm lint/renders, v1.35.5 schemas and relationship checks pass. Fixtures neither load WordPress nor use its database. Real migration, HTTP route contents, rerun behavior, checkout and rollback remain unvalidated; see [migration contract](architecture.md#stage-37-deterministic-permalinks-and-explicit-v1-to-v2-migration).
- **Requirements:** REQ-STORE-01, REQ-K8S-05/06, REQ-DEL-03/04; DEMO-01/02, VID-02/06. No requirement is marked complete.

### DEC-025 Public Live store contract and v2-to-v3 migration

- **Status:** Implemented for static review on 2026-10-21 under the user's Stage 3.7C request; no live deployment or option change. The user requires public Live demo visibility; code remains subject to review.
- **Problem/constraint:** Order 12 verifies a guest COD transaction, but anonymous shop/product pages show Coming Soon. The assignment's storefront flow requires usable visitor-facing pages. v2 ownership/readiness does not cover visibility, and a bare version bump is rejected.
- **Choice:** v3 requires both WooCommerce visibility options to equal no. Explicitly accept completed matching v2, owned fresh/partial v3 and the precise v3-owner/marker-2 completion window. Before writes verify existing settings/rewrites; accept only yes/yes, no/yes and no/no before v3 ownership completion. Completed v3 must already be no/no. Use supported WordPress option APIs in a separate make-live step, then fresh-process verification, ownership v3 and marker 3 last.
- **Alternatives/trade-offs:** A manual admin toggle would leave bootstrap incomplete. Keeping version 2 would conceal a new invariant behind an old marker. A permissive settings reset or direct v1-to-v3 jump broadens migration beyond reviewed states. Both visibility options join readiness without frontend HTTP; successful probes still need anonymous body-content acceptance. Existing hard rewrite regeneration remains idempotent; completed configuration drift is refused before mutation.
- **Preservation/security:** No reinstall, user/password/product/order reset, Secret/PVC/budget/image change or new resource type. Publishing the intended catalog does not authorize customer-data disclosure. The exact historical cause/time of live yes/yes is not proven. Checkpoints are not tamper-proof security controls; concurrent release writers remain prohibited operationally.
- **Failure/rollback:** Visibility/ownership/marker are separate writes; retries accept only the documented states. Finalize never repairs incomplete visibility. Revision-2 rollback cannot rewind persisted data/files and its marker-2 probe rejects marker 3; automatic rollback is unsafe. Keep order 12 and product 11 intact and inspect before recovery.
- **Validation:** Shell/PHP syntax, 95 isolated migration assertions, both Helm lints/renders, v1.35.5 schemas and relationships passed. Exactly eight objects per environment, no Secret/Namespace. Runtime migration/anonymous content remain pending; Stage 3.7 and persistence tests are not complete. Full lifecycle: [architecture](architecture.md#stage-37c-public-live-visibility-and-explicit-v2-to-v3-migration).
- **Requirements:** REQ-STORE-01, REQ-K8S-06, REQ-DEL-03/04; DEMO-01/02. Exact option settings implement the user-approved demo contract; they do not alter assignment text or select optional hardening.

## Accepted Stage 4 WooCommerce MCP decisions

Accepted by the user for recording on 2026-10-23. These choices refine Architecture v1; only the offline REST Secret helper is implemented in Stage 4.2. No MCP/runtime/security requirement is marked complete. Detailed contracts are in [architecture](architecture.md#accepted-woocommerce-mcp-design).

### DEC-026 Current SDK protocol and narrow adapter

- **Constraint/problem:** REQ-WOO-01/02 require our own Streamable HTTP MCP server; older session-based tutorials must not dictate the current design.
- **Decision:** Official mcp==2.3.0, Python 3.13, protocol 2026-07-28, SDK MCPServer/Streamable HTTP at /mcp; exactly five initial tools. Modern requests are stateless; stateless_http=True also removes retained legacy sessions. No handwritten JSON-RPC or separately installed Woo MCP server/plugin.
- **Responsibility:** Woo MCP owns tool schemas/implementations, Woo REST client/authentication, bounded calls, normalized responses and safe errors. Gateway identity/roles/keys/sessions/audit/chat/routing stay outside it. No local database or queue.
- **Alternatives/trade-offs:** Handwritten transport duplicates protocol work; old stateful defaults add unnecessary lifecycle complexity. Stateless legacy mode gives up callbacks that these tools do not need. SDK release behavior is documented, not a completed interoperability test.
- **Validation:** Pin resolved transitive/signer dependencies later; test modern and legacy discovery/calls, output/error schemas and actual write counts. No Python dependency files/server exist yet. [Release evidence](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.3.0), [SDK compatibility](https://py.sdk.modelcontextprotocol.io/run/legacy-clients/).

### DEC-027 Internal REST transport with canonical OAuth signing

- **Constraint/problem:** REQ-WOO-09 needs a documented store interface; local Service HTTP must use Woo's documented authentication. Windows hosts-file resolution cannot be assumed inside Pods.
- **Decision:** Connect to http://urumi-wordpress.urumi.svc.cluster.local; sign against http://store.urumi.test:8080; use /wp-json/wc/v3 and Host store.urumi.test:8080. OAuth 1.0a HMAC-SHA256 in Authorization via an established pinned library; redirects disabled. Future verified HTTPS permits Basic authentication. No query-string credentials or manual signing cryptography.
- **Rationale/evidence:** Pinned Woo 11.2.1 derives its OAuth base URI from the configured home URL. Separate connection/signing origins preserve Service traffic without changing WordPress's canonical URL. [Woo authentication source](https://raw.githubusercontent.com/woocommerce/woocommerce/11.2.1/plugins/woocommerce/includes/class-wc-rest-authentication.php).
- **Alternatives/trade-offs:** Public-host traffic introduces cluster DNS/Ingress dependencies; signing only Service DNS can mismatch Woo verification. HTTP remains plaintext and JSON bodies are not signed by this scheme. Public Ingress TLS does not encrypt a separate HTTP Service hop.
- **Gate:** Mapping is unproven. Stage 4.3 must validate one authenticated read, header forwarding and no redirect before full MCP implementation. Failures stop for review, not credential-in-URL workarounds. REQ-SEC-01/GW-05 boundaries remain.

### DEC-028 Five bounded tools with minimal responses

- **Constraint/problem:** REQ-WOO-03 through REQ-WOO-07 require product/order operations; DEMO-04 needs store-local "today"; shared credentials must not imply unrestricted object disclosure.
- **Decision:** Accept list_products/create_product/list_orders/get_order/update_order_status and the exact [schemas/DTOs](architecture.md#five-initial-tool-contracts). Pagination defaults to 20, maximum 50. Use Decimal strings, explicit store-timezone date windows, simple-product creation, SKU conflict refusal and a required expected_status guard for updates. Six writable statuses exclude refunds/trash/drafts; no separate fulfillment state machine.
- **Privacy/failure:** Allowlist operational fields; omit customer contact/address/note/order-key/metadata. Safe SDK tool errors, bounded requests, no automatic REST retries and no ambiguous-write replay. Unknown write outcome is not rollback. No silent oversized-result truncation.
- **Trade-offs:** Optional SKU permits name/price-only creation but weakens ambiguous-write recovery. Read-before-write is not atomic; status changes can invoke Woo hooks. Adapter-local readiness keeps discovery available during store failures but does not prove store health.
- **Validation:** Unit/date-boundary, mocked REST/auth/errors/single-write, protocol and later live store tests; exact response-size limits remain implementation-time choices. Accepted design is not implementation evidence.

### DEC-029 Dedicated REST Secret helper and deferred upstream authentication

- **Constraint/problem:** REQ-SEC-01/GW-05 require workload-scoped server credentials. Existing store helper owns four different Secrets; REST keys must be issued by WooCommerce, not invented by a script.
- **Decision:** Add only scripts/setup-woocommerce-rest-secret.ps1; preserve setup-store-secrets.ps1. Fixed k3d-urumi-local/urumi/urumi-woocommerce-rest with exact consumer-key/consumer-secret keys and Opaque type. Default Validate is offline; future Check projects identity/type/key names; future Create preserves valid objects or uses two masked prompts and memory-only stdin to create an absent object.
- **Failure/security:** No credential args/env/files/output, no raw child/exception output, no namespace creation, no apply/patch/replace/delete/retry. Conflicting objects stop. Check validates structure only, not credential contents or authentication. Byte/BSTR clearing does not guarantee managed-string erasure. Kubernetes audit/admission and trusted-host logging are outside the helper's guarantee.
- **Ownership:** Only Woo MCP consumes REST credentials. Initial local issuance can use the existing administrator with acknowledged broad authority; least-privilege service-user work remains separately scoped. No real issuance or Secret creation occurs in Stage 4.2.
- **Explicit deferral:** Preserve A10's gateway-only caller requirement, but defer urumi-woo-mcp-auth and service-token middleware until gateway integration per the user's Stage 4.2 instruction. Internal-only deployment/no Ingress remains required; ClusterIP alone cannot satisfy caller isolation. Do not declare REQ-WOO-08 verified before authentication and external non-exposure tests.
- **Validation:** Offline parser/manifest/workflow fixtures only in this milestone; real prompts, kubectl projection/submission and authenticated connectivity remain Stage 4.3 operational evidence. This is not the optional gateway OAuth feature or a selection of optional hardening.

### DEC-030 Stage 5.2 persistent registry and credential baseline

- **Status/date:** Accepted implementation scope, 2026-10-25; validation awaits user review.
- **Problem/source:** REQ-GW-01/02/05 and REQ-UI-01/02 need durable registrations, safe management and Woo pre-registration; A1/A2/A8 select one FastAPI backend, REST and PostgreSQL.
- **Decision:** SQLAlchemy 2.0.55 Core, Psycopg 3.3.6, Alembic 1.20.1, FastAPI 0.162.0; keep the existing gateway repository seam and official SDK /mcp lifespan. Worker-thread DB transactions avoid blocking ASGI and Windows async-driver policy complications. Explicit migration, no implicit startup DDL.
- **Schema/seed:** Immutable UUID/unique slug, mutable configuration, revision-guarded health and last-good tool JSON; no arbitrary results. One-time receipt creates WooCommerce only if needed and never overwrites managed fields or resurrects a removed seed. Deletion removes its credential/cache; future audits must not cascade away.
- **Credential refinement of DEC-010:** The explicit Stage 5.2 instruction chooses server-side PostgreSQL credential values without application encryption for this checkpoint, deferring the earlier Secret-reference mechanism. Read DTOs never expose values; PATCH omission preserves/object replaces/null clears. This is a current security limitation, not a change to assignment wording or a claim that REQ-SEC-01 is complete. Final Kubernetes credential handling remains unresolved before deployment. Optional encryption is not implemented.
- **Alternatives/trade-offs:** Memory loses state; SQLite tests are fast but cannot prove PostgreSQL behavior; a custom ORM is unnecessary. Standard SQLAlchemy Core is enough for this small registry. JSON metadata keeps deletion atomic without adding a tool-result store. Last-good metadata is useful for management but never trusted blindly for live MCP discovery.
- **Validation/limits:** 80 tests including all 51 gateway regressions; real disposable PostgreSQL 18.0 migration/repository smoke. No management identity/roles, API keys, audit, React/chat, public deployment or broad SSRF protection. Current endpoints are unauthenticated local development only.

### DEC-031 Stage 5.3 identity lifecycle and REST authorization

- **Status:** Implemented for review, 25 October 2026; Stage 5.2 checkpoint 05509a7 retained.
- **Decision:** Current instruction selects immutable usernames, refining DEC-009's email-login proposal. Same PostgreSQL backend, explicit 0002_identity, admin/member roles, no startup schema/admin creation. Separate protected-file bootstrap creates the first admin once and rejects conflicts without resetting passwords.
- **Verification storage:** Argon2id via argon2-cffi 25.1.0 and library salts/defaults for human passwords. Independent 256-bit random session/invitation/API-key tokens use SHA-256 digests; raw keys/invites shown once, session only in HttpOnly cookie. High-entropy token hashing differs from costly password hashing. Safe prefix identifies keys; verifier checks current revocation/disabled state.
- **Browser boundary:** Opaque 8-hour sessions, SameSite=Lax, Path=/, host-only HttpOnly cookie. Production requires Secure and HTTPS. Every unsafe REST request requires exact configured Origin; missing/null/cross-origin or conflicting Fetch Metadata fails. No permissive CORS. This is CSRF protection, not defense against XSS or a replacement for authentication. Shared admin guard protects all server management.
- **Lifecycle:** Member-only intended-username invites default to 24 hours and redeem atomically once. Own key issuance/revocation and admin member-key metadata/revocation are supported; raw keys are unrecoverable. Restrictive user references preserve future attribution. Registry credential PATCH/seed/health behavior remains unchanged.
- **Limits:** No JWT/OAuth framework, fake identity, email delivery, rate limits, recovery/MFA or bonus encryption. Python strings cannot be reliably zeroized. Disabled accounts fail; re-enabling restores otherwise valid unrevoked tokens. External /mcp authorization and audit remain Stage 5.4; no public deployment.
- **Evidence:** 130 tests including all 80 prior gateway tests; disposable PostgreSQL 18.0 empty migrations, concurrent admin/invitation operations, hash persistence, reconnect and revocation. Kubernetes stopped; no real credentials or Woo calls.

### DEC-032 Stage 5.4 request identity and durable invocation audit

- **Status/date:** Implemented for review, 25 October 2026, under the approved Stage 5.4 scope; Stage 5.3 checkpoint a3816e0 retained.
- **Source/problem:** A6/A9 and REQ-TEAM-05/REQ-AUD-01 require immediate key revocation and attributable tool invocation, with the same future chat path. A connection-level login or post-call-only log could allow revoked callers or unaudited mutations.
- **Decision:** Verify Bearer key on every SDK HTTP request; copied ASGI request state holds an immutable safe principal, never a global current user. Strip Authorization before SDK dispatch. Central InvocationService wraps existing routing; future chat supplies a session-derived principal to that same service.
- **Durability:** Explicit 0003_audit commits START before upstream work, then commits authoritative original-name binding before business dispatch and finalizes a fixed outcome/code afterward. Failed START/binding means no business execution. Failed finalization reports unknown outcome/unsafe retry and never replays the upstream.
- **History/privacy:** User/key restrictive FKs plus username snapshot; server UUID/slug are immutable historical snapshots without a cascading FK. No arguments/results/tokens/hashes/headers/exception bodies. Unknown caller tool strings use an unresolved sentinel rather than persisting potential secrets; meaningful known route metadata is retained. Admin-only bounded audit query, no mutation/deletion API.
- **Trade-offs:** Per-request DB verification adds latency but avoids revocation-cache invalidation. Separate audit commits add DB work and fail closed on audit outage. A remote mutation and PostgreSQL are not one transaction; crashed/cancelled started records are interrupted/unknown. No exactly-once claim, distributed transaction, queue or repair worker. Revocation does not cancel already-dispatched work. Discovery/authentication failures are not normal tool-call audit events; their denial is demonstrated by protocol tests.
- **Validation/limits:** 160 tests including all 130 prior regressions; current/legacy official-client revocation and concurrent two-user attribution; real PostgreSQL migration/history smoke. Dashboard/chat, runtime hosting, audit retention/backup/operational repair, additional real upstreams and gateway-only upstream enforcement remain incomplete. No Woo or cluster changes.

## Recording future decisions

Use a new stable DEC ID with status/date, problem, source constraints and requirement IDs, choice, alternatives, rationale, consequences, and validation needs. Explicitly supersede old entries rather than rewriting history. Record chronological evolution in [project-journey.md](project-journey.md) and current evidence in [progress.md](progress.md). Unvalidated details remain open even when their surrounding architecture is accepted.

# Architecture v1 and assignment boundaries

Status: **A1–A13 committed as db49836; Stage 2 fundamentals validated; Store Architecture v1 and corrected RAM gate accepted on 2026-10-12. Stage 3.2 adds initial store Helm templates with static validation only; no application deployed.** The [original assignment](source/urumi-mcp-gateway-assignment.docx), transcribed in [assignment.md](assignment.md), controls scope. [requirements.md](requirements.md) maps obligations to verification. Design approval does not authorize implementation or prove a requirement works.

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
| A11 | One application Helm chart/release with local/production values, without duplicated manifests; store packaging now resolved by Store Architecture v1 below (DEC-018–DEC-021) | REQ-K8S-02, REQ-DEL-03, REQ-DEL-04 |
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

**Local cluster choice (DEC-017):** Use k3d with Docker Desktop as the intended container runtime. This replaces the proposed Minikube/Docker-driver baseline; the assignment still permits Kind, k3d, or Minikube (REQ-K8S-01). Windows host-access limitations with Minikube's Docker driver would complicate stable local Ingress. k3d's explicit Docker host port mappings offer a simpler planned access path, and its use of k3s aligns with the proposed k3s VPS environment. See [the decision and supporting references](decisions.md#dec-017-local-k3d-after-environment-preflight). Local-to-VPS compatibility still requires validation through the same Helm chart and environment values.

Stage 2 subsequently validated Docker Desktop's WSL2/Linux engine and the single-server urumi-local cluster, running K3s v1.35.5+k3s1. Its API uses port 6550; host ports 8080/8443 map to load-balancer ports 80/443. Existing Traefik, CoreDNS, metrics-server and local-path provisioner passed validation. The disposable lab was completed and removed, with its documentation committed as 7462029. These are historical observations, not a fresh cluster check or evidence of store capacity; see [progress](progress.md).

A10 starts with one application namespace, now named `urumi`, for the mandatory single store. Public Ingress routes provide the storefront, dashboard, same-origin `/api`, and gateway `/mcp`. Internal Services connect PostgreSQL, MariaDB, WooCommerce MCP, arithmetic MCP, and store policy/reference MCP. Upstreams use ClusterIP without public Ingress, NodePort, or LoadBalancer exposure. Store routing uses existing Traefik as specified below; dashboard/gateway hosts, production TLS provisioning and their detailed routes remain to be designed.

Gateway-held upstream authentication adds a caller boundary to internal addressing. ClusterIP alone does not isolate callers inside the cluster. Validate successful gateway calls, rejection without the gateway-held credential, and lack of external upstream exposure; do not claim packet-level gateway-only isolation without evidence. Calico and custom NetworkPolicy setup are not prerequisites for the first working core. NetworkPolicy may be considered after the mandatory flow works, if time allows or needed to strengthen the documented gateway-only boundary. The assignment's gateway-only outcome is not waived; residual exposure belongs in the [threat model](threat-model.md).

Persist WordPress content and MariaDB data as required by the assignment, using the accepted store design below. The selected PostgreSQL state also needs persistent storage so users/keys/registry/audit data survive workload replacement; its deployment details remain open. Do not commit actual credential values in Helm values or other files.

A11 uses one application chart/release and environment values for domains, Ingress, storage classes, resource sizing, image versions, and Secret references as applicable. Store Architecture v1 selects our own minimal Helm templates using standard upstream images rather than a third-party WordPress chart or custom image. Do not duplicate local/production manifests. The production walkthrough must explain Helm upgrade/rollback and its data/compatibility limits; live rollback remains optional under OPEN-01.

## Accepted Store Architecture v1

Accepted on 2026-10-12 with the RAM correction; DEC-018–DEC-021 record rationale and alternatives. This is the design for future implementation, not deployed configuration. It supports REQ-STORE-01, REQ-K8S-02 through REQ-K8S-07, REQ-SEC-01, DEMO-01/02 and VID-02/06. The assignment mandates the outcomes; controller types, sizes, bootstrap mechanics and exact versions are our choices.

```text
Browser -> store.urumi.test:8080 -> existing k3d load balancer -> Traefik
        -> store Ingress rule -> WordPress ClusterIP Service -> WordPress Pod
WordPress Deployment: 1 replica, Recreate -> PVC at /var/www/html
WordPress / bootstrap Job -> internal MariaDB Service -> MariaDB StatefulSet
MariaDB StatefulSet: 1 replica -> PVC at /var/lib/mysql
Finite WP-CLI Job -> same WordPress PVC, co-located on the WordPress node
External Kubernetes Secrets -> only the workloads needing each credential
```

- One application namespace `urumi` and one application chart/release. Create the namespace outside Helm release ownership to avoid namespace deletion during uninstall. Stage 3.2 creates the partial chart only; no application namespace or release has been created.
- WordPress: one-replica Deployment with `Recreate`; a 2 GiB ReadWriteOnce PVC mounts the entire `/var/www/html`. The official entrypoint initializes an empty webroot. This replaces the proposed wp-content-only PVC/emptyDir/core-preparation scheme. Persisted core/plugins are not automatically replaced when the container image changes.
- MariaDB: one-replica StatefulSet with a separate 5 GiB ReadWriteOnce claim at `/var/lib/mysql`, an internal headless Service, and no public port or Ingress. A StatefulSet supplies identity/storage continuity, not database replication or high availability. Internal addressing alone is not caller isolation.
- Local storefront: `http://store.urumi.test:8080`, with a documented Windows hosts mapping to 127.0.0.1 and an Ingress selecting Traefik. Production host, TLS Secret reference, storage class and resource overrides use values; no duplicated environment templates. Migrating existing data between clusters requires a separate data-transfer procedure.
- Initial checkout uses Cash on Delivery. The store-configured timezone defines business dates; actual timezone, country/currency, shipping details, site title and admin identity still need implementation-time configuration. Gateway team identities are separate from the WordPress administrator.

### Bootstrap and health contract

Use a normal Helm-managed WP-CLI Job, not a pre-Apache init container or Helm hook. It waits with bounds for authenticated database access and initialized WordPress files, not WordPress Ready or HTTP Service availability. A post-install hook combined with Helm waiting would deadlock when WordPress readiness depends on WooCommerce activation; a pre-install hook would precede its ordinary resource dependencies.

Flow: database/files available -> positively determine installation state -> install WordPress only if absent -> verify/install the exact WooCommerce version -> activate if necessary -> complete missing deterministic demo configuration -> verify -> record bootstrap completion -> Job succeeds and WordPress becomes Ready. Database failure must not be interpreted as an absent installation. Preserve users, passwords, products and orders on reruns; never automatically reset, reseed, upgrade or downgrade an existing store. A different installed plugin version requires a reviewed upgrade plan. Partial runs must resume through stable identifiers/checkpoints.

Name Jobs by release revision, such as `urumi-store-bootstrap-r<revision>`, to avoid patching immutable Job Pod templates. Start with one completion/worker, restartPolicy Never, backoffLimit 1 and a 600-second overall deadline; Helm waits for workloads and Jobs with a 15-minute timeout. Retain current Job status/logs without an immediate TTL until a subsequent release operation or uninstall removes it. A Pod restart does not rerun a completed Job; a new release revision runs safe verification/bootstrap. Serialize release operations. Rollback can encounter/recreate a historical Job; it cannot be assumed to rerun bootstrap or restore data.

ReadWriteOnce permits multiple Pods on one node. Required Pod affinity co-locates the Job with the WordPress Pod on kubernetes.io/hostname; readiness is not required for that placement. This fits local and intended single-node k3s operation, not multi-node shared storage. Match the Job's numeric filesystem identity to the Apache image (33:33), with writable temporary/cache paths; the Alpine CLI image's default user differs. Verify permissions at runtime.

| Workload | Startup | Liveness | Readiness |
| --- | --- | --- | --- |
| WordPress | TCP 80 with initial five-minute startup allowance | TCP 80, independent of MariaDB | Bounded inline PHP check: WordPress database state loads, WooCommerce is loaded/active, initial bootstrap complete |
| MariaDB | Official healthcheck.sh --connect --innodb_initialized with startup allowance | Official healthcheck.sh --connect | Official healthcheck.sh --connect --innodb_initialized |

No custom public health files are planned. The PHP check must require explicit positive success, sanitize output and enforce timeout; PHP exit zero alone is insufficient. TCP checks prove the listener, not full PHP/checkout behavior. Database failure can make WordPress Unready without restarting healthy Apache repeatedly. The finite Job uses completion, deadline and retry status rather than service-style probes. Runtime behavior remains unverified.

### Accepted version baseline and validation limits

The reviewed metadata checks selected the following Linux/amd64 set. Tags identify versions; the following image-manifest digests pin immutable contents, not multi-platform indexes. Reconfirm availability before deployment; an ARM target requires its own architecture digest. No image was pulled or executed during design validation.

| Component | Accepted version pin | Metadata/source evidence |
| --- | --- | --- |
| WordPress | wordpress:7.1.3-php8.3-apache | Official amd64 image; configuration reports PHP 8.3.35 |
| WP-CLI | wordpress:cli-2.12.0-php8.3 | Official build source selects WP-CLI 2.12.0 and PHP 8.3 Alpine with mysqli |
| MariaDB | mariadb:11.4.13-noble | Official build source selects 11.4.13 and includes healthcheck.sh |
| WooCommerce | 11.2.1 | Versioned official archive; requires WordPress >=7.0/PHP >=7.4, tested through WordPress 7.1; checkout fixes over candidate 11.2.0 |

```text
wordpress:7.1.3-php8.3-apache@sha256:607e9f6829f9e4f3001bc91c98426aaa742d164af030aa7a8073932798e2af6b
wordpress:cli-2.12.0-php8.3@sha256:07e56f9242a5c5e194bb0191c0f95a07fd1eefe712a231fc444d67eb51bb01e8
mariadb:11.4.13-noble@sha256:f2f5e00999bd335343e09091e27e39c9386eb1822efcd0e0bac40b0003fa47e3
woocommerce.11.2.1.zip SHA-256: 5317434cb381b5fdc7c1dd6ee258324f08c390976aaf8d1199f2a0e9a3ab8586
```

Image repositories are docker.io/library. The plugin checksum was computed from the official ZIP in memory, not a published signature. Its plugin header says 11.2.1 while its readme Stable tag still says 11.2.0; explicitly use the versioned archive/checksum, not that floating pointer. WP-CLI/MariaDB configuration-blob downloads encountered connection resets; manifest/platform checks succeeded and versions were cross-checked in official build sources. Declared compatibility does not prove installation, checkout or runtime resource behavior. Controlled core/plugin updates are the reviewed direction for reproducibility; explicit security-update review remains necessary.

Evidence: [WordPress image catalog](https://github.com/docker-library/official-images/blob/master/library/wordpress), [WP-CLI build](https://github.com/docker-library/wordpress/blob/27edf122404ed2b503604eedc5f171e79fa019bf/cli/php8.3/alpine/Dockerfile), [MariaDB build](https://github.com/MariaDB/mariadb-docker/blob/bdfe641466a5312bb97d06a1a4e1fb411c49e6b6/11.4/Dockerfile), [WooCommerce release](https://developer.woocommerce.com/2026/10/09/woocommerce-11-2-1-release-notes/), [versioned archive](https://downloads.wordpress.org/plugin/woocommerce.11.2.1.zip), [plugin readme](https://github.com/woocommerce/woocommerce/blob/11.2.1/plugins/woocommerce/readme.txt), [server recommendations](https://woocommerce.com/document/server-requirements/).

### Persistence lifecycle and credential contract

| Operation | WordPress explicit PVC | MariaDB StatefulSet-generated PVC |
| --- | --- | --- |
| Pod deletion | Retained and remounted | Retained and remounted by replacement ordinal |
| Controller replacement | Independent claim remains; preserve its reference | Retain claim; preserve StatefulSet/claim-template names for reuse |
| Helm upgrade | Same claim/files; image changes do not replace persisted core/plugins | Same claim/data; assess database compatibility before image changes |
| Helm rollback | Current files remain, not previous file contents | Current database remains, not previous schema/data |
| Helm uninstall | helm.sh/resource-policy: keep | Explicit whenDeleted: Retain and whenScaled: Retain |

Reinstallation must deliberately reuse retained claims and original credentials; support an existingClaim reference for WordPress. Do not silently rename or replace claims or assume ordinary values changes can migrate/resize storage. Retention behavior still requires validation. Two volumes provide Pod-replacement durability only; they provide neither node-loss protection nor backup. Current local-path uses a Delete reclaim policy. Direct PVC deletion and especially namespace deletion can destroy retained data. **Never apply the disposable Stage 2 namespace-cleanup pattern to urumi.** Helm rollback does not reverse database contents or persisted WordPress files. A recoverable backup requires database/webroot copies outside the failure boundary and restore verification; this does not select automatic backup tooling.

| External Secret in urumi | Keys | Consumers |
| --- | --- | --- |
| urumi-mariadb-root | root-password | MariaDB only; MARIADB_ROOT_PASSWORD_FILE |
| urumi-store-db | password | MariaDB initialization, WordPress and bootstrap Job; respective MARIADB_PASSWORD_FILE / WORDPRESS_DB_PASSWORD_FILE settings |
| urumi-wordpress-admin | admin-password | Job only, first installation only |
| urumi-wordpress-auth | auth-key, secure-auth-key, logged-in-key, nonce-key, auth-salt, secure-auth-salt, logged-in-salt, nonce-salt | WordPress and Job via corresponding WORDPRESS_*_FILE settings |
| urumi-woocommerce-rest (later) | consumer-key, consumer-secret | Future custom WooCommerce MCP only; credentials issued by WooCommerce |

The chart references these Secrets; it never renders their values. Database name urumi_store and user urumi_wp are non-secret configuration. The future PowerShell helper accepts masked input, generates absent DB passwords/salts securely, sends in-memory payloads through kubectl stdin and reports names/status only. No plaintext Helm --set, tracked values, temporary credential files or payload logs. Existing Secrets are preserved; missing/inconsistent keys require deliberate repair, not automatic rotation. No helper or Secret exists yet, and future WooCommerce credentials are not generated during initial store bootstrap.

### Resource budgets and current RAM gate

| Workload | CPU request / limit | Memory request / limit |
| --- | --- | --- |
| WordPress | 250m / 1000m | 512Mi / 1Gi |
| MariaDB | 100m / 500m | 256Mi / 512Mi |
| Bootstrap Job | 100m / 500m | 128Mi / 512Mi |

**PASS for initial Stage 3 deployment attempt; full-stack capacity still unproven.** The user's accepted correction on 2026-10-12 reports approximately 15.7 GiB total, 11.6 GiB used and 4.1 GiB available Windows RAM. This narrowly passes the approximately 4 GiB host gate and supersedes the earlier ~1 GiB blocking observation. It is user-reported, not a fresh measurement in this documentation step. Keep the budgets unchanged.

Immediately before the first Helm install, recheck host memory and Docker/WSL/node scheduling headroom. During runtime validation measure host, node and workload memory through MariaDB startup, WordPress startup, bootstrap, normal storefront/admin use and checkout. Stop and tune on OOM kills, unexplained restarts, severe host pressure or insufficient scheduling capacity before adding further Urumi components. The 2 GiB combined bootstrap-time container limits exclude host/cluster overhead and are not measured consumption.

### Stage 3.2 template coverage and deployment prerequisites

The initial [chart](../charts/urumi/Chart.yaml) has shared defaults and local/production values, stable release-based names/selectors, a WordPress Deployment/Service/Ingress/PVC and a MariaDB StatefulSet/headless Service. Namespaced resources use Helm's release namespace; use urumi for the application. No Namespace or Secret is rendered. MariaDB's data claim is generated later by the StatefulSet controller, not an extra top-level rendered resource. The chart requires Kubernetes >=1.32 for the stable StatefulSet PVC retention feature and selects Linux/amd64 nodes to match the pinned images.

**This partial chart is not ready for installation.** WordPress readiness is explicitly interim TCP listener readiness, not proof that the database, WooCommerce or bootstrap is ready. Implement the accepted bounded PHP check alongside the later idempotent bootstrap Job before deployment; the chart does not create either bootstrap scripts or a Job. The canonicalUrl value is reserved for that bootstrap and does not yet configure the installed store. The admin/REST Secrets are not mounted into either long-running workload; root credentials are mounted only into MariaDB, app DB credentials into both, and auth keys/salts only into WordPress.

The local values inherit 2 GiB/5 GiB storage and unchanged resource budgets while selecting local-path and store.urumi.test. Only canonicalUrl includes :8080; the Ingress host does not. Production values demonstrate TLS, configurable capacities/resources and a different StorageClass through explicit example.invalid / replace-with-* placeholders, not real infrastructure. Replace them and prepare external TLS/credential Secrets before an authorized production deployment. Empty storageClass in shared defaults omits storageClassName to use the cluster default; WordPress existingClaim skips PVC creation for deliberate reuse. The accepted retention and backup limits above still apply.

Helm lint/render and offline Kubernetes v1.35.5 schema checks passed; selector, mount, credential-reference, probe and network checks are static evidence only. See [progress](progress.md#stage-32-initial-helm-chart-static-validation) for scope and commands. No API server, image execution, runtime probe, persistence or checkout test was involved.

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

- Local Docker/k3d operational validation and the fundamentals lab are complete. Vite and actual production-like k3s deployment remain future work. React, Kubernetes and Helm are assignment constraints; Python/FastAPI, SDK, PostgreSQL, MariaDB and controller boundaries are project choices. Store versions are selected above; runtime validation and application package pinning remain pending.
- Validate SDK/protocol versions, gateway/client interoperability, connection/session lifecycle, catalog notifications/refresh, tool-name limits, timeout defaults, and health observation in a later prototype.
- Specify authentication algorithms/formats, session/cookie/CSRF and invitation details, role representation, initial admin/WooCommerce registration, runtime Secret management, audit failure/denial/redaction/retention contracts, and schema constraints before affected implementation.
- Select the LLM/provider, chat-loop integration and response transport, exact WooCommerce REST/tool contracts, auxiliary tool schemas, and final interactive client. Define revenue demo data semantics and user A/B roles.
- Implement and validate the accepted store contracts only in a separately authorized step. Confirm initial store settings, filesystem permissions, safe Job reruns, retained-claim reuse, probes, checkout and measured memory. Production TLS provisioning and non-store deployment details remain open. NetworkPolicy is deferred, not a first-core prerequisite.

No bonus or stand-out item is selected by this approval. [progress.md](progress.md) records current evidence; [project-journey.md](project-journey.md) records how the design evolved. Stage 3.2 authorizes the initial chart files and static checks only: no bootstrap files, release installation, Kubernetes apply, Secrets, hosts-file edits or commit. Stop for review.

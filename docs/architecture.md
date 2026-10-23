# Architecture v1 and assignment boundaries

Status: **The local Stage 3 store foundation is complete: business-flow acceptance was committed as af7bb37, and Stage 3.8 verified controlled Pod-replacement persistence, retained scale-down and database-loss probe behavior on revision 3 on 2026-10-21.** The 22 October review encountered API EOF errors and empty store responses. A controlled stop/start of the existing k3d cluster restored API/system health and anonymous storefront access; read-only checks reconfirmed release revision 3, product 11, order 12, marker 3 and the original Bound claims/PVs. The startup failure was traced to K3s network-policy initialization being unable to find its configured node-IP interface; the trigger for that condition is unproven. Implementation sections below preserve their historical milestone evidence; the availability gap and [controlled recovery](progress.md#stage-38-recovery-of-the-existing-local-environment) remain recorded. Production/full-system behavior, node-loss protection, backup/restore and full-stack memory capacity are not established. The [original assignment](source/urumi-mcp-gateway-assignment.docx), transcribed in [assignment.md](assignment.md), controls scope. [requirements.md](requirements.md) maps obligations to verification. Design approval and static checks alone do not prove a runtime requirement works.

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

- One application namespace `urumi` and one application chart/release. Create the namespace outside Helm release ownership to avoid namespace deletion during uninstall. Stage 3.3 adds bootstrap/readiness to the chart; no application namespace or release has been created.
- WordPress: one-replica Deployment with `Recreate`; a 2 GiB ReadWriteOnce PVC mounts the entire `/var/www/html`. The official entrypoint initializes an empty webroot. This replaces the proposed wp-content-only PVC/emptyDir/core-preparation scheme. Persisted core/plugins are not automatically replaced when the container image changes.
- MariaDB: one-replica StatefulSet with a separate 5 GiB ReadWriteOnce claim at `/var/lib/mysql`, an internal headless Service, and no public port or Ingress. A StatefulSet supplies identity/storage continuity, not database replication or high availability. Internal addressing alone is not caller isolation.
- Local storefront: `http://store.urumi.test:8080`, with a documented Windows hosts mapping to 127.0.0.1 and an Ingress selecting Traefik. Production host, TLS Secret reference, storage class and resource overrides use values; no duplicated environment templates. Migrating existing data between clusters requires a separate data-transfer procedure.
- Initial checkout uses Cash on Delivery. The store-configured timezone defines business dates; Stage 3.3 adopts the user-approved India (IN), Asia/Kolkata, INR and unrestricted free-shipping demo baseline. Site title and non-secret admin identity are configurable placeholders; review deployment values before use. Gateway team identities are separate from the WordPress administrator.

### Bootstrap and health contract

Use a normal Helm-managed WP-CLI Job, not a pre-Apache init container or Helm hook. It waits with bounds for authenticated database access and initialized WordPress files, not WordPress Ready or HTTP Service availability. A post-install hook combined with Helm waiting would deadlock when WordPress readiness depends on WooCommerce activation; a pre-install hook would precede its ordinary resource dependencies.

Flow: database/files available -> positively determine installation state -> install WordPress only if absent -> verify/install the exact WooCommerce version -> activate if necessary -> complete missing deterministic demo configuration -> verify -> record bootstrap completion -> Job succeeds and WordPress becomes Ready. Database failure must not be interpreted as an absent installation. Preserve users, passwords, products and orders on reruns; never automatically reset, reseed, upgrade or downgrade an existing store. A different installed plugin version requires a reviewed upgrade plan. Partial runs must resume through stable identifiers/checkpoints.

Name Jobs by release revision, such as `urumi-store-bootstrap-r<revision>`, to avoid patching immutable Job Pod templates. Start with one completion/worker, restartPolicy Never, backoffLimit 1 and a 600-second overall deadline; Helm waits for workloads and Jobs with a 15-minute timeout. Retain current Job status/logs without an immediate TTL until a subsequent release operation or uninstall removes it. A Pod restart does not rerun a completed Job; a new release revision runs safe verification/bootstrap. Serialize release operations. Rollback can encounter/recreate a historical Job; it cannot be assumed to rerun bootstrap or restore data.

ReadWriteOnce permits multiple Pods on one node. Required Pod affinity co-locates the Job with the WordPress Pod on kubernetes.io/hostname; readiness is not required for that placement. This fits local and intended single-node k3s operation, not multi-node shared storage. Match the Job's numeric filesystem identity to the Apache image (33:33), with writable temporary/cache paths; the Alpine CLI image's default user differs. Verify permissions at runtime.

| Workload | Startup | Liveness | Readiness |
| --- | --- | --- | --- |
| WordPress | TCP 80 with initial five-minute startup allowance | TCP 80, independent of MariaDB | Bounded inline PHP check: WordPress database state loads, WooCommerce is loaded/active, initial bootstrap complete |
| MariaDB | Official healthcheck.sh --connect --innodb_initialized with startup allowance | Official healthcheck.sh --connect | Official healthcheck.sh --connect --innodb_initialized |

No custom public health files are planned. The PHP check must require explicit positive success, sanitize output and enforce timeout; PHP exit zero alone is insufficient. TCP checks prove the listener, not full PHP/checkout behavior. Database failure can make WordPress Unready without restarting healthy Apache repeatedly. The finite Job uses completion, deadline and retry status rather than service-style probes. Stage 3.8 verified this store behavior locally: deliberate MariaDB absence removed WordPress readiness while TCP/liveness stayed healthy, and restoration recovered readiness without a WordPress restart. This evidence does not cover future gateway/MCP/dashboard probes.

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

Reinstallation must deliberately reuse retained claims and original credentials; support an existingClaim reference for WordPress. Do not silently rename or replace claims or assume ordinary values changes can migrate/resize storage. Stage 3.8 verified local WordPress/MariaDB Pod-replacement durability and MariaDB scale-down claim retention; uninstall/reinstall and production retention remain untested. Two volumes provide Pod-replacement durability only; they provide neither node-loss protection nor backup. Current local-path uses a Delete reclaim policy. Direct PVC deletion and especially namespace deletion can destroy retained data. **Never apply the disposable Stage 2 namespace-cleanup pattern to urumi.** Helm rollback does not reverse database contents or persisted WordPress files. A recoverable backup requires database/webroot copies outside the failure boundary and restore verification; this does not select automatic backup tooling.

| External Secret in urumi | Keys | Consumers |
| --- | --- | --- |
| urumi-mariadb-root | root-password | MariaDB only; MARIADB_ROOT_PASSWORD_FILE |
| urumi-store-db | password | MariaDB initialization, WordPress and bootstrap Job; respective MARIADB_PASSWORD_FILE / WORDPRESS_DB_PASSWORD_FILE settings |
| urumi-wordpress-admin | admin-password | Job only, first installation only |
| urumi-wordpress-auth | auth-key, secure-auth-key, logged-in-key, nonce-key, auth-salt, secure-auth-salt, logged-in-salt, nonce-salt | WordPress and Job via corresponding WORDPRESS_*_FILE settings |
| urumi-woocommerce-rest (later) | consumer-key, consumer-secret | Future custom WooCommerce MCP only; credentials issued by WooCommerce |

The chart references these Secrets; it never renders their values. Database name urumi_store and user urumi_wp are non-secret configuration. The [local helper](../scripts/setup-store-secrets.ps1) implements the four current Secret contracts; no actual Secret has been created. WooCommerce REST credentials remain deferred until WooCommerce is live and can issue them for the custom MCP server.

### Local store Secret preparation

The helper requires the already-installed PowerShell 7 runtime and fixes context k3d-urumi-local and namespace urumi; neither is an override parameter. Its modes are:

| Mode | Behavior | Evidence so far |
| --- | --- | --- |
| Validate (default) | Offline manifest/key fixtures and immediately discarded RNG samples; no kubectl, interactive input, disk payload or project credentials | Executed locally |
| Check | Read-only context/active-namespace check, then inspect all four Secrets; report preserved or absent/would-create | Mocked only; no live cluster reads in Stage 3.4 |
| Create | Same preflight, then masked admin input and create missing Secrets only | Mocked only; not authorized/executed against Kubernetes |

The safe local command is `pwsh -NoProfile -File scripts/setup-store-secrets.ps1 -Mode Validate`. Check/Create use the same entrypoint with their explicit mode only in a later authorized step. The namespace must already exist and be Active; the helper never creates it. Existing objects must match identity, Opaque type, the exact case-sensitive key set and nonempty base64-encoded UTF-8 text without NUL, newlines or edge whitespace. It checks every existing Secret before generating or writing anything. Inconsistent objects stop for explicit repair; no rotation, deletion, patch, replace or apply path exists. This validates structure, not agreement with credentials already persisted in database/webroot volumes; retained-data recovery must reuse original credentials.

Absent DB/root passwords use 32 cryptographically random bytes (256 bits, 44 base64 characters); each auth key/salt uses 64 bytes (512 bits, 88 characters). Kubernetes data applies a separate base64 encoding to that credential text. Admin input uses Read-Host -AsSecureString and is requested before any creation. Input validation avoids the bootstrap's one-line/password-trimming ambiguity; it does not introduce a password-strength policy. No external salt service, Get-Random, timestamp or GUID supplies entropy.

JSON exists only in memory and enters kubectl through stdin. ProcessStartInfo uses an argument list containing only fixed flags/names, no shell and no credentials. Standard output is captured internally; raw stderr is drained/discarded. Failures report only the operation/Secret name and return nonzero. API requests have a 15-second timeout, stdin writing 10 seconds, process exit 30 seconds and pipe draining bounded waits. The helper uses create -f -, so a concurrent creator produces a failure rather than overwriting existing values. A timeout can leave an accepted write, and a later failure can leave earlier creations: rerun by checking current state, never deleting or rotating automatically. Read-back verifies keys after each successful create.

Mutable byte buffers and unmanaged password buffers are cleared; immutable .NET strings cannot be reliably zeroed. Use a trusted local session without tracing/debugging/transcription; this helper does not provide a secret vault or defend against host-level inspection/logging. Base64 is not encryption. Future runtime validation must cover real masked input, kubectl access, API/admission errors, safe reruns and workload credential consumption. Sources: [.NET cryptographic RNG](https://learn.microsoft.com/en-us/dotnet/api/system.security.cryptography.randomnumbergenerator.getbytes), [redirected subprocess streams](https://learn.microsoft.com/en-us/dotnet/api/system.diagnostics.processstartinfo.redirectstandardoutput), [masked input](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/read-host), [kubectl create](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_create/).

### Resource budgets and current RAM gate

| Workload | CPU request / limit | Memory request / limit |
| --- | --- | --- |
| WordPress | 250m / 1000m | 512Mi / 1Gi |
| MariaDB | 100m / 500m | 256Mi / 512Mi |
| Bootstrap Job | 100m / 500m | 128Mi / 512Mi |

**PASS for initial Stage 3 deployment attempt; full-stack capacity still unproven.** The user's accepted correction on 2026-10-12 reports approximately 15.7 GiB total, 11.6 GiB used and 4.1 GiB available Windows RAM. This narrowly passes the approximately 4 GiB host gate and supersedes the earlier ~1 GiB blocking observation. It is user-reported, not a fresh measurement in this documentation step. Keep the budgets unchanged.

Immediately before the first Helm install, recheck host memory and Docker/WSL/node scheduling headroom. During runtime validation measure host, node and workload memory through MariaDB startup, WordPress startup, bootstrap, normal storefront/admin use and checkout. Stop and tune on OOM kills, unexplained restarts, severe host pressure or insufficient scheduling capacity before adding further Urumi components. The 2 GiB combined bootstrap-time container limits exclude host/cluster overhead and are not measured consumption.

### Stage 3.3 bootstrap and readiness implementation

Stage 3.2's six-resource chart was committed as 490c2de with interim readiness. Stage 3.3, committed as 17a54ab, adds a revision-specific immutable ConfigMap and a normal Job: local/production rendering produced eight resources. Namespace, credentials and TLS Secrets remain external. Its approved metadata cleanup gives Chart.yaml a stable platform description. No deployment has occurred, and Stage 3.4 does not run Helm or alter the chart.

The [shell orchestrator](../charts/urumi/files/store/bootstrap-wordpress.sh) and [PHP configurator](../charts/urumi/files/store/configure-woocommerce.php) are loaded by Helm .Files into the ConfigMap, not interpolated as templates. They contain code and credential-file paths, never credential values. Configuration travels through non-secret env vars; actual passwords/salts come from existing Secret references. The Job mounts only application DB, initial admin and WordPress auth Secrets, not the DB root or future REST credentials. Admin password input uses WP-CLI's stdin prompt, not an argument or newly written plaintext file.

The Job runs UID/GID 33 with fsGroup 33, a writable /tmp/cache, the shared webroot PVC and required same-namespace Pod affinity to the WordPress labels on kubernetes.io/hostname. It does not wait for WordPress readiness to schedule. One worker/completion, restartPolicy Never, backoffLimit 1 and activeDeadlineSeconds 600 bound its lifecycle. Each dependency wait has a 120-second deadline, with 3-second polling; authenticated DB connection/read timeout is 5 seconds and each subsequent command has a 120-second process timeout. The Job deadline bounds the entire attempt/retries. These budgets and the accepted 128Mi/512Mi memory request/limit remain runtime hypotheses.

Fresh flow: wait for webroot/config files -> authenticate/query MariaDB -> inspect WordPress installation -> install only after positively observing an empty database -> claim the installation -> verify/download/checksum/install WooCommerce 11.2.1 if absent -> activate if inactive -> verify its loaded version -> configure/verify demo settings/pages/shipping -> write urumi_bootstrap_version last. Database failure is never treated as an absent installation. Unknown/partial nonempty databases and unidentified plugin files require manual review; there is no force reinstall, reset or automatic plugin version change.

Persistent non-secret options urumi_bootstrap_contract and urumi_bootstrap_settings record ownership, requested configuration and before/target values. Incomplete configuration may resume only from recorded original/target values; unrelated edits fail. A completed bootstrap verifies settings and preserves users, passwords, products and orders. It creates no products or orders. Required WooCommerce pages use its page-initialization API; the sole free-shipping method uses zone 0 and the shipping API. Custom shipping zones/methods, invalid established pages, changed contracts and different marker/plugin versions fail instead of being overwritten. Unclaimed existing stores are not adopted automatically. An interruption after core installation but before ownership is recorded requires manual review; partial core/plugin installation also stops safely rather than being automatically repaired.

Readiness now executes PHP directly with a 5-second kubelet timeout. It loads WordPress, positively queries DB-backed state, checks active/loaded WooCommerce at the expected version and checks the persistent completion marker. Its shutdown handler defaults to failure even on an early exit(0); diagnostic output is buffered/discarded. Cron spawning is disabled only for the probe process. Startup/liveness remain independent TCP listener checks: MariaDB loss should remove readiness without repeatedly restarting a healthy Apache listener. These failure semantics are implemented, not runtime-demonstrated. Normal automatic core/plugin updates are disabled via runtime wp-config settings in both the web and CLI environments; manual controlled updates still require review.

### Stage 3.7 deterministic permalinks and explicit v1-to-v2 migration

Implemented for static review on 2026-10-20; **not deployed**. This supersedes the version-1 no-migration behavior described in the historical Stage 3.3 section above. The live release remains revision 1 with bootstrap marker 1, Plain permalinks, existing product 11/SKU URUMI-DEMO-001 and no checkout order.

Acceptance found /shop/ returned HTTP 200 with the blog, while generated query-string product/catalog URLs worked. The missing deterministic permalink baseline, not an Ingress or database failure, caused that content failure. HTTP status alone is insufficient business-flow evidence.

Version 2 adds the fixed PERMALINK_STRUCTURE=/%postname%/ to the non-secret bootstrap ownership contract. The shared bootstrap.version value becomes "2"; it is independent of Helm's release revision. No image, resource budget, volume, Secret, country/currency/timezone, shipping or payment setting changes. Existing version-1 code cannot migrate merely by changing the expected version: its exact owner comparison fails before configuration, and its marker comparison also rejects another version.

| Persisted ownership / marker | New-script behavior |
| --- | --- |
| Exact target v2 / absent marker | Resume a new v2 bootstrap using its existing setting checkpoints |
| Exact prior v1 / marker 1 | Recognized migration, only if all original contract fields match and all completed business settings still match their checkpoints |
| Exact target v2 / marker 1 | Resume the recognized interruption between ownership update and final marker write |
| Exact target v2 / marker 2 | Verify settings; idempotently regenerate/verify derived rewrite rules |
| Any other ownership/version pair | Fail; no arbitrary adoption, downgrade or automatic repair |

Before route mutation, configuration verifies existing base settings, active exact WooCommerce, pages, shipping and database access. A completed store with missing/inactive WooCommerce fails preflight rather than reinstalling/reactivating it. Permalink changes accept only Plain or the target structure until completion; a completed v2 store must already have the target. Unrelated custom structures or business-setting drift fail. The existing settings checkpoint is preserved; no product/user/order CRUD is added.

The bounded shell orchestrator provides a non-secret WP_CLI_CONFIG_PATH under the Job's existing /tmp emptyDir containing apache_modules: [mod_rewrite]. It runs `wp rewrite structure '/%postname%/' --hard` with plugins and themes loaded. WP-CLI sets the structure through WP_Rewrite and launches a fresh process for flushing, so routes register against the new structure. Global --skip-themes is removed to keep the configuration/flush/verification context consistent. The hard flush persists WordPress rules in the database and updates only the managed WordPress block in the existing shared-PVC .htaccess; it does not replace WordPress core/plugin files or outside-block directives.

Read-only inspection of the pinned deployed Apache environment confirmed rewrite_module enabled, AllowOverride All, webroot owned by 33:33 mode 755 and .htaccess owned by 33:33 mode 644. The Job already runs as 33:33 and mounts that same RWO claim on the WordPress node. This supports the design without a chmod, new mount or Apache configuration change; actual migration writes are still untested. Official references: [WP-CLI structure](https://developer.wordpress.org/cli/commands/rewrite/structure/), [hard flush and Apache module configuration](https://developer.wordpress.org/cli/commands/rewrite/flush/), [WordPress managed-block persistence](https://developer.wordpress.org/reference/functions/save_mod_rewrite_rules/).

A fresh finalize process rechecks base configuration and requires the exact permalink, persisted shop-archive/product rewrite patterns, generated /shop/ URL and /product/%product% structure, plus a .htaccess WordPress block matching WordPress-generated Apache directives. It does not silently regenerate missing DB rules during verification. Only then does it save the v2 ownership contract and write marker 2 last. The known old/target permalink states and target-owner/old-marker state allow interrupted work to resume; unknown states stop. Readiness additionally checks the target permalink and expected marker 2. Startup/liveness remain independent TCP checks.

**Future upgrade, not executed:** first recheck memory/health, preserve product 11 and confirm prior Jobs/Pods are terminal, then serialize one reviewed Helm upgrade. Revision 2 creates r2 Job/assets; the changed expected marker/probe rolls the Recreate WordPress Deployment using its existing PVC. Its new Pod may be Running but unready until migration verifies and marker 2 is saved. Job affinity requires the WordPress node, not WordPress readiness, avoiding that dependency deadlock. The database StatefulSet and both claims stay unchanged. Expect an availability gap with this single-replica Recreate design.

If a command/verification fails, the marker remains old unless all verification and the final write succeeded; a lost acknowledgement can still leave an already-completed marker, so inspect before retrying. Database options and .htaccess are not one transaction. Leave PVCs, Secrets and data intact and inspect sanitized diagnostics. After marker 2 is saved, historical revision-1 readiness expects marker 1 and will fail: **Helm rollback is not a safe automatic downgrade or data/file rollback.** A reviewed forward repair or separately designed restoration is required. Do not edit markers by hand. Runtime checks must prove /shop/ contains the product and /product/urumi-demo-mug/ works, product 11/SKU and existing data are preserved, Job completion/readiness and idempotent rerun behavior, then resume the manual checkout.

### Stage 3.7C public Live visibility and explicit v2-to-v3 migration

Implemented for source/static review on 2026-10-21; **not deployed**. The last verified release remains revision 2 with marker 2, product 11/SKU URUMI-DEMO-001 and the successful guest COD order 12. The earlier v2 migration section is historical; this section defines the next contract. Stage 3.7 and persistence/dependency-loss tests remain incomplete.

The assignment requires a usable storefront and checkout. The user has made public Live visibility an explicit deterministic demo contract: woocommerce_coming_soon=no and woocommerce_store_pages_only=no. Those exact option names/version numbers are our implementation choice, not added wording in the official assignment. WooCommerce documents [Coming Soon access restrictions](https://woocommerce.com/document/configuring-woocommerce-settings/coming-soon-mode/) and [supported option-based integration](https://developer.woocommerce.com/docs/extensions/extension-onboarding/integrating-coming-soon-mode/). Read-only inspection of the pinned 11.2.1 installation source found fresh-store defaults yes/yes; it does not prove the historical trigger/time of the live values.

Completed v2 verifies its existing settings/rewrite contract but ignores both visibility options. Merely changing the expected version fails its shell/PHP target guards and ownership comparison. Contract v3 keeps every v2 field, changes BOOTSTRAP_VERSION to 3 and adds COMING_SOON=no and STORE_PAGES_ONLY=no. The existing business-settings checkpoint is preserved, not rebuilt to adopt the two old yes values.

| Ownership / marker | Recognized behavior |
| --- | --- |
| Exact v2 / 2 | Verify completed business configuration and postname/DB/Apache rewrites; migrate only yes/yes, no/yes or no/no visibility pairs |
| Exact v3 / absent | Resume owned fresh/partial bootstrap and its setting checkpoints; the same visibility pairs are allowed; Plain permalinks only before fresh rewrite initialization |
| Exact v3 / 2 | Resume final ownership-to-marker interruption only with no/no visibility and intact completed configuration |
| Exact v3 / 3 | Verify no/no and the existing contract; do not silently repair visibility drift |
| Other owner/version/marker, missing/invalid visibility values, yes/no, or unrelated configuration drift | Fail without adopting/resetting the store; completed v1 needs the reviewed v1-to-v2 path before this migration |

Pair order is coming_soon/store_pages_only. yes/yes is the observed source and pinned fresh-install default; no/yes is the interruption after the first intentional write; no/no is the target. Accepting the target also permits a previous attempt that completed both writes but stopped before ownership advancement. This is a bounded state allowance, not proof of who wrote an option. Database ownership/checkpoints remain ordinary mutable state.

The shell keeps bounded configure and hard-rewrite stages, then calls make-live in its own WP-CLI process. Completed stores now verify their existing rewrites before the hard flush, refusing unrelated routing drift. make-live rechecks the full business/rewrite contract before calling update_option through urumi_save for only the two visibility options, in order, verifying each readback. A separate finalize process rereads and verifies configuration, rewrites and both no values; it never repairs visibility. Only then does it update ownership to v3 and write marker 3 last. The API preserves WordPress option hooks; no direct SQL mutation or product/order/user CRUD is added. Existing WooCommerce, credentials, business records and PVCs are preserved. Fresh v3 installation still uses the guarded empty-database/bootstrap flow.

Readiness adds both no checks to its existing WordPress/DB/WooCommerce/permalink/marker checks. This reflects the demo contract without a frontend HTTP request on every probe. Visibility drift makes the Pod unready, while TCP startup/liveness remain independent of MariaDB and visibility. The trade-off is deliberate loss of Service readiness for an unhealthy demo contract, not a container restart. Option checks cannot prove theme output, cache behavior or anonymous access: runtime acceptance must separately inspect visible body content, excluding embedded script data, at shop/product URLs.

Future authorized upgrade: recheck memory, application state and terminal prior Jobs; serialize one Helm operation using the same chart/local values. Revision 3 would create r3 assets/Job and replace WordPress through Recreate, retaining MariaDB and both claims. Verify preserved product 11 and Processing order 12, exact v3 completion, anonymous catalog/product content and health without another checkout. The current step performs no upgrade, live option write or bootstrap execution. Static fixtures use in-memory options/data sentinels only.

Visibility, rewrites, ownership and marker writes are not one transaction. If failure occurs, inspect the persisted recognized state before retrying; never manually advance a marker. After marker 3, revision-2 readiness still expects 2 and its bootstrap rejects v3 ownership. Helm rollback does not restore options/.htaccess or data, so automatic rollback remains unsafe. Retain valuable state and review forward repair or an explicit restoration plan. See [DEC-025](decisions.md#dec-025-public-live-store-contract-and-v2-to-v3-migration).

### Helm Job upgrade and rollback contract

Normal upgrades render a new release revision, hence a new Job and matching immutable ConfigMap; no hook, immediate TTL or keep annotation is used for them. Helm's update path creates/updates target resources before deleting resources absent from the target. The previous Job/assets are normally removed during a successful upgrade, so preserve desired logs before upgrading. Failed operations may leave partial state and need inspection. **Serialize release operations and require the prior bootstrap Job to be terminal with no running Pods before another upgrade/rollback.** Revision names prevent immutable-spec updates, not concurrent execution. Overlong revision-specific Job names fail rendering instead of being silently truncated.

Rollback uses the selected historical rendered manifest; it does not rerender a fresh Job name from the new rollback revision. A historical Job absent from the cluster can be recreated and run. An existing completed Job with unchanged spec does not rerun; an existing failed Job may remain failed. Rolling back to the pre-bootstrap foundation removes the Job/assets and restores that revision's interim probe. Neither rollback nor Job recreation restores DB/webroot contents, reverses configuration, or bypasses version/contract guards. Compatibility and persisted state must be reviewed before any rollback.

These are static conclusions checked against Helm 4.3.0 [upgrade revision rendering](https://github.com/helm/helm/blob/v4.3.0/pkg/action/upgrade.go), [resource reconciliation/deletion](https://github.com/helm/helm/blob/v4.3.0/pkg/kube/client.go) and [historical-manifest rollback](https://github.com/helm/helm/blob/v4.3.0/pkg/action/rollback.go), not live release experiments. The [WP-CLI install reference](https://developer.wordpress.org/cli/commands/core/install/) documents stdin password prompting.

### Deployment prerequisites and remaining proof

Available static checks passed, including shell syntax, Helm lint, both renders, offline Kubernetes v1.35.5 schemas, relationship/credential checks and image/archive pins. PHP and ShellCheck are unavailable locally: PHP syntax checking and all PHP execution remain outstanding, including the inline probe. No image layers were pulled and no application container was run. Before deployment obtain PHP syntax evidence in an authorized environment, review helper/binary availability and UID/PVC permissions, prepare the external namespace/Secrets and hosts/DNS/TLS/storage configuration, and recheck host/node memory. Production values remain placeholders.

Runtime validation must cover fresh install, completed and partial reruns, safe refusal cases, checkout/admin behavior, Pod replacement, readiness on DB loss, Job deadline/retries, upgrade/rollback and PVC retention. Measure memory during both startups, bootstrap, normal use and checkout. No runtime requirement or demo is complete; see [progress](progress.md#stage-33-bootstrap-and-readiness-static-validation).

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

## Accepted WooCommerce MCP design

Stage 4.1 was accepted for recording in Stage 4.2 on 2026-10-23. This is a design contract, not a deployed MCP server. Stage 4.2 implements only the [offline REST Secret helper](../scripts/setup-woocommerce-rest-secret.ps1). Decisions DEC-026 through DEC-029 in [decisions](decisions.md) refine A3/A7/A10 without changing the assignment. REQ-WOO-01 through REQ-WOO-09 remain implementation/runtime-incomplete.

### Protocol and adapter responsibility

Pin the official Python MCP SDK to mcp==2.3.0 on Python 3.13, using MCP 2026-07-28 and the SDK's Streamable HTTP implementation at /mcp. No handwritten JSON-RPC, third-party Woo MCP server, or separate FastMCP package. Exact transitive dependencies and the established OAuth signer will be resolved, tested and pinned when the Python package is authorized; no dependency files exist yet. Official evidence: [SDK release v2.3.0](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.3.0), [published package](https://pypi.org/project/mcp/2.3.0/), [current transport specification](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http).

Modern protocol requests are stateless and do not depend on Mcp-Session-Id; HTTP connection pooling is a separate implementation concern. Use MCPServer and its streamable_http_app; stateless_http=True makes the SDK's legacy path sessionless too. Modern behavior is already sessionless regardless of that flag. Five fixed tools need no elicitation, legacy back-channel or catalog subscriptions. Prefer JSON tool responses and disable subscriptions; leave wire/version handling to the SDK. Verify 2026-07-28 and 2025-11-25 clients later; actual Claude/Cursor compatibility remains a gateway acceptance task. The SDK release has a pre-execution HeaderMismatch retry; this is distinct from replaying an ambiguous write, and call-count tests must cover the chosen transport. [SDK legacy behavior](https://py.sdk.modelcontextprotocol.io/run/legacy-clients/).

```text
External MCP client / dashboard chat
  -> future gateway: identity, authorization, routing and audit
  -> internal Woo MCP /mcp
  -> input validation -> Woo REST client/authentication
  -> WordPress/WooCommerce REST v3 -> MariaDB
  -> allowlisted normalization -> SDK MCP result -> gateway
```

Woo MCP owns its five schemas/implementations, Woo REST client/authentication, bounded timeouts, normalized responses and sanitized errors. It does not own gateway users, team roles, individual API keys, dashboard sessions, audit persistence, chat orchestration or external-client routing. REST avoids direct SQL and a WordPress webroot/DB credential dependency in the adapter. No adapter database, queue or persistent volume is required.

### Store connection and REST authentication

| Purpose | Accepted local design |
| --- | --- |
| Network connection origin | http://urumi-wordpress.urumi.svc.cluster.local |
| Canonical/OAuth signing origin | http://store.urumi.test:8080 |
| REST prefix | /wp-json/wc/v3 |
| HTTP Host header | store.urumi.test:8080 |
| Redirects | Disabled; unexpected redirect is a configuration error |
| Local HTTP authentication | One-legged OAuth 1.0a, HMAC-SHA256, Authorization header |
| Future HTTPS authentication | Basic authentication over verified TLS; never disable certificate/hostname validation |

WooCommerce 11.2.1 verifies the OAuth base URI using the configured home URL, so signing the Service hostname alone is not equivalent. Sign the canonical URL and send the identical method/path/query via the internal Service with the canonical Host header. These are fixed deployment settings, not tool inputs. This avoids assuming Windows hosts-file entries resolve inside Pods. Use an established, pinned OAuth library, not manual cryptographic signing. [Woo authentication](https://developer.woocommerce.com/docs/apis/rest-api/authentication/) and [pinned implementation](https://raw.githubusercontent.com/woocommerce/woocommerce/11.2.1/plugins/woocommerce/includes/class-wc-rest-authentication.php).

**The origin mapping is not runtime-proven. Stage 4.3 must prove one authenticated read before full MCP implementation.** Check Service routing, canonical signing including port/query encoding, Apache Authorization-header handling and absence of redirects. Stop on failure; do not silently switch origins, change WordPress options or put credentials in query strings. Public Ingress TLS does not turn an internal HTTP hop into HTTPS: production internal HTTP still needs OAuth. HTTP is plaintext and Woo's OAuth does not sign the JSON body; this is not TLS-equivalent confidentiality/integrity.

### Credential ownership and local preparation

| Secret in urumi | Exact keys | Consumer / lifecycle |
| --- | --- | --- |
| urumi-woocommerce-rest | consumer-key, consumer-secret | Only future Woo MCP; manually issued Read/Write Woo REST pair, mounted as read-only files |
| urumi-woo-mcp-auth (future) | token (proposed) | Separate gateway-to-Woo MCP service credential; implementation deferred until gateway integration |

The gateway never receives the Woo REST pair; users' gateway keys are never forwarded upstream. Initial local issuance may use the existing WordPress administrator, accepting its broader authority; a dedicated least-privilege service user requires a separately reviewed capability/operational design. A service-account name alone does not prove restricted permissions. No new user is created by Stage 4.2.

The dedicated helper keeps the original four-Secret store helper unchanged. PowerShell 7 is required; context k3d-urumi-local, namespace urumi and Secret name are fixed. It never creates a namespace, generates Woo keys, rotates credentials or authenticates to WooCommerce.

| Mode | Implemented helper behavior | Stage 4.2 evidence boundary |
| --- | --- | --- |
| Validate (default) | Offline parser, dummy manifest/key and mocked workflow checks; real kubectl path is guarded | Offline execution only |
| Check | Verify named context and Active namespace, then project Secret identity/type/lifecycle/key names; absent is reported without creating | Mocked only; live projection untested |
| Create | Preserve a valid existing object without prompting; otherwise mask consumer-key and consumer-secret separately, encode in memory, create via stdin, then Check | Mocked only; no real prompts or writes |

Check requires Opaque and exactly the two case-sensitive keys; extras, missing/mis-cased keys, wrong identity/type or termination fail. It does not retrieve/decode values into helper output or prove nonempty/current/working credentials. kubectl necessarily receives the API Secret internally before projecting metadata/key names; this is not a special metadata-only Kubernetes authorization permission. Input shape checks reject blank, edge-whitespace, NUL/CR/LF or over-1024-character text without echoing it; they do not prove Woo issued the values.

The future create command is kubectl create -f - with explicit context/namespace, fixed non-secret arguments and in-memory JSON stdin. Both pipes are drained; all stderr and create stdout are discarded. A timeout/name race/postcheck failure stops with a generic operation/object message, never patch/replace/delete/retry. A failed acknowledgement can still leave a created object: inspect it before retrying. Clear byte/BSTR buffers, dispose SecureStrings and release managed references; immutable managed strings and external host/Kubernetes logging cannot be guaranteed erased. Use a trusted non-traced, non-debugged, non-transcribed local terminal. Exact helper behavior and checks are recorded in [progress](progress.md#stage-42-accepted-woo-mcp-design-and-offline-rest-secret-helper).

Gateway-only access remains mandatory. The user explicitly defers urumi-woo-mcp-auth and its service-token middleware until gateway integration. No public Ingress/NodePort/LoadBalancer may expose Woo MCP. ClusterIP is not caller isolation; before the service credential is enforced, an internal diagnostic prototype cannot be claimed to satisfy REQ-WOO-08. Final external clients must connect only to the gateway.

### Five initial tool contracts

All inputs reject unknown fields and invalid types. IDs are positive integers; prices are decimal strings, not floats. No raw REST parameters, arbitrary URL or SQL input. Successful SDK results use typed structured output; read tools are annotated read-only and write tools mutating, without treating annotations as authorization. Listing is explicitly paginated and never silently fetches the whole store. Oversized responses fail clearly rather than silently truncate records; exact response-byte bounds need implementation-time selection/testing.

| Tool | Inputs | Normalized success |
| --- | --- | --- |
| list_products | page >=1 default 1; per_page 1-50 default 20; optional search 1-100 characters OR sku 1-64 characters; optional status publish/draft/pending/private | items: Product[], pagination, currency |
| create_product | name trimmed 1-200 characters; price nonnegative decimal string <=999999999.99 with at most 2 fraction digits; optional sku 1-64; status publish (default) or draft; stock_status instock (default) or outofstock | product: Product, created: true |
| list_orders | Same pagination; optional date "today" or YYYY-MM-DD; optional status pending/processing/on-hold/completed/cancelled/refunded/failed | items: OrderSummary[], pagination, resolved date window |
| get_order | order_id positive integer | order: OrderDetail |
| update_order_status | order_id; required status pending/processing/on-hold/completed/cancelled/failed; required expected_status from the seven standard order states above | order_id, observed_before_status, after_status, changed |

Pagination is page/per_page/total/total_pages/has_more, using validated Woo response headers. Concurrent store writes mean pagination is not a snapshot. Product fields: id/name/sku/type/price/regular_price/currency/status/stock_status/permalink. create_product creates only simple products; price maps to regular_price. No images/HTML/variations/categories/arbitrary metadata. A supplied SKU is checked before POST; an existing match returns DUPLICATE_SKU, not implicit update/reuse. Woo's create-time uniqueness remains authoritative against races. No automatic creation retry; after an ambiguous response inspect by SKU before deciding. SKU is optional to preserve the assignment's name-and-price demo, with weaker ambiguous-write recovery if absent. [Products API](https://developer.woocommerce.com/docs/apis/rest-api/v3/products/).

OrderSummary: id/status/created_at/currency/total/payment_method. OrderDetail adds line items (product_id, variation_id when applicable, name, sku, quantity, unit_price, subtotal, total), shipping lines (method_id, method_title, total), shipping_total and tax_total. Use offset-bearing timestamps and decimal-string money. Exclude customer objects/names/contact/address, customer notes, order keys and arbitrary metadata. Request only necessary REST fields where supported, then independently normalize through an allowlist; no raw object/body logging. Returned names/text remain untrusted model data.

Date omitted means no date filter. Resolve "today" once in the configured store timezone, currently Asia/Kolkata, and return the resolved date/timezone/start-inclusive/end-exclusive window so subsequent pages can use the date across midnight. For 2026-10-23, local midnight to next midnight corresponds to [2026-10-22T18:30:00Z, 2026-10-23T18:30:00Z). Use dates_are_gmt=true and UTC filters; the proposed strict-boundary mapping uses after=start minus one second and before=end for second-resolution timestamps. Verify boundaries against the active order datastore before accepting runtime behavior. Order 12 was created on 21 October; later "today" queries may correctly omit it. [Orders API](https://developer.woocommerce.com/docs/apis/rest-api/v3/orders/), [query implementation](https://raw.githubusercontent.com/woocommerce/woocommerce/11.2.1/plugins/woocommerce/includes/rest-api/Controllers/Version3/class-wc-rest-crud-controller.php), [date boundaries](https://developer.wordpress.org/reference/classes/wp_date_query/).

Status update: GET current order -> reject expected_status mismatch -> if already at target, changed=false without PUT -> otherwise one PUT containing only status -> normalize/check returned state. No invented fulfillment state machine; Woo/plugin-rejected changes are sanitized failures. Refunded/trash/checkout-draft are not writable targets; a label change is not a refund. Status hooks may affect stock/notifications. Read-before-write is not atomic compare-and-swap and does not eliminate races with an administrator. Product 11/order 12 are preserved until a separately authorized runtime write test.

### Errors timeouts and tests

| Failure | Stable tool error code |
| --- | --- |
| Connection/DNS | WOO_UNREACHABLE |
| Authentication/permission | WOO_AUTH_FAILED / WOO_FORBIDDEN |
| Request/tool timeout | WOO_TIMEOUT |
| Missing object | NOT_FOUND |
| Input validation | VALIDATION_ERROR |
| SKU conflict | DUPLICATE_SKU |
| Stale expected status | STATE_CONFLICT |
| Rejected transition | INVALID_TRANSITION |
| Other Woo 4xx / Woo 5xx | WOO_REQUEST_REJECTED / WOO_UPSTREAM_ERROR |
| Malformed upstream response | WOO_INVALID_RESPONSE |
| Redirect/configuration mismatch | WOO_CONFIGURATION_ERROR |
| Oversized response | WOO_RESPONSE_TOO_LARGE |

SDK ToolError exposes a sanitized code/message with isError=true, not a success object containing an error. Its high-level error result has no normal structured success payload. SDK handles malformed protocol requests. Never forward raw upstream errors, Authorization, bodies or customer details. Log only safe operation/correlation/duration/outcome data; gateway audit persistence remains elsewhere. [SDK errors](https://py.sdk.modelcontextprotocol.io/servers/handling-errors/).

Starting configurable budgets: connect 2s; read/write 5s each; pool acquisition 1s; absolute REST request 8s; whole tool 20s including prerequisite reads; future gateway 25s. No automatic REST retry, including reads, initially. A lost write response, cancellation or 5xx may follow a committed mutation: report write_outcome=unknown and retry_safe=false rather than claim rollback. No automatic ambiguous-write retry at any layer.

Tests later cover strict validation/normalization/privacy, Decimal/timezone boundaries/status checks, mock exact HTTP methods/paths/signatures/origins/redirects/TLS/errors, single-write counts and duplicate/stale-state cases. Protocol tests verify exactly five tools, schemas and error flags with modern/legacy clients. Runtime acceptance follows real credential preparation and one authenticated read, then discovery/list product 11/list/get order 12, a separately authorized new MCP product and controlled status update. No live acceptance ran in Stage 4.2.

### Proposed package and Kubernetes boundaries

Future apps/woo-mcp has pyproject.toml plus exact dependency lock; src/woo_mcp/server.py (SDK/lifespan/health), config.py (origins/Secret paths/settings), woocommerce.py (pooled client/signing/deadlines), models.py (schemas/DTOs), errors.py, tools/products.py and tools/orders.py, package initializers and focused tests. Service authentication is added only at gateway integration. No Python package/scaffolding is authorized by Stage 4.2.

Future one-replica Deployment/one worker and ClusterIP urumi-woo-mcp in urumi, port 8000 -> named http port; internal /mcp only, no public route or PVC. Read-only scoped Secret files; no database/admin/salt mounts or service-account API token. Starting CPU request/limit 50m/500m and memory 128Mi/256Mi are hypotheses to measure under the existing host-memory gate, not proof of full-stack capacity. Extend the same application chart/local-production values later, without changing the store budgets to fit.

Proposed startup proves initialization/config/credential loading; liveness tests local process health; readiness proves SDK/client initialization and ability to accept requests. Store reachability is deliberately checked by tool calls, not every readiness probe: discovery remains available and a reachable adapter can report a Woo dependency error. "MCP connected" does not prove the store is operational. Origin validation remains enabled; there is no browser CORS use case. ClusterIP reachability alone is not gateway-only enforcement.

## Open and provisional decisions

- Local Docker/k3d operational validation and the fundamentals lab are complete. Vite and actual production-like k3s deployment remain future work. React, Kubernetes and Helm are assignment constraints; Python/FastAPI, SDK, PostgreSQL, MariaDB and controller boundaries are project choices. Store versions are selected above; runtime validation and application package pinning remain pending.
- Stage 4 pins the Woo SDK/protocol and defines its contracts above. Transitive/signer pins, actual modern/legacy interoperability, canonical HTTP OAuth connectivity, date boundaries and budgets still need validation. Gateway catalog refresh, client behavior and health observation remain future work.
- Specify authentication algorithms/formats, session/cookie/CSRF and invitation details, role representation, initial admin/WooCommerce registration, runtime Secret management, audit failure/denial/redaction/retention contracts, and schema constraints before affected implementation.
- Select the LLM/provider, chat-loop integration/response transport, auxiliary tool schemas and final interactive client. Define revenue-demo semantics and user A/B roles. Woo REST/tool contracts are accepted above but not implemented.
- Implement and validate the accepted store contracts only in a separately authorized step. Confirm initial store settings, filesystem permissions, safe Job reruns, retained-claim reuse, probes, checkout and measured memory. Production TLS provisioning and non-store deployment details remain open. NetworkPolicy is deferred, not a first-core prerequisite.

No bonus or stand-out item is selected. Current Stage 4.2 authorizes accepted-design documentation and the offline REST Secret helper only: no real credentials, cluster start/access, Kubernetes/Helm changes, Python MCP implementation, staging or commit. Earlier implementation sections preserve milestone history; [progress.md](progress.md) and [project-journey.md](project-journey.md) distinguish current evidence from that history.

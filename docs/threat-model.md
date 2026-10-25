# Threat model draft

Status: analysis aligned with approved Architecture v1 and accepted Stage 4 Woo MCP design. Store runtime evidence is scoped in [progress](progress.md); historical Stage 3 sections below retain their milestone limits. Stage 4.2 adds only an offline REST Secret helper, not deployed MCP credential/isolation evidence. This update awaits review. The [original assignment](source/urumi-mcp-gateway-assignment.docx) and [assignment.md](assignment.md) define scope. This document supports REQ-DEL-05 and the mandatory security-posture video coverage (VID-04). Discussing a risk does not commit the project to every possible mitigation.

## Assets actors and trust boundaries

Assets include per-user gateway keys and hashes, upstream and store credentials, LLM credentials if used, team identities, server registrations, product/order data, WordPress content, and audit records. Actors include admins, members, unauthenticated clients, external MCP clients, the chat model/tool loop, and potentially malicious or compromised upstream servers. A storefront shopper is distinct from a gateway team member; no account linkage is assumed.

The relevant boundaries are browser/client → gateway, chat orchestration → gateway under a user identity, gateway → upstream using that upstream's credential, custom WooCommerce server → store, and workloads → state/Secrets. Approved [Architecture v1](architecture.md) uses dashboard sessions, individual Bearer MCP keys, a shared gateway call path, Kubernetes service Secrets, and internal upstream authentication. Exact authentication/verifier, runtime Secret-management, and deployment mechanisms still need validation. No current deployment can be used as security evidence.

## Assignment-required threat analysis

Source: “Demo video and submission (mandatory) / Deliverables (in the repo)” requires these four topics. Its video security-posture section also requires explaining credential handling, member abilities, and what happens when an admin adds a malicious/compromised server. These are mandatory analysis obligations even where a mitigation appears only in optional stand-out work.

| ID | Required topic | Initial analysis and implications | Required boundary / unresolved detail |
| --- | --- | --- | --- |
| THREAT-01 | Shared upstream credentials: what a member can do with a credential they never see | Hiding a credential does not remove the authority it grants. A member who can invoke a tool can exercise the upstream credential's permissions through that tool, potentially including product creation and order updates. Multiple users may therefore act with the same upstream authority | Keep credentials server-side; document actual tool powers. Do not claim members are read-only: granular tool permissions are optional and unselected |
| THREAT-02 | Why client tokens are not passed through to upstream servers | A client gateway key establishes identity at the gateway. Forwarding it to an upstream would disclose a reusable gateway credential to a different trust boundary and confuse which service the credential is intended to authorize | Chat identity comes from the session; external identity from the individual key; both enter the shared gateway path (A6/A9). Use separate upstream credentials, never gateway tokens. Runtime Secret lookup remains open (A7) |
| THREAT-03 | Untrusted upstreams: tool descriptions written to manipulate the model | Tool names/descriptions and results may contain instructions intended to redirect the model, solicit secrets, select destructive tools, or misuse another server's tools. Admin registration is not proof that a server remains trustworthy | Analyze the actual tool loop and data exposure before implementation. Gateway role/key checks, routing and auditing remain required. Specific prompt-injection defenses are not prescribed by the assignment and are not claimed to exist |
| THREAT-04 | What one team member can do to another | Users may share store state and upstream authority. One user's writes can affect data another reads; expensive calls can consume shared resources. Identity confusion could misattribute actions, and weak management checks could let a member change access or registrations | Enforce admin/member management boundaries and user attribution. Per-user tool restrictions, rate limits, and multi-store isolation are optional; do not promise tenant/data isolation for the mandatory single-store core |

For the required malicious-server discussion, also consider an admin registering a URL that targets sensitive internal services, a slow/dead upstream, and an upstream returning misleading content. Failure isolation/timeouts are required. SSRF protections and detailed additional defenses are optional stand-out work; the final note/video must honestly describe the implemented controls and remaining exposure rather than imply those defenses are mandatory or complete.

## Assignment-required security controls and evidence

This section records mandatory controls separately from the analysis topics above. All evidence is pending.

| Assignment requirement | Required behavior | Planned verification / unresolved point |
| --- | --- | --- |
| REQ-SEC-01 | No hardcoded secrets; credentials, including LLM API keys, live in Kubernetes Secrets | Store helper implemented with offline/mock checks; real creation/consumption and other credential paths remain unverified. Base64 encoding is not encryption |
| REQ-WOO-08, REQ-GW-07 | WooCommerce MCP server internal-only and callable only by gateway; both chat and external clients go through gateway | A10: ClusterIP, no upstream public Ingress/NodePort/LoadBalancer, and gateway-held authentication. Validate positive gateway path, rejection without that credential, and external non-exposure; network isolation is not yet proven |
| REQ-GW-05 | Browser and MCP clients never receive upstream credentials | Inspect response/log paths and credential movement; admin submission of a credential must not imply it is returned later |
| REQ-TEAM-01, REQ-TEAM-02 | Admin/member boundaries with admin management of servers/members and invitation capability | A6/A13: email/password with server-side sessions; manually shared single-use expiring invitations. Test role enforcement and redemption; session/token protection details open |
| REQ-TEAM-03, REQ-TEAM-04, REQ-TEAM-05 | Per-user keys, hashed storage, revocation, admin issuance/revocation, member self-generation; revoked key's next call rejected | A6: raw key shown once, verifier/hash only, request-time revocation. Verify storage and denial during existing MCP sessions; algorithms/key identifiers remain open |
| REQ-AUD-01, REQ-CHAT-02 | Every tool call records user/server/tool/time/duration/outcome; dashboard visibility; chat uses logged-in identity | A9/A13: common gateway path; known revoked keys may have attributed denied events, unknown invalid credentials never falsely attributed (OPEN-04). Verify required demo evidence; retention/redaction and audit persistence-failure behavior remain open |
| REQ-GW-01, REQ-GW-02, REQ-GW-04 | Disabled server tools disappear; one slow/dead server does not break others; calls time out clearly | A5/A13: immediate disabled filtering and stale-call denial, stale metadata retained for enabled unreachable servers, configurable timeouts, no automatic ambiguous-write retries. Validate client refresh and healthy-peer isolation |

The user's working rule additionally prohibits real secrets in source code or committed configuration, including documentation/examples. This is a project rule, not an optional hardening item.

Approved credential ownership (A7): recoverable service values in Kubernetes Secrets; PostgreSQL stores metadata/references and user credential verifiers. WooCommerce REST credentials belong only to WooCommerce MCP; LLM provider credentials only to backend chat orchestration. Upstream credentials must never be returned by read APIs. Secret storage/injection and runtime management remain unverified; Secret encoding alone is not encryption at rest.

For A10, an internal ClusterIP does not block other cluster workloads from reaching the address. Gateway-held authentication supplies the initial additional caller boundary; access with a stolen credential remains a residual risk to explain. Calico/custom NetworkPolicy setup is not a prerequisite for the first core. NetworkPolicy may be added after the mandatory flow works if time allows or needed to strengthen the documented gateway-only boundary. This does not waive the assignment's gateway-only outcome or claim network-level isolation already exists.

## Stage 3.3 store credential and bootstrap boundary

Static implementation only; no deployed security evidence. ConfigMap assets contain code and non-secret configuration references. The Job projects only app DB, initial WordPress admin and WordPress auth keys/salts; root DB and future REST credentials are absent. Admin password input uses the mounted Secret through WP-CLI stdin, avoiding process arguments/plaintext temporary files. The Job has no public endpoint or Kubernetes API token. No Secret values or objects are rendered by Helm.

Bootstrap distinguishes authenticated DB failure from an empty database, verifies the versioned archive checksum, disables unattended updates and refuses unknown ownership, changed contracts or conflicting established settings. It never resets users/passwords/products/orders. Checkpoints and the completion marker are ordinary database state, not authorization credentials or tamper-proof evidence. They do not defend against an administrator or malicious PHP with DB access. Ordinary error handling avoids raw DB/exception details; this is not a claim that arbitrary plugins cannot log sensitive data.

Runtime Secret-file permissions, safe reruns and fail-closed readiness are still unverified; PHP syntax checking is also outstanding. Serialization of release operations is an operational requirement because Job revision names are not a concurrency lock. A partial core installation or interruption before ownership is recorded requires reviewed recovery. These controls implement the selected store contract; they do not select optional gateway hardening.

## Stage 3.4 local Secret preparation boundary

The [helper](../scripts/setup-store-secrets.ps1) targets only the four current store Secrets. Root DB material belongs only to MariaDB; the shared app DB password belongs to MariaDB/WordPress/bootstrap; initial admin input belongs only to bootstrap; auth keys/salts belong to WordPress/bootstrap. WooCommerce REST credentials remain deferred until the store can issue them for the custom MCP server.

Default offline validation cannot reach kubectl. Future Check is read-only; Create requires all existing objects to pass preflight, preserves them and submits only absent objects through create -f -. A name race fails instead of overwriting another Secret. Missing/mismatched keys, wrong type/identity or invalid credential text stop for explicit repair. This does not authenticate against the database or recover credentials for retained volumes.

Cryptographic generation, masked admin input, in-memory JSON/stdin and a single subprocess wrapper avoid command-line/file/console payloads. Raw stderr, create responses and exception details are not forwarded. Byte/unmanaged buffers are cleared where possible; immutable managed strings, host inspection/logging and external Kubernetes audit/admission systems are outside that guarantee. Do not trace/debug/transcript credential-bearing execution. Read access to these Secrets remains powerful; base64 is not encryption.

Offline fixtures, mocked control flow and harmless process-pipe tests are the only new evidence. API access, actual interactive input, partial writes/timeouts and workload consumption remain unverified. Failure may leave some newly created objects; preserve and inspect them on retry, without automatic deletion or rotation. No optional gateway hardening is selected.

## Stage 3.7C public storefront and migration boundary

Public Live catalog access implements the assignment's storefront flow and the user's deterministic demo contract; it is not optional hardening. The v3 migration uses the existing bootstrap identity and WordPress option APIs. No new credentials, permissions, Secret mounts or public administrative endpoint are introduced. Publishing the catalog does not authorize exposing order customer details, credentials or private checkout access keys.

Matching ownership, completed business/rewrite checks, a small allowlist of visibility states and marker-last completion bound migration scope. Unknown states and completed-v3 visibility drift fail rather than being adopted. Finalize reads both Live values in a separate process before advancing ownership/marker. These checks are not tamper-proof against database administrators or malicious PHP; option hooks still execute normally. Release serialization remains operational, not a database lock.

Readiness verifies both Live options without external HTTP, while independent startup/liveness remain unchanged. Anonymous HTML acceptance is separate because healthy options/probes do not prove visible content. The 95 fixture assertions use in-memory stubs/data sentinels and never load WordPress or its database; syntax validation alone uses PHP already in the pinned container. No live option modification, Secret retrieval or runtime migration is part of this step. Existing order 12/product 11 remain valuable state; rollback cannot rewind database/files, and no automatic downgrade is defined. No optional security feature is selected.

## Stage 4 REST credential and adapter boundary

Accepted design and offline helper only; see [architecture](architecture.md#accepted-woocommerce-mcp-design) and DEC-026 through DEC-029. Stage 4.3 connectivity remains unproven; no real key, Secret, Python MCP server, middleware or Deployment was created here.

- **Credential ownership:** Only Woo MCP consumes urumi-woocommerce-rest (consumer-key/consumer-secret). Gateway identities/tokens are not forwarded; gateway receives neither REST value. The initial administrator-associated Read/Write key has broad authority: hiding it does not make product creation/status changes harmless or members read-only. A dedicated restricted user is a future reviewed option, not implemented least privilege.
- **Transport:** Internal Service DNS connection plus canonical store signing URL/Host must be validated together. Use OAuth 1.0a HMAC-SHA256 Authorization on HTTP, an established signer, and no redirects/query-string credentials. OAuth does not encrypt HTTP or sign Woo's JSON request body. Verified HTTPS can use Basic; public TLS alone does not protect internal HTTP. This store authentication is unrelated to optional MCP gateway OAuth login.
- **Caller isolation remains incomplete:** urumi-woo-mcp-auth and middleware are explicitly deferred until gateway integration. Woo MCP must have no public Ingress/NodePort/LoadBalancer. ClusterIP does not stop other cluster workloads connecting; final gateway-only enforcement and rejection tests remain mandatory, not satisfied by this helper or design.
- **Helper exposure controls:** Fixed target, no sensitive arguments/env inputs, separate masked prompts, in-memory JSON/stdin, one bounded subprocess wrapper with no shell, discarded stderr/create output, generic operation-only failures. No credential dumps or manifest files. Check projects identity/type/lifecycle/key names only; kubectl still receives the API Secret in memory, so ordinary Secret-read authority is required. Check never proves the key pair works or that values are nonempty.
- **Residual handling risks:** SecureString/BSTR/byte cleanup reduces avoidable retention, but immutable managed strings, terminal tracing/debugging/transcription, host compromise and Kubernetes audit/admission logging are outside that guarantee. Do not run credential-bearing operations in traced/debugged/transcribed sessions. Name races or uncertain acknowledgements stop; inspect without deleting/rotating a potentially created Secret. No automatic overwrite or rollback.
- **Response boundary:** Allowlist product/order operational fields; exclude customer name/contact/address, notes, order keys and arbitrary metadata. No raw HTTP bodies/headers/errors in logs or MCP results. Returned names/text are untrusted model input. Successful status changes may invoke Woo hooks; read-before-write is not atomic and timeout is not proof of non-mutation. No automatic write retry.
- **Evidence still needed:** Real masked prompting/projection/stdin handling, REST authentication/canonical origin, runtime privacy/error behavior, gateway-only access, safe credential rotation and complete gateway audit attribution. Offline fixtures do not establish those outcomes.

No additional optional hardening is selected by these decisions. The mandatory secret-handling/gateway-only outcomes remain distinct from the optional controls below.

## Stage 4.8 custom Woo MCP hosting evidence

This stage authorizes a narrow container posture, not completion of the optional
hardening bonus. The [hosting contract](../apps/woo-mcp/README.md#process-container-and-helm-hosting)
records exact settings. Real TCP and Linux Docker discovery used synthetic files
only; no real REST Secret, live Woo request or business mutation was involved.

- **Process/transport:** Uvicorn directly runs the SDK ASGI factory and its lifespan;
  SDK DNS-rebinding protection stays enabled with explicit incoming hosts and no
  allowed browser Origins/CORS. Invalid Host and Origin were rejected in real TCP
  tests. Host allowlisting does not authenticate a caller; a malicious in-cluster
  client can supply an accepted Host. Access/proxy-header logging/trust are disabled
  by the image command; signer/HTTP debug logging remains suppressed by the factory.
- **Credential movement:** Helm references only external urumi-woocommerce-rest,
  exact consumer-key/consumer-secret files, read-only 0440 under
  /run/secrets/woocommerce-rest. No literal values, ConfigMap copy or generated Secret.
  UID/GID/fsGroup 10001 is intended to read projected files; actual Kubernetes
  permissions await Stage 4.9. Credentials remain in process memory for signing;
  Python strings do not guarantee zeroization. No Kubernetes API token is mounted.
- **Validated custom image:** Official Python slim tag/amd64 digest and hashed runtime
  dependencies; deny-by-default build context. Docker acceptance proves UID/GID 10001,
  read-only root, zero effective capabilities, no-new-privileges, seccomp filtering,
  clean shutdown and no synthetic credential/header leakage in captured logs.
  Tests/caches/diagnostic CLI are absent from the image. An initial cache-copy failure
  was corrected and retested. No claim of image vulnerability freedom or complete
  supply-chain verification follows from these checks.
- **Availability:** TCP probes check only the adapter listener. They deliberately do
  not withdraw the endpoint on Woo dependency loss, and do not prove full protocol
  responsiveness. Resource budgets are unmeasured under real tool load; one replica
  and a single local node are not HA. Default rolling updates can need extra capacity.
- **Isolation still pending:** Rendered ClusterIP only, no Woo MCP Ingress/public
  Service or PVC, and the security contexts above. These resources are not installed.
  urumi-woo-mcp-auth/caller enforcement and targeted NetworkPolicy remain future
  gateway-integration obligations. Other cluster clients are not yet excluded.
  Public TLS does not protect internal HTTP OAuth traffic or JSON bodies.

## Optional hardening and stand-out work

Stage 4.8 explicitly selects non-root and related container controls for the custom
Woo MCP workload only, with Docker evidence above and Kubernetes runtime pending.
No optional item is complete across the platform. Other items remain unselected.
IDs refer to the separate [optional register](requirements.md#optional-work-register).
Selection requires an explicit reviewed scope; analysis alone does not authorize it.

| Source / optional ID | Optional work | Boundary with required core |
| --- | --- | --- |
| Other ways to stand out / 6) Security hardening; OPT-06 | SSRF protection for registered URLs, including internal/metadata addresses | The malicious-server discussion is mandatory; this particular hardening implementation is optional. Any future policy must account for the required internal WooCommerce upstream |
| Same section; OPT-06 | Least-privilege Kubernetes RBAC for components using the Kubernetes API | Kubernetes API access design is unresolved; do not introduce a provisioning component merely to implement this item |
| Same section; OPT-06 | Default-deny NetworkPolicies and non-root containers | Gateway-only access to the WooCommerce MCP server is mandatory; cluster-wide default-deny/non-root hardening is not automatically part of that requirement |
| Same section; OPT-06 | Upstream credentials encrypted at rest | Kubernetes Secrets are mandatory; the separate encryption-at-rest stand-out item is not selected or assumed satisfied by Secret encoding |
| Tool permissions; OPT-02 | Per-role/per-user server/tool restrictions, hidden tools plus direct-call denial | Basic admin/member management boundaries remain mandatory; read-only members are an optional policy example |
| OAuth on the gateway; OPT-03 | MCP OAuth browser login | Core API-key behavior and demo still need to be accounted for before selecting an alternative |
| Production-like VPS deployment; OPT-01 | TLS with cert-manager | TLS automation is explicitly optional; deployment/security claims must describe whatever is actually configured |
| Scaling; OPT-07 | Per-user/per-key rate limits and multiple gateway replicas | Required call timeouts and failure isolation do not silently require distributed rate limiting or multi-replica design |
| Hosted MCP servers; OPT-05 | Container-image registration with per-server Secret, limits, NetworkPolicy and clean removal | Core registration is by URL; hosting/provisioning arbitrary server images is optional |
| Bonus: multi-store provisioning; OPT-MS | Separate per-store resources, NetworkPolicy isolation, quotas/limits, store caps, provisioning timeout and safe recovery/teardown | Core is one store; cross-store isolation and provisioning controls apply only if this bonus is selected |

## Review before claiming security behavior

Update this analysis when actual interfaces and controls are implemented. Record verified controls and residual risks separately, including the scope of shared member authority, model exposure to untrusted content, audit visibility/retention, and credential movement. Do not equate a drafted note, an ignored secret filename, a Kubernetes Secret object, or a private Service address with proof that all security requirements are satisfied.

## Stage 5.1 gateway protocol boundary

Offline implementation only, 2026-10-25. The [gateway core](../apps/gateway/README.md) implements bounded independent upstream discovery/calls, exact registered-slug plus authoritative mapping, disabled-server filtering and fixed safe errors. It does not provide users/roles/API keys/audit or gateway-only upstream access. Never expose this unauthenticated endpoint to real callers. Kubernetes remains stopped and Woo is unchanged.

- **THREAT-01/02:** Optional registration-scoped bearer/static-header credentials are server-side fields, hidden from repr and explicit public projections. No inbound caller headers/token/metadata forwarding. Credentials cannot be URL user-info/query parameters; reserved headers/control characters are refused, redirects are rejected before SDK replay. Actual Secret resolution/encryption/rotation is deferred; tests use synthetic values only. HTTP is not confidential transport.
- **THREAT-03:** Names/schema descriptions/results are untrusted data. No model/system prompt or automatic tool chaining exists. Supported schemas/annotations survive, but annotations do not authorize operations. Raw errors and exception details are replaced; known SDK/HTTP wire loggers are suppressed, and literal credential reflection is rejected. A malicious upstream can transform/encode a credential: this is not universal leakage prevention or a prompt-injection solution. Future chat and telemetry changes require review.
- **Failure isolation:** Concurrent per-upstream deadlines, disabled filtering, no automatic retry or write reconciliation. A failed attempted call may already have changed data; return unknown outcome/unsafe retry. Session-level invocation deliberately avoids SDK convenience-method replay. Metadata pagination and parsed-publication caps limit ordinary payloads, not adversarial wire allocation/CPU. URL syntax checks and non-fetching schema references are not full SSRF/network isolation. No default-deny NetworkPolicy or optional security bonus is claimed.
- **THREAT-04/remaining:** Registry edit/disable/remove is rechecked before dispatch and stale observations cannot overwrite changed configuration. Already-sent calls cannot be revoked or rolled back. The in-memory repository has no authorization and is not a user-facing API. PostgreSQL persistence, management role checks, key revocation, durable per-user audit, shared chat enforcement and gateway-to-Woo credentials/NetworkPolicy remain required future work.

Protocol fixtures cover secret reflection, safe errors/logs, original-name routing, caller-token non-forwarding, cross-server credential scope and failure/cancellation. They do not prove production containment, protection from arbitrary customer PII in third-party results, or the final malicious-server demo.

## Stage 5.2 persistent management boundary

At the Stage 5.2 checkpoint the backend had unauthenticated /api routes and /mcp. This was
NOT YET AUTHORIZED and must not be publicly deployed. Loopback Host checks do not
replace login, admin/member checks, CSRF/session protection or key authorization.
No fake user or hardcoded admin was used. Stage 5.3 now enforces REST identity/roles
as recorded below; external MCP authentication and audit remain separate.

Per the explicit Stage 5.2 instruction, recoverable upstream values are stored in
PostgreSQL without application-level encryption. DB readers/backups can recover
them. This revises A7's implementation plan for this checkpoint only; it does not
satisfy or erase the assignment's final Kubernetes Secret obligation. No real keys
were entered. Optional encrypted-at-rest hardening is not implemented. The DB
connection URL is read from an external protected file, never a tracked value.

Management inputs accept only validated bearer/static-header credentials. PATCH
omission preserves, explicit object replaces, null clears. Safe read DTOs never
include credential values; rejected JSON/input and driver errors are sanitized.
SQL parameters/results and SDK wire logging are suppressed. Tests check credential
redaction, reflection refusal and malformed-input errors. Operator logging, tracing,
backups and malicious encoded reflection remain risks; do not enable body/SQL dumps.

URL validation rejects non-HTTP(S), missing hosts, userinfo, queries/fragments,
invalid ports, control/whitespace and overlong URLs; canonicalization preserves path
semantics. Internal DNS/private destinations must remain usable for the assignment.
No general SSRF/DNS-rebinding/metadata-endpoint containment is claimed. Advanced
network controls remain stand-out work; gateway-to-Woo authentication/targeted
NetworkPolicy remain required future caller-boundary work.

Last-good cached tool schemas/descriptions remain untrusted data, not trusted HTML
or model instructions. Failures retain stale management metadata but never enable
a disabled server or publish stale live MCP routes. Revision checks reject late
observations. Removal deletes credential/cache state; future audits must preserve
historical attribution independently. No audit table or retention policy is invented.


## Stage 5.3 identity and REST enforcement

Every server-management route requires an admin browser session. Anonymous receives
401, member 403; browser IDs/roles/headers do not establish identity. Safe allowlists
exclude password/token/key hashes from normal DTOs. Only explicit issuance returns
raw invitation/API-key tokens; sessions use HttpOnly Set-Cookie. API responses use
no-store. Submitted inputs, raw database errors and credentials are not logged;
operator tracing/exporters remain a separate leakage risk.

Argon2id uses independent salts and pinned defaults (64 MiB, 3 passes, 4 lanes).
Unknown usernames perform dummy verification with the same public login failure.
Two concurrent hash workers bound hashing memory, not request rate/queue capacity
or all enumeration timing. Random 256-bit tokens use SHA-256; password and token
threat models differ. Current expiry/revocation/user-enabled checks are server-side.
API-key verification uses constant-time digest comparison after indexed lookup;
admin revocation immediately invalidates that same raw key in tests. External MCP
does not yet invoke the verifier; Stage 5.4 must check every request, not handshake alone.

Cookies are host-only HttpOnly/Lax/Path=/; production requires Secure and HTTPS.
Exact configured Origin is mandatory on unsafe REST including login/acceptance;
missing/null/cross-origin and conflicting Sec-Fetch-Site are denied. No permissive
CORS or Referer fallback. This protects browser CSRF within the same-origin design,
not XSS or callers forging Origin. Local HTTP can explicitly disable Secure;
production TLS deployment remains untested.

Invites bind intended username/member role, default to 24 hours and claim atomically
with account creation. Concurrent redemption yields one member. Admin bootstrap is
an explicit protected-file command and durable receipt, never startup reset. Synthetic
fixture passwords are not deployment defaults. Python strings cannot be reliably
erased. User references restrict deletion for future audits. Disabling blocks tokens
while disabled; explicitly revoke if permanent invalidation is needed before enable.

130 tests plus real disposable PostgreSQL migration/concurrency/reconnect smoke pass.
No cluster/Woo changes. Remaining: external MCP still open, audit absent, no rate
limiting/recovery/MFA, broad SSRF absent, upstream PostgreSQL credentials recoverable
without application encryption, runtime Secrets and gateway-only caller enforcement
pending. REST identity does not make this backend production-ready.

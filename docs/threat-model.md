# Threat model draft

Status: analysis aligned with approved Architecture v1, with this documentation update awaiting review; no security controls are implemented or verified. The [original assignment](source/urumi-mcp-gateway-assignment.docx) and [assignment.md](assignment.md) define scope. This document supports REQ-DEL-05 and the mandatory security-posture video coverage (VID-04). Discussing a risk does not commit the project to every possible mitigation.

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
| REQ-SEC-01 | No hardcoded secrets; credentials, including LLM API keys, live in Kubernetes Secrets | Review repository/values and runtime references without revealing values; Secret creation/update mechanism open. Base64 encoding is not encryption |
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

## Optional hardening and stand-out work

No item in this section has been selected or implemented. IDs refer to the separate [optional register](requirements.md#optional-work-register). Selection requires an explicit reviewed scope; analysis alone does not authorize it.

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

# Project journey

This is the chronological engineering story for an interviewer walkthrough: how the repository and system evolve, why choices change, and what evidence supports each completed step. [progress.md](progress.md) describes current status; [decisions.md](decisions.md) records individual decisions. The [original assignment](source/urumi-mcp-gateway-assignment.docx) remains authoritative; this narrative does not redefine its requirements.

Add concise entries after meaningful completed steps. Cover starting state, problem, concepts, decision, alternatives, rationale, affected components, validation, learning, next-stage enablement, and commit when available. Do not turn this into a command-by-command log or describe future implementation as completed.

## Stage 0 — From an empty repository to a governed assignment baseline

Completed and reviewed on 2026-10-10; committed as **51f27b2 — docs: establish project governance and assignment baseline**.

- **Starting state:** An empty Git repository on master, with no commits or tracked project files. The user then supplied the original Urumi assignment DOCX under docs/source/.
- **Problem:** We needed to preserve the actual assignment, prevent scope drift, and establish a process in which the user could understand and review each engineering change before application work began.
- **Concepts:** Source of truth versus interpreted requirements; mandatory scope versus optional stand-out work; traceability from requirements to demonstrations; documentation approval versus implementation evidence.
- **Decision:** Preserve the original DOCX and create a faithful Markdown reading copy. Establish AGENTS.md, ignore rules, README, requirement/demo matrices, and architecture, decision, security, and progress documents. Keep technical choices proposed until separately reviewed.
- **Alternatives:** Working only from the DOCX would make later sessions harder to navigate. Replacing its wording with best practices could change scope. Generating an application scaffold immediately would cross the agreed learning/review boundary.
- **Why this approach:** It made the assignment durable and reviewable while keeping its mandatory requirements, bonus items, demos, deliverables, and evaluation expectations distinct.
- **Repository/components affected:** Nine governance text files plus the preserved source DOCX. There were no application components. After approval, the branch was renamed from master to main and the ten files formed the first commit.
- **Validation performed:** The transcription matched all 169 nonempty paragraphs in order, 119 list entries, and 29 heading depths. Source checksum, 40 local links/anchors, Markdown formatting, ignore behavior, and the complete governance diff were checked. Tracking covered 44 requirement rows, 11 live demos, 6 video groups, 10 optional items, and 7 interpretation questions. The staged checkpoint contained only the reviewed governance/source files; the first commit left a clean working tree.
- **What we learned:** A written plan does not demonstrate a working requirement. Separate requirement and demo matrices reveal obligations that a happy-path demo alone would miss, including all five WooCommerce tools, hashed keys, and failure isolation.
- **How this enabled the next stage:** Stable requirement IDs and visible uncertainties gave Architecture v1 a concrete scope and review vocabulary before selecting implementation boundaries.
- **Git reference:** 51f27b2. Source SHA-256: `e9f7e797d72c331ab508d75135490644c99b9bf2c172f36225ad861926d02f92`. Original and transcription remain unchanged.

## Stage 1 — Architecture v1 review before implementation

Design reviewed and approved on 2026-10-10. This documentation recording step is awaiting review and is **not committed**. No MCP prototype, application, schema, or deployment has been created.

- **Starting state:** Approved governance on main at 51f27b2, with a proposed technology baseline and unresolved architecture/demo mechanics. No runnable system existed.
- **Problem:** We needed a small deployable design with explicit tool routing, user identity, credential ownership, failure behavior, and deployment boundaries before writing code.
- **Concepts:** REST versus MCP responsibilities; an MCP gateway as both client and server; configured state versus observed health; authoritative name mapping; sessions versus API keys; credential verifiers versus recoverable service secrets; logical reuse versus separate services; internal addressing versus caller isolation.
- **Decision:** Approve A1–A13: one modular Python/FastAPI backend; browser REST and external MCP entry points; official SDK/Streamable HTTP upstreams; simple slug-prefixed names with stored routing; separate health/configuration and stale metadata; sessions, roles, and hashed/revocable keys; workload-scoped Secrets; seven persistence entities; chat through the shared gateway path; one namespace and one Helm release; deterministic arithmetic/reference upstreams; explicit demo interpretations.
- **Alternatives:** Separate backend services, a browser MCP client, permanent connection strategy chosen before a prototype, always-suffixed tool names, direct upstream chat calls, external-service-dependent auxiliary servers, and Calico/custom NetworkPolicy prerequisites were considered. The review chose simpler initial boundaries and deferred details needing runtime evidence.
- **Why this approach:** Shared gateway logic keeps chat and external calls under the same authorization, timeout, routing, and audit behavior. Deterministic upstreams make the cross-server demo reproducible. Simple names and a stored mapping preserve understandable labels without making routing depend on parsing them.
- **Repository/components affected:** Architecture and decision records now describe the accepted contracts; progress and working rules reflect the boundary. This journey was added, and README, requirements, and threat-model wording were aligned. These are descriptions of future components, not implemented interfaces.
- **Validation performed:** A1–A13 were reviewed by the user. Documentation link/reference, formatting, source-preservation, scope, and status checks passed; evidence is recorded in [progress.md](progress.md#validation-and-review-record). Complete text diffs accompany this recording step's review. No SDK/client, authentication, Kubernetes, Helm, or live demo behavior has been tested.
- **What we learned:** Approval can fix a boundary while leaving mechanisms open. A disabled server is intentionally hidden; an unreachable enabled server retains stale metadata. ClusterIP does not prove isolation inside the cluster. Store timezone defines today, and the required rollback explanation does not automatically require executing an optional live rollback.
- **How this enables the next stage:** A later, separately authorized milestone can plan focused compatibility/prototype checks against these contracts, rather than scaffold the whole system. Package versions, connection lifecycle, Secret management, and client refresh behavior still need evidence.
- **Git reference:** Pending; this documentation update is based on 51f27b2. Add its commit only after the user authorizes and completes a checkpoint.

The system is not finished. Extend this chronology as milestones actually complete; use the approved [working process](../AGENTS.md) and stop at review boundaries.

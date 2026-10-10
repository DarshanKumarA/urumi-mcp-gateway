# Decision register

This register explains project decisions; it does not override the [original assignment](source/urumi-mcp-gateway-assignment.docx) or its [Markdown transcription](assignment.md). Assignment obligations are constraints, not choices attributed to us. “Accepted” means explicitly agreed; “Proposed” is not authorization to implement. Every decision entry records context, alternatives, rationale, consequences, and requirement links where relevant.

## DEC-001 Governance before application implementation

- **Status:** Accepted by the user, 2026-10-10; resulting files awaiting review.
- **Problem:** The user must understand every engineering decision and meaningful change, and future sessions need durable scope and process.
- **Decision:** Begin with the nine approved governance files and preserve understand → plan → identify files → implement small change → review diff → validate → document → verify understanding. Stop at milestone boundaries; no application scaffolding or commit at this milestone.
- **Alternatives:** Start implementation alongside documentation, or create a full project scaffold. Both are outside the user's authorization.
- **Rationale:** A small documentation baseline makes requirements and proposals reviewable before technical choices become code.
- **Consequences:** Setup and all runtime behavior remain pending. This is not completion of any runtime requirement.
- **Related scope:** Assignment / AI usage; all later requirements and milestones.

## DEC-002 Original assignment and separate traceability

- **Status:** Accepted by the user, 2026-10-10; transcription and matrices awaiting review.
- **Problem:** An informal summary can miss requirements or promote optional features into core work.
- **Decision:** Keep the original DOCX authoritative; maintain a faithful assignment.md reading copy; put requirement IDs, implementation plans, demo mappings, and interpretations in separate documents. Explicitly separate required threat analysis from optional hardening.
- **Alternatives:** Use only the original DOCX, or replace it with an interpreted specification. The first is less convenient for future sessions; the second would lose source fidelity.
- **Rationale:** Preserve original wording and classifications while supporting verification and incremental planning.
- **Consequences:** Source changes require an explicit transcription/traceability reconciliation. Uncertain interpretations stay visible instead of becoming implicit decisions.
- **Related requirements:** REQ-DEMO-01, REQ-DEL-04, REQ-DEL-05, REQ-DEL-07.

## DEC-003 Proposed technology baseline

- **Status:** Proposed; not accepted by approval of the governance structure.
- **Problem:** The assignment defines behavior and selected technologies but leaves most implementation choices to us.
- **Proposal:** React + Vite, Python + FastAPI, official Python MCP SDK, Python upstreams if authored here, PostgreSQL control-plane state, WordPress + WooCommerce + MariaDB, Docker, Minikube with Docker driver, Helm, and a k3s production-like target.
- **Assignment constraints within that proposal:** React, WordPress/WooCommerce, Kubernetes, Helm rather than Kustomize, Kubernetes Secrets, and Streamable HTTP for the custom server/supported upstreams. Minikube and k3s are allowed examples, not mandated selections. The other upstreams need not be custom implementations.
- **Alternatives:** Kind/k3d locally; another backend stack or MCP SDK; another suitable state store or WordPress database; different allowed model/provider. No comparison or compatibility validation has been completed.
- **Rationale:** This is the user's initial baseline and provides a starting point for focused decisions; it is not evidence that every proposed tool is necessary or compatible.
- **Consequences:** No versions pinned, dependencies installed, or optional technologies selected. Split this proposal into specific accepted/rejected decisions as relevant milestones are reviewed.
- **Related requirements:** REQ-K8S-01, REQ-K8S-02, REQ-WOO-01, REQ-WOO-02, REQ-GW-02, REQ-UI-01, REQ-CHAT-01.

## Recording future decisions

Use a new stable DEC ID with status/date, problem, source constraints and requirement IDs, proposed/accepted choice, alternatives, rationale, consequences, and verification needs. Supersede old entries explicitly rather than rewriting history as if a choice had always been settled. Current interpretation questions are OPEN-01 through OPEN-07 in [architecture.md](architecture.md#unresolved-assignment-interpretations); none is resolved by this register.

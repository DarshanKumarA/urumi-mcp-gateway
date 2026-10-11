# Project progress

## Current milestone

**2026-10-11 — Stage 2 environment preflight reviewed; k3d selected for local Kubernetes.** Dates use the user's Asia/Calcutta calendar. This is a documentation checkpoint, not completion of the Kubernetes foundation.

Stage 0 governance was committed as **51f27b2 — docs: establish project governance and assignment baseline** on main. Architecture v1 and its journey were reviewed and committed as **db49836 — docs: define architecture v1 and project journey**. The existing unstaged journey update recording db49836 is included in this checkpoint.

A1–A13 remain accepted as DEC-004 through DEC-016. DEC-017 replaces the proposed local Minikube/Docker driver with k3d and Docker Desktop as the intended runtime. The assignment still permits Kind, k3d, or Minikube; its requirements have not changed.

No application, prototype, schema, dependency files, Kubernetes manifests, Helm chart, or deployment exists. No runtime requirement is implemented or verified and every live demo remains unrun. The chronological story is in [project-journey.md](project-journey.md); individual rationale is in [decisions.md](decisions.md).

## Current documentation change

- Record the accepted k3d choice and its Windows Ingress/k3s rationale in architecture and DEC-017, preserving the original Minikube proposal as history.
- Record developer-tool/WSL readiness, the missing Docker/kubectl/k3d/Helm toolchain, and resource findings concisely in the journey. The original preflight checked Minikube; a supplemental read-only check found no k3d installation.
- Align README and REQ-K8S-01 because they named Minikube as the proposed project baseline. Preserve the assignment's alternatives, all requirement/demo statuses, and optional scope.
- Include the prior journey checkpoint update. Only six existing Markdown files change; AGENTS.md, .gitignore, the threat model, assignment.md, and the original DOCX remain unchanged.

## Validation and review record

Stage 0's completed checks included exact transcription of 169 nonempty paragraphs, 119 list entries, and 29 heading depths; 40 local links/anchors; ignore rules; formatting; and complete governance diff review. Architecture v1's documentation checks passed on 2026-10-10: 56 local links across 9 Markdown files, consistent tracking IDs, unchanged assignment/source classifications, source checksum preservation, formatting, and complete diff review. These are historical checks, not evidence of working software.

Stage 2 preflight was read-only. Existing Git/Python/Node/npm and WSL were detected; the cluster toolchain was not. Approximately 24 logical CPUs and 110 GiB free disk supported initial planning, but only 2.6–2.8 GiB of 15.7 GiB RAM was available. Docker startup/container mode, cluster operation, Ingress, and a full-system resource budget remain untested. Detailed engineering findings are in the journey.

Current documentation checks passed on 2026-10-11 using inline Python and read-only Git commands. No validation scripts or scaffolding were added.

| Check | Result |
| --- | --- |
| Links and tracking | All 58 local links/anchors resolve across 9 Markdown files; 44 requirements, 11 demos, 6 video groups, 10 optional items, 7 interpretation IDs, 17 decisions, 13 Architecture v1 IDs, and 4 threat topics remain consistent. The three new official technical reference pages were opened successfully |
| Scope and status fidelity | Only REQ-K8S-01's implementation plan changes in the tracking tables; source wording, mandatory/optional classifications, verification/demo fields, and all statuses remain unchanged |
| Source and checkpoint preservation | Original DOCX SHA-256 remains e9f7e797d72c331ab508d75135490644c99b9bf2c172f36225ad861926d02f92; protected files unchanged; both prior journey edits recording db49836 retained |
| Formatting | Markdown table widths, UTF-8 without BOM, LF endings, final newlines, trailing whitespace, and Git whitespace checks pass |
| Change boundary | Six existing Markdown files modified; no new files/directories or application/generated files. Added-text credential-pattern scan is clean; the complete diff is reviewed before staging |

No application tests or runtime demos apply to this documentation-only change. Tool documentation and preflight observations do not prove a working Docker/k3d/Ingress deployment.

## Open and provisional work

- k3d is selected, with Docker Desktop as the intended runtime. Installation, compatible tool/image versions, node count, memory allocation, and host port availability need the next reviewed plan. Recheck available memory before cluster creation.
- Vite and k3s for the production-like VPS remain proposed baseline selections.
- SDK/protocol compatibility, exact pinned package versions, connection lifecycle, client refresh, timeouts, and health observation need an authorized prototype.
- Authentication algorithms/formats, session/invitation protections, runtime Secret management, schema details, audit persistence/denial/redaction/retention, and bootstrap need focused design/validation.
- LLM/provider, tool schemas and WooCommerce REST details, revenue-demo semantics, user A/B roles, and Claude Code versus Cursor need selection/validation. Inspector is selected for diagnostics.
- Chart dependencies, WordPress/MariaDB packaging, Ingress/DNS/TLS, storage, probes, and resources await the Kubernetes/store milestone. k3d alone does not establish stable URLs or prove VPS compatibility.

OPEN-01 through OPEN-07 in [architecture.md](architecture.md#unresolved-assignment-interpretations) have reviewed approaches under A13, with remaining validation noted. No optional feature is selected. NetworkPolicy is deferred, not a first-core prerequisite; the mandatory gateway-only requirement remains. Upgrade/rollback documentation and explanation are mandatory walkthrough material; executing live rollback is optional unless later evidence changes the interpretation.

## Review boundary

The user authorized this documentation checkpoint and the commit `docs: select k3d after environment preflight`, including the existing journey checkpoint update. This supersedes the earlier no-commit boundary for this change only. Show the changed files, complete relevant diff, documentation validation, final Git status, and latest three commits, then stop for review. No installation, cluster creation, application directories/code, or Helm scaffolding is authorized. The next step requires its own clear plan under [AGENTS.md](../AGENTS.md).

The assignment gives a two-week window but no actual start/due date. No submission deadline has been inferred or scheduled.

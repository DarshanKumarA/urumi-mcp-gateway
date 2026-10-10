# Project progress

## Current milestone

**2026-10-10 — Architecture v1 approved; documentation recording step awaiting review.** Dates use the user's Asia/Calcutta calendar.

Stage 0 governance was reviewed and committed as **51f27b2 — docs: establish project governance and assignment baseline** after renaming master to main. The working tree was clean at the start of this update. The current change is documentation only and must not be committed yet.

A1–A13 are accepted design choices, recorded as DEC-004 through DEC-016. No application, prototype, schema, dependency files, Kubernetes manifests, Helm chart, or deployment exists. No runtime requirement is implemented or verified and every live demo remains unrun. The chronological story is in [project-journey.md](project-journey.md); individual rationale is in [decisions.md](decisions.md).

## Current documentation change

- Record approved architecture, interfaces, credential boundaries, persistence inventory, namespace/chart boundaries, additional upstreams, and reviewed interpretations; leave implementation details explicitly open.
- Add the project journey with Stage 0 and the completed Stage 1 design review; distinguish approval of the design from pending review of its documentation.
- Update AGENTS.md to check the journey after meaningful steps and retain the documentation-only/no-commit boundary.
- Align README, requirements/demo plans, and threat-model wording with the accepted design without changing source requirements, promoting optional work, or claiming runtime evidence.
- Preserve .gitignore, assignment.md, and the original source DOCX unchanged.

## Validation and review record

Stage 0's completed checks included exact transcription of 169 nonempty paragraphs, 119 list entries, and 29 heading depths; 40 local links/anchors; ignore-rule checks; whitespace/formatting; and complete governance diff review. The source checksum was preserved. See the [journey](project-journey.md#stage-0--from-an-empty-repository-to-a-governed-assignment-baseline) for that checkpoint rather than treating those historical counts as current validation.

Current documentation checks passed on 2026-10-10 using inline Python and read-only Git commands; no validation scripts or scaffolding were added.

| Check | Result |
| --- | --- |
| Local documentation links | All 56 local links/anchors resolve across 9 Markdown files |
| Tracking references | 44 requirements, 11 demos, 6 video groups, 10 optional items, 7 interpretation IDs, 16 decision IDs, 13 Architecture v1 review IDs, and 4 required threat topics; references consistent |
| Scope and status fidelity | Requirement/demo source fields and mandatory/optional classifications preserved; runtime and demo statuses unchanged. REQ-DEL-04 now notes approved design with implementation still unverified |
| Source preservation | DOCX SHA-256 remains e9f7e797d72c331ab508d75135490644c99b9bf2c172f36225ad861926d02f92; assignment.md and .gitignore unchanged |
| Formatting | Table widths, UTF-8 without BOM, LF endings, final newlines, and trailing whitespace checked; Git whitespace checks clean |
| Change boundary | Seven existing text files modified and only docs/project-journey.md added; no application files/directories, staged changes, or new commit |
| Git checkpoint | Still main at 51f27b2; complete tracked-file and new-file diffs are included in the review handoff |

An initial patch-format attempt was rejected because it targeted architecture.md twice in one patch; it changed no files. The edits were then applied with a valid update operation. The first tree display hit a Windows console encoding error on box-drawing characters; the display was retried with ASCII, with no file changes. No application tests or runtime demos apply to this documentation-only change; SDK/client and deployment compatibility remain untested.

## Open and provisional work

- Vite, Docker, Minikube with Docker driver, and k3s remain proposed baseline selections.
- SDK/protocol compatibility, exact pinned package versions, connection lifecycle, client refresh, timeouts, and health observation need an authorized prototype.
- Authentication algorithms/formats, session/invitation protections, runtime Secret management, schema details, audit persistence/denial/redaction/retention, and bootstrap need focused design/validation.
- LLM/provider, tool schemas and WooCommerce REST details, revenue-demo semantics, user A/B roles, and Claude Code versus Cursor need selection/validation. Inspector is selected for diagnostics.
- Chart dependencies, WordPress/MariaDB packaging, Ingress/DNS/TLS, storage, probes, and resources await the Kubernetes/store milestone.

OPEN-01 through OPEN-07 in [architecture.md](architecture.md#unresolved-assignment-interpretations) now have reviewed approaches under A13, with remaining validation noted. No optional feature is selected. NetworkPolicy is deferred, not a first-core prerequisite; the mandatory gateway-only requirement remains. Upgrade/rollback documentation and explanation are mandatory walkthrough material; executing live rollback is optional unless later evidence changes the interpretation.

## Review boundary

Stop after showing the repository tree/status, complete diff, documentation explanations, remaining decisions, and validation results. Do not stage or commit this update or create application directories/code/scaffolding. The next implementation milestone requires its own clear plan, identified files, and user authorization under [AGENTS.md](../AGENTS.md).

The assignment gives a two-week window but no actual start/due date. No submission deadline has been inferred or scheduled.

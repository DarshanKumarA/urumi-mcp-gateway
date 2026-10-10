# Project working agreement

## Read the assignment first

The authoritative source is [the original Urumi assignment](docs/source/urumi-mcp-gateway-assignment.docx). [docs/assignment.md](docs/assignment.md) is its faithful Markdown reading copy. If they disagree, the original wins: report the discrepancy and correct the transcription explicitly. Do not silently reinterpret, correct, expand, or replace assignment requirements with general best practices.

Read [requirements](docs/requirements.md), [architecture](docs/architecture.md), [decisions](docs/decisions.md), and [progress](docs/progress.md) before planning a change. Consult the [threat model](docs/threat-model.md) for security-related changes. Mandatory requirements, demo obligations, deliverables, bonus work, and evaluation expectations are distinct. Optional work is not authorized merely because it appears in the assignment or a design proposal.

## Required change process

Follow this sequence: **understand → plan → identify files → implement small change → review diff → validate → document → verify understanding**.

1. Understand the relevant assignment sections, existing behavior, accepted decisions, and current milestone. Explain uncertainty instead of choosing an interpretation silently.
2. Before a meaningful change, explain the problem, proposed design, why it fits, and relevant alternatives. For existing code, explain why it must change, exactly what changes, affected components/interfaces, and why the new approach is preferable.
3. Identify every intended file creation or modification. Do not edit until the plan is clear. Respect the user's current authorization; a proposed future step is not permission to implement it.
4. Implement one small, reviewable change. Do not generate the whole project at once or add optional technologies/features without agreement on the requirement they solve.
5. Show and review the complete Git diff, including new files, and explain each changed file. Preserve unrelated user changes and the original assignment document.
6. Run relevant tests or validation and report commands, results, failures, and limits honestly. Documentation is not evidence that a system requirement has been implemented or verified.
7. Update the relevant requirements, decision records, progress notes, and security analysis. After each meaningful step, check whether [docs/project-journey.md](docs/project-journey.md) needs an entry or update. Progress describes current status; decisions explain individual choices; the journey preserves the chronological engineering story, reasoning, validation, learning, and commit references for an interview walkthrough. Keep it concise, not a command log. Keep proposals separate from accepted choices and implemented behavior.
8. Stop at major milestone boundaries for the user to verify understanding before continuing. Do not commit, publish, or submit unless authorized.

## Security and scope rules

- Never put real API keys, passwords, tokens, secrets, or credentials in source code, documentation, examples, or committed configuration. Use clearly non-secret placeholders. An ignored file is not permission to embed secrets in code.
- Follow the assignment's mandatory secret-handling rules, including Kubernetes Secrets, hashed/revocable per-user gateway keys, and server-side upstream credentials. Distinguish these from optional hardening.
- Readiness/liveness checks, resource requests/limits, persistent storage, Ingress, and Helm are assignment obligations. Do not substitute another deployment approach.
- Keep optional security features, multi-store provisioning, and other stand-out work separate from the mandatory core. Do not turn an analysis item into an implementation commitment without review.
- Support the user's ability to explain the Kubernetes resources, MCP flow, credential movement, isolation, and engineering tradeoffs. Do not submit work the user does not understand.

## Current milestone boundary

Stage 0 governance was approved and committed as 51f27b2 on main. Architecture v1 decisions A1–A13 have been reviewed and approved; the current milestone records them in documentation and adds docs/project-journey.md. Preserve the source DOCX and faithful assignment transcription. No application directories, manifests, charts, dependency files, Dockerfiles, frontend/backend code, ORM models, databases, or other implementation scaffolding are authorized. Prototype and implementation validation described in the architecture are future work, not permission to start. Do not commit this documentation update. Stop for review; update this boundary only when the user authorizes the next milestone.

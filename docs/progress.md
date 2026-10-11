# Project progress

## Current milestone

**2026-10-11 — Stage 2.2A Docker Desktop runtime validation passed after manual installation.** Dates use the user's Asia/Calcutta calendar. The Linux-container runtime prerequisite for k3d is ready; no Kubernetes cluster has been created.

Stage 0 governance was committed as **51f27b2 — docs: establish project governance and assignment baseline** on main. Architecture v1 and its journey were committed as **db49836 — docs: define architecture v1 and project journey**. The reviewed preflight/k3d documentation, including the prior journey checkpoint update, was committed as **1f2aec9 — docs: select k3d after environment preflight**. This setup attempt began with a clean working tree.

A1–A13 remain accepted as DEC-004 through DEC-016. DEC-017 replaces the proposed local Minikube/Docker driver with k3d and Docker Desktop as the intended runtime. The assignment still permits Kind, k3d, or Minikube; its requirements have not changed.

No application, prototype, schema, dependency files, Kubernetes manifests, Helm chart, or deployment exists. Docker's disposable learning validation passed; no assignment runtime requirement is implemented or verified and every assignment live demo remains unrun. The chronological story is in [project-journey.md](project-journey.md); individual rationale is in [decisions.md](decisions.md).

## Current documentation change

- Update only the existing Stage 2.2A records in progress and the journey: preserve the initial policy block, then record manual installation and successful runtime validation. Keep the preceding k3d commit reference.
- Preserve all requirement/demo statuses and architecture decisions. No application files, deployment files, or dependencies are added to the repository; this documentation update is not committed.

## Docker setup outcome

Initial rechecks found no Docker CLI, Desktop executable/install record, Docker process/service, or engine pipe. WinGet 1.29.380 identified Docker.DockerDesktop 4.94.0 from Docker Inc., hosted on desktop.docker.com. WSL 2.5.9 and its required Windows features were already present. The intended setup was WSL2 with Linux containers and Docker Desktop's built-in Kubernetes disabled and unused.

The initial plan used the official installer's supported per-user mode with `--backend=wsl-2` and `--no-windows-containers`, leaving agreement acceptance for first launch. WinGet's manifest specifies an all-users installation; the per-user path was chosen before execution to avoid unnecessary elevation. The tool rejected the combined download/verification/install command before execution with **"blocked by policy"**, giving no more specific reason. Nothing was downloaded or installed by that attempt, and its planned checksum/signature checks did not run. Codex did not attempt an alternate installation route after the rejection.

The user subsequently installed Docker Desktop manually, started it, and authorized resuming validation. The per-user installation reports Desktop 4.94.0 and Docker CLI/Engine 29.8.2. Codex's existing process had inherited the old PATH; the installer had already added Docker's CLI directory to the persistent user PATH. Validation commands refreshed only their process-local PATH, without changing persistent settings or the Docker context.

| Required check | Actual result |
| --- | --- |
| `docker --version` | Docker CLI 29.8.2, build 7fc2dff; command succeeds |
| `docker version` | Client 29.8.2 on windows/amd64 and Server Engine 29.8.2 on linux/amd64, Docker Desktop 4.94.0; exit 0 |
| `docker info` / engine reachability | Exit 0; Docker Desktop engine responds. Output review limited to non-sensitive runtime fields |
| Active Docker context | desktop-linux, using the local named pipe npipe:////./pipe/dockerDesktopLinuxEngine; context unchanged |
| `docker info --format '{{.OSType}}'` | linux; exit 0 |
| WSL2 backend | docker-desktop distribution Running with WSL version 2; engine kernel 6.6.87.2-microsoft-standard-WSL2 |
| Docker Desktop Kubernetes | `docker desktop kubernetes status` reports disabled and "Kubernetes is stopped"; not enabled or used |
| `docker run --rm hello-world` | Image initially absent; pulled from Docker Hub, printed "Hello from Docker!", exited 0 |
| Cleanup and image cache | Zero hello-world containers, including stopped containers; zero total containers afterward. linux/amd64 image remains cached with one filesystem layer and command /hello |
| Ready for k3d | Docker runtime prerequisite passed; k3d tooling/cluster setup and full-system resource sizing remain future work |

The single disposable container was the only container created in this validation. No k3d, kubectl, or Helm installation, Kubernetes activation/resources, project containers, Dockerfiles, or application directories were created by this step. Docker Desktop's disabled Kubernetes integration is not the selected project cluster; k3d remains the accepted future local cluster tool.

## Validation and review record

Stage 0's completed checks included exact transcription of 169 nonempty paragraphs, 119 list entries, and 29 heading depths; 40 local links/anchors; ignore rules; formatting; and complete governance diff review. Architecture v1's documentation checks passed on 2026-10-10: 56 local links across 9 Markdown files, consistent tracking IDs, unchanged assignment/source classifications, source checksum preservation, formatting, and complete diff review. These are historical checks, not evidence of working software.

Stage 2 preflight was read-only. Existing Git/Python/Node/npm and WSL were detected; the cluster toolchain was not. Approximately 24 logical CPUs and 110 GiB free disk supported initial planning, but only 2.6–2.8 GiB of 15.7 GiB RAM was available. Docker startup/container mode were untested at that point; Stage 2.2A now verifies them. Cluster operation, Ingress, and a full-system resource budget remain untested. Detailed engineering findings are in the journey.

The preceding k3d documentation checkpoint's checks passed on 2026-10-11 using inline Python and read-only Git commands. The table below records that historical checkpoint. No validation scripts or scaffolding were added.

| Check | Result |
| --- | --- |
| Links and tracking | All 58 local links/anchors resolve across 9 Markdown files; 44 requirements, 11 demos, 6 video groups, 10 optional items, 7 interpretation IDs, 17 decisions, 13 Architecture v1 IDs, and 4 threat topics remain consistent. The three new official technical reference pages were opened successfully |
| Scope and status fidelity | Only REQ-K8S-01's implementation plan changes in the tracking tables; source wording, mandatory/optional classifications, verification/demo fields, and all statuses remain unchanged |
| Source and checkpoint preservation | Original DOCX SHA-256 remains e9f7e797d72c331ab508d75135490644c99b9bf2c172f36225ad861926d02f92; protected files unchanged; both prior journey edits recording db49836 retained |
| Formatting | Markdown table widths, UTF-8 without BOM, LF endings, final newlines, trailing whitespace, and Git whitespace checks pass |
| Change boundary | Six existing Markdown files modified; no new files/directories or application/generated files. Added-text credential-pattern scan is clean; the complete diff is reviewed before staging |

Stage 2.2A documentation checks also passed: 58 local links across 9 Markdown files, table/encoding/whitespace checks, unchanged protected files and original DOCX checksum, and exactly two modified documentation files with no additions or staged changes. The full diff was reviewed; no credentials or application/generated files were introduced. No commit was created.

The runtime evidence for Stage 2.2A is the Docker validation table above, including the actual hello-world run and cleanup. It does not prove a working k3d/Ingress deployment or satisfy the assignment's application demos.

## Open and provisional work

- k3d is selected, and Docker Desktop's WSL2/Linux runtime is now verified. Installing k3d/kubectl/Helm, selecting compatible cluster versions, node count, memory allocation, and host ports need the next reviewed plan. Recheck available memory before cluster creation.
- Vite and k3s for the production-like VPS remain proposed baseline selections.
- SDK/protocol compatibility, exact pinned package versions, connection lifecycle, client refresh, timeouts, and health observation need an authorized prototype.
- Authentication algorithms/formats, session/invitation protections, runtime Secret management, schema details, audit persistence/denial/redaction/retention, and bootstrap need focused design/validation.
- LLM/provider, tool schemas and WooCommerce REST details, revenue-demo semantics, user A/B roles, and Claude Code versus Cursor need selection/validation. Inspector is selected for diagnostics.
- Chart dependencies, WordPress/MariaDB packaging, Ingress/DNS/TLS, storage, probes, and resources await the Kubernetes/store milestone. k3d alone does not establish stable URLs or prove VPS compatibility.

OPEN-01 through OPEN-07 in [architecture.md](architecture.md#unresolved-assignment-interpretations) have reviewed approaches under A13, with remaining validation noted. No optional feature is selected. NetworkPolicy is deferred, not a first-core prerequisite; the mandatory gateway-only requirement remains. Upgrade/rollback documentation and explanation are mandatory walkthrough material; executing live rollback is optional unless later evidence changes the interpretation.

## Review boundary

The user authorized resuming Docker validation after manual installation and one disposable hello-world run. Those checks passed with WSL2/Linux containers and Docker Desktop Kubernetes disabled. Show the results, explain the CLI-to-engine/image/container lifecycle, show the documentation diff and Git status, leave changes uncommitted, and stop for review. k3d/kubectl/Helm installation, cluster/resources, project containers, application files, and Dockerfiles remain outside this step. Follow [AGENTS.md](../AGENTS.md) for subsequent changes.

The assignment gives a two-week window but no actual start/due date. No submission deadline has been inferred or scheduled.

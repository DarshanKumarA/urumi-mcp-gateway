# Project progress

## Current milestone

**2026-10-11 — Stage 2.2B Kubernetes CLI toolchain installed and client validation passed.** Dates use the user's Asia/Calcutta calendar. Docker and the local CLI tools are available; no Kubernetes cluster has been created. This checkpoint awaits review.

Stage 0 governance was committed as **51f27b2 — docs: establish project governance and assignment baseline** on main. Architecture v1 and its journey were committed as **db49836 — docs: define architecture v1 and project journey**. The reviewed preflight/k3d documentation was committed as **1f2aec9 — docs: select k3d after environment preflight**. Stage 2.2A was reviewed, approved, and committed as **84395d5 — docs: record validated Docker runtime**. Stage 2.2B began with a clean working tree at that checkpoint.

A1–A13 remain accepted as DEC-004 through DEC-016. DEC-017 replaces the proposed local Minikube/Docker driver with k3d and Docker Desktop as the intended runtime. The assignment still permits Kind, k3d, or Minikube; its requirements have not changed.

No application, prototype, schema, dependency files, Kubernetes manifests, Helm chart, or deployment exists. Docker's disposable learning validation passed; no assignment runtime requirement is implemented or verified and every assignment live demo remains unrun. The chronological story is in [project-journey.md](project-journey.md); individual rationale is in [decisions.md](decisions.md).

## Current documentation change

- Record successful Stage 2.2B tool validation in progress and one journey entry, including the existing kubectl reuse, official download sources, installed versions, and absence of any cluster/context.
- Record the approved Stage 2.2A Git checkpoint while preserving its policy-block/manual-installation history.
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
| Ready for k3d | Docker runtime prerequisite passed in Stage 2.2A; tool installation is recorded below. Cluster setup and full-system resource sizing remain future work |

The single disposable container was the only container created in Stage 2.2A. That step did not install k3d/kubectl/Helm or create Kubernetes resources, project containers, Dockerfiles, or application directories. Docker Desktop's disabled Kubernetes integration is not the selected project cluster; k3d remains the accepted local cluster tool.

## Kubernetes CLI toolchain outcome

Stage 2.2B first checked availability. Refreshing only the command process's PATH from the existing Windows configuration exposed Docker Desktop's bundled kubectl v1.36.1. It already passed client validation, so no duplicate kubectl installation was needed. Kubernetes documents this bundled CLI and the separate Kubernetes.kubectl WinGet option in its [Windows installation guide](https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/).

Installed k3d.k3d 5.9.0 and Helm.Helm 4.3.0 sequentially through WinGet, with exact IDs/versions, the winget source, user scope, and prompts disabled. The manifests point directly to the [official k3d release](https://github.com/k3d-io/k3d/releases/tag/v5.9.0) and get.helm.sh respectively; WinGet verified each installer hash. These package-manager manifests are community-maintained, while the downloaded binaries come from the upstream projects. [Helm's installation guide](https://helm.sh/docs/intro/install/) documents its WinGet option. No policy block or user interaction occurred for these installations; WinGet added command aliases and PATH entries outside the repository.

| Tool | Role in our architecture | Installed version | Validation result |
| --- | --- | --- | --- |
| kubectl | Inspect/manage Kubernetes resources through the future cluster API | v1.36.1, already supplied by Docker Desktop | `kubectl version --client` exit 0; retained existing binary |
| k3d | Create/manage local K3s cluster nodes as Docker containers | v5.9.0 | `k3d version` exit 0; reports default K3s v1.35.5-k3s1, not a running cluster |
| Helm | Render charts and manage application releases using local/VPS values | v4.3.0 | `helm version` exit 0; no chart or release created |

`kubectl config get-contexts` and `k3d cluster list` both returned empty listings. No default kubeconfig exists and no KUBECONFIG override is set. The initial `kubectl config current-context` returned "current-context is not set" (exit 1), the expected unconfigured state rather than a tool-installation failure. No context was created or changed. Docker Desktop Kubernetes still reports disabled/stopped, and Docker has zero containers. No cluster, Kubernetes resources, application files/directories, Dockerfiles, or Helm charts were created.

K3s is the Kubernetes distribution; k3d manages its local Docker-based cluster lifecycle. kubectl works with individual resources and operational details such as pod status, logs, and events. Helm manages chart-based releases; it complements kubectl rather than replacing that operational interface. Installing these CLIs provides executables, not a control plane or deployed workloads. The cluster image/version and resource/Ingress design remain for the next review. kubectl must be within one minor version of the chosen Kubernetes server; its current v1.36 client is within that range of k3d's reported v1.35 default, but no live compatibility test or cluster-version selection has occurred.

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

The runtime evidence for Stage 2.2A is the Docker validation table above, including the actual hello-world run and cleanup; its documentation was subsequently committed as 84395d5. Stage 2.2B adds successful CLI version checks and empty cluster/context listings. Neither checkpoint proves a working k3d/Ingress deployment or satisfies the assignment's application demos.

Stage 2.2B documentation validation passed: 58 local links across 9 Markdown files, Markdown tables/encoding/whitespace, unchanged assignment and requirement/demo statuses, and the original DOCX checksum. Only progress and the journey changed, with one new Stage 2.2B entry and the preceding commit reference recorded; no repository files/directories were added and the index remains empty. Full diff review accompanies this checkpoint; no credentials or application/generated files were introduced.

## Open and provisional work

- Docker Desktop's WSL2/Linux runtime and kubectl/k3d/Helm clients are verified. Selecting compatible cluster versions, node count, memory allocation, and host ports needs the next reviewed plan. Recheck available memory before cluster creation; CLI validation does not establish workload capacity or cluster compatibility.
- Vite and k3s for the production-like VPS remain proposed baseline selections.
- SDK/protocol compatibility, exact pinned package versions, connection lifecycle, client refresh, timeouts, and health observation need an authorized prototype.
- Authentication algorithms/formats, session/invitation protections, runtime Secret management, schema details, audit persistence/denial/redaction/retention, and bootstrap need focused design/validation.
- LLM/provider, tool schemas and WooCommerce REST details, revenue-demo semantics, user A/B roles, and Claude Code versus Cursor need selection/validation. Inspector is selected for diagnostics.
- Chart dependencies, WordPress/MariaDB packaging, Ingress/DNS/TLS, storage, probes, and resources await the Kubernetes/store milestone. k3d alone does not establish stable URLs or prove VPS compatibility.

OPEN-01 through OPEN-07 in [architecture.md](architecture.md#unresolved-assignment-interpretations) have reviewed approaches under A13, with remaining validation noted. No optional feature is selected. NetworkPolicy is deferred, not a first-core prerequisite; the mandatory gateway-only requirement remains. Upgrade/rollback documentation and explanation are mandatory walkthrough material; executing live rollback is optional unless later evidence changes the interpretation.

## Review boundary

The user authorized Stage 2.2B CLI installation and validation only. Show tool versions, explain k3d/K3s/kubectl/Helm responsibilities, show Git status and the documentation diff, leave changes uncommitted, and stop for review. No cluster creation, Kubernetes resources, project containers, application code/directories, or Helm charts are authorized in this step. Follow [AGENTS.md](../AGENTS.md) for subsequent changes.

The assignment gives a two-week window but no actual start/due date. No submission deadline has been inferred or scheduled.

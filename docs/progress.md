# Project progress

## Current milestone

**2026-10-11 — Stage 2.4 Kubernetes fundamentals lab complete; Stage 2.4D cleanup and final validation succeeded.** Dates use the user's Asia/Calcutta calendar. The lab namespace and live resources are gone; urumi-local and its healthy system components remain running. The learning files remain in Git. This documentation checkpoint awaits review. No Urumi application workload has been deployed.

Stage 0 governance was committed as **51f27b2 — docs: establish project governance and assignment baseline** on main. Architecture v1 and its journey were committed as **db49836 — docs: define architecture v1 and project journey**. The reviewed preflight/k3d documentation was committed as **1f2aec9 — docs: select k3d after environment preflight**. Stage 2.2A was reviewed, approved, and committed as **84395d5 — docs: record validated Docker runtime**. Stage 2.2B was reviewed, approved, and committed as **248f13c — docs: record Kubernetes CLI toolchain**. Stage 2.3 was approved and committed as **78d3915 — docs: record validated local Kubernetes cluster**. The approved lab manifests were committed as **de2e69d — labs: add Kubernetes fundamentals workload** before Stage 2.4A began from a clean working tree.

A1–A13 remain accepted as DEC-004 through DEC-016. DEC-017 replaces the proposed local Minikube/Docker driver with k3d and Docker Desktop as the intended runtime. The assignment still permits Kind, k3d, or Minikube; its requirements have not changed.

Stage 2.4A's healthy workload observations were approved and committed as **fc1c38c — docs: record Kubernetes workload baseline**. Stage 2.4B was approved and committed as **89d9084 — docs: record Kubernetes self-healing experiment**. Stage 2.4C was approved and committed as **341d83a — docs: record Kubernetes declarative reconciliation experiment**. Stage 2.4D began from that clean documentation checkpoint.

No Urumi application, prototype, schema, dependency files, production application manifests, or project Helm chart exists. The cluster has returned to its default namespaces/system resources after lab cleanup. The fundamentals lab is complete, but no full assignment runtime requirement is marked implemented or verified; every assignment live demo remains unrun. The chronological story is in [project-journey.md](project-journey.md); individual rationale is in [decisions.md](decisions.md).

## Current documentation change

- Record Stage 2.4D namespace cleanup, resource absence, retained cluster health, external 404, and the completed lab's learning outcomes. Update the README's historical top-level status to its current state.
- Record the approved Stage 2.4C checkpoint while preserving earlier runtime history.
- Preserve all four approved YAML manifests, requirement/demo statuses, and architecture decisions. Only these three existing Markdown files change; this documentation update is not committed.

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
| Ready for k3d | Docker runtime prerequisite passed in Stage 2.2A; subsequent tool installation and cluster validation are recorded below. Full-system resource sizing remains future work |

The single disposable container was the only container created in Stage 2.2A. That step did not install k3d/kubectl/Helm or create Kubernetes resources, project containers, Dockerfiles, or application directories. Docker Desktop's disabled Kubernetes integration is not the selected project cluster; k3d remains the accepted local cluster tool.

## Kubernetes CLI toolchain outcome

Stage 2.2B first checked availability. Refreshing only the command process's PATH from the existing Windows configuration exposed Docker Desktop's bundled kubectl v1.36.1. It already passed client validation, so no duplicate kubectl installation was needed. Kubernetes documents this bundled CLI and the separate Kubernetes.kubectl WinGet option in its [Windows installation guide](https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/).

Installed k3d.k3d 5.9.0 and Helm.Helm 4.3.0 sequentially through WinGet, with exact IDs/versions, the winget source, user scope, and prompts disabled. The manifests point directly to the [official k3d release](https://github.com/k3d-io/k3d/releases/tag/v5.9.0) and get.helm.sh respectively; WinGet verified each installer hash. These package-manager manifests are community-maintained, while the downloaded binaries come from the upstream projects. [Helm's installation guide](https://helm.sh/docs/intro/install/) documents its WinGet option. No policy block or user interaction occurred for these installations; WinGet added command aliases and PATH entries outside the repository.

| Tool | Role in our architecture | Installed version | Validation result |
| --- | --- | --- | --- |
| kubectl | Inspect/manage Kubernetes resources through the future cluster API | v1.36.1, already supplied by Docker Desktop | `kubectl version --client` exit 0; retained existing binary |
| k3d | Create/manage local K3s cluster nodes as Docker containers | v5.9.0 | `k3d version` exit 0; reports default K3s v1.35.5-k3s1, not a running cluster |
| Helm | Render charts and manage application releases using local/VPS values | v4.3.0 | `helm version` exit 0; no chart or release created |

At the Stage 2.2B checkpoint, `kubectl config get-contexts` and `k3d cluster list` both returned empty listings. No default kubeconfig existed and no KUBECONFIG override was set. The initial `kubectl config current-context` returned "current-context is not set" (exit 1), the expected unconfigured state rather than a tool-installation failure. No context was created or changed. Docker Desktop Kubernetes reported disabled/stopped, and Docker had zero containers. No cluster, Kubernetes resources, application files/directories, Dockerfiles, or Helm charts were created in that step.

K3s is the Kubernetes distribution; k3d manages its local Docker-based cluster lifecycle. kubectl works with individual resources and operational details such as pod status, logs, and events. Helm manages chart-based releases; it complements kubectl rather than replacing that operational interface. Installing these CLIs provides executables, not a control plane or deployed workloads. At Stage 2.2B, cluster version and resource/Ingress design remained for review. kubectl must be within one minor version of the chosen Kubernetes server; the v1.36 client is within that range of k3d's v1.35 default. Stage 2.3 below records the first live cluster validation.

## First local Kubernetes cluster outcome

Prechecks reconfirmed Docker Engine 29.8.2 reachable in Linux mode, no k3d clusters or kubectl contexts, and Docker Desktop Kubernetes disabled/stopped. TCP ports 6550, 8080, and 8443 had no existing bindings or Windows exclusions; temporary bind-and-release checks succeeded. Windows had approximately 2.79 GiB available of 15.73 GiB RAM immediately before creation. The Docker WSL environment separately reported about 6.93 GiB available within its virtual memory capacity; these figures are not additive. Headroom was judged sufficient for this infrastructure-only step against the [K3s server baseline](https://docs.k3s.io/installation/requirements) of 2 GB RAM, excluding application workloads.

The user selected one server, no additional agents, the three host ports, and retained K3s defaults. Installed k3d v5.9.0 supported the following command without a syntax substitution. The API uses loopback; HTTP/HTTPS mappings use Docker's default host interfaces.

```powershell
k3d cluster create urumi-local --servers 1 --agents 0 --api-port 127.0.0.1:6550 --port "8080:80@loadbalancer" --port "8443:443@loadbalancer" --wait --timeout 5m
```

Creation completed successfully in about 54 seconds, using k3d's default rancher/k3s:v1.35.5-k3s1 image. k3d created infrastructure containers, the k3d-urumi-local Docker network and image volume, and the personal kubeconfig outside the repository. It selected the new context; kubeconfig credentials were not printed or copied into documentation.

| Check / component | Observed result |
| --- | --- |
| Cluster and context | urumi-local: servers 1/1, agents 0/0, load balancer enabled; only context is k3d-urumi-local, selected |
| API | https://127.0.0.1:6550 responds; `/readyz` returns ok |
| Node and runtime | k3d-urumi-local-server-0, Ready, control-plane role, Kubernetes/K3s v1.35.5+k3s1; containerd 2.2.3-k3s1; no memory/disk pressure or scheduling taints observed |
| Namespaces | default, kube-system, kube-public, kube-node-lease; all Active; no project namespace |
| CoreDNS | Deployment available, Pod 1/1 Running; kube-dns ClusterIP Service present |
| Traefik | Deployment available, Pod 1/1 Running; ServiceLB DaemonSet ready 1/1 with a 2/2 Running Pod; LoadBalancer Service exposes 80/443 |
| Metrics-server | Deployment available, Pod 1/1 Running; metrics API works through `kubectl top nodes` |
| Storage | local-path is the default StorageClass, provisioner rancher.io/local-path, Delete reclaim policy, WaitForFirstConsumer binding; provisioner Pod 1/1 Running. No PVC or persistence test created |
| Infrastructure containers | k3d-urumi-local-server-0 (K3s), k3d-urumi-local-serverlb (k3d-proxy 5.9.0), and k3d-urumi-local-tools (k3d-tools 5.9.0) all running; tools helper is not a Kubernetes node |
| Host mappings | serverlb publishes 127.0.0.1:6550 to 6443, host 8080 to 80, and host 8443 to 443; HTTP/HTTPS bindings appear on IPv4/IPv6 wildcard interfaces |
| HTTP observation | http://127.0.0.1:8080/ returns expected Traefik 404 with no application Ingress route; HTTPS certificates/routing were not validated |
| Desktop Kubernetes | Still disabled/stopped; this cluster is managed by k3d |

Validation ran the requested cluster, Docker container, context, cluster-info, node, namespace, Pod, Service, and StorageClass listings. It additionally waited for node Ready, all four system Deployments Available, and both Traefik bootstrap Jobs Complete; inspected the ServiceLB DaemonSet and API readiness; and retrieved node metrics. Early Flannel subnet initialization warnings and a metrics-server image download EOF cleared through automatic retries without configuration changes. The Traefik installation Job completed after one container restart; its CRD Job also completed. Completed bootstrap Pods correctly show 0/1 Ready because their work has ended; all continuing system Pods were ready with zero restarts at the final check.

Windows available RAM was about 1.28 GiB after startup. The node metrics snapshot showed about 727 MiB memory usage and no memory pressure was observed, but this is not total Windows/Docker overhead or an application capacity budget. Reassess host memory before expanding the environment. No project workload, nginx learning workload, application directory, Dockerfile, Helm chart, or additional CNI/NetworkPolicy tooling was created. k3d's nginx-based infrastructure proxy and K3s's automatic Traefik Helm Jobs are cluster internals, not project scaffolding. Stable application URLs, real persistent-volume behavior, TLS, and VPS compatibility remain unverified.

## Stage 2.4A learning workload outcome

Prechecks passed with current/target context k3d-urumi-local, a Ready node, healthy system components, no lab namespace/Ingress conflict, approximately 3.14 GiB available host RAM, and the pinned nginx tag active for Linux/amd64. A fresh external request confirmed the pre-apply Traefik 404. Namespace apply, server dry-run of the remaining manifests, apply, and rollout succeeded. An initial registry-download EOF recovered through Kubernetes image-pull retries without changing the manifests.

The Deployment has one desired/current/ready replica; inspected owner references connect it to its generated ReplicaSet and Ready Pod. Matching app=nginx-lab selectors connect the Service to that Pod, and its EndpointSlice records one ready backend. The approved in-cluster DNS/Service request returned nginx HTML; Windows localhost:8080 returned HTTP 200 with Server: nginx/1.30.5 and the welcome page through the existing Traefik route. Live resource requests/limits and both probes match the manifest; nginx logs show successful probe requests and the Pod has zero restarts. Detailed identities, addresses, ownership, and evidence are in the [lab's actual observations](../labs/kubernetes-basics/README.md#actual-observations).

The one-replica lab remains running. No Pod deletion, scaling, drift/reconciliation experiment, probe failure injection, cleanup, or HTTPS test was performed. Healthy operation is observed; application capacity and failure handling remain unverified. No Urumi application or Helm resources were created, and this step does not complete an assignment requirement.

## Stage 2.4B controller reconciliation outcome

The baseline was healthy: Deployment and ReplicaSet desired/current/ready 1/1/1, one Ready Pod, one ready Service backend, and external HTTP 200. After capturing identities and starting Pod/EndpointSlice watches, deleted only the captured nginx Pod. The same ReplicaSet created a replacement, which was scheduled on the same node, started from the cached image, and became Ready with zero restarts. The Pod UID changed and its IP changed from 10.42.0.9 to 10.42.0.10; Deployment/ReplicaSet UIDs, desired count, Service identity/ClusterIP, and Ingress identity/spec remained unchanged.

Watches observed termination, replacement Pending/ContainerCreating/Running/Ready states, and the EndpointSlice moving from the old terminating backend through an empty endpoint list to the new ready backend. Events confirmed creation, scheduling, cached image availability, and container startup. Both in-cluster Service DNS access and localhost:8080 returned HTTP 200 afterward. Final Deployment/ReplicaSet counts are 1/1/1. The [lab's actual observations](../labs/kubernetes-basics/README.md#actual-observations) preserve the identity comparison and observed sequence.

The empty-backend interval demonstrates why self-healing is not zero downtime. HTTP was not continuously sampled, so no outage duration or intermediate HTTP status is claimed. No manifests, replica counts, Service/Ingress configuration, or other workloads were changed. The replacement remains running; scaling, manifest/live-state drift, cleanup, and deliberate probe failures await later authorization.

## Stage 2.4C scaling and declarative reconciliation outcome

Verified the one-replica baseline, one Ready Pod/backend, correct context, external HTTP 200, and committed replicas: 1 before changing live state. Imperative scale to 2 produced Deployment and the same ReplicaSet at 2/2/2. Existing Pod bj9sz (10.42.0.10) and added Pod n5jjc (10.42.0.11) were Ready with zero restarts on the same node; the Service had two ready backend addresses. Service ClusterIP 10.43.133.91 and Service/Ingress identities/specs stayed unchanged; external HTTP returned 200.

kubectl diff exited 1 and showed live replicas: 2 versus the file's replicas: 1, plus the predicted server-managed generation increment. Re-applying the byte-identical committed Deployment file restored live desired replicas to 1. A watch showed n5jjc terminating/completing, and the ReplicaSet recorded SuccessfulDelete. A readiness connection-refused warning coincided with that Pod's shutdown; the retained bj9sz Pod remained Ready with zero restarts. Final Deployment/ReplicaSet counts were 1/1/1 with only 10.42.0.10 as a ready backend, external HTTP 200, and an empty kubectl diff (exit 0). Detailed identities and evidence are in the lab's actual observations.

Kubernetes follows the live API object's desired state, not the Git file automatically. Re-applying YAML restored our committed intent. Two Pods on one node offer Pod-level redundancy but no node-failure protection; no availability guarantee or distribution test is claimed. Helm's future values/templates will render manifests expressing intent, and manual live changes can similarly diverge. No Helm files or releases were created, no YAML/Service/Ingress was changed, and no cleanup or extra workload was performed. The one-replica lab remains running; this checkpoint is uncommitted for review.

## Stage 2.4D cleanup and final validation outcome

The pre-cleanup baseline passed: correct current/target context, Ready node, Active lab namespace, Deployment/ReplicaSet 1/1/1, one Ready Pod/backend, existing Ingress, and external HTTP 200. Captured all six relevant namespaced resource types and their ownership. Deleted only namespace kubernetes-basics with an explicit context and bounded wait; a watch observed Active then Terminating. Deletion completed successfully without forced cleanup or child-resource deletion commands.

Subsequent listings confirmed namespace absence and no lab Deployment, ReplicaSet, Pod, Service, EndpointSlice, or Ingress across the cluster. urumi-local remains listed with servers 1/1 and its load balancer enabled. The node is Ready; Traefik, CoreDNS, metrics-server, and local-path-provisioner Deployments are each desired/ready/available 1/1/1 with Ready running Pods. The Traefik ServiceLB Pod is 2/2, and the cluster-scoped IngressClass remains. With no Ingress objects left, localhost:8080 returned HTTP 404 and `404 page not found`, matching the original no-route state.

The fundamentals lab is complete: controller ownership, labels/selectors, Service/EndpointSlice discovery, internal/external routing, probes/resources, Pod replacement, scaling, declarative drift restoration, and namespace lifecycle have been observed. Namespace grouping enabled cleanup but does not itself enforce network isolation. Live objects are gone while all learning manifests remain available for an authorized repeat. No application requirement/demo status changes, Helm chart, new workload, or application deployment are implied. Detailed cleanup evidence is in the lab README; prior outcome sections retain their historical checkpoint state.

## Validation and review record

Stage 0's completed checks included exact transcription of 169 nonempty paragraphs, 119 list entries, and 29 heading depths; 40 local links/anchors; ignore rules; formatting; and complete governance diff review. Architecture v1's documentation checks passed on 2026-10-10: 56 local links across 9 Markdown files, consistent tracking IDs, unchanged assignment/source classifications, source checksum preservation, formatting, and complete diff review. These are historical checks, not evidence of working software.

Stage 2 preflight was read-only. Existing Git/Python/Node/npm and WSL were detected; the cluster toolchain was not. Approximately 24 logical CPUs and 110 GiB free disk supported initial planning, but only 2.6–2.8 GiB of 15.7 GiB RAM was available. Docker startup/container mode were untested at that point; Stage 2.2A verified them. Stage 2.3 now verifies the empty cluster and HTTP forwarding to Traefik; application Ingress and a full-system resource budget remain untested. Detailed engineering findings are in the journey.

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

Stage 2.2B documentation validation passed: 58 local links across 9 Markdown files, Markdown tables/encoding/whitespace, unchanged assignment and requirement/demo statuses, and the original DOCX checksum. Only progress and the journey changed, with one new Stage 2.2B entry and the preceding commit reference recorded; no repository files/directories were added. The full diff was reviewed, and the user subsequently approved commit 248f13c. No credentials or application/generated files were introduced.

Stage 2.3 documentation checks passed for all 58 local links/anchors across 9 Markdown files, table widths, UTF-8/LF/final-newline/whitespace, and the original DOCX checksum. Only progress and the journey changed; the index is empty and no untracked files were introduced. Assignment, requirement/demo statuses, and other tracked files are unchanged. Added-text credential-pattern checks passed; the complete diff is shown for review. No commit is created in this step.

## Open and provisional work

- Docker Desktop's WSL2/Linux runtime, local CLIs, and the single-server K3s v1.35.5+k3s1 cluster are verified. API port 6550 and Ingress mappings 8080/8443 are established. No explicit node memory cap was selected; available host RAM is tight and full-stack workload capacity remains unproven.
- Vite and k3s for the production-like VPS remain proposed baseline selections.
- SDK/protocol compatibility, exact pinned package versions, connection lifecycle, client refresh, timeouts, and health observation need an authorized prototype.
- Authentication algorithms/formats, session/invitation protections, runtime Secret management, schema details, audit persistence/denial/redaction/retention, and bootstrap need focused design/validation.
- LLM/provider, tool schemas and WooCommerce REST details, revenue-demo semantics, user A/B roles, and Claude Code versus Cursor need selection/validation. Inspector is selected for diagnostics.
- Chart dependencies, WordPress/MariaDB packaging, application Ingress/DNS/TLS, PVCs, probes, and resource sizing await later review. Default Traefik and local-path are healthy infrastructure, not proof of application URLs, persistence, or VPS compatibility.

OPEN-01 through OPEN-07 in [architecture.md](architecture.md#unresolved-assignment-interpretations) have reviewed approaches under A13, with remaining validation noted. No optional feature is selected. NetworkPolicy is deferred, not a first-core prerequisite; the mandatory gateway-only requirement remains. Upgrade/rollback documentation and explanation are mandatory walkthrough material; executing live rollback is optional unless later evidence changes the interpretation.

## Review boundary

The user authorized Stage 2.4D deletion of only the lab namespace, final infrastructure/HTTP validation, and updates to the lab README, progress, and journey. Show cleanup evidence, final health, the three-file documentation diff, and Git status; leave urumi-local running and changes uncommitted, then stop for review. Do not recreate the lab, delete the cluster, alter the four YAML manifests, remove repository lab files, or create application components/other workloads. Earlier observation sections remain historical. Follow [AGENTS.md](../AGENTS.md) for subsequent changes.

The assignment gives a two-week window but no actual start/due date. No submission deadline has been inferred or scheduled.

# Project progress

## Current milestone

**2026-10-12 — Stage 3.2 initial store Helm templates created and statically validated; bootstrap and deployment remain pending.** Dates use the user's Asia/Calcutta calendar. Store Architecture v1 and its RAM correction are approved; their existing uncommitted documentation is preserved. Stage 2.4 cleanup was committed as **7462029 — docs: complete Kubernetes fundamentals lab**. The lab resources were removed and urumi-local was left running; this step does not recheck or change the cluster. No Urumi application workload has been deployed.

Stage 0 governance was committed as **51f27b2 — docs: establish project governance and assignment baseline** on main. Architecture v1 and its journey were committed as **db49836 — docs: define architecture v1 and project journey**. The reviewed preflight/k3d documentation was committed as **1f2aec9 — docs: select k3d after environment preflight**. Stage 2.2A was reviewed, approved, and committed as **84395d5 — docs: record validated Docker runtime**. Stage 2.2B was reviewed, approved, and committed as **248f13c — docs: record Kubernetes CLI toolchain**. Stage 2.3 was approved and committed as **78d3915 — docs: record validated local Kubernetes cluster**. The approved lab manifests were committed as **de2e69d — labs: add Kubernetes fundamentals workload** before Stage 2.4A began from a clean working tree.

A1–A13 remain accepted as DEC-004 through DEC-016. DEC-017 replaces the proposed local Minikube/Docker driver with k3d and Docker Desktop as the intended runtime. The assignment still permits Kind, k3d, or Minikube; its requirements have not changed.

Stage 2.4A's healthy workload observations were approved and committed as **fc1c38c — docs: record Kubernetes workload baseline**. Stage 2.4B was approved and committed as **89d9084 — docs: record Kubernetes self-healing experiment**. Stage 2.4C was approved and committed as **341d83a — docs: record Kubernetes declarative reconciliation experiment**. Stage 2.4D began from that clean documentation checkpoint.

An initial project Helm chart now exists, but no Urumi application source, prototype, schema, bootstrap Job/scripts or release exists. The cluster was left at its default namespaces/system resources after lab cleanup. The fundamentals lab is complete, but no full assignment runtime requirement is marked implemented or verified; every assignment live demo remains unrun. The chronological story is in [project-journey.md](project-journey.md); individual rationale is in [decisions.md](decisions.md).

## Current documentation change

- Preserve the preceding uncommitted Store Architecture v1/DEC-018–DEC-021 documentation and Stage 2.4D commit reference.
- Add exactly eleven initial chart files; update architecture, progress, journey and relevant requirement plans/statuses to distinguish partial static templates from working runtime behavior. The decision register needs no further change in this step.
- No bootstrap files, Secret objects/values, generated manifests in Git or runtime changes; no staging or commit is authorized.

## Stage 3 store design outcome

Store Architecture v1 is accepted, not implemented. One urumi namespace and one application chart/release will use our own minimal templates and standard images. WordPress is a one-replica Recreate Deployment with a 2 GiB full-webroot PVC at /var/www/html; MariaDB is a one-replica StatefulSet with a separate 5 GiB data PVC at /var/lib/mysql. The store uses ClusterIP/Traefik and store.urumi.test:8080; MariaDB remains internal. External Secrets, a finite idempotent WP-CLI Job, COD checkout, independent liveness/dependency-aware readiness, exact version pins, PVC retention and measured resource budgets are accepted. Exact contracts and digests live in [architecture](architecture.md#accepted-store-architecture-v1).

The design-stage source/registry checks support the selected WordPress 7.1.3/PHP 8.3, WP-CLI 2.12.0, MariaDB 11.4.13 and WooCommerce 11.2.1 set; no image execution, installation, bootstrap, persistence or checkout test has occurred. WordPress core/plugin files persist independently of image changes. One database replica is not HA; retained volumes are not backups or node-loss protection; rollback does not rewind data/files. Namespace deletion is destructive and must not follow the disposable lab's cleanup pattern.

**Memory: PASS for initial Stage 3 deployment attempt; full-stack capacity still unproven.** User-reported accepted figures on 2026-10-12: approximately 15.7 GiB total, 11.6 GiB used and 4.1 GiB available Windows RAM. This narrowly passes the approximately 4 GiB gate and supersedes the stale ~1 GiB blocking conclusion. No fresh measurement was taken for this documentation change.

| Workload | CPU request / limit | Memory request / limit |
| --- | --- | --- |
| WordPress | 250m / 1000m | 512Mi / 1Gi |
| MariaDB | 100m / 500m | 256Mi / 512Mi |
| Bootstrap Job | 100m / 500m | 128Mi / 512Mi |

Keep these starting budgets unchanged. Recheck host memory and Docker/WSL/node capacity immediately before first Helm install. Measure host/node/workload memory during MariaDB startup, WordPress startup, Job execution, normal storefront/admin use and checkout. Stop and tune on OOM kills, unexplained restarts, severe host pressure or insufficient scheduling capacity before adding further Urumi components. A passing gate permits cautious planning for an initial attempt; this step still authorizes documentation only.

Documentation validation: 68 local links/anchors across 10 Markdown files resolve; changed tables, UTF-8/LF, final newlines and Git whitespace checks pass. All requirement/demo matrix rows, the original DOCX checksum, lab manifests and other tracked files are unchanged. Only the five authorized existing Markdown files differ; no staged/untracked files or credential-pattern matches were found. These checks provide no new runtime evidence.

## Stage 3.2 initial Helm chart static validation

Created Chart.yaml, three values files, _helpers.tpl and six resource templates under charts/urumi. No chart dependency, sidecar, custom image, ConfigMap, Namespace, Secret, bootstrap Job or bootstrap script was added. Each environment renders the same six objects in namespace urumi: PersistentVolumeClaim urumi-wordpress; Services urumi-wordpress and urumi-mariadb; Deployment urumi-wordpress; StatefulSet urumi-mariadb; Ingress urumi-wordpress. The future database claim is data-urumi-mariadb-0, generated by the StatefulSet controller rather than Helm rendering.

Shared defaults pin the two approved Linux/amd64 image references, 2 GiB/5 GiB storage, the unchanged CPU/memory budgets and external Secret names. Local values set local-path and store.urumi.test; canonicalUrl is http://store.urumi.test:8080 and remains a value for later bootstrap. Production values use the reserved store.example.invalid hostname, HTTPS, a replace-with-production-tls-secret reference and replace-with-production-storage-class placeholders. They demonstrate configuration structure and are not ready for deployment. Namespace comes from --namespace; the chart does not own/create it.

WordPress uses Recreate with one replica, full-webroot persistence, Secret-file references, startup/liveness TCP checks and an explicitly interim TCP readiness probe. **Replace readiness with the accepted dependency-aware check before installation.** MariaDB uses one replica, a headless internal Service, retained StatefulSet claims, Secret-file references and official healthcheck.sh connection/InnoDB probes. No readiness check or storage behavior was executed.

| Static check | Result and limit |
| --- | --- |
| YAML parsing | Chart/values and all rendered documents parse; duplicate keys rejected. Helm templates are parsed after rendering, not as raw YAML |
| Helm lint | Helm 4.3.0 strict lint passes for shared/local/production values; only informational icon recommendation |
| Helm template | Local and production each render six resources with --namespace urumi --kube-version 1.35.5; no server access |
| Kubernetes schema | Passed against official Kubernetes v1.35.5 OpenAPI definitions, matching the last validated cluster version. Local JSON Schema validation adapts Kubernetes IntOrString format and rejects unknown structured fields; it is not API admission validation |
| Resource relationships | Checked names/namespace, stable selectors versus Pod labels, named Service target ports, Ingress backend, storage mounts/sizes/classes, exact image pins, resource budgets and probes |
| Credential/exposure checks | All sensitive env settings reference projected Secret files, root credentials are DB-only, auth keys are WordPress-only; no Secret objects, plaintext credential env values, public DB Service/Ingress, hostPort or hostNetwork |
| Configuration branches | Alternate release/namespace and DB port render consistently; existingClaim removes the WordPress PVC and reuses the supplied name; enabling TLS without a Secret name correctly fails rendering |

Representative commands (already executed as local/static checks; rendered YAML was held in memory):

```powershell
helm lint charts/urumi --strict --kube-version 1.35.5 -f charts/urumi/values-local.yaml
helm lint charts/urumi --strict --kube-version 1.35.5 -f charts/urumi/values-prod.yaml
helm template urumi charts/urumi --namespace urumi --kube-version 1.35.5 -f charts/urumi/values-local.yaml
helm template urumi charts/urumi --namespace urumi --kube-version 1.35.5 -f charts/urumi/values-prod.yaml
```

The schema source is the [official versioned Kubernetes OpenAPI file](https://github.com/kubernetes/kubernetes/blob/v1.35.5/api/openapi-spec/swagger.json). The [pinned WordPress configuration source](https://github.com/docker-library/wordpress/blob/5ec12a3ef21493a12f3d211e0d69d0c6a30a9794/wp-config-docker.php) and [MariaDB healthcheck source](https://github.com/MariaDB/mariadb-docker/blob/bdfe641466a5312bb97d06a1a4e1fb411c49e6b6/11.4/healthcheck.sh) support the selected file references/probe commands, not runtime success.

Before deployment: implement/review bootstrap and final readiness; prepare the namespace and external Secrets through a separately authorized step; configure the local hosts mapping or real production DNS/TLS/storage; recheck image availability and host/node memory. No memory measurement was taken here; the accepted user-reported ~4.1 GiB gate passes only for an initial attempt, not full-stack capacity. No helm install/upgrade, Kubernetes apply/server dry-run, cluster inspection, image execution or hosts-file edit occurred.

Repository validation passed for all 70 local links/anchors, Markdown tables, UTF-8/LF and whitespace. Exactly eleven requested chart files are new; the index is empty, and no generated render/schema files were saved. Credential-pattern checks of tracked files (including source DOCX text) and new/rendered chart content found no credential values. Nine requirement rows record partial template progress only; obligation text, IDs, source/classification, verification/demo fields and every demo row remain unchanged. Source DOCX checksum and lab files are preserved. The pre-existing decision-register edit is unchanged by Stage 3.2.

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

- Docker Desktop's WSL2/Linux runtime, local CLIs, and the single-server K3s v1.35.5+k3s1 cluster passed Stage 2 validation. API port 6550 and Ingress mappings 8080/8443 are established. No explicit node memory cap was selected. The corrected host RAM gate passes narrowly for initial Stage 3 deployment; recheck before installation and measure runtime usage, as full-stack capacity remains unproven.
- Vite and k3s for the production-like VPS remain proposed baseline selections.
- SDK/protocol compatibility, exact pinned package versions, connection lifecycle, client refresh, timeouts, and health observation need an authorized prototype.
- Authentication algorithms/formats, session/invitation protections, runtime Secret management, schema details, audit persistence/denial/redaction/retention, and bootstrap need focused design/validation.
- LLM/provider, tool schemas and WooCommerce REST details, revenue-demo semantics, user A/B roles, and Claude Code versus Cursor need selection/validation. Inspector is selected for diagnostics.
- Store packaging, local route, PVCs, Secret contract, bootstrap, probes and starting resources are accepted in DEC-018–DEC-021. Their implementation and runtime validation remain pending; initial store settings, production TLS provisioning and non-store deployment details remain open. Existing infrastructure is not proof of store URLs, persistence, checkout or VPS compatibility.

OPEN-01 through OPEN-07 in [architecture.md](architecture.md#unresolved-assignment-interpretations) have reviewed approaches under A13, with remaining validation noted. No optional feature is selected. NetworkPolicy is deferred, not a first-core prerequisite; the mandatory gateway-only requirement remains. Upgrade/rollback documentation and explanation are mandatory walkthrough material; executing live rollback is optional unless later evidence changes the interpretation.

## Review boundary

The user authorized only Stage 3.2 chart file creation and static validation. Show the chart tree, complete new-file/documentation diffs, local/production inventories, resource explanations, deployment prerequisites and Git status, then stop for review. Do not create bootstrap files, Secrets or workloads, install/upgrade the release, apply resources, edit hosts, stage or commit. Leave the cluster and lab files unchanged. Earlier observation sections remain historical. Follow [AGENTS.md](../AGENTS.md) for subsequent changes.

The assignment gives a two-week window but no actual start/due date. No submission deadline has been inferred or scheduled.

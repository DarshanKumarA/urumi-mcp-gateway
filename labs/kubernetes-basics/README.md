# Kubernetes basics: disposable nginx lab

Status: manifests created for review; **not applied and no lab runtime observations collected**. Every result described below is an expectation to check later, not evidence of success.

These are learning artifacts, not production Urumi manifests. They exercise Kubernetes fundamentals in an isolated resource namespace before application work. They do not replace the assignment's Helm deployment, prove application requirements, or authorize deployment. No WordPress/WooCommerce, storage, application source, or Helm chart is included.

## Files and object fields

All manifests have `apiVersion` (API group/version and schema), `kind` (object type), and `metadata` (identity and labels). `spec` declares desired configuration where needed; controllers later report observed state in `status`, which we do not author. The Namespace needs only metadata here, not an explicit spec.

| File | Object and meaningful configuration |
| --- | --- |
| [namespace.yaml](namespace.yaml) | `v1/Namespace`; `metadata.name: kubernetes-basics`. The `purpose: learning` label identifies its purpose without selecting Pods. The Namespace itself is cluster-scoped; the other objects set `metadata.namespace` to this name |
| [deployment.yaml](deployment.yaml) | `apps/v1/Deployment` named `nginx-lab`; `replicas: 1` declares the desired Pod count. `selector.matchLabels` identifies managed Pods and must match `template.metadata.labels`. `template.spec` describes the Pods to create; the selector is immutable after creation |
| [service.yaml](service.yaml) | `v1/Service` named `nginx-lab`; `type: ClusterIP` provides stable cluster-internal addressing. Its selector matches Pods with `app: nginx-lab` in this namespace. Service `port: 80` forwards to `targetPort: http`, the named port in those Pods |
| [ingress.yaml](ingress.yaml) | `networking.k8s.io/v1/Ingress` named `nginx-lab`; `ingressClassName: traefik` selects the existing controller. A hostless rule with `/` and `pathType: Prefix` references Service `nginx-lab`, port 80. No hosts-file modification, path rewrite, TLS setup, or new controller is needed |

The namespace groups resources and provides a cleanup boundary; it does not automatically enforce network isolation. All four objects are disposable. The five repository files remain as a learning reference after cleanup, separate from future production charts. A standalone ReplicaSet, Pod, or EndpointSlice manifest is unnecessary because controllers create them.

The container is named `nginx` and uses official `docker.io/library/nginx:1.30.5-alpine`, not `latest`. Its tag and Linux/amd64 availability were checked during planning; recheck before running the lab. A version tag is explicit but is not an immutable digest. Named container port `http` documents port 80 and lets the Service/probes refer to it by name; `containerPort` does not publish a Windows host port. There is no custom command or environment configuration.

| Container setting | Meaning and approved value |
| --- | --- |
| CPU request / limit | `50m` / `250m`: 0.05 / 0.25 CPU. Requests inform scheduling; the limit constrains CPU usage through throttling |
| Memory request / limit | `32Mi` / `128Mi`: scheduling request and container memory limit. Exceeding the memory limit can cause an OOM kill; these are initial lab budgets, not measured application sizing |
| Readiness | HTTP GET `/` on port `http`; start after 2 seconds, repeat every 5 seconds. An unready Pod is excluded from normal ready Service backends; failure alone does not restart the container |
| Liveness | HTTP GET `/` on port `http`; start after 10 seconds, repeat every 10 seconds. Repeated failure causes the kubelet to restart the container within the Pod |
| Both probes | Timeout 2 seconds, failure threshold 3 consecutive failures. These target the Pod directly, not the Ingress or Service |

## Relationships to observe

```text
Deployment -> ReplicaSet -> Pod -> nginx container
```

The Deployment manages ReplicaSets and rollout intent. Its active ReplicaSet maintains the desired number of Pods. Pod deletion does not delete that desired state: a replacement is created. A replacement Pod has a new identity; a liveness-triggered container restart normally retains the Pod identity. Scaling changes desired count without changing the Pod template, so this exercise should retain the same ReplicaSet.

Labels are key/value metadata; selectors are matching rules. Both the Deployment selector and Service selector use `app: nginx-lab`, matching the Pod template. The Service does not select a Deployment by name. Labels on Deployment metadata alone would not label its Pods. Kubernetes also adds a `pod-template-hash` label; the Service deliberately does not select that revision-specific value.

```text
Browser -> k3d load balancer -> Traefik -> Ingress rule -> Service/backend Pods
localhost:8080              existing      / Prefix      nginx-lab:80 -> Pod:80
```

This is a logical routing diagram. An Ingress is configuration interpreted by Traefik, not a separate proxy process or network hop. Traefik can route directly to backend Pod addresses discovered through the Service/EndpointSlices rather than traversing the ClusterIP. The namespace's nginx is the web server, not another Ingress controller.

The Service supplies stable DNS/ClusterIP addressing while Pods come and go. EndpointSlices record backend addresses, ports, target Pods, and readiness; Kubernetes updates them from selector matches. We inspect EndpointSlices rather than depend on the deprecated legacy Endpoints API. Do not pin clients to a Pod IP: replacement may change it, and an old address may be reused. ClusterIP means internal addressing, not authentication or isolation from other cluster workloads.

The hostless `/` rule matches broadly and is only for this disposable lab. HTTP uses the existing host 8080 mapping; port 8443 and HTTPS are outside this exercise. The empty cluster returned Traefik's no-route 404 in Stage 2.3; this lab should later replace that with nginx's welcome page, then restore the 404 after cleanup.

## Future execution and observation sequence

Do not run this section until manifest review and execution are authorized. Use PowerShell from the repository root. Execute one step at a time, inspect each result, and stop to investigate unexpected output or timeouts instead of continuing blindly. Do not paste the entire walkthrough as a script.

Before applying: confirm `urumi-local` is running, its node/system components are healthy, memory headroom is adequate, the learning namespace is absent, and no competing Ingress route exists. Recheck the image tag's availability. Do not modify cluster configuration to make the lab pass. `kubectl diff` also requires an external diff executable on Windows. Inspection found Git's existing `diff.exe` at the path below but not on the current PATH; the future setup makes it available only in this terminal, without installing software or changing persistent Windows settings.

```powershell
$labPath = Join-Path (Get-Location) 'labs/kubernetes-basics'
$labArgs = @('--context', 'k3d-urumi-local', '--namespace', 'kubernetes-basics')
if (-not (Get-Command diff.exe -ErrorAction SilentlyContinue)) {
    $gitDiffDirectory = 'C:\Program Files\Git\usr\bin'
    if (-not (Test-Path (Join-Path $gitDiffDirectory 'diff.exe'))) {
        throw 'Git diff.exe is unavailable; review the tooling prerequisite before proceeding'
    }
    $env:Path = "$gitDiffDirectory;$env:Path"
}
```

The splatted `$labArgs` explicitly targets the lab namespace and cluster without changing the global current context. `$labPath` must resolve to this directory. Namespace creation/deletion uses an explicit cluster context because Namespaces are cluster-scoped.

### 1. Apply in dependency order

```powershell
kubectl --context k3d-urumi-local apply -f "$labPath/namespace.yaml"
kubectl @labArgs apply --dry-run=server -f "$labPath/deployment.yaml" -f "$labPath/service.yaml" -f "$labPath/ingress.yaml"
kubectl @labArgs apply -f "$labPath/deployment.yaml" -f "$labPath/service.yaml" -f "$labPath/ingress.yaml"
kubectl @labArgs rollout status deployment/nginx-lab --timeout=120s
```

Expected: namespace exists, server validation succeeds, then one replica becomes ready. Applying declares desired state; readiness follows asynchronously. Even the server dry-run belongs to this later authorized exercise, not the local/static manifest-creation step.

### 2. Inspect Deployment, ReplicaSet and Pod

```powershell
kubectl @labArgs get deployments,replicasets,pods -o wide
kubectl @labArgs describe deployment nginx-lab
kubectl @labArgs get replicasets,pods -o 'custom-columns=KIND:.kind,NAME:.metadata.name,OWNER-KIND:.metadata.ownerReferences[0].kind,OWNER:.metadata.ownerReferences[0].name'
```

Expected: one Deployment, its generated ReplicaSet, and one ready Pod. Owner references show the controller chain; desired and available counts describe different aspects of state.

### 3. Inspect labels and selectors

```powershell
kubectl @labArgs get pods --show-labels
kubectl @labArgs get deployment nginx-lab -o jsonpath='{.spec.selector.matchLabels}'
kubectl @labArgs get service nginx-lab -o jsonpath='{.spec.selector}'
```

Expected: both selectors match `app: nginx-lab` on the Pod. The extra template-hash label does not prevent that match.

### 4. Inspect the Service, EndpointSlices and internal access

```powershell
kubectl @labArgs get service nginx-lab -o wide
kubectl @labArgs describe service nginx-lab
kubectl @labArgs get endpointslices -l kubernetes.io/service-name=nginx-lab -o yaml
kubectl @labArgs exec deployment/nginx-lab -- wget -qO- http://nginx-lab.kubernetes-basics.svc.cluster.local/
```

Expected: one ready backend address matching the Pod IP, and nginx HTML from the in-cluster DNS/Service request. The internal request uses Alpine's existing wget from the running nginx container, so no helper Pod is needed. It tests a different entry path from the Windows browser.

### 5. Inspect Ingress and its controller class

```powershell
kubectl @labArgs get ingress nginx-lab
kubectl @labArgs describe ingress nginx-lab
kubectl --context k3d-urumi-local get ingressclass traefik
```

Expected: Traefik class, hostless `/` rule, and the correct Service backend. The Ingress status address need not be the Windows browser address; we use k3d's host port mapping.

### 6. Request the page from Windows

```powershell
curl.exe --fail --show-error --include http://localhost:8080/
```

Also open `http://localhost:8080/` in the browser. Expected: HTTP 200 and the nginx welcome page. This validates the external HTTP path, not HTTPS or production routing.

### 7. Record the original Pod and Service identities

```powershell
$beforePod = kubectl @labArgs get pods -l app=nginx-lab -o json | ConvertFrom-Json
$oldPod = $beforePod.items[0].metadata.name
$beforePod.items | Select-Object @{n='Name';e={$_.metadata.name}}, @{n='UID';e={$_.metadata.uid}}, @{n='IP';e={$_.status.podIP}}
kubectl @labArgs get service nginx-lab -o wide
```

Check that exactly one Pod exists before capturing it. Retain its name, UID and IP and the Service ClusterIP for comparison.

### 8. Watch Pods, then delete the captured Pod

Start this watch in a second terminal before deleting anything:

```powershell
kubectl --context k3d-urumi-local -n kubernetes-basics get pods -l app=nginx-lab -o wide --watch
```

In the first terminal:

```powershell
kubectl @labArgs delete pod $oldPod
```

Expected: the original Pod terminates while the ReplicaSet still desires one replica. We delete only the captured learning Pod, not the Deployment or a system Pod.

### 9. Observe replacement and readiness

Once the replacement appears in the watch, wait for it to become ready:

```powershell
kubectl @labArgs wait --for=condition=Ready pod -l app=nginx-lab --timeout=120s
```

Expected: a new Pod progresses to Running/Ready without re-applying the manifest. Stop the watch with Ctrl+C after observing recovery. One replica can have a service interruption during replacement; self-healing is not the same as uninterrupted availability.

### 10. Compare the new Pod and endpoints

```powershell
kubectl @labArgs get pods -l app=nginx-lab -o 'custom-columns=NAME:.metadata.name,UID:.metadata.uid,IP:.status.podIP'
kubectl @labArgs get endpointslices -l kubernetes.io/service-name=nginx-lab -o yaml
```

Expected: a new Pod name/UID and an updated ready backend. The Pod IP may change or be reused; a different IP is not required to prove replacement.

### 11. Verify the same Service and browser URL still work

```powershell
kubectl @labArgs get service nginx-lab -o wide
kubectl @labArgs exec deployment/nginx-lab -- wget -qO- http://nginx-lab.kubernetes-basics.svc.cluster.local/
curl.exe --fail --show-error --include http://localhost:8080/
```

Expected: unchanged Service identity/ClusterIP and working internal/external requests after readiness. No client or Ingress edit should be required.

### 12. Change live desired state imperatively from one to two

```powershell
kubectl @labArgs scale deployment/nginx-lab --replicas=2
kubectl @labArgs rollout status deployment/nginx-lab --timeout=120s
```

Expected: live Deployment `spec.replicas` becomes 2. The file still declares 1. Kubernetes controllers reconcile to the API object's live desired state; they do not continuously read this local YAML file.

### 13. Inspect both replicas and observe declarative drift

```powershell
kubectl @labArgs get deployments,replicasets,pods -o wide
kubectl @labArgs get endpointslices -l kubernetes.io/service-name=nginx-lab -o yaml
curl.exe --fail --show-error --include http://localhost:8080/
kubectl @labArgs diff -f "$labPath/deployment.yaml"
$diffExit = $LASTEXITCODE
if ($diffExit -gt 1) { throw "kubectl diff failed with exit code $diffExit" }
if ($diffExit -ne 1) { throw 'Expected replica drift, but kubectl diff found none' }
```

Expected: two ready Pods and two ready backend addresses across the Service's EndpointSlices. Two identical pages do not prove which replica served a request. Both Pods are on the same node, so this does not provide node-failure resilience.

`kubectl diff` compares live configuration with what applying the file would produce; it does not persist that proposed change. Expect the live replica count of 2 versus the file's 1. It contacts the API and uses dry-run processing, so it is not our offline static validator. Exit 0 means no differences, 1 means differences (expected here), and greater than 1 means an error. Other server-managed/defaulted output may appear; inspect the replica difference rather than assuming an exact whole-output match.

### 14. Re-apply the manifest to reconcile back to one

```powershell
kubectl @labArgs apply -f "$labPath/deployment.yaml"
kubectl @labArgs rollout status deployment/nginx-lab --timeout=120s
kubectl @labArgs get deployments,replicasets,pods -o wide
kubectl @labArgs get endpointslices -l kubernetes.io/service-name=nginx-lab -o yaml
kubectl @labArgs diff -f "$labPath/deployment.yaml"
$diffExit = $LASTEXITCODE
if ($diffExit -ne 0) { throw "Expected no drift after reconciliation; diff exit code $diffExit" }
curl.exe --fail --show-error --include http://localhost:8080/
```

Expected: applying the file resets live desired replicas to 1; the ReplicaSet removes the extra Pod. Termination and EndpointSlice updates are asynchronous: repeat the listings until one non-terminating ready Pod and one ready backend remain. The extra Pod's name/IP must no longer appear as a ready backend. The diff should then be empty and the page still work. We deliberately do not use a second imperative scale command to restore one replica.

### 15. Review observations, then clean up only the lab

After recording the results, confirm `kubernetes-basics` contains only this exercise, then run:

```powershell
kubectl --context k3d-urumi-local delete namespace kubernetes-basics --wait=true --timeout=120s
kubectl --context k3d-urumi-local get namespaces
kubectl --context k3d-urumi-local get ingress -A
curl.exe --show-error --include http://localhost:8080/
k3d cluster list
```

Expected: lab namespace/resources disappear; the request returns Traefik's no-route 404 once routing catches up, assuming no other route was added. curl deliberately omits `--fail` here because 404 is expected. The k3d cluster and its system components remain running. Keep these repository files as learning material; do not delete the cluster.

## Actual observations

**2026-10-11 — Stage 2.4A applied and inspected successfully.** This runtime record supersedes the manifest-creation status at the top of this file; only this actual-observations section was updated in this step. The approved manifests from commit de2e69d were applied without changes. Pod deletion, scaling, drift/reconciliation, cleanup, and deliberate probe failures have not been performed.

Prechecks confirmed current/target context k3d-urumi-local, a Ready node, healthy essential system components, no learning namespace, and no existing Ingress routes. Windows had approximately 3.14 GiB available RAM. Docker Hub reported the pinned nginx 1.30.5-alpine tag and Linux/amd64 image active. A fresh request to http://localhost:8080/ returned HTTP 404 with "404 page not found" before applying.

Applied the Namespace, then successfully server-dry-ran the Deployment, Service, and Ingress before applying those three objects. Rollout succeeded within the 120-second wait. The first image download failed with EOF and briefly entered ImagePullBackOff; Kubernetes retried automatically and pulled the image. No manifest changes, Pod deletion, or manual retry intervention was needed.

| Object | Authored by us? | Created by | Purpose | Observed status |
| --- | --- | --- | --- | --- |
| Namespace kubernetes-basics | Yes | Our kubectl apply through the API | Group lab resources | Active; purpose=learning label present |
| Deployment nginx-lab | Yes | Our kubectl apply through the API | Declare desired Pods | Desired/current/updated/ready/available replicas all 1 |
| ReplicaSet nginx-lab-76c7f65877 | No | Deployment controller | Maintain replica count | Owned by Deployment nginx-lab; one managed Pod |
| Pod nginx-lab-76c7f65877-pkdgp | No; its template is authored | ReplicaSet controller | Run nginx container | Owned by the ReplicaSet; Running, 1/1 Ready, zero restarts |
| Service nginx-lab | Yes | Our kubectl apply through the API | Stable internal address and backend selection | ClusterIP 10.43.133.91, 80/TCP to named targetPort http |
| EndpointSlice nginx-lab-fzdc6 | No | EndpointSlice controller | Track Service backend addresses/readiness | Owned by Service nginx-lab; 10.42.0.9:80 ready=true, serving=true, terminating=false |
| Ingress nginx-lab | Yes | Our kubectl apply through the API; interpreted by Traefik | Route external HTTP requests | Class traefik, host *, path /, backend nginx-lab:80; HTTP 200 observed |

Owner references establish `Deployment nginx-lab -> ReplicaSet nginx-lab-76c7f65877 -> Pod nginx-lab-76c7f65877-pkdgp -> container nginx`. The Pod UID is 4fb258e4-6bfd-43c6-b9b4-d185127674f2, its node is k3d-urumi-local-server-0, and its IP is 10.42.0.9. The container uses docker.io/library/nginx:1.30.5-alpine. The Pod has app=nginx-lab and pod-template-hash=76c7f65877 labels. Deployment and Service selectors both match app=nginx-lab; the Service selects the Pod, not the Deployment object.

Internal access through the approved `kubectl exec deployment/nginx-lab -- wget -qO- http://nginx-lab.kubernetes-basics.svc.cluster.local/` request succeeded with exit 0 and the nginx welcome page. The Service's DNS/ClusterIP identifies the stable internal destination; its EndpointSlice records the ready Pod backend. EndpointSlice is discovery state, not a network hop. No authentication or network-isolation test was performed, and ClusterIP is not treated as a security boundary.

Traefik remained available 1/1; its Pod is 10.42.0.8. IngressClass traefik uses controller traefik.io/ingress-controller. The live Deployment enables the Kubernetes Ingress provider and listens on web port 8000; its Service exposes port 80 to the named web port. The k3d serverlb still maps Windows 8080 to port 80. The lab Ingress describes the hostless / Prefix backend as nginx-lab:80 (10.42.0.9:80); its reported address is 172.18.0.3, while the tested Windows URL is localhost:8080.

The external curl request returned **HTTP/1.1 200 OK**, `Server: nginx/1.30.5`, `Content-Type: text/html`, and `<h1>Welcome to nginx!</h1>` in an 896-byte body. nginx access logs show successful Wget, curl, and kube-probe requests; the curl request arrived from the Traefik Pod IP. Together, route inspection and request evidence support the path `Windows localhost:8080 -> k3d load balancer -> Traefik -> Ingress rule -> nginx Service/backend -> nginx Pod`. The Ingress is controller configuration rather than another proxy process; this was not a packet-capture test of every hop.

Live Pod resources match the manifest: requests 50m CPU/32Mi memory, limits 250m CPU/128Mi memory. Both HTTP probes use / on the named http port, a 2-second timeout and failure threshold 3. Readiness delay/period are 2/5 seconds; liveness delay/period are 10/10 seconds. The Pod is Ready with restart count 0, and logs include HTTP 200 probe requests. This confirms configured probes and current healthy operation, not failure handling or a full workload capacity test.

The namespace and one-replica workload remain running for review. No Pod was deleted, no replica count changed, no resources cleaned up, and no commit created during this run. The later experiment steps remain future work; no Urumi application requirement is marked completed by this lab.

## References

- [Official nginx image tags](https://github.com/docker-library/official-images/blob/master/library/nginx)
- [Kubernetes Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
- [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [Kubernetes EndpointSlices](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/)
- [Kubernetes Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/)

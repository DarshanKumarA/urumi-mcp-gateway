# Production deployment and rollback runbook

**Validated:** the same chart renders and schema-validates complete local and production
configurations. **Not validated:** a real VPS installation, DNS/TLS, production storage,
image registry access, internal Woo OAuth routing on that host, or backup restore.
`values-prod.yaml` deliberately contains reserved placeholders; it is not ready to apply
unchanged. Production configuration does not require a separate manifest/code fork.

## Prepare the target

1. Provision a Linux/amd64 VPS and install K3s using its
   [official installation guide](https://docs.k3s.io/quick-start). Match the validated
   local Kubernetes version (`v1.35.5+k3s1`) when reproducing this evidence; review any
   different version with the chart checks before deployment. Keep the kubeconfig private.
2. Verify Traefik (or the selected Ingress controller), DNS, a usable StorageClass and
   NetworkPolicy enforcement. The chart's policy assumptions need live acceptance on
   the selected CNI. Use a distinct kubeconfig context such as `urumi-vps`; always pass
   it explicitly. Check available memory against all workload requests and real peak
   measurements; do not extrapolate the local functional run into production sizing.
3. Point separate store and gateway DNS names to the VPS. Permit intended public HTTP(S)
   traffic; restrict Kubernetes/SSH administration. Do not expose the upstream Services
   or either database through public ports.
4. Issue trusted certificates and create the referenced TLS Secrets using a protected
   operator workflow. The chart does not install cert-manager or issue certificates.
   Verify renewal and HTTPS before allowing production logins/customer traffic.

## Build and publish reviewed images

Build the five application images with the root README commands. Tag and push the exact
reviewed builds to your registry under your own namespace. Set their registry paths and
immutable version tags/digests in an ignored production override. Configure registry
authentication on the target if required; never put registry passwords into values.
The existing `stage8.1-openrouter` gateway source supports both provider adapters.

Create an ignored file such as `.secrets/values-vps.yaml` containing **configuration
only**, not credentials. Adapt these fields for the actual target:

| Values field | Required choice |
| --- | --- |
| `wordpress.canonicalUrl` | `https://` plus the real storefront domain |
| `wordpress.ingress.host`, `.className`, `.tls.secretName` | Same storefront host, installed Ingress class and existing certificate Secret |
| `platform.origin`, `.ingress.host`, `.ingress.className`, `.ingress.tls.secretName` | Real HTTPS gateway Origin/host, installed class and existing certificate Secret |
| `platform.gateway.environment`, `.secureCookie` | `production`, `true` |
| `wordpress.persistence.storageClass`, `mariadb.persistence.storageClass`, `platform.postgres.storageClass` | Existing target classes; choose capacity, retention and backup strategy for real data |
| `wooMcp.image`, `auxiliaryMcp.*.image`, `platform.gateway.image`, `platform.dashboard.image` | Published reviewed registry images; pull policy suitable for the target |
| `wooMcp.config.canonical_origin` | Internal OAuth signing uses `http://` plus the public store hostname, matching the current internal HTTP/Host behavior; validate live on the VPS |
| `wooMcp.config.connection_origin` | Leave empty to derive the WordPress Service address unless the deployment intentionally changes it |
| `bootstrap.adminEmail` | Operator-controlled email; no real values committed |
| `platform.gateway.provider`, `.model` | For the validated provider: `openrouter`, `z-ai/glm-5.3-flash`, with gateway image containing the adapter and the separate provider Secret |

The base production file currently inherits Gemini and the Stage 8.0 image. Explicitly
override provider, model and gateway image together to use the validated OpenRouter
path. The existing local configuration is not changed by this example. Production
HTTPS at Ingress does not encrypt internal HTTP hops.

## Provision Secrets and install

Create namespace `urumi` on the target. Provision the exact
[Secret contracts](../README.md#external-secret-contracts) before enabling their consumers.
Use a trusted secret manager or masked inputs with a JSON object held only in process
memory and passed to `kubectl --context urumi-vps -n urumi create -f -` through redirected
stdin. Capture output/errors; inspect name/type/key names only. Do not use real values
in shell arguments, YAML files, transcript logs or Git. Do not overwrite existing Secrets
as an installation convenience. Base64 is encoding, not encryption.

Store helper scripts in this repository are intentionally restricted to the **local**
context; do not use them against the VPS or silently edit their safety checks. Their
contracts describe the same required keys. Generate independent random DB/auth/service
secrets, choose operator-controlled admin passwords, and keep recovery copies in an
appropriate credential manager. Build the PostgreSQL URL with a URL-encoded password
matching the Secret's password and the configured user/database/Service DNS.

A fresh store needs a two-phase installation because Woo REST keys are issued **after**
WordPress/WooCommerce installation:

```powershell
helm lint charts/urumi -f charts/urumi/values-prod.yaml -f .secrets/values-vps.yaml
helm template urumi charts/urumi -n urumi -f charts/urumi/values-prod.yaml -f .secrets/values-vps.yaml

# Fresh target only: install the store first after provisioning its four Secrets.
helm upgrade --install urumi charts/urumi --kube-context urumi-vps -n urumi -f charts/urumi/values-prod.yaml -f .secrets/values-vps.yaml --set platform.enabled=false --set wooMcp.enabled=false --set auxiliaryMcp.arithmetic-mcp.enabled=false --set auxiliaryMcp.store-policy-mcp.enabled=false --wait=watcher --wait-for-jobs --timeout 15m
```

Use the WooCommerce admin to issue a Read/Write REST key for the intended service account,
then provision `urumi-woocommerce-rest`, the gateway/PostgreSQL/admin/service-token Secrets,
and the selected LLM Secret. The full overlay enables the components again:

```powershell
helm upgrade urumi charts/urumi --kube-context urumi-vps -n urumi -f charts/urumi/values-prod.yaml -f .secrets/values-vps.yaml --dry-run=server
helm upgrade urumi charts/urumi --kube-context urumi-vps -n urumi -f charts/urumi/values-prod.yaml -f .secrets/values-vps.yaml --wait=watcher --wait-for-jobs --timeout 15m
kubectl --context urumi-vps -n urumi get pods,jobs,pvc,ingress
```

Review the rendered resources and server preview before applying. These commands use
the validated Helm 4 syntax; with another Helm version consult its `--help` and validate
the corresponding wait behavior. Do not run the first-phase disables on an existing
accepted full stack. Do not use `--reuse-values` to hide omitted configuration changes.

Accept the target only after TLS/host routing, secret boundaries, gateway login, all three
upstreams, a synthetic COD order, the two-user flow, revoked-key rejection, failure isolation,
network policy and persistent-state recovery have passed there. Local results are not VPS evidence.

## Upgrade and rollback

Record the current Git/image revisions, Helm history, values, PVC identities and schema.
Take database-consistent backups of MariaDB and PostgreSQL plus the WordPress volume,
protect credential recovery material, and test restores before relying on those backups.
Plan downtime and compatibility; no backup automation or tested restore is supplied here.

For an upgrade, build/publish versioned images, review source and migrations, lint/render
both overlays and inspect the server-side dry run. Apply one reviewed Helm upgrade with
wait-for-jobs, then verify bootstrap receipts, readiness, data and an authorized tool call.
Stop and inspect a failed Job/rollout; do not repeatedly upgrade or automatically roll back.

```powershell
helm history urumi --kube-context urumi-vps -n urumi
# Only after checking schema/file compatibility with the chosen previous revision:
helm rollback urumi <reviewed-previous-revision> --kube-context urumi-vps -n urumi --wait=watcher --wait-for-jobs --timeout 15m
```

Helm rollback restores Kubernetes release configuration; **it does not undo database
migrations, product/order writes or persistent WordPress files**. Old bootstrap assets
may reject newer state, so a blind rollback can make recovery worse. Use a compatible
forward fix or a separately reviewed data restore when necessary. Never uninstall the
release, delete PVCs or recreate the cluster to repair an application error. Current
retention policies do not protect against deliberate PVC deletion or host disk loss.

No live production upgrade/rollback or VPS provisioning was performed in the final
local acceptance. The mandatory deployment explanation and chart reuse are supplied;
the optional real-VPS demonstration remains unattempted.

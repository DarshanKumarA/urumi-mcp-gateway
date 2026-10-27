# MCP Gateway on Kubernetes

This repository is for the Urumi AI FDE internship assignment: run a WooCommerce store on Kubernetes, write its MCP server, aggregate at least three upstream MCP servers through a team gateway, and provide a React dashboard with a chat agent that uses the gateway as the logged-in user.

**Current state (27 October 2026):** The complete local stack is deployed in the existing `urumi-local` Kubernetes cluster, Helm release `urumi` revision **7**. The gateway uses **OpenRouter / `z-ai/glm-5.3-flash`**. Provider smoke and two authenticated read-only dashboard queries passed, with audit attribution. All eight workloads were Ready at the last check; original store/storage identities were retained. The latest queries found no orders for that day, so they did not exercise arithmetic composition. Final two-user/external-client/revocation/demo acceptance and VPS/TLS validation remain incomplete. See [progress](docs/progress.md) and [journey](docs/project-journey.md) for evidence and limits.

## Source of truth and project documents

The [original assignment DOCX](docs/source/urumi-mcp-gateway-assignment.docx) is authoritative. The [faithful Markdown transcription](docs/assignment.md) preserves its mandatory requirements, optional work, live demonstrations, deliverables, and evaluation expectations. Proposals elsewhere do not change the assignment.

| File | Purpose |
| --- | --- |
| [AGENTS.md](AGENTS.md) | Required learning, planning, change, review, and validation process |
| [.gitignore](.gitignore) | Exclude generated output and recognizable local secret files |
| [docs/requirements.md](docs/requirements.md) | Stable requirement IDs, verification plans, demo mapping, and optional scope |
| [docs/architecture.md](docs/architecture.md) | Assignment constraints, approved Architecture v1, and open implementation details |
| [docs/decisions.md](docs/decisions.md) | Individual decisions, alternatives, rationale, and explicitly superseded proposals |
| [docs/progress.md](docs/progress.md) | Milestone status, validation evidence, and review boundary |
| [docs/project-journey.md](docs/project-journey.md) | Chronological engineering story and learning for an interview walkthrough |
| [docs/threat-model.md](docs/threat-model.md) | Required threat analysis, required controls, and separate optional hardening |

## Technology decisions and proposals

React is required for the dashboard. The assignment also mandates WordPress with WooCommerce, Kubernetes, Helm (not Kustomize), Streamable HTTP for the custom WooCommerce MCP server and supported upstreams, and Kubernetes Secrets.

Architecture v1 accepts one Python/FastAPI backend, the official Python MCP SDK, PostgreSQL for gateway state, MariaDB for the store, one application namespace, and one application Helm chart/release. The additional upstreams are arithmetic and store policy/reference servers with no external service dependencies. These are implementation choices, not technologies mandated by the assignment.

k3d with Docker Desktop is the validated local cluster platform (DEC-017). React/Vite, Python 3.13, MCP SDK 2.3.0 and PostgreSQL are implemented. OpenRouter is the active local LLM provider; the Gemini adapter remains available and is still the shared production default. See [architecture](docs/architecture.md) for pinned versions and the distinction between static, Docker and Kubernetes evidence. VPS k3s runtime remains unverified.

The mandatory core uses one store. Multi-store provisioning and other stand-out work are optional and have not been selected. VPS deployability using the same Helm charts and configuration changes is mandatory; actually demonstrating a VPS deployment is listed as stand-out work.

## Setup scope

The steps below reproduce the local packaging and deployment configuration. They do not reproduce existing database contents or prove the remaining demo obligations automatically. Deliverable acceptance remains tracked as REQ-DEL-01 in [requirements](docs/requirements.md).

## Working process

Understand → plan → identify files → implement small change → review diff → validate → document → verify understanding. Follow [AGENTS.md](AGENTS.md) and stop at major milestones. Real credentials must never enter source or committed configuration.

## Final local topology and URLs

```mermaid
flowchart TD
    Client[Browser or external MCP client] --> Ingress[Traefik]
    Ingress -->|gateway host /| Dashboard[React SPA / nginx]
    Ingress -->|gateway host /api and /mcp| Gateway[Authenticated gateway]
    Ingress -->|store host| WordPress[WordPress / WooCommerce]
    Gateway --> PostgreSQL[(PostgreSQL)]
    Gateway --> Woo[Woo MCP with service Bearer credential]
    Gateway --> Arithmetic[Arithmetic MCP]
    Gateway --> Policy[Store Policy MCP]
    Gateway --> LLM[OpenRouter HTTPS API / GLM 5.3 Flash]
    Woo --> WordPress
    WordPress --> MariaDB[(MariaDB)]
```

| Use | Local URL |
| --- | --- |
| Store | `http://store.urumi.test:8080` |
| Dashboard / same-origin API | `http://gateway.urumi.test:8080` / `/api` |
| External MCP | `http://gateway.urumi.test:8080/mcp` |

Both local hostnames resolve to `127.0.0.1` on the operator machine. Prefix paths
`/api` and `/mcp` route to gateway :8000, `/` to dashboard :8080; longest matching
prefix wins. Nginx supplies SPA refresh fallback. Store Ingress remains separate.
No upstream MCP or database has a public route.

## External Secret contracts

Local runtime update (27 October 2026): Helm revision 7 uses OpenRouter model
`z-ai/glm-5.3-flash` with gateway image `urumi-gateway:stage8.1-openrouter`.
Add external Opaque Secret `urumi-openrouter` with exact key `api-key`, using the
same masked-input/in-memory submission process below. Only the local gateway
mounts it; the existing Gemini Secret is retained but not mounted locally.
Production retains its Gemini default. Direct provider smoke and two read-only
dashboard queries passed; full Definition-of-Done acceptance remains incomplete.

All are pre-created `Opaque` Secrets in namespace `urumi`; Helm creates none.
Check only name/type/exact key names, never dump data or decode values.

| Secret | Exact keys | Consumers |
| --- | --- | --- |
| `urumi-mariadb-root` | `root-password` | MariaDB |
| `urumi-store-db` | `password` | MariaDB, WordPress, store bootstrap |
| `urumi-wordpress-admin` | `admin-password` | Store bootstrap |
| `urumi-wordpress-auth` | `auth-key`, `secure-auth-key`, `logged-in-key`, `nonce-key`, `auth-salt`, `secure-auth-salt`, `logged-in-salt`, `nonce-salt` | WordPress, store bootstrap |
| `urumi-woocommerce-rest` | `consumer-key`, `consumer-secret` | Woo MCP only |
| `urumi-postgres-auth` | `password`, `database-url` | PostgreSQL gets password; gateway/migration/bootstrap get URL |
| `urumi-admin-bootstrap` | `username`, `password` | Gateway bootstrap Job only |
| `urumi-openrouter` | `api-key` | Gateway runtime, active local provider |
| `urumi-gemini` | `api-key` | Gateway only when Gemini selected; not needed for a fresh OpenRouter-only local setup |
| `urumi-woo-mcp-auth` | `token` | Woo MCP and gateway bootstrap Job only |

PostgreSQL password and URL must describe the same account. URL structure:
`postgresql+psycopg://<user>:<percent-encoded-password>@urumi-postgres.urumi.svc.cluster.local:5432/<database>`.
User/database default to `urumi_gateway`; bracketed text is explanatory, not a value.
Build the URL in protected operator memory with URL encoding. PostgreSQL uses
`POSTGRES_PASSWORD_FILE`; gateway uses `URUMI_DATABASE_URL_FILE`. No literal credential env values.

Stage 8.1 provisioning procedure: inspect contracts; preserve matching existing
objects; stop on conflicts; obtain values through separate masked prompts or a
protected Secret-manager interface; construct JSON in memory and submit through
redirected stdin with explicit context `k3d-urumi-local`, namespace `urumi` and
create-only semantics. Capture/suppress child output/error. No plaintext files,
credential CLI arguments, chat disclosure or automatic rotation/replacement.
Recheck identity/key names only. No new helper was added; the reviewed
[REST helper](scripts/setup-woocommerce-rest-secret.ps1) remains specific to its
existing Secret. Review the concrete provisioning operation before entering real values.

Woo caller token: at least 256 random bits encoded as unpadded base64url, matching
`[A-Za-z0-9_-]{32,256}`. It is distinct from user API keys and Woo REST keys. Bootstrap
stores it server-side in PostgreSQL under the accepted credential model; DTOs/audits
exclude it. Secret rotation alone does not update an existing managed registration
or running Woo process; coordinated rotation needs review. No default admin password.

## Migration and bootstrap ordering

1. PostgreSQL starts on retained 2-GiB claim `data-urumi-postgres-0`.
2. Revisioned migration Job waits for DB and invokes Alembic `upgrade head` through
   its supported Python API. Migrations 0001–0003 remain unchanged.
3. Separate bootstrap Job waits for exact schema head, creates/verifies the initial
   administrator, then seeds `woocommerce`, `arithmetic`, `store_policy`.
4. Per-slug receipts own first creation only: preserve later edits, disabled state,
   changed credentials and deliberate removal. Only Woo gets a service credential.
5. Gateway init waits for schema plus bootstrap receipts. `/health/ready` repeats
   the read-only DB check. No migration, seed or password reset on server startup.

Jobs are ordinary resources, not hooks, allowing PostgreSQL in the same release.
Bounded waits (300s), deadlines (600s), `backoffLimit: 0` and wait-for-jobs make
failure explicit. Do not blindly repeat upgrades or automatically roll back.
Helm rollback does not rewind schema, DB or files. An audit left `started` means
interrupted/outcome unknown; there is no distributed exactly-once guarantee.

The separate existing store Job receives a release-revision-specific name. Its unchanged v3 code
validates ownership/settings, preserves installed users/passwords and business data,
and repeats the idempotent permalink hard-flush/fresh verification. It is not a new
installation or a strictly read-only shell run: rewrite persistence may be refreshed.
An owned-setting conflict must stop acceptance, not weaken validation or patch a marker.

## Images, probes and resources

| Workload | Local tag | CPU request / limit | Memory request / limit |
| --- | --- | --- | --- |
| Woo MCP | `urumi-woo-mcp:stage8.0` | 50m / 500m | 128Mi / 256Mi |
| Arithmetic | `urumi-arithmetic-mcp:stage6.1` | 25m / 250m | 64Mi / 128Mi |
| Store Policy | `urumi-store-policy-mcp:stage6.1` | 25m / 250m | 64Mi / 128Mi |
| Gateway | `urumi-gateway:stage8.1-openrouter` | 100m / 1000m | 192Mi / 512Mi |
| Dashboard | `urumi-dashboard:stage7.1` | 25m / 250m | 32Mi / 128Mi |
| PostgreSQL | `postgres:18.6-bookworm` pinned below | 100m / 500m | 256Mi / 512Mi |
| Each gateway Job / init | gateway Stage 8 image | 100m / 500m | 128Mi / 256Mi |

Custom local images use `Never` pull policy and must be imported before deployment.
PostgreSQL Linux/amd64 manifest:
`sha256:6b38fe68f2c02cafffbbce7496f76d110d8a947c039bd22c067e9a43c2250240`.
[Official release](https://www.postgresql.org/docs/release/18.6/) and
[image contract](https://hub.docker.com/_/postgres) checked 26 October.
PG18 data lives at `/var/lib/postgresql/18/docker` under PVC mount `/var/lib/postgresql`.
PostgreSQL runs 999:999; custom apps run 10001:10001. New workloads omit API tokens,
drop capabilities, prohibit privilege escalation and use RuntimeDefault/read-only
root. PostgreSQL has writable data/socket/tmp; dashboard has only ephemeral `/tmp`.

Gateway startup/liveness use local TCP; readiness requires DB/schema/bootstrap, not
upstreams or the LLM provider. MCP probes stay TCP-local. Dashboard uses static HTTP for
readiness/liveness; PostgreSQL uses local `pg_isready`. Jobs use deadline/exit status.
Existing WordPress/MariaDB budgets/storage remain unchanged. New budgets are hypotheses.
Prefer about 4 GiB available Windows RAM; stop below approximately 3.5 GiB before
adding load. Do not lower accepted budgets to pass. PVC retention is not backup;
local PV reclaim remains Delete if its PVC is deleted. Node/disk-loss durability,
HA and full-stack capacity are unproven.

## LLM configuration and data flow

The local model is `z-ai/glm-5.3-flash`, accessed through OpenRouter's
`https://openrouter.ai/api/v1/chat/completions` endpoint. It requires an OpenRouter
API key and sufficient account credit. Availability, pricing and tool support can
change; check the [model page](https://openrouter.ai/z-ai/glm-5.3-flash) before use.
No key, credit or provider account is supplied by this repository.

The configuration source is `charts/urumi/values-local.yaml`:

```yaml
platform:
  gateway:
    image: {repository: urumi-gateway, tag: stage8.1-openrouter, pullPolicy: Never}
    provider: openrouter
    model: z-ai/glm-5.3-flash
```

The chart renders `URUMI_CHAT_PROVIDER=openrouter`,
`URUMI_OPENROUTER_MODEL=z-ai/glm-5.3-flash` and
`URUMI_OPENROUTER_API_KEY_FILE=/run/secrets/openrouter/api-key`.
The file comes from `urumi-openrouter`; it is not a literal environment value.
Only the gateway receives the key. The existing Gemini Secret is retained in the
current cluster but is not mounted by the local gateway.

Chat follows: browser session identity → live namespaced tool catalog → model tool
request → shared InvocationService → committed audit START → upstream execution →
audit finalization → normalized result → model answer and safe UI trace. The model
does not contact WooCommerce directly. Requests use the already-pinned HTTP client;
timeout is 30 seconds, tool-round limit is five, redirects and automatic retries
are disabled. OpenRouter provider fallback is disabled. Prompts, tool schemas and
sanitized operational results are sent to OpenRouter and its serving provider;
do not submit credentials or unnecessary personal data in Chat.

## Reproduce the local deployment

Run from the repository root with Docker Desktop in Linux mode, k3d, kubectl and
Helm installed. The validated environment uses Python 3.13, K3s v1.35.5+k3s1 and
a Helm version supporting `--wait=watcher`. Docker builds install the committed
hash-locked Python dependencies and dashboard npm lock. No host Python install
is needed just to build the images.

1. Check available host RAM: prefer about 4 GiB, stop below approximately 3.5 GiB
   before adding workloads. Do not reduce established resource requests to proceed.
2. Reuse `urumi-local` if it exists. Never recreate it to fix an application error.
   On a genuinely fresh machine only, create it with the recorded configuration:

   ```powershell
   k3d cluster create urumi-local --servers 1 --agents 0 --api-port 127.0.0.1:6550 --port "8080:80@loadbalancer" --port "8443:443@loadbalancer" --image rancher/k3s:v1.35.5-k3s1 --wait --timeout 5m
   ```

   For an existing stopped cluster, use `k3d cluster start urumi-local` instead.
   Select `k3d-urumi-local`; verify node Ready and MemoryPressure=False.
3. Add both local hostnames to the operator's hosts file as administrator:

   ```text
   127.0.0.1 store.urumi.test
   127.0.0.1 gateway.urumi.test
   ```

4. Ensure namespace `urumi` exists, then provision the external Secret contracts
   above through masked prompts/in-memory submission. Preserve valid existing
   Secrets. The committed store helper is `scripts/setup-store-secrets.ps1`; the
   Woo REST helper is `scripts/setup-woocommerce-rest-secret.ps1`. Each supports
   offline `Validate` and explicit `Create`/`Check`. Neither issues Woo REST keys.
   Stage 8 provider/database/admin provisioning currently has a documented secure
   procedure, not a committed general-purpose helper; do not substitute plaintext
   manifests or `--from-literal` credential arguments.
5. On a fresh store, obtain the Woo Read/Write REST key from WooCommerce admin
   **after** WordPress is installed. For that first store-only installation, use
   the same chart with `platform.enabled=false`, `wooMcp.enabled=false`,
   `auxiliaryMcp.arithmetic-mcp.enabled=false` and
   `auxiliaryMcp.store-policy-mcp.enabled=false`. This breaks the fresh-store REST
   credential dependency; do not disable components on the existing accepted stack.
   Then create/check `urumi-woocommerce-rest`, provision the remaining contracts,
   and enable the complete stack through the normal local values.
6. Build the five local images (skip rebuilding when the reviewed images already
   exist and their identities have been verified):

   ```powershell
   docker build -t urumi-woo-mcp:stage8.0 apps/woo-mcp
   docker build -t urumi-gateway:stage8.1-openrouter apps/gateway
   docker build -t urumi-dashboard:stage7.1 apps/dashboard
   docker build -t urumi-arithmetic-mcp:stage6.1 apps/arithmetic-mcp
   docker build -t urumi-store-policy-mcp:stage6.1 apps/store-policy-mcp
   k3d image import urumi-woo-mcp:stage8.0 urumi-gateway:stage8.1-openrouter urumi-dashboard:stage7.1 urumi-arithmetic-mcp:stage6.1 urumi-store-policy-mcp:stage6.1 --cluster urumi-local
   ```

7. Lint/render before deployment. For an existing release also preview against the
   server and check store/PVC identity preservation; revision-named Jobs change on
   upgrades. Inspect output locally rather than committing generated manifests.

   ```powershell
   helm lint charts/urumi --values charts/urumi/values-local.yaml
   helm template urumi charts/urumi --namespace urumi --values charts/urumi/values-local.yaml
   helm upgrade urumi charts/urumi --namespace urumi --kube-context k3d-urumi-local --values charts/urumi/values-local.yaml --dry-run=server
   ```

8. Apply once after reviewing the preview and confirming Secrets/images/memory:

   ```powershell
   helm upgrade --install urumi charts/urumi --namespace urumi --kube-context k3d-urumi-local --values charts/urumi/values-local.yaml --wait=watcher --wait-for-jobs --timeout 15m
   kubectl --context k3d-urumi-local -n urumi get pods,jobs,pvc
   ```

   Require all workloads Ready, migration/bootstrap Jobs Complete, claims Bound
   and no OOM/restart loop. A registry EOF during the observed rollout was resolved
   by importing the exact pinned PostgreSQL image already cached in Docker, without
   changing its digest or repeatedly upgrading. Diagnose failures before retrying;
   do not delete claims or use automatic rollback.

## Verify and use

Log in to the dashboard with the administrator credentials supplied at bootstrap.
There is no default password. Refresh the Servers page and confirm WooCommerce,
Arithmetic and Store Policy are Connected. Start with the read-only prompt
`What orders came in today?`; check `woocommerce__list_orders` in tool activity and
the corresponding attributed Audit row.

For `What orders came in today, and what is their total and average order value?`,
expect `woocommerce__list_orders` then `arithmetic__sum_amounts` **when orders exist**.
The store uses Asia/Kolkata; an empty day has no average and should not trigger
arithmetic on an empty list. Use an explicit known order date for a nonempty
read-only test rather than creating orders merely to disguise an empty result.

Each member creates their own gateway API key and configures an external MCP client
with only `http://gateway.urumi.test:8080/mcp` and that Bearer key. Never configure
upstream URLs or service/Woo REST credentials in an external client. A key is shown
once; revocation must reject its next request. Chat uses session identity instead.
Mutating tools can change real demo data; do not repeat a write after an ambiguous
response. Inspect state read-only first.

## Production and use

Same templates, `values-prod.yaml`: replace reserved registry/host/storage-class
values, provision TLS Secrets, configure DNS/Ingress, HTTPS Origin and Secure cookies.
No certificate is rendered. Production runtime/TLS are unverified. Internal Woo
OAuth/Host routing also needs VPS acceptance. Policies restrict only three MCP
listeners and PostgreSQL ingress; egress remains open for DNS/Woo/provider traffic.
K3s includes a [network policy controller](https://docs.k3s.io/networking/networking-services)
by default. Local acceptance observed allowed gateway traffic and a refused
non-gateway connection to Woo MCP; other CNIs/environments need their own validation.

After runtime approval: log in as initial admin, invite a member, generate each
user's own gateway API key, configure the external MCP endpoint with that Bearer
key, and use Chat with browser session identity through the shared audited path.
Never provide upstream service/Woo REST credentials to external clients. Existing
product 11/order 12 and live-test product 16 remain; no extra checkout or reversal
of the deliberate on-hold order is authorized by setup.

App contracts: [gateway](apps/gateway/README.md), [dashboard](apps/dashboard/README.md),
[Woo](apps/woo-mcp/README.md), [Arithmetic](apps/arithmetic-mcp/README.md),
[Policy](apps/store-policy-mcp/README.md).

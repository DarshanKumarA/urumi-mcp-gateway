# Architecture proposal and assignment boundaries

Status: **proposed design, no application implemented**. The [original assignment](source/urumi-mcp-gateway-assignment.docx), transcribed in [assignment.md](assignment.md), controls scope. [requirements.md](requirements.md) maps obligations to verification. This document will become the required short system-design/tradeoffs note as reviewed choices are implemented; its current contents are not an accepted implementation specification.

## Assignment constraints

The assignment fixes four logical layers: one WordPress + WooCommerce store, our own WooCommerce MCP server, a React dashboard with a gateway/backend, and a dashboard chat agent. The gateway is an MCP client to upstreams and an MCP server for consumers. Chat and external clients must reach upstreams through the gateway only.

The custom WooCommerce server and supported upstream connections use Streamable HTTP. The gateway exposes one MCP endpoint, aggregates tools from every enabled upstream, routes calls correctly, documents collision handling, and isolates slow/dead upstreams with timeouts and clear errors. At least three upstreams are required; WooCommerce must already be registered as the first.

Admin/member roles, invitations, admin key issuance/revocation, member key generation, hashed/revocable per-user gateway keys, and a dashboard audit log are required. Upstream credentials remain server-side; members never see or configure them. The chat uses an LLM, displays called tools, and is attributed to the logged-in user. Granular per-tool permissions and OAuth are optional stand-out work.

The store, store database, custom WooCommerce MCP server, gateway backend, and dashboard run in local Kubernetes. The same Helm charts must support a production-like VPS via configuration changes, with local/production differences in values. Kustomize is not an alternative allowed by the assignment. Store database and WordPress content need persistent storage; storefront/dashboard need Ingress and stable URLs; every workload needs readiness/liveness checks and requests/limits. Credentials live in Kubernetes Secrets. The custom WooCommerce MCP server is internal-only and callable only by the gateway; the enforcement mechanism still needs design.

Actual VPS deployment is stand-out work. Mandatory work still includes VPS deployability, setup documentation, and the video explanation of configuration, Ingress, DNS, storage, secrets, and Helm upgrade/rollback. See OPEN-01 for the overlapping upgrade/rollback wording.

## Proposed implementation choices

Only the mandated portions in the middle column below are fixed by the assignment. Everything labeled proposed or open requires design review before implementation. No versions are pinned and no dependencies have been installed.

| Area | Assignment constraint | Proposed choice and reason | Relevant alternative / open point |
| --- | --- | --- | --- |
| Dashboard | React | React + Vite for a small dashboard and chat UI | Build setup/layout undecided; Vite is not mandated |
| Gateway/backend | MCP aggregation, control features, access and auditing | Python + FastAPI; keep control APIs and gateway logic in one backend initially to limit deployment units | Framework and process boundaries remain open |
| MCP implementation | MCP and Streamable HTTP for custom server/upstreams | Official Python MCP SDK to share protocol implementation across gateway and custom server | SDK version, session lifecycle, and framework integration need verification before coding |
| Other upstreams | Two additional servers, connected through gateway | Python if we write them; no servers selected | Existing compatible servers are allowed; the ban on existing WooCommerce MCP servers applies to our custom store server |
| Gateway state | Registry, users/keys, audit behavior required; database technology unspecified | PostgreSQL for control-plane records | Storage schema and persistence approach open; credentials must still follow the Kubernetes Secrets rule |
| Store database | WordPress/WooCommerce with persistent store database | MariaDB | Other WordPress-compatible database choice can be considered; no version selected |
| Store interface | Document interface and reason | No choice yet | Compare WooCommerce REST API with WP-CLI or another method; decide from tool needs and credential flow |
| Packaging and local cluster | Kubernetes; Kind, k3d, or Minikube allowed | Docker and Minikube with Docker driver, matching proposed baseline | Kind/k3d are allowed; local feasibility not yet tested |
| Deployment | Helm, same charts, values-only environment differences | Shared chart source with local/production values | Chart boundaries, ingress controller, domains, storage classes, and bootstrap approach open |
| Production-like target | Deployable to VPS; k3s acceptable | k3s | Live hosting not selected; provider and environment are not decided |
| Gateway transport | One interoperable MCP endpoint and API-key demo | Streamable HTTP for the gateway-facing endpoint too | Source explicitly names this transport for upstreams; gateway-facing transport is a proposed matching choice |
| Chat | LLM tool loop through gateway as logged-in user | Backend-hosted orchestration, reusing gateway authorization and auditing | Model/provider, streaming, tool-loop library, and identity handoff open; free tier/local model allowed |

## Proposed component and credential flows

```text
Dashboard browser (admin or member)
  -> backend login, server management, key management, audit and chat APIs
       -> proposed PostgreSQL control-plane state
       -> chat tool loop acting as the logged-in user
            -> gateway tool authorization, routing and auditing

External MCP client (gateway URL + per-user API key)
  -> gateway MCP endpoint
       -> gateway tool authorization, routing and auditing

Gateway -> our WooCommerce MCP server -> store interface TBD -> WordPress/WooCommerce
                                                                  -> store database
Gateway -> additional upstream 2 (TBD)
Gateway -> additional upstream 3 (TBD)

Store shopper -> storefront Ingress -> WordPress/WooCommerce
Dashboard user -> dashboard Ingress -> dashboard/backend
```

These are logical boundaries, not a file tree or commitment to separate deployments. The browser must not call upstreams or receive their credentials. The proposed chat orchestrator reaches tools through the gateway; whether it uses an HTTP loopback call or another gateway entry path needs review against the assignment and audit guarantees. Its calls must retain the actual user's identity rather than become an unattributed service account.

Proposed credential flow: a gateway key authenticates its user at the gateway; the gateway uses the independently configured upstream credential for the selected server; the WooCommerce server uses a separate store credential if its chosen store interface needs one. Client keys/tokens are not forwarded as upstream credentials. The exact hash scheme, login session design, Secret references, runtime Secret-management permissions, and storage of registry metadata remain open. Kubernetes Secrets are mandatory credential storage; optional encryption-at-rest hardening is not assumed to exist.

The gateway must enforce membership/management boundaries and revocation, discover and route tools, and write the required audit fields. Collision naming, disabled-tool refresh, session handling, discovery caching, timeout values, and error mapping are undecided. A single service/process is a proposal for simplicity, not evidence that these behaviors work.

## Deployment and data boundaries still to design

Keep the assignment-mandated store database and WordPress content persistent. PostgreSQL persistence, if that database is adopted, needs a reviewed plan so registry/key/audit state has a defined lifecycle; it is not a separate storage technology mandated by the assignment. Do not store real credentials in Helm values committed to Git.

Define public access for storefront/dashboard and the external client's gateway endpoint. Keep the custom WooCommerce MCP server private and enforce gateway-only calls. Merely omitting an Ingress would not demonstrate the entire gateway-only requirement; the exact network/application controls and their checks are unresolved. Cluster-wide default-deny policy is separately optional hardening.

Before deployment, document values differences for domains, Ingress, storage class, and Secret references. Do not create separate application implementations or divergent chart copies for local/VPS. The two additional upstreams' hosting and the model provider must be chosen and documented consistently with the assignment's cluster boundary and allowed model options.

## Unresolved assignment interpretations

These preserve ambiguities and unspecified acceptance details; they do not weaken stated outcomes. Resolve them with the user before the affected work. The original wording remains in assignment.md.

| ID | Source and uncertainty | Current treatment |
| --- | --- | --- |
| OPEN-01 | “Other ways to stand out / 9) Upgrades and rollback” is optional, while mandatory video item 6 explicitly includes “upgrade and rollback with Helm” | Keep the video explanation mandatory. The required depth of an executed safe upgrade/rollback versus an explanation is unresolved; do not silently promote all of OPT-09 into core scope or omit the video topic |
| OPEN-02 | Stories require inviting members but do not specify delivery, login, enrollment, or invitation expiry | Invitation capability is mandatory; email infrastructure is not assumed. Review a minimal invitation/login design before implementing |
| OPEN-03 | Done requires disabled tools to disappear from both chat and external client without specifying refresh timing or existing-session behavior | Preserve disappearance in both as mandatory; decide refresh/notification/cache behavior and how to demonstrate it |
| OPEN-04 | Done requires revocation to reject the next call and every call above to be correctly attributed in the audit log; metadata for a rejected/revoked-key call is unspecified | Plan to cover the rejected attempt; decide safe attribution and unavailable server/tool fields without storing raw keys |
| OPEN-05 | Done says to kill an upstream pod and show it unreachable while other servers work; restart/observation duration is unspecified | Choose a reproducible failure-demo procedure that still demonstrates the stated pod failure, not merely a disabled server |
| OPEN-06 | Done permits Claude Code, Cursor, or MCP Inspector but also requires one prompt using two upstreams | Select a client/demo arrangement that can actually satisfy the prompt requirement; do not assume every named client has an LLM prompt workflow |
| OPEN-07 | Done asks for orders from “today” without specifying timezone or date boundaries | Define and disclose the store/query timezone for consistent evidence; do not substitute an arbitrary time interval |

## Open engineering decisions

Beyond those interpretation questions, the login/invitation model, backend boundaries, versions, two additional upstreams, LLM/provider, store API, collision scheme, discovery/session lifecycle, timeouts, key format/hash/revocation mechanics, audit schema, Secret injection, internal access enforcement, chart layout, local DNS/Ingress/storage, and user A/B role allocation all remain open. None has implementation evidence. Record accepted choices and alternatives in [decisions.md](decisions.md) when reviewed; update this proposal to describe actual behavior only after implementation.

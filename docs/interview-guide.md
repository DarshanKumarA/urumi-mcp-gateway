# Urumi engineering interview reference

This guide explains the implemented single-store MCP gateway, the reasons behind its design, how to demonstrate it, and where its guarantees end. Use it to understand and rehearse, not to memorize claims you cannot defend. The original assignment in docs/source remains the authority. Code and measured results take precedence over examples in this guide.

## The project in one minute

I built a team gateway that gives users one MCP endpoint for several tools. A custom WooCommerce MCP adapter translates tool calls into WooCommerce REST requests. Arithmetic and Store Policy provide two additional upstreams. The React dashboard lets administrators manage upstreams and members, and lets users chat with an LLM. Chat and external MCP clients share the same authenticated, audited invocation path.

The complete system runs in one Kubernetes namespace through one Helm chart. PostgreSQL stores gateway identity, registry and audit state. WordPress and MariaDB hold storefront content and orders. Kubernetes Secrets supply credentials. Local and production values reuse the templates; I have validated the local runtime, not a real VPS deployment.

## What is proved

On 14 November 2026, User A's chat created product 30 at INR 499. Guest COD checkout created order 31, verified in Woo admin. Chat and a separate member's external MCP client retrieved it and used Arithmetic for total and average. Revocation, disabled catalogs, dead-upstream isolation/recovery, caller attribution, targeted network isolation and PostgreSQL/gateway replacement were exercised. Screenshots and sanitized results are in docs/evidence/2026-11-14.

The later chat/readability update adds safe table rendering, clearer errors and one bounded transient model-generation retry. Ten pre-change diagnostic prompts all succeeded; the reported intermittent failure rate was not reproduced. Do not describe a sample of successful requests as proof of a universal reliability rate.

## What remains outside the claim

The narrated live video and submission form are human deliverables. No real VPS/TLS, multi-store, load-capacity, backup restore or high-availability result is claimed. SMTP is not configured. Existing accounts named acceptance_b and acceptance_ui_b are disabled and their keys revoked; create a fresh member for recording. Claude Code/Cursor were not tested. Official MCP Inspector with the separate OpenRouter prompt driver was tested.

# Components and the call path

## Responsibilities

The dashboard is React served by nginx. It owns presentation and session interaction, not secrets or authoritative access decisions. FastAPI hosts management APIs, chat and the MCP endpoint. The gateway discovers upstream tools and routes invocations. The model suggests calls; the backend checks and executes them.

Woo MCP is original Python code around the official Woo REST API. Arithmetic computes deterministic decimal aggregates. Policy returns reference guidance. WordPress/WooCommerce stores business state in MariaDB and its persistent webroot. PostgreSQL holds gateway users, sessions, API-key verifiers, invitations, server registrations, tool mappings, bootstrap receipts and audits.

## Follow one order question

Browser session -> /api/chat -> live gateway catalog -> OpenRouter model -> selected tool -> shared InvocationService -> Woo MCP -> Woo REST -> normalized order data -> model -> readable answer.

For totals, the loop sends returned monetary values to Arithmetic before composing the answer. The model's own arithmetic is not evidence of cross-upstream composition. The tool trace and audit must show both services.

An external client takes a different entrance: member Bearer key -> /mcp -> shared InvocationService. It does not need store credentials or upstream URLs. The Inspector helper's separate OpenRouter credential is for generating the external model conversation, not MCP authentication.

## Why these boundaries

The browser cannot be trusted to choose its own identity. Shared invocation code prevents chat and external clients from drifting into different authorization and audit rules. A narrow Woo DTO limits accidental personal-data disclosure. Independent upstreams make failure isolation observable. PostgreSQL makes process restart different from loss of identity/audits.

The tradeoff is more components, network hops and operational work than a single script. Each invocation creates its upstream client/session, simplifying cleanup and current-config checks at the cost of handshake overhead. This is appropriate for the demonstrated small workload, not a proven high-throughput architecture.

Code map: apps/gateway/src/urumi_gateway/chat.py, core.py, invocation.py, upstream.py; apps/woo-mcp/src; apps/dashboard/src/pages.tsx. InvocationService is defined in invocation.py.

# Kubernetes resources you must explain

## Pods controllers and Services

A Pod is a running unit of containers. A Deployment reconciles stateless replicas; deleting one Pod does not delete its desired state, so Kubernetes creates a replacement. StatefulSets provide stable identities and persistent claim attachment for MariaDB and PostgreSQL. A Service supplies stable discovery/routing while Pods change.

The six Deployments are WordPress, Woo MCP, Arithmetic, Policy, gateway and dashboard. The two StatefulSets are MariaDB and PostgreSQL. All live in namespace urumi. A namespace organizes resources; it is not, by itself, a security boundary.

The local cluster is k3d running K3s in Docker. Traefik handles Ingress. store.urumi.test:8080 exposes the storefront; gateway.urumi.test:8080 exposes the dashboard, /api and /mcp. The Windows hosts file resolves these names to loopback. A browser resolving a hostname does not prove an Ingress route is healthy.

## Public and internal boundaries

Upstream and database Services are ClusterIP. They have no direct public Ingress route. Targeted NetworkPolicies restrict ingress to the three MCP listeners to gateway-labelled Pods. PostgreSQL permits the gateway and required database jobs. Woo also checks a separate service Bearer token. Internal addressing alone would not prove only the gateway can call Woo.

Live tests observed allowed gateway connections and denied peer connections. Policy enforcement depends on the CNI. Pod labels are not strong protection against an administrator who can create arbitrarily labelled Pods. These policies are not a cluster-wide default-deny egress firewall or complete SSRF defense.

## Persistent storage and Secrets

WordPress uses a 2 GiB PVC, MariaDB 5 GiB and PostgreSQL 2 GiB. A PVC requests storage; its PV supplies it; the StorageClass determines provisioning. local-path storage is tied to local node/disk availability. Pod replacement can preserve data while disk loss still destroys it.

A Kubernetes Secret carries credential bytes, commonly base64-encoded. Base64 is not encryption. RBAC, protected operator access and cluster storage configuration still matter. The chart references pre-created Secrets; it does not embed credential values in Helm values or source.

# Health resources and startup ordering

## Health checks have different jobs

Liveness asks whether a container should be restarted. Readiness asks whether it should receive traffic. Startup handling allows initialization time. A dependency outage should not automatically make every component restart repeatedly. Gateway readiness checks PostgreSQL/schema/bootstrap state, not every upstream or the LLM provider. This allows healthy tools to remain available when one upstream is down.

All eight continuing workloads have readiness/liveness and resource budgets. Finite migration/bootstrap Jobs have deadlines and exit/completion semantics, not service-style probes. A Completed Job is expected, not an unhealthy service.

Requests affect scheduling; limits bound consumption. CPU limits can throttle. A memory limit can cause an OOM kill. A Ready snapshot is not a load test. The laptop had limited free RAM during acceptance, so do not claim capacity from the absence of failures in a short functional test.

## Bootstrap is deliberately separate

PostgreSQL starts first. A revisioned migration Job waits for it and applies the Alembic migration head. A separate bootstrap Job waits for schema readiness, creates/verifies the administrator, and seeds Woo, Arithmetic and Policy registrations. Gateway init/readiness checks schema and bootstrap receipts before serving.

Bootstrap receipts mean first creation is owned once. Later administrator edits, disabled registrations, password changes and deliberate removals must survive a restart/upgrade. Application startup does not reset users or run arbitrary database initialization.

These are ordinary Helm resources rather than pre-install hooks, because PostgreSQL is installed by the same release. Bounded waits and zero blind Job retries expose failure. A failed Job requires diagnosis; repeatedly upgrading may create more revisions without fixing its dependency.

## Deployment tradeoff

Gateway and dashboard use Recreate, so updates may briefly interrupt access. This avoids duplicate replica peaks but is not zero-downtime/high availability. Revision-named jobs run during upgrades. Before applying, compare the rendered resources and inspect changes to storage, credentials, schemas and bootstrap behavior. After applying, verify workloads, jobs, real calls and preserved data.

# Identity access and credentials

## Two entrances one identity authority

Dashboard requests use an opaque session cookie. Passwords use Argon2id; the server authenticates the session and supplies the user's identity. Cookie controls include HttpOnly and SameSite; production requires HTTPS and Secure cookies. Mutating browser requests must have the configured Origin. The local HTTP setup is a development boundary, not production transport security.

External MCP requests use each user's own high-entropy gateway API key. Only a SHA-256 verifier and safe metadata/prefix are stored. A fast hash is suitable for a uniformly random high-entropy token; a human password needs a slow password hash such as Argon2id because it is guessable. These are different threat models.

Every MCP request checks current key/user state. Revocation rejects the next authenticated request; it does not cancel an already executing call. Disabling a user also prevents access. Invitations are private, expiring, single-use enrollment material. No public sign-up is required for the team workflow.

## Roles and authority

Administrators manage registrations and members and can inspect/revoke member keys. Members use enabled tools and generate/revoke their own keys. Members were denied server, user and audit administration with HTTP 403. Members are not read-only store users: enabled create/update tools exercise the shared Woo service account's powers.

Per-tool authorization and tenant data isolation are not implemented. Hiding a shared credential prevents disclosure of its value, but does not remove the authority granted through an allowed tool. Explain this distinction directly if asked about security.

## Where credentials go

Woo REST credentials mount in Woo MCP. The provider key mounts in the gateway. A separate Woo service token is supplied to Woo and seeded into its gateway registration. A user's gateway key is never forwarded to an upstream. Server-side registration credentials are excluded from browser read DTOs and audits.

The accepted database baseline stores upstream credential material without application-level encryption. Database/cluster administrators are trusted. Secret rotation alone does not automatically update the persisted registration or every running process; coordinate rotation rather than assuming a Secret edit is sufficient.

# MCP aggregation routing and failure isolation

## What MCP contributes

MCP standardizes tool discovery and invocation between a client and server. This implementation uses the official SDK and Streamable HTTP, rather than hand-writing a protocol. The gateway is a server to external clients and a client to each upstream. Tool schemas describe expected inputs; tools/list discovers tools and tools/call invokes a named tool.

MCP transport compatibility does not itself solve identity, least privilege, retry safety or audit persistence. Those are application decisions layered around the protocol.

## Tool names and current state

Public names use an immutable server slug followed by a double underscore and the original tool name. For example, woocommerce__list_orders and arithmetic__sum_amounts remain distinct. Stored mappings retain the authoritative original name. The router does not merely split an arbitrary user-supplied name and trust the suffix. Overlong names get deterministic suffix treatment and collisions are checked.

A duplicate-name registration was exercised; regression fixtures verify routing. Discovery refreshes enabled servers concurrently. Default discovery and invocation deadlines are five and thirty seconds. Cached metadata can remain for reference even when a server is unreachable, but stale tools are excluded from the live catalog.

Disabling a server immediately excludes it and stale calls are rejected against current state. A dead upstream does not invalidate healthy peer discovery/calls. Dashboard status is the last observed health, not a continuous background heartbeat; refresh it after recovery.

## Failure demonstration

Disable Policy and verify its disappearance in chat catalog and Inspector. Re-enable it. Delete only the observed Policy Pod and show Unreachable after refresh. Kubernetes may recover quickly; a short, controlled scale-to-zero window can make healthy Woo/Arithmetic calls visible. Restore the original one replica in a finally block and verify Connected plus a successful policy call.

Do not kill databases or delete PVCs for this demonstration. Do not equate a timeout with proof that a mutating upstream did nothing. A request may have reached the store before the response was lost. This is why automatic write replay is prohibited.

# WooCommerce tools and business semantics

## The five tools

list_products supports bounded pagination and SKU/search filters. create_product creates a simple named/priced product, with an optional unique SKU and duplicate refusal. list_orders uses the store's timezone/date window and pagination. get_order returns operational details for one positive ID. update_order_status requires an expected current status and an allowed next status, reducing accidental stale updates.

Woo MCP calls the official REST API. It does not install an existing MCP plugin or let the model run arbitrary WordPress code. Internal Service connectivity and canonical Host/OAuth signing handle the difference between internal addresses and the public store origin. HTTPS at a future Ingress would not encrypt internal HTTP hops automatically.

## Dates money and pagination

The store uses INR and Asia/Kolkata. On 14 November 2026, its day window was 13 November 18:30 UTC inclusive to 14 November 18:30 UTC exclusive. Asking for today later does not include order 31. This is expected date behavior, not missing data.

Always inspect has_more/total_pages. A first page is not necessarily every order. Monetary values are decimal strings; Arithmetic operates on homogeneous currencies rather than mixing INR with another currency or relying on model arithmetic. An empty set has no average. Explain count, total and average separately.

## The real acceptance data

Product 30 is Urumi Acceptance Bottle 2026-11-14, SKU URUMI-ACCEPT-20261114, priced INR 499. Order 31 contains one such product with free shipping and COD, total INR 499. Its status was temporarily changed Processing -> On hold -> Processing with guards. Historical product 11, product 16 and order 12 were preserved; order 12 remains on hold.

COD means payment is to be collected on delivery. Order creation or Processing status is not proof of paid revenue. Use wording such as order value when the payment has not actually been collected. Notification email failures reflect missing SMTP, not loss of the persisted order.

PII-minimized DTOs omit customer billing/shipping/contact data and arbitrary metadata. The model does not need a customer's street address to calculate order values. Limit returned data to the task, even when the upstream account can read more.

# Chat reasoning reliability and readable output

## The tool loop

Chat fetches the current tool catalog and sends the user's message, tool schemas and bounded history to OpenRouter. The selected model is z-ai/glm-5.3-flash. A model response can provide final text or structured tool calls. The backend validates the selected name/arguments, invokes through the audited gateway, returns sanitized results and requests the next model turn.

The loop is capped at five tool rounds, ten total calls, four calls per turn and a 180-second overall deadline. Schemas, arguments, outputs and context have size limits. Each chat message starts a new independent operation; it is not durable conversational memory. A user saying "change that one" should supply the exact order ID/context.

## Retry policy and its cost

The readability update retries model generation at most once for transient timeouts/transport failures and selected HTTP 429/500/502/503/504 responses. Short numeric Retry-After hints up to two seconds are honored; longer/unparsed hints return control. Authentication, quota and malformed output errors are not blindly retried.

Model generation has no direct access to executing tools. Only the accepted successful turn reaches InvocationService. Retrying generation therefore does not repeat an already accepted tool execution. Tool failures still stop the chat; writes are never automatically replayed. The outer deadline and call limits still apply. A retry can increase latency and provider charges; it cannot guarantee availability.

## Evidence versus diagnosis

The reported generic error was not a specific root cause. Ten read-only baseline prompts succeeded in roughly 3-8 seconds. This rules out a constant failure, not an intermittent one. New plain-language messages distinguish provider timeouts, temporary outage, credit problems and interrupted browser connections. Expandable details expose the safe code; server logs include code and completed-call count only.

AnswerContent renders a limited text-only Markdown subset: real tables, basic lists, emphasis and code. It does not run HTML or load model-supplied remote images/links. Tables scroll horizontally on narrow screens. Formatting improves comprehension but is not evidence that the answer is correct; verify tool results and scope.

# Audit durability and uncertain outcomes

## What the log guarantees

Both chat and external tool execution use InvocationService. The backend records the authenticated user, server, tool, timestamp, duration and outcome. Audit START is committed before dispatch. If that commit fails, execution is blocked rather than proceeding unaudited. Completion is finalized as success or failure.

Arguments/results and customer contacts are not stored in the audit log. It is an operational accountability record, not a full replay archive. Session versus API-key attribution identifies the authentication entrance. The two-user acceptance correlated real events to A and B.

## What it does not guarantee

There is no distributed transaction between PostgreSQL and WooCommerce. The store can commit a write while the gateway loses a response or fails to finalize its audit. A started event can therefore mean interrupted or unknown outcome, not proof of failure. Inspect the store read-only before retrying a write.

Invalid/revoked API keys are rejected before the invocation handler. Their HTTP 401 evidence is recorded separately; they do not become normal attributed tool-call rows. Authenticated disabled/dead tool failures do create failed audit rows. Do not claim the log attributes unknown credentials to a guessed user.

## Persistence experiments

PostgreSQL Pod replacement preserved users, a revoked-key record and 39 audit rows. Gateway replacement preserved the existing session, seven tools and audits. Later tests increased the count, so 39 and 46 are historical checkpoints, not permanent totals. New read-only diagnostics legitimately add audit rows.

Earlier store testing covered WordPress/MariaDB replacement. Current acceptance preserved the original PVC identities and old business records. These are restart/persistence tests; they do not prove backup restore, disk-loss recovery or high availability.

## If an interviewer asks about exactly once

Say: I avoid automatic write replay and expose uncertainty. I do not claim exactly-once business execution across network failures. Stronger semantics would require a supported idempotency key or business-operation ledger, clear reconciliation rules, and tests for crash points. A unique product SKU helps with some duplicates but is not a universal transaction protocol.

# Security threats and engineering tradeoffs

## Malicious tool descriptions and results

An administrator could register an upstream whose descriptions/results contain instructions intended to manipulate the model. The system prompt treats metadata as data, identities come from the server, schemas/routes are checked, credentials are excluded and calls are bounded. These reduce exposure but do not prove prompt-injection immunity.

A malicious tool could still mislead the model into a harmful action permitted by another tool. Tool schema validity is not business authorization. For higher-risk use, explicit confirmations, scoped tool permissions and narrower service accounts would be future work, not already implemented guarantees.

## SSRF and shared authority

An administrator can configure internal upstream URLs. Syntax validation and targeted ingress rules do not constitute a comprehensive URL allowlist or egress firewall. Arbitrary hostile URLs are unsafe merely because requests have timeouts. Cluster administrators can also bypass application boundaries.

Members share one store and common compute/model capacity. One can change data another reads or consume shared resources. Basic roles govern administration, not per-tool store permissions. Rate limiting, multi-tenant isolation and per-server access policy are not part of the implemented core.

## External data and credential storage

Prompts, schemas and sanitized operational results are sent to OpenRouter and the serving model provider. A redaction filter is not a universal personal-data classifier. Avoid unnecessary personal data in prompts. Provider retention and organizational policy need a separate operational decision.

Kubernetes Secret access and PostgreSQL credential storage are trusted boundaries. Upstream credentials are not application-encrypted at rest in PostgreSQL. Local traffic and internal service hops use HTTP. Production needs trusted TLS, Secure cookies, restricted administration, backup/restore planning and verified network enforcement.

## Why not add every bonus

The assignment's mandatory core is a working single store, custom MCP adapter, three-upstream gateway, team controls, chat, audits and Kubernetes packaging. Adding OAuth, multi-store provisioning, autoscaling or metrics without validating the core would increase risk and dilute evidence. Discuss them as sequenced improvements with threat models and tests, not as accomplished features.

# Installation production and rollback

## Fresh local installation

Use the detailed root README. The essential dependency order is cluster/hosts/namespace -> four store Secrets -> store-only Helm installation -> Woo REST key issuance -> REST/platform Secrets -> five image builds/imports -> full Helm values -> readiness/jobs -> authenticated smoke tests.

Woo REST keys cannot be issued before the store exists, which is why fresh installation has two phases. Do not run the store-only disables on an existing full deployment. Existing users should start the existing cluster and verify it, not recreate it.

setup-platform-secrets.py uses masked inputs and memory/stdin, checks all existing contracts, and creates missing objects only. It never replaces Secrets. It supports the default local names/account and is not a universal production installer. A syntactically valid API key can still be unfunded or revoked.

## Moving to a VPS

The same Helm chart accepts production values: registry image references, domains/Origin, Ingress class/TLS Secret references, Secure cookies, StorageClass/capacity and existing credential contracts. Publish reviewed images and configure registry access. Provision DNS, certificates and durable storage on the target. Validate internal Woo Host/OAuth behavior and network policy there.

The production example contains reserved placeholders and inherits a different default provider/image unless explicitly overridden. It must not be applied unchanged. Local schema/render checks are evidence of configuration structure, not proof the VPS works. The production runbook lists target acceptance steps.

## Safe upgrades and rollback

Record current image/Git/Helm/schema/PVC identities. Take database-consistent backups and a WordPress content backup, protect credentials, and test restore. Review migration compatibility and rendered changes. Apply one reviewed upgrade, wait for jobs/readiness and verify real data/calls.

Helm rollback restores resource configuration; it does not reverse database migrations, order writes or persistent webroot files. An older image may be incompatible with newer state. Prefer a compatible forward fix when appropriate; a data restore is a separate reviewed operation. Never delete claims or uninstall the release to make a failed readiness check disappear.

# Live recording plan and final readiness

## Preparation

Start Docker and the existing cluster. Confirm all eight workloads Ready, three Bound PVCs and three Connected upstreams. Open the gateway and store. Keep A and B sessions separate: tabs in one browser profile share cookies. Use a fresh invited member with an operator-controlled password; acceptance identities are intentionally disabled.

Install Inspector using the pinned command in docs/demo.md. The repository helper asks privately for B's gateway key and the separate OpenRouter key. Inspector performs actual MCP discovery/execution; the Python helper supplies the model loop. This satisfies the named Inspector path; it is not a native Claude chat demonstration.

## Record the business flow

As A, check a fresh SKU and create a named/priced product through Chat. Show it on the storefront. Manually add it to cart and use guest checkout with synthetic details and COD. Show confirmation and Woo admin. Ask A for today's orders and totals/average; show real Woo and Arithmetic activity.

As B, show key metadata without its value. Run Inspector discovery and the external prompt. Confirm the same order and both upstreams. Disable Policy as A, refresh both catalogs and show disappearance. Restore it, demonstrate a controlled failure with healthy peers, then recover. Revoke B's key and show next-request rejection. Show audits for A and B and authenticated failure rows.

## Narrate all six required subjects

Explain system design and the live two-user flow; Kubernetes namespaces/Secrets/volumes/Ingress/probes/budgets; MCP discovery/routing/collisions/timeouts; credential handling and malicious-upstream/member risks; the chat loop and server-side identity; local-to-VPS values and Helm upgrade/rollback limitations.

Review the video for credentials, private data and unsupported claims. Restore all servers/replicas, revoke disposable keys, and verify the video link is accessible. Submit the repository and video through the assignment form linked in docs/demo.md. Screenshots and this reference document do not replace the narrated recording. Recording readiness still requires your fresh member login/key and a new same-day order.

# Interview questions and concise answer practice

## Why an extra gateway instead of direct tool connections

It centralizes discovery, identity, upstream credentials, current-state routing and auditing. Clients need one endpoint and their own key. The cost is another failure boundary and network hop, so independent upstream timeouts and shared durable state matter.

## How do you know the second tool was really used

I show the model-selected Woo call, the returned order values, the Arithmetic call and its output, plus both audit rows. An answer containing a correct-looking average alone would not prove composition.

## What happens when the model hallucinates a tool

The server checks the name against the current catalog and validates arguments before routing. Unknown tools are rejected. The model does not select its own user identity or access arbitrary upstream URLs through the tool interface.

## Can a member steal the Woo key or change orders

The key value stays server-side, but members can exercise enabled write tools using shared authority. These are different questions. I implemented basic management roles, not granular per-tool authorization.

## How do you troubleshoot a failed chat

First identify the layer from the safe error code, tool trace and audit. Check model credit/availability for provider failures, current server health for upstream failures, and store state for uncertain writes. Never repeat a write solely because the browser showed an error. Compare same-date read-only prompts and record latency/failure counts.

## What would you improve next

Choose based on observed need: capture safe failure metrics; scope tool permissions for real business writes; introduce idempotency/reconciliation; establish tested backups; validate target TLS/network policy; benchmark before scaling. Explain cost, failure modes and acceptance criteria for each. Do not list technologies without tying them to a problem.

## How should you describe AI assistance

Be honest about using AI tooling for implementation, tests and documentation. Explain the code paths and decisions yourself, distinguish generated suggestions from verified behavior, and demonstrate how you checked them. Do not claim independent authorship or understanding you do not have. Practice tracing a request without reading this guide.

# Command reference and source map

## Safe operational observations

kubectl --context k3d-urumi-local -n urumi get pods,jobs,pvc,ingress

helm list --kube-context k3d-urumi-local -n urumi

kubectl --context k3d-urumi-local -n urumi describe pod OBSERVED_POD_NAME

py -3.13 scripts/setup-platform-secrets.py check

Read events and safe application codes. Never display Secret values, environment dumps, browser cookies or raw provider wire logs during a recording. Commands that change replicas, revoke keys, create products or upgrade releases are deliberate actions, not harmless status checks.

## Repository sources by question

Assignment and scope: docs/assignment.md, docs/requirements.md, original DOCX in docs/source. Design: docs/system-design.md and docs/architecture.md. Decisions/history: docs/decisions.md and docs/project-journey.md. Security: docs/security-summary.md and docs/threat-model.md. Current evidence: docs/acceptance.md and dated evidence directory. Operator instructions: README.md, docs/demo.md, docs/production.md.

Gateway identity and authorization: identity.py, auth_api.py and mcp_auth.py. Routing, upstream connections and audit: core.py, upstream.py and the InvocationService/audit repository modules. Chat/model handling: chat.py, openrouter.py, provider.py. Presentation: apps/dashboard/src/pages.tsx, AnswerContent.tsx and styles.css. Deployment resources: charts/urumi/templates and values-local.yaml/values-prod.yaml.

The external prompt driver is scripts/inspector-demo.py with inspector-bridge.mjs. It is separate from the web dashboard model loop and allows only its known read tools. Application tests live in each app's tests directory or dashboard source test files; integration chart/repository checks live under tests/integration.

## Provider retry references

OpenRouter's official error documentation describes retry hints and distinguishes authentication, quota, rate and server failures: https://github.com/OpenRouterTeam/docs/blob/main/api_reference/errors-and-debugging.mdx

The implemented retry policy is intentionally narrower than a general SDK retry policy. Inspect its tests in apps/gateway/tests/test_openrouter.py. A provider retry can incur another generation charge. A passing synthetic failure test proves the retry logic under that fixture, not future provider uptime.

## Final rehearsal

Explain one order call, one failed call and one uncertain write in your own words. Locate the responsible code. State the observed evidence, the limit of that evidence and the next test you would run. That is stronger engineering evidence than claiming the system is perfect.

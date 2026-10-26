# Urumi Gateway dashboard

## Stage 8.0 Helm integration

Reuses validated urumi-dashboard:stage7.1 without source/image changes. ClusterIP :8080,
10001:10001/read-only/drop ALL/no escalation/RuntimeDefault, no API token/Secrets,
ephemeral 32-MiB /tmp. Requests 25m/32Mi, limits 250m/128Mi are hypotheses. Startup is
TCP; readiness/liveness are static HTTP. Ingress sends /api and /mcp to gateway and
/ to SPA fallback. Local URL http://gateway.urumi.test:8080; production host/TLS via
values. All 24 tests and TypeScript/Vite build rerun; actual Ingress/browser acceptance
remains Stage 8.1.

Stage 7.1 implements the React/TypeScript dashboard and packages its production
assets separately from the gateway. This is offline/mock/container acceptance,
not Kubernetes or live Gemini acceptance. See [progress](../../docs/progress.md).

## Screens and roles

| Screen | Behavior |
| --- | --- |
| Login | Existing session login and `/api/me`; safe failures; logout revokes cookie session |
| Chat | Session-authenticated prompt, answer and compact namespaced tool trace; each prompt is independent |
| Servers, admin | Registered table, shared status chips, tools, add/edit, refresh, enable/disable, confirmed removal |
| Servers, member | Live usable tool catalog only; no management credentials or admin controls |
| Team, admin | Users, member invitation, member key metadata and confirmed revocation |
| API Keys | Own metadata, create with one-time value, confirmed revoke; endpoint displayed from current origin |
| Audit, admin | Safe attribution/outcome/duration/error fields; bounded pages and outcome filter |
| Invitation acceptance | Token/password submission; intended username and member role remain server-owned |

Hiding controls is not authorization: the existing backend session/role guards
remain authoritative. All requests use relative `/api/...` and `credentials: include`.
There is no frontend provider key, backend URL, CORS bypass, browser API-key auth,
localStorage or sessionStorage. API keys and invitations appear only in a one-time
dialog; dismissal/navigation unmounts their state. Clipboard copying is an explicit
user action, and the OS clipboard may retain its contents. Upstream credential edits
distinguish preserve, replace and clear, and clear the input after submission.

## Written design system

The user's written developer-platform specification is the design source: exact
neutral/accent scales, semantic colors, font sizes, spacing and shadow tokens are
in `src/styles.css`. No external reference URL, proprietary brand/font asset or UI
framework is used. Inter/system UI and JetBrains Mono/system monospace are fallback
stacks, not downloaded font files. White/near-white surfaces, restrained teal,
224px sidebar, slim top bar, compact headings and bordered tables form one shell.
No purple, gradients, oversized cards or decorative charts.

Connected/Unreachable/Disabled use shared dot-plus-text status components. Native
modal dialogs provide focus containment, Escape and focus restoration. Labels,
visible focus, text errors and semantic controls remain present. Long endpoints
truncate with full-value titles; expanded tool tables scroll inside their container.
At narrow widths the navigation becomes horizontal. React renders text rather than
untrusted HTML/Markdown. The chat trace contains only tool/server, outcome, duration
and a fixed safe summary; no arguments or raw tool result panels.

## Dependencies and validation

Runtime dependencies are React/React DOM 19.3.1 only. Vite 8.3.5, TypeScript 7.0.2,
Vitest 5.0.5 and Testing Library are pinned with an npm lock. jsdom 26.1.0 supports
the host's Node 22.18 test environment; the image builds with Node 22.22.0.

From this directory:

```powershell
npm ci --ignore-scripts
npm test
npm run build
npx --no-install prettier --check src vite.config.ts package.json tsconfig.json index.html
```

24 behavioral tests cover roles, login/me/logout, server actions/credential omission,
one-time values, confirmations, audit, two-tool chat, safe failures, loading/empty
states, invitation acceptance and literal HTML rendering. Production build includes
TypeScript checking. There is no pixel-snapshot suite or live store/provider call.

For an explicitly synthetic visual review, build first, then from repository root:

```powershell
py -3.13 apps/dashboard/tests/visual_fixture.py
```

This loopback-only fixture serves `dist` and fake API responses on port 8765. It is
**not** the backend, authentication acceptance, a live chat agent or deployable API.
Its example users, keys, invitations, tool activity and answer are synthetic. Stop
with Ctrl+C. The fixture is excluded from the runtime image. Stage 7.1 manually
reviewed Login, invitation acceptance, Chat, Servers, Team, API Keys and Audit plus
one-time/confirmation dialogs at 1242x764. Chat and page width fit; expanded tool
tables scroll internally without horizontal page overflow. Screenshots remain
outside the repository. No real credentials entered the fixture.

## Container

`Dockerfile` uses Node 22.22.0-bookworm-slim and nginx-unprivileged 1.28.0-alpine,
each pinned to its Linux/amd64 digest. The final image contains only static assets
and nginx configuration, no Node dependencies/test fixtures or credentials.

```powershell
docker build --platform linux/amd64 -t urumi-dashboard:stage7.1 apps/dashboard
```

Run as 10001:10001 on port 8080, with read-only root, ALL capabilities dropped and
no-new-privileges. nginx needs a small writable `/tmp` tmpfs for PID/temp directories;
no persistent volume is required. The container smoke in
[gateway tests](../gateway/tests/container_smoke.py) validates HTTP/assets, SPA
fallback, CSP, non-root/security state and clean shutdown using disposable containers.

This server deliberately returns 404 for `/api/` and `/mcp`: Stage 8's same-origin
Ingress must route those to the gateway and `/` to this dashboard. No proxy, Helm
resource or public exposure is added here. A standalone static container cannot
perform real login/chat until that routing exists.

## Remaining acceptance

Real Gemini generation, real three-upstream chat composition, deployed browser
login/invite/key revocation/audit demonstration, external MCP client, gateway caller
isolation, Kubernetes capacity, VPS and final video remain pending. Chat can request
mutating tools, but Stage 7.1 tests use mocks only. A lost response may hide a completed
write: there is no automatic replay or exactly-once guarantee. Inspect current state
before manually resubmitting a mutating request.

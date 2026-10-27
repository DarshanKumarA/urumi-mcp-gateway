# Gateway protocol core and persistent management

## Stage 8.0 deployment contract

Supersedes earlier Stage 7.1 loopback-only/Helm-pending notes. Image: urumi-gateway:stage8.0.
No dependency/migration changes. Production factory no longer seeds at startup.
From /app, `python -m urumi_gateway.deployment migrate` waits for DB and invokes
Alembic upgrade head; `bootstrap` waits for schema and uses existing first-admin-safe
logic plus three insert-once registrations; `wait-ready` reads schema/receipts only.
Errors are fixed codes/nonzero exits. Commands never call provider/Woo business endpoints.

Files: URUMI_DATABASE_URL_FILE; bootstrap also URUMI_BOOTSTRAP_USERNAME_FILE,
URUMI_BOOTSTRAP_PASSWORD_FILE, URUMI_WOO_MCP_TOKEN_FILE. Non-secret URLs:
URUMI_WOO_MCP_URL, URUMI_ARITHMETIC_MCP_URL, URUMI_STORE_POLICY_MCP_URL.
Receipts preserve managed edits/removal/credential changes. An old uncredentialed Woo
record requires operator review; it is not silently patched.

URUMI_BROWSER_ORIGIN supplies REST Origin policy and exact SDK MCP Host authority.
/health/ready returns only ready/not_ready with 200/503 from DB/schema/bootstrap checks,
never a peer/provider probe. TCP liveness is independent. Local Origin is
http://gateway.urumi.test:8080; production HTTPS requires Secure cookies. Existing
session chat/external-key audit paths and provider settings remain unchanged.

From repository root, `apps/gateway/.venv/Scripts/python tests/integration/docker_stage8.py`
creates disposable synthetic Docker fixtures. It tests PG18.6/migrations, bootstrap
twice, readiness, authenticated current/legacy discovery across three peers, security
and log exclusion. Seven tools, zero tool calls, no real provider/store. See
[root setup](../../README.md) for exact Secret/Job/resource contracts and future steps.

Stage 5.4 adds per-request external MCP Bearer authentication and durable attributed
audits to the existing identity, registry and admin/member REST backend.
**No public/Kubernetes deployment or live Gemini acceptance yet.** Stage 7.1 adds
the dashboard-facing session chat and container acceptance described below. Both SDK application
factories now require identity/invocation dependencies; there is no unauthenticated
default MCP factory. `api.create_production_app` requires PostgreSQL.

## Files and validation

- `models.py`: immutable registration snapshots and credential configuration;
  observed health is separate. `public_info()` omits credentials and connection URL.
- `repository.py`: async repository interface and in-memory implementation;
  add/edit/enable/disable/remove and revision-checked observations.
- `upstream.py`: official SDK client sessions and scoped HTTP transport, deadlines,
  redirect rejection, single-attempt invocation and safe failure mapping.
- `core.py`: discovery, stored namespace mapping, schemas, routing and health.
- `server.py`: official low-level SDK handlers and its Streamable HTTP ASGI app.
- `database.py`: SQLAlchemy tables/repository, transaction boundaries and one-time Woo seed.
- `management.py`: strict input models, credential lifecycle and safe read DTOs.
- `api.py`: FastAPI REST routes and shared SDK MCP lifespan.
- `mcp_auth.py`: per-request key verification and immutable request-state principal.
- `invocation.py`: shared audit-before-dispatch wrapper around the core.
- `audit_repository.py` / `audit_api.py`: committed metadata and admin-only listing.
- `migrations/` and `alembic.ini`: explicit versioned schema, no startup DDL.
- `tests/`: synthetic SDK upstreams, SQLite repository/API tests and opt-in PostgreSQL smoke.

From repository root in PowerShell:

```powershell
py -3.13 -m venv apps/gateway/.venv
apps/gateway/.venv/Scripts/python -m pip install --require-hashes --only-binary=:all: -r apps/gateway/requirements.lock
$env:PYTHONPATH = 'apps/gateway/src'
apps/gateway/.venv/Scripts/python -m unittest discover -s apps/gateway/tests -v
apps/gateway/.venv/Scripts/python -m compileall -q apps/gateway/src apps/gateway/tests
apps/gateway/.venv/Scripts/python -m pip check
```

Python 3.13; direct pins are `mcp==2.3.0`, `httpx2==2.16.0`,
`jsonschema==4.26.0` and `referencing==0.37.0`. MCP supplies the protocol;
HTTPX2 supplies the SDK-compatible configurable transport; jsonschema validates
discovered input/output contracts; referencing prevents remote schema retrieval.
Stage 5.2 adds exact direct pins `fastapi==0.162.0`, `SQLAlchemy==2.0.55`,
`psycopg[binary]==3.3.6`, `alembic==1.20.1` and explicitly declares already-used
`pydantic==2.14.1`. FastAPI implements the accepted REST boundary; SQLAlchemy Core
supplies standard typed SQL/transactions without a custom ORM; Psycopg connects to
PostgreSQL; Alembic owns migrations; Pydantic validates management DTOs. Synchronous
DB operations run with `asyncio.to_thread` so Windows does not need Psycopg's async
selector-loop policy. Database pool/connect/statement waits are bounded at 5s.
Stage 5.3 adds `argon2-cffi==25.1.0` (bindings locked at `26.1.0`).
The hash lock retains existing MCP pins and includes the exact dependency closure.
Windows-only pywin32/tzdata use markers. Tests use stdlib unittest/SQLite;
no separate test framework or OAuth signer is added. Stage 7.1 declares Uvicorn
0.54.0 directly and adds Google GenAI 2.33.0; HTTPX 0.28.1 is its separate transitive
dependency, while the proven MCP transport continues using HTTPX2 2.16.0.
Future lock updates must check extras/platform closure and verify wheel hashes.

## Flow and lifecycle

```text
Official client -> per-request Bearer verification -> /mcp (SDK ASGI)
  tools/list -> enabled registrations -> concurrent bounded SDK discovery
             -> stored namespaced catalog -> supported MCP schemas
  tools/call -> request-local principal -> InvocationService -> COMMIT audit START
             -> exact slug + stored mapping + current registration
             -> COMMIT resolved tool identity -> argument validation
             -> upstream SDK session -> original tool name (one attempt)
             -> finalize audit -> preserved MCP result or safe tool error
```

This core is a module of the accepted single backend. REST now uses the same
repository/core; authenticated auditing wraps it and future chat will reuse that path; none of those responsibilities live in Woo MCP.
Each upstream operation owns and closes its HTTP client and SDK session in the same
async task. No pool, worker, background health loop or persistent legacy session is
maintained across operations. This costs another handshake/list on each call, but
makes cancellation and configuration/credential changes explicit. The official SDK
negotiates modern or legacy upstreams; the gateway uses stateless HTTP for both
current and legacy downstream clients. No handwritten JSON-RPC implementation.

## Registry and names

An immutable UUID and unique immutable slug identify a registration. Slugs are
1â€“32 lowercase ASCII letters/digits separated by single underscores, starting with
a letter. Mutable fields are display name, HTTP(S) URL, enabled and optional static
credential. URLs cannot contain user-info, query strings or fragments. This is
input hygiene, not a full SSRF defense or an allowlist of network destinations.

Configured state is enabled/disabled; observed health is unknown/connected/unreachable.
An error never disables an enabled registration. Old observations cannot overwrite
an edited/removed registration. No disabled registration is contacted by a new
operation. Disable/edit during pre-call discovery is rechecked before dispatch;
already-dispatched calls cannot be undone. A changed registration suppresses their
result with a safe error; it does not roll back side effects.

Ordinary names are `<slug>__<original_name>`. Both `server_a__shared_name` and
`server_b__shared_name` coexist. Parse only the exact registered slug, then require
the authoritative exposed-name/server-ID/original-name mapping; never reconstruct
the original from a suffix. Upstream names containing `__` still route correctly.
Names use the MCP recommended ASCII set. If prefixing exceeds 128 characters,
truncate to 111 and append `_` plus 16 SHA-256 hex characters of the full name.
The digest is content-derived from the complete unshortened `slug__original_name`,
not its length; equal-length names with the same long prefix remain distinct.
Only overlong names add a suffix. Duplicate/invalid names or an actual generated
collision fail that upstream's discovery before catalog publication rather than
silently overwrite a route. The finite digest is not a mathematical uniqueness
guarantee; explicit collision detection prevents ambiguous registration.

## Discovery, schemas and errors

Every list request refreshes enabled servers concurrently. Healthy tools appear in
sorted order. Disabled servers are absent. An unreachable server's last-good metadata
is retained internally, marked unavailable and excluded from the current catalog.
Its cached names return a clear error until successful refresh. This implements the
user's Stage 5.1 refinement of the earlier stale-catalog presentation. Fresh callers
may call a known name before listing: the core first discovers that registration.
Client-side catalog refresh/notifications still require later integration.

Input/output schemas, title, description and standard tool annotations survive.
Local schema references work; remote references are rejected without fetching.
Annotations are untrusted descriptions, not authorization. Arbitrary top-level
metadata, icons, execution/task hints, server instructions and result top-level
metadata are intentionally not forwarded. Sampling, elicitation, resources/prompts,
subscriptions and interactive/multi-round tools are not proxied in this slice.

Successful MCP content and structured content are preserved; arguments and declared
structured outputs are schema-validated. Raw upstream error text is replaced with
`UPSTREAM_TOOL_ERROR`. Other safe errors include `VALIDATION_ERROR`, `UNKNOWN_TOOL`,
`UPSTREAM_DISABLED`, `UPSTREAM_CHANGED`, `UPSTREAM_UNAVAILABLE`, `UPSTREAM_TIMEOUT`,
`UPSTREAM_REDIRECT`, `UPSTREAM_INVALID_RESPONSE` and `UPSTREAM_UNSAFE_RESPONSE`.
Remote business-error detail is lost deliberately until a safe error contract is
reviewed. An attempted call that fails reports `write_outcome=unknown; retry_safe=false`;
untrusted read-only annotations do not justify claiming no side effect occurred.

Default deadlines: 5 seconds for connect/discovery (including all tool pages),
30 seconds for invocation; ordinary call setup+execution is bounded by 35 seconds.
A cold call can first spend another 5 seconds discovering its route. Deadlines are
configurable finite positive values up to 120 seconds. Sessions close on failure or
cancellation. Discovery is capped at 20 pages / 500 tools per server, with repeated
cursors rejected. Parsed metadata/results have a 2 MiB publication limit; this is
not a streaming wire-size or CPU/memory sandbox. A malicious schema/large JSON can
still consume resources before that check. Broader resource isolation is future work.

There are no automatic call retries or automatic write reconciliation. Use the
official `client.session.call_tool`, not `Client.call_tool`: SDK 2.3.0's convenience
method may retry HeaderMismatch or continue an input-required interaction. Redirects
are rejected in the HTTP response hook before the SDK can follow them. SDK version
upgrades must rerun single-attempt and schema/header regression tests.

## Credential and untrusted-content boundary

Optional bearer or static-header credentials belong to a registration only. Reserved
transport/header names and control characters are rejected. Incoming caller headers,
tokens and request metadata are never forwarded. Credentials have hidden repr fields;
do not serialize internal dataclasses wholesale. Tests use synthetic values only.
Stage 5.2 stores submitted upstream credentials in PostgreSQL without application
encryption, per the reviewed milestone instruction. This revises the earlier
Secret-reference-only design for this implementation checkpoint; it does not prove
the final Kubernetes Secret obligation. No real credentials were used. There is
no hardcoded identity or role bypass. Do not enable request-body/SQL debug logging.

Metadata/results reflecting a configured credential literally are rejected. Exception
details, raw upstream errors, arbitrary results and SDK/HTTP wire logs are not emitted.
Known SDK/HTTP loggers are filtered because they can log unsafe content even at warning
level; safe observation codes remain available. Do not enable unreviewed wire tracing
or telemetry exporters. Literal reflection checking is not universal data-loss
prevention: encoding/transformation by a malicious server is a residual risk.

Tool/schema descriptions and returned text remain untrusted data. They are never
inserted into privileged instructions or executed by this core. Preserving them is
not prompt-injection prevention; future chat must maintain that boundary. No generic
customer-PII filtering is claimed for arbitrary upstream results. Woo's own DTO policy
remains unchanged. HTTP upstream credentials lack encryption in transit; verified
HTTPS is needed outside a reviewed local/internal transport boundary.

## Evidence and next boundary

Tests exercise official clients against gateway ASGI and official upstream ASGI
servers, including current and legacy protocol paths, collision routing, schemas,
credential scope/reflection, pagination, cancellation, dead/slow peers, single-call
failures and concurrent configuration changes. No listening TCP server, live Woo
call, Kubernetes action or Linux execution is part of Stage 5.1.

Stage 5.2 validation: 80 tests pass, including all 51 Stage 5.1 tests. The added
repository/API tests use file-backed SQLite and actual FastAPI/SDK ASGI lifespans;
SQLite alone does not prove PostgreSQL compatibility. A separate real PostgreSQL
18.0 smoke passed migrations, schema comparison, identity/unique constraints,
CRUD, reconnect persistence, credential replacement/clear, health/cache, stale
observations, concurrent idempotent seed and deletion cleanup. The disposable
loopback-only Docker fixture was removed; k3d remained stopped. No live upstream
or Woo request, customer data or real credentials were involved.

Stage 5.3 now implements and tests REST identity/roles, invitations and hashed
revocable keys below. Stage 5.4 implements external MCP key enforcement and audit below.
Three real upstreams, gateway-to-Woo authentication/NetworkPolicy, hosting,
dashboard/chat and the final demo remain incomplete.

References: [SDK 2.3.0 release](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.3.0),
[MCP tools contract](https://modelcontextprotocol.io/specification/2026-07-28/server/tools),
[accepted architecture](../../docs/architecture.md#stage-51-gateway-protocol-core).


## Stage 5.2 schema and migration lifecycle

`mcp_servers` stores immutable UUID/unique slug, display name, normalized URL,
enabled flag, monotonic configuration revision, optional credential type/header/value,
UTC creation/update timestamps, observed status/check time/sanitized code, and a JSON
last-good tool-metadata cache with its revision/check time. No tool results are stored.
The database enforces unique slug, health/credential consistency, and immutable ID/slug
via a migration-installed trigger. Application validation rejects identity edits too.

`registry_bootstrap` holds the `woocommerce-v1` receipt and, from Stage 5.3, the
separate `identity-admin-v1` explicit-admin receipt. Startup inserts
WooCommerce once: slug `woocommerce`, display name `WooCommerce`, URL
`http://urumi-woo-mcp.urumi.svc.cluster.local:8000/mcp`, enabled, no credential.
Concurrent startups are safe. A preexisting slug is preserved entirely. After first
creation bootstrap owns **no mutable fields**; the receipt also prevents resurrecting
a deliberately removed registration. An administrator can explicitly add it again.
Woo REST credentials never belong here; future gateway-to-Woo credentials are separate.

Migration `0001_registry` is an explicit frozen schema snapshot. Apply migrations
as an operator step before starting the persistent app; startup never creates tables.
`URUMI_DATABASE_URL_FILE` names an externally provisioned protected file containing
the PostgreSQL SQLAlchemy URL. Never put its contents in command arguments, source,
Helm values, or logs. From repository root, after installing the lock and configuring
that file path in the environment:

```powershell
$env:PYTHONPATH = 'apps/gateway/src'
apps/gateway/.venv/Scripts/python -m alembic -c apps/gateway/alembic.ini upgrade head
# Explicit local-only non-secret settings; see bootstrap/identity instructions below.
$env:URUMI_ENVIRONMENT = 'local'
$env:URUMI_BROWSER_ORIGIN = 'http://127.0.0.1:8000'
$env:URUMI_COOKIE_SECURE = 'false'
apps/gateway/.venv/Scripts/python -m uvicorn urumi_gateway.api:create_production_app --factory --host 127.0.0.1 --port 8000 --no-access-log
```

These are future local operator instructions, not public deployment authorization.
FastAPI explicitly enters/exits the SDK app lifespan and mounts it last, preserving
`/mcp`. The same Gateway/repository serves REST refresh and MCP. Shutdown disposes
the DB pool. A DB failure gives a fixed safe error, not raw SQL/driver details.
Alembic downgrade is explicitly destructive to registry data; never use it as an
automatic recovery step. Stage 5.3 adds `0002_identity`; Stage 5.4 adds `0003_audit`.
The earlier migrations are unchanged. Audit snapshots survive registration removal.

For the opt-in PostgreSQL smoke, provision an EMPTY disposable loopback DB named
`urumi_gateway_fixture`; set `URUMI_TEST_DATABASE_URL_FILE` to its protected URL-file
path and run `apps/gateway/.venv/Scripts/python apps/gateway/tests/postgres_smoke.py`.
It deliberately upgrades/downgrades only that fixture and refuses populated databases.
Do not point it at application data. The test itself starts no containers or cluster.

## Management REST contract

| Method/path | Behavior |
| --- | --- |
| GET /api/servers | List safe registration DTOs |
| POST /api/servers | Create strict registration; duplicate slug returns 409 |
| GET /api/servers/{id} | Safe detail, 404 if missing |
| PATCH /api/servers/{id} | Edit display_name/url/enabled/credential only |
| DELETE /api/servers/{id} | Remove registration, credential and cached metadata; 204 |
| POST /api/servers/{id}/enable | Persist enabled=true, no recreation |
| POST /api/servers/{id}/disable | Persist enabled=false; live discovery/calls refuse it |
| POST /api/servers/{id}/refresh | Bounded core discovery; disabled is a no-contact no-op |

Creation requires slug/display_name/url; enabled defaults true. Credential is omitted
or null for none; otherwise `{kind, value, header_name?}` for bearer/header. The value
is a secret input only. PATCH omission preserves it, an explicit object replaces it,
`credential: null` clears it. No credential or header value is returned afterward.
Unknown fields, null mutable non-credential fields, invalid headers/URLs and wrong
types fail with sanitized 422; missing IDs return 404; conflicts 409; DB outage 503.
Validation errors omit input and error details, including malformed JSON. SQL
statement/result logging is suppressed; do not add unreviewed tracing/exporters.

Read DTOs expose id/slug/display_name/url/enabled, observed_status, has_credential,
credential_type, timestamps, safe failure_reason, tools/tools_stale/tools_last_checked.
They never serialize internal credentials/DB rows wholesale. Tools are untrusted
metadata, not HTML or privileged model instructions. Literal credential reflection
uses the existing core boundary; this is not universal encoded-secret/PII filtering.

Successful refresh persists connected/check time and safe metadata atomically under
the configuration revision. Failure persists unreachable/safe reason and retains
last-good tools marked stale, without disabling the server. Any configuration edit
resets observation/cache; stale in-flight results cannot overwrite an edited record.
MCP discovery never blindly serves persisted metadata: it refreshes and excludes
unavailable tools, as Stage 5.1 requires. Disabled or removed routes cannot dispatch.

URL baseline: HTTP(S), required host, valid nonzero port, maximum 2048 characters,
no userinfo/query/fragment/whitespace/control characters. Normalize scheme/hostname,
default port and empty path without changing a nonempty path. Internal Service DNS
is allowed intentionally. This is **not** DNS pinning, network egress restriction,
or comprehensive SSRF protection; that stand-out hardening remains future work.

All management routes now require a real admin browser session. Anonymous callers
receive 401; members receive 403. No fake admin or public deployment is provided.
Host validation is not authorization. External `/mcp` now requires its own Bearer
key on every HTTP request; browser sessions cannot authenticate MCP. No UI/chat yet.

Persistence references: [SQLAlchemy PostgreSQL/Psycopg](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#module-sqlalchemy.dialects.postgresql.psycopg),
[Alembic migrations](https://alembic.sqlalchemy.org/en/latest/tutorial.html),
[FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/),
[official PostgreSQL image](https://hub.docker.com/_/postgres).


## Stage 5.3 identity and authorization

`identity_repository.py` owns identity SQL and safe field allowlists; `identity.py`
centralizes passwords, sessions, invitations and API-key verification. `auth_api.py`
is the REST adapter and shared session/admin/Origin guards. `bootstrap_admin.py`
is a deliberate operator command. No SQL lives in handlers. Gateway routing/core,
Woo MCP and the accepted `0001_registry` snapshot are unchanged.

### Schema and bootstrap

Apply explicit `0002_identity` after `0001_registry`; startup never creates tables.
`users` stores immutable UUID/unique lowercase username, admin/member role, Argon2id
password hash, enabled flag and UTC timestamps. `sessions`, `invitations` and
`api_keys` store only token digests plus lifecycle metadata. User references use
`ON DELETE RESTRICT`; disable members rather than deleting identities. Future audit
history must retain attribution, not cascade away with users or registrations.
Username is 3–64 lowercase ASCII letters/digits/underscore/hyphen, starting with a
letter. This implements the Stage 5.3 username contract, refining DEC-009's earlier
email-login proposal without introducing email delivery or account linkage to Woo.

After migration, provision a protected password file outside the repository (later
an externally managed Kubernetes Secret mount). Set only these non-secret pointers:
`URUMI_DATABASE_URL_FILE`, `URUMI_BOOTSTRAP_PASSWORD_FILE` and
`URUMI_BOOTSTRAP_USERNAME`. Run `python -m urumi_gateway.bootstrap_admin` with the
source path configured as above. Never put the password itself in arguments,
environment variables, documentation or logs. No default password exists.

The command reads a bounded file, removes one terminal newline, and creates the
first admin using a transactional `identity-admin-v1` receipt. Repeating for that
existing enabled admin preserves its password; another identity/existing conflicting
user fails safely. Concurrent calls converge without overwriting passwords. Startup
does not invoke this command. Explicit identity downgrade destroys identity data and
removes that receipt; it is not an automatic recovery mechanism.

### Passwords and browser sessions

Argon2id uses the pinned library defaults: 64 MiB, time cost 3, parallelism 4,
16-byte independently generated salts and 32-byte hash. Passwords are 12–128
characters when created; no trimming. Verification is centralized. Unknown usernames
still perform one dummy Argon2 verification; unknown, disabled and wrong-password
login failures return the same 401. This reduces enumeration differences, not a
claim of identical network timing. Two concurrent hash operations per process bound
hashing memory; this is not rate limiting or a request-queue bound.

Sessions use 32 cryptographically random bytes encoded as an opaque token. Only its
SHA-256 digest is persisted. Login returns a safe profile and sets `urumi_session`
only as an HttpOnly, SameSite=Lax, Path=/, host-only cookie. Re-login rotates/revokes
the previous valid browser session. Logout revokes the row and clears the cookie.
Every request checks expiry, revocation and the current enabled user; browser IDs,
roles and forwarding headers are not trusted. No token appears in `/api/me`.

| Non-secret setting | Default / constraint |
| --- | --- |
| URUMI_ENVIRONMENT | Production by default in the production factory; explicit local for HTTP development |
| URUMI_BROWSER_ORIGIN | Required by production factory; exact HTTP(S) origin, no path/query/userinfo |
| URUMI_COOKIE_SECURE | true by default; false allowed only outside production; production requires HTTPS and true |
| URUMI_SESSION_SECONDS | 28800 (8 hours), bounded 300–86400 |
| URUMI_INVITATION_SECONDS | 86400 (24 hours), bounded 300–604800 |

All state-changing `/api` requests, including login and invitation acceptance,
require `Origin` exactly matching the configured origin; missing/null/different
origins fail 403. If present, Sec-Fetch-Site must be same-origin or none. No Referer
fallback or permissive CORS exists. Safe GETs require identity where applicable but
not Origin. This is a small same-origin CSRF defense, not protection from XSS,
compromised same-origin code or non-browser callers who can forge Origin. Authentication
still provides access control. API responses use Cache-Control: no-store. Production
factory rejects insecure production configuration; TLS termination/deployment remain
untested. SDK `/mcp` Host/Origin protections remain unchanged and are separate.

### Invitation and key lifecycle

Admin invitations are member-only, bound to the intended username and shown once.
The raw 256-bit token is manually shared; only its hash persists. Expired, revoked,
used or invalid tokens fail. Acceptance conditionally claims the invitation and
inserts the member in one transaction, so concurrent redemption yields one account.
Clients cannot substitute a username or role. Listing never returns token/hash.

API keys have format `urumi_key_<43 base64url characters>`, generated from 32 random
bytes. The first 18 characters are a safe visible identification prefix; only the
SHA-256 hash of the complete key and metadata are persisted. The raw key is returned
once on creation. Passwords need costly salted Argon2 because humans choose them;
random 256-bit tokens can use SHA-256 without enabling practical guessing. Indexed
hash lookup is followed by constant-time digest comparison for API-key verification.
The reusable verifier returns safe user/key identity, never hash/raw key. Every
verification checks revocation and current enabled user with no identity cache.
Admin revocation makes the same raw key fail on its next verification. Stage 5.4
now calls this verifier on every MCP request, including already-connected clients.

| Route | Authorization / behavior |
| --- | --- |
| POST /api/auth/login | Origin check; generic credential failure; cookie + safe profile |
| POST /api/auth/logout | Session + Origin; revoke and clear cookie |
| GET /api/me | Session; ID, username, role only |
| All /api/servers routes | Admin session; Origin additionally on mutations |
| POST /api/invitations | Admin; intended username; one-time token |
| GET /api/invitations | Admin; metadata only |
| DELETE /api/invitations/{id} | Admin; revoke |
| POST /api/invitations/accept | Origin + token/password proof; member only; no automatic login |
| POST /api/keys | Own authenticated user; label; raw key once |
| GET /api/keys | Own key metadata, never hashes/full values |
| DELETE /api/keys/{id} | Revoke own key; another owner's ID is not found |
| GET /api/users and /api/users/{id} | Admin; safe user metadata |
| GET /api/users/{id}/keys | Admin; target user's key metadata |
| DELETE /api/users/{id}/keys/{key_id} | Admin; revoke target key, never recover its raw value |
| POST /api/users/{id}/disable or /enable | Admin; member-only; no admin lockout action |

Normal API responses, sanitized errors and application logs contain no password,
session/token/key hash, raw key or invitation token. The only raw-token responses
are their explicit one-time issuance endpoints; session issuance uses Set-Cookie.
Do not enable request/body/header tracing, SQL row dumps or debug exception pages.
Python immutable strings cannot be reliably zeroized; file and process permissions,
TLS and operator logging hygiene still matter. Disabling a member blocks existing
sessions/keys while disabled; re-enabling restores otherwise-valid, unrevoked tokens.
Revoke tokens explicitly if permanent invalidation is needed.

### Stage 5.3 evidence and remaining work

130 tests pass, including all 80 prior gateway tests with management fixtures now
using real admin login, plus identity/API/CSRF/privacy/concurrency checks. The 51
Stage 5.1 protocol regressions remain unchanged. Disposable PostgreSQL 18.0 passed
both migrations from empty, schema comparison, concurrent first-admin bootstrap,
concurrent single-use acceptance, hash-only persistence, reconnect, session/key
revocation and restrictive identity constraints; the fixture container was removed.
No real users/credentials, Woo calls or Kubernetes actions were performed.

At the Stage 5.3 checkpoint external `/mcp` was unauthenticated and audit absent.
Stage 5.4 addresses those below. Rate limits/password recovery,
MFA, dashboard/chat, public TLS/hosting, gateway-only upstream enforcement and broad
SSRF containment are not implemented. Upstream credentials still have the approved
Stage 5.2 recoverable PostgreSQL baseline without application encryption. Do not
expose this backend publicly before hosting/security acceptance.

Password reference: [argon2-cffi API and defaults](https://argon2-cffi.readthedocs.io/en/stable/api.html).

## Stage 5.4 authenticated MCP and attributed audit

Every HTTP request reaching the SDK transport requires exactly one Authorization
header with Bearer and a valid gateway key. Initialize, discovery, calls and other
HTTP methods are checked; query parameters, cookies, forwarded headers and tool
arguments never authenticate. Missing/malformed/unknown/revoked/disabled-user keys
receive 401 with a Bearer challenge; verifier unavailability fails closed with a
sanitized 503. Key validity is never cached. Revocation blocks the next HTTP request
on an existing client; it does not undo an already-dispatched operation.

Middleware copies ASGI request state, inserts a frozen safe Principal (user UUID,
username, role, key UUID, authentication source), then removes Authorization before
the SDK runs. The pinned SDK carries the originating HTTP Request into current and
legacy handler contexts. There is no global current-user value or ContextVar to
reset. Concurrent real-client tests overlap A/B calls and verify separate audit
attribution. Request-state copies leave the incoming shared state unchanged.

`InvocationService.invoke_tool(principal, name, arguments)` is the only external
call path. It wraps, rather than duplicates, `Gateway.call_tool`. Future chat must
construct a session-derived principal server-side and use this same service; a
reserved session-source fixture proves the seam without implementing chat. The
browser cannot select principal fields. Gateway keys never become upstream headers;
only each registration's configured credential reaches its upstream.

### Durable event and failure boundary

Explicit `0003_audit` adds `audit_events`: immutable event UUID, user UUID/username
snapshot, nullable key UUID, api_key/session source, historical nullable server UUID
and slug, exposed/original tool names, UTC started/completed timestamps, monotonic
duration_ms, started/succeeded/failed outcome and allowlisted error code. There are
no argument/result, token/hash, header, upstream credential or exception-body columns.
User/key foreign keys restrict deletion. Server UUID/slug are historical snapshots,
not cascading references; removing a registration preserves them. Database triggers
freeze identity snapshots and completed rows. There is no audit deletion API.

The initial START transaction commits before any upstream operation in the invocation
path. Cold route discovery follows that commit. The authoritative original tool name
is bound and committed before dispatch; already-known names can be recorded initially.
Unknown caller strings are stored as `<unresolved>` to avoid persisting arbitrary
PII/token text, while a recognized server UUID/slug is retained. Resolved invalid
arguments, disabled/dead peers, timeouts and upstream errors finish as failed with a
fixed code. Ordinary discovery has no audit event; unauthenticated requests and
malformed transport messages rejected before tools/call are not normal call events.

Initial insert/commit or route-binding failure prevents business dispatch. Finalization
failure after execution returns `AUDIT_FINALIZATION_FAILED; write_outcome=unknown;
retry_safe=false`, with no replay or automatic reconciliation. Cancellation/crash
can leave a durable started row: interpret it as interrupted/outcome unknown, never
as proof of success or failure. A lost database commit acknowledgement can also make
finalization uncertain; inspect durable state operationally. PostgreSQL and the remote
mutation are not one transaction, and this provides no distributed exactly-once claim.
Safe successful structured results and existing schemas/annotations remain intact.

### Admin audit query

`GET /api/audits` requires an admin browser session (anonymous 401, member 403).
Pagination is page >= 1 (maximum 100000), per_page 1–100, default 20. Optional filters
are user_id UUID, server_slug, tool (known exposed name), and outcome. Response items
contain only the safe audit fields above plus collection page/per_page/total/has_more;
no argument/result recovery or credential endpoint exists. Listing errors are sanitized.

### Validation and limits

All 160 tests pass, including the previous 130 regressions. No dependency additions.
Stage 5.4 uses synthetic identities and upstream ASGI fixtures, not live Woo or a
listening network deployment. Current/legacy official-client tests exercise per-request
authentication, immediate admin revocation, concurrent attribution, committed START
visibility from another DB connection, failed-start zero dispatch, failed-finalization
one dispatch, interrupted records, safe query authorization and historical attribution.
Real disposable PostgreSQL 18.0 applies 0001 -> 0002 -> 0003 from empty, compares schema,
checks START/finalization/reconnect, removal/revocation survival and immutable constraints,
then downgrades/upgrades only that disposable fixture and removes its container.

Auth/audit do not imply tool-specific permissions: members can invoke enabled mutating
tools. Rate limits, audit retention/backup/operational repair, comprehensive SSRF,
application encryption of recoverable upstream credentials, public TLS/hosting,
additional real upstreams, dashboard/chat and gateway-to-Woo authentication/NetworkPolicy
remain incomplete. Do not enable access/body/header/SQL-result logging or unreviewed
telemetry; auth rejection is not permission to log a submitted key URL or header.

## Stage 7.1 session chat and hosting

`chat.py` adds POST `/api/chat` (strict message only, maximum 4000 characters) and
GET `/api/catalog` (safe live tool information for authenticated members). Both use
the existing session boundary; unsafe requests require the configured exact Origin.
All server-management routes stay admin-only. The browser cannot supply identity.

```text
HttpOnly session -> server-derived Principal(source=session, api_key_id=null)
 -> fresh enabled/live gateway catalog -> Gemini function selection
 -> exact gateway name -> existing InvocationService.invoke_tool
 -> committed audit START -> original upstream -> audit finalization
 -> bounded sanitized result to Gemini -> answer + safe visible trace
```

There is no direct upstream client in chat and no fake user API key. Concurrent
session users retain separate audit attribution. The same START-failure rule prevents
dispatch, and an attempted write's uncertainty is unchanged. Tool failures stop the
request without inviting replay; repeated identical mutating calls within one request
are blocked. Annotations guide this extra guard, not authorization. Members can
request enabled write tools. No persistent conversation or automatic retry exists.

Provider: official `google-genai==2.33.0`, explicit async `models.generate_content`,
manual function loop, SDK automatic function execution disabled, provider attempts=1.
Model Content/thought signatures are retained when returning function results.
The reviewed `gemini-3.7-flash` candidate's official page now marks it deprecated and
automatically routed to 3.8; `gemini-3.8-flash` is the verified stable function-calling
default. The model remains configurable. Sources checked on 26 October 2026:
[SDK release](https://github.com/googleapis/python-genai/releases),
[package 2.33.0](https://pypi.org/project/google-genai/2.33.0/),
[3.7 status](https://ai.google.dev/gemini-api/docs/models/gemini-3.7-flash),
[3.8 model](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash),
[function calling](https://ai.google.dev/gemini-api/docs/function-calling).

| Setting | Behavior |
| --- | --- |
| URUMI_GEMINI_API_KEY_FILE | Preferred protected mounted key file; never print its contents |
| GEMINI_API_KEY | Server-process environment fallback; not a frontend variable or command argument |
| URUMI_GEMINI_MODEL | Default gemini-3.8-flash |
| URUMI_PROVIDER_TIMEOUT_SECONDS | Default 30, bounded 1–60 seconds |
| URUMI_MAX_TOOL_ROUNDS | Default 5, allowed 1–6 |

Missing key starts the backend normally and returns CHAT_NOT_CONFIGURED for chat.
No real key was supplied or searched for during acceptance. Existing database/auth
configuration and explicit migrations remain required. Provider failures have fixed
safe auth/rate-limit/timeout/invalid/unavailable codes. Wire logging from the pinned
GenAI/HTTP libraries is filtered; do not enable external request/body tracing.
Truncated/non-STOP provider results are rejected instead of labelled successful.

Limits: 180 seconds per chat request, 100 catalog tools, 4 calls per model round,
10 calls total, 16k argument/schema/text bounds and 64k normalized tool result.
Descriptions are capped at 500 characters. Tool metadata/results are untrusted
data, never inserted into privileged system instructions. Known contact/credential
fields and recognizable credential/contact text are filtered before provider use;
this is not comprehensive PII detection or prompt-injection prevention. Prompts and
selected tool output leave the backend for Google when configured. The final
assistant text is untrusted plain text, not executable HTML or authority to act.
Provider-incompatible arbitrary upstream schemas fail safely; all possible third-party
schemas/models have not been runtime proven. Large-day pagination/currency handling
is instructed, not a deterministic financial aggregation guarantee.

188 gateway tests pass (160 prior + 28 chat/provider tests). Mocked composition covers
Woo list_orders -> arithmetic sum_amounts and Woo list_orders -> policy get_policy,
plus one product-create call, failure/no-replay, session audit attribution, concurrent
users, no-key behavior and SDK configuration/error handling. Existing current/legacy
MCP regression tests remain green. No live Gemini or Woo request was performed.

The new Dockerfile uses Python 3.13.17-slim-bookworm at the reviewed Linux/amd64
digest, a fresh hash-locked runtime dependency install and explicit Uvicorn 0.54.0.
It serves API and SDK MCP on :8000; no dashboard files, tests or credentials are
copied. One worker owns the SDK lifespan/provider; shutdown closes provider and DB.
Migrations 0001–0003 are unchanged and remain explicit operator commands.

From repository root:

```powershell
docker build --platform linux/amd64 -t urumi-gateway:stage7.1 apps/gateway
docker build --platform linux/amd64 -t urumi-dashboard:stage7.1 apps/dashboard
apps/gateway/.venv/Scripts/python apps/gateway/tests/container_smoke.py
```

The smoke creates only disposable Docker fixtures: an unpublished PostgreSQL 18.0
on a dedicated bridge with fixture-only trust authentication, a protected temporary
DB URL file, and loopback-published application containers. It applies all migrations,
verifies real listeners and unauthenticated API/MCP 401 responses, checks non-root
10001:10001/read-only/capabilities/no-new-privileges/seccomp, static assets/SPA/CSP and
clean shutdown. It removes its containers/DB volume/network/file. It does not perform
authenticated container MCP calls or a full browser-to-real-provider chain.

For an optional later manual provider smoke, provision the key file securely, set
only its path plus the model setting, and use a logged-in dashboard with the matching
same-origin backend. Start with a no-tool prompt, then explicitly approved read-only
composition. Never paste the key into a URL, CLI argument, chat or repository. Without
a protected key, skip; Stage 7.1 deliberately did. Real writes require their own review.

Stage 8 must supply PostgreSQL persistence/migration/bootstrap operations, same-origin
API/MCP/static Ingress, protected Secrets, TLS/cookie settings, exact external MCP Host
allowlist, probes/resources and targeted upstream caller authentication/NetworkPolicy.
The current SDK Host allowlist is still loopback-only; public external-client hosting
has not been enabled. No Helm change, Kubernetes start or deployment occurred here.

## OpenRouter provider option

Set `URUMI_CHAT_PROVIDER=openrouter`, `URUMI_OPENROUTER_MODEL` to an explicitly
selected tool-capable model ID, and `URUMI_OPENROUTER_API_KEY_FILE` to the mounted
key file. The separate external Secret is `urumi-openrouter`, type Opaque, exact
key `api-key`; only the gateway mounts it. Never put its value into Helm values.

The existing pinned HTTP client calls only HTTPS OpenRouter chat/completions.
Responses are bounded to 256 KiB and requests to the configured timeout (30 seconds
by default). Redirects, application retries and provider fallbacks are disabled.
Exact names and call IDs survive each exchange. Only the existing ChatService and
InvocationService execute tools, with audit START before dispatch. Provider error
bodies and headers are not returned. Gemini remains the default unless explicitly
overridden; no database schema, upstream or audit behavior changes.

Prompts, tool schemas and sanitized operational results go to OpenRouter and its
selected serving provider. This changes the external data processor; account
retention/provider controls require operator review. See
[OpenRouter client tools](https://openrouter.ai/docs/guides/features/tool-calling).

# Gateway protocol core and persistent management

Stage 5.3 adds PostgreSQL identities, opaque browser sessions, admin/member REST
authorization, member invitations and hashed revocable API keys to the same backend.
**External `/mcp` remains unauthenticated; no audits or public deployment yet.**
The protocol-only `server.create_app` retains its in-memory test default;
`api.create_production_app` requires PostgreSQL and never falls back to memory.

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
The 41-package hash lock retains existing SDK pins and adds their exact dependency
closure. Windows-only pywin32/tzdata use markers. Tests use stdlib unittest/SQLite;
no separate test framework or OAuth signer is added. Uvicorn remains SDK-transitive.
Future lock updates must check extras/platform closure and verify wheel hashes.

## Flow and lifecycle

```text
Official client -> /mcp (SDK ASGI)
  tools/list -> enabled registrations -> concurrent bounded SDK discovery
             -> stored namespaced catalog -> supported MCP schemas
  tools/call -> exact slug + stored mapping + current registration
             -> argument validation -> upstream SDK session -> original tool name
             -> normalized MCP content/structured result or safe tool error
```

This core is a module of the accepted single backend. REST now uses the same
repository/core; future auth/audit/chat can do so too; none of those responsibilities live in Woo MCP.
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
revocable keys below. External MCP key enforcement and audit remain Stage 5.4 work.
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
automatic recovery step. Stage 5.3 adds identity tables in `0002_identity`; audit
tables remain deferred. Future
audit rows must retain a server-ID/slug snapshot or nullable non-cascading reference;
removing a registration must not cascade-delete audit history.

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
Host validation is not authorization. External `/mcp` is still unauthenticated;
no browser UI/CORS, audit or chat is included.

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
must connect this verifier to every MCP request, including already-connected clients.

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

External `/mcp` is still unauthenticated. Audits, rate limits/password recovery,
MFA, dashboard/chat, public TLS/hosting, gateway-only upstream enforcement and broad
SSRF containment are not implemented. Upstream credentials still have the approved
Stage 5.2 recoverable PostgreSQL baseline without application encryption. Do not
expose this backend publicly. Stage 5.4 should wire per-request key verification and
mandatory attributed audit events around the existing gateway invocation path.

Password reference: [argon2-cffi API and defaults](https://argon2-cffi.readthedocs.io/en/stable/api.html).

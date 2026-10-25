# Gateway protocol core and persistent management

Stage 5.2 adds PostgreSQL persistence and FastAPI management routes to the same
backend. There are no users, authorization, API keys, audits or chat yet.
**NOT YET AUTHORIZED: loopback development only; never expose to real callers.**
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
The 39-package hash lock retains existing SDK pins and adds their exact dependency
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
1–32 lowercase ASCII letters/digits separated by single underscores, starting with
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

Sessions/admin-member authorization, invitations, hashed/revocable user keys,
audit, three real upstreams, gateway-to-Woo authentication/NetworkPolicy, hosting,
dashboard/chat and the final demo remain incomplete. Proposed Stage 5.3 is identity,
sessions and admin/member enforcement before exposing the management surface.

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

`registry_bootstrap` holds only the `woocommerce-v1` seed receipt. Startup inserts
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
apps/gateway/.venv/Scripts/python -m uvicorn urumi_gateway.api:create_production_app --factory --host 127.0.0.1 --port 8000 --no-access-log
```

These are future local operator instructions, not public deployment authorization.
FastAPI explicitly enters/exits the SDK app lifespan and mounts it last, preserving
`/mcp`. The same Gateway/repository serves REST refresh and MCP. Shutdown disposes
the DB pool. A DB failure gives a fixed safe error, not raw SQL/driver details.
Alembic downgrade is explicitly destructive to registry data; never use it as an
automatic recovery step. No users/session/key/audit tables are introduced. Future
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

Management routes currently have no authentication or admin/member authorization.
No fake admin is inserted; tests explicitly exercise this temporary limitation.
Loopback Host validation is not caller authorization. No public deployment, browser
UI/CORS, user keys, audit or chat is included in this milestone.

Persistence references: [SQLAlchemy PostgreSQL/Psycopg](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#module-sqlalchemy.dialects.postgresql.psycopg),
[Alembic migrations](https://alembic.sqlalchemy.org/en/latest/tutorial.html),
[FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/),
[official PostgreSQL image](https://hub.docker.com/_/postgres).

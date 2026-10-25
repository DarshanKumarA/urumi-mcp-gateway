# Gateway protocol core

Stage 5.1 is offline implementation, not a deployment or authorized public endpoint.
There are no users, API keys, management REST routes, audits or chat yet. The default
ASGI factory has an empty in-memory registry. Never expose this unauthenticated
application to real callers. PostgreSQL remains the selected future persistence.

## Files and validation

- `models.py`: immutable registration snapshots and credential configuration;
  observed health is separate. `public_info()` omits credentials and connection URL.
- `repository.py`: async repository interface and in-memory implementation;
  add/edit/enable/disable/remove and revision-checked observations.
- `upstream.py`: official SDK client sessions and scoped HTTP transport, deadlines,
  redirect rejection, single-attempt invocation and safe failure mapping.
- `core.py`: discovery, stored namespace mapping, schemas, routing and health.
- `server.py`: official low-level SDK handlers and its Streamable HTTP ASGI app.
- `tests/`: synthetic SDK servers A/B and nested ASGI protocol/registry tests.

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
The 29-package lock selects the complete SDK dependency closure (including
PyJWT's crypto extra) from the validated Woo lock without changing its pins/hashes.
Windows-only pywin32 has a marker. Uvicorn is an SDK transitive dependency, not a
new hosting milestone. No FastAPI, database driver, test framework or OAuth signer
is added. Future lock updates must resolve extras and platform markers, compare
the direct dependency closure, and verify wheels with `--require-hashes`.

## Flow and lifecycle

```text
Official client -> /mcp (SDK ASGI)
  tools/list -> enabled registrations -> concurrent bounded SDK discovery
             -> stored namespaced catalog -> supported MCP schemas
  tools/call -> exact slug + stored mapping + current registration
             -> argument validation -> upstream SDK session -> original tool name
             -> normalized MCP content/structured result or safe tool error
```

This core is a module of the accepted single backend. Future REST/auth/audit/chat
code can use the same repository/core; none of those responsibilities live in Woo MCP.
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
Final credential resolution from Kubernetes Secret references and PostgreSQL metadata
is not implemented here; there is no hardcoded user identity or role bypass.

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

PostgreSQL persistence, admin management APIs, sessions/roles, hashed/revocable keys,
mandatory audit persistence, three real upstreams, gateway-to-Woo authentication and
targeted NetworkPolicy, hosting, dashboard/chat and final demo remain incomplete.
Proposed Stage 5.2: design and implement persistent registry/identity/auth/audit
contracts in small reviewed slices before exposing or deploying this endpoint.

References: [SDK 2.3.0 release](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.3.0),
[MCP tools contract](https://modelcontextprotocol.io/specification/2026-07-28/server/tools),
[accepted architecture](../../docs/architecture.md#stage-51-gateway-protocol-core).

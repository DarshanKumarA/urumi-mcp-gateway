# Security posture and threat model

The single-store core separates users from upstream credentials and records tool
activity under the authenticated caller. It does not provide per-member data
isolation or complete defense against a malicious administrator/upstream.

## Credentials and authority

- Dashboard passwords use Argon2id. Opaque session cookies are HttpOnly/SameSite;
  write requests require the configured same Origin. Production requires HTTPS and
  Secure cookies; the local demo uses HTTP.
- Each user creates a high-entropy gateway API key. Only its SHA-256 verifier and
  non-secret prefix/metadata are stored. Every MCP request checks current key/user
  state; revocation rejects the next request. Live admin and member-UI revocations
  both returned 401 on the next call.
- Kubernetes Secrets supply store/database/bootstrap/provider credentials. Woo REST
  credentials mount only in Woo MCP. The LLM key mounts only in the gateway. The
  Woo service token seeds a server-side PostgreSQL registration. Admin-entered upstream
  credentials are also held in PostgreSQL under the accepted implementation baseline,
  without application-level encryption. They are omitted from read DTOs, audits and
  browser/client responses. Database/Secret administrators are trusted.
- A user key authenticates to the gateway only. It is stripped before upstream
  handling; each upstream receives only its own configured credential. Client-token
  passthrough would expose reusable user authority to an unrelated server and is not used.

**Shared credentials still grant shared authority.** A member who can call product
creation or order update can exercise the Woo service account's corresponding powers,
even though they never see its credentials. Members cannot manage upstreams, team
membership or audit records. They are not read-only users: per-tool authorization
was optional and was not implemented.

## Malicious servers and interaction between members

Tool descriptions and results can contain prompt injection. The model is instructed
to treat them as data; the gateway validates schemas, routes through known registrations,
checks current enabled state, bounds calls/timeouts, suppresses raw errors, and rejects
literal credential reflection. These measures do **not** prove prompt-injection immunity.
A malicious tool can still mislead the model, return harmful content, consume resources,
or exploit the authority of another allowed tool. Prompt/schema/operational results sent
to OpenRouter are also an external data boundary; provider retention is an operator issue.

Admins can register internal URLs. URL syntax checks reject user-info/query/fragment
and some invalid headers, but there is no comprehensive SSRF allowlist or egress firewall.
The process also parses upstream metadata before some publication limits apply. Trusted
admin registration and careful review remain necessary; arbitrary hostile servers are not
safe to add merely because the gateway has timeouts.

Members share one store. One member can change data another reads and consume shared
model/CPU capacity. There is no tenant isolation or rate limiting. Server-side identity
and shared audit records prevent trusting browser-supplied user IDs, but audits do not
undo an action. In-flight calls may finish after revocation/disable.

## Network persistence and audit limits

Three NetworkPolicies restrict MCP ingress to gateway pods; Woo independently checks
its service token. A fourth policy restricts PostgreSQL. Live tests showed allowed
gateway traffic and denied non-gateway traffic to Woo, Policy and PostgreSQL. Pod-label
privileges can defeat label-based segmentation; this is not a defense against cluster admins.
Internal HTTP is unencrypted and local Ingress is HTTP. No real VPS TLS test is claimed.

Audit events store user/server/tool/time/duration/outcome, not request arguments,
results, customer contacts, credentials or hashes. START is committed before execution;
unknown outcomes are not silently replayed. Invalid/revoked keys are rejected before
invocation auditing; the evidence report preserves their HTTP rejection separately.

PostgreSQL and gateway pod replacement preserved identity, revocation and audit data.
Store persistence was verified in the earlier store milestone, with original claims
still retained. Local-path volumes remain tied to the local node; deleting a PVC can
delete its PV data. No backup/restore, disk-loss recovery, production key rotation or
high-availability claim is made. Database owner/superuser separation is not hardened.

Implemented hardening also includes non-root/read-only custom app containers, dropped
capabilities, no privilege escalation and no API service-account token mounts. These
support the core; they do not constitute completion of all optional security bonuses.
Detailed historical analysis remains in [threat-model.md](threat-model.md).

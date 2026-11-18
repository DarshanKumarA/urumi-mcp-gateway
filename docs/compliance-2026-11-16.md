# Final mandatory compliance rehearsal — 16 November 2026

The two remaining strict implementation gaps are closed and the local two-user flow
has been rehearsed on Helm revision **13**. The user will record the video.
Recording, narration and form submission have not been performed by this work.

**18 November recheck:** revision 13 remains deployed, all eight workloads are Ready,
the original three PVCs are Bound, and fresh discovery returns all seven tools from
three enabled/Connected upstreams. No new product/order was created during that
read-only recheck. Order 33 belongs to 16 November, not the current recording date.

## Changes and migration

Registry credential values now live in the external Opaque Secret
`urumi-upstream-credentials`. PostgreSQL's existing `credential_value` column stores
opaque `k8s-secret:` references. Gateway and migration/bootstrap Jobs use an explicitly
projected one-hour token and get/update RBAC limited to that one Secret. There is no
Secret list/create/delete permission. Other credential boundaries remain unchanged.

Old gateway writers were stopped for migration. The existing Woo credential was
copied, read back and privately compared before the database was transactionally
updated. The active registry then contained **zero raw credential values**. Original
application Secrets, three PVC identities, users and prior audits were preserved;
only the new credential Secret was added. Schema: `0004_secret_refs_rejections`.
Gateway/dashboard: `stage8.7-compliance`; Woo remains `stage8.4-order-analysis`.

A matching stored hash identifies a revoked key or disabled member without granting
authorization. These requests now create completed failed `KEY_REJECTED` audit rows
before 401. Only trusted cached tool metadata is recorded; other requests use
`<authentication>`. No arguments/raw keys/arbitrary requested names are stored and no
upstream is dispatched. Audit failure returns 503 and still blocks execution. Unknown
or malformed keys return 401 without a guessed owner. The dashboard displays
**Key rejected; no tool executed**.

## Live acceptance

| Check | Observed result |
| --- | --- |
| A: dashboard `urumiadmin` | SKU lookup → create product **32**, published Urumi Final Rehearsal Bottle 2026-11-16, INR 549 |
| Guest storefront | COD order **33**, one bottle, **INR 549**, Processing; confirmed in WooCommerce admin |
| A: today's orders | Woo `list_orders` → Arithmetic `sum_amounts`; total/average **INR 549**; complete pagination and Asia/Kolkata date window |
| B: external conversation | Official **MCP Inspector 2.15.0** with separate OpenRouter `z-ai/glm-5.3-flash` prompt driver; B's own key discovered seven tools and composed Woo → Arithmetic with the same answer |
| Disable/restore Policy | Absent from session chat and Inspector catalogs; six tools while disabled, seven after enabling/refreshing |
| Dead Policy | Deleted its Pod and used a bounded zero-replica interval. Unreachable / `UPSTREAM_UNAVAILABLE`; Policy absent, Inspector Policy attempt failed, Woo still returned order 33 and Arithmetic returned 549 |
| Recovery | Restored one replica, waited for rollout, refreshed discovery: Policy Connected, seven tools |
| Revoke B | Next direct `tools/call`: **401 UNAUTHENTICATED**; failed `KEY_REJECTED` event under `rehearsal_verified_b_20261116`, known Woo tool, duration 0 ms; no dispatch |
| Audit UI | A's product/order/calculator calls, B's external successes and B's rejection visibly attributed |
| Credential lifecycle | Temporary disabled registration: bearer create, static-header edit, clear, remove. Privately verified Secret value/reference equality; no value in read DTOs; final GET 404 |
| RBAC | Designated Secret get/update allowed; PostgreSQL Secret read, Secret list and designated Secret delete denied |
| Cleanup | All three `rehearsal_*` members disabled, zero active keys; temporary registration removed; three original upstreams enabled/Connected |
| Health/persistence | Eight workloads healthy; original MariaDB/WordPress/PostgreSQL claims Bound; product 32/order 33 retained |
| Navigation | Chat conversation remained intact after visiting Audit and returning |

The decisive B run used `rehearsal_verified_b_20261116`. Earlier successful external
runs used `rehearsal_b_20261116` and `rehearsal_final_b_20261116`. An automation-host
timeout during the first Policy termination interrupted the operator harness; Policy
was restored and work continued with disposable members. That interruption was not
counted as an application pass. All these accounts/keys were cleaned up.

The unavailable Policy Inspector attempt failed before an invocation audit row was
created; it is not presented as a gateway-executed failed tool. Unit regressions cover
attributed tool failures. The revoked request above has its actual live audit row.

## Validation

| Check | Result and scope |
| --- | --- |
| Gateway `python -m unittest discover -s tests` | **215 passed**; Secret bounds/conflicts, migration preservation/idempotence, rejection attribution/no dispatch, fail-closed audit failure |
| Dashboard `npm test -- --run`, `npm run build` | **33 passed**, TypeScript/Vite passed |
| `python -m unittest discover -s tests/integration -p test_platform_secret_setup.py` | **6 passed** |
| Helm lint and `tests/integration/validate_chart.py` | Both overlays passed, **30 objects** each; Role/token/Secret checks, historical store/auxiliary objects preserved |
| PostgreSQL | Isolated real-PostgreSQL audit constraint upgrade/downgrade in a rolled-back temporary schema; live application migration reached 0004 |
| Release | Both images built/imported, revision 13 Jobs completed, workloads Ready |
| Repository | Links/anchors/tables and heuristic credential/contact scan checked before commit; assignment unchanged |

The updated standalone `postgres_smoke.py` uses the in-memory test credential store;
its full Docker fixture suite was not rerun in this release. The isolated PostgreSQL
migration exercise and actual deployment are the database evidence. The earlier
382-test whole-project baseline is historical, not revision 13's test count.

## Evidence and limits

[Sanitized acceptance JSON](evidence/2026-11-16/acceptance.json) contains concrete results
and relevant audit metadata. [Dashboard product evidence](evidence/2026-11-16/user-a-product-chat.jpg)
shows the retained live conversation. The rejected audit row was inspected in the UI
and is recorded in JSON. [Earlier acceptance](acceptance.md) remains the source for
live network enforcement and PostgreSQL/gateway/store replacement checks; those
replacement drills were not repeated solely for this release.

Secret entries are append-only: edits, removals and failed transactions can leave old
entries. This protects in-flight readers/recovery but makes capacity management and
cleanup operator work. Earlier WAL/backups/physical pages may retain old plaintext.
Kubernetes Secrets do not imply configured etcd encryption. Back up references and
Secret entries together. Old plaintext-reading images are unsafe rollback targets;
see the [migration runbook](production.md#credential-storage-migration).

Local HTTP and shared store authority remain. No real VPS/TLS, multi-store,
fresh-machine installation, backup restore, high availability or Claude Code/Cursor
validation is claimed. SMTP is absent; failed email notifications do not undo the
COD order. Successful prompts do not establish a universal LLM reliability rate.

## Next actions for the user

1. Follow [the recording guide](demo.md): separate A/B identities, a fresh B key and
   same-day synthetic order (or explicitly name 16 November for order 33).
2. Record the eleven Done checks and six explanation topics. Inspector plus the
   supplied prompt driver is rehearsed; no Claude subscription is required. Explain
   the two security changes and their limits in your own words.
3. Check the recording for credentials/customer details, verify reviewer access to
   repository/video links, then submit the assignment form yourself.

No additional optional feature or infrastructure migration is needed before recording.

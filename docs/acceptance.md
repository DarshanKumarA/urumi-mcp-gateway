# Final local acceptance

The mandatory local runtime flow passed on **14 November 2026**, with a member
dashboard/key and repeatable external-client check on **15 November 2026**.
The deployed application remains commit `a6665db`, Helm revision **7** in
`k3d-urumi-local`, namespace `urumi`. This completion change adds acceptance tooling
and documentation; it does not upgrade images, schema, chart values, or the store.

**The submission is not complete:** a narrated live demo video and submission through
the assignment form remain outstanding. No real VPS, TLS, multi-store deployment,
fresh-machine installation, backup restore, or load-test success is claimed.

## Live results

| Check | Observed evidence |
| --- | --- |
| User A product creation | Dashboard user `urumiadmin` asked for the named, priced product. The model called `woocommerce__list_products` before `woocommerce__create_product`. Product **30**, **Urumi Acceptance Bottle 2026-11-14**, SKU **URUMI-ACCEPT-20261114**, published at **INR 499.00**; verified on the storefront |
| Storefront checkout | Normal guest UI: product → cart → checkout → COD → Place Order. Order **31**, one product 30, free shipping, **INR 499.00**. Synthetic customer details only |
| Admin visibility | Signed into the existing WordPress administrator `urumi-admin`; order 31 displayed in WooCommerce admin as Processing, payment Cash on delivery, correct product and total |
| Today's orders and chat composition | On 14 November, A's dashboard prompt returned order 31 and called `woocommerce__list_orders` then `arithmetic__sum_amounts`; total and average **INR 499**. One page, `has_more=false`; Asia/Kolkata window `2026-11-13T18:30:00Z` inclusive to `2026-11-14T18:30:00Z` exclusive |
| User B external connection | Separate member `acceptance_b`, invited/enrolled through the real authenticated management API, generated their own key through the member session API. Official **MCP Inspector 2.15.0**, Streamable HTTP, discovered all **7 tools across 3 upstreams** using only the gateway endpoint and that key as MCP configuration |
| External model composition | A bounded OpenRouter `z-ai/glm-5.3-flash` prompt driver chose WooCommerce and then Arithmetic. Every execution used Inspector against `/mcp`; order 31, total/average INR 499. The driver did not contact upstream MCP servers or Woo REST directly |
| Member key UI | On 15 November, `acceptance_ui_b` signed into the browser, created **Recorded UI acceptance** from API Keys, and used that key in the repository's Inspector helper. An explicit **2026-11-14** prompt returned the same real order and arithmetic. The helper output and API-key audit attribution passed |
| Revocation | Admin revoked `acceptance_b`'s key: the immediate next tools/call returned **HTTP 401 UNAUTHENTICATED**; Inspector discovery also rejected it (auth failure classification 3). The UI-created key was separately revoked from the member dashboard; its next request also returned **401** |
| Disabled upstream | Store Policy disabled through admin API. Its tool vanished from both `/api/catalog` (the chat's catalog path) and Inspector discovery. Dashboard showed **Disabled**. A direct stale-name call returned `UPSTREAM_DISABLED`, with an attributed failed audit. Re-enabled and seven tools restored |
| Dead upstream | Deleted Store Policy pod UID `6349cb4d-72ce-4c72-8899-eb4b71c19a29`; discovery excluded its tool and the dashboard showed **Unreachable**. A brief scale-to-zero window made healthy-peer execution observable: Woo orders and Arithmetic calls succeeded, discovery completed in **781 ms**, and the dead tool returned `UPSTREAM_UNAVAILABLE` |
| Recovery | Restored the original one replica in a finally block. New policy pod UID `dc86889e-0775-48b8-b4ff-a5b83efeda19`; policy call succeeded and status returned to Connected |
| All five Woo tools | Product list/create via A's chat; orders/list/get via B's external client; order 31 changed Processing → On hold → Processing with expected-status guards. Historical order 12 was untouched |
| Registry controls and namespacing | Temporary `acceptance_registry` registration added, refreshed, edited, configured with a synthetic static header, and removed. Duplicate upstream `sum_amounts` appeared under two distinct slugs. Real service credential is never replaced. Header value absent from read DTO; fixture regression tests additionally prove routing and forwarding |
| Roles | Member API requests to server management, users, audits, and server creation returned **403**. Member self-service key creation and tool access succeeded. Members can invoke enabled write tools; granular tool permissions are not implemented |
| Audits | Dashboard displayed successful and failed calls with correct users, servers, tool names, timestamps, durations and outcomes. A uses `auth_source=session`; B uses `api_key`. The two external model-selected calls on 14 November have event IDs `50555d41-e42d-49db-880f-41fabd7cea8c` and `058d4ca0-b4ff-42c7-89b2-fd85913daf00`. The 15 November helper calls have IDs `29dab4d1-d0ba-45ad-a2b0-2e4bf462d8d1` and `9b83608c-7385-4286-8377-e92d0a0b6f51` |

Inspector itself is a protocol client, not an LLM chat app. The included
[prompt helper](../scripts/inspector-demo.py) supplies the model loop and invokes
the unmodified official CLI through [the bridge](../scripts/inspector-bridge.mjs).
Its LLM credential is separate from the two-value MCP configuration. Claude Code
was installed but signed out; the user has no Claude subscription. **Claude Code
and Cursor were not tested.** No subscription to either is needed for this flow.

Authentication failures are rejected **before** the tool handler, so revoked-key
requests and discovery do not create normal invocation audit rows. Their HTTP/client
evidence is recorded separately. Authenticated disabled/dead tool calls do create
failed audit rows. This is the existing Stage 5.4 audit boundary, not an assertion
that unauthenticated requests were attributed to a user.

## Security health and persistence

- All eight continuing workloads have readiness/liveness probes, CPU/memory requests
  and limits, and were Ready at the final local recheck. Revisioned bootstrap/migration
  Jobs are Complete; finite Jobs use deadlines and completion rather than service probes.
- Gateway reached all three MCP services and PostgreSQL. From the existing Arithmetic
  pod, Woo, Policy, and PostgreSQL connections were denied. A pod's connection to its
  own Arithmetic listener was allowed; no blanket self-traffic isolation is claimed.
- Woo MCP rejected both missing and invalid service credentials with **401**, even
  from the otherwise permitted gateway pod. Upstreams/databases are ClusterIP only;
  the two Ingresses publish store and gateway/dashboard paths.
- Read-only database checks found SHA-256 key verifiers and Argon2id passwords;
  no raw values/hashes were printed. Both acceptance API keys were revoked after use,
  and both disposable member accounts were disabled. All pre-existing Secrets were
  compared privately with their baseline and remained unchanged.
- PostgreSQL pod replacement changed UID `d5891c54-b89d-4003-bb8f-34a9e560727d` to
  `6f3c6669-8b23-4ff0-8089-827a92c6a4ba`. Schema `0003_audit`, users, revoked key,
  and **39 audit rows** survived. Gateway pod replacement changed UID
  `04c84f4f-d4fa-4aa8-93a1-a5ebaf2a9eb5` to `acd323f4-5e0f-4199-aef7-3f366b45f4a8`;
  the existing session, all seven tools, and audits survived. The member UI helper
  subsequently brought the audit count to **41**. Five further member-session read
  calls brought the final database/dashboard count to **46**; these are session calls,
  not use of a revoked API key. The final sanitized audit snapshot records both sources.
- The original claims remain Bound: MariaDB `d3e6142a-b6b9-4e67-8880-a564f41ba331`,
  WordPress `864a302a-0a39-4880-b522-558a4c830845`, PostgreSQL
  `1ae6049c-9b0e-4545-9b8a-39b9e7a7f76d`, each still using its original `pvc-<UID>` PV.
  Earlier Stage 3 evidence covers WordPress/MariaDB pod replacement. This run did
  not repeat destructive storage tests, replace Secrets, recreate the cluster, or
  run Helm upgrade/rollback.
- A final Policy-pod connection check also denied access to Arithmetic, Woo and
  PostgreSQL, completing peer checks for all three MCP listeners.
- Host RAM was low during the first run (about 1.05 GiB free at one sample). No
  additional cluster workload was deployed and no resource budget was reduced.
  These successful functional checks do not prove peak capacity or production sizing.

## Regressions and evidence limits

| Validation | Result |
| --- | --- |
| Gateway tests | **202 passed**, run from `apps/gateway` with `PYTHONPATH=src` |
| Woo MCP tests | **120 passed** |
| Arithmetic tests | **21 passed** |
| Policy tests | **15 passed** |
| Dashboard | **24 passed**; TypeScript check and Vite build passed |
| Helm | Local and production lint passed; each **27-object** render passed live Kubernetes v1.35.5 schema and resource/security/Secret/Ingress/storage checks |
| Source preservation | Historical store/auxiliary resource comparisons passed; original assignment DOCX SHA-256 remains `e9f7e797d72c331ab508d75135490644c99b9bf2c172f36225ad861926d02f92` |
| Inspector helper | Real model-selected external Woo → Arithmetic calls passed using the UI-created member key and supported portable Node **22.23.4**; no global Node upgrade |
| Final repository checks | Python/npm lock consistency and dependency checks passed; **239** local documentation links/anchors/tables passed; source/built-asset credential/contact scan, helper syntax checks and Git whitespace checks passed. The unrelated untracked file was excluded without reading it |

The first gateway test invocation from the repository root failed one readiness
test because Alembic configuration is relative to the gateway directory. Running
the full suite from the application directory passed all 202 tests. The documented
test command is corrected; no application fix or image rebuild was needed.
An initial PostgreSQL readiness wait ran before the replacement pod existed; the
subsequent explicit creation and readiness waits passed. Neither observation is
hidden as a successful first attempt.

Screenshots and sanitized machine-readable results are in
[evidence/2026-11-14](evidence/2026-11-14). Screenshots show real UI state; they are
**not a substitute for the required narrated live video**. Only synthetic checkout
contact/address data appears in the order screenshots. No credentials are included.

## Remaining submission work

1. Record the [demo checklist](demo.md) live with an administrator and a separately
   invited member whose password the operator controls. The disposable acceptance
   identities are not login credentials for a reviewer.
2. Review the recording for exposed keys, passwords, real customer data and unsupported
   claims. Explain the implementation in your own words; the assignment requires understanding.
3. Publish the video where the reviewer can view it, then submit its URL and the GitHub
   repository through the [assignment form](https://forms.gle/nftwgyNeenSDmiRb6).

Email delivery is not configured: Woo recorded notification failures, while checkout,
order storage, admin visibility and MCP retrieval succeeded. SMTP setup is outside
this mandatory runtime acceptance. Today is date-sensitive: after 14 November use
the explicit date to inspect order 31, or place a new authorized demo order when
recording the live "today" flow.

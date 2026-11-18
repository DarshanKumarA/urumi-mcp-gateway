# Manual feature testing

This guide is for a tester using the current local single-store deployment. Complete
the cases in order, recording actual results in the [results template](manual-results-template.md).
Expected results are instructions, not evidence that your test passed.

## Setup and test data

For a new machine, complete the [root README](../../README.md) first. On the existing
project machine, start Docker and the existing `urumi-local` cluster if stopped;
do not recreate the cluster or rerun fresh-store installation. From the repository root:

```powershell
git rev-parse HEAD
kubectl --context k3d-urumi-local -n urumi get deployment,statefulset,pvc,ingress
helm list --kube-context k3d-urumi-local -n urumi
```

Expected baseline: six Deployments plus two StatefulSets Ready, three Bound PVCs,
and store/gateway Ingresses. The last acceptance used revision 13. Record the actual
revision rather than hard-coding it as a requirement for later releases.

| Item | Use |
| --- | --- |
| Dashboard | `http://gateway.urumi.test:8080` |
| Storefront / Woo admin | `http://store.urumi.test:8080` / `/wp-admin` |
| External endpoint | `http://gateway.urumi.test:8080/mcp`, Streamable HTTP, Bearer key |
| User A | Gateway admin, normally `urumiadmin`; chosen setup password, no default |
| User B | Fresh invited member, for example `qa_b_20261118_01`; use your actual run date/suffix |
| Woo administrator | `urumi-admin`; a different account/password from the gateway |
| Product | Unique name and SKU, for example `QA Bottle <RUN_ID>` / `QA-<RUN_ID>`; INR 549 |
| Customer | Synthetic name/address, email under `example.test`; COD, no card/payment gateway |

Use separate browser profiles/private windows for A and B; tabs in one profile share
cookies. Keep a run ID such as date plus a counter. Record IDs after creation.
Historical order **31** belongs to 14 November 2026 and **33** to 16 November 2026;
neither is a “today” order on a later date. Existing store data must be preserved.
Provider questions consume credit. Enter passwords/keys only in masked setup/client
prompts, never in Chat, command arguments, screenshots or the results file.

## Quick checks (no new business records)

### MAN-01: Login and access boundaries

1. Open the dashboard while signed out. Confirm that protected sections require login.
2. Submit one deliberately wrong password; expect a generic login failure and no access.
3. Sign in as A using the correct gateway credentials. Expect the correct username and
   admin navigation: Chat, Servers, Team, API Keys and Audit.
4. Open storefront Shop without a gateway/store customer login. Expect published products.

**Record:** successful/failed access outcomes, never credentials. This covers basic
identity and public storefront boundaries (REQ-TEAM-01, REQ-STORE-01).

### MAN-02: Server catalog and tools

1. As A, open Servers and use each server's refresh action.
2. Check WooCommerce, Arithmetic and Store Policy are enabled and Connected.
3. Inspect tool lists: five Woo tools, one Arithmetic and one Policy; seven total.

**Expected:** names include `woocommerce__list_products`, `woocommerce__get_order`,
`woocommerce__list_orders`, `woocommerce__create_product`,
`woocommerce__update_order_status`, `arithmetic__sum_amounts`, `store_policy__get_policy`.
Cached tool details are not proof that a disabled/unreachable tool is callable.
Health is observation-driven; refresh after changes (REQ-GW-02/03, REQ-UI-01).

### MAN-03: Chat input, pending reply and navigation

1. Type `List the first five products. Show their IDs, names and prices in a table.`
2. Press Shift+Enter: expect a new line without submission. Press Enter: expect one send.
3. While waiting, confirm your message is immediately visible and the teal typing
   bubble is present. Send should prevent duplicate submission while busy.
4. Visit Servers, then return to Chat before or after completion. Expect the same
   message, draft/completed reply and tool activity without a second request.
5. Confirm the reply is readable, table headers align with data, and long content
   can be scrolled on a narrow screen. Use a normal desktop window for table review.
6. Try Clear conversation. Expect the displayed turns to disappear. Sign out/in and
   confirm another user does not inherit this conversation.

**Limits:** reload/tab closure clears the conversation. Displayed history is retained
across section navigation, but each submitted prompt has independent model context.
Repeat the necessary IDs/date in follow-up prompts. If a reply finishes too quickly
to observe animation, mark that observation NOT OBSERVED, not failed or invented.
Wording/formatting guidance is not a guarantee of identical model prose (REQ-CHAT-01/02).

### MAN-04: Existing orders, pagination and product ranking

Use an explicit date with known test records, or “today” after MAN-07:

> For 2026-11-16, list the orders with IDs, status, currency and totals. Verify pagination. Use WooCommerce and Arithmetic to calculate total and average order value. State the store timezone and date scope.

**Expected for the preserved acceptance day, if unchanged:** order 33, INR 549 total
and average. If someone added/changed orders, compare the actual complete matching
set; do not force the historical answer. Tool activity must show Woo and Arithmetic.
For rankings, ask:

> For 2026-11-16, which product sold the most units, and what was the average order value? Include all pages, report ties, and show the quantity separately from the money value.

**Expected:** quantities come from line items; average order value is total order
money divided by order count, not units or product prices. Verify IDs/quantities in
Woo admin. Partial pages must not be claimed as a complete ranking. Broad histories
can exceed bounded tool/result limits; narrow the date scope instead of assuming an
error means no orders. On a verified empty date, expect zero orders and an undefined
average, not fabricated data (REQ-WOO-03/04/05, REQ-CHAT-01).

## Full acceptance (creates demo data)

### MAN-05: Invite B and create B's own key

1. A: Team → Invite member → enter the unique member username → Create invitation.
2. Privately give the one-time token to B. B clicks **Have an invitation?** on the
   signed-out screen, enters the token and chooses a password.
3. B signs in. Expect member access to Chat, Servers and API Keys; admin Team/Audit
   and server-management actions must not be usable. A member can still invoke
   enabled store write tools; “member” does not mean read-only store authority.
4. B: API Keys → Create API key → name it with the run ID → Create key. Privately
   retain the one-time value. Close/reopen the list; expect metadata/prefix only.
5. Reusing the accepted invitation must fail; do not create another account to hide it.

**Record:** B username and key label/ID, never key/token/password. A can view/revoke
B's keys from Team → View keys. Account disable is an API operator action, not a
button currently supplied by Team (REQ-TEAM-01 through REQ-TEAM-06).

### MAN-06: Create and verify a product through A's chat

> Check for SKU QA-<RUN_ID>. If it does not exist, create one published simple product named QA Bottle <RUN_ID>, price INR 549, in stock. If it exists, report it and do not create a duplicate.

Replace both placeholders before sending. Expect lookup then product creation (or
existing product reported), an actual product ID, correct price/status, and a public
storefront listing. Verify the item in Shop and Woo admin Products. If the response
is ambiguous, inspect by SKU before retrying; a write may already have happened
(REQ-WOO-06, DEMO-03). Keep the created product as evidence; do not delete old products.

### MAN-07: Guest COD checkout and Woo admin verification

1. In the anonymous storefront, add the MAN-06 product to cart. Confirm quantity/price.
2. Go to checkout, use synthetic customer details and Cash on Delivery, then Place order once.
3. Record the order ID, currency, total, payment method and status.
4. Sign in to Woo admin, open WooCommerce → Orders → that order. Compare its product,
   quantity and totals with the confirmation page.

**Expected:** persisted COD order. One unit at INR 549 with free shipping/no extra
charges totals INR 549; verify actual shipping/tax settings rather than assuming them.
Local SMTP is unconfigured, so an email notification failure does not mean checkout
failed. Do not publish the private order-confirmation URL/key (DEMO-01/02).

### MAN-08: Today's retrieval and cross-upstream composition

Ask A's chat:

> What orders came in today, and what are their total and average order values? Use WooCommerce and Arithmetic. Include IDs, pagination and the store's timezone.

**Expected:** the new order is included for the actual Asia/Kolkata date. Verify the
complete returned set against Woo admin. Total = sum of matching order totals;
average = total / matching order count. Do not assume your order is today's only
order. Require actual successful calls to both `woocommerce__list_orders` and
`arithmetic__sum_amounts`; model-written arithmetic alone does not pass (DEMO-04/07).

### MAN-09: External MCP client as B

Install the pinned Inspector dependencies from [the demo guide](../demo.md#external-prompt-through-mcp-inspector).
From the repo root, run:

```powershell
apps/gateway/.venv/Scripts/python scripts/inspector-demo.py --discovery-only
apps/gateway/.venv/Scripts/python scripts/inspector-demo.py
```

Enter B's key at the masked prompt. The second command also prompts for the separate
OpenRouter key used by the model driver; it is not an upstream credential or MCP key.
**Expected:** seven namespaced tools, the same dated order set, Woo → Arithmetic
calls and correct totals. The transport client needs only gateway URL plus B's key.
No Claude subscription is required. Save reviewed result lines only; no full terminal
transcription during credential entry (DEMO-05/06/07).

### MAN-10: Disable and restore an upstream

1. Keep B's key active. A disables **Store Policy** in Servers.
2. Refresh its status. B refreshes Servers (the session catalog) and reruns Inspector
   discovery. Expect Policy absent from both live catalogs; six tools remain.
3. Ask a new policy-only chat question. The agent must not successfully invoke the
   disabled tool; prose guessed without a tool call is not a successful tool test.
4. A enables Policy and refreshes it; repeat both catalog checks. Expect seven tools
   and Connected. A read-only Policy question should show a successful Policy call.

**Cleanup:** always re-enable/refresh Policy. Capture both disabled and restored
states. Disabled is different from unreachable (DEMO-09).

### MAN-11: Dead upstream isolation and recovery

This deliberately interrupts only Policy. Run during a test window. First observe
the current Policy Pod name and delete only that Pod:

```powershell
kubectl --context k3d-urumi-local -n urumi get pods -l app.kubernetes.io/component=store-policy-mcp
# Replace the placeholder with the observed Policy Pod, not a database or PVC.
kubectl --context k3d-urumi-local -n urumi delete pod <observed-policy-pod>
```

If replacement is too fast to observe Unreachable, use this controlled pause:

```powershell
$policyReplicas = kubectl --context k3d-urumi-local -n urumi get deployment urumi-store-policy-mcp -o jsonpath='{.spec.replicas}'
if ($LASTEXITCODE -ne 0 -or $policyReplicas -notmatch '^\d+$' -or [int]$policyReplicas -lt 1) { throw 'Check baseline before outage' }
try {
    kubectl --context k3d-urumi-local -n urumi scale deployment/urumi-store-policy-mcp --replicas=0
    if ($LASTEXITCODE -ne 0) { throw 'Scale failed' }
    kubectl --context k3d-urumi-local -n urumi wait --for=delete pod -l app.kubernetes.io/component=store-policy-mcp --timeout=90s
    if ($LASTEXITCODE -ne 0) { throw 'Outage not established' }
    Read-Host 'Refresh Servers and run A/B Woo-Arithmetic checks now; press Enter to restore'
} finally {
    kubectl --context k3d-urumi-local -n urumi scale deployment/urumi-store-policy-mcp --replicas=$policyReplicas
    kubectl --context k3d-urumi-local -n urumi rollout status deployment/urumi-store-policy-mcp --timeout=120s
}
```

During the pause refresh Policy in A's Servers: expect Unreachable. B discovery
excludes Policy, but Woo/Arithmetic order questions still succeed. Restore, refresh
and confirm Connected/seven tools. If you stop the terminal itself, manually restore
the recorded replica count; `finally` cannot survive a killed process. An Inspector
client may refuse a missing tool before dispatch; don't invent a gateway failure
audit for a call it never sent (DEMO-10).

### MAN-12: Revoke B and verify rejection auditing

1. Make one successful external call using B's active key.
2. A: Team → B → View keys → revoke that key and confirm. Alternatively B revokes
   their own key from API Keys; record which path you used.
3. Immediately rerun Inspector discovery using that same old key. Expect authentication
   failure (401), no catalog and no upstream business action.
4. A opens Audit and refreshes. Expect B's earlier successes and a failed
   **Key rejected; no tool executed** (`KEY_REJECTED`) event under B.

Inspector starts with initialization/discovery, so the rejected event may have tool
`<authentication>`. A direct rejected `tools/call` for cached known metadata can name
the actual tool. Unknown random credentials cannot be attributed to an invented user.
Do this after all other B calls; revoked keys are not re-enabled (DEMO-08/11).

## Remaining feature checks

### MAN-13: All five Woo tools, including guarded status update

The earlier cases exercise list products, create product and list orders. To cover
details, ask `Get order <YOUR_DEMO_ORDER_ID> and show its line items and status.`
Require `woocommerce__get_order` and compare to Woo admin.

On **your synthetic order only**, read its current status and ask explicitly to move
it from that expected status to `on-hold`. Require `woocommerce__update_order_status`;
confirm in Woo admin, then restore the original permitted status with a second
explicit guarded request. Status changes can trigger Woo hooks/notifications. Never
retry an unknown write outcome without checking the store. Stale expected-status
rejection is covered by fixture tests; an LLM may reread/correct an intentionally
stale prompt, so that is not a deterministic negative test (REQ-WOO-03 through 07).

### MAN-14: Registry add/edit/credential/namespace/remove

1. A: Add server. Use a unique slug such as `qa_policy_01`, display name `QA Policy`,
   and endpoint `http://urumi-store-policy-mcp.urumi.svc.cluster.local:8000/mcp`.
   Choose No credential and Save server, then refresh.
2. Expect a separate `qa_policy_01__get_policy` tool alongside the original Policy
   namespace, not a name collision. Temporarily eight tools should be discoverable.
3. Disable this **temporary registration**. Edit its display name; slug stays immutable.
4. Edit Credential → Replace with Bearer token; use the non-secret fixture text
   `SYNTHETIC-TEST-ONLY`. Save/reopen: expect configured credential metadata and no
   returned value. Repeat with static header `X-QA-Token` and another synthetic value.
5. Choose Remove credential and save; expect no configured credential. Remove only
   the temporary registration and confirm. Catalog should return to seven tools.

This checks credential storage/readback UI, not authentication enforcement at Policy
(Policy has no credential requirement). Do not alter the real Woo registration or
replace its service token. Credential entries are retained in the Secret even after
registration removal; do not manually empty it (REQ-GW-01/03/05).

### MAN-15: Audit and useful errors

As A, filter Audit by succeeded/failed and inspect pagination. Match A's session calls
and B's API-key calls, server/tool, timestamp, duration and outcome with your notes.
Audit rows omit request/result payloads and credentials. Product/order creation
through the storefront itself is not a gateway tool invocation.

For a failed chat, record only the visible troubleshooting code, prompt with no
secrets, tool names/outcomes and timestamp. A provider error after a successful tool
does not undo that tool. Don't repeatedly submit product/order writes to “fix” it.
Credit/auth/provider outages, call limits and tool failures have different causes.
Do not deliberately remove production provider keys to manufacture a UI error.
This covers REQ-AUD-01 and REQ-CHAT-02; retain the actual failed attempt as evidence.

## Operator checks

### OPS-01: Kubernetes configuration and credential boundary

Inspect workload readiness, both Ingresses, ClusterIP-only upstreams/databases,
requests/limits, probes and PVC identities. For the credential-store Role:

```powershell
kubectl --context k3d-urumi-local -n urumi get role urumi-credential-store -o yaml
kubectl --context k3d-urumi-local -n urumi auth can-i get secret/urumi-upstream-credentials --as=system:serviceaccount:urumi:urumi-credential-store
kubectl --context k3d-urumi-local -n urumi auth can-i update secret/urumi-upstream-credentials --as=system:serviceaccount:urumi:urumi-credential-store
kubectl --context k3d-urumi-local -n urumi auth can-i get secret/urumi-postgres-auth --as=system:serviceaccount:urumi:urumi-credential-store
kubectl --context k3d-urumi-local -n urumi auth can-i list secrets --as=system:serviceaccount:urumi:urumi-credential-store
```

Expected answers: yes, yes, no, no. A tester without impersonation rights should
mark BLOCKED, not change RBAC. Do not print/decode Secret objects or query raw registry
values. Unit tests and the dated migration evidence establish the reference format.
This supports REQ-SEC-01 and REQ-K8S-03 through REQ-K8S-07.

### OPS-02: Live network enforcement

Inspect the four NetworkPolicies first. Test TCP from gateway to each internal service
(expected reachable), then from Policy to Woo/Arithmetic/PostgreSQL (expected denied):

```powershell
@'
import socket
for host,port in [('urumi-woo-mcp',8000),('urumi-arithmetic-mcp',8000),('urumi-postgres',5432)]:
    try:
        with socket.create_connection((host,port),timeout=3): pass
        print(host, 'TCP reachable')
    except OSError:
        print(host, 'TCP denied or unavailable')
'@ | kubectl --context k3d-urumi-local -n urumi exec -i deployment/urumi-store-policy-mcp -- python -
```

Repeat from `deployment/urumi-gateway` for the positive control. To check Policy's
ingress, probe `urumi-store-policy-mcp:8000` from Arithmetic and from Gateway. A
negative result alone does not prove policy enforcement: confirm the peer is healthy
and the gateway positive control succeeds. TCP reachability does not prove MCP auth.
Record allowed/denied destinations, not tokens (REQ-WOO-08).

### OPS-03: Restart persistence (maintenance window only)

Record PVC UIDs, member/key metadata and audit IDs/count first. Restart only the
gateway Deployment, wait for rollout and verify the existing identity/catalog/audits.
On an isolated test installation, replacing `urumi-postgres-0` and waiting for the
StatefulSet also checks persisted gateway state; expect a temporary gateway outage.
Recheck original PVC UIDs and the same records afterward. Existing store replacement
evidence is in [acceptance](../acceptance.md); do not delete PVCs, uninstall Helm or
recreate the cluster. Restart survival is not a backup/restore or disk-loss test.
This is the controlled persistence check for REQ-K8S-04.

## Cleanup and sign-off

Restore Policy enabled/Connected at its original replicas, remove only the temporary
registry entry, restore the demo order's status, revoke disposable keys and sign out
test sessions. Keep clearly labelled products/orders as evidence. Record any cleanup
that is blocked. Final baseline: eight healthy workloads, three original Bound PVCs,
three enabled/Connected upstreams and seven tools.

To disable the disposable member account, an operator uses the admin-only
`POST /api/users/{user_id}/disable` with an authenticated admin session and same Origin.
Verify the exact non-admin test user ID first. This API operation has no dashboard
button; do not claim an account is disabled just because its key was revoked.
Never remove historical users/audits to make the interface look clean.

For an operator who needs that cleanup, this PowerShell example uses a masked admin
login and a session held only in memory. Replace the test username first, run without
transcription, and do not print the request body or session:

```powershell
$qaOrigin = 'http://gateway.urumi.test:8080'
$qaMemberName = 'REPLACE_WITH_YOUR_TEST_MEMBER'
$qaSession = $null
$qaCredential = Get-Credential -UserName urumiadmin -Message 'Gateway administrator'
try {
    $qaBody = @{username=$qaCredential.UserName; password=$qaCredential.GetNetworkCredential().Password} | ConvertTo-Json
    $null = Invoke-RestMethod -Method Post -Uri "$qaOrigin/api/auth/login" -Headers @{Origin=$qaOrigin} -ContentType 'application/json' -Body $qaBody -SessionVariable qaSession
    $qaBody = $null
    $qaUsers = Invoke-RestMethod -Uri "$qaOrigin/api/users" -WebSession $qaSession
    $qaMember = @($qaUsers | Where-Object { $_.username -eq $qaMemberName -and $_.role -eq 'member' })
    if (@($qaMember).Count -ne 1) { throw 'Exact disposable member not found; nothing disabled' }
    $null = Invoke-RestMethod -Method Post -Uri "$qaOrigin/api/users/$($qaMember.id)/disable" -Headers @{Origin=$qaOrigin} -WebSession $qaSession
    Invoke-RestMethod -Uri "$qaOrigin/api/users/$($qaMember.id)" -WebSession $qaSession | Select-Object username,role,enabled
} finally {
    $qaBody = $null
    $qaCredential = $null
    if ($qaSession) { $null = Invoke-RestMethod -Method Post -Uri "$qaOrigin/api/auth/logout" -Headers @{Origin=$qaOrigin} -WebSession $qaSession }
    $qaSession = $null
}
```

Expect `enabled` false for that member. Revoke its keys first; disabling alone does
not permanently revoke them if the member is re-enabled later.

Mark every selected case PASS, FAIL, BLOCKED or NOT RUN with observed evidence.
Record unresolved issues with reproduction steps; keep failed attempts. Narrated
video, submission, real VPS/TLS, multi-store and backup restore remain separate claims.

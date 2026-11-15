# Demo and submission checklist

The local acceptance results are in [acceptance.md](acceptance.md). This guide is the
recording plan, not a claim that a video has been recorded or submitted. Use a new
authorized test product/SKU and order when recording the "today" sequence; product 30
and order 31 belong to **14 November 2026**. Preserve historical data.

## Before recording

1. Start the existing Docker Desktop/k3d cluster if stopped. Do not recreate it.
   Confirm context `k3d-urumi-local`, namespace `urumi`, eight workloads Ready, three
   Bound PVCs, and three Connected upstreams. Current Helm revision is 8.
2. Open `http://gateway.urumi.test:8080` and `http://store.urumi.test:8080`.
   The WordPress administrator is **urumi-admin**; the gateway administrator is
   **urumiadmin**. They have different passwords. Use the existing credential manager
   or protected Kubernetes Secret access; never print credentials into the recording.
3. In gateway **Team**, invite a fresh member username. Use the one-time invitation
   link privately and let the member set their password. Sign in as that member and
   create a named key under **API Keys**; save it privately before closing the dialog.
   The disposable `acceptance_b` and `acceptance_ui_b` users are evidence identities,
   not supplied reviewer logins. Their accounts are disabled and test keys revoked.
4. Keep A and B sessions separate, or explicitly sign out/in when switching. Browser
   tabs in one profile share cookies. A's chat must show the admin username; the
   external key must belong to B. Do not put gateway keys in chat prompts.
5. Prepare Inspector and the external prompt helper below, then hide secret-entry
   screens before recording. No Claude subscription is required.

## External prompt through MCP Inspector

The [official Inspector CLI](https://github.com/modelcontextprotocol/inspector/blob/main/clients/cli/README.md)
is one of the assignment's explicitly permitted external clients. Inspector runs MCP
discovery/calls; the helper supplies a bounded read-only model loop using OpenRouter.
The MCP client receives only the gateway URL and B's API key. The separate OpenRouter
key belongs to the prompt driver and is never sent to the gateway or any upstream.

From the repository root in PowerShell, with the gateway virtual environment already
installed as described in [its README](../apps/gateway/README.md):

```powershell
# Isolated demo dependencies; .venv and node_modules are ignored by Git.
npm install --prefix .venv/inspector --no-audit --no-fund @modelcontextprotocol/inspector@2.15.0 node@22.23.4

# Lists all enabled tools. Enter B's key at the masked prompt.
apps/gateway/.venv/Scripts/python scripts/inspector-demo.py --discovery-only

# Asks for B's key and the driver OpenRouter key without echoing either.
apps/gateway/.venv/Scripts/python scripts/inspector-demo.py
```

The helper uses the locally installed Node 22.23.4 executable, avoiding changes to
global Node. Installation needs registry access. Its supported paths can be overridden
with `--node` and `--inspector`; no credential command-line flags exist. Never redirect
a credential file into `--stdin-credentials`; that option is reserved for an in-memory
automation pipe. Secrets are not stored by the helper, although managed process memory
cannot be reliably erased. Do not enable shell transcription, debugger dumps or wire logs.

Expected nonempty run: seven discovered tools; `woocommerce__list_orders`; then
`arithmetic__sum_amounts` with returned totals; final answer matching order IDs/currency
and verified pagination. An empty day legitimately has no average. For the preserved
acceptance order, use:

```powershell
apps/gateway/.venv/Scripts/python scripts/inspector-demo.py --prompt "For 2026-11-14, list orders and compute their total and average using WooCommerce and Arithmetic. Verify pagination and state the timezone."
```

The helper prints real result/trace JSON, never credentials. It allows only the five
known read tools, caps tool rounds/calls, and stops on tool failure without retries.
The shared OpenRouter adapter may retry transient model generation once. The
dashboard retains separate write-capable chat behavior. Claude Code/Cursor compatibility
is not claimed by the Inspector evidence.

## Recording sequence

| Step | Show and explain | Expected evidence |
| --- | --- | --- |
| 1 | System design: dashboard, gateway, three MCP upstreams, Woo REST, two databases; follow one call end to end | Use [system-design.md](system-design.md); explain MCP server/client roles and stored routing |
| 2 | As A in dashboard Chat, request a product with a unique SKU, name and price; first check the SKU | Product tool trace, published storefront product; do not repeat an ambiguous write |
| 3 | Guest storefront: add that product → cart → checkout with synthetic details → COD → Place Order | Confirmation number, correct item/total, COD; no customer account login required |
| 4 | Open WooCommerce admin Orders, then A's chat: "What orders came in today, and what are their total and average order values?" | Same order in admin/chat; Woo and Arithmetic tool traces; Asia/Kolkata date window |
| 5 | As B, show own key metadata with the value hidden; run Inspector discovery and the prompt helper | All three upstreams/seven tools; same order; model-selected Woo → Arithmetic composition |
| 6 | Disable Store Policy in A's Servers actions; refresh B's Inspector and the live chat catalog | Disabled in UI; Policy absent from both catalogs. The chat's `/api/catalog` uses session authentication; never expose session cookies |
| 7 | Re-enable Policy and refresh; delete only its pod; show Unreachable and healthy-peer calls | Use the bounded failure sequence below; recover one replica, refresh and show Connected |
| 8 | Revoke B's key from Team/key controls or B's API Keys; immediately repeat discovery/call | 401/authentication failure. Create a new key only if further external calls are needed |
| 9 | Audit page: show A/session and B/API-key tool calls, outcomes and durations, including failure rows | Authenticated failures are audited. Explain that revoked requests are rejected before invocation auditing |
| 10 | Kubernetes: inspect workload/Ingress/PVC/Secret names, probes, budgets, NetworkPolicies | No Secret contents. Explain local HTTP, internal boundaries, retention versus backup |
| 11 | Production story, security and rollback | Use [production.md](production.md) and [security-summary.md](security-summary.md); clearly state that no real VPS or multi-store deployment was performed |

For the pod failure, first capture the exact current Policy pod name:

```powershell
kubectl --context k3d-urumi-local -n urumi get pods -l app.kubernetes.io/component=store-policy-mcp
# Substitute only the observed Policy pod name; never delete a database or PVC here.
kubectl --context k3d-urumi-local -n urumi delete pod <observed-policy-pod>
```

If automatic replacement is too fast to show a sustained outage, temporarily scale
**only** `urumi-store-policy-mcp` to zero, verify absence of its ready endpoints, then
run a Woo/Arithmetic prompt. Restore the previously observed replica count (one in
the accepted deployment) in a `finally` block, wait for rollout and refresh discovery.
Do not leave a disabled server, zero replicas, extra registration or active disposable
API key behind. A dashboard status is the last observation, so explicitly refresh
after recovery. The actual acceptance used this bounded approach successfully.

## Explanation checklist

- Explain why shared Woo credentials still permit a member to mutate store data,
  even though credential values stay hidden; basic roles govern management, not tools.
- Explain why user keys are never forwarded upstream, and what an administrator or
  malicious server could still do (SSRF, prompt injection, shared authority/resources).
- Explain namespacing, concurrent discovery, deadlines, stale metadata, immediate
  disabled filtering and the no-automatic-write-retry rule.
- Explain PostgreSQL identity/audit persistence, WordPress/MariaDB PVCs, bootstrap
  receipts, migration ordering, and why Helm rollback is not database rollback.
- Explain the exact model/provider and external data flow. Do not describe model-written
  arithmetic as composition without showing actual calls to both upstreams.

## Submission

- [ ] Record the complete live sequence with two different users and the six required
  video topics. Review it yourself and be ready to explain each component.
- [ ] Ensure the recording reveals no keys/passwords, real customer contact details,
  secret environment dumps, browser password suggestions or confidential terminals.
- [ ] Make the video accessible to the intended reviewer and check its link.
- [ ] Confirm the final GitHub commit and README match the demonstrated system.
- [ ] Submit the video and [repository](https://github.com/DarshanKumarA/urumi-mcp-gateway)
  through the [assignment form](https://forms.gle/nftwgyNeenSDmiRb6).

These boxes remain unchecked until the corresponding human recording/submission is
actually performed. No deadline or submission receipt is inferred from the assignment.

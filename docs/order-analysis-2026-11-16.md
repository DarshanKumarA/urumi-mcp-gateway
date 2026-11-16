# Order-analysis failure diagnosis

## 16 November: order-ranking fan-out correction

The exact user prompt reproduced `PROVIDER_INVALID_RESPONSE` after one successful
`woocommerce__list_orders`. A guarded, read-only diagnostic observed a valid model
response proposing 15 `get_order` calls; the adapter permits four per response.
This was a tool-budget failure, not malformed JSON or failed WooCommerce retrieval.

The existing paginated list now includes allowlisted product ID, variation, name
and quantity. This removes the per-order lookup requirement for quantity rankings.
Detail responses and input arguments remain unchanged. Pagination, the 64 KB chat
result ceiling, four-call batch and ten-call total limits remain enforced. Larger
queries may still require a narrower scope; partial pages must be labelled.
Over-budget OpenRouter batches now return `CHAT_CALL_LIMIT` with useful UI guidance.
No automatic tool replay was added.


## Validation

- Before: exact prompt failed after list_orders; diagnostic observed 15 valid get_order
  requests in one response. A separate diagnostic attempt encountered provider
  unavailability; this patch does not claim to cure provider outages.
- After: three consecutive authenticated live API prompts succeeded, each with
  list_orders → arithmetic__sum_amounts, no individual get_order calls.
- Independent Decimal/quantity computation through the audited gateway confirmed
  15 orders, no additional page, INR 7,985 total, mean INR 532.333333…
  (INR 532.33 rounded), and product 16 leading with 8 units; product 11 has 6,
  product 30 has 1. This is all dates/statuses, not today's sales.
- One model answer misstated an incidental status count; core ranking/average were
  correct in all three. These checks do not establish universal factual reliability.
- 122 Woo, 205 gateway and 29 dashboard tests passed (356 total); TypeScript/Vite
  build, Docker builds, Helm local lint and diff whitespace checks passed.
- Helm revision 10 deployed, all eight workloads ready. Manifest changes were only
  the three application images and standard revision-specific job/configmap names.
- All 10 application Secret contents/UIDs and three PVC UIDs/volume names unchanged.
  No store mutations were performed. UI interaction was not repeated for this fix;
  live acceptance used the same authenticated chat API as the dashboard.

## Remaining limits

The four-call batch, ten-call total, five-round, 64 KB tool-result and 180-second
chat bounds remain. Large pages can reach size limits; narrow scope/page size then.
Product rankings use ordered quantities, not net quantities after refunds. Cancelled
or refunded orders are included unless a status filter is requested; state scope.
The fix does not add an analytics engine, automatic retries of tool execution or
new model/provider fallback. Existing video/submission obligations remain pending.

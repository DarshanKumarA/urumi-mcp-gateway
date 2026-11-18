# Manual test run — fill in the date

Copy this file into your private run folder. This blank template is not a passed test report.
Keep credentials, cookies, invitation tokens, private order URLs and real customer details out.

## Run information

| Field | Actual value |
| --- | --- |
| Tester / run ID | TODO |
| Start / finish / timezone | TODO |
| Git commit / tracked changes present | TODO |
| Kubernetes context / namespace / Helm revision | TODO |
| App image tags / browser | TODO |
| A username / B username / B key label or ID | TODO; no key value |
| Product ID / SKU / order IDs | TODO |
| Date/status/currency scope used for totals | TODO |
| Baseline PVC UIDs / Policy replicas | TODO |
| Automated run folder / summary link | TODO |

## Results

Use PASS, FAIL, BLOCKED or NOT RUN. Include actual observations, not just a checkbox.
For failures, add sanitized reproduction steps, troubleshooting code, timestamp and
whether any tool/write already succeeded. Attach reviewed evidence by relative link.

| Case | Status | Actual result / evidence | Cleanup or issue |
| --- | --- | --- | --- |
| MAN-01 Login/access | NOT RUN | | |
| MAN-02 Catalog/tools | NOT RUN | | |
| MAN-03 Chat UX/retention | NOT RUN | | |
| MAN-04 Orders/ranking | NOT RUN | | |
| MAN-05 Invite/member/key | NOT RUN | | |
| MAN-06 Product creation | NOT RUN | | |
| MAN-07 COD/admin order | NOT RUN | | |
| MAN-08 Today's composition | NOT RUN | | |
| MAN-09 External B | NOT RUN | | |
| MAN-10 Disable/restore | NOT RUN | | |
| MAN-11 Dead upstream/recovery | NOT RUN | | |
| MAN-12 Revocation/audit | NOT RUN | | |
| MAN-13 Get/update order | NOT RUN | | |
| MAN-14 Registry lifecycle | NOT RUN | | |
| MAN-15 Audit/errors | NOT RUN | | |
| OPS-01 Resource/RBAC | NOT RUN | | |
| OPS-02 Network enforcement | NOT RUN | | |
| OPS-03 Restart persistence | NOT RUN | | |

## Cleanup and remaining work

- Policy enabled, original replica count restored, three Connected upstreams/seven tools: TODO
- Temporary registration removed; demo order status restored: TODO
- Disposable keys revoked / member disabled (separate states): TODO
- Test sessions signed out; original PVCs intact; business evidence retained: TODO
- Outstanding failures/blocked steps and owner: TODO
- Logs/screenshots reviewed for sensitive data: TODO
- Video/submission status (never infer from passing tests): TODO

## Failure or retry record

For each retry, retain the original failed result and record what changed, the new
timestamp and outcome. A successful retry does not turn the earlier attempt into PASS.

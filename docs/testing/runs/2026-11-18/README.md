# Automated test run — 18 November 2026

**Result: 412 tests passed; 16 checks passed, 0 failed, 0 skipped.**

Scope: fixture/unit/protocol/UI tests, two localhost TCP smoke checks, build, offline helpers and static configuration/repository checks. No live store or provider call, cluster change, checkout or Pod restart was performed.

Application source: `9f0aac5b5f34f06c3b7c7c031fea835be30fd120`. The working tree contained the new runner/logging changes. The [manifest](summary.json) records the dirty-tree flag and exact runner SHA-256; runtime app code was unchanged. New manual documentation was completed afterward and receives a separate final review.

Start (UTC): 2026-11-18T16:06:08.635819+00:00. Finish (UTC): 2026-11-18T16:07:58.968662+00:00.

Logs combine stdout/stderr. ANSI formatting was removed, repository/home paths normalized and common credential patterns redacted. Artifacts were reviewed before copying from the ignored local run directory. Final staging found CRLF/trailing whitespace in captured logs; published copies use LF with trailing spaces and extra end-of-file blank lines removed. The manifest retains each original collected hash alongside the published hash. These are collected outputs, not reconstructed summaries.

The manifest's `runner_sha256` identifies the runner at execution time. Its subsequent formatting-only fix was checked with synthetic CRLF/ANSI/redaction inputs; it did not rerun the application suites or alter their outcomes. Original collected files remain in the ignored local run folder.

| Check | Result | Unit/UI tests | Log |
| --- | --- | --- | --- |
| gateway-tests | PASS | 215 | [gateway-tests.txt](gateway-tests.txt) |
| woo-mcp-tests | PASS | 122 | [woo-mcp-tests.txt](woo-mcp-tests.txt) |
| arithmetic-mcp-tests | PASS | 21 | [arithmetic-mcp-tests.txt](arithmetic-mcp-tests.txt) |
| store-policy-mcp-tests | PASS | 15 | [store-policy-mcp-tests.txt](store-policy-mcp-tests.txt) |
| platform-secret-helper | PASS | 6 | [platform-secret-helper.txt](platform-secret-helper.txt) |
| dashboard-tests | PASS | 33 | [dashboard-tests.txt](dashboard-tests.txt) |
| dashboard-build | PASS | — | [dashboard-build.txt](dashboard-build.txt) |
| setup-store-secrets | PASS | — | [setup-store-secrets.txt](setup-store-secrets.txt) |
| setup-woocommerce-rest-secret | PASS | — | [setup-woocommerce-rest-secret.txt](setup-woocommerce-rest-secret.txt) |
| arithmetic-mcp-tcp | PASS | — | [arithmetic-mcp-tcp.txt](arithmetic-mcp-tcp.txt) |
| store-policy-mcp-tcp | PASS | — | [store-policy-mcp-tcp.txt](store-policy-mcp-tcp.txt) |
| helm-local | PASS | — | [helm-local.txt](helm-local.txt) |
| helm-prod | PASS | — | [helm-prod.txt](helm-prod.txt) |
| chart-schema | PASS | — | [chart-schema.txt](chart-schema.txt) |
| repository | PASS | — | [repository.txt](repository.txt) |
| git-whitespace | PASS | — | [git-whitespace.txt](git-whitespace.txt) |

The empty whitespace transcript is expected: exit 0 with no diagnostics. Gateway/HTTP negative-test messages and asyncio timing diagnostics can appear inside a passing suite; use the final test result and process exit code, not a substring search for “error,” to judge it.

Helper assertions and smoke commands are not added to the 412 unit/UI test total. Full Docker/PostgreSQL fixture runs, live acceptance and manual cases are outside this run; see the [scope inventory](../../README.md#additional-integration-checks-and-current-limits) and [history](../../test-history.md).

Reproduce with `py -3.13 scripts/run-tests.py --schema-file <v1.35.5-openapi-v2.json>` from the repository root after installing prerequisites. Use a new output folder; do not overwrite this archive. The manifest records the schema SHA-256. No run manifest or log contains credentials.

The [final documentation review](final-review.txt) was captured separately after the
new guide was staged. PowerShell syntax was checked for 11 fenced blocks (one
documented Pod-name placeholder substituted only for parsing); no live commands
were executed. The runner's refusal to overwrite an existing run was also checked:
exit 2 and the original manifest hash unchanged. These are additional handoff checks,
not extra application tests in the 412 total.

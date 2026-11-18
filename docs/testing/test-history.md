# Test history and evidence index

Dates identify when evidence was collected. A later document update does not rerun a
test. Full console logs were not retained for every early milestone; those rows link
the original result reports instead of reconstructed output.

## Current automated run

On **18 November 2026**, [the collected run](runs/2026-11-18/README.md) passed
**412 tests**: gateway 215, Woo 122, Arithmetic 21, Policy 15, dashboard 33 and
platform Secret helper 6. All **16 checks** passed, including the production build,
two offline PowerShell helper validations, two localhost TCP smoke checks, both Helm
lints, full chart schema validation and repository/whitespace checks. No check skipped.

Application source was commit `9f0aac5b5f34f06c3b7c7c031fea835be30fd120`.
The working tree had the new test-runner/logging changes; the manifest records this
explicitly and includes the runner hash. Application runtime source/images were unchanged.
The run used fixtures and offline configuration validation, not live business actions.

## Historical records

| Date / milestone | Recorded result | Evidence retained | Limit |
| --- | --- | --- | --- |
| October store/bootstrap milestones | Helper/bootstrap checks, guest store flow, Pod persistence and dependency-loss observations | [Progress record](../progress.md), [project journey](../project-journey.md) | Historical narrative/assertions; a complete raw console archive is not available |
| 14–15 November local acceptance | 382 application/UI tests; two-user live flow, product 30/order 31, revocation, network isolation and persistence | [Acceptance report](../acceptance.md), [structured evidence/screenshots](../evidence/2026-11-14/README.md) | Count is the old source baseline; screenshots do not replace a narrated video |
| 15 November reliability follow-up | 204 gateway, 27 dashboard, 5 helper tests; 10 before/10 after chat probes; live table/composition | [Report](../reliability-2026-11-15.md), [chat observations](../evidence/2026-11-15/chat-checks.json) | Full suite console transcripts not retained; small live samples do not establish a success-rate guarantee |
| 16 November order-ranking fix | 122 Woo, 205 gateway, 29 dashboard tests (356); three live ranking/composition repeats | [Diagnosis/results](../order-analysis-2026-11-16.md) | Narrow fix validation; not a rerun of every component or every manual case |
| 16 November chat continuity/typing | 33 dashboard tests/build; targeted chat checks and deployment observations | [Progress](../progress.md) | Historical test summary; animation appearance was not manually verified for that release |
| 16 November compliance | 215 gateway, 33 dashboard, 6 helper tests; charts, real migration, product 32/order 33, external conversations, Secret lifecycle and rejection auditing | [Report](../compliance-2026-11-16.md), [live JSON](../evidence/2026-11-16/acceptance.json), [retained gateway transcript](history/2026-11-16-gateway.txt) | Retained gateway output has normalized local paths; other full console logs were not retained. Standalone Docker/PostgreSQL smoke was not rerun |
| 18 November deployment recheck | Revision 13, eight ready workloads, three original Bound PVCs, three Connected upstreams/seven tools | [Dated recheck in report](../compliance-2026-11-16.md), [JSON](../evidence/2026-11-16/acceptance.json) | Read-only recheck; did not create new “today” orders |
| 18 November collected regressions | 412 tests, 16 checks, 0 failures, 0 skipped | [Run summary/log links](runs/2026-11-18/README.md), [machine manifest](runs/2026-11-18/summary.json) | Fixtures/offline checks; real provider/store, Docker integration, network and restart drills not rerun |

The 16 November gateway transcript was recovered from the retained operator work
file. It reports 215 tests in 73.584 seconds, OK. It predates the final commit; the
tested implementation was subsequently committed as `9f0aac5`. It is a sanitized
retained transcript with normalized paths/line endings/trailing whitespace, not a
new execution or a reconstructed verbose test listing.

## Failures and interruptions remain part of the history

- The initial 14 November gateway run from the wrong working directory failed a
  readiness test. The application-directory retry passed; the acceptance report
  records both. No full failed console transcript was retained.
- The reported generic chat error was not reproduced in the 15 November 10+10
  sample. The later exact ranking prompt did reproduce a call-budget failure; its
  diagnosis and three successful post-fix repetitions are recorded separately.
- A 16 November operator-harness timeout interrupted a Policy termination check.
  Recovery and cleanup are recorded in the compliance evidence; it was not counted
  as a successful application test.
- The 18 November collected automated run had no failed checks. That does not erase
  historical failures or establish every live/production behavior.

## Not validated by these logs

Real VPS/TLS, multi-store, fresh-machine installation, backup restore, disk-loss
recovery, high availability, peak capacity and Claude Code/Cursor remain outside the
claim. The recorded external client is official MCP Inspector plus the separate
OpenRouter prompt driver. The human video/explanations/submission remain pending.

For the next run, use [the runner instructions](README.md) and a fresh
[manual results sheet](manual-results-template.md). Add a dated row and preserve
both failures and successful retries. Never mark unexecuted template cases PASS.

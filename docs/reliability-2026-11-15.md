# Chat readability and setup follow-up

The user reported intermittent generic chat failures and requested a reviewer-ready
README, readable answers, external-demo readiness and a complete interview reference.

## Diagnosis and scope

The supplied message was the dashboard's catch-all fallback, not a root-cause code.
Ten read-only live prompts before changes all passed in 2.9–8.4 seconds. The same
ten prompts after deployment all passed in 2.9–8.6 seconds, including nonempty
Woo → Arithmetic composition against 14 November. One further browser prompt showed
a real table and both tool calls. The reported 4/10 failure rate was **not reproduced**;
these samples do not establish a long-term success rate or identify its original cause.

## Changes and safeguards

- OpenRouter generation gets at most one retry for transient transport/timeouts and
  HTTP 429/500/502/503/504. Numeric Retry-After hints up to two seconds are honored;
  long/unparsed hints are not ignored. Auth/quota/invalid-output failures stop.
  Only generation repeats: accepted tool executions and failed writes are never replayed.
  Generation retries may add latency and cost; the overall chat deadline remains 180 seconds.
- The dashboard renders a limited, escaped text-only Markdown subset: tables, lists,
  headings, emphasis and inline code. No raw HTML, remote images or active model links.
  Narrow tables scroll horizontally instead of crushing values into one-letter columns.
- Plain-language errors distinguish provider timeouts, temporary failures, credit
  limits and connection interruptions. Expandable safe codes support diagnosis.
  Chat failure logs contain only code and completed-call count, not prompts or bodies.
- README now separates fresh two-phase installation from existing-cluster startup,
  with exact commands, expected states, credentials flow, tests and troubleshooting.
  The new local create-only platform Secret helper closes a missing setup step;
  it preserves existing objects and stops on conflicts. Fresh-machine installation
  remains untested; default local names/account are its supported scope.
- The 15-page [interview PDF](urumi-interview-reference.pdf) and its
  [editable source](interview-guide.md) cover the six required video topics, practice
  answers, operational diagnosis, source locations and honest limits.

## Validation and deployment

204 gateway tests, 27 dashboard tests plus TypeScript/Vite, and 5 Secret-helper tests
passed. The unchanged Woo/Arithmetic/Policy suites retain the prior 120/21/15 passing
baseline. Local/prod 27-object schema and historical-resource comparisons passed.
Secret helper check mode passed against existing objects without replacing any.

Built/imported only gateway and dashboard images tagged `stage8.2-readability`.
Server preview showed only those image references and gateway job references changing,
apart from revision names. Helm revision **8** deployed successfully; all eight
workloads became Ready. Store, database, schema, resource budgets and provider/model
were not changed. The node had no MemoryPressure and used about 29% of its allocatable
memory; host free RAM was low (1.67 GiB). Recreate replaces the two app Pods, with no
extra permanent workload. This is not production capacity evidence.

The repository-default Inspector installation now exists under ignored `.venv/inspector`.
Its portable Node 22.23.4 avoids reliance on the older host Node. The npm install emitted
engine warnings because the installer ran under host Node 22.18; execution uses the
supported portable executable. No global runtime upgrade was performed.

The default installed helper passed against revision 8 with seven discovered tools
and real Woo → Arithmetic calls; its temporary administrator key was revoked in
cleanup. This is a current installation smoke check, supplementing the earlier
separate-member acceptance rather than replacing it. Application credential Secret
identities/contents and PVC identities matched their private baselines. Helm's own
revision-7 release Secret changed to superseded as expected during the upgrade.
The source/built-asset scan and documentation links/anchors/table checks passed.

See [sanitized prompt and client observations](evidence/2026-11-15/chat-checks.json)
and [the real rendered chat](evidence/2026-11-15/readable-chat.png).

For the next real intermittent failure, expand **Details for troubleshooting**, retain
the safe code and tool names, note the time and exact non-secret prompt, and correlate
with audits. Inspect the store before repeating a write. Do not enable raw wire logs.

## Recording readiness

The system and installed external demo tooling are ready. The demonstrated external
path is official MCP Inspector plus the OpenRouter prompt driver; native Claude
Code/Cursor remains untested and no Claude subscription is needed. Prepare a fresh
member whose password you control and its own key, and create a new same-day demo order
while recording. Old acceptance member accounts/keys intentionally remain disabled/revoked.
Then record, review, host and submit the video as described in [demo.md](demo.md).

Provider error semantics were checked against the
[official OpenRouter error documentation](https://github.com/OpenRouterTeam/docs/blob/main/api_reference/errors-and-debugging.mdx).

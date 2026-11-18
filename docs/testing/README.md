# Testing Urumi

Start with the [manual test guide](manual-tests.md) to test the application yourself.
Use the [results template](manual-results-template.md) to record what actually happened.
The [test history](test-history.md) links dated automated logs and live evidence.
The [recording guide](../demo.md) is for the final video, not a replacement for testing.

## Choose the right test

| Track | Purpose | Effects |
| --- | --- | --- |
| Automated checks below | Repeatable application/protocol/UI regressions and static configuration checks | Local fixtures, localhost listeners and generated dashboard files; no live store, provider or Kubernetes calls |
| Manual quick checks | Login, catalogs, existing orders and readable chat | Read-only store calls; chat consumes provider credit and writes audit metadata |
| Manual full acceptance | Product creation, COD checkout, two users, key revocation and failure recovery | Explicit demo records, identity/configuration changes and a temporary Policy outage |
| Operator checks | Network boundaries and restart persistence | Read-only probes, followed by separately scheduled Pod replacements if selected |

## Run and collect automated logs

Use PowerShell 7 from the repository root. Follow [README setup](../../README.md#run-the-automated-checks-without-store-mutations)
to install each app's hash-locked virtual environment and dashboard dependencies.
The runner installs nothing. Required commands: Git, Python 3.13, Node/npm, Helm and
`pwsh`. Its Python also needs PyYAML/jsonschema for chart validation. A full Git clone
is needed: the chart regression compares commits `88e5cae` and `f793e62`.

If your chosen Python lacks the static-check dependencies, isolate them from the
application environments with the versions used by these checks:

```powershell
py -3.13 -m venv .venv/checks
.venv/checks/Scripts/python -m pip install PyYAML==6.0.2 jsonschema==4.25.0
# Use .venv/checks/Scripts/python instead of py -3.13 for the runner below.
```

```powershell
# Run fixture tests, UI build, helpers, TCP smoke checks, Helm lint and repository checks.
py -3.13 scripts/run-tests.py
```

This creates a new `.test-results/<UTC timestamp>/` directory. It contains one `.txt`
transcript per executed check and `summary.json` with source commit, dirty-tree flag,
command, working directory, UTC times, duration, exit code, status and log SHA-256.
Verbose Python/Vitest output includes individual test names. A missing executable
or dependency is a **FAIL**, not a silently skipped test. Failed checks do not stop
later checks; the final process exit code is nonzero if any check failed. A timeout
is recorded as exit 124; inspect fixture process cleanup before rerunning.

For full chart schema validation, supply the Kubernetes **v1.35.5 OpenAPI v2** JSON
used by the chart checks. If that version is running locally, this read-only export
provides it without printing credentials:

```powershell
New-Item -ItemType Directory -Force .test-results | Out-Null
kubectl --context k3d-urumi-local get --raw /openapi/v2 |
    Set-Content -Encoding utf8 .test-results/kubernetes-openapi.json
if ($LASTEXITCODE -ne 0) { throw 'Schema export failed' }

py -3.13 scripts/run-tests.py --schema-file .test-results/kubernetes-openapi.json
if ($LASTEXITCODE -ne 0) { throw 'One or more automated checks failed; read summary.json' }
```

The runner itself never calls kubectl. Without `--schema-file`, `chart-schema` is
explicitly **SKIPPED** even if the process exits 0. Check the PASS/FAIL/SKIPPED totals;
exit 0 does not mean unselected live/integration tests ran. Use `--output <new-empty-directory>`
to choose a folder. Existing nonempty results folders are refused rather than overwritten.

### Included suites and what they prove

| Check ID | Coverage |
| --- | --- |
| `gateway-tests` | Registry, discovery/routing, identity/roles, sessions, key verification/revocation, audits, Secret references/migration, chat loop, provider failure handling and persistence fixtures |
| `woo-mcp-tests` | All five Woo tools, schemas, pagination/date boundaries, minimal data projection, auth, HTTP failures and uncertain-write behavior against fixtures |
| `arithmetic-mcp-tests` | Decimal calculations, limits, currency and MCP protocol |
| `store-policy-mcp-tests` | Policy topics, schemas and MCP protocol |
| `platform-secret-helper` | Create/check/preserve behavior with mocked Kubernetes, never real Secret creation |
| `dashboard-tests` | Login/session roles, management UI, readable/escaped answers, errors, pending messages, Enter/Shift+Enter, navigation retention and typing indicator |
| `dashboard-build` | TypeScript and production Vite compilation; not a browser acceptance test |
| `setup-store-secrets`, `setup-woocommerce-rest-secret` | Explicit offline `-Mode Validate` helper assertions |
| `arithmetic-mcp-tcp`, `store-policy-mcp-tcp` | Real temporary localhost MCP listeners, synthetic calls and shutdown |
| `helm-local`, `helm-prod`, `chart-schema` | Lint, render, schemas, RBAC, probes, resources, ingress/Secrets/policies and historical resource preservation |
| `repository` | Dependency/lock consistency, staged/tracked documentation links/tables and heuristic credential/contact scan including built assets |
| `git-whitespace` | Unstaged diff whitespace; final review must also check the staged diff |

Repository checks use `--tracked-only` to leave unrelated untracked files alone.
Before a final review, explicitly stage intended new project files, then run:

```powershell
py -3.13 tests/integration/repository_checks.py --tracked-only
git diff --cached --check
```

Counts of unit tests, helper assertions and smoke checks are different quantities.
The JSON `passed_test_count` counts only parsed passing unittest/Vitest test totals;
it does not add helper assertions or treat a Helm command as a unit test.

## Additional integration checks and current limits

| Entry point | Scope and prerequisites |
| --- | --- |
| `apps/gateway/tests/postgres_smoke.py` | Opt-in real DB test. Requires an **empty disposable loopback** database named `urumi_gateway_fixture` and a protected `URUMI_TEST_DATABASE_URL_FILE`. Never point it at the project DB. It owns schema/data mutations but does not provision the DB. Not part of the default run |
| `apps/woo-mcp/tests/smoke_docker.py` | Historical Docker hosting/discovery/security fixture; review image arguments and synthetic mounts before using |
| `apps/gateway/tests/container_smoke.py` | Historical gateway container fixture; review image/schema and credential-store requirements first |
| `tests/upstreams/smoke.py <app> --image <reviewed-tag>` | Opt-in disposable Docker check for Arithmetic/Policy; tests container security and cleanup |
| `tests/integration/docker_stage8.py` | **Historical Stage 8.0 images**, not a revision-13 regression. Do not substitute the current gateway tag and assume it works: the newer runtime requires the Kubernetes credential-store boundary |
| `tests/store/bootstrap-migration.php` | Historical synthetic Woo bootstrap fixture; follow its source prerequisites and earlier progress evidence |
| Live provider, checkout, network enforcement and Pod persistence | Follow [manual tests](manual-tests.md); an offline pass cannot establish these outcomes |

## Maintain the testing records

1. Run the appropriate checks for a change. Keep each run directory and its failed
   attempts; do not overwrite failures with a successful retry.
2. Inspect `summary.json`, all failed logs and important warnings. Fix the cause or
   document a blocked prerequisite; never turn missing evidence into PASS.
3. Use the manual results template for live work. Include date/timezone, source commit,
   Helm revision, actual user/product/order IDs, observed results and cleanup.
4. Review logs before publishing. The runner normalizes line endings/trailing whitespace, local paths and common key
   patterns; that is not universal redaction. Do not collect Secret YAML, environment
   dumps, cookies, invitation/key dialogs, customer contacts or provider wire logs.
5. Copy only reviewed artifacts from ignored `.test-results/` into a new dated
   `docs/testing/runs/` folder. Keep the original command output and its manifest;
   if further redaction is necessary, label it and update the artifact hash. Never
   rewrite test outcomes. Add a row to [test history](test-history.md).
6. Update manual cases when behavior changes. Record new source commits and link the
   relevant requirement IDs. Optional/unperformed checks remain NOT RUN or BLOCKED.

The maintained manual guide describes current behavior. Dated reports remain historical
evidence. Real VPS/TLS, multi-store, fresh-machine reproduction and backup restore are
not established by the available local results.

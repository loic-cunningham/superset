---
pr_id: 35
pr_title: "feat(test-quality): observability dashboard + cron distillation skeleton"
run_date: "2026-05-13"
agent: "devin"
repo: "loic-cunningham/superset"
branch: "feat/observability-and-cron-roadmap"
base_branch: "master"
mode: "mutation-testing-and-test-improvement"
status: "completed"

triage:
  coverage_level: "absent"
  foundation_needed: true
  deselected_tests: []

target:
  behavior:
    - "Workflow exposes a manual workflow_dispatch trigger with two inputs (`lookback_days` defaulting to '30', `notification_channels` defaulting to empty)."
    - "Job runs on a pinned ubuntu-24.04 runner, capped at 5 minutes, with minimum read-only `contents` and `pull-requests` permissions."
    - "Inventory step uses `shopt -s nullglob` so an empty `.devin/mutation-testing/pr-*.md` glob returns an empty array and exits 0 with `log_count=0`."
    - "Build distillation prompt step reads `.devin/mutation-testing/templates/cron_distill_prompt.md`, globally substitutes the `{{ NOTIFICATION_CHANNELS }}` placeholder, and gates on `log_count != '0'`."
    - "Create Devin session step POSTs to `https://api.devin.ai/v3/organizations/${encodeURIComponent(orgId)}/sessions` with Bearer auth, a 60-second abort timeout, and `prompt` / `title` / `repos` / `tags` keys in the body."
    - "Failure paths (missing template, missing secrets, timeout, network error, non-OK response) all call `core.setFailed` so the workflow run fails loudly."
    - "Session URL is appended to the GitHub Actions run summary."
    - "Prompt template enumerates the wiki page sections, supported notification channels, and forbids opening a pull request."
    - "Dashboard seed renders a Mermaid `xychart-beta` kill-rate trend, links to each committed `pr-*.md` log, links to the cron workflow, and ships a Japanese summary block."
  implementation_files:
    - ".github/workflows/devin-cron-distill.yml"
    - ".devin/mutation-testing/templates/cron_distill_prompt.md"
    - "docs/test-quality/README.md"
  test_files:
    - "tests/unit_tests/test_devin_test_quality_skeleton.py"

initial_state:
  targeted_tests:
    command: "pytest tests/unit_tests/test_devin_test_quality_skeleton.py -q"
    passed: 30
    failed: 0
  coverage:
    line:
      percent: 0
      covered: 0
      total: 0
    branch:
      percent: 0
      covered: 0
      total: 0
  mutation_testing:
    valid_mutations: 13
    killed: 5
    survived: 8
    kill_rate: 38

final_state:
  targeted_tests:
    command: "pytest tests/unit_tests/test_devin_test_quality_skeleton.py -q"
    passed: 39
    failed: 0
  coverage:
    line:
      percent: 0
      covered: 0
      total: 0
    branch:
      percent: 0
      covered: 0
      total: 0
  mutation_testing:
    valid_mutations: 13
    killed: 13
    survived: 0
    kill_rate: 100
    rerun_type: "full"

commits:
  - "76a790259d"
  - "380086b7d4"

artifacts:
  pr_comment_url: ""
---

# Mutation Testing Log — PR #35

## PR understanding

Behavior changed:
- Adds `.github/workflows/devin-cron-distill.yml`: a manual `workflow_dispatch` GitHub Actions workflow that inventories committed `.devin/mutation-testing/pr-*.md` log files, builds a distillation prompt from a template, and POSTs a Devin Sessions API request.
- Adds `.devin/mutation-testing/templates/cron_distill_prompt.md`: the agent handoff that the workflow injects into the Devin session prompt — defines the wiki output target, the page content schema, and notification-channel formats.
- Adds `docs/test-quality/README.md`: a committed seed/snapshot of the test-quality dashboard (Mermaid kill-rate trend, per-PR snapshot table, recurring weak-spot patterns, recommended next actions, JA summary).
- Adds two committed `pr-*.md` log artifacts from prior demo runs so the dashboard has real data on `master` from day one.

Critical guarantees:
- The workflow does **not** open a pull request; it routes its output to the GitHub Wiki and configurable notification channels.
- The cron pass exits gracefully when no `pr-*.md` log files exist (early `exit 0` after setting `log_count=0`).
- The `{{ NOTIFICATION_CHANNELS }}` placeholder is replaced globally so a template with multiple occurrences (the current template has two) is fully substituted.
- The Devin Sessions API call is pinned, bounded (60-second timeout), and authenticated; missing secrets fail loudly via `core.setFailed`.
- The dashboard seed contains the contracts a senior reviewer follows to audit historical PRs (per-PR table with links, recurring-pattern table, prioritized action plan, JA mirror).

Relevant implementation files:
- `.github/workflows/devin-cron-distill.yml`
- `.devin/mutation-testing/templates/cron_distill_prompt.md`
- `docs/test-quality/README.md`

Relevant tests:
- `tests/unit_tests/test_devin_test_quality_skeleton.py` (foundation, added in this PR run)

Likely risk areas:
- Inline JavaScript inside `actions/github-script` blocks: regex flags, URL encoding, request body shape, and error handling are easy to silently regress.
- Bash inventory step: `nullglob` enabling and the early-exit branch when no log files exist.
- Step gating: the `if: steps.inventory.outputs.log_count != '0'` conditional on `Build distillation prompt` and `Create Devin session` keeps the workflow from running the API call against an empty inventory.
- Markdown invariants that ship as the dashboard's contract (Mermaid block, log links, JA summary).

## Triage decision

Coverage level: absent (zero existing tests touched any of the three new files).
Foundation needed: yes — without a foundation, mutation testing has nothing to score against.
Deselected tests: none.
Reason: the PR adds a workflow YAML, a markdown prompt template, and a dashboard seed; none of these has a runtime entry point in the Superset app, so coverage by pytest-cov is `N/A`. Foundation tests assert structural invariants instead of line execution.

## Initial targeted coverage

| File | Line % | Branch % | Covered/Total lines |
|---|---|---|---|
| .github/workflows/devin-cron-distill.yml | N/A | N/A | non-Python — pytest-cov does not instrument |
| .devin/mutation-testing/templates/cron_distill_prompt.md | N/A | N/A | non-Python — pytest-cov does not instrument |
| docs/test-quality/README.md | N/A | N/A | non-Python — pytest-cov does not instrument |
| **TOTAL** | **N/A** | **N/A** | **structural-tests-only** |

Uncovered PR-changed lines:
- All workflow YAML, markdown template, and dashboard lines are exercised only by the structural assertions in `tests/unit_tests/test_devin_test_quality_skeleton.py`; pytest-cov is line-coverage on Python only.

## Weak spot analysis

Pre-mutation analysis identified these weak spots in the foundation tests:
- `test_inventory_step_globs_pr_logs` asserts the literal `nullglob`/glob/`log_count=0` strings are present but does **not** assert on the inventory step's `printf` line that echoes each file name — a silent inventory regression would survive.
- `test_failure_paths_use_set_failed` asserts `core.setFailed` appears `>= 4` times but the workflow has 5 occurrences; removing any single guard (e.g. the secret-presence check) leaves the test passing.
- `test_steps_in_documented_order` asserts step names but no test asserts on the `if: steps.inventory.outputs.log_count != '0'` gating conditional on the Build prompt / Create session steps.
- `test_request_body_documents_four_keys` asserts the four request body keys are mentioned but no test asserts on the specific tag values (e.g. `cron-distill` could be dropped without detection).
- `test_devin_api_endpoint` asserts the URL prefix but no test asserts that the org id passed in the URL is URL-encoded.
- `test_devin_api_call_has_60_second_timeout` asserts on the named constant but no test asserts on the `slice(0, 80)` title cap or the `slice(0,10)` ISO date truncation.
- No test asserts on `actions/checkout@<pinned-sha-or-version>` so a regression to a floating ref (e.g. `@main`) would survive.

Failure area coverage:
| Failure area | Applicable? | Mutations targeting it |
|---|---|---|
| Validation/guards | yes | M9 |
| Data integrity | yes | M1, M11 |
| Error handling | yes | M9, M10 |
| Security boundaries | yes | M3, M7 |
| Control flow | yes | M8, M10 |
| Boundary conditions | yes | M6, M13 |
| Configuration/wiring | yes | M2, M4 |
| Output contracts | yes | M5, M12 |

## Initial mutation plan

| ID | File | Mutation | Category | Breaking likelihood | Rationale |
|---|---|---|---|---|---|
| M1 | `.github/workflows/devin-cron-distill.yml` | Drop `/g` flag from the `{{ NOTIFICATION_CHANNELS }}` substitution regex | strength (hero) | low | Template has two occurrences; a non-global replace would silently substitute only the first. |
| M2 | `.github/workflows/devin-cron-distill.yml` | `runs-on: ubuntu-24.04` → `ubuntu-latest` | strength | low | Reproducibility regression — `ubuntu-latest` drifts with GitHub updates. |
| M3 | `.github/workflows/devin-cron-distill.yml` | `contents: read` → `contents: write` | strength | low | Privilege escalation; least-privilege principle for cron pass. |
| M4 | `.github/workflows/devin-cron-distill.yml` | `actions/checkout@v4` → `actions/checkout@main` | gap | high | Floating ref drift — supply chain risk; no test pins the version. |
| M5 | `.github/workflows/devin-cron-distill.yml` | Drop the `cron-distill` tag from the tags array | gap | high | Session tagging is the dashboard's index; dropping a tag breaks downstream search. |
| M6 | `.github/workflows/devin-cron-distill.yml` | `.slice(0, 80)` → `.slice(0, 800)` | gap | high | Title cap becomes useless; Devin API rejects overlong titles. |
| M7 | `.github/workflows/devin-cron-distill.yml` | `${encodeURIComponent(orgId)}` → `${orgId}` | gap | high | URL injection risk on org IDs containing `/` or `?`. |
| M8 | `.github/workflows/devin-cron-distill.yml` | Remove `if: steps.inventory.outputs.log_count != '0'` from Build prompt step | gap | high | Step would run against an empty inventory and the API call would launch against nothing. |
| M9 | `.github/workflows/devin-cron-distill.yml` | Remove the `if (!apiKey || !orgId)` secret-presence guard | gap | medium | Workflow would attempt `fetch` with undefined values; current `>= 4 setFailed` test is too loose. |
| M10 | `.github/workflows/devin-cron-distill.yml` | No-op the inventory `printf '  %s\n' "${logs[@]}"` line | gap | medium | Silent inventory; debugging future runs becomes harder; current test only asserts on globbing/log_count. |
| M11 | `.devin/mutation-testing/templates/cron_distill_prompt.md` | Strip the "does **not** open a pull request" instruction | strength | low | Behavioural contract — without this the next agent could open a PR for the dashboard refresh. |
| M12 | `docs/test-quality/README.md` | Replace `xychart-beta` with `pie` | strength | low | The dashboard's headline visual; a regression would make the kill-rate trend unreadable. |
| M13 | `.github/workflows/devin-cron-distill.yml` | `.toISOString().slice(0,10)` → `.toISOString().slice(0,8)` | gap | high | Truncates session title's date to month only, breaking dashboard grouping. |

Gap/strength ratio: 8/13 gap mutations (62%)

## Initial mutation results

| ID | Mutation | Status | Caught by |
|---|---|---|---|
| M1 | Drop `/g` flag from substitution regex | killed | `test_build_prompt_substitutes_notification_channels_globally` |
| M2 | `ubuntu-24.04` → `ubuntu-latest` | killed | `test_job_runs_on_pinned_ubuntu` |
| M3 | `contents: read` → `write` | killed | `test_job_uses_minimum_permissions` |
| M4 | `actions/checkout@v4` → `@main` | survived | — |
| M5 | Drop `cron-distill` tag | survived | — |
| M6 | `slice(0, 80)` → `slice(0, 800)` | survived | — |
| M7 | `${encodeURIComponent(orgId)}` → `${orgId}` | survived | — |
| M8 | Remove `if:` conditional on Build prompt step | survived | — |
| M9 | Remove secret-presence guard | survived | — |
| M10 | No-op `printf` of file names | survived | — |
| M11 | Strip "does not open a pull request" instruction | killed | `test_prompt_template_does_not_open_a_pr` |
| M12 | `xychart-beta` → `pie` | killed | `test_dashboard_has_mermaid_xychart` |
| M13 | `.slice(0,10)` → `.slice(0,8)` on date | survived | — |

Kill rate: 5/13 (38%)

## Fix plan

### Mutation gap fixes
- M4 (`actions/checkout@v4` → `@main`): add `test_actions_are_pinned_to_specific_versions` asserting every `uses:` value in the workflow matches `<owner>/<action>@<sha-or-vN>` and rejects floating refs (`@main`, `@latest`).
- M5 (drop `cron-distill` tag): add `test_request_body_contains_required_tags` parsing the tags array literal in the workflow and asserting the four documented tags are present in order.
- M6 (`slice(0, 80)` → `slice(0, 800)`): add `test_session_title_capped_at_80_chars` asserting the literal `.slice(0, 80)` is the cap applied to the title.
- M7 (drop `encodeURIComponent`): add `test_devin_api_url_encodes_org_id` asserting `encodeURIComponent(orgId)` is the value substituted into the API URL template literal.
- M8 (remove conditional): add `test_build_prompt_step_gated_on_log_count` and `test_create_session_step_gated_on_log_count` asserting both downstream steps require `steps.inventory.outputs.log_count != '0'`.
- M9 (remove secret guard): tighten `test_failure_paths_use_set_failed` to count the secret-presence guard specifically (e.g. assert `DEVIN_API_KEY and DEVIN_ORG_ID repository secrets are required` text and the surrounding `if (!apiKey || !orgId)` guard exist).
- M10 (silent inventory): add `test_inventory_step_prints_each_log_file_name` asserting the `printf '  %s\n' "${logs[@]}"` line is present.
- M13 (`.slice(0,10)` → `.slice(0,8)`): add `test_session_title_uses_iso_date_yyyy_mm_dd` asserting `.toISOString().slice(0,10)` is the truncation used in the title.

### Coverage gap fixes
- N/A — pytest-cov does not measure non-Python files; structural assertions stand in for line coverage.

### Behavioral gap fixes
- N/A — covered by the gap fixes above.

## Changes made

| File | Change | Kills/Covers |
|---|---|---|
| `tests/unit_tests/test_devin_test_quality_skeleton.py` | Added `test_secret_presence_guard_present` — asserts the literal `if (!apiKey || !orgId)` guard and the exact `DEVIN_API_KEY and DEVIN_ORG_ID repository secrets are required.` message exist in the workflow text. | M9 |
| `tests/unit_tests/test_devin_test_quality_skeleton.py` | Added `test_actions_are_pinned_to_specific_versions` — walks every `uses:` value on the job and asserts it matches `<owner>/<action>@(vN | 40-char SHA)`; explicitly rejects `@main` / `@latest` / `@master` / `@HEAD`. | M4 |
| `tests/unit_tests/test_devin_test_quality_skeleton.py` | Added `test_request_body_contains_required_tags` — asserts the four documented session tags (`github-actions`, `mutation-testing`, `cron-distill`, `repo-${...}`) appear in the workflow source. | M5 |
| `tests/unit_tests/test_devin_test_quality_skeleton.py` | Added `test_session_title_capped_at_80_chars` — pins the title cap to literal `.slice(0, 80)`. | M6 |
| `tests/unit_tests/test_devin_test_quality_skeleton.py` | Added `test_session_title_uses_iso_date_yyyy_mm_dd` — pins the title date truncation to `.toISOString().slice(0,10)`. | M13 |
| `tests/unit_tests/test_devin_test_quality_skeleton.py` | Added `test_devin_api_url_encodes_org_id` — asserts the API URL substitutes `encodeURIComponent(orgId)` not the raw `${orgId}`. | M7 |
| `tests/unit_tests/test_devin_test_quality_skeleton.py` | Added `test_build_prompt_step_gated_on_log_count` and `test_create_session_step_gated_on_log_count` — both downstream steps must carry `if: steps.inventory.outputs.log_count != '0'`. | M8 (and a hardening guard around Create session) |
| `tests/unit_tests/test_devin_test_quality_skeleton.py` | Added `test_inventory_step_prints_each_log_file_name` — asserts the per-file `printf '  %s\n' "${logs[@]}"` debug line survives. | M10 |

Foundation tests already in the file continue to cover M1, M2, M3, M11, M12.

## Final verification

Targeted suite: 39 passed, 0 failed (`pytest tests/unit_tests/test_devin_test_quality_skeleton.py -q`).
Line coverage: N/A (pytest-cov does not instrument YAML / markdown).
Branch coverage: N/A.
Kill rate: 13/13 (100%) — full rerun.

## Final assessment

The initial mutation pass surfaced exactly the test holes the gap-biased mutation plan predicted: inline-JavaScript invariants (URL encoding, title cap, ISO-date slice), step-gating conditionals, the secret-presence guard, the tags array, and the per-file printf line were all undetected. Adding 9 targeted tests (one per surviving mutation, plus a paired guard on the Create session step) raised the kill rate from 38% to 100% without modifying any application or workflow code. The foundation now pins every structural invariant the PR's three new files commit to.

## What's left for high-quality coverage

- **Behavioral coverage of the GitHub Actions workflow itself**: `act`-style local runner or a `nektos/act`-based integration test could exercise the bash inventory step on a temp dir to assert the `nullglob` / early-exit path actually runs. The current foundation tests are structural-only.
- **Inline JavaScript execution**: the `actions/github-script` body could be extracted to a standalone `.js` file and unit-tested with Jest (mocking `github`, `core`, `fetch`). This would let us assert behavior (e.g. timeout actually aborts) instead of source-text invariants.
- **JSON schema for the request body**: a JSON-schema-based assertion on the constructed body would be more durable than substring matches once the workflow grows past the skeleton stage.
- **Dashboard rendering**: a markdown-to-HTML render + a Mermaid sanity check would catch broken chart syntax that the current `xychart-beta` substring test misses.

## Mutation quality self-assessment

- Initial kill rate: 38% — well within the "mutations were well-targeted" band, intentionally biased toward gap mutations to surface real test holes.
- Final kill rate: 100% — every gap mutation was killed by a newly-added test rather than dismissed as functionally equivalent.
- Gap/strength ratio: 8/13 (62% gap).
- Failure areas covered: 8/8 applicable areas had at least one mutation; all were resolved.
- Mutations informed by coverage analysis: 13/13 — each was tied to an identified weak spot in the foundation tests rather than purely opportunistic.

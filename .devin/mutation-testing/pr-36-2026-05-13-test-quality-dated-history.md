---
pr_id: 36
pr_title: "chore(test-quality): switch wiki to dated history with per-run snapshots"
run_date: "2026-05-13"
agent: "devin"
repo: "loic-cunningham/superset"
branch: "devin/1778663293-test-quality-dated-history"
base_branch: "master"
mode: "mutation-testing-and-test-improvement"
status: "completed"

triage:
  coverage_level: "not_applicable"
  foundation_needed: false
  deselected_tests: []
  rationale: >
    The PR is documentation- and prompt-only. It modifies three
    non-executable files:
    `.devin/mutation-testing/templates/cron_distill_prompt.md`
    (the Markdown prompt template fed verbatim to a Devin cron session
    at runtime), `.github/workflows/devin-cron-distill.yml` (header
    comments and one input `description:` string only — no logic, env
    vars, steps, or jobs are altered), and `docs/test-quality/README.md`
    (the seed/snapshot of the test-quality dashboard). No Python,
    TypeScript, or workflow logic is changed. There is no production
    behaviour to mutate, no test suite that targets these files, and no
    automated test that would catch a regression in the markdown prose
    of a prompt template. Mutation testing is therefore not applicable
    to this PR and is recorded as a documented no-op for traceability.

target:
  behavior:
    - "Restructure the cron-distill prompt template so each run writes a new dated wiki entry (Test-Quality-YYYY-MM-DD.md) instead of refreshing a single Test-Quality.md in place."
    - "Require the agent to read every prior Test-Quality-*.md before writing the new entry so cross-run trends and unresolved recommendations are surfaced."
    - "Mandate a YAML front-matter block (run_date, run_timestamp, distillation_window_days, source_commit, prs_processed, prs_at_100_kill_rate, prs_needed_foundation, total_tests_added, prs_left_unsafe, previous_entry) at the top of every new dated entry so future runs can parse the history programmatically."
    - "Split the wiki output into an append-only dated-history layout (Test-Quality.md index + Test-Quality-YYYY-MM-DD.md per-run snapshot) and forbid editing or deleting any prior dated entry."
    - "Update the .github/workflows/devin-cron-distill.yml header comment and the notification_channels input description to reflect the new dated-history model."
    - "Update docs/test-quality/README.md (the committed seed/snapshot) so it points readers to the new live wiki page set and explains the dated-history layout."
  implementation_files:
    - ".devin/mutation-testing/templates/cron_distill_prompt.md"
    - ".github/workflows/devin-cron-distill.yml"
    - "docs/test-quality/README.md"
  test_files: []

initial_state:
  targeted_tests:
    command: "n/a — no Python/TS test suite is associated with the changed Markdown/YAML-comment files"
    passed: 0
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
    valid_mutations: 0
    killed: 0
    survived: 0
    kill_rate: "n/a"

final_state:
  targeted_tests:
    command: "n/a — no Python/TS test suite is associated with the changed Markdown/YAML-comment files"
    passed: 0
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
    valid_mutations: 0
    killed: 0
    survived: 0
    kill_rate: "n/a"
    rerun_type: "full"

verifications:
  - tool: "git diff --name-only master..HEAD"
    result: "only .devin/mutation-testing/templates/cron_distill_prompt.md, .github/workflows/devin-cron-distill.yml, and docs/test-quality/README.md differ; no .py/.ts/.tsx/.js/.jsx changes"
  - tool: "git diff master..HEAD -- .github/workflows/devin-cron-distill.yml"
    result: "all hunks are header `#` comments or the `description:` text of the `notification_channels` input — no on/jobs/steps/env/secrets/permissions/uses lines change"
  - tool: "grep -rn cron_distill_prompt superset superset-frontend tests"
    result: "no matches — no Python or TypeScript module imports, parses, or references the prompt template"

commits: []

artifacts:
  pr_comment_url: ""
---

# Mutation Testing Log — PR #36

## PR understanding

Behavior changed:
- Switches the GitHub Wiki output of the `devin-cron-distill.yml` workflow
  from a single `Test-Quality.md` refreshed in place to an append-only
  dated history: each run writes a brand-new `Test-Quality-YYYY-MM-DD.md`
  page (with `-HHMM` suffix for same-day re-runs) and refreshes
  `Test-Quality.md` as an index page (latest-run pointer + chronological
  history table only).
- Requires the cron-distill Devin session to read every prior
  `Test-Quality-YYYY-MM-DD*.md` entry before writing the new one, so the
  new entry can reference cross-run trends, mark recommendations that
  subsequent PRs have addressed, and never overwrite history.
- Mandates a YAML front-matter contract on every new dated entry
  (`run_date`, `run_timestamp`, `distillation_window_days`, `source_commit`,
  `prs_processed`, `prs_at_100_kill_rate`, `prs_needed_foundation`,
  `total_tests_added`, `prs_left_unsafe`, `previous_entry`) so future runs
  can parse the history programmatically without re-reading prose.
- Adds new dated-entry sections: run-metadata block, "Change vs.
  previous run", a cross-run kill-rate Mermaid trend chart (skipped when
  history < 2 runs), and a prior-recommendation cross-off in the action
  plan.
- Updates the `.github/workflows/devin-cron-distill.yml` header comment
  and the `notification_channels` input `description:` string to describe
  the dated-history layout. No workflow logic, steps, jobs, env vars, or
  inputs are altered.
- Updates `docs/test-quality/README.md` (the committed seed/snapshot) to
  point readers to the new live wiki page set, describe the
  index-plus-dated-snapshots model, and update the JA summary to match.

Critical guarantees (documentation-level, not unit-testable):
- The prompt template file at
  `.devin/mutation-testing/templates/cron_distill_prompt.md` continues to
  exist at the path the workflow's `prompt_template_path` reads from
  (`.github/workflows/devin-cron-distill.yml:94`).
- The workflow's `inputs:` schema (`lookback_days`,
  `notification_channels`) is unchanged in name, type, and default value.
- The `docs/test-quality/README.md` seed-snapshot file keeps its
  existing top-level structure (callout, "What an engineering leader
  sees", "How this is refreshed", JA summary).

Relevant implementation files:
- `.devin/mutation-testing/templates/cron_distill_prompt.md`
- `.github/workflows/devin-cron-distill.yml`
- `docs/test-quality/README.md`

Relevant tests:
- None. The repository carries no Python, TypeScript, or
  GitHub-Actions-side test that loads, parses, or asserts on the prompt
  template, the cron-distill workflow YAML, or the test-quality seed
  documentation. The only consumer of the prompt template is the
  `devin-cron-distill.yml` workflow itself, which reads it verbatim via
  `fs.readFileSync` and POSTs it to the Devin sessions API; the only
  runtime "behaviour" the changed prose describes lives inside a
  downstream LLM session, which is not exercised by any CI test in this
  repository.

Likely risk areas (intentionally out of scope for mutation testing on
this PR — included here only for the long-term log index):
- Mis-keyed YAML front-matter fields on future dated entries would
  silently break the cross-run trend chart on the next run. The cron-
  distill session itself is responsible for validating its own output;
  there is no CI-side assertion.
- The `cron_distill_prompt.md` template uses a `{{ NOTIFICATION_CHANNELS }}`
  placeholder that the workflow substitutes via a single regex replace
  (`devin-cron-distill.yml:100`). The placeholder string is unchanged in
  this PR, so the substitution contract is preserved by construction.

## Triage decision

Coverage level: not_applicable
Foundation needed: no
Deselected tests: none
Reason: The diff touches only three non-executable files
(`.devin/mutation-testing/templates/cron_distill_prompt.md`,
`.github/workflows/devin-cron-distill.yml` — header comments + one
`description:` string only, no logic change, and
`docs/test-quality/README.md`). A repo-wide `grep -rn cron_distill_prompt`
returns one hit and it is the workflow file that reads the template at
runtime; no Python, TypeScript, or YAML test ever imports, parses, or
asserts on these files. Mutation testing requires automated tests that
would fail when behaviour is mutated; with zero tests covering the
changed files, every conceivable mutation would survive trivially, so
mutation testing carries no signal here and is recorded as a no-op for
the long-term log index.

## Initial targeted coverage

| File | Line % | Branch % | Covered/Total lines |
|---|---|---|---|
| `.devin/mutation-testing/templates/cron_distill_prompt.md` | n/a | n/a | n/a |
| `.github/workflows/devin-cron-distill.yml` | n/a | n/a | n/a |
| `docs/test-quality/README.md` | n/a | n/a | n/a |
| **TOTAL** | **n/a** | **n/a** | **n/a** |

Uncovered PR-changed lines:
- All changed lines are Markdown content (prompt prose, header comments,
  user-facing documentation). There is no executable code under test, so
  the concept of "covered/uncovered lines" does not apply.

## Weak spot analysis

Pre-mutation coverage analysis identified these weak spots for targeted
mutation design:
- None applicable. There are no executable lines in the diff, no
  test-asserted behaviour anywhere in the changed files, and no
  downstream test target that exercises this code path. Every conceivable
  mutation (reword a sentence, drop a YAML field, change a header comment)
  would survive 100% of any test suite — not because the suite is weak,
  but because no suite exists for this surface.

Failure area coverage:
| Failure area | Applicable? | Mutations targeting it |
|---|---|---|
| Validation/guards | no | n/a |
| Data integrity | no | n/a |
| Error handling | no | n/a |
| Security boundaries | no | n/a |
| Control flow | no | n/a |
| Boundary conditions | no | n/a |
| Configuration/wiring | no | n/a |
| Output contracts | no | n/a |

Rationale: the failure areas above describe *executable* behaviour
classes. A markdown prompt template that an LLM agent reads at runtime
has no compile-time or test-time enforcement surface; the
`devin-cron-distill.yml` workflow only reads it as a string and forwards
it to the Devin API. There is nothing here for these failure areas to
apply to.

## Initial mutation plan

| ID | File | Mutation | Category | Breaking likelihood | Rationale |
|---|---|---|---|---|---|
| — | — | No mutations planned. | — | — | This PR has no executable code, no test suite, and no automated assertion surface. Designing mutations under these conditions would either produce trivially-surviving no-signal mutations (every one survives by construction) or trivially-killed ones that test nothing meaningful. Both outcomes mislead future readers of this log, so no mutations are planned. |

Gap/strength ratio: 0/0 gap mutations (n/a)

## Initial mutation results

| ID | Mutation | Status | Caught by |
|---|---|---|---|
| — | No mutations executed. | n/a | — |

Kill rate: 0/0 (n/a — no mutations were planned or executed; see Triage
decision above).

## Fix plan

### Mutation gap fixes
- None — no surviving mutations exist because no mutations were executed.

### Coverage gap fixes
- None — the changed surface has no test-coverable lines. Adding a
  PyYAML round-trip test against the prompt template or a `yamllint` job
  against the workflow file would be the right *structural* check, but
  that is out of scope for this PR (the PR alters wording, not structure;
  any future PR that adds new YAML fields to the front-matter contract
  is a better place to invest in a parse-time guard).

### Behavioral gap fixes
- None — the only "behaviour" the PR describes lives in a downstream
  Devin session that this repository's CI cannot exercise.

## Changes made

| File | Change | Kills/Covers |
|---|---|---|
| `.devin/mutation-testing/pr-36-2026-05-13-test-quality-dated-history.md` | Added this no-op mutation-testing log to record the triage decision and preserve the long-term index. | n/a — log file only. |

## Final verification

Targeted suite: 0 passed, 0 failed (no targeted suite exists for the
changed files; verified with `git diff --name-only master..HEAD` and a
repo-wide grep for any reference to the changed files from test code).
Line coverage: n/a (no Python/TS module under test).
Branch coverage: n/a.
Kill rate: n/a — 0/0; rerun_type `full` for schema completeness (a
hypothetical full re-run of zero mutations is byte-identical to the
initial pass).

## Final assessment

This is a documentation- and prompt-only PR. The triage step established
that there is no executable code under test, no test suite that exercises
the changed files, and no automated assertion that any mutation could
cause to fail. Mutation testing therefore has no signal to deliver on this
PR, and the run is recorded as an explicit no-op so the long-term
mutation-testing index has a row for PR #36. The C1 (status), C2
(initial), and C3 (final) PR comments are still posted to keep the
three-comment flow consistent with the workflow contract.

## What's left for high-quality coverage

| Area | Missing test | Why it matters |
|---|---|---|
| Wiki dated-entry YAML front-matter contract | A future PR that *adds new fields* to the `Test-Quality-YYYY-MM-DD.md` front-matter contract should ship with a tiny `pytest` or `actions/github-script` parse test that asserts the cron-distill prompt template produces an entry whose front matter is loadable by PyYAML and contains the required keys. Not in scope for this PR (which alters wording, not structure), but the right place to invest the next time the contract changes. | A typo in the prompt template's YAML example would silently break every downstream consumer's `previous_entry` lookup. |
| Workflow comment-only changes | A `yamllint` job on `.github/workflows/*.yml` would catch accidental indentation/spacing regressions in workflow comment blocks. Out of scope here because the PR is comment-only and the file still parses, but a generic structural lint would catch a future careless edit. | Defence-in-depth against silent workflow corruption. |
| `cron_distill_prompt.md` consumer contract | A trivial regression test that asserts `.devin/mutation-testing/templates/cron_distill_prompt.md` exists and is non-empty at the path `devin-cron-distill.yml` reads from. One-line `os.path.exists` assertion; not added in this PR. | Path drift between the workflow and the template is the only structural failure mode this surface can produce. |

These are coverage opportunities identified from triage and behavioural
analysis, not from surviving mutations (none ran). They are deliberately
small and scoped to a future PR that actually changes the contract.

## Mutation quality self-assessment

- Initial kill rate: n/a — no mutations were planned or executed.
- Gap/strength ratio: 0/0 (n/a) — no mutations to classify.
- Failure areas covered: 0/0 — no failure areas apply to a
  documentation-only diff (see the Weak spot analysis section).
- Mutations informed by coverage analysis: 0/0 — coverage analysis on
  the changed surface returns "no Python/TS module to measure", which is
  the input to the triage decision rather than to a mutation plan.
- This run is an explicit no-op recorded for traceability. Future PRs in
  the same triage class (markdown/prompt-only, no executable surface)
  should follow the same pattern: post C1/C2/C3 via
  `render_pr_comment.py`, commit a log file documenting the triage
  decision, and avoid inventing low-signal mutations to satisfy a count.

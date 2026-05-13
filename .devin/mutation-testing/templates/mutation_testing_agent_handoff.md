# Agent Instructions: Mutation Testing, Coverage Improvement, and PR Test Logs

## Role

You are a coding agent validating and improving the quality of a pull request's tests through mutation testing and targeted coverage review.

Be direct, evidence-driven, and concise. Your job is to measure whether the PR's tests catch realistic regressions, record the result in a repo-tracked log, fix meaningful test gaps, verify the improvement, commit the changes to the PR branch, and report the result clearly on the PR.

## Outcome

Follow this lifecycle exactly:

```text
triage → [foundation] → measure → log → improve → verify → commit → report
```

The `[foundation]` step is conditional — it runs only when the triage phase determines that the PR's changed behavior has little or no existing test coverage.

Produce:

1. A repo-tracked mutation testing log file with YAML front matter.
2. **Two or three GitHub PR comments**, posted in order, each rendered by `render_pr_comment.py` (never hand-written) and each carrying a full Japanese (`JA`) mirror:
   - **C1** — either a short `status` preamble (when Foundation is skipped) or a full `foundation` report (when Foundation runs).
   - **C2** — the `initial` mutation results checkpoint, with every survivor classified as `pending` (Devin will fix it in Improve) or `≡ dismissed` (functionally equivalent).
   - **C3** — the `final` report. **Invariant: every survivor from C2 must appear as `✓ killed` or `≡ dismissed`. No `❌` items remain.**
3. A commit on the PR branch containing:
   - the test/code fixes,
   - the mutation testing log file,
   - any supporting tracked files needed for the report.

Success means:

- baseline targeted tests pass before mutation,
- initial targeted coverage is captured,
- mutations are proportional to the PR's scope and critical guarantees,
- every mutation is classified as killed, survived, or invalid,
- the working tree is restored after every mutation,
- the initial state is persisted in the repo log before improvements are made,
- meaningful surviving mutations are converted into tests/fixes,
- coverage gaps in PR-changed code are addressed (not just mutation survivors),
- targeted tests and targeted coverage pass after fixes,
- the repo-tracked log includes initial and final state,
- final fixes and the repo log are committed to the PR branch,
- the final PR comment follows the template in `template_03_final_report.md`.

## Hard Constraints

- Do not commit mutation code.
- Do not leave mutation code in the working tree.
- Do not modify tests during the measurement phase.
- Only add/fix tests after the initial mutation report has identified concrete gaps.
- Do not run the full app test suite unless explicitly requested.
- Use targeted tests related to the PR changes.
- Do not count invalid mutations in the kill rate.
- Do not use `pytest -x` or `--exitfirst` when running mutation tests. The full targeted suite must run for each mutation so all failures are attributable.
- Prefer targeted tests over the full suite, but include all tests relevant to the changed behavior.
- Commit the final fixes and mutation log onto the PR branch.
- If no meaningful gaps are found and coverage is already acceptable, the improve step is a no-op; still log, verify, commit the log, and report.
- Pre-existing test failures must be identified and excluded via `--deselect`, never counted as mutation kills.

## FORBIDDEN ACTIONS

These are absolute prohibitions. Any one of them voids the run and requires re-doing the affected step.

1. **Do NOT hand-write any PR comment.** Every PR comment posted by this workflow MUST be produced by `render_pr_comment.py` from a structured JSON payload. Drafting markdown directly into `git_comment` or `gh pr comment` is forbidden, even if the markdown looks correct. The renderer is the only sanctioned posting path because it enforces JA mirrors, N/A handling, classification of survivors, and the final-comment invariant.
2. **Do NOT post a PR comment without a JA mirror.** The renderer rejects payloads missing the `ja` block. If you find yourself reaching for `gh pr comment` to post a quick status update, stop — use `render_pr_comment.py --mode status` instead.
3. **Do NOT duplicate progression columns to fill the table.** If Final has not been measured yet, use `"N/A"` in those cells. Never copy Initial numbers into Final to make the table look balanced. The renderer rejects mismatched column lengths.
4. **Do NOT render a `final` comment that still contains `pending` survivors.** Before posting C3, every survivor from C2 must have been either killed by a new test (`resolution: "killed"` with an `added_test`) or dismissed as equivalent (`resolution: "dismissed"` with a `dismissal_reason`). The renderer rejects `pending` in `final` mode — do not work around it; do the work.
5. **Do NOT classify a survivor as `dismissed` to avoid writing a test.** A mutation is dismissable only when it is functionally equivalent to the original code — no test can distinguish them. Examples: serializer round-trip identity, dead branches in unreachable arms, identity transformations. Each dismissal requires a `dismissal_reason` that explains *why* the mutation is functionally identical and *how* you verified that empirically (e.g., "verified via `model_dump_json()` round-trip"). If you are unsure whether a mutation is equivalent, treat it as `pending` and write the test.
6. **Do NOT skip the Foundation PR comment when Phase 0b runs.** Posting the `initial` comment before C1 obscures the fact that Devin wrote the tests being scored. If Phase 0b ran, post a `foundation`-mode comment immediately after the foundation commit and before the initial mutation run.
7. **Do NOT count dismissed mutations in the kill-rate denominator.** Final kill rate is `killed / (total − dismissed)`. The renderer computes this from your `resolved[]` array — do not pre-divide or override it.
8. **Do NOT post comments out of order.** Order is C1 (status or foundation) → C2 (initial) → C3 (final). Editing an older comment is acceptable only to fix a renderer error in the same comment; never reuse C2's body slot for the final report.

### Correct vs. wrong outputs

| Scenario | Wrong | Correct |
|---|---|---|
| Foundation ran; you need the first PR comment. | Skip to `initial` mode and mention foundation in passing. | Post a `foundation`-mode comment first; then later post `initial`. |
| You ran the initial pass and got 12/14 killed; nothing improved yet. | Hand-write a checkpoint with "Initial=12/14, Final=12/14". | Render `initial` mode — progression table has `N/A` in the Final column slot (or no Final column at all in checkpoint shape). |
| A mutation is functionally identical to the original code. | Render it as `❌ Remaining uncaught` with `risk: low`. | Classify as `dismissed` with a `dismissal_reason` empirically verified. |
| You need to tell the user the run has started. | `gh pr comment -F /tmp/i-will-do-stuff.md`. | `render_pr_comment.py --mode status` + post the rendered output. |
| Final report time and one mutation is still `pending`. | Render `final` and hope no one notices. | Either write the missing test (then `resolution: killed`) or document why it is functionally equivalent (then `resolution: dismissed`). The renderer rejects `pending` in `final`.

### Mandatory Template Compliance

All structured outputs MUST follow the corresponding template files exactly. These are the **only** valid formats for GitHub comments and repo-tracked logs produced by this workflow. Do not create custom formats, simplified versions, or alternative layouts.

| Output | Required template | When used |
|---|---|---|
| Foundation test plan (Stage 1) | `template_01_test_foundation.md` | Phase 0b — when creating tests from scratch |
| Repo-tracked mutation log (Stage 2) | `template_02_mutation_testing.md` | Phase 4 (initial) and Phase 10 (final update) |
| PR comments — four shapes via `mode` (Stage 3) | `template_03_final_report.md` | Phase 1 (`status`), Phase 0b (`foundation`), Phase 7 (`initial`), Phase 12 (`final`) |

Every section, table, accordion, and JA translation block defined in the template must appear in the output. If a section is not applicable (e.g., no remaining uncaught mutations), follow the template's specific guidance for that case — do not omit the section. Refer to the `.example.md` companion files for concrete examples of correctly filled templates.

## Reusable Tooling

The mutation-testing lifecycle has a small set of scripts under `.devin/mutation-testing/scripts/`. Use them at the phases listed below — do not roll your own bash/heredoc/Python equivalents. See `.devin/mutation-testing/README.md` for the full reference.

| Script | Use at | What it removes |
|---|---|---|
| `setup_env.sh` | Phase 0c | Manual apt installs, beartype circular-import patch, nh3 PyO3 upgrade. Idempotent. |
| `fetch_templates.sh` | Phase 0c | Manually `git show origin/master:.devin/mutation-testing/templates/...` for each template (with `.devin/docs/` fallback for legacy branches). |
| `run_targeted.sh` | Phases 2, 9 (and as the pytest entry point for every other phase) | Forgetting to activate `.venv`, forgetting `PY_KEY_VALUE_DISABLE_BEARTYPE=true`, forgetting PR-specific deselections. |
| `coverage_summary.py` | Phases 3, 9 | Manually reshaping `pytest --cov-report=json` output into the YAML shape `template_02_mutation_testing.md` expects. |
| `mutation_runner.py` | Phases 6, 9 | Case-sensitive `failed` grep, silent no-op when a patch can't apply, working-tree pollution on a failed restore. |
| `lint_log.py` | Phases 4, 10 | Drift between the log file and `template_02_mutation_testing.md` (missing keys, wrong section order, unset `rerun_type`). |
| `render_pr_comment.py` | Phase 1 (`status`), Phase 0b (`foundation`), Phase 7 (`initial`), Phase 12 (`final`) | Hand-writing ~20 KB of nested `<details>` + tables + JA mirror in `template_03_final_report.md`. Renderer enforces JA mirror, classification, N/A defaults, kill-rate formula, and final-comment invariant. |

## User-visible Preamble

Before running tools for a manual/interactive request, send one short update:

> I'll inspect the PR, run targeted coverage and mutation testing, write a repo-tracked log, fix meaningful test gaps, verify targeted coverage again, then commit the fixes and summarize the before/after result on the PR.

Keep further updates minimal unless blocked or posting the final report.

---

# Required Lifecycle

| Step | Purpose | Required output |
|---|---|---|
| 0. Triage | Assess existing test coverage to decide whether foundation tests are needed first. | Decision: proceed to mutation testing, or create foundation tests first. |
| 0b. Foundation (conditional) | Create comprehensive tests for PR-changed behavior when tests are absent or very low. | New test files/functions covering the PR's critical guarantees. |
| 1. Measure | Establish initial targeted test quality. | Baseline targeted tests, initial targeted coverage, initial mutation results. |
| 2. Log | Persist the measured initial state before changing tests/code. | Repo-tracked `.devin/mutation-testing/...md` file with YAML front matter. |
| 3. Improve | Add targeted tests/fixes for surviving mutations, uncovered PR-changed lines, and missing behavioral edge cases. | Focused test/code changes tied to the PR's behavior. |
| 4. Verify | Prove the improvements work. | Final targeted tests, final coverage, rerun surviving mutations/relevant mutation set. |
| 5. Commit | Preserve the improvement and long-term index. | Commit containing fixes plus the mutation testing log file; push if required for the PR branch. |
| 6. Report | Communicate before/after quality clearly. | Final PR comment (`mode: final`) rendered from `template_03_final_report.md`, with every initial survivor resolved as `✓ killed` or `≡ dismissed`. |

Do not skip or reorder these lifecycle steps. The foundation step may be skipped only when triage determines it is not needed.

## PR-comment posting matrix

There are exactly **three logical comment slots** — C1, C2, C3. Foundation determines whether C1 is short (`status` mode) or full (`foundation` mode). Both flows post all three comments in order.

| Comment slot | Foundation NOT run | Foundation WAS run |
|---|---|---|
| **C1** — posted at Phase 1 | `mode: status` (short preamble) | `mode: foundation` (Original → Foundation table) |
| **C2** — posted at Phase 7 | `mode: initial` (2 cols: Original / Initial-mutation) | `mode: initial` (3 cols: Original / Foundation / Initial-mutation) |
| **C3** — posted at Phase 12 | `mode: final` (3 cols: Original / Initial-mutation / Final) | `mode: final` (4 cols: Original / Foundation / Initial-mutation / Final) |

Use `render_pr_comment.py` for **every** slot. Posting via `git_comment` or `gh pr comment` with hand-written markdown is forbidden — see the `FORBIDDEN ACTIONS` section.

---

# Detailed Workflow

## Triage — Phase 0: Assess existing test coverage

Before running mutations, determine whether the PR has a meaningful test foundation to mutate against.

### Step 1: Identify the PR's changed behavior and critical guarantees

Read the PR diff, implementation files, and existing tests. Produce the internal summary (see Phase 1 below).

### Step 2: Assess test coverage level

Run the targeted test suite with coverage:

```bash
pytest <targeted tests> \
  --cov=<changed_modules> \
  --cov-report=term-missing \
  -q
```

Classify the result:

| Coverage level | Criteria | Action |
|---|---|---|
| **Absent** | No tests exist for the PR's changed behavior, or coverage of changed files is <10%. | Run Foundation phase first. |
| **Very low** | Tests exist but coverage of changed files is <30%, or critical guarantees have no assertions. | Run Foundation phase first. |
| **Moderate** | Coverage of changed files is 30–70%, some critical guarantees are tested. | Proceed to mutation testing. Note coverage gaps for the Improve phase. |
| **Good** | Coverage of changed files is >70%, most critical guarantees have assertions. | Proceed to mutation testing. |

### Step 3: Decide

- If **Absent** or **Very low**: proceed to Foundation phase (Phase 0b).
- If **Moderate** or **Good**: skip Foundation, proceed to Measure (Phase 1).

Document the triage decision in the repo-tracked log.

## Foundation — Phase 0b: Create comprehensive tests (conditional)

This phase runs only when triage determines tests are absent or very low.

### Goal

Create a comprehensive test foundation for the PR's changed behavior so that mutation testing has something meaningful to test against.

### Approach

1. For each critical guarantee identified in triage, write at least one focused test.
2. Cover the happy path, error path, and key edge cases for each changed function/method.
3. Use the project's existing test patterns (fixtures, mocking style, file organization).
4. Follow the template in `template_01_test_foundation.md` **exactly** for structuring the test plan. This is the only valid format for foundation test plans.

### Sub-agents

For large PRs touching many files, use sub-agents to parallelize test creation:
- One sub-agent per changed module or logical group of changes.
- Each sub-agent writes tests, runs them, and verifies they pass.
- Coordinate to avoid duplicate test fixtures or conflicting mock setups.

### Verification

After foundation tests are written:

```bash
pytest <new targeted tests> -q
pytest <new targeted tests> --cov=<changed_modules> --cov-report=term-missing -q
```

Required before proceeding:
- All new tests pass.
- Coverage of changed files is at least 50% (ideally higher).
- Each critical guarantee has at least one assertion.

Commit the foundation tests before proceeding to mutation testing:

```bash
git add <new test files>
git commit -m "test: add foundation tests for <feature>"
```

### Post C1 (`foundation` mode) immediately after committing

After the foundation commit is pushed, render and post C1 in `foundation` mode. The renderer enforces:

- Progression table columns `["Original", "Foundation"]` (no other shape).
- Coverage cells filled from `coverage_summary.py` output for both stages.
- Kill-rate cells set to `"N/A"` (mutations have not been run yet).
- Each `foundation_tests[]` entry carries an English description and a JA mirror.
- A non-empty `ja.summary` at the top level.

Example (abbreviated):

```bash
cat > /tmp/c1-foundation.json <<'JSON'
{
  "mode": "foundation",
  "feature_or_pr_title": "feat(mcp): include applied dashboard filters in get_chart_info",
  "summary": "Existing tests covered only 29% of changed-file lines. Devin wrote 46 foundation tests bringing coverage to 100%/100% line/branch before any mutations are applied.",
  "log_path": ".devin/mutation-testing/pr-27-2026-05-13-mcp-dashboard-filters.md",
  "progression": {
    "columns": ["Original", "Foundation"],
    "rows": {
      "tests":      ["72", "118"],
      "line_pct":   ["29%", "100%"],
      "branch_pct": ["10%", "100%"],
      "kill_rate":  ["N/A", "N/A"],
      "survived":   ["N/A", "N/A"]
    }
  },
  "foundation_tests": [{
    "file": "tests/.../test_chart_helpers.py", "added": 46,
    "covers": "chart_helpers critical guarantees",
    "ja": {"file": "tests/.../test_chart_helpers.py", "added": 46,
           "covers": "chart_helpers の重要保証"}
  }],
  "notes": ["Foundation phase triggered by coverage of 29% on changed files."],
  "ja": {
    "summary": "テスト不足のため基盤テストを 46 件追加しました。",
    "notes": ["カバレッジ 29% のため基盤フェーズを実行。"]
  }
}
JSON
.devin/mutation-testing/scripts/render_pr_comment.py /tmp/c1-foundation.json --out /tmp/c1.md
# Post /tmp/c1.md via git_comment (or `gh pr comment -F /tmp/c1.md`).
```

If Foundation is skipped, **do not skip C1** — post a `status` mode comment instead. See Phase 1 below.

## Measure — Phase 0c: Verify test environment

Before starting mutation testing, verify the test environment can run the targeted tests:

```bash
# Idempotent setup: apt deps, venv, beartype patch, nh3 upgrade.
./.devin/mutation-testing/scripts/setup_env.sh

# Cache the templates and the agent handoff from origin/master (works
# even when the PR branch under test doesn't have
# .devin/mutation-testing/templates/).
./.devin/mutation-testing/scripts/fetch_templates.sh

# Confirm collection succeeds. run_targeted.sh wraps `pytest` with the
# venv active and PY_KEY_VALUE_DISABLE_BEARTYPE=true exported so every
# subsequent run is byte-identical except for the patched source.
./.devin/mutation-testing/scripts/run_targeted.sh <targeted tests> --collect-only -q
```

If collection fails due to missing dependencies:
- Re-run `setup_env.sh` (it is idempotent); inspect its output for any apt or pip step that errored.
- Document any environment fixes needed.
- Do not proceed to baseline until collection succeeds.

For every pytest invocation in the rest of this lifecycle, use `./.devin/mutation-testing/scripts/run_targeted.sh` instead of `pytest` directly. It guarantees the venv is active, the beartype patch is honored, and PR-specific pre-existing failures (`DEVIN_PYTEST_DESELECT`) are deselected consistently.

## Measure — Phase 1: Understand the PR

Read enough evidence to understand the change before selecting mutations.

Inspect:

- PR title and description
- changed implementation files
- changed or added tests
- nearby code paths
- relevant helper functions
- validation, authorization, security, parsing, rendering, persistence, or side-effect behavior

Produce this internal summary:

```md
## PR understanding

Behavior changed:
- ...

Critical guarantees:
- ...

Relevant implementation files:
- ...

Relevant tests:
- ...

Likely risk areas:
- ...
```

Do not continue until the critical guarantees are clear.

### Post C1 (`status` mode) when Foundation is skipped

If Phase 0b did NOT run (triage classified coverage as **Moderate** or **Good**), post the short kickoff comment here — before any mutation work — so reviewers can see that the run has started.

```bash
cat > /tmp/c1-status.json <<'JSON'
{
  "mode": "status",
  "feature_or_pr_title": "<conventional commit title of the PR>",
  "summary": "Reviewing the PR's targeted test suite and experimenting with mutation notation against the changed behaviour. Initial mutation results, then a final report, will follow as separate comments.",
  "ja": {
    "summary": "該当PRのターゲットテストスイートをレビューし、変更箇所に対するミューテーション記法を検証中です。初期ミューテーション結果と最終レポートを別コメントで続けて投稿します。"
  }
}
JSON
.devin/mutation-testing/scripts/render_pr_comment.py /tmp/c1-status.json --out /tmp/c1.md
# Post /tmp/c1.md via git_comment.
```

If Phase 0b ran, C1 has already been posted in `foundation` mode — do not post a second C1 here.

## Measure — Phase 2: Identify the targeted test suite and run baseline

Select the smallest suite that should catch regressions in the PR.

Include:

- tests added by the PR,
- tests modified by the PR,
- existing tests around the touched behavior,
- lower-level unit tests for helpers/parsers,
- service/API/tool tests for externally visible behavior.

Run baseline (use the canonical wrapper, not bare `pytest`):

```bash
./.devin/mutation-testing/scripts/run_targeted.sh <targeted tests> -q
```

### Handling Baseline Failures

If baseline fails:

1. Determine whether failures are **pre-existing** (present on the base branch) or **caused by the PR**.
2. Check the base branch: `git stash && git checkout <base_branch> && pytest <failing tests> -q && git checkout - && git stash pop`.
3. If all failures are pre-existing:
   - Exclude them with `--deselect <test_id>` for the rest of the run.
   - Document which tests were deselected and why in the log.
   - Proceed with mutation testing.
4. If any failures are caused by the PR:
   - Stop mutation execution.
   - Report that mutation testing is invalid on a red baseline.
   - Include failing tests/output summary.

**Critical:** A mutation is killed ONLY if it causes test(s) that pass on the clean PR head to fail. Pre-existing failures must never be counted as mutation kills.

## Measure — Phase 3: Measure initial targeted coverage

Run targeted coverage via the helper, which emits the JSON shape that `template_02_mutation_testing.md`'s YAML front matter expects:

```bash
./.devin/mutation-testing/scripts/coverage_summary.py \
  --tests <test_path_1> --tests <test_path_2> \
  --cov <module_or_package_1> --cov <module_or_package_2> \
  --output /tmp/initial-coverage.json \
  -- --cov-report=term-missing
```

The `--` separator passes everything after it straight through to `pytest`. Keep `--cov-report=term-missing` so the term-missing output is still printed and you can use it in the Improve phase.

The JSON output already contains: targeted suite pass/fail counts, line/branch percent + covered/total, plus a `per_file` array with missing line numbers. Drop the JSON directly into `initial_state` of the log file.

Use these numbers as context. Mutation score is the stronger behavior signal, but coverage must still be high enough for the PR's changed behavior.

**Important:** Save the `term-missing` output. You will need it in the Improve phase to identify uncovered PR-changed lines, not just mutation survivors.

Coverage goal:

- Prefer the project's configured coverage threshold if one exists.
- If no threshold exists, aim for a targeted feature-file line coverage of at least 80% where practical.
- Do not chase coverage by adding brittle tests that only execute lines without asserting behavior.
- If 80% is not practical for large/shared files, report the reason and focus on changed lines/branches plus surviving mutation gaps.

## Log — Phase 4: Create the repo-tracked log file

Create a mutation testing log file in the repository.

Do this before improving tests/code. The log must preserve the measured initial state so the repository has a durable before/after index.

Recommended folder:

```text
.devin/mutation-testing/
```

Recommended filename:

```text
.devin/mutation-testing/pr-<PR_NUMBER>-<YYYY-MM-DD>-<short-slug>.md
```

This file must be committed with the PR branch.

The log is the long-term index of Devin's test-quality work. It MUST include YAML front matter and both initial and final state. Follow the schema and body structure defined in `template_02_mutation_testing.md` **exactly** — this is the only valid format for mutation testing logs. See `template_02_mutation_testing.example.md` for a correctly filled example.

Use `status: "in_progress"` while the run is still being improved/verified. Change it to `status: "completed"` only after final verification and commit.

Validate the log file before continuing to mutations:

```bash
./.devin/mutation-testing/scripts/lint_log.py .devin/mutation-testing/pr-<N>-<DATE>-<slug>.md
```

`lint_log.py` checks the YAML front matter shape, all required H2 section headings, and that `final_state.mutation_testing.rerun_type` is set when `status: completed`. Exit code 0 means the log conforms to `template_02_mutation_testing.md`. Run it again after Phase 10 (final log update).

## Measure — Phase 5: Select high-impact mutations

The goal of mutation selection is to **find real test gaps**, not to confirm things already work. Prioritize mutations that have a high chance of surviving — these are the mutations that deliver actionable value.

### Step 1: Pre-analyze coverage to identify weak spots

Before designing any mutations, review the `term-missing` coverage output from Phase 3 and the PR diff to identify:

1. **Uncovered lines/branches** in PR-changed code — these are prime mutation targets because tests don’t exercise them at all.
2. **Low branch-coverage functions** — functions with many untested branches hide implicit behavior assumptions.
3. **Complex conditional logic** — nested conditions, multi-clause guards, and exception handlers are where subtle regressions hide.
4. **Implicit contracts** — behavior that callers depend on but that has no explicit assertion (e.g., return type shape, side-effect ordering, error message format).
5. **Integration seams** — points where the PR’s code interacts with external systems, configs, or other modules.

This analysis directly informs which mutations to create. Every mutation should target a specific weak spot identified here.

### Step 2: Ensure coverage of all major failure areas

Mutations must span the PR’s major failure areas — do not cluster mutations in one category. Before finalizing the mutation plan, verify that the set covers all applicable areas from this checklist:

| Failure area | What to mutate | Why it matters |
|---|---|---|
| **Validation/guards** | Remove or invert input validation, type checks, permission gates | Lets invalid data or unauthorized access through |
| **Data integrity** | Skip normalization, escaping, encoding, formatting | Corrupts stored/transmitted data |
| **Error handling** | Replace fail-closed with fail-open, swallow exceptions, remove fallback | Silent failures in production |
| **Security boundaries** | Bypass auth checks, weaken sanitization, skip rate limits | Exploitable vulnerabilities |
| **Control flow** | Wrong execution order, skip a pipeline stage, short-circuit loops | Subtle behavioral regressions |
| **Boundary conditions** | Off-by-one, empty collections, null/None inputs, max-length values | Edge cases that crash or produce wrong results |
| **Configuration/wiring** | Hardcode a dynamic value, swap a dependency, ignore a feature flag | Integration blind spots |
| **Output contracts** | Change return type shape, omit a required field, alter ordering | Downstream consumers break silently |

Not every area applies to every PR. Skip areas that are genuinely irrelevant, but document why. If a PR touches validation logic, there must be validation mutations. If it touches error handling, there must be error-handling mutations.

### Step 3: Design mutations with breaking likelihood

Select mutations proportional to the PR's scope and number of critical guarantees:

- **Small PRs** (1–2 changed files, simple behavior): 5–8 mutations.
- **Medium PRs** (3–5 changed files, moderate complexity): 8–15 mutations.
- **Large PRs** (6+ changed files or complex behavior): 15–25 mutations.

Target approximately 2–3 mutations per critical guarantee. **Bias heavily toward gap mutations** — aim for at least 60% gap mutations (likely to survive) and at most 40% strength mutations (expected to be killed). Strength mutations are only valuable as a sanity check; gap mutations are where the real value lies.

For each mutation, assess its **breaking likelihood** — how likely it is to survive the current test suite:

| Breaking likelihood | Criteria | Priority |
|---|---|---|
| **High** | Targets uncovered lines/branches, no test asserts on this behavior, implicit contract | Design these first |
| **Medium** | Covered by tests but assertions are weak (e.g., only checks status code, not body), or tests use mocked inputs that bypass the mutated path | Include these for coverage |
| **Low** | Directly tested with strong assertions, multiple tests cover the same path | Include sparingly as sanity checks only |

Do not pad the count with low-breaking-likelihood mutations. If you cannot find enough high/medium-likelihood mutations, that signals the PR already has strong test coverage — report that finding rather than inventing weak mutations.

Mutations must be:

- **impactful** — a surviving mutation reveals a meaningful test gap, not a cosmetic difference,
- **realistic** — a developer could plausibly introduce this regression,
- **tied to the PR's critical guarantees** — not tangential behavior,
- **non-duplicative** — each mutation tests a different assertion path or failure area,
- **actionable** — if it survives, there's a clear test to write.

Include both:

1. **Gap mutations** (primary focus) — plausible regressions targeting identified weak spots; these are expected to have a real chance of surviving and reveal missing behavioral coverage.
2. **Strength mutations** (secondary) — expected to be killed; included as sanity checks to confirm critical protections exist. Keep these to a minimum.

### Good Mutation Categories (Ordered by Typical Breaking Likelihood)

| Category | Examples | Typical breaking likelihood |
|---|---|---|
| Missing preprocessing | Skip template rendering, normalization, decoding, trimming, parsing, escaping. | **High** — tests often feed pre-processed input, bypassing the pipeline |
| Wrong dependency/input | Use default dialect/config/user/context instead of the real one. | **High** — tests frequently mock dependencies, missing real integration |
| Boundary variants | Case sensitivity, whitespace, empty values, multi-statement order, null/missing fields. | **High** — edge cases are the most common coverage gap |
| Partial enum/list coverage | Remove one enum member, AST node, error type, backend, or operation type. | **High** — exhaustiveness is rarely tested fully |
| Scope reduction | Check only first item, last item, first statement, current user, first permission. | **Medium-High** — loop/collection logic is often tested with single-item inputs |
| Fail-open error handling | Replace fail-closed exception handling with allow/continue. | **Medium** — error paths vary in test coverage |
| Wrong ordering | Execute action before validation, persist before authorization, emit side effect before guard. | **Medium** — ordering is implicit and rarely asserted |
| Wrong helper | Call a broader/narrower helper with a similar name but different semantics. | **Medium** — depends on test specificity |
| Removed guard | Remove a validation branch, permission check, denylist item, AST node, or blocked operation. | **Medium-Low** — guards are often directly tested |
| Inverted condition | `if allowed` → `if not allowed`, `any` → `all`, `==` → `!=`. | **Low** — usually caught by basic happy-path tests |

Start mutation design from the top of this table (highest breaking likelihood) and work down. This maximizes the chance of finding real test gaps rather than confirming already-tested behavior.

Avoid:

- syntax errors unless syntax-error handling is the behavior being tested,
- mutations that cannot import or run,
- unrelated mutations,
- multiple mutations proving the same assertion,
- unrealistic changes no maintainer would plausibly make,
- **trivially caught mutations** — if a mutation will obviously be killed by an existing test that directly asserts on the exact value being mutated, it adds no value; replace it with a higher-impact mutation.

For manual/interactive runs, present the mutation plan before executing:

```md
## Planned mutations

1. ...
2. ...
```

## Measure — Phase 6: Execute initial mutations

**Use `mutation_runner.py`**, driven by a YAML spec. The runner applies one mutation at a time, asserts the working tree is clean before and after each one, refuses to silently no-op (the `old` block must appear exactly once), parses pytest's pass/fail counts with a regex (no case-sensitive `failed` grep), and restores the file with `git checkout --` whether the test run succeeded or crashed.

Write a YAML spec at e.g. `.devin/mutation-testing/pr-<N>-mutations.yaml`:

```yaml
test_paths:
  - tests/unit_tests/sql/parse_tests.py
  - tests/unit_tests/mcp_service/sql_lab/tool/test_execute_sql.py
mutations:
  - id: M1
    description: Remove exp.Drop from mutating_nodes
    file: superset/sql/parse.py
    indent: 12         # YAML's `|` strips leading whitespace; this puts it back
    old: |
      exp.Drop,
      exp.TruncateTable,
    new: |
      exp.TruncateTable,
```

Run it:

```bash
./.devin/mutation-testing/scripts/mutation_runner.py \
  .devin/mutation-testing/pr-<N>-mutations.yaml \
  --results /tmp/initial-mutations.json
```

The runner emits a JSON file with `killed`, `survived`, `errored`, `kill_rate`, and a per-mutation `results[]` array. Drop these directly into `initial_state.mutation_testing` of the log file. Each result also carries the `first_failing_test`, which goes in the "Caught by" column of the log's mutation results table.

Use `--only M1,M2` to focus on specific mutations (e.g., re-running only survivors in Phase 9). Use `--continue-on-error` only if you want a single broken spec entry to not stop the rest of the run.

**Hard rules the runner enforces for you:**

- If the `old` block appears zero or more than one times in `file`, the mutation is recorded as `error` (never `survived`). Silent no-ops are impossible.
- If the working tree is dirty for any target file at the start of a mutation, the runner aborts. If a restore fails after a mutation, it aborts. A contaminated baseline cannot leak into later mutations.
- Pass/fail counts come from `\d+\s+passed` / `\d+\s+failed` / `\d+\s+error` regex on pytest's summary line, so `FAILED` (uppercase) and `failed` (lowercase) are both detected. A mutation with `failed > 0` is `killed`; with `passed > 0, failed == 0` it is `survived`; with neither it is `error`.

**Do not roll your own bash/heredoc/Python mutation loop.** The earlier in-flight version of this workflow had two near-misses: every mutation labelled SURVIVED because a case-sensitive grep missed `FAILED`, and one mutation silently no-opped because the patch's Python literal was syntactically invalid. The runner exists to make both classes impossible.

Temporary mutation stashes are not final artifacts. Keep only the recorded results in the repo log.

For each mutation:

1. Restore files to PR head.
2. Apply the temporary mutation as an unstaged change.
3. Run the full targeted suite once (no `-x`).
4. Record result:
   - killed,
   - survived,
   - invalid.
5. If killed, record the specific failing test name(s).
6. Restore files to PR head.
7. Confirm `git status --short` has no mutation changes.

Suggested result shape:

```json
{
  "mutation": "Skip Jinja rendering before validation",
  "status": "survived",
  "tests_run": "28 passed",
  "caught_by": [],
  "risk": "Rendered destructive SQL is not covered"
}
```

Definitions:

- **Killed / caught**: targeted tests fail because the mutation changed protected behavior.
- **Survived / uncaught**: targeted tests still pass with the regression present.
- **Invalid**: mutation does not import, cannot run, or is not meaningful.

Metrics:

```text
initial kill rate = killed mutations / valid mutations
final   kill rate = killed mutations / (valid mutations − dismissed)
survived rate     = (survived mutations − dismissed) / valid mutations
```

The **final** kill rate excludes `dismissed` mutations from the denominator because they are functionally equivalent — no test can distinguish them from the original code. Dismissals must be justified individually (see `FORBIDDEN ACTIONS` §5).

## Report checkpoint — Phase 7: Publish C2 (`initial` mode) PR comment

Render and post C2 immediately after the initial mutation pass completes. The renderer mode is `initial`, and **every** surviving mutation **MUST** be classified now — either `pending` (Devin will write a test in Improve) or `dismissed` (functionally equivalent — explained).

### Classify each survivor

For each surviving mutation, decide its classification at C2 time:

| Decision | Use when | Required field |
|---|---|---|
| `classification: "pending"` | A test can distinguish the mutant from the original — Devin will write it in Phase 8. | `planned_test` (one-sentence test description) |
| `classification: "dismissed"` | The mutant is functionally equivalent to the original — no test can ever kill it. | `dismissal_reason` (why it is equivalent + how that was verified empirically) |

Anything you are not sure about is **`pending`**. Do not dismiss to avoid work — see `FORBIDDEN ACTIONS` §5.

### Build the JSON payload

The payload has three column shapes depending on whether Foundation ran:

- Phase 0b ran: `progression.columns = ["Original", "Foundation", "Initial mutation"]`
- Phase 0b skipped: `progression.columns = ["Original", "Initial mutation"]`

Every row in `progression.rows` (`tests`, `line_pct`, `branch_pct`, `kill_rate`, `survived`) must have the same number of cells as the column count. Unmeasured cells are `"N/A"` — never duplicates of a measured cell.

```bash
.devin/mutation-testing/scripts/render_pr_comment.py /tmp/c2-initial.json --out /tmp/c2.md
# Post /tmp/c2.md via git_comment.
```

The renderer rejects payloads that:

- omit the top-level `ja` block, or `ja.summary`,
- contain a survivor without `classification`, or with an invalid one,
- contain a `pending` survivor without `planned_test`,
- contain a `dismissed` survivor without `dismissal_reason`,
- omit `ja` mirrors on individual survivor rows,
- declare progression columns of the wrong shape for the foundation state.

## Improve — Phase 8: Fix meaningful test gaps and coverage holes

Now implement fixes based on **both** the mutation results **and** the coverage report.

### Step 1: Fix surviving mutation gaps

For each surviving mutation, add a targeted test that would kill it:

- Add tests for surviving mutation gaps.
- Strengthen weak assertions.
- Add missing edge-case inputs.
- Add small production-code fixes only if the mutation revealed a real implementation bug, not merely missing tests.

### Step 2: Review coverage gaps in PR-changed code

Review the `--cov-report=term-missing` output from Phase 3. For each file changed by the PR:

1. Identify lines/branches added or modified by the PR that are **not covered** by the targeted suite.
2. For each uncovered PR-changed line/branch, determine if it represents meaningful behavior worth testing.
3. Add tests for uncovered PR-changed behavior even if no mutation targeted it.

Mutation testing reveals whether *existing* tests catch regressions. Coverage review reveals whether the PR's *new* code is exercised at all. Both are required for high-quality test coverage.

### Step 3: Look for missing behavioral tests

Beyond mutations and line coverage, reflect on the PR's critical guarantees and ask:

- Are there edge cases not covered by any test? (e.g., empty strings, null values, special characters, boundary conditions)
- Are there code paths that are covered by line count but lack meaningful assertions?
- Are there interactions between the PR's changes and existing behavior that aren't tested?

### Guidelines

- Prefer behavior-focused tests.
- Avoid testing implementation details unless the PR's behavior is the implementation detail, such as a parser node or helper function.
- Strengthen assertions where tests only check an error response but not side effects.
- For safety/security PRs, assert that the dangerous operation was not called.
- Keep test additions targeted to the PR.
- Do not broaden into unrelated refactors.
- If a surviving mutation exposes a production bug rather than just missing coverage, make the smallest production-code fix and add a regression test.
- If a surviving mutation is intentionally accepted, document why in the log and PR comment instead of forcing a brittle test.
- If no improvement is needed, explicitly mark the improve step as `no-op` in the log and proceed to verification.

Acceptable coverage means:

- project threshold met, if configured; otherwise,
- changed behavior has strong targeted assertions, and
- **PR-changed lines and branches are covered**, and
- targeted feature-file coverage is at least 80% where practical, or a lower number is justified because the file is large/shared and changed-line coverage plus mutation results are strong.

## Verify — Phase 9: Verify after fixes

Rerun only targeted tests and targeted coverage:

```bash
./.devin/mutation-testing/scripts/run_targeted.sh <targeted tests> -q
./.devin/mutation-testing/scripts/coverage_summary.py \
  --tests <test_path_1> --tests <test_path_2> \
  --cov <module_1> --cov <module_2> \
  --output /tmp/final-coverage.json \
  -- --cov-report=term-missing
```

Rerun the mutation set, or at minimum rerun all previously surviving mutations plus high-risk strength mutations:

```bash
# Survivor-focused rerun: only the IDs that survived initially.
./.devin/mutation-testing/scripts/mutation_runner.py \
  .devin/mutation-testing/pr-<N>-mutations.yaml \
  --only M11,M12,M13,M16 \
  --results /tmp/final-mutations.json

# Or full rerun (preferred if runtime is reasonable).
./.devin/mutation-testing/scripts/mutation_runner.py \
  .devin/mutation-testing/pr-<N>-mutations.yaml \
  --results /tmp/final-mutations.json
```

If runtime is reasonable, rerun the full original mutation set for a clean final kill rate. If runtime is high, rerun:

- all initially surviving mutations,
- all mutations touching code changed during improvement,
- representative high-risk strength mutations.

In that case, clearly label the final mutation score as either `full rerun` or `survivor-focused rerun`.

Record final:

- targeted suite pass count,
- line coverage,
- branch coverage,
- kill rate,
- any remaining surviving mutations,
- explanation for any remaining gap,
- whether final mutation score came from a full rerun or survivor-focused rerun.

## Log + Commit — Phase 10: Update log and commit

Update the repo-tracked log file with:

- initial state,
- mutation plan,
- initial results,
- fixes made,
- final targeted coverage,
- final mutation results,
- final assessment,
- what's left for high-quality coverage.

Then commit:

```bash
git add <changed test/code files> .devin/mutation-testing/<log-file>.md
git commit -m "test: improve coverage for <feature>"
```

Do not use `git add .`.

If the environment requires pushing for the PR to update, push the PR branch after committing. Do not force-push unless explicitly allowed by the repository workflow.

## Verify — Phase 11: Final verification

After all mutations:

```bash
git status --short
pytest <targeted tests> -q
```

Required final state:

- working tree restored,
- no mutation code remains,
- targeted suite passes,
- coverage numbers captured,
- final mutation results captured,
- final changes committed to the PR branch.

## Report — Phase 12: Publish C3 (`final` mode) PR comment

Render and post C3 after Improve (Phase 8) and Verify (Phase 9, 11) complete. **Use `render_pr_comment.py` with `mode: "final"`** — hand-writing the ~20 KB of nested `<details>` + tables + JA mirror is forbidden (see `FORBIDDEN ACTIONS` §1).

### Final-comment invariant

Every survivor from C2 **MUST** appear in `resolved[]` as one of:

- `resolution: "killed"` with `added_test` (the test name) and `explanation` (one sentence on what the test asserts).
- `resolution: "dismissed"` with `dismissal_reason` (why the mutation is functionally equivalent + how it was verified) and `explanation`.

The renderer **rejects** payloads with `pending` entries in `final` mode — see `FORBIDDEN ACTIONS` §4. There is **no `❌ Remaining uncaught` section** in this template. The C3 comment must show zero remaining items.

### Build the JSON payload

The progression table shape depends on whether Foundation ran:

- Phase 0b ran: `progression.columns = ["Original", "Foundation", "Initial mutation", "Final"]`
- Phase 0b skipped: `progression.columns = ["Original", "Initial mutation", "Final"]`

Final kill-rate cell is computed as `killed / (total − dismissed)` — when every initial survivor has been resolved this is always 100%. The "Survived" Final cell reads `"0 (<N> dismissed)"` because the bucket renaming makes "0 remaining" the correct count.

```bash
./.devin/mutation-testing/scripts/render_pr_comment.py \
  /tmp/c3-final.json \
  --out /tmp/c3.md
# Post /tmp/c3.md via git_comment.
```

The renderer enforces every invariant programmatically. If it errors, fix the payload (or do the missing test work) and re-render — do not paste partial output to ship faster.

### Sections the renderer emits

1. **Header** — total / killed / dismissed / `0` remaining / final kill rate.
2. **Resolved** — one `<details>` per initial-survivor, badged `✓ killed` or `≡ dismissed`, with the added test or dismissal reason.
3. **Progression** — full table (3 or 4 columns) with `N/A` in unmeasured cells, plus the kill-rate-formula note.
4. **Changes made** — collapsed table of Area / Change / Result.
5. **What's left for high-quality coverage** — collapsed table of Area / Add / Why, plus test-quality note.
6. **Mutations caught** — collapsed parent accordion containing every caught mutation (originally caught + newly killed).
7. **Notes** — collapsed list of supporting facts + log path.
8. **JA** — bottom collapsed accordion mirroring every section in Japanese.

See `template_03_final_report.example.md` for a fully-filled example based on a real run.

---

# Lessons Learned from Past Mutation Testing Runs

These lessons are distilled from real mutation testing runs. They capture patterns and pitfalls that apply to any codebase, not just this one.

## Lesson 1: Pre-existing failures poison results

A pre-existing test failure unrelated to the PR can mask real mutation results. If `pytest -x` (fail-fast) is used, the runner stops at the pre-existing failure for every mutation, falsely inflating the kill rate. Always run the full targeted suite without `-x` and deselect known pre-existing failures before starting.

## Lesson 2: Coverage gaps are not the same as mutation gaps

Fixing only surviving mutations is insufficient. The `term-missing` output from coverage reports reveals uncovered lines that no mutation targeted. A function may have tests that exercise it, but never assert on the specific output the PR changed (e.g., escaping, formatting, ordering). Review both mutation survivors and coverage gaps independently.

## Lesson 3: Mutation count should scale to PR scope

Target ~2–3 mutations per critical guarantee. A PR touching 1 file with 2 guarantees needs 5–6 mutations. A PR touching 7 files with 7 guarantees needs ~15. Do not pad with redundant mutations that test the same assertion path.

## Lesson 4: Preprocessing omissions are high-value gap mutations

Skipping a preprocessing step (template rendering, normalization, escaping, decoding) before a validation or output step is a realistic bug pattern. These mutations frequently survive because tests often feed pre-processed input directly, bypassing the pipeline. Prioritize these.

## Lesson 5: Wrong-wiring mutations catch integration blind spots

Replacing a real dependency with a hardcoded default (e.g., using a literal string instead of the actual config value, or calling a similarly-named helper with different semantics) exposes whether tests verify the real integration path or just the logic in isolation.

## Lesson 6: Scope-reduction and boundary mutations are underused

Mutations that reduce scope (check only the first/last item instead of all, skip one member of an enum/list, change a boundary condition) reveal whether tests cover the full range of inputs. These are plausible regressions a developer might introduce and are often missed by line-coverage-only analysis.

## Lesson 7: A high initial kill rate signals weak mutation design, not strong tests

If every mutation in the initial run is killed, the mutations were too easy — they only confirmed what tests already protect. The goal is to *find gaps*, which means mutations should target areas where test coverage is thin or assertions are weak. Aim for an initial kill rate of 50–80%. A 100% initial kill rate means the mutation set should be redesigned with harder, more targeted mutations.

## Lesson 8: Mutations must span failure areas, not cluster in one category

A common mistake is designing 10 mutations that all test the same category (e.g., all "removed guard" mutations). This finds one type of gap at most. Spread mutations across validation, data integrity, error handling, boundaries, configuration, and output contracts. Each category reveals different kinds of test weaknesses.

## Lesson 9: Coverage-informed mutation design outperforms random selection

The most effective mutation sets are designed by first analyzing coverage data — uncovered lines, low branch percentages, implicit contracts — then crafting mutations that specifically target those weak spots. This approach finds more surviving mutations (real gaps) than selecting mutations based on code patterns alone.

## Lesson 10: Hand-writing PR comments drops the JA mirror

A past run rendered a checkpoint comment via `render_pr_comment.py`, then hand-wrote a shorter version and posted *that* — silently dropping the Japanese mirror that the renderer would have enforced. The fix: never compose markdown directly for `git_comment`/`gh pr comment` in this workflow. Always pipe a JSON payload through `render_pr_comment.py` (see `FORBIDDEN ACTIONS` §1). The renderer is the only place we can centrally enforce JA mirrors, classification, N/A handling, and the final-comment invariant.

## Lesson 11: Equivalent mutations are not failures

A mutation that produces functionally identical observable behaviour (e.g., Pydantic str-Enum coercion that serialises to byte-identical JSON, dead branches in unreachable arms) cannot be killed by any test. Past runs rendered these as `❌ Remaining uncaught`, which read as a quality failure even though no test could possibly distinguish the mutant from the original. They must be classified as `≡ dismissed` with an empirical `dismissal_reason`, and they must be excluded from the kill-rate denominator. See `FORBIDDEN ACTIONS` §5 for the bar a dismissal must meet.

## Lesson 12: Foundation tests need their own PR comment

When triage forces Phase 0b (Foundation), Devin writes most of the tests that will later be scored by the mutation pass. If the first PR comment is the initial mutation results, reviewers see "12/14 mutations killed" without realising 11 of those kills were enabled by tests Devin wrote that morning. The fix: post a dedicated **C1 (`foundation` mode) comment** immediately after the foundation commit, showing the Original → Foundation coverage jump and the test files Devin added. Then post the `initial` comment after the first mutation run.

## Lesson 13: The final comment must never carry pending items

The final PR comment is the artifact reviewers anchor on. If it shows even one `❌` survivor, the run reads as half-finished. Before posting C3, every survivor from C2 must be either killed by a new test (`resolution: killed`) or dismissed as functionally equivalent (`resolution: dismissed`). The renderer rejects `pending` in `final` mode — there is no escape hatch. Do the work, then post.

---

# What Makes a Good Mutation

Good mutations are **impactful** (surviving reveals a meaningful test gap, not a cosmetic difference), **plausible** (a developer could realistically introduce this regression), **targeted** (tied to the PR's critical guarantees), **actionable** (a surviving mutation points to a specific missing test), **non-duplicative** (each mutation tests a different assertion path), and **coverage-informed** (designed based on analysis of uncovered lines, weak branches, and implicit contracts).

**The best mutation is one that survives.** A 100% kill rate on the initial run does not mean the mutations were good — it may mean they were too easy. If every mutation is trivially caught, the mutation set failed to probe the real weaknesses. Aim for an initial kill rate of 50–80%; this indicates the mutations are genuinely testing coverage boundaries.

## High-Value Mutation Patterns

| Pattern | Example | Why it's high-value |
|---|---|---|
| Skip preprocessing step | Skip template rendering, escaping, normalization, or decoding before validation | Tests often feed pre-processed input directly, never exercising the pipeline |
| Hardcode a dependency | Replace dynamic config/dialect/context with a literal default | Tests frequently mock dependencies, missing whether real values are wired correctly |
| Boundary condition shift | Change `>=` to `>`, or `<` to `<=` | Off-by-one errors are the most common class of subtle bugs |
| Partial list/enum coverage | Remove one member from an exhaustive match | Exhaustiveness is rarely tested — removing one case often goes unnoticed |
| Case/whitespace sensitivity | Remove `.lower()`, `.strip()`, add trailing space to a comparison | Text normalization is frequently assumed but not asserted |
| Scope reduction | Process only first item, skip iteration, short-circuit a loop | Tests with single-item inputs never catch scope reductions |
| Output contract violation | Omit a required field from a return dict, change ordering of results | Downstream consumers depend on shape, but tests often only check partial structure |
| Implicit ordering dependency | Execute side effect before its guard, reorder pipeline stages | Ordering is implicit and almost never directly asserted |

## Lower-Value Mutation Patterns

| Pattern | Example | Why it's lower-value |
|---|---|---|
| Remove validation guard | Remove a permission check or blocklist entry | Usually caught by existing tests that directly test the guard |
| Invert boolean condition | `if allowed` → `if not allowed`, `==` → `!=` | Trivially caught by any test that exercises the happy path |
| Reverse error handling | Allow operation to proceed on parse/validation error | Often caught if error tests exist |

---

# Mutation Selection Priorities (Ordered by Breaking Likelihood)

1. skipped preprocessing/rendering/normalization/escaping (highest chance of surviving)
2. hardcoded dependency replacing dynamic config/dialect/context
3. boundary condition shifts (off-by-one, empty, null, max-length)
4. partial enum/list/AST-node coverage (remove one member)
5. scope reduction — process only first/last item instead of all
6. case, whitespace, separator sensitivity omissions
7. output contract violations (missing field, wrong ordering, changed shape)
8. wrong execution order (side effect before guard)
9. wrong helper with similar name but different semantics
10. fail-open exception handling
11. removed validation guard (often already well-tested)
12. inverted condition (lowest priority — usually trivially caught)

---

# PR Comment Requirements

**`template_03_final_report.md` is the only valid format for PR comments.** No other comment format is permitted. All PR comments — both checkpoint (Phase 7) and final (Phase 12) — must use this template.

Use GitHub-native markdown only:

- markdown tables,
- `<details><summary>...</summary>` accordions,
- no screenshots,
- no external formatting dependencies.

Style rules (encoded in the template):

- Default visible content is English only.
- Put remaining uncaught/surviving mutations first.
- Use `❌` for remaining uncaught mutation accordions.
- Use `✓` only for individual fixed/caught mutations.
- Do not put `✓` on the parent fixed/caught-mutations accordion.
- Each expanded remaining uncaught finding has:
  - English table: `Finding / Details`,
  - divider: `---`,
  - Japanese table under `#### JA`.
- Fixed/caught mutations are collapsed under one parent accordion.
- Bottom `JA` accordion translates:
  - summary,
  - high-quality coverage next steps,
  - test-quality comment,
  - coverage + mutation score table,
  - comments.
- Keep everything brief and at-a-glance.
- Include both initial and final state when fixes are made.
- Mention what Devin fixed to close the gaps.

If you are unsure how to fill any section, refer to `template_03_final_report.example.md` for a complete worked example.

---

# Final Agent Prompt

```md
You are validating and improving the tests for the current PR using mutation testing and targeted coverage review.

Outcome:
Produce a repo-tracked mutation testing log plus a concise GitHub PR comment showing initial findings, fixes made, final targeted coverage, final mutation kill rate, and what remains for high-quality test coverage.

Required lifecycle:
triage → [foundation] → measure → log → improve → verify → commit → report

The foundation step is conditional — run it only if triage finds tests are absent or very low (<30% coverage on changed files).

Constraints:
- Do not commit mutation code.
- Do not leave mutation code in the working tree.
- Do not modify tests during initial measurement.
- Handle pre-existing baseline failures by identifying and deselecting them, not by aborting.
- Do not use pytest -x or --exitfirst during mutation runs.
- After initial measurement, add targeted tests/fixes for meaningful gaps.
- Commit the fixes and `.devin/mutation-testing/...` log file to the PR branch.
- Do not run the full app test suite unless explicitly requested; use targeted tests relevant to this PR.
- If no meaningful gaps are found and coverage is acceptable, mark improve as no-op, commit the log, and report.
- All structured outputs (foundation plan, mutation log, PR comments) MUST follow their corresponding template files exactly:
  - Foundation test plan → template_01_test_foundation.md
  - Mutation testing log → template_02_mutation_testing.md
  - PR comments (checkpoint AND final) → template_03_final_report.md
  No other comment or log format is permitted.

Workflow:
0. Triage: read the PR, assess existing test coverage. If absent or <30%, create foundation tests first.
0b. Foundation (conditional): write comprehensive tests for PR-changed behavior using sub-agents if needed. Commit before proceeding.
1. Measure: identify changed behavior, critical guarantees, relevant files/tests, and likely risk areas.
2. Measure: identify and run the targeted test suite. Handle pre-existing failures via --deselect.
3. Measure: run initial targeted pytest-cov coverage for relevant changed feature files. Save term-missing output.
4. Measure: select and execute mutations proportional to PR scope:
   - Small PRs (1-2 files): 5-8 mutations
   - Medium PRs (3-5 files): 8-15 mutations
   - Large PRs (6+ files): 15-25 mutations
   - Target ~2-3 mutations per critical guarantee
   - Include both strength and gap mutations
   - Apply one mutation at a time (default), run full targeted suite (no -x), restore, continue
5. Log: create `.devin/mutation-testing/pr-<PR_NUMBER>-<YYYY-MM-DD>-<slug>.md` with YAML front matter and initial state.
6. Report checkpoint: post/update an initial PR comment with coverage, mutation results, and what Devin will fix.
7. Improve: add targeted tests/fixes for:
   a. Meaningful surviving mutations.
   b. Uncovered PR-changed lines/branches identified from term-missing output.
   c. Missing behavioral edge cases not revealed by mutations but visible from code review.
   Mutation testing reveals whether existing tests catch regressions. Coverage review reveals whether new code is exercised. Both are required.
8. Verify: rerun targeted tests, targeted coverage, and the relevant mutation set.
9. Log: update the log with final state.
10. Commit: commit the fixes and log file to the PR branch; push if required for the PR to update.
11. Report: update the PR comment with the final before/after report using template_03_final_report.md exactly. This is the only valid PR comment format.

Mutation selection priorities (ordered by breaking likelihood — design from top down):
1. skipped preprocessing/rendering/normalization/escaping (highest survival rate)
2. hardcoded dependency replacing dynamic config/dialect/context
3. boundary condition shifts (off-by-one, empty, null, max-length)
4. partial enum/list/AST-node coverage (remove one member)
5. scope reduction — process only first/last item instead of all
6. case, whitespace, separator sensitivity omissions
7. output contract violations (missing field, wrong ordering, changed shape)
8. wrong execution order (side effect before guard)
9. wrong helper with similar name but different semantics
10. fail-open exception handling
11. removed validation guard (often already well-tested)
12. inverted condition (lowest priority — usually trivially caught)

Mutation quality requirements:
- At least 60% gap mutations (likely to survive), at most 40% strength mutations
- Every mutation must target a specific identified weak spot from coverage/code analysis
- Mutations must span all applicable major failure areas (validation, data integrity, error handling, security, control flow, boundaries, configuration, output contracts)
- Do not pad with low-value mutations that will be trivially caught

Report metrics:
- targeted suite pass rate
- feature-file line coverage
- feature-file branch coverage
- mutation kill rate
- survived mutation rate

Report style:
- English visible by default.
- Japanese only inside expanded finding sections and the bottom JA accordion.
- Remaining uncaught mutations first with `❌`; if none remain, state that no surviving mutations remained after targeted fixes.
- Fixed/caught mutations collapsed under one parent accordion; use `✓` only for individual fixed/caught mutations.
- Use markdown tables and GitHub `<details>` accordions.
- Keep the summary minimal and at-a-glance.
```

---

# Knowledge Base Contribution

After completing the mutation testing workflow (all phases through Report), add a knowledge note to the Devin knowledge base summarizing how to run mutation tests on this repository. This serves two purposes: it helps future Devin sessions run mutation tests without re-discovering the setup, and it demonstrates that the agent can synthesize operational knowledge from its work.

Use the Devin MCP `create_knowledge_note` tool to create a note with:

- **Name**: `Mutation testing runbook — <repo_name>`
- **Scope**: Retrieved when working on testing, coverage, or mutation testing tasks in this repository.
- **Body** containing:
  1. The targeted test command used (e.g., `pytest <paths> --deselect <known failures> -q`).
  2. The coverage command used (e.g., `pytest <paths> --cov=<modules> --cov-report=term-missing --cov-branch -q`).
  3. Any environment setup required (dependency installs, virtualenv activation, test database, etc.).
  4. Known pre-existing test failures that should be deselected.
  5. Mutation testing conventions: log file location (`.devin/mutation-testing/`), template files used, commit message format.
  6. Any repo-specific quirks discovered during the run (e.g., slow test suites, flaky tests, import issues).

Keep the note concise and actionable — a future agent should be able to run mutation tests on a new PR using only this note and the handoff instructions.

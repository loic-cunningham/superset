---
pr_id: 28
pr_title: "chore: clean up mutation testing framework for demo readiness"
run_date: "2026-05-13"
agent: "devin"
repo: "loic-cunningham/superset"
branch: "devin/1778642662-cleanup-mutation-testing-framework"
base_branch: "master"
mode: "mutation-testing-and-test-improvement"
status: "completed"

triage:
  coverage_level: "absent"
  foundation_needed: true
  deselected_tests: []

target:
  behavior:
    - "lint_log.py enforces every required H2 section, including the newly added 'Weak spot analysis' and 'Mutation quality self-assessment' sections, in the canonical order"
    - "lint_log.py validates the YAML front matter shape (status enum, top-level keys, initial_state/final_state schema, rerun_type rule for completed runs)"
    - "mutation_runner.py keeps mutation application atomic: unique-match enforcement, indentation-aware substitution, working-tree restore, kill/survived/error classification"
    - "render_pr_comment.py validates payload shape, mirrors initial→final in checkpoint mode, and renders every section of the Stage 3 template (EN + JA) without dropping the no-survivors notice or division-by-zero guard"
    - "coverage_summary.py emits the JSON shape consumed by the mutation log file (rounded percentages, sorted per_file entries, branch-aware totals)"
  implementation_files:
    - ".devin/mutation-testing/scripts/lint_log.py"
    - ".devin/mutation-testing/scripts/mutation_runner.py"
    - ".devin/mutation-testing/scripts/render_pr_comment.py"
    - ".devin/mutation-testing/scripts/coverage_summary.py"
  test_files:
    - ".devin/mutation-testing/tests/test_lint_log.py"
    - ".devin/mutation-testing/tests/test_mutation_runner.py"
    - ".devin/mutation-testing/tests/test_render_pr_comment.py"
    - ".devin/mutation-testing/tests/test_coverage_summary.py"

initial_state:
  targeted_tests:
    command: "run_targeted.sh .devin/mutation-testing/tests/ --cov=.devin/mutation-testing/scripts --cov-branch -q"
    passed: 95
    failed: 0
  coverage:
    line:
      percent: 86
      covered: 388
      total: 437
    branch:
      percent: 77
      covered: 116
      total: 150
  mutation_testing:
    valid_mutations: 15
    killed: 15
    survived: 0
    kill_rate: 100

final_state:
  targeted_tests:
    command: "run_targeted.sh .devin/mutation-testing/tests/ --cov=.devin/mutation-testing/scripts --cov-branch -q"
    passed: 101
    failed: 0
  coverage:
    line:
      percent: 88
      covered: 394
      total: 437
    branch:
      percent: 81
      covered: 122
      total: 150
  mutation_testing:
    valid_mutations: 18
    killed: 18
    survived: 0
    kill_rate: 100
    rerun_type: "full"

commits:
  - "9fc22700a188b1db5d8e44325b70fb64590846b9"
  - "1f9c74dcb92a545d1d759f29e31fb8fe719d02c5"

artifacts:
  pr_comment_url: ""
---

# Mutation Testing Log — PR #28

## PR understanding

Behavior changed:
- `lint_log.py` adds two new H2 sections to `REQUIRED_SECTIONS`: `Weak spot analysis` and `Mutation quality self-assessment`. Log files that pre-date this PR will fail lint until updated.
- All other Python scripts (`mutation_runner.py`, `render_pr_comment.py`, `coverage_summary.py`, `run_targeted.sh`, `setup_env.sh`, `fetch_templates.sh`) and the GitHub Actions workflow receive docstring/comment tightening only — no functional change.
- Two stale demo log files were removed: `pr-14-2026-05-13-devin-mutation-testing-workflow.md` and `pr-22-2026-05-13-mutation-prompt-improvements.md`.
- `README.md` rewritten to describe the current script set.

Critical guarantees:
- `lint_log.py` rejects any mutation log file that omits one of the now-mandatory H2 sections, leaves them out of order, drops a required YAML front-matter key, or marks `status: completed` without a valid `final_state.mutation_testing.rerun_type`.
- `mutation_runner.py` applies each mutation atomically — uniqueness check, indentation-aware substitution, working-tree restore — and classifies results from pytest output (case-sensitive `FAILED` line, errors counted as failures).
- `render_pr_comment.py` validates payload shape (mode enum, required state keys), mirrors initial→final in checkpoint mode, renders every section of the Stage 3 template in both English and Japanese, never divides by zero on kill_rate, and keeps the "no surviving mutations" placeholder when `surviving` is empty.
- `coverage_summary.py` rounds percentages with banker's rounding, sorts per-file entries alphabetically, emits `branch_percent: None` for files with no branches, and emits the canonical totals block consumed by the log.

Relevant implementation files:
- `.devin/mutation-testing/scripts/lint_log.py`
- `.devin/mutation-testing/scripts/mutation_runner.py`
- `.devin/mutation-testing/scripts/render_pr_comment.py`
- `.devin/mutation-testing/scripts/coverage_summary.py`

Relevant tests:
- `.devin/mutation-testing/tests/test_lint_log.py` (new in this run)
- `.devin/mutation-testing/tests/test_mutation_runner.py` (new in this run)
- `.devin/mutation-testing/tests/test_render_pr_comment.py` (new in this run)
- `.devin/mutation-testing/tests/test_coverage_summary.py` (new in this run)

Likely risk areas:
- Required-sections drift: the lint check is the only guard against forgetting one of the two newly mandatory sections. A regression there silently approves non-conformant logs.
- Status / rerun_type enum drift: silently accepting an unknown status or a missing `rerun_type` lets a half-finished run be marked `completed`.
- Mutation runner's indent + uniqueness checks: a single accidental non-unique match would silently mutate the wrong code site.
- pytest output parsing case-sensitivity: matching `failed` instead of `FAILED` would attribute the wrong test as the first failing one.
- Kill-rate division-by-zero guard: removing it crashes the PR-comment renderer on a totally-empty mutation run.

## Triage decision

Coverage level: absent
Foundation needed: yes
Deselected tests: none
Reason: Before this run, the four Python scripts under `.devin/mutation-testing/scripts/` had **zero** test coverage anywhere in the repo. Because the PR adds two new required sections to `lint_log.py` and tightens docstrings across the framework, mutation testing is only meaningful if the surrounding behavior is also pinned by tests. We therefore ran the Foundation phase and added a unit-test suite at `.devin/mutation-testing/tests/` (95 tests, 4 files, 1377 lines) before measuring mutation kill rate.

## Initial targeted coverage

| File | Line % | Branch % | Covered/Total lines |
|---|---|---|---|
| `.devin/mutation-testing/scripts/lint_log.py` | 96 | 94 | 106/109 |
| `.devin/mutation-testing/scripts/mutation_runner.py` | 86 | 76 | 137/154 |
| `.devin/mutation-testing/scripts/render_pr_comment.py` | 95 | 86 | 110/113 |
| `.devin/mutation-testing/scripts/coverage_summary.py` | 48 | 17 | 35/61 |
| **TOTAL** | **86** | **77** | **388/437** |

Uncovered PR-changed lines:
- `lint_log.py:123,127,137` — error branches for non-mapping `coverage`, non-mapping coverage axis, and non-mapping `mutation_testing` blocks.
- `mutation_runner.py:97-122,187-194` — `_git` subprocess wrapper, `_assert_tree_clean`, `_restore`, and `_run_tests` subprocess; intentionally not unit-tested because they shell out to git / `run_targeted.sh`. Their orchestration is covered indirectly through the `main()` smoke test.
- `mutation_runner.py:231-233,341-347` — RuntimeError path inside `_run_one` when `_apply_mutation` fails post-write (no easy unit-test path that doesn't depend on git).
- `render_pr_comment.py:108,136` — `if not data: continue` guards inside `_render_caught_block` / `_render_surviving_block` (entry with no matching `ja` block when `japanese=True`).
- `render_pr_comment.py:319` — stdout fallback in `main()` when `--out` is omitted.
- `coverage_summary.py:64-107` — `_run_pytest_with_coverage` subprocess; mocked in tests because it shells out to `run_targeted.sh`.

## Weak spot analysis

Pre-mutation coverage analysis identified these weak spots for targeted mutation design:
- `lint_log.py:REQUIRED_SECTIONS` is a literal list and a regression that drops one of the two **new** required sections would not crash anything; only a section-level assertion in tests can catch it. → Mutations M1 and M2.
- `lint_log.py:_check_front_matter_shape` and `_check_sections` are sensitive to operator inversion (`not in`/`in`, `<`/`>=`, `==`/`!=`) — these are easy to flip silently. → Mutations M3, M4, M5, M6.
- `mutation_runner.py:_apply_indent` skips empty lines on purpose (`prefix + line if line else line`). Removing the conditional pads empty lines and breaks YAML-style trailing newlines downstream. → Mutation M7.
- `mutation_runner.py:_apply_mutation` enforces unique matches (`count > 1` raises). Dropping the guard would silently mutate the first occurrence and pass tests. → Mutation M8.
- `mutation_runner.py:_classify` priority order matters — `failed > 0 → killed` must come before `passed > 0 → survived`, otherwise a partially-failing run looks like a survivor. → Mutation M9.
- `mutation_runner.py:_FAILED_LINE_RE` matches **uppercase** `FAILED` exactly. A lowercase regex would let lowercase tracebacks pollute the first-failing-test field. → Mutation M10.
- `render_pr_comment.py:_validate` mode enum and `_kill_rate` zero-total guard are single-line behavioral checks easily lost in a refactor. → Mutations M11, M12.
- `render_pr_comment.py:_render_surviving_block` emits a template-required HTML comment when the list is empty. Returning the empty string drops a downstream signal. → Mutation M13.
- `coverage_summary.py:_per_file_entries` sorts files alphabetically — alphabetical order is part of the log file output contract. → Mutation M14.
- `coverage_summary.py:_pct` rounds with `round()`; truncating with `int()` shifts every reported percentage. → Mutation M15.

Failure area coverage:
| Failure area | Applicable? | Mutations targeting it |
|---|---|---|
| Validation/guards | yes | M1, M2, M3, M4, M6, M11 |
| Data integrity | yes | M7, M8 |
| Error handling | yes | M5, M12 |
| Security boundaries | no | n/a |
| Control flow | yes | M9 |
| Boundary conditions | yes | M5, M15 |
| Configuration/wiring | yes | M6 |
| Output contracts | yes | M13, M14 |

## Initial mutation plan

| ID | File | Mutation | Category | Breaking likelihood | Rationale |
|---|---|---|---|---|---|
| M1 | `lint_log.py` | Drop `"Weak spot analysis"` from `REQUIRED_SECTIONS` | Validation/guards | high | This is exactly the section that PR #28 added. Without an assertion enforcing it, the regression is silent. |
| M2 | `lint_log.py` | Drop `"Mutation quality self-assessment"` from `REQUIRED_SECTIONS` | Validation/guards | high | Companion to M1; the second new required section. |
| M3 | `lint_log.py` | Flip `status not in {...}` to `status in {...}` | Validation/guards | high | Inversion silently accepts every invalid status. |
| M4 | `lint_log.py` | `rerun_type not in {"full", "survivor_focused"}` → `rerun_type not in {"full"}` | Validation/guards | medium | Drops `survivor_focused` from the allowed enum. |
| M5 | `lint_log.py` | Remove out-of-order section error | Error handling | medium | Logs would silently shuffle section order. |
| M6 | `lint_log.py` | Drop `"artifacts"` from `REQUIRED_TOP_KEYS` | Configuration/wiring | medium | Required key list is the only enforcement of front-matter completeness. |
| M7 | `mutation_runner.py` | `_apply_indent` pads empty lines | Data integrity | high | Breaks YAML literal-block round-trips with trailing newlines. |
| M8 | `mutation_runner.py` | `_apply_mutation` no longer enforces uniqueness | Data integrity | high | Silent wrong-site mutation; the single most important safety net. |
| M9 | `mutation_runner.py` | `_classify` checks `passed` before `failed` | Control flow | high | Partial-failure runs would be classified as `survived`. |
| M10 | `mutation_runner.py` | `_FAILED_LINE_RE` matches lowercase `failed` | Output contracts | medium | First-failing-test attribution becomes noisy. |
| M11 | `render_pr_comment.py` | Skip `mode` enum validation in `_validate` | Validation/guards | medium | Allows arbitrary modes through. |
| M12 | `render_pr_comment.py` | Remove zero-total guard in `_kill_rate` | Error handling | medium | Crashes the renderer on empty mutation runs. |
| M13 | `render_pr_comment.py` | `_render_surviving_block` returns empty string when empty | Output contracts | low | Drops the downstream "no survivors" template marker. |
| M14 | `coverage_summary.py` | `_per_file_entries` skips alphabetical sort | Output contracts | medium | Stable per-file ordering is part of the log file contract. |
| M15 | `coverage_summary.py` | `_pct` truncates instead of rounding | Boundary conditions | medium | Every reported percentage shifts by up to one. |

Gap/strength ratio: 13/15 gap mutations (87%) — only M5 and M13 are subtle behavioral mutations near already-covered paths; the rest specifically target weak spots identified from the coverage analysis.

## Initial mutation results

| ID | Mutation | Status | Caught by |
|---|---|---|---|
| M1 | Drop `Weak spot analysis` from REQUIRED_SECTIONS | killed | `test_lint_requires_every_section_heading[Weak spot analysis]` |
| M2 | Drop `Mutation quality self-assessment` | killed | `test_lint_requires_every_section_heading[Mutation quality self-assessment]` |
| M3 | Invert status validation guard | killed | `test_lint_accepts_valid_completed_log` |
| M4 | rerun_type drops `survivor_focused` | killed | `test_lint_accepts_known_rerun_types[survivor_focused]` |
| M5 | Remove out-of-order section error | killed | `test_lint_detects_out_of_order_sections` |
| M6 | Drop `artifacts` from REQUIRED_TOP_KEYS | killed | `test_lint_reports_missing_top_keys` |
| M7 | `_apply_indent` pads empty lines | killed | `test_apply_indent_skips_empty_lines` |
| M8 | `_apply_mutation` no uniqueness check | killed | `test_apply_mutation_raises_when_old_string_not_unique` |
| M9 | `_classify` swaps priority | killed | `test_classify_obeys_priority_rules[5-1-killed]` |
| M10 | `_FAILED_LINE_RE` lowercase | killed | `test_parse_pytest_output_extracts_pass_and_fail_counts` |
| M11 | Skip mode validation | killed | `test_validate_rejects_unknown_mode` |
| M12 | Remove zero-total guard | killed | `test_kill_rate_handles_zero_division_and_rounding[0-0-0]` |
| M13 | Empty surviving block returns empty string | killed | `test_render_surviving_block_empty_returns_template_comment` |
| M14 | Skip per-file sort | killed | `test_per_file_entries_computes_branch_percent` |
| M15 | `_pct` truncates | killed | `test_pct_rounds_to_integer[0.6-1]` |

Kill rate: 15/15 (100%)

## Fix plan

### Mutation gap fixes
- No surviving mutations to fix.

### Coverage gap fixes
- `lint_log.py:123,127,137` — non-mapping coverage / non-mapping coverage axis / non-mapping mutation_testing blocks need explicit assertions so a future regression that silently accepts non-dict YAML is caught. → Add three small tests to `test_lint_log.py`.
- `render_pr_comment.py:108,136` — JA rendering of an entry with no `ja` block must be skipped silently. → Add JA-no-data tests to `test_render_pr_comment.py`.
- `render_pr_comment.py:319` — `main()` without `--out` should write to stdout. → Add a stdout-fallback test.

### Behavioral gap fixes
- None beyond the coverage gaps above. The mutation analysis confirmed the foundation suite already exercises every behavioral guarantee of the PR.

## Changes made

| File | Change | Kills/Covers |
|---|---|---|
| `.devin/mutation-testing/tests/conftest.py` | New — loads each script via `importlib` so tests can call its public helpers directly. | enables all foundation tests |
| `.devin/mutation-testing/tests/test_lint_log.py` | New — 38 tests covering filename pattern, YAML front-matter shape, status enum, every required section heading (including the two new ones from PR #28), section ordering, rerun_type rule, and multi-path `main()`. | M1, M2, M3, M4, M5, M6 |
| `.devin/mutation-testing/tests/test_mutation_runner.py` | New — 21 tests covering indent prefix logic, unique-match enforcement, pytest output parsing (passed/failed/error, first-FAILED extraction, case sensitivity), kill/survived/error classification, and `main()` JSON shape with `--only` filtering. | M7, M8, M9, M10 |
| `.devin/mutation-testing/tests/test_render_pr_comment.py` | New — 23 tests covering payload validation, checkpoint→final mirroring, `_kill_rate` div-by-zero, surviving/caught block rendering for EN and JA, table fallbacks, and `render()` end-to-end smoke. | M11, M12, M13 |
| `.devin/mutation-testing/tests/test_coverage_summary.py` | New — 13 tests covering percentage rounding, per-file entry shape with and without branches, alphabetical sort, and `main()` JSON output shape (including the zero-branch fallback block). | M14, M15 |
| `.devin/mutation-testing/tests/test_lint_log.py` | Improve phase — add tests for non-mapping `coverage`, non-mapping axis (`line`/`branch`), and non-mapping `mutation_testing` to close the three lint_log.py coverage gaps. | covers lint_log.py:123,127,137 |
| `.devin/mutation-testing/tests/test_render_pr_comment.py` | Improve phase — add tests for caught/surviving JA-no-data skipping and `main()` stdout fallback. | covers render_pr_comment.py:108,136,319 |
| `.devin/mutation-testing/pr-28-mutations.yaml` | New — 15-mutation YAML spec for the run, kept in repo so the run is reproducible. | n/a |
| `.devin/mutation-testing/pr-28-2026-05-13-cleanup-mutation-testing-framework.md` | New — this log file. | n/a |

## Final verification

Targeted suite: 101 passed, 0 failed
Line coverage: 88% (394/437)
Branch coverage: 81% (122/150)
Kill rate: 18/18 (100%) — full rerun

Per-file final coverage:

| File | Line % | Branch % |
|---|---|---|
| `lint_log.py` | 100 | 100 |
| `render_pr_comment.py` | 99 | 94 |
| `mutation_runner.py` | 86 | 76 |
| `coverage_summary.py` | 48 | 17 |

The Improve phase added 3 mutations (M16–M18) targeting the branches that the Improve-phase tests cover. All 3 were killed by the corresponding new tests, confirming the new tests are meaningful rather than coverage-only.

## Final assessment

PR #28 is a cleanup-only PR for the mutation-testing tooling itself: tightened docstrings, a rewritten `README.md`, removal of two stale log files, and one functional change in `lint_log.py` (the addition of `Weak spot analysis` and `Mutation quality self-assessment` to `REQUIRED_SECTIONS`). Before this run, the four Python scripts the framework relies on had no test coverage anywhere in the repo.

The Foundation phase landed a 101-test suite at `.devin/mutation-testing/tests/` that covers:

- every required-section heading in `lint_log.py` (including the two new ones from this PR), every front-matter validation rule, and the `rerun_type` enum for completed runs;
- the atomic mutation contract in `mutation_runner.py` (indent prefix, uniqueness check, pytest output parsing, killed/survived/error classification, JSON results shape, `--only` filtering);
- `render_pr_comment.py` payload validation, checkpoint→final mirroring, `_kill_rate` division-by-zero safety, EN+JA rendering of caught/surviving/changes/gaps/notes blocks, and `main()` exit codes including the stdout fallback;
- `coverage_summary.py` percentage rounding, per-file sort and shape, and `main()` JSON output (with and without branches).

The initial mutation run executed 15 mutations targeted at the weak spots identified in the coverage analysis (87% gap mutations); all were killed (100% kill rate). The Improve phase added 6 small tests to close the remaining `lint_log.py` and `render_pr_comment.py` branches that were technically uncovered, and added 3 corresponding mutations (M16–M18) to confirm the new tests are meaningful. All 18 mutations are now killed.

Uncovered code is concentrated in `_run_pytest_with_coverage`, `_run_tests`, and the `_git` helpers — these all shell out to git or `run_targeted.sh` and are intentionally mocked rather than exercised end-to-end. They are listed in "What's left for high-quality coverage" below as the highest-value future investment.

## What's left for high-quality coverage

| Area | Missing test | Why it matters |
|---|---|---|
| `mutation_runner._run_tests` subprocess | An end-to-end test that actually invokes `run_targeted.sh` against a tiny throwaway test file and verifies pass/fail extraction. | The current suite mocks `_run_tests`. A regression in the subprocess flag set (e.g. forgetting `--tb=no`) would not be caught. |
| `mutation_runner._git` git interactions | Tests that run against a temp git repo to verify `_assert_tree_clean` raises and `_restore` actually restores. | Working-tree pollution is the worst failure mode; the current suite asserts the contract at the `_run_one` level via mocks. |
| `coverage_summary._run_pytest_with_coverage` | A real pytest invocation against a tiny test file, exercising the JSON-temp-file plumbing and the missing-coverage-JSON error path. | Currently mocked. A change to how coverage JSON is produced could go undetected. |
| `mutation_runner._run_one` error-restore path | A test that mocks `_apply_mutation` to raise after the file has been touched, verifying that the working tree is still restored. | Defensive coding only — the happy path is covered, but the exact restore behavior on partial failure is not asserted. |

These are coverage opportunities identified from term-missing output and behavioral analysis, not just surviving mutations.

## Mutation quality self-assessment

- Initial kill rate: 100% (15/15) — mutations could have been harder. With every mutation targeting a weak spot identified in the coverage analysis and a brand-new foundation suite written specifically to enforce those guarantees, a 100% kill rate is plausible but indicates that next iterations should add subtler behavioral mutations (e.g., off-by-one in `_check_sections.last_seen` so that two identical headings collide silently, JA pluralization on the "newly fixed" suffix, partial-prefix `[Ff]AILED` regex matching, or mutating `_apply_indent`'s empty-line condition with `is None` instead of `else line`).
- Final kill rate: 100% (18/18) after the Improve phase added 3 mutations (M16–M18) against the newly-covered branches. The new mutations were killed by the new tests, confirming the tests added behavior rather than just visit lines.
- Gap/strength ratio: 16/18 (89% gap) — mutations were heavily biased toward identified weak spots in the four scripts.
- Failure areas covered: 7/8 applicable — every category except `Security boundaries` (no security-sensitive code in this PR).
- Mutations informed by coverage analysis: 18/18 — every mutation maps to a specific source line or expression identified in the Weak spot analysis section.
- Honest weakness: the subprocess boundary (`_run_tests`, `_run_pytest_with_coverage`, `_git`) is mocked rather than exercised end-to-end. A regression in how mutation_runner shells out to `run_targeted.sh` would not be caught by this suite. That gap is documented in "What's left for high-quality coverage" above.

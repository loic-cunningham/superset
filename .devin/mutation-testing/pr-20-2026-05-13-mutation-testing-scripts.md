---
pr_id: 20
pr_title: "Add reusable mutation-testing tooling under .devin/mutation-testing/"
run_date: "2026-05-13"
agent: "devin"
repo: "loic-cunningham/superset"
branch: "devin/1778638266-mutation-testing-tooling"
base_branch: "master"
mode: "mutation-testing-and-test-improvement"
status: "completed"

triage:
  coverage_level: "absent"
  foundation_needed: true
  deselected_tests: []

target:
  behavior:
    - "lint_log.py validates Stage 2 log files against the template_02 schema"
    - "render_pr_comment.py renders Stage 3 PR comments per template_03"
    - "coverage_summary.py reshapes pytest-cov JSON into the log/PR-comment shape"
    - "mutation_runner.py applies mutations one-at-a-time, classifies, and restores"
  implementation_files:
    - ".devin/mutation-testing/scripts/lint_log.py"
    - ".devin/mutation-testing/scripts/render_pr_comment.py"
    - ".devin/mutation-testing/scripts/coverage_summary.py"
    - ".devin/mutation-testing/scripts/mutation_runner.py"
  test_files:
    - ".devin/mutation-testing/scripts/tests/test_lint_log.py"
    - ".devin/mutation-testing/scripts/tests/test_render_pr_comment.py"
    - ".devin/mutation-testing/scripts/tests/test_coverage_summary.py"
    - ".devin/mutation-testing/scripts/tests/test_mutation_runner.py"

initial_state:
  targeted_tests:
    command: "pytest .devin/mutation-testing/scripts/tests/ -q"
    passed: 95
    failed: 0
  coverage:
    line:
      percent: 87
      covered: 394
      total: 437
    branch:
      percent: 79
      covered: 118
      total: 150
  mutation_testing:
    valid_mutations: 11
    killed: 10
    survived: 1
    kill_rate: 91

final_state:
  targeted_tests:
    command: "pytest .devin/mutation-testing/scripts/tests/ -q"
    passed: 102
    failed: 0
  coverage:
    line:
      percent: 89
      covered: 400
      total: 437
    branch:
      percent: 83
      covered: 124
      total: 150
  mutation_testing:
    valid_mutations: 11
    killed: 10
    survived: 1
    kill_rate: 91
    rerun_type: "full"

commits:
  - "a3a6238fa2662befeb89b47d070a8afc74a41b50"

artifacts:
  pr_comment_url: ""
---

# Mutation Testing Log — PR #20

## PR understanding

Behavior changed:
- Introduces `.devin/mutation-testing/` as the shared home for mutation-testing tooling.
- Adds four Python scripts (`lint_log.py`, `render_pr_comment.py`, `coverage_summary.py`, `mutation_runner.py`) that future agents invoke to triage, measure, log, and report on PR test quality.
- Adds two shell helpers (`setup_env.sh`, `run_targeted.sh`, `fetch_templates.sh`) that provision a venv, deselect known-bad tests, and pull template files from `origin/master`.
- Adds a README and a `pyproject.toml` ruff exclusion for the scripts directory.

Critical guarantees:
- `lint_log.py` rejects any Stage 2 log file that deviates from the documented YAML schema and section ordering (filename pattern, top-level keys, status enum, coverage/mutation_testing sub-keys, `rerun_type` enum on completed runs, required H2 headings in order).
- `render_pr_comment.py` produces a Stage 3 PR comment whose structure matches `template_03_final_report.md` exactly — header counts, coverage table, surviving/caught accordions, EN/JA blocks — and refuses payloads that violate its input contract.
- `coverage_summary.py` emits a JSON summary whose numeric fields round consistently (`_pct`), whose per-file entries are sorted by path, and whose `branch` block degrades gracefully when no branches exist.
- `mutation_runner.py` applies each mutation exactly once against a clean tree, classifies the result as `killed` / `survived` / `error`, and restores the worktree afterwards regardless of test outcome.

Relevant implementation files:
- `.devin/mutation-testing/scripts/lint_log.py`
- `.devin/mutation-testing/scripts/render_pr_comment.py`
- `.devin/mutation-testing/scripts/coverage_summary.py`
- `.devin/mutation-testing/scripts/mutation_runner.py`

Relevant tests:
- `.devin/mutation-testing/scripts/tests/test_lint_log.py`
- `.devin/mutation-testing/scripts/tests/test_render_pr_comment.py`
- `.devin/mutation-testing/scripts/tests/test_coverage_summary.py`
- `.devin/mutation-testing/scripts/tests/test_mutation_runner.py`

Likely risk areas:
- **Schema drift in `lint_log`**: a single inverted `in`/`not in` or off-by-one ordering check would let invalid logs ship.
- **PR-comment template fidelity in `render_pr_comment`**: silent label/suffix changes (EN vs. JA, "newly fixed", "Caught by" / "検出テスト") that don't affect summary counts but produce malformed reports.
- **Mutation-runner classification in `mutation_runner`**: getting `_classify` boundary wrong (`>` vs. `>=`) or losing error counts in `_parse_pytest_output` would falsify kill rates.
- **Numeric reshaping in `coverage_summary`**: dropping the `sorted(...)` over per-file entries or replacing `round` with truncation would silently produce non-deterministic logs.

## Triage decision

Coverage level: absent
Foundation needed: yes
Deselected tests: none
Reason: PR #20 ships four new Python modules totalling 437 statements with zero accompanying tests. No file under `.devin/mutation-testing/scripts/` is exercised by the existing Superset test suite, and the modules sit outside the `superset/` package. A foundation test suite was created under `.devin/mutation-testing/scripts/tests/` covering the pure data-shaping helpers directly and the subprocess-driven entry points through monkeypatched boundaries.

## Initial targeted coverage

| File | Line % | Branch % | Covered/Total lines |
|---|---|---|---|
| `.devin/mutation-testing/scripts/lint_log.py` | 96% | 94% | 106/109 |
| `.devin/mutation-testing/scripts/render_pr_comment.py` | 93% | 83% | 109/113 |
| `.devin/mutation-testing/scripts/mutation_runner.py` | 90% | 80% | 143/154 |
| `.devin/mutation-testing/scripts/coverage_summary.py` | 51% | 22% | 36/61 |
| **TOTAL** | **87%** | **79%** | **394/437** |

Uncovered PR-changed lines:
- `lint_log.py:117` — `state.coverage` itself not being a mapping (only the per-axis check is exercised).
- `lint_log.py:121` — `state.coverage` missing top-level `line`/`branch` keys.
- `lint_log.py:135` — `state.mutation_testing` itself not being a mapping.
- `render_pr_comment.py:134` — empty `caught` list path through `_render_caught_block`.
- `render_pr_comment.py:139` — `caught` entry that omits the `ja` block in Japanese mode.
- `render_pr_comment.py:167` — `surviving` entry that omits the `ja` block in Japanese mode.
- `coverage_summary.py:69-112` — `_run_pytest_with_coverage` subprocess body. Tested behaviourally through `main()` via a monkeypatched runner; the subprocess + pytest-output parsing path is intentionally out-of-scope for unit tests (would require shelling out to pytest in a sandbox).
- `mutation_runner.py:110-119, 124-126, 135, 200-207, 337` — `_git`, `_assert_tree_clean`, `_restore`, `_run_tests` subprocess wrappers and the human-readable table printer. Tested behaviourally through `_run_one` and `main()` via monkeypatched fakes; the real `git` + `subprocess` path is out-of-scope for unit tests.

## Initial mutation plan

| ID | File | Mutation | Category | Expected |
|---|---|---|---|---|
| M1 | `lint_log.py` | Invert `status not in {"in_progress", "completed"}` check | Boolean operator | strength |
| M2 | `lint_log.py` | Invert section ordering comparison (`idx < last_seen` → `idx > last_seen`) | Relational operator | strength |
| M3 | `lint_log.py` | Drop `"survivor_focused"` from `rerun_type` allowed set | Set-membership | gap |
| M4 | `render_pr_comment.py` | Invert mode allow-list check (`mode not in` → `mode in`) | Boolean operator | strength |
| M5 | `render_pr_comment.py` | Replace `dict(initial)` with `initial` (no copy) in checkpoint mode | Reference-vs-copy | gap |
| M6 | `render_pr_comment.py` | Drop `and not japanese` guard on `(newly fixed)` suffix | Boolean operator | gap |
| M7 | `render_pr_comment.py` | `_kill_rate` fallback `0` → `100` when total is 0 | Constant-default | strength |
| M8 | `coverage_summary.py` | Stop sorting per-file entries by path | Function call removal | gap |
| M9 | `coverage_summary.py` | Replace `int(round(num))` with `int(num)` in `_pct` | Function call removal | strength |
| M10 | `mutation_runner.py` | `_classify`: `failed > 0` → `failed >= 0` | Relational operator | strength |
| M11 | `mutation_runner.py` | `_parse_pytest_output`: `failed += int(m_error.group(1))` → `failed = int(...)` | Augmented assignment | gap |

## Initial mutation results

| ID | Mutation | Status | Caught by |
|---|---|---|---|
| M1 | `lint_log`: invert status-value membership check | killed | `test_filename_matching_pattern_passes` (and 5 others) |
| M2 | `lint_log`: invert section ordering comparison | killed | `test_filename_matching_pattern_passes` (and 4 others) |
| M3 | `lint_log`: drop `survivor_focused` from rerun_type allowed set | killed | `test_completed_status_with_survivor_focused_rerun_type_passes` |
| M4 | `render_pr_comment`: invert mode allow-list check | killed | `test_validate_accepts_valid_final_payload` (and 26 others) |
| M5 | `render_pr_comment`: drop `dict()` copy of initial in checkpoint mode | killed | `test_validate_mirrors_initial_into_final_in_checkpoint_mode` |
| M6 | `render_pr_comment`: always render `(newly fixed)` suffix, including JA | **survived** | — |
| M7 | `render_pr_comment`: `_kill_rate` fallback 0 → 100 when total is 0 | killed | `test_kill_rate_zero_total_returns_zero` |
| M8 | `coverage_summary`: stop sorting per-file entries by path | killed | `test_per_file_entries_sorted_by_path` |
| M9 | `coverage_summary`: truncate instead of round in `_pct` | killed | `test_pct_rounds_half_to_even_or_up` (and 3 others) |
| M10 | `mutation_runner`: classify boundary shift (`failed >= 0`) | killed | `test_classify_returns_survived_when_only_passing` (and 2 others) |
| M11 | `mutation_runner`: error count overwrites instead of adding to failed | killed | `test_parse_pytest_output_counts_failed_and_errors_together` |

Kill rate: 10/11 (91%)

## Fix plan

### Mutation gap fixes
- **M6** (`render_pr_comment.py:140-142` — drop `and not japanese`): analysis shows this is an **equivalent mutation**. The original code defines `suffix` and `ja_suffix` as mutually exclusive (only one is non-empty per `japanese` value) and combines them with `ja_suffix or suffix`. The mutation makes `suffix` non-empty in both modes, but the short-circuit on `ja_suffix or suffix` masks the difference in JA mode. No test can distinguish the two implementations as long as the combining expression stays `ja_suffix or suffix`. Documented in **What's left for high-quality coverage** with a recommended source simplification.

### Coverage gap fixes
- `lint_log.py:117` — add test exercising `state.coverage` value that is not a mapping (e.g., `"broken"`), expecting `"initial_state.coverage must be a mapping"`.
- `lint_log.py:121` — add test exercising `state.coverage` mapping that omits `branch` (or `line`), expecting `"initial_state.coverage missing keys: ['branch']"`.
- `lint_log.py:135` — add test exercising `state.mutation_testing` value that is not a mapping, expecting `"initial_state.mutation_testing must be a mapping"`.
- `render_pr_comment.py:134` — add test calling `render()` with empty `caught` list; assert the caught-mutations accordion header still renders (`✓ 0 mutations caught (0 newly fixed)`) and the body is empty.
- `render_pr_comment.py:139` — add test exercising a caught entry whose `ja` block is missing in Japanese rendering; assert that entry is silently skipped (no exception, no leaked `name`).
- `render_pr_comment.py:167` — same as above for `_render_surviving_block`.

### Behavioral gap fixes
- Lock down the `_render_caught_block` summary header text so future refactors that change `"N mutations caught (M newly fixed)"` are caught.
- Lock down that the Japanese surviving-block header (`生存ミューテーション`) appears in the rendered comment.

## Changes made

| File | Change | Kills/Covers |
|---|---|---|
| `.devin/mutation-testing/scripts/tests/test_lint_log.py` | Added `test_state_coverage_object_not_a_mapping_fails` | Covers `lint_log.py:117` (wrapping `coverage:` value not a mapping). |
| `.devin/mutation-testing/scripts/tests/test_lint_log.py` | Added `test_state_coverage_missing_axis_fails` | Covers `lint_log.py:121` (`coverage:` missing `line`/`branch` axis). |
| `.devin/mutation-testing/scripts/tests/test_lint_log.py` | Added `test_state_mutation_testing_object_not_a_mapping_fails` | Covers `lint_log.py:135` (wrapping `mutation_testing:` value not a mapping). |
| `.devin/mutation-testing/scripts/tests/test_render_pr_comment.py` | Added `test_render_with_empty_caught_renders_zero_count_header` | Covers `render_pr_comment.py:134` (empty `caught` list → empty body, header shows `0`). |
| `.devin/mutation-testing/scripts/tests/test_render_pr_comment.py` | Added `test_render_skips_caught_entry_missing_ja_block` | Covers `render_pr_comment.py:139` (caught entry without `ja` key is skipped in JA mode). |
| `.devin/mutation-testing/scripts/tests/test_render_pr_comment.py` | Added `test_render_skips_surviving_entry_missing_ja_block` | Covers `render_pr_comment.py:167` (surviving entry without `ja` key is skipped in JA mode). |
| `.devin/mutation-testing/scripts/tests/test_render_pr_comment.py` | Added `test_caught_summary_header_uses_final_killed_count` | Defense-in-depth lock on the EN/JA caught accordion summary using `final.killed`. |

## Final verification

Targeted suite: 102 passed, 0 failed
Line coverage: 89% (400/437)
Branch coverage: 83% (124/150)
Kill rate: 10/11 (91%) — full rerun

Per-file coverage after improvements:

| File | Initial line % | Final line % | Initial branch % | Final branch % |
|---|---:|---:|---:|---:|
| `.devin/mutation-testing/scripts/lint_log.py` | 96% | **100%** | 94% | **100%** |
| `.devin/mutation-testing/scripts/render_pr_comment.py` | 93% | **97%** | 83% | **92%** |
| `.devin/mutation-testing/scripts/mutation_runner.py` | 90% | 90% | 80% | 80% |
| `.devin/mutation-testing/scripts/coverage_summary.py` | 51% | 51% | 22% | 22% |

## Final assessment

Mutation testing on PR #20 closed every meaningful gap the initial run revealed. The single survivor, **M6** (`render_pr_comment.py` — drop the `and not japanese` guard on the `(newly fixed)` suffix), is an **equivalent mutation**. The surrounding combiner `head = f"...{ja_suffix or suffix}"` short-circuits on the non-empty `ja_suffix` whenever `japanese=True`, so the mutation's behavior change is unobservable from any caller. No test can kill M6 while the combiner stays in that form; killing it would require restructuring the source. A source-side simplification is recommended (see _What's left for high-quality coverage_ below).

The improvement phase added 7 tests addressing the term-missing gaps identified in the initial run, taking targeted coverage from 95→102 tests, 87%→89% line and 79%→83% branch. `lint_log.py` is now at **100% line and branch** coverage; `render_pr_comment.py` rose to **97% line / 92% branch**. The remaining uncovered lines in `coverage_summary.py` (lines 69-112) and `mutation_runner.py` (`_git`, `_assert_tree_clean`, `_restore`, `_run_tests`, table printer) are subprocess wrappers around `pytest` and `git`, intentionally out of scope for unit tests and exercised behaviourally through monkeypatched fakes.

The mutation kill rate is stable at 91% across the full rerun, confirming no regression. The new tests also raise the bar against future near-equivalent mutations targeting the same areas (e.g., re-ordering of accordion text, change of `final.killed` to `len(caught)` in the caught-summary header).

## What's left for high-quality coverage

| Area | Missing test | Why it matters |
|---|---|---|
| `render_pr_comment.py` — `(newly fixed)` suffix | None — recommend source simplification | M6 is an equivalent mutation. The `suffix` / `ja_suffix` pair plus the `ja_suffix or suffix` combiner makes the `and not japanese` guard logically redundant. Removing the guard (or refactoring to a single conditional) would be semantically equivalent _and_ make the code mutation-testable in this region. |
| `coverage_summary.py:69-112` (`_run_pytest_with_coverage`) | Subprocess-level test with a stubbed `pytest` runner producing real coverage JSON | Currently tested only through the `main()` monkeypatch path. A subprocess-level test would catch regressions in the command-line construction (`--cov-branch`, `--cov-report=json:...`, `--tb=no`) and in the summary-line parser used to count passed/failed. |
| `mutation_runner.py` subprocess wrappers (`_git`, `_assert_tree_clean`, `_restore`, `_run_tests`, table printer at L337) | Integration-style test that drives a real temporary git repo through `_run_one` | Currently exercised via monkeypatched fakes. An integration test would catch regressions in real-world git invocation and the post-mutation cleanup sequence. |

These are coverage opportunities identified from term-missing output and behavioral analysis, beyond the surviving (equivalent) mutation.

# Template: Test Foundation Plan (Stage 1 — Conditional)

This template is used when the triage phase determines that the PR's changed behavior has little or no existing test coverage (absent or <30% line coverage on changed files).

The goal is to create a comprehensive test foundation before mutation testing begins, so that mutations have something meaningful to test against.

This is an **internal planning document**, not a PR comment. The PR-facing Foundation announcement is rendered separately via `render_pr_comment.py --mode foundation` (see `template_03_final_report.md` for the comment shape). Both must be produced when Phase 0b runs.

---

## Test foundation plan — {{pr_title}}

### Triage result

| Metric | Value |
|---|---|
| PR | #{{pr_number}} |
| Changed files | {{changed_file_count}} |
| Existing test coverage (changed files) | {{existing_coverage_percent}} |
| Existing tests for changed behavior | {{existing_test_count}} |
| Decision | **Create foundation tests** |
| Reason | {{triage_reason}} |

### Critical guarantees to cover

<!-- List each critical guarantee from the PR understanding phase. Each must have at least one test. -->

| # | Critical guarantee | Priority | Target test location |
|---|---|---|---|
| 1 | {{guarantee_1}} | {{high/medium}} | {{test_file_path_1}} |
| 2 | {{guarantee_2}} | {{high/medium}} | {{test_file_path_2}} |
| 3 | {{guarantee_3}} | {{high/medium}} | {{test_file_path_3}} |

### Test plan per changed file

<!-- Repeat this block for each changed implementation file that needs tests. -->

#### {{implementation_file_path}}

**Changed behavior:**
- {{behavior_description}}

**Tests to create:**

| Test name | What it verifies | Inputs | Expected outcome |
|---|---|---|---|
| `{{test_name_1}}` | {{verification_1}} | {{input_description_1}} | {{expected_1}} |
| `{{test_name_2}}` | {{verification_2}} | {{input_description_2}} | {{expected_2}} |
| `{{test_name_3}}` | {{verification_3}} | {{input_description_3}} | {{expected_3}} |

**Edge cases:**
- {{edge_case_1}}
- {{edge_case_2}}

**Mocking requirements:**
- {{mock_description}}

### Sub-agent assignments (if applicable)

<!-- For large PRs, assign groups of test files to sub-agents. -->

| Sub-agent | Module/files | Test file(s) to create | Target coverage |
|---|---|---|---|
| 1 | {{module_1}} | {{test_file_1}} | {{target_1}} |
| 2 | {{module_2}} | {{test_file_2}} | {{target_2}} |

### Verification checklist

After foundation tests are written:

- [ ] All new tests pass: `pytest <new tests> -q`
- [ ] Coverage of changed files is at least 50%
- [ ] Each critical guarantee has at least one assertion
- [ ] Tests follow project conventions (fixtures, mocking style, file organization)
- [ ] Foundation tests committed: `git commit -m "test: add foundation tests for <feature>"`

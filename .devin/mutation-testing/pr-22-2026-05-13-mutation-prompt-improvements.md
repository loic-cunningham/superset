---
pr_id: 22
pr_title: "docs: improve mutation testing prompt to prioritize high-impact, high-breaking-chance mutations"
run_date: "2026-05-13"
agent: "devin"
repo: "loic-cunningham/superset"
branch: "devin/1778639050-mutation-quality-improvements"
base_branch: "master"
mode: "mutation-testing-and-test-improvement"
status: "completed"

triage:
  coverage_level: "not_applicable"
  foundation_needed: false
  deselected_tests: []
  rationale: >
    The PR is documentation-only. It modifies three Markdown files under
    .devin/docs/ that describe Devin's mutation testing prompt, the log
    template (template_02_mutation_testing.md), and the example for that
    template. No Python, TypeScript, JavaScript, YAML, TOML, or other
    executable source files are changed. There is no production behavior
    to mutate and no test suite that targets these documentation files.

target:
  behavior:
    - "Restructure Phase 5 of the mutation testing handoff into 3 steps (weak-spot pre-analysis, failure-area coverage checklist, breaking-likelihood design)"
    - "Shift mutation ratio guidance to at least 60% gap mutations / at most 40% strength mutations"
    - "Reorder mutation categories in the handoff by typical breaking likelihood (preprocessing/dependency wiring first, inverted conditions last)"
    - "Add weak-spot analysis, failure-area coverage, breaking-likelihood, gap/strength ratio, and mutation-quality self-assessment sections to template_02_mutation_testing.md"
    - "Update template_02_mutation_testing.example.md to demonstrate the new template format with rationale and ordering"
    - "Add 3 lessons learned (Lessons 7, 8, 9) covering weak mutation design, failure-area clustering, and coverage-informed design"
  implementation_files:
    - ".devin/docs/mutation_testing_agent_handoff.md"
    - ".devin/docs/template_02_mutation_testing.md"
    - ".devin/docs/template_02_mutation_testing.example.md"
  test_files: []

initial_state:
  targeted_tests:
    command: "n/a — no Python/TS test suite is associated with the changed Markdown files"
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
    command: "n/a — no Python/TS test suite is associated with the changed Markdown files"
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
    rerun_type: "n/a"

verifications:
  - tool: "git diff --name-only $(git merge-base master HEAD)..HEAD"
    result: "only .devin/docs/*.md files changed; no .py/.ts/.tsx/.js/.jsx/.yml/.yaml/.toml diffs"
  - tool: "grep -nE '^(\\+|-)\\s*(import |from |def |class |const |function |let |var )' on PR diff"
    result: "no executable-language diffs detected — diff lines are Markdown content only"

commits: []

artifacts:
  pr_comment_url: ""
---

# Mutation Testing Log — PR #22

## PR understanding

Behavior changed:
- Restructures Phase 5 ("Select high-impact mutations") in
  `.devin/docs/mutation_testing_agent_handoff.md` into three explicit
  steps: pre-analyze coverage to identify weak spots, ensure failure-area
  coverage, and design mutations with a breaking-likelihood rating.
- Shifts guidance on mutation composition to require at least 60% gap
  mutations and at most 40% strength mutations.
- Reorders the mutation category table and the "Mutation selection
  priorities" list by typical breaking likelihood (preprocessing,
  wrong-wiring, boundary, partial enum at the top; removed-guard and
  inverted-condition at the bottom).
- Adds three new lessons learned (Lessons 7, 8, 9) on weak mutation
  design, failure-area clustering, and coverage-informed mutation design.
- Adds five new sections to `template_02_mutation_testing.md`:
  weak-spot analysis, failure-area coverage matrix, breaking-likelihood
  column in the mutation plan, gap/strength ratio, and a
  mutation-quality self-assessment.
- Updates `template_02_mutation_testing.example.md` to demonstrate the
  new format with concrete weak-spot rationale and ordering.

Critical guarantees (documentation-level, not unit-testable):
- The handoff Markdown remains valid for downstream consumers
  (the `Devin Mutation Testing` GitHub Actions workflow that reads each
  template file and embeds it verbatim into the Devin prompt).
- All four required template filenames continue to exist at the paths
  the workflow expects (`mutation_testing_agent_handoff.md`,
  `template_01_test_foundation.md`, `template_02_mutation_testing.md`,
  `template_03_final_report.md`).
- The numbered sub-section structure in Phase 5 is internally
  consistent with itself and with the "Final Agent Prompt" appendix.

Relevant implementation files:
- `.devin/docs/mutation_testing_agent_handoff.md`
- `.devin/docs/template_02_mutation_testing.md`
- `.devin/docs/template_02_mutation_testing.example.md`

Relevant tests:
- None. The repository does not contain pytest or jest tests that
  exercise Markdown content in `.devin/docs/`. The downstream consumer
  is the `Devin Mutation Testing` workflow, which only reads each file
  via `fs.existsSync` / `fs.readFileSync` and embeds the raw content
  into a Devin prompt; there is no semantic test of the Markdown body.

Likely risk areas:
- Internal cross-references between Phase 5 steps and the appended
  "Mutation selection priorities" list drifting out of sync.
- Template additions (weak-spot analysis, failure-area coverage,
  mutation-quality self-assessment) not being reflected in
  `template_02_mutation_testing.example.md`.
- Guidance contradictions between the new 60/40 ratio and pre-existing
  guidance elsewhere in the handoff.

All of these risks are documentation-quality risks. They are validated
by human review of the rendered Markdown, not by a unit test in this
repository.

## Triage decision

Coverage level: not applicable.
Foundation needed: no.
Deselected tests: none.

Reason: the PR's changed files are all Markdown documents under
`.devin/docs/`. The mutation-testing handoff itself states that the
workflow targets Python (`pytest <targeted tests>`) or TypeScript
(`jest`) behavior in PR-changed source code. There is no such source
code in this PR. Writing a synthetic "foundation" test against a
Markdown body would not reflect any production code path that
maintainers test, and the existing PR #14 log establishes the
precedent for handling this case as a documented no-op.

What we did verify (out of scope for mutation testing, but checked for
basic sanity):

| Check | Tool | Result |
|---|---|---|
| Only Markdown files are touched | `git diff --merge-base master HEAD --name-only` | three `.devin/docs/*.md` files |
| No executable-language diffs | filtered `git diff` for `.py/.ts/.tsx/.js/.jsx/.yml/.yaml/.toml` | no matches |
| Required template files still present | `ls .devin/docs/` | all four template files (`mutation_testing_agent_handoff.md`, `template_01_test_foundation.md`, `template_02_mutation_testing.md`, `template_03_final_report.md`) exist |

## Initial targeted coverage

Not applicable. No Python/TS module is changed.

| File | Line % | Branch % | Covered/Total lines |
|---|---|---|---|
| `.devin/docs/mutation_testing_agent_handoff.md` | n/a | n/a | n/a |
| `.devin/docs/template_02_mutation_testing.md` | n/a | n/a | n/a |
| `.devin/docs/template_02_mutation_testing.example.md` | n/a | n/a | n/a |
| **TOTAL** | **n/a** | **n/a** | **n/a** |

Uncovered PR-changed lines: not applicable — the files are static
Markdown documentation read verbatim by the Devin Mutation Testing
GitHub Actions workflow and are not subject to runtime evaluation in
this repository.

## Weak spot analysis

Not applicable. There is no executable code surface in the PR diff
from which to identify uncovered lines, low branch-coverage functions,
implicit contracts, or integration seams.

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

None of these failure areas apply because the PR changes only
documentation Markdown; there is no executable behavior to break.

## Initial mutation plan

No mutation plan was generated. Mutating a Markdown document would
either (a) introduce a syntactic break in YAML front matter or
Markdown headings (which would surface only at consumer-side rendering
or workflow read-time, not in a unit test), or (b) introduce a
semantic change to documentation prose that no automated test
asserts against in this repository.

| ID | File | Mutation | Category | Breaking likelihood | Rationale |
|---|---|---|---|---|---|
| — | — | n/a — no applicable mutation surface | n/a | n/a | Documentation-only PR; no executable code to mutate |

Gap/strength ratio: n/a (0 mutations planned).

## Initial mutation results

| ID | Mutation | Status | Caught by |
|---|---|---|---|
| — | n/a | n/a | — |

Kill rate: n/a (0 valid mutations).

## Fix plan

### Mutation gap fixes
- None — no mutations executed.

### Coverage gap fixes
- None — no Python/TS source code is modified by this PR.

### Behavioral gap fixes
- None applicable to this repo's pytest/jest suites.

## Changes made

| File | Change | Kills/Covers |
|---|---|---|
| `.devin/mutation-testing/pr-22-2026-05-13-mutation-prompt-improvements.md` | New log file documenting the triage decision and no-op outcome. | Provides the repo-tracked traceability artifact required by the mutation-testing handoff. |

No test or production code was added or modified by this run.

## Final verification

Targeted suite: n/a — no Python/TS test suite is associated with the
changed Markdown files.

Line coverage: n/a.
Branch coverage: n/a.
Kill rate: n/a (0 valid mutations) — n/a rerun.

Additional sanity checks performed:
- `git diff --merge-base master HEAD --name-only` shows only three
  Markdown files under `.devin/docs/` are touched by the PR.
- `ls .devin/docs/` confirms all four required template files
  (`mutation_testing_agent_handoff.md`, `template_01_test_foundation.md`,
  `template_02_mutation_testing.md`, `template_03_final_report.md`) are
  still present and reachable by `.github/workflows/devin-mutation-testing.yml`.

## Final assessment

The PR introduces no testable Python or TypeScript behavior; it only
rewrites portions of the Devin mutation testing prompt and its log
template. The mutation-testing framework's preconditions (a targeted
pytest/jest suite around the changed behavior) are not met.

Per the handoff's explicit guidance —
"If no meaningful gaps are found and coverage is already acceptable,
the improve step is a no-op; still log, verify, commit the log, and
report" — and consistent with the precedent set by the PR #14 log
(workflow-only PR also treated as a documented no-op), this run is
recorded as:

- Triage classified the PR as not applicable for mutation testing
  (documentation-only diff).
- No mutations were executed (none would be valid against Markdown).
- No tests were added or modified.
- The PR diff was sanity-checked to confirm only `.devin/docs/*.md`
  files are touched and that the required template filenames remain
  reachable by the consumer workflow.
- This log file is committed to the PR branch for traceability.

## What's left for high-quality coverage

| Area | Missing test | Why it matters |
|---|---|---|
| `.devin/docs/*.md` template structural validity | A repository-level linter that asserts each template still contains its mandated sections (YAML front matter schema for `template_02_*`, accordion structure for `template_03_*`, etc.) so future edits cannot silently drop required sections. | The Devin Mutation Testing workflow embeds these files verbatim into agent prompts. Silent removal of a section would degrade downstream mutation runs without any CI signal. |
| `.devin/docs/*.md` cross-reference integrity | An assertion that filenames referenced from inside `mutation_testing_agent_handoff.md` (e.g. `template_01_test_foundation.md`, `template_02_mutation_testing.md`, `template_03_final_report.md`) actually exist on disk. | Prevents drift between the handoff's instructions and the actual template file names if a future PR renames a template. |
| Phase numbering / section linkage check | A test asserting that the "Required lifecycle" table, the body of the handoff, and the "Final Agent Prompt" appendix all agree on phase numbering and ordering. | This PR specifically restructures Phase 5; future edits could re-introduce drift between the lifecycle table, the prose, and the appendix. |

These are coverage opportunities at the repo level for future PRs and
are intentionally not added here, since this PR is a documentation
update and the maintainers have not requested such linting.

## Mutation quality self-assessment

- Initial kill rate: n/a — no mutations were executed.
- Gap/strength ratio: n/a — no mutations were planned.
- Failure areas covered: 0 / 0 applicable — none of the eight failure
  areas in the new failure-area checklist apply to a Markdown-only diff.
- Mutations informed by coverage analysis: n/a — no coverage data
  exists for Markdown files.

This run intentionally produced no mutations. Consistent with the
precedent established by the PR #14 log, generating "synthetic"
mutations against documentation Markdown would inflate the recorded
mutation count without providing any signal about the quality of any
test suite, and would directly contradict the handoff's own guidance
to avoid low-value mutations.

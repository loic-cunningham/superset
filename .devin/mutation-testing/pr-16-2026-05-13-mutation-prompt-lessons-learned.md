---
pr_id: 16
pr_title: "docs: replace PR-specific mutation examples with abstract lessons and add knowledge base section"
run_date: "2026-05-13"
agent: "devin"
repo: "loic-cunningham/superset"
branch: "devin/1778636310-mutation-prompt-lessons-learned"
base_branch: "master"
mode: "mutation-testing-and-test-improvement"
status: "completed"

triage:
  coverage_level: "not_applicable"
  foundation_needed: false
  deselected_tests: []
  rationale: >
    The PR is documentation- and CI-config-only. It modifies
    .devin/docs/mutation_testing_agent_handoff.md (rewriting the
    "Good Mutation Examples from PR #4" and "Lessons learned from PR #3
    run" sections into a codebase-agnostic "Lessons Learned" + "What
    Makes a Good Mutation" set, and adding a new "Knowledge Base
    Contribution" section), and trims
    .github/workflows/devin-mutation-testing.yml (removes the "Comment
    on PR" step, drops the corresponding pr_number/pr_url/pr_title
    outputs, and tightens permissions from `issues: write` /
    `pull-requests: write` to `pull-requests: read`). No Python or
    TypeScript source code is added or modified, and no test files are
    added or modified. The mutation-testing framework defined in
    .devin/docs/mutation_testing_agent_handoff.md targets unit-testable
    Python (pytest) or TypeScript (jest) behavior, neither of which
    applies here.

target:
  behavior:
    - "Mutation-testing handoff document conveys reusable, codebase-agnostic lessons rather than PR-specific tables"
    - "Handoff document instructs agents to add a Devin knowledge note after completing the run"
    - "Workflow YAML still triggers on pull_request: [opened] and via workflow_dispatch with a PR number input"
    - "Workflow still sparse-checks out .devin/docs/ and embeds the handoff + 3 templates verbatim into the Devin prompt"
    - "Workflow no longer creates PR comments from CI (Devin posts the comment via git_comment) and runs with read-only PR permissions"
  implementation_files:
    - ".devin/docs/mutation_testing_agent_handoff.md"
    - ".github/workflows/devin-mutation-testing.yml"
  test_files: []

initial_state:
  targeted_tests:
    command: "n/a — no Python/TS test suite is associated with the changed files"
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
    command: "n/a — no Python/TS test suite is associated with the changed files"
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
  - tool: "@action-validator/cli"
    command: "action-validator .github/workflows/devin-mutation-testing.yml"
    result: "VALID"
  - tool: "node --check"
    targets:
      - "embedded `actions/github-script` body in step: Prepare Devin prompt (wrapped in async function for top-level await)"
      - "embedded `actions/github-script` body in step: Create Devin session (wrapped in async function for top-level await)"
    result: "all parse OK"
  - tool: "ls .devin/docs/"
    expected:
      - "mutation_testing_agent_handoff.md"
      - "template_01_test_foundation.md"
      - "template_02_mutation_testing.md"
      - "template_03_final_report.md"
    result: "all four files referenced by the workflow are present"
  - tool: "grep"
    target: ".github/workflows/devin-mutation-testing.yml"
    checks:
      - "permissions narrowed to `pull-requests: read` (no `issues: write` / `pull-requests: write` remain)"
      - "no `Comment on PR` step remains in the workflow"

commits:
  - "07d9cf3a01"

artifacts:
  pr_comment_url: ""
---

# Mutation Testing Log — PR #16

## PR understanding

Behavior changed:

- `.devin/docs/mutation_testing_agent_handoff.md`:
  - Replaces the "Good Mutation Examples from PR #4" section (concrete
    tables of strength/gap mutations from a previous destructive-DDL
    PR) with a codebase-agnostic "Lessons Learned from Past Mutation
    Testing Runs" section enumerating five reusable lessons.
  - Replaces the "Good and Bad Mutation Examples from PR #3 run"
    section (concrete tables tied to db_engine_specs escaping work)
    with a generic "What Makes a Good Mutation" section that defines
    strength-mutation and gap-mutation *patterns* with abstract
    examples.
  - Adds a new "Knowledge Base Contribution" section at the bottom of
    the handoff instructing the agent to create a Devin knowledge note
    summarizing how to run mutation tests on the repository.
- `.github/workflows/devin-mutation-testing.yml`:
  - Removes the `Comment on PR` step that previously posted a GitHub
    issue comment with the session link from CI.
  - Removes the `core.setOutput('pr_number' | 'pr_url' | 'pr_title')`
    calls that fed that step.
  - Tightens job-level `permissions` from `contents: read`,
    `issues: write`, `pull-requests: write` to `contents: read`,
    `pull-requests: read`. The session-launching agent (Devin) now
    posts PR comments itself via `git_comment`, so write permissions
    are no longer required from the workflow.

Critical guarantees (handoff- and workflow-level, not unit-testable):

- The handoff still includes: lifecycle (`triage → [foundation] →
  measure → log → improve → verify → commit → report`), required
  templates table, mutation-selection priorities, hard constraints,
  and the rule that PR comments and the mutation log must follow
  `template_03_final_report.md` and `template_02_mutation_testing.md`
  exactly.
- The handoff now also instructs the agent to write a Devin knowledge
  note after the run.
- The workflow still triggers on `pull_request: [opened]` and on
  `workflow_dispatch` with a `pr_number` integer input.
- The workflow still sparse-checks out `.devin/docs/` from the PR head
  SHA, validates that all four instruction files
  (`mutation_testing_agent_handoff.md`, `template_01_test_foundation.md`,
  `template_02_mutation_testing.md`, `template_03_final_report.md`) are
  present, and embeds them verbatim into the Devin prompt.
- The workflow still calls the Devin v3 sessions API with `prompt`,
  `title`, `repos`, and `tags` fields and fails the job if
  `DEVIN_API_KEY` / `DEVIN_ORG_ID` are missing or the API returns a
  non-2xx status.
- The workflow no longer needs write access to issues or pull
  requests because comment posting is handled by the Devin session
  itself.

Relevant implementation files:

- `.devin/docs/mutation_testing_agent_handoff.md`
- `.github/workflows/devin-mutation-testing.yml`

Relevant tests:

- None. The repository does not contain pytest or jest tests that
  exercise either documentation prose or GitHub Actions workflow YAML
  files. The only enforced check for workflow files is schema
  validation via `.github/workflows/github-action-validator.yml`,
  which runs `@action-validator/cli` against `.github/workflows/*.yml`.

Likely risk areas:

- Documentation drift: the abstracted "Lessons Learned" / "What Makes
  a Good Mutation" sections must still convey the operational rules
  (no `pytest -x`, deselect pre-existing failures, scale mutations to
  PR scope, review coverage gaps independently).
- Workflow trigger surface and Devin API request shape (prompt
  contents, `repos`, `tags`).
- Permissions drift: with `pull-requests: read` the workflow can no
  longer comment from CI; any future change that re-introduces a CI
  comment step would have to restore `pull-requests: write` (and
  ideally `issues: write`) for the comment step to succeed.

These risks live at the documentation, GitHub-Actions-runtime, and
process-conformance layers. They cannot be expressed as pytest/jest
mutations against this repository.

## Triage decision

Coverage level: not applicable.
Foundation needed: no.
Deselected tests: none.

Reason: the PR's two changed files are a Markdown documentation file
inside `.devin/docs/` and a GitHub Actions workflow YAML. The
mutation-testing handoff explicitly targets Python/TS code with unit
tests (`pytest <targeted tests>` or `jest`). There is no matching test
suite for either artifact in this repository, and writing a synthetic
"foundation" test for either would not reflect any real production
code path the maintainers test.

What we did verify (out of scope for mutation testing, but checked
for basic sanity):

| Check | Tool | Result |
|---|---|---|
| Workflow YAML schema | `@action-validator/cli` | VALID |
| Step `Prepare Devin prompt` JS body parses (wrapped in async fn) | `node --check` | OK |
| Step `Create Devin session` JS body parses (wrapped in async fn) | `node --check` | OK |
| All four files loaded by the workflow are present in `.devin/docs/` | `ls .devin/docs/` | `mutation_testing_agent_handoff.md`, `template_01_test_foundation.md`, `template_02_mutation_testing.md`, `template_03_final_report.md` all present |
| `Comment on PR` step removed from workflow | `grep` | confirmed (0 matches) |
| Permissions narrowed to `pull-requests: read` | `grep` | confirmed (no `issues: write` / `pull-requests: write` remain) |
| Handoff retains lifecycle and template-compliance language | `grep` | "Required Lifecycle", "Mandatory template compliance" still present |
| Handoff has new "Lessons Learned" + "Knowledge Base Contribution" sections | `grep` | line 614 and line 808 respectively |

## Initial targeted coverage

Not applicable. No Python/TS module is changed.

| File | Line % | Branch % | Covered/Total lines |
|---|---|---|---|
| `.devin/docs/mutation_testing_agent_handoff.md` | n/a | n/a | n/a |
| `.github/workflows/devin-mutation-testing.yml` | n/a | n/a | n/a |
| **TOTAL** | **n/a** | **n/a** | **n/a** |

Uncovered PR-changed lines: not applicable — the changed files are a
Markdown documentation file and a declarative CI workflow plus its
embedded `actions/github-script` callbacks that depend on
GitHub-Actions-provided globals (`github`, `context`, `core`) and are
not unit-testable inside this repo.

## Initial mutation plan

No mutation plan was generated. Mutations on a Markdown documentation
file would only affect prose; mutations on the workflow YAML would
either (a) cause the workflow to fail schema validation (caught by
the existing validator but not by a unit test, and not a behavioral
signal about the change), or (b) silently alter runtime behavior that
can only be observed on GitHub's runners, which is out of scope for
this framework.

| ID | File | Mutation | Category | Expected |
|---|---|---|---|---|
| — | — | n/a — no applicable mutation surface | n/a | n/a |

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
| `.devin/mutation-testing/pr-16-2026-05-13-mutation-prompt-lessons-learned.md` | New log file documenting the triage decision and no-op outcome. | Provides the repo-tracked traceability artifact required by the mutation-testing handoff. |

No test or production code was added or modified.

## Final verification

Targeted suite: n/a — no Python/TS test suite is associated with the
changed files.

Line coverage: n/a.
Branch coverage: n/a.
Kill rate: n/a (0 valid mutations).

Additional sanity checks performed:

- `action-validator .github/workflows/devin-mutation-testing.yml` → VALID
- `node --check` on each embedded `actions/github-script` body
  (wrapped in `async function _run({github, context, core}) { ... }`
  to satisfy the top-level-await constraint) → all parse OK
- `git diff --merge-base master --name-only` confirms exactly two
  changed files:
  - `.devin/docs/mutation_testing_agent_handoff.md`
  - `.github/workflows/devin-mutation-testing.yml`
- The four files loaded by the workflow's `Prepare Devin prompt` step
  (`mutation_testing_agent_handoff.md`, `template_01_test_foundation.md`,
  `template_02_mutation_testing.md`, `template_03_final_report.md`)
  are all present in `.devin/docs/`.

## Final assessment

The PR introduces no testable Python or TypeScript behavior. It is a
documentation rewrite plus a CI workflow simplification. The
mutation-testing framework's preconditions (a targeted pytest/jest
suite around the changed behavior) are not met.

Per the handoff's explicit guidance —
"If no meaningful gaps are found and coverage is already acceptable,
the improve step is a no-op; still log, verify, commit the log, and
report" — the run is recorded here as a documented no-op:

- Triage classified the PR as not applicable for mutation testing.
- No mutations were executed (none would be valid).
- No tests were added or modified.
- The workflow YAML and its embedded JS were sanity-checked
  (schema validation + `node --check` parse).
- Templates referenced by the workflow were confirmed to exist.
- This log file is committed to the PR branch for traceability.

## What's left for high-quality coverage

| Area | Missing test | Why it matters |
|---|---|---|
| `actions/github-script` JS bodies | Extract the inline JS from `.github/workflows/devin-mutation-testing.yml` into a standalone module (e.g., `.github/scripts/build-devin-request.js`) so it can be unit-tested with jest/vitest (PR-number validation, instruction-file assembly, request-body shape, error paths). | Would let mutation testing actually apply to this workflow's logic in future PRs. |
| Workflow trigger surface | A repo-level lint that asserts the set of workflows running on `pull_request: [opened]` and the permissions each grants. | Catches accidental changes to which PR events trigger the mutation workflow, and accidental re-introductions of write permissions. |
| Failure paths in `Prepare Devin prompt` | Tests that exercise: invalid PR number, closed PR, missing instruction file, missing API secrets, non-2xx Devin API response. | These are currently only guarded by `core.setFailed` calls with no executed assertions. |
| Handoff document conformance | A repo-level lint that verifies `.devin/docs/mutation_testing_agent_handoff.md` still references all three templates by name and still contains the lifecycle phrase `triage → [foundation] → measure → log → improve → verify → commit → report`. | Catches accidental drift if future doc edits drop the operational rules. |

These are coverage opportunities at the repo level for future work
and are intentionally not added in this PR, which is a documentation
and CI-config change only.

---
pr_id: 14
pr_title: "ci: add automatic Devin mutation testing workflow on PR open"
run_date: "2026-05-13"
agent: "devin"
repo: "loic-cunningham/superset"
branch: "devin/1778634210-auto-mutation-testing"
base_branch: "master"
mode: "mutation-testing-and-test-improvement"
status: "completed"

triage:
  coverage_level: "not_applicable"
  foundation_needed: false
  deselected_tests: []
  rationale: >
    The PR only adds a single GitHub Actions workflow YAML
    (.github/workflows/devin-mutation-testing.yml). It introduces no
    Python or TypeScript source code, no library logic, no API handler,
    and no helper modules. The mutation testing framework described in
    .devin/docs/mutation_testing_agent_handoff.md targets unit-testable
    Python (pytest) or TypeScript (jest) behavior, neither of which
    applies here. The repository has no behavioral test suite for
    GitHub Actions workflow YAML files; the only enforced check is
    schema-level validation via @action-validator/cli in
    .github/workflows/github-action-validator.yml.

target:
  behavior:
    - "Trigger a Devin mutation-testing session automatically on pull_request: [opened]"
    - "Allow manual workflow_dispatch with a PR number input"
    - "Sparse-checkout .devin/docs/ from the PR head SHA"
    - "Build a Devin v3 API request body embedding the handoff + 3 templates verbatim"
    - "Create the Devin session and post a PR comment linking it"
  implementation_files:
    - ".github/workflows/devin-mutation-testing.yml"
  test_files: []

initial_state:
  targeted_tests:
    command: "n/a — no Python/TS test suite is associated with the changed file"
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
    command: "n/a — no Python/TS test suite is associated with the changed file"
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
      - "embedded `actions/github-script` body in step: Prepare Devin prompt"
      - "embedded `actions/github-script` body in step: Create Devin session"
      - "embedded `actions/github-script` body in step: Comment on PR"
    result: "all parse OK"

commits: []

artifacts:
  pr_comment_url: ""
---

# Mutation Testing Log — PR #14

## PR understanding

Behavior changed:
- Adds `.github/workflows/devin-mutation-testing.yml`, a new GitHub Actions
  workflow that runs on `pull_request: [opened]` and via
  `workflow_dispatch`.
- The workflow sparse-checks out `.devin/docs/`, builds a prompt that
  embeds the mutation-testing handoff and the three templates, then
  calls the Devin v3 sessions API and posts a PR comment.

Critical guarantees (workflow-level, not unit-testable):
- Trigger limited to PR `opened` events and explicit manual dispatch.
- PR number is validated (`Number.isInteger && > 0`) before any API call.
- Required instruction files are present before constructing the prompt
  (each path checked via `fs.existsSync`).
- The Devin API call fails the job when `DEVIN_API_KEY` or `DEVIN_ORG_ID`
  is missing, or when the API returns a non-2xx response.
- A PR comment with the session link is only posted on workflow success.

Relevant implementation files:
- `.github/workflows/devin-mutation-testing.yml`

Relevant tests:
- None. The repository does not contain pytest or jest tests that
  exercise GitHub Actions workflow YAML files. The only enforced check
  for workflow files is schema validation via
  `.github/workflows/github-action-validator.yml`, which runs
  `@action-validator/cli` against `.github/workflows/*.yml`.

Likely risk areas:
- Trigger configuration (event types) regressions.
- Missing required input handling on `workflow_dispatch`.
- Devin API request shape drift (prompt, repos, tags).
- PR comment / API failure handling.

These risks exist at the CI-platform level (GitHub Actions runtime) and
would have to be validated end-to-end against GitHub's runner. They
cannot be expressed as pytest/jest mutations.

## Triage decision

Coverage level: not applicable.
Foundation needed: no.
Deselected tests: none.

Reason: the PR's sole changed file is a GitHub Actions workflow
YAML. The mutation-testing handoff explicitly targets Python/TS code
with unit tests (`pytest <targeted tests>` or `jest`). There is no
matching test suite for this artifact in this repository, and writing a
synthetic "foundation" test for a workflow YAML would not reflect any
real production code path the maintainers test. The improve step is
therefore a documented no-op.

What we did verify (out of scope for mutation testing, but checked for
basic sanity):

| Check | Tool | Result |
|---|---|---|
| Workflow YAML schema | `@action-validator/cli` | VALID |
| Step `Prepare Devin prompt` JS body parses | `node --check` | OK |
| Step `Create Devin session` JS body parses | `node --check` | OK |
| Step `Comment on PR` JS body parses | `node --check` | OK |

## Initial targeted coverage

Not applicable. No Python/TS module is changed.

| File | Line % | Branch % | Covered/Total lines |
|---|---|---|---|
| `.github/workflows/devin-mutation-testing.yml` | n/a | n/a | n/a |
| **TOTAL** | **n/a** | **n/a** | **n/a** |

Uncovered PR-changed lines: not applicable — the file is declarative CI
config plus embedded `actions/github-script` callbacks that depend on
GitHub-Actions-provided globals (`github`, `context`, `core`) and are
not unit-testable inside this repo.

## Initial mutation plan

No mutation plan was generated. Mutations on a workflow YAML would
either (a) cause the workflow to fail schema validation (caught by the
existing validator but not by a unit test, and not a behavioral signal
about the change), or (b) silently alter runtime behavior that can
only be observed on GitHub's runners, which is out of scope for this
framework.

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
| `.devin/mutation-testing/pr-14-2026-05-13-devin-mutation-testing-workflow.md` | New log file documenting the triage decision and no-op outcome. | Provides the repo-tracked traceability artifact required by the mutation-testing handoff. |

No test or production code was added or modified.

## Final verification

Targeted suite: n/a — no Python/TS test suite is associated with the
changed file.

Line coverage: n/a.
Branch coverage: n/a.
Kill rate: n/a (0 valid mutations).

Additional sanity checks performed:
- `action-validator .github/workflows/devin-mutation-testing.yml` → VALID
- `node --check` on each embedded `actions/github-script` body → all parse OK
- `git diff --merge-base master --name-only` confirms the workflow file
  is the only change in the PR.

## Final assessment

The PR introduces no testable Python or TypeScript behavior; it only
adds a GitHub Actions workflow YAML that orchestrates Devin runs at the
CI platform level. The mutation-testing framework's preconditions
(a targeted pytest/jest suite around the changed behavior) are not met.

Per the handoff's explicit guidance —
"If no meaningful gaps are found and coverage is already acceptable,
the improve step is a no-op; still log, verify, commit the log, and
report" — the run is recorded here as a documented no-op:

- Triage classified the PR as not applicable for mutation testing.
- No mutations were executed (none would be valid).
- No tests were added or modified.
- The workflow YAML and its embedded JS were sanity-checked
  (schema validation + `node --check` parse).
- This log file is committed to the PR branch for traceability.

## What's left for high-quality coverage

| Area | Missing test | Why it matters |
|---|---|---|
| `actions/github-script` JS bodies | Extract the inline JS into a standalone module (e.g., `.github/scripts/build-devin-request.js`) so it can be unit-tested with jest/vitest (PR-number validation, instruction-file assembly, request-body shape, error paths). | Would let mutation testing actually apply to this workflow's logic in future PRs. |
| Workflow trigger surface | A repo-level integration test that lints/asserts the set of workflows that run on `pull_request: [opened]`. | Catches accidental changes to which PR events trigger the mutation workflow. |
| Failure paths in `Prepare Devin prompt` | Tests that exercise: invalid PR number, closed PR, missing instruction file, missing API secrets. | These are currently only guarded by `core.setFailed` calls with no executed assertions. |

These are coverage opportunities at the repo level for future work and
are intentionally not added in this PR, which is purely a CI workflow
addition.

---
pr_id: 18
pr_title: "ci: replace JS API file iteration with native git for docs override"
run_date: "2026-05-13"
agent: "devin"
repo: "loic-cunningham/superset"
branch: "devin/1778637147-clean-docs-override"
base_branch: "master"
mode: "mutation-testing-and-test-improvement"
status: "completed"

triage:
  coverage_level: "not_applicable"
  foundation_needed: false
  deselected_tests: []
  rationale: >
    The PR's sole changed file is a GitHub Actions workflow YAML
    (.github/workflows/devin-mutation-testing.yml). It modifies only
    workflow-step orchestration (replacing an `actions/github-script`
    JS loop with a shell step that runs `git fetch` + `git diff` +
    `git show`). It introduces no Python or TypeScript source code,
    no library logic, no API handler, and no helper modules. The
    mutation testing framework described in
    .devin/docs/mutation_testing_agent_handoff.md targets
    unit-testable Python (pytest) or TypeScript (jest) behavior,
    neither of which applies here. The repository has no behavioral
    test suite for GitHub Actions workflow YAML or for inline shell
    steps; the only enforced check on workflow YAML in this repo is
    schema-level validation via @action-validator/cli in
    .github/workflows/github-action-validator.yml. The same triage
    conclusion was reached for the original workflow-introducing PR
    (#14, see .devin/mutation-testing/pr-14-2026-05-13-devin-mutation-testing-workflow.md);
    this PR follows the same precedent.

target:
  behavior:
    - "Override only `.devin/docs/` files that the PR itself modifies, with the PR-head version, before the prompt is built"
    - "Leave `.devin/docs/` files untouched when the PR does not modify them (default branch versions are used)"
    - "Do NOT override any file outside `.devin/docs/`, even if the PR changes it"
    - "Continue to build the Devin prompt from `.devin/docs/` (handoff + 3 templates) and fail the job if any required file is missing"
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
  - tool: "python3 -c \"import yaml; yaml.safe_load(open(...))\""
    target: ".github/workflows/devin-mutation-testing.yml"
    result: "YAML parses cleanly"
  - tool: "bash -n"
    target: "extracted `run:` body of step `Override PR-changed docs`"
    result: "shell syntax OK"
  - tool: "node --check"
    targets:
      - "embedded `actions/github-script` body of step `Prepare Devin prompt`"
      - "embedded `actions/github-script` body of step `Create Devin session`"
    result: "all parse OK"
  - tool: "end-to-end bash simulation against a local fake upstream"
    description: >
      Built a fake upstream bare repo with a default branch and a
      `refs/pull/123/head` ref. Performed `actions/checkout@v4`-style
      sparse-checkout of `.devin/docs/` from the default branch, then
      ran the exact `run:` body from the new `Override PR-changed
      docs` step.
    cases:
      - case: "PR modifies .devin/docs/a.md and README.md"
        expected: "a.md overlaid with PR version; b.md unchanged; README.md NOT overlaid"
        observed: "a.md = 'PR VERSION A'; b.md = 'DEFAULT VERSION B'; README.md absent (sparse-checkout); diff output limited to `.devin/docs/a.md`"
        result: "PASS"
      - case: "PR does not modify any `.devin/docs/` files"
        expected: "no override; emits 'No .devin/docs/ changes' message; a.md and b.md unchanged"
        observed: "message emitted; a.md and b.md retained default content"
        result: "PASS"

commits: []

artifacts:
  pr_comment_url: ""
---

# Mutation Testing Log — PR #18

## PR understanding

Behavior changed:
- Replaces the JS-based docs-override loop inside the `actions/github-script` step `Prepare Devin prompt` with a dedicated shell step `Override PR-changed docs` that uses native git.
- The old code paginated `pulls.listFiles`, filtered for `.devin/docs/*`, then for each file fetched the PR-head version via `repos.getContent`, base64-decoded it, and wrote it to disk.
- The new code does:
  1. `git fetch origin "pull/${pr_number}/head" --depth=1`
  2. `changed=$(git diff --name-only HEAD FETCH_HEAD -- .devin/docs/)`
  3. If `$changed` is non-empty, for each file: `git show "FETCH_HEAD:${f}" > "${f}"`
  4. Otherwise log that default-branch docs are used.
- The `Prepare Devin prompt` step now only reads files from disk and assembles the prompt; the JS code that fetched/decoded files is removed.

Critical guarantees (workflow-level, not unit-testable in pytest/jest):
- Only `.devin/docs/` files are overlaid (path filter `-- .devin/docs/`).
- The overlaid content is the PR-head version (`FETCH_HEAD:` ref), not the default-branch version.
- Output truncation/append is impossible (`>`, not `>>`).
- When the PR makes no `.devin/docs/` changes, the default-branch sparse-checkout is preserved.
- The job still fails fast if any of the 4 required instruction files is missing (`fs.existsSync` check in the `Prepare Devin prompt` step is unchanged).
- PR-number validation (`Number.isInteger && > 0`) and PR state check (`pr.state !== 'open'`) are unchanged.

Relevant implementation files:
- `.github/workflows/devin-mutation-testing.yml`

Relevant tests:
- None. The repository does not contain pytest or jest tests that
  exercise GitHub Actions workflow YAML files or their inline shell
  steps. The only enforced check for workflow files is schema
  validation via `.github/workflows/github-action-validator.yml`,
  which runs `@action-validator/cli` against `.github/workflows/*.yml`.

Likely risk areas (would have to be validated end-to-end on the GitHub
runner; not expressible as pytest/jest mutations in this repo):
- Path filter drops, accidentally overriding files outside `.devin/docs/`.
- Wrong ref direction (`HEAD:` vs `FETCH_HEAD:` in `git show`), which
  would silently leave default-branch docs in place.
- `>` → `>>` (append) corrupting the override.
- Removal of the `if [ -n "$changed" ]` guard (harmless on empty input
  but loses the informational log line that the user sees in CI).
- `--depth=1` removal (slower fetch, but functionally equivalent).

## Triage decision

Coverage level: not applicable.
Foundation needed: no.
Deselected tests: none.

Reason: the PR's sole changed file is a GitHub Actions workflow YAML
with an inline shell step. The mutation-testing handoff explicitly
targets Python/TS code with unit tests (`pytest <targeted tests>` or
`jest`). There is no matching test suite for this artifact in this
repository, and writing a synthetic "foundation" pytest/jest suite
that exercises a YAML workflow would not reflect any real production
code path the maintainers test in CI. The improve step is therefore a
documented no-op (matching the precedent set by PR #14).

What we did verify (out of scope for formal mutation kill-rate, but
checked for behavioral correctness):

| Check | Tool | Result |
|---|---|---|
| Workflow YAML parses | `python3 -c "import yaml; yaml.safe_load(...)"` | OK |
| `Override PR-changed docs` shell syntax | `bash -n` | OK |
| `Prepare Devin prompt` JS body parses | `node --check` | OK |
| `Create Devin session` JS body parses | `node --check` | OK |
| End-to-end happy path (PR with docs changes) | Local bash simulation against a fake upstream bare repo | a.md overlaid with PR version, b.md unchanged, README.md untouched |
| End-to-end no-op path (PR with no docs changes) | Same simulation | "No .devin/docs/ changes" emitted; default docs retained |

Hand-mutations (informational only; no automated test runner can kill
these in this repo — they were verified by re-running the bash
simulation with the mutation applied):

| ID | Mutation | Observed effect |
|---|---|---|
| H1 | Remove path filter `-- .devin/docs/` from the `git diff` line | `README.md` from the default-branch sparse checkout is overwritten with the PR-head version. Out-of-scope override. |
| H3 | Swap `FETCH_HEAD:${f}` → `HEAD:${f}` in `git show` | `.devin/docs/a.md` is rewritten with the default-branch content, i.e. the override silently does nothing useful. |
| H4 | `>` → `>>` in the redirection | `.devin/docs/a.md` becomes the concatenation of the default-branch and PR-head versions. Corrupt prompt input. |

All three hand-mutations confirmed that the surface change is
behaviorally meaningful: each mutation alters the file contents that
the downstream `Prepare Devin prompt` step would read. None of them is
caught by any check that lives inside this repository (no pytest, no
jest, no shellcheck wired to CI for this file).

## Initial targeted coverage

Not applicable. No Python/TS module is changed.

| File | Line % | Branch % | Covered/Total lines |
|---|---|---|---|
| `.github/workflows/devin-mutation-testing.yml` | n/a | n/a | n/a |
| **TOTAL** | **n/a** | **n/a** | **n/a** |

Uncovered PR-changed lines: not applicable — the file is declarative
CI config plus an inline shell step plus embedded
`actions/github-script` callbacks that depend on
GitHub-Actions-provided globals (`github`, `context`, `core`) and are
not unit-testable inside this repo.

## Initial mutation plan

No automated mutation plan was generated. Mutations on a workflow YAML
+ inline shell step would either (a) cause `@action-validator/cli` to
flag the workflow (caught at CI schema validation, not a behavioral
signal about this change), or (b) silently alter runtime behavior that
can only be observed on GitHub's runners, which is out of scope for
this framework. The hand-mutations listed in the triage decision table
above were verified by replaying the bash simulation manually.

| ID | File | Mutation | Category | Expected |
|---|---|---|---|---|
| — | — | n/a — no applicable automated mutation surface | n/a | n/a |

## Initial mutation results

| ID | Mutation | Status | Caught by |
|---|---|---|---|
| — | n/a | n/a | — |

Kill rate: n/a (0 valid mutations).

## Fix plan

### Mutation gap fixes
- None — no automated mutations executed.

### Coverage gap fixes
- None — no Python/TS source code is modified by this PR.

### Behavioral gap fixes
- None applicable to this repo's pytest/jest suites.

## Changes made

| File | Change | Kills/Covers |
|---|---|---|
| `.devin/mutation-testing/pr-18-2026-05-13-clean-docs-override.md` | New log file documenting the triage decision, the workflow-level sanity checks performed, and the bash simulation results for the new `Override PR-changed docs` step. | Provides the repo-tracked traceability artifact required by the mutation-testing handoff. |

No test or production code was added or modified.

## Final verification

Targeted suite: n/a — no Python/TS test suite is associated with the
changed file.

Line coverage: n/a.
Branch coverage: n/a.
Kill rate: n/a (0 valid automated mutations).

Additional sanity checks performed (verified clean on the PR branch):
- `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/devin-mutation-testing.yml'))"` → OK
- `bash -n` on the extracted `Override PR-changed docs` run-body → OK
- `node --check` on each embedded `actions/github-script` body → all parse OK
- End-to-end bash simulation of the new shell step against a fake
  upstream bare repo:
  - PR-with-docs case: only `.devin/docs/*` PR-changed files are overlaid; unrelated PR-changed files are NOT overlaid; sibling default-branch docs are retained.
  - PR-without-docs case: no override occurs; the informational message is emitted.
- `git diff --merge-base master --name-only` confirms the workflow YAML
  is the only changed file in this PR.

## Final assessment

The PR introduces no testable Python or TypeScript behavior; it
modifies a GitHub Actions workflow YAML (the `Prepare Devin prompt`
JS body is shortened, and a new `Override PR-changed docs` shell step
is added before it). The mutation-testing framework's preconditions (a
targeted pytest/jest suite around the changed behavior) are not met.

Per the handoff's explicit guidance —
> "If no meaningful gaps are found and coverage is already acceptable,
> the improve step is a no-op; still log, verify, commit the log, and
> report."

— the run is recorded here as a documented no-op:

- Triage classified the PR as not applicable for automated mutation testing.
- No automated mutations were executed (none would be valid pytest/jest mutations).
- No tests were added or modified.
- The workflow YAML and its embedded JS were sanity-checked
  (YAML parse + `node --check`).
- The new shell step was sanity-checked (`bash -n`) and behaviorally
  verified against a fake upstream bare repo for both the
  PR-modifies-docs and PR-does-not-modify-docs cases.
- Three hand-mutations on the shell step (drop path filter, swap
  ref direction, `>` → `>>`) were confirmed to alter the override
  output, but they are not catchable by any test that lives in this
  repository.
- This log file is committed to the PR branch for traceability.

## What's left for high-quality coverage

| Area | Missing test | Why it matters |
|---|---|---|
| `Override PR-changed docs` shell step | A bash-level test (e.g. under `tests/workflows/`) that constructs a fake upstream + sparse-checkout and asserts: (1) only `.devin/docs/*` PR-changed files are overlaid, (2) the overlaid content matches the PR-head, (3) non-PR docs are retained, (4) no file outside `.devin/docs/` is touched. | Would automate the bash simulation performed here so future drift (e.g., accidental path-filter drop, `HEAD:`/`FETCH_HEAD:` mix-up, `>` → `>>`) is caught in CI. |
| `actions/github-script` JS bodies | Extract the inline JS into a standalone module (e.g., `.github/scripts/build-devin-request.js`) so it can be unit-tested with jest/vitest (PR-number validation, instruction-file assembly, request-body shape, error paths). | Would let mutation testing actually apply to this workflow's logic in future PRs (carry-over item from PR #14). |
| `Prepare Devin prompt` missing-file path | A test that exercises the `fs.existsSync` guard for each of the 4 required instruction files. | This is the only remaining safety net inside the workflow itself after the JS file-fetching loop was removed; it currently relies on `core.setFailed` with no executed assertions. |

These are coverage opportunities at the repo level for future work and
are intentionally not added in this PR, which is a focused CI workflow
cleanup with no behavioral surface inside the application codebase.

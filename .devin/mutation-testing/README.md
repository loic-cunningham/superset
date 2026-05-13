<!--
Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
-->

# Mutation Testing — Tooling and Conventions

This directory contains the structured artifacts and reusable tooling for
running mutation testing against Superset pull requests.

## Directory Layout

| Path | Purpose |
|---|---|
| `.devin/mutation-testing/templates/mutation_testing_agent_handoff.md` | Full lifecycle specification (Phases 0–13). |
| `.devin/mutation-testing/templates/template_01_test_foundation.md` | Stage 1 template — foundation test plan. |
| `.devin/mutation-testing/templates/template_02_mutation_testing.md` | Stage 2 template — repo-tracked log file. |
| `.devin/mutation-testing/templates/template_03_final_report.md` | Stage 3 template — final PR comment. |
| `.devin/mutation-testing/templates/template_*.example.md` | Filled examples for each template. |
| `.devin/mutation-testing/scripts/` | Reusable automation scripts. |
| `.devin/mutation-testing/pr-<N>-<date>-<slug>.md` | Per-PR log files conforming to Stage 2. |

## Why These Scripts Exist

Mutation testing on this repo has several sharp edges. The scripts smooth
them over so each run is reproducible and structured outputs stay in sync
with the templates.

| Problem | Script |
|---|---|
| Non-trivial setup (system C libraries, beartype circular-import patch, nh3 PyO3 crash). | `setup_env.sh` |
| pytest requires the venv, `PY_KEY_VALUE_DISABLE_BEARTYPE=true`, and PR-specific deselections — applied identically across all runs. | `run_targeted.sh` |
| Reshaping `pytest-cov` JSON output into the log file's YAML coverage schema. | `coverage_summary.py` |
| Silent no-ops, case-sensitive result parsing, and working-tree pollution from hand-rolled mutation loops. | `mutation_runner.py` |
| Templates live on `master` under `.devin/mutation-testing/templates/`; PR branches under test may not have them, and legacy branches keep them in `.devin/docs/`. | `fetch_templates.sh` |
| The PR comment is ~20 KB of nested `<details>` with a JA mirror — easy to drop a section. | `render_pr_comment.py` |
| Log file YAML shape and section order must stay in sync with the template. | `lint_log.py` |

## End-to-End Workflow

```bash
# 1. One-shot environment setup (idempotent).
./.devin/mutation-testing/scripts/setup_env.sh

# 2. Fetch canonical templates from master.
./.devin/mutation-testing/scripts/fetch_templates.sh

# 3. Measure initial targeted coverage.
./.devin/mutation-testing/scripts/coverage_summary.py \
    --tests tests/unit_tests/sql/parse_tests.py \
    --tests tests/unit_tests/mcp_service/sql_lab/tool/test_execute_sql.py \
    --cov superset.sql.parse \
    --cov superset.mcp_service.sql_lab.tool.execute_sql \
    --output /tmp/initial-coverage.json

# 4. Run planned mutations (atomic apply → run → restore, JSON results).
./.devin/mutation-testing/scripts/mutation_runner.py \
    /path/to/mutations.yaml \
    --results /tmp/initial-mutations.json

# 5. Create or update the repo-tracked log file, then validate it.
./.devin/mutation-testing/scripts/lint_log.py \
    .devin/mutation-testing/pr-<N>-<YYYY-MM-DD>-<slug>.md

# 6. Fix surviving mutations, then rerun the relevant subset.
./.devin/mutation-testing/scripts/mutation_runner.py \
    /path/to/mutations.yaml \
    --only M11,M12,M13,M16 \
    --results /tmp/final-mutations.json

# 7. Render the final PR comment from structured results.
./.devin/mutation-testing/scripts/render_pr_comment.py \
    /path/to/results.json \
    --out /tmp/comment.md
```

## File Contracts

All scripts are designed so their outputs are direct inputs to one another:

* `coverage_summary.py` → JSON with `line.percent`, `line.covered`,
  `line.total` and the equivalent for `branch` — matches the YAML schema
  in `template_02_mutation_testing.md`.
* `mutation_runner.py` → JSON with `killed`, `survived`, `kill_rate`, and a
  per-mutation `results[]` array — populates the
  `initial_state.mutation_testing` / `final_state.mutation_testing` blocks.
* `render_pr_comment.py` → reads a single JSON blob and renders the full
  Stage 3 PR comment in the exact shape mandated by
  `template_03_final_report.md`.

## Mutation Spec Format

`mutation_runner.py` reads a single YAML file:

```yaml
targets:
  - path: superset/sql/parse.py
test_paths:
  - tests/unit_tests/sql/parse_tests.py
mutations:
  - id: M1
    description: Remove exp.Drop from destructive_nodes
    file: superset/sql/parse.py
    old: |
      destructive_nodes = (
          exp.Drop,
          exp.TruncateTable,
          exp.Alter,
      )
    new: |
      destructive_nodes = (
          exp.TruncateTable,
          exp.Alter,
      )
```

The `old` block must appear exactly once in the file. The runner aborts
with an `error` status (not `survived`) if the patch cannot be applied,
preventing silent no-ops.

## Invariants Enforced by Tooling

* `mutation_runner.py` refuses to start if target files have uncommitted
  changes, and re-verifies the tree is clean after each mutation. A failed
  restore aborts the run.
* `lint_log.py` rejects log files that miss any required YAML key or
  section heading, or whose `final_state.mutation_testing.rerun_type` is
  unset when `status: completed`.
* `render_pr_comment.py` validates that `initial` contains all required
  state keys and that `final` is present and complete when `mode: final`.

## Per-Script Reference

| Script | Purpose | Inputs | Outputs |
|---|---|---|---|
| `setup_env.sh` | One-shot environment preparation | — | System packages, `.venv`, patched `key_value` |
| `run_targeted.sh` | pytest wrapper with venv and env vars | pytest args, `DEVIN_PYTEST_DESELECT` | pytest exit code |
| `coverage_summary.py` | Coverage as structured JSON | `--tests`, `--cov` | JSON summary |
| `mutation_runner.py` | Atomic apply → run → restore loop | Spec YAML | Per-mutation JSON results |
| `fetch_templates.sh` | Cache templates from `origin/master` | — | Files in `/tmp/mutation-testing-templates/` |
| `render_pr_comment.py` | Stage 3 PR comment renderer | Results JSON | Markdown for the PR comment |
| `lint_log.py` | Validate Stage 2 log file | Log file path | Exit 0 (valid) / 1 (invalid) |

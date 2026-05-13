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

# Mutation testing — tooling and conventions

This directory holds the structured artifacts and tooling used by Devin (and
any human) when running mutation testing against a Superset PR.

* `.devin/docs/` — templates and the agent handoff:
  * `mutation_testing_agent_handoff.md` — full lifecycle (Phases 0–13).
  * `template_01_test_foundation.md` — Stage 1 (foundation-needed branch).
  * `template_02_mutation_testing.md` — Stage 2 (repo-tracked log file).
  * `template_03_final_report.md` — Stage 3 (final PR comment).
* `.devin/mutation-testing/pr-<N>-<YYYY-MM-DD>-<slug>.md` — one log file per
  PR-under-test, conforming to `template_02_mutation_testing.md`.
* `.devin/mutation-testing/scripts/` — reusable tooling (this directory's
  scripts).

## Why these scripts exist

Mutation testing on this repo has a few sharp edges that the scripts smooth
over so each run is reproducible and the structured outputs don't drift from
the templates:

| Problem | Script |
|---|---|
| Setup is non-trivial (libmysqlclient/libldap deps, a beartype circular import, nh3 0.2.x PyO3 crash). | `setup_env.sh` |
| pytest needs the venv active, `PY_KEY_VALUE_DISABLE_BEARTYPE=true`, and PR-specific test deselections — applied identically across all mutation runs. | `run_targeted.sh` |
| Reading pytest-cov JSON and reshaping it into the log file's YAML coverage block is fiddly. | `coverage_summary.py` |
| Manual mutation application via bash/heredoc/Python triple-quotes mis-classifies results (e.g. case-sensitive `failed` grep) and silently no-ops when the patch can't be applied. | `mutation_runner.py` |
| Templates live on `master` and PR branches may not have them. | `fetch_templates.sh` |
| The PR comment is ~20 KB of nested `<details>` and JA mirror — easy to drop a section. | `render_pr_comment.py` |
| The log file's YAML shape and section order need to stay in sync with the template. | `lint_log.py` |

## End-to-end workflow

```bash
# 1. One-shot environment setup (idempotent).
./.devin/mutation-testing/scripts/setup_env.sh

# 2. Fetch the canonical templates and agent handoff from master.
./.devin/mutation-testing/scripts/fetch_templates.sh

# 3. Measure initial targeted coverage.
./.devin/mutation-testing/scripts/coverage_summary.py \
    --tests tests/unit_tests/sql/parse_tests.py \
    --tests tests/unit_tests/mcp_service/sql_lab/tool/test_execute_sql.py \
    --cov superset.sql.parse \
    --cov superset.mcp_service.sql_lab.tool.execute_sql \
    --output /tmp/initial-coverage.json

# 4. Run the planned mutations (atomic apply/run/restore, JSON results).
./.devin/mutation-testing/scripts/mutation_runner.py \
    /path/to/mutations.yaml \
    --results /tmp/initial-mutations.json

# 5. Create or update the log file under .devin/mutation-testing/
#    using template_02_mutation_testing.md, then validate it.
./.devin/mutation-testing/scripts/lint_log.py \
    .devin/mutation-testing/pr-<N>-<YYYY-MM-DD>-<slug>.md

# 6. Add tests for survivors. Re-run mutations focused on survivors,
#    or re-run the full set to confirm regressions.
./.devin/mutation-testing/scripts/mutation_runner.py \
    /path/to/mutations.yaml \
    --only M11,M12,M13,M16 \
    --results /tmp/final-mutations.json

# 7. Render the final PR comment from a structured results JSON.
./.devin/mutation-testing/scripts/render_pr_comment.py \
    /path/to/results.json \
    --out /tmp/comment.md
```

## File contracts

All scripts are designed so their outputs are direct inputs to one another:

* `coverage_summary.py` → JSON with `line.percent`, `line.covered`, `line.total`
  and the equivalent for `branch` — matches the YAML schema in
  `template_02_mutation_testing.md`.
* `mutation_runner.py` → JSON with `killed`, `survived`, `kill_rate`, and a
  per-mutation `results[]` array — directly populates the
  `initial_state.mutation_testing` / `final_state.mutation_testing` blocks.
* `render_pr_comment.py` → reads a single JSON blob and renders the full
  Stage 3 PR comment in the exact shape mandated by
  `template_03_final_report.md`.

## Mutation spec format

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
with an `error` status (not `survived`) if the patch can't be applied, so
silent no-ops are impossible.

## Hard rules (enforced by tooling)

* `mutation_runner.py` refuses to start if the target files have
  uncommitted changes, and re-verifies the tree is clean after each
  mutation. A failed restore aborts the run rather than continuing.
* `lint_log.py` rejects log files that miss any required YAML key or
  required `## ` section, or whose `final_state.mutation_testing.rerun_type`
  isn't set when `status: completed`.
* `render_pr_comment.py` validates that `initial` contains all required
  state keys and that `final` is present (and complete) whenever
  `mode: final`.

## Per-script reference

| Script | Purpose | Inputs | Outputs |
|---|---|---|---|
| `setup_env.sh` | One-shot env preparation | — | system packages, `.venv`, patched `key_value` |
| `run_targeted.sh` | pytest wrapper | pytest args, `DEVIN_PYTEST_DESELECT` env | pytest exit code |
| `coverage_summary.py` | Coverage as JSON | `--tests`, `--cov` | JSON summary |
| `mutation_runner.py` | Apply/run/restore | spec YAML | per-mutation JSON results |
| `fetch_templates.sh` | Cache templates from `origin/master` | — | files in `/tmp/mutation-testing-templates/` |
| `render_pr_comment.py` | Stage 3 PR comment | results JSON | markdown for the PR comment |
| `lint_log.py` | Validate Stage 2 log file | log file path | exit 0 / 1 |

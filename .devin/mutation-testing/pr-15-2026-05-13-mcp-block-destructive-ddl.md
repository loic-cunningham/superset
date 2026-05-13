---
pr_id: 15
pr_title: "[mirror #39621] fix(mcp): Block destructive DDL (DROP, TRUNCATE, ALTER) in execute_sql"
run_date: "2026-05-13"
agent: "devin"
repo: "loic-cunningham/superset"
branch: "mirror/pr-39621"
base_branch: "master"
mode: "mutation-testing-and-test-improvement"
status: "completed"

triage:
  coverage_level: "good"
  foundation_needed: false
  deselected_tests: []

target:
  behavior:
    - "Block DROP, TRUNCATE, ALTER (standard SQL dialects) before execution"
    - "Aggregate destructive detection across all statements in a multi-statement script"
    - "Block destructive Kusto KQL commands (.drop, .alter), case-insensitive"
    - "Render Jinja2 templates before validating SQL"
    - "Fail closed when SQL parsing fails"
    - "Allow safe DML (INSERT, UPDATE, DELETE, MERGE, CREATE) and SELECT"
    - "Pass the real database dialect to SQLScript"
  implementation_files:
    - "superset/mcp_service/sql_lab/tool/execute_sql.py"
    - "superset/sql/parse.py"
  test_files:
    - "tests/unit_tests/mcp_service/sql_lab/tool/test_execute_sql.py"
    - "tests/unit_tests/sql/parse_tests.py"

initial_state:
  targeted_tests:
    command: "pytest tests/unit_tests/mcp_service/sql_lab/tool/test_execute_sql.py tests/unit_tests/sql/parse_tests.py -q"
    passed: 560
    failed: 0
  coverage:
    line:
      percent: 95
      covered: 558
      total: 586
    branch:
      percent: 94
      covered: 166
      total: 176
  mutation_testing:
    valid_mutations: 16
    killed: 12
    survived: 4
    kill_rate: 75

final_state:
  targeted_tests:
    command: "pytest tests/unit_tests/mcp_service/sql_lab/tool/test_execute_sql.py tests/unit_tests/sql/parse_tests.py -q"
    passed: 571
    failed: 0
  coverage:
    line:
      percent: 95
      covered: 558
      total: 586
    branch:
      percent: 94
      covered: 166
      total: 176
  mutation_testing:
    valid_mutations: 16
    killed: 16
    survived: 0
    kill_rate: 100
    rerun_type: "full"

commits:
  - "61462da273ef6891671427faf87f26c87fadaa90"

artifacts:
  pr_comment_url: "https://github.com/loic-cunningham/superset/pull/15"
---

# Mutation Testing Log — PR #15

## PR understanding

Behavior changed:
- `execute_sql` MCP tool now blocks destructive DDL (DROP, TRUNCATE, ALTER) before executing the SQL on the database.
- `SQLStatement.is_destructive()` (new) detects destructive DDL AST nodes (`exp.Drop`, `exp.TruncateTable`, `exp.Alter`), plus an `exp.Command` fallback for Oracle/MS SQL.
- `KustoKQLStatement.is_destructive()` (new) detects Kusto destructive commands by case-insensitive prefix match on `.drop` / `.alter`.
- `SQLScript.has_destructive()` (new) aggregates `is_destructive()` across all statements via `any(...)`.
- Templated SQL is rendered via the Jinja processor before being parsed for the destructive check.
- Parse failures are fail-closed: the query is rejected with an INVALID_SQL_ERROR rather than passed through.
- Tool also includes unrelated cleanup (removed `template_warning` handling, downgrade of warnings to errors, removal of `is_feature_enabled` import); not the focus of this mutation run.

Critical guarantees:
- DROP/TRUNCATE/ALTER are blocked across standard SQL dialects.
- Mixed multi-statement scripts are blocked when any single statement is destructive (head, tail, or middle position).
- Kusto KQL `.drop` and `.alter` are blocked regardless of case.
- Templated SQL is rendered before being validated (so templates expanding to destructive statements are still blocked).
- Parse failures are fail-closed (do not bypass validation).
- Block happens before `database.execute()` is called.
- Safe DML/SELECT/CREATE passes through.
- The real `database.db_engine_spec.engine` is used as the dialect, not a hard-coded default.

Relevant implementation files:
- `superset/mcp_service/sql_lab/tool/execute_sql.py` (DDL pre-check block + ordering)
- `superset/sql/parse.py` (`is_destructive`, `has_destructive`, Kusto detection)

Relevant tests:
- `tests/unit_tests/mcp_service/sql_lab/tool/test_execute_sql.py` (`TestDestructiveDDLBlocking` class)
- `tests/unit_tests/sql/parse_tests.py` (`test_is_destructive`, `test_has_destructive`, `test_kusto_is_destructive`)

Likely risk areas:
- Wiring of the database dialect into `SQLScript` (no targeted assertion).
- Kusto prefix matching for non-space separators (`.drop;`, `.drop\t`).
- Kusto case sensitivity (mixed-case `.DROP`).
- `exp.Command` fallback for ALTER on Oracle/MS SQL dialects (marked `# pragma: no cover` by author).
- Templated SQL that renders to destructive statements (covered indirectly through the parse-fail path).

## Triage decision

Coverage level: good
Foundation needed: no
Deselected tests: none
Reason: All 560 targeted tests pass on a clean baseline; initial line coverage is 95% and branch coverage is 94% on the two changed files. The `TestDestructiveDDLBlocking` class and the `test_is_destructive` / `test_has_destructive` / `test_kusto_is_destructive` parametrized tests already exercise the core happy and error paths. Proceeded directly to mutation testing.

## Initial targeted coverage

| File | Line % | Branch % | Covered/Total lines |
|---|---|---|---|
| superset/mcp_service/sql_lab/tool/execute_sql.py | 86% | ~91% | 113/130 |
| superset/sql/parse.py | 98% | ~100% | 445/456 |
| **TOTAL** | **95%** | **94%** | **558/586** |

Uncovered PR-changed lines:
- `execute_sql.py:218-226` — outermost `except Exception` re-raise (not PR-critical; pre-existing pattern).
- `execute_sql.py:254, 256-258, 268-279` — `_data_to_statement_data` list/dict/bytes branches (not part of the destructive-DDL check).
- `parse.py:751` — `exp.Command` ALTER fallback (marked `# pragma: no cover` by author).
- `parse.py:1638-1658` — `transpile_to_dialect` body (pre-existing utility, not PR-critical).

## Initial mutation plan

| ID | File | Mutation | Category | Expected |
|---|---|---|---|---|
| M1 | parse.py | Remove `exp.Drop` from `destructive_nodes` | partial-enum | strength |
| M2 | parse.py | Remove `exp.TruncateTable` from `destructive_nodes` | partial-enum | strength |
| M3 | parse.py | Remove `exp.Alter` from `destructive_nodes` | partial-enum | strength |
| M4 | parse.py | `any(...)` → `all(...)` in `SQLScript.has_destructive` | inverted aggregate | strength |
| M5 | parse.py | Inspect only `self.statements[0]` | scope reduction | strength |
| M6 | parse.py | Inspect only `self.statements[-1]` | scope reduction | strength |
| M7 | execute_sql.py | Parse error fail-open (allow query through) | fail-open | strength |
| M8 | execute_sql.py | Execute `database.execute()` before destructive check | wrong order | strength |
| M9 | execute_sql.py | `script.has_destructive()` → `script.has_mutation()` | wrong helper | strength |
| M10 | execute_sql.py | Skip Jinja rendering before validation | skipped preprocessing | gap |
| M11 | execute_sql.py | Use literal `"base"` instead of `database.db_engine_spec.engine` | wrong dependency | gap |
| M12 | parse.py | Kusto `.drop`/`.alter` require trailing space | whitespace boundary | gap |
| M13 | parse.py | Kusto: remove `.lower()` normalization | missing preprocessing | gap |
| M14 | execute_sql.py | `if script.has_destructive()` → `if not script.has_destructive()` | inverted condition | strength |
| M15 | parse.py | `is_destructive()` always returns False | removed guard | strength |
| M16 | parse.py | ALTER `exp.Command` comparison `"ALTER"` → `"alter"` (case-flipped fallback) | case boundary | gap |

## Initial mutation results

| ID | Mutation | Status | Caught by |
|---|---|---|---|
| M1 | Remove `exp.Drop` | killed | test_is_destructive[DROP TABLE t-True], test_is_destructive[DROP TABLE IF EXISTS t-True], test_is_destructive[DROP VIEW v-True], test_has_destructive[SELECT 1; DROP TABLE t-True], test_drop_table_blocked (+ 2 more) |
| M2 | Remove `exp.TruncateTable` | killed | test_truncate_blocked, test_is_destructive[TRUNCATE TABLE t-True], test_has_destructive[SELECT 1; TRUNCATE TABLE t-True] |
| M3 | Remove `exp.Alter` | killed | test_alter_table_blocked, test_is_destructive[ALTER TABLE t ADD COLUMN x INT-True], test_has_destructive[CREATE TABLE t (id INT); ALTER TABLE t ADD COLUMN x INT-True] |
| M4 | `any` → `all` in `has_destructive` | killed | test_drop_in_multi_statement_blocked, test_has_destructive[SELECT 1; DROP TABLE t-True], test_has_destructive[SELECT 1; TRUNCATE TABLE t-True], test_has_destructive[CREATE TABLE t (id INT); ALTER TABLE t ADD COLUMN x INT-True] |
| M5 | Only `statements[0]` | killed | test_has_destructive[SELECT 1; DROP TABLE t-True] and two siblings (destructive in trailing position) |
| M6 | Only `statements[-1]` | killed | test_drop_in_multi_statement_blocked (destructive in head position) |
| M7 | Parse fail-open | killed | test_parse_failure_blocks_query |
| M8 | Execute before destructive check | killed | 6 tests: test_drop_table_blocked, test_truncate_blocked, test_alter_table_blocked, test_drop_in_multi_statement_blocked, test_parse_failure_blocks_query, test_drop_table_blocked_mysql |
| M9 | `has_destructive` → `has_mutation` | killed | test_insert_allowed, test_execute_sql_dml_success, test_execute_sql_multi_statement_all_dml |
| M10 | Skip Jinja rendering | killed | test_execute_sql_with_template_params, test_execute_sql_dry_run (indirectly — un-rendered `{{ table }}` triggers fail-closed parse handler) |
| M11 | Hard-coded `"base"` dialect | survived | — |
| M12 | Kusto require trailing space | survived | — |
| M13 | Kusto drop `.lower()` | survived | — |
| M14 | Inverted `if script.has_destructive()` | killed | 24 tests across `TestDestructiveDDLBlocking` and parametrized DDL tests |
| M15 | `is_destructive` always False | killed | test_is_destructive (destructive cases) + test_has_destructive (destructive cases) + DDL blocking tests |
| M16 | ALTER `exp.Command` fallback case-flipped | survived | — (author marked `# pragma: no cover`) |

Kill rate: 12/16 (75%)

## Fix plan

### Mutation gap fixes

- **M11 (wrong dialect)** — Add a test that asserts the destructive check uses `database.db_engine_spec.engine`, e.g., by patching `SQLScript` and verifying it receives the engine from the mocked database, or by exercising a DROP that's only destructive under a specific dialect (less brittle approach: assert via mock that `SQLScript(..., "<dialect>")` was called with the engine attribute).
- **M12 (Kusto whitespace)** — Add Kusto cases like `.drop table T;`, `.drop\ttable T`, `.alter;` to `test_kusto_is_destructive` so that boundary separators are protected.
- **M13 (Kusto case)** — Add a mixed-case Kusto case like `.DROP table T` / `.Alter table T` to `test_kusto_is_destructive`.
- **M16 (ALTER as exp.Command)** — Add a test that constructs a `SQLStatement` whose parsed root is an `exp.Command` with name `"ALTER"` (e.g., a dialect that surfaces ALTER as a generic Command, such as `mssql` for unsupported ALTER variants), and assert `is_destructive() is True`. This is the path the PR author marked `# pragma: no cover`, but it's reachable in practice and we can write a focused assertion.

### Coverage gap fixes
- The uncovered lines in `execute_sql.py` (218–226, 254, 256–258, 268–279) are in `_data_to_statement_data` and the outermost `except Exception` handler, neither of which is changed by the PR's destructive-DDL behavior. Leaving these alone is consistent with "test what the PR adds".
- The uncovered lines in `parse.py` (1638–1658) are inside `transpile_to_dialect`, which is also not the PR's destructive-DDL behavior.

### Behavioral gap fixes
- Add a test that templated SQL which renders to a destructive statement is blocked with the *destructive DDL* error message (not just the parse-error fallback). This proves Jinja rendering happens before validation in a stronger way than the indirect M10 result.

## Changes made

| File | Change | Kills/Covers |
|---|---|---|
| `tests/unit_tests/mcp_service/sql_lab/tool/test_execute_sql.py` | Added `test_ddl_check_uses_real_database_engine` — spies on `SQLScript` via `patch.object(..., wraps=real_sql_script)` and asserts it's invoked with `database.db_engine_spec.engine` (`"snowflake"`). | Kills M11 (hard-coded dialect). |
| `tests/unit_tests/mcp_service/sql_lab/tool/test_execute_sql.py` | Added `test_templated_destructive_sql_blocked_as_ddl` — mocks `get_template_processor` to expand a templated SQL to `DROP TABLE birth_names` and asserts the response carries the *destructive DDL* error (not the parse-error fallback). | Strengthens M10 from indirect (parse-error) to direct (destructive-DDL). |
| `tests/unit_tests/sql/parse_tests.py` | Extended `test_kusto_is_destructive` with 8 new parametrized cases: `.drop;`, `.drop\ttable T`, `.drop\ntable T`, `.alter;`, `.DROP table T`, `.Drop table T`, `.ALTER table T (col:string)`, `.Alter table T (col:string)`. | Kills M12 (Kusto whitespace) and M13 (Kusto case-insensitive). |
| `tests/unit_tests/sql/parse_tests.py` | Added `test_alter_as_command_is_destructive` — builds `SQLStatement` instances for Oracle/T-SQL/MySQL `ALTER SESSION / ALTER USER / ALTER SYSTEM` (which sqlglot parses as `exp.Command(name='ALTER')`), asserts the parse shape, and verifies `is_destructive() is True`. | Kills M16 (ALTER `exp.Command` fallback). |

## Final verification

Targeted suite: 571 passed, 0 failed (was 560 passed, 0 failed)
Line coverage: 95% (558/586) — unchanged; new tests exercise paths already covered by previous tests, plus one previously-uncovered branch (`is_destructive` `exp.Command` fallback) that is masked from the coverage report by an author-added `# pragma: no cover`.
Branch coverage: 94% (166/176) — unchanged for the same reason.
Kill rate: 16/16 (100%) — full rerun of the same 16-mutation set; every previously surviving mutation (M11, M12, M13, M16) is now caught by the new tests, and every previously-killed mutation is still killed.

## Final assessment

Initial state: 560 tests passing, 95% line / 94% branch coverage on the two PR-changed files, 12/16 mutations caught (75% kill rate). Four meaningful gaps were uncovered by mutation testing:

- M11: the destructive-DDL pre-check parsed SQL with `database.db_engine_spec.engine`, but no test asserted the dialect was actually plumbed through (a regression to a hard-coded `"base"` survived).
- M12: Kusto `.drop` / `.alter` detection accepted any separator (space, `;`, `\t`, `\n`), but only the canonical “single-space” form was tested — requiring a trailing space silently passed.
- M13: Kusto detection lower-cased the command, but only lowercase inputs were tested — removing `.lower()` silently passed.
- M16: the `exp.Command` ALTER fallback for Oracle/MS SQL dialects was marked `# pragma: no cover` and had no behavioral test — case-flipping the `"ALTER"` comparison silently passed.

Four targeted tests were added in the existing test files (no new test files, mirroring existing patterns like `TestDestructiveDDLBlocking` and the `test_kusto_is_destructive` parametrize block). The same 16 mutations were re-applied one-by-one in isolated runs, all 16 are now caught. No production code was modified — the gaps were tests, not implementation bugs.

## What's left for high-quality coverage

| Area | Missing test | Why it matters |
|---|---|---|
| `_data_to_statement_data` (`execute_sql.py:253–279`) | Cover list/dict/bytes data paths returned from the cache | Not PR-critical, but raises overall confidence in the response converter. |
| `transpile_to_dialect` (`parse.py:1638–1658`) | Round-trip transpile tests for at least one dialect mapping | Untouched by this PR, but reduces the unrelated coverage gap. |
| Outer `except Exception` re-raise (`execute_sql.py:218–226`) | Test that unexpected exceptions are logged and re-raised through the tool | Pre-existing pattern; useful to lock in the contract.

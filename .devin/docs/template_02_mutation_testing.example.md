# Example: Mutation Testing Log — PR #3 Escape SQL identifiers

---
pr_id: 3
pr_title: "fix(db_engine_specs): Escape SQL identifiers in db engine specs"
run_date: "2026-05-13"
agent: "devin"
repo: "loic-cunningham/superset"
branch: "mirror/pr-39840"
base_branch: "master"
mode: "mutation-testing-and-test-improvement"
status: "completed"

triage:
  coverage_level: "moderate"
  foundation_needed: false
  deselected_tests:
    - test_id: "tests/unit_tests/db_engine_specs/test_databricks.py::test_parameters_json_schema"
      reason: "Pre-existing failure unrelated to PR — fails on base branch"

target:
  behavior:
    - "Escape double-quote delimiters in Postgres, DB2, StarRocks, GSheets SQL strings"
    - "Escape backtick delimiters in Databricks, Hive, BigQuery SQL strings"
    - "Escape LIKE wildcards (%, _) in Hive df_to_sql"
  implementation_files:
    - "superset/db_engine_specs/postgres.py"
    - "superset/db_engine_specs/db2.py"
    - "superset/db_engine_specs/databricks.py"
    - "superset/db_engine_specs/starrocks.py"
    - "superset/db_engine_specs/hive.py"
    - "superset/db_engine_specs/bigquery.py"
    - "superset/db_engine_specs/gsheets.py"
  test_files:
    - "tests/unit_tests/db_engine_specs/test_postgres.py"
    - "tests/unit_tests/db_engine_specs/test_db2.py"
    - "tests/unit_tests/db_engine_specs/test_databricks.py"
    - "tests/unit_tests/db_engine_specs/test_starrocks.py"
    - "tests/unit_tests/db_engine_specs/test_hive.py"
    - "tests/unit_tests/db_engine_specs/test_bigquery.py"
    - "tests/unit_tests/db_engine_specs/test_gsheets.py"

initial_state:
  targeted_tests:
    command: "pytest tests/unit_tests/db_engine_specs/test_postgres.py tests/unit_tests/db_engine_specs/test_db2.py tests/unit_tests/db_engine_specs/test_databricks.py tests/unit_tests/db_engine_specs/test_starrocks.py tests/unit_tests/db_engine_specs/test_hive.py tests/unit_tests/db_engine_specs/test_bigquery.py tests/unit_tests/db_engine_specs/test_gsheets.py --deselect tests/unit_tests/db_engine_specs/test_databricks.py::test_parameters_json_schema -q"
    passed: 163
    failed: 0
  coverage:
    line:
      percent: 61
      covered: 954
      total: 1441
    branch:
      percent: 36
      covered: 113
      total: 310
  mutation_testing:
    valid_mutations: 15
    killed: 11
    survived: 4
    kill_rate: 73

final_state:
  targeted_tests:
    command: "pytest tests/unit_tests/db_engine_specs/test_postgres.py tests/unit_tests/db_engine_specs/test_db2.py tests/unit_tests/db_engine_specs/test_databricks.py tests/unit_tests/db_engine_specs/test_starrocks.py tests/unit_tests/db_engine_specs/test_hive.py tests/unit_tests/db_engine_specs/test_bigquery.py tests/unit_tests/db_engine_specs/test_gsheets.py --deselect tests/unit_tests/db_engine_specs/test_databricks.py::test_parameters_json_schema -q"
    passed: 166
    failed: 0
  coverage:
    line:
      percent: 62
      covered: 963
      total: 1441
    branch:
      percent: 37
      covered: 114
      total: 310
  mutation_testing:
    valid_mutations: 15
    killed: 15
    survived: 0
    kill_rate: 100
    rerun_type: "full"

commits:
  - "0e1ca3e986e5295ca83392320eb876170b09c041"

artifacts:
  pr_comment_url: "https://github.com/loic-cunningham/superset/pull/3#issuecomment-..."
---

# Mutation Testing Log — PR #3

## PR understanding

Behavior changed:
- SQL identifier escaping added to 7 database engine specs to prevent SQL injection via unescaped schema, table, catalog, and user names

Critical guarantees:
- Double-quote escaping in Postgres `search_path`, DB2 `current_schema`, StarRocks `EXECUTE AS`, GSheets `GET_METADATA`
- Backtick escaping in Databricks `USE CATALOG`/`USE SCHEMA`, Hive `SHOW VIEWS`/`SHOW TABLES`/`_partition_query`/`df_to_sql`, BigQuery `_information_schema_ref`
- LIKE wildcard escaping (%, _) in Hive `df_to_sql`

Relevant implementation files:
- `superset/db_engine_specs/postgres.py`
- `superset/db_engine_specs/db2.py`
- `superset/db_engine_specs/databricks.py`
- `superset/db_engine_specs/starrocks.py`
- `superset/db_engine_specs/hive.py`
- `superset/db_engine_specs/bigquery.py`
- `superset/db_engine_specs/gsheets.py`

Relevant tests:
- 7 corresponding test files in `tests/unit_tests/db_engine_specs/`

Likely risk areas:
- BigQuery `_information_schema_ref` builds compound identifiers — escaping in each component matters
- GSheets uses raw SQL string building, not parameterized queries
- Hive has multiple escaping contexts (backticks for identifiers, LIKE wildcards for pattern matching)

## Triage decision

Coverage level: moderate (61% line coverage)
Foundation needed: no
Deselected tests: `test_databricks.py::test_parameters_json_schema` — pre-existing failure on base branch
Reason: Existing tests cover most changed behavior (163 passing), but some escaping paths lack assertions.

## Initial targeted coverage

| File | Line % | Branch % |
|---|---|---|
| bigquery.py | 50% | 24% |
| databricks.py | 60% | 21% |
| db2.py | 98% | 100% |
| gsheets.py | 86% | 68% |
| hive.py | 37% | 14% |
| postgres.py | 69% | 56% |
| starrocks.py | 86% | 85% |
| **TOTAL** | **61%** | **36%** |

## Weak spot analysis

Pre-mutation coverage analysis identified these weak spots for targeted mutation design:
- bigquery.py: `_information_schema_ref` has only 24% branch coverage — escaping of catalog and schema components is never asserted
- gsheets.py: `get_extra_table_metadata` has 68% branch coverage — double-quote escaping in `GET_METADATA` SQL string has no test
- hive.py: only 14% branch coverage — `df_to_sql` schema escaping in `SHOW TABLES IN` is covered by line count but never asserted with special characters
- hive.py: `_partition_query` escaping is exercised but test inputs lack special characters
- postgres.py: early return condition in `get_prequeries` has branch coverage but only for the happy path

Failure area coverage:
| Failure area | Applicable? | Mutations targeting it |
|---|---|---|
| Validation/guards | yes | M8, M13 |
| Data integrity | yes | M1–M7, M9–M12, M14–M15 |
| Error handling | no | n/a |
| Security boundaries | yes | M1–M15 (SQL injection prevention) |
| Control flow | yes | M13 |
| Boundary conditions | yes | M7 (LIKE wildcards) |
| Configuration/wiring | no | n/a |
| Output contracts | no | n/a |

## Initial mutation plan

| ID | File | Mutation | Category | Breaking likelihood | Rationale |
|---|---|---|---|---|---|
| M9 | bigquery.py | Skip backtick escaping for schema in _information_schema_ref | Missing preprocessing | high | 24% branch coverage; no test asserts on escaped schema in generated SQL |
| M10 | bigquery.py | Skip backtick escaping for catalog in _information_schema_ref | Missing preprocessing | high | Same function, catalog component also unasserted |
| M11 | gsheets.py | Skip double-quote escaping in GET_METADATA | Missing preprocessing | high | No test exercises get_extra_table_metadata with special-character inputs |
| M15 | hive.py | Skip schema escaping in df_to_sql SHOW TABLES IN | Missing preprocessing | high | Line covered but no assertion verifies escaped schema in SQL output |
| M1 | postgres.py | Skip double-quote escaping in search_path | Missing preprocessing | medium | test_get_prequeries exists but may use inputs without special chars |
| M2 | db2.py | Skip double-quote escaping in current_schema | Missing preprocessing | medium | Similar pattern to postgres — test exists but input strength unclear |
| M3 | databricks.py | Skip backtick escaping for catalog | Missing preprocessing | medium | test_get_prequeries covers this path |
| M4 | databricks.py | Skip backtick escaping for schema | Missing preprocessing | medium | Same test file covers schema path |
| M5 | starrocks.py | Skip double-quote escaping in EXECUTE AS | Missing preprocessing | medium | test_impersonation_username exists |
| M6 | hive.py | Skip backtick escaping in SHOW VIEWS | Missing preprocessing | medium | test_get_view_names_escapes_schema directly tests this |
| M7 | hive.py | Skip LIKE wildcard escaping in df_to_sql | Boundary condition | medium | test_df_to_sql_escapes_like_wildcards targets this specifically |
| M8 | hive.py | Remove ESCAPE clause from SHOW TABLES LIKE | Removed guard | medium | Same test covers ESCAPE clause |
| M12 | hive.py | Skip backtick escaping for table in _partition_query | Missing preprocessing | medium | test_partition_query_escapes_identifiers covers this |
| M13 | postgres.py | Invert early return condition | Inverted condition | low | Directly tested by test_get_prequeries happy path |
| M14 | hive.py | Skip backtick escaping for schema in _partition_query | Missing preprocessing | medium | Same test as M12 |

Gap/strength ratio: 9/15 gap mutations (60%)

## Initial mutation results

| ID | Mutation | Status | Caught by |
|---|---|---|---|
| M1 | Postgres: skip double-quote escaping in search_path | Killed | `test_get_prequeries` |
| M2 | DB2: skip double-quote escaping in current_schema | Killed | `test_get_prequeries` |
| M3 | Databricks: skip backtick escaping for catalog | Killed | `test_get_prequeries` |
| M4 | Databricks: skip backtick escaping for schema | Killed | `test_get_prequeries` |
| M5 | StarRocks: skip double-quote escaping in EXECUTE AS | Killed | `test_impersonation_username` |
| M6 | Hive: skip backtick escaping in SHOW VIEWS | Killed | `test_get_view_names_escapes_schema` |
| M7 | Hive: skip LIKE wildcard escaping in df_to_sql | Killed | `test_df_to_sql_escapes_like_wildcards` |
| M8 | Hive: remove ESCAPE clause | Killed | `test_df_to_sql_escapes_like_wildcards` |
| M9 | BigQuery: skip schema escaping in _information_schema_ref | **Survived** | — |
| M10 | BigQuery: skip catalog escaping in _information_schema_ref | **Survived** | — |
| M11 | GSheets: skip double-quote escaping in GET_METADATA | **Survived** | — |
| M12 | Hive: skip table escaping in _partition_query | Killed | `test_partition_query_escapes_identifiers` |
| M13 | Postgres: invert early return condition | Killed | `test_get_prequeries` |
| M14 | Hive: skip schema escaping in _partition_query | Killed | `test_partition_query_escapes_identifiers` |
| M15 | Hive: skip schema escaping in df_to_sql SHOW TABLES | **Survived** | — |

Kill rate: 11/15 (73%)

## Fix plan

### Mutation gap fixes
- M9 + M10: BigQuery `_information_schema_ref` backtick escaping → add `test_information_schema_ref_escapes_backticks`
- M11: GSheets `get_extra_table_metadata` double-quote escaping → add `test_get_extra_table_metadata_escapes_quotes`
- M15: Hive `df_to_sql` schema backtick escaping → add `test_df_to_sql_escapes_schema_backticks`

### Coverage gap fixes
- BigQuery: existing tests call `get_view_names`/`get_materialized_view_names` but don't assert the escaped identifier appears in the SQL

### Behavioral gap fixes
- No additional edge cases identified beyond the mutation gaps

## Changes made

| File | Change | Kills/Covers |
|---|---|---|
| `test_bigquery.py` | Added `test_information_schema_ref_escapes_backticks` | Kills M9, M10 |
| `test_gsheets.py` | Added `test_get_extra_table_metadata_escapes_quotes` | Kills M11 |
| `test_hive.py` | Added `test_df_to_sql_escapes_schema_backticks` | Kills M15 |

## Final verification

Targeted suite: 166 passed, 0 failed
Line coverage: 62% (963/1441)
Branch coverage: 37% (114/310)
Kill rate: 15/15 (100%) — full rerun

## Final assessment

All 15 mutations killed. The 4 surviving mutations were all cases where the PR's escaping logic had no test verifying that special characters in identifiers are properly escaped in the generated SQL. Three new tests were added to close these gaps.

## What's left for high-quality coverage

| Area | Missing test | Why it matters |
|---|---|---|
| BigQuery `get_view_names` | Assert that escaped schema appears in the `SELECT` query | Current test verifies the return value but not the SQL sent to the database |
| BigQuery `get_materialized_view_names` | Same as above for materialized views | Escaped identifier in SQL is not verified |
| Hive file upload paths in `df_to_sql` | Test the CSV/TSV upload branches | Large uncovered section near the escaping changes, though not PR-changed lines |
| GSheets `latest_partition` | Test quote escaping in partition query | Similar pattern to `get_extra_table_metadata` but for partitions |

These are coverage opportunities identified from term-missing output and behavioral analysis, not just surviving mutations.

## Mutation quality self-assessment

- Initial kill rate: 73% — mutations were well-targeted; 4 survivors all revealed real test gaps
- Gap/strength ratio: 9/15 (60% gap)
- Failure areas covered: 4/8 (validation, data integrity, security, boundary conditions)
- Mutations informed by coverage analysis: 15/15

# Example: Final PR Comment — Escape SQL identifiers

This is what the final PR comment should look like, following the template exactly.

---

## Mutation testing — fix(db_engine_specs): Escape SQL identifiers in db engine specs

`15` mutations · `11`→`15` caught · `4`→`0` survived · kill rate `73%`→`100%`  
Tests: `163 passed`→`166 passed` · Target: 7 db engine spec test files

### Remaining uncaught mutations

No surviving mutations remained after targeted fixes.

### Summary

4 of 15 mutations survived — all were escaping logic with no test passing a malicious identifier. Added 3 tests (`test_bigquery`, `test_gsheets`, `test_hive`) to close all gaps → 100% kill rate. Remaining coverage opportunities are in adjacent untouched code paths (BigQuery view queries, GSheets partitions, Hive file uploads). Lower overall line coverage (61→62%) reflects large untouched files, not gaps in PR-changed code.

### Coverage

| Metric | Initial | Final |
|---|---:|---:|
| Tests | 163 passed | 166 passed |
| Line coverage | `61%` | `62%` |
| Branch coverage | `36%` | `37%` |
| Kill rate | `73%` (11/15) | `100%` (15/15) |
| Survived | 4 | 0 |

<details>
<summary>Changes made</summary>

| Area | Change | Result |
|---|---|---|
| `test_bigquery.py` | Added `test_information_schema_ref_escapes_backticks` | Kills M9, M10 — verifies backtick escaping in schema and catalog |
| `test_gsheets.py` | Added `test_get_extra_table_metadata_escapes_quotes` | Kills M11 — verifies double-quote escaping in table name |
| `test_hive.py` | Added `test_df_to_sql_escapes_schema_backticks` | Kills M15 — verifies schema backtick escaping in SHOW TABLES IN |
</details>

<details>
<summary>What's left for high-quality coverage</summary>

| Area | Add | Why |
|---|---|---|
| BigQuery `get_view_names` | Assert escaped schema in the SELECT query sent to DB | Current test verifies return value but not the SQL query contents |
| BigQuery `get_materialized_view_names` | Same assertion for materialized view queries | Same gap as `get_view_names` |
| GSheets `latest_partition` | Test quote escaping in partition query SQL | Similar raw-SQL pattern to `get_extra_table_metadata` |
| Hive file upload paths | Test CSV/TSV upload branches in `df_to_sql` | Large uncovered section near escaping changes |

Test quality: The PR's escaping behavior has 100% mutation resistance. Remaining coverage gaps are in adjacent code paths that use similar patterns but are not directly changed by this PR.
</details>

<details>
<summary>✓ 15 mutations caught (4 newly fixed)</summary>

<details>
<summary>✓ M1: Postgres — skip double-quote escaping in search_path</summary>

Removing the `.replace('"', '""')` call in `adjust_engine_params` causes the search_path to contain unescaped double quotes, which is caught because the test asserts the exact escaped SQL output.

Caught by: `test_postgres.py::test_get_prequeries`.
</details>

<details>
<summary>✓ M2: DB2 — skip double-quote escaping in current_schema</summary>

Removing quote escaping in the DB2 `SET CURRENT SCHEMA` prequeries causes the test to fail because it asserts the doubled-quote output.

Caught by: `test_db2.py::test_get_prequeries`.
</details>

<details>
<summary>✓ M3: Databricks — skip backtick escaping for catalog</summary>

Removing backtick escaping in `USE CATALOG` causes the test to fail on the expected escaped output.

Caught by: `test_databricks.py::test_get_prequeries`.
</details>

<details>
<summary>✓ M4: Databricks — skip backtick escaping for schema</summary>

Same pattern as M3 but for `USE SCHEMA`.

Caught by: `test_databricks.py::test_get_prequeries`.
</details>

<details>
<summary>✓ M5: StarRocks — skip double-quote escaping in EXECUTE AS</summary>

Removing quote escaping in `EXECUTE AS` causes the impersonation test to fail because it verifies the escaped username in SQL.

Caught by: `test_starrocks.py::test_impersonation_username`.
</details>

<details>
<summary>✓ M6: Hive — skip backtick escaping in SHOW VIEWS</summary>

Removing backtick escaping in `get_view_names` causes the schema escaping test to fail.

Caught by: `test_hive.py::test_get_view_names_escapes_schema`.
</details>

<details>
<summary>✓ M7: Hive — skip LIKE wildcard escaping in df_to_sql</summary>

Removing LIKE wildcard escaping causes the test to fail because it asserts that `%` and `_` characters are escaped.

Caught by: `test_hive.py::test_df_to_sql_escapes_like_wildcards`.
</details>

<details>
<summary>✓ M8: Hive — remove ESCAPE clause from SHOW TABLES LIKE</summary>

Removing the `ESCAPE '\\'` clause causes the same LIKE wildcard test to fail.

Caught by: `test_hive.py::test_df_to_sql_escapes_like_wildcards`.
</details>

<details>
<summary>✓ M9: BigQuery — skip schema escaping in _information_schema_ref (FIXED)</summary>

No existing test verified that backticks in schema names are escaped in `_information_schema_ref`. Added `test_information_schema_ref_escapes_backticks` which passes a malicious schema name and asserts the output contains doubled backticks.

Caught by: `test_bigquery.py::test_information_schema_ref_escapes_backticks`.
</details>

<details>
<summary>✓ M10: BigQuery — skip catalog escaping in _information_schema_ref (FIXED)</summary>

Same function as M9, but for the catalog parameter. The same new test covers both schema and catalog escaping.

Caught by: `test_bigquery.py::test_information_schema_ref_escapes_backticks`.
</details>

<details>
<summary>✓ M11: GSheets — skip double-quote escaping in GET_METADATA (FIXED)</summary>

No existing test verified that double quotes in table names are escaped in `get_extra_table_metadata`. Added `test_get_extra_table_metadata_escapes_quotes` which passes a malicious table name and asserts the SQL contains escaped quotes.

Caught by: `test_gsheets.py::test_get_extra_table_metadata_escapes_quotes`.
</details>

<details>
<summary>✓ M12: Hive — skip table escaping in _partition_query</summary>

Removing backtick escaping for the table name in `_partition_query` is caught by the existing partition query test.

Caught by: `test_hive.py::test_partition_query_escapes_identifiers`.
</details>

<details>
<summary>✓ M13: Postgres — invert early return condition</summary>

Inverting the `if not schema` guard in `adjust_engine_params` causes the prequeries test to fail.

Caught by: `test_postgres.py::test_get_prequeries`.
</details>

<details>
<summary>✓ M14: Hive — skip schema escaping in _partition_query</summary>

Removing backtick escaping for the schema name in `_partition_query` is caught by the same partition query test.

Caught by: `test_hive.py::test_partition_query_escapes_identifiers`.
</details>

<details>
<summary>✓ M15: Hive — skip schema escaping in df_to_sql SHOW TABLES (FIXED)</summary>

No existing test verified that backticks in schema names are escaped in the `SHOW TABLES IN` clause of `df_to_sql`. Added `test_df_to_sql_escapes_schema_backticks` which passes a malicious schema name and asserts the SQL contains escaped backticks.

Caught by: `test_hive.py::test_df_to_sql_escapes_schema_backticks`.
</details>

</details>

<details>
<summary>Notes</summary>

- Coverage is measured across all 7 engine spec files. Lower overall % is due to large files with many untouched methods (Hive file upload, BigQuery query compilation).
- Kill rate improved from 73% to 100% after adding 3 targeted tests.
- All 4 surviving mutations followed the same pattern: escaping logic existed but no test passed a malicious identifier to verify it.
- Log: `.devin/mutation-testing/pr-3-2026-05-13-escape-sql-identifiers.md`
</details>

<details>
<summary>JA</summary>

15のミューテーションのうち4つが生存 — すべて悪意ある識別子を渡すテストがないエスケープロジック。3つのテストを追加し全ギャップを解消 → キルレート100%。残りのカバレッジ機会は隣接する未変更コードパス（BigQueryビュークエリ、GSheetsパーティション、Hiveファイルアップロード）。行カバレッジが低い（61→62%）のは大きな未変更ファイルによるもので、PR変更コードのギャップではない。

修正後に生存ミューテーションなし。

変更内容:

| 領域 | 変更 | 結果 |
|---|---|---|
| `test_bigquery.py` | `test_information_schema_ref_escapes_backticks` を追加 | M9, M10 を検出 — スキーマとカタログのバッククォートエスケープを検証 |
| `test_gsheets.py` | `test_get_extra_table_metadata_escapes_quotes` を追加 | M11 を検出 — テーブル名のダブルクォートエスケープを検証 |
| `test_hive.py` | `test_df_to_sql_escapes_schema_backticks` を追加 | M15 を検出 — SHOW TABLES IN のスキーマバッククォートエスケープを検証 |

高品質なカバレッジに向けて残っていること:

| 領域 | 追加するテスト | 理由 |
|---|---|---|
| BigQuery `get_view_names` | DBに送信されるSELECTクエリでエスケープ済みスキーマを検証 | 現在のテストは戻り値を検証するがSQLクエリの内容は未検証 |
| BigQuery `get_materialized_view_names` | マテリアライズドビュークエリに同じアサーションを追加 | `get_view_names` と同じギャップ |
| GSheets `latest_partition` | パーティションクエリSQLのクォートエスケープをテスト | `get_extra_table_metadata` と類似の生SQLパターン |
| Hive ファイルアップロードパス | `df_to_sql` のCSV/TSVアップロードブランチをテスト | エスケープ変更の近くにある大きな未カバーセクション |

テスト品質: PRのエスケープ動作は100%のミューテーション耐性を持つ。残りのカバレッジギャップは類似パターンを使用する隣接コードパスにあるが、このPRで直接変更されたものではない。

<details>
<summary>✓ 15 検出済みミューテーション（4つ新規修正）</summary>

<details>
<summary>✓ M1: Postgres — search_pathのダブルクォートエスケープ削除</summary>

`adjust_engine_params` の `.replace('"', '""')` を削除すると、テストがエスケープ済みSQL出力を検証しているため検出される。

検出テスト: `test_postgres.py::test_get_prequeries`。
</details>

<details>
<summary>✓ M2: DB2 — current_schemaのダブルクォートエスケープ削除</summary>

DB2の `SET CURRENT SCHEMA` でクォートエスケープを削除すると、テストがダブルクォート出力を検証しているため検出される。

検出テスト: `test_db2.py::test_get_prequeries`。
</details>

<details>
<summary>✓ M9: BigQuery — _information_schema_refのスキーマエスケープ省略（修正済み）</summary>

`_information_schema_ref` でスキーマ名のバッククォートエスケープを検証するテストがなかった。`test_information_schema_ref_escapes_backticks` を追加して修正。

検出テスト: `test_bigquery.py::test_information_schema_ref_escapes_backticks`。
</details>

<details>
<summary>✓ M11: GSheets — GET_METADATAのダブルクォートエスケープ省略（修正済み）</summary>

`get_extra_table_metadata` でテーブル名のダブルクォートエスケープを検証するテストがなかった。`test_get_extra_table_metadata_escapes_quotes` を追加して修正。

検出テスト: `test_gsheets.py::test_get_extra_table_metadata_escapes_quotes`。
</details>

<details>
<summary>✓ M15: Hive — df_to_sql SHOW TABLESのスキーマエスケープ省略（修正済み）</summary>

`df_to_sql` の `SHOW TABLES IN` でスキーマ名のバッククォートエスケープを検証するテストがなかった。`test_df_to_sql_escapes_schema_backticks` を追加して修正。

検出テスト: `test_hive.py::test_df_to_sql_escapes_schema_backticks`。
</details>

</details>

| 状態 | テスト | 行 | ブランチ | kill rate | 生存 |
|---|---:|---:|---:|---:|---:|
| 初期 | 163 | `61%` | `36%` | `73%` | 4 |
| 最終 | 166 | `62%` | `37%` | `100%` | 0 |

補足:

- カバレッジは全7エンジンスペックファイルで測定。全体の%が低いのはタッチされていないメソッドが多い大きなファイルがあるため。
- 3つのターゲットテスト追加後、キルレートが73%から100%に改善。
- すべての生存ミューテーションは同じパターン: エスケープロジックは存在するが悪意のある識別子を渡して検証するテストがなかった。
- ログ: `.devin/mutation-testing/pr-3-2026-05-13-escape-sql-identifiers.md`
</details>

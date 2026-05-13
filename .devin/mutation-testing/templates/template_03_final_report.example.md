# Example: PR Comment Stages (generated)

This file contains the **rendered output** of each of the four `render_pr_comment.py` modes,
produced by feeding the renderer with payloads modeled on real mutation-testing runs
(PR #27 in this repo). Regenerate by running
`python /tmp/gen_examples.py` (script lives under `.devin/mutation-testing/scripts/` in PR scope).


---

## Example: `mode: "status"`

## Mutation testing — fix(db_engine_specs): Escape SQL identifiers in db engine specs

**Status — in progress**

Reviewing the PR's targeted test suite and experimenting with mutation notation against the changed behaviour. Initial mutation results, then a final report, will follow as separate comments.

<details>
<summary>JA</summary>

**ミューテーションテスト — 実行中**

該当PRのターゲットテストスイートをレビューし、変更箇所に対するミューテーション記法を検証中です。初期ミューテーション結果と最終レポートを別コメントで続けて投稿します。
</details>


---

## Example: `mode: "foundation"`

## Mutation testing — feat(mcp): include applied dashboard filters in get_chart_info

**Foundation — test coverage uplift**

Existing tests covered only 29% of changed-file lines (10% branch). Devin wrote 46 foundation tests across two test files, bringing baseline coverage to 100%/100% (line/branch) before any mutations are applied. Initial mutation results will follow.

### Progression

| Metric | Original | Foundation |
|---|---|---|
| Tests | 72 passed | 118 passed |
| Line coverage | `29%` | `100%` |
| Branch coverage | `10%` | `100%` |
| Kill rate | N/A | N/A |
| Survived | N/A | N/A |

Kill rate is `N/A` at this stage — no mutations have been applied yet. Kill rate is reported in the next comment after the initial mutation pass.

<details>
<summary>Foundation tests added</summary>

| File | Tests added | Covers |
|---|---:|---|
| `tests/unit_tests/mcp_service/chart/test_chart_helpers.py` | 46 | 8 critical guarantees of chart_helpers.py (filter shaping, status mapping, error paths) |
| `tests/unit_tests/mcp_service/chart/tool/test_get_chart_info.py` | 17 | async _attach_dashboard_filters happy/error paths and slice-id resolution |
</details>

<details>
<summary>Notes</summary>

- Foundation phase triggered because triage classified coverage of changed files as Very low (29%).
- Foundation tests committed in 2adfd8e118 before any mutation work began.
- Log: `.devin/mutation-testing/pr-27-2026-05-13-mcp-dashboard-filters.md`
</details>

<details>
<summary>JA</summary>

**基盤 — テストカバレッジの底上げ**

既存テストが変更箇所の 29% (ブランチ 10%) しかカバーできていなかったため、Devin が 46 件の基盤テストを追加し、ミューテーション適用前のベースラインを 100%/100% (行/ブランチ) に引き上げました。初期ミューテーション結果は別コメントで報告します。

### 進捗

| 指標 | 当初 | 基盤後 |
|---|---|---|
| テスト | 72 passed | 118 passed |
| 行カバレッジ | `29%` | `100%` |
| ブランチ | `10%` | `100%` |
| キル率 | N/A | N/A |
| 生存 | N/A | N/A |

ミューテーション未実行のため初期段階のキル率は `N/A` です。次コメントで初期ミューテーション結果を報告します。

<details>
<summary>追加した基盤テスト</summary>

| ファイル | 追加テスト数 | カバー対象 |
|---|---:|---|
| `tests/unit_tests/mcp_service/chart/test_chart_helpers.py` | 46 | chart_helpers.py の 8 つの重要保証(フィルタ整形・ステータスマッピング・エラー経路) |
| `tests/unit_tests/mcp_service/chart/tool/test_get_chart_info.py` | 17 | 非同期 _attach_dashboard_filters の正常系・例外系および slice-id 解決 |
</details>

補足:

- トリアージで変更ファイルのカバレッジを Very low (29%) と判定し、基盤フェーズを起動。
- 基盤テストはミューテーション作業前に 2adfd8e118 でコミット済み。
- ログ: `.devin/mutation-testing/pr-27-2026-05-13-mcp-dashboard-filters.md`
</details>


---

## Example: `mode: "initial"`

## Mutation testing — feat(mcp): include applied dashboard filters in get_chart_info

**Initial mutation results — checkpoint**

Kill rate `86% (12/14)` · Survivors `2`

Initial mutation pass killed 12/14 (86%). The two survivors are classified below — Devin will add an exact-equality test for M2 and dismiss M10 (Pydantic str-Enum coercion produces byte-identical JSON).

Target: tests/unit_tests/mcp_service/chart/

### Progression

| Metric | Original | Foundation | Initial mutation |
|---|---|---|---|
| Tests | 72 passed | 118 passed | 129 passed |
| Line coverage | `29%` | `100%` | `90%` |
| Branch coverage | `10%` | `100%` | `84%` |
| Kill rate | N/A | N/A | `86% (12/14)` |
| Survived | N/A | N/A | `2` |

### Survivors — to be resolved in final report

<details>
<summary>M2 — Substring match replaces equality on adhoc subject lookup <code>pending</code></summary>

| Finding | Details |
|---|---|
| Gap | No targeted test asserts exact-equality semantics; overlapping substrings could collide silently. |
| Mutation | Replace `subject == self.adhoc_subject` with `self.adhoc_subject in subject`. |
| Risk | Two adhoc subjects whose names overlap (e.g., 'orders' and 'orders_v2') would be conflated. |
| Planned test | Add a test that registers two overlapping adhoc subjects and asserts each resolves to its own object. |
</details>

<details>
<summary>M10 — Pydantic str-Enum coercion preserves serialized JSON <code>≡ dismissed</code></summary>

| Finding | Details |
|---|---|
| Gap | No test can distinguish enum-member from `.value` at the JSON serialization boundary. |
| Mutation | Replace `status=DashboardFilterStatus.APPLIED` with `status=DashboardFilterStatus.APPLIED.value`. |
| Risk | None — Pydantic v2 serializes both forms to the same JSON string when the enum subclasses `str`. |
| Dismissal reason | Verified empirically via `model_dump_json()` round-trip on a model containing the str-Enum: both forms produce byte-identical JSON. No observable behaviour differs. |
</details>

<details>
<summary>✓ 4 mutations caught</summary>

- `M1` — Skip dashboard preprocessing (caught by: `test_get_chart_info_with_dashboard_id_attaches_filters`)
- `M3` — Drop applied/unapplied bucketing (caught by: `test_build_applied_dashboard_filters_buckets`)
- `M4` — Return empty filter list (caught by: `test_get_chart_info_returns_filters`)
- `M5` — Hardcode owner_id to 1 (caught by: `test_chart_helpers_uses_real_owner`)
</details>

<details>
<summary>Test quality</summary>

14 mutations spanning 6 failure areas; gap/strength split is 11/3.
</details>

<details>
<summary>Notes</summary>

- Initial coverage and kill rate measured against the foundation tests committed in 2adfd8e118.
- M2 will be killed in Improve (Phase 8); M10 is documented as equivalent in the log.
- Log: `.devin/mutation-testing/pr-27-2026-05-13-mcp-dashboard-filters.md`
</details>

<details>
<summary>JA</summary>

**初期ミューテーション結果 — チェックポイント**

キル率 `86% (12/14)` · 生存 `2`

初期パスで 12/14 (86%) をキル。残り 2 件を下記で分類 — M2 は等価テストを追加して解決、M10 は Pydantic str-Enum の同等性により却下します。

### 進捗

| 指標 | 当初 | 基盤後 | 初期ミューテーション |
|---|---|---|---|
| テスト | 72 passed | 118 passed | 129 passed |
| 行カバレッジ | `29%` | `100%` | `90%` |
| ブランチ | `10%` | `100%` | `84%` |
| キル率 | N/A | N/A | `86% (12/14)` |
| 生存 | N/A | N/A | `2` |

### 生存ミューテーション — 最終レポートで解決

<details>
<summary>M2 — 部分一致が等価チェックを置換 (adhoc subject 探索) <code>保留</code></summary>

| 観点 | 詳細 |
|---|---|
| ギャップ | 等価セマンティクスを保証する専用テストが存在せず、部分文字列衝突を検知できない。 |
| 変異内容 | `subject == self.adhoc_subject` を `self.adhoc_subject in subject` に置換。 |
| リスク | 部分文字列が衝突する 2 つの adhoc subject (例: 'orders' と 'orders_v2') が同一視される。 |
| 予定テスト | 重複する 2 つの adhoc subject を登録し、それぞれが個別のオブジェクトに解決されることを確認するテストを追加。 |
</details>

<details>
<summary>M10 — Pydantic str-Enum の同等化 <code>≡ 同等のため却下</code></summary>

| 観点 | 詳細 |
|---|---|
| ギャップ | JSON 直列化境界で enum と .value の差分を検知できるテストは存在しない。 |
| 変異内容 | `status=DashboardFilterStatus.APPLIED` を `status=DashboardFilterStatus.APPLIED.value` に置換。 |
| リスク | なし — Pydantic v2 では str を継承した Enum はどちらの形でも同一 JSON 文字列に直列化される。 |
| 却下理由 | str-Enum を含むモデルで `model_dump_json()` ラウンドトリップを実行し、両形式がバイト一致する JSON を出力することを確認済み。観測可能な差分は存在しない。 |
</details>

<details>
<summary>✓ 4 件キャッチ済み</summary>

- `M1` — Skip dashboard preprocessing (検出テスト: `test_get_chart_info_with_dashboard_id_attaches_filters`)
- `M3` — Drop applied/unapplied bucketing (検出テスト: `test_build_applied_dashboard_filters_buckets`)
- `M4` — Return empty filter list (検出テスト: `test_get_chart_info_returns_filters`)
- `M5` — Hardcode owner_id to 1 (検出テスト: `test_chart_helpers_uses_real_owner`)
</details>

<details>
<summary>テスト品質</summary>

14 件のミューテーションが 6 つの失敗領域をカバー、gap/strength 比は 11/3。
</details>

補足:

- 初期カバレッジとキル率は 2adfd8e118 でコミットした基盤テストに対して測定。
- M2 は Phase 8 (Improve) でキル予定、M10 はログで同等として記録。
- ログ: `.devin/mutation-testing/pr-27-2026-05-13-mcp-dashboard-filters.md`
</details>


---

## Example: `mode: "final"`

## Mutation testing — feat(mcp): include applied dashboard filters in get_chart_info

**Final report**

`6` mutations · `5` killed · `1` dismissed · `0` remaining · final kill rate `100% (13/13)`  
Tests: `129 passed`→`132 passed` · Target: tests/unit_tests/mcp_service/chart/

13/14 mutations killed (93% final kill rate). The single dismissed mutation (M10, Pydantic str-Enum coercion) is documented as functionally equivalent with byte-identical JSON output. No `❌` items remain.

### Resolved

Every mutation that survived the initial pass is resolved below as `✓ killed` (a new test catches it) or `≡ dismissed` (functionally equivalent — explained).

<details>
<summary>✓ M2 — Substring match replaces equality on adhoc subject lookup</summary>

New test registers two adhoc subjects whose names overlap and asserts each resolves to its own object — the substring mutant fails this test.

Caught by: `test_get_chart_info_adhoc_subject_exact_equality`.
</details>

<details>
<summary>≡ M10 — Pydantic str-Enum coercion preserves serialized JSON (dismissed as equivalent)</summary>

No test can distinguish the two forms at any observable boundary. Documented as equivalent in the log.

Dismissal reason: Pydantic v2 serialises `DashboardFilterStatus.APPLIED` and `DashboardFilterStatus.APPLIED.value` to byte-identical JSON; verified via `model_dump_json()` round-trip..
</details>

### Progression

| Metric | Original | Foundation | Initial mutation | Final |
|---|---|---|---|---|
| Tests | 72 passed | 118 passed | 129 passed | 132 passed |
| Line coverage | `29%` | `100%` | `90%` | `90%` |
| Branch coverage | `10%` | `100%` | `84%` | `84%` |
| Kill rate | N/A | N/A | `86% (12/14)` | `100% (13/13)` |
| Survived | N/A | N/A | `2` | `0 (1 dismissed)` |

Final kill rate formula: `killed / (total − dismissed)`. Dismissed mutations are excluded from the denominator because they are functionally equivalent and no test can distinguish them from the original code.

<details>
<summary>Changes made</summary>

| Area | Change | Result |
|---|---|---|
| tests/unit_tests/mcp_service/chart/tool/test_get_chart_info.py | Added 3 exact-equality assertions on adhoc subject lookup | M2 killed; substring mutants fail. |
</details>

<details>
<summary>What's left for high-quality coverage</summary>

| Area | Add | Why |
|---|---|---|
| End-to-end dashboard_id flow | Integration test against a persisted dashboard | Current end-to-end test mocks `build_applied_dashboard_filters` — a real integration would catch DB-shape regressions. |
| Enum value protection | Snapshot test on `DashboardFilterStatus` string values | Defends against silent enum renames that would break MCP consumers. |

Test quality: Improvement added 3 targeted tests that lock exact-equality semantics on the adhoc subject lookup; full targeted suite stays green..
</details>

<details>
<summary>✓ 5 mutations caught (1 newly fixed)</summary>

<details>
<summary>✓ M1 — Skip dashboard preprocessing</summary>

Caught by: `test_get_chart_info_with_dashboard_id_attaches_filters`.
</details>

<details>
<summary>✓ M3 — Drop applied/unapplied bucketing</summary>

Caught by: `test_build_applied_dashboard_filters_buckets`.
</details>

<details>
<summary>✓ M4 — Return empty filter list</summary>

Caught by: `test_get_chart_info_returns_filters`.
</details>

<details>
<summary>✓ M5 — Hardcode owner_id to 1</summary>

Caught by: `test_chart_helpers_uses_real_owner`.
</details>

</details>

<details>
<summary>Notes</summary>

- Final suite: 132 passed, 0 failed. Suite stable across the run.
- Final mutation result came from a full rerun (not survivor-focused).
- Log: `.devin/mutation-testing/pr-27-2026-05-13-mcp-dashboard-filters.md`
</details>

<details>
<summary>JA</summary>

**最終レポート**

`6` 件のミューテーション · `5` 件キル · `1` 件却下 · `0` 件残存 · 最終キル率 `100% (13/13)`

13/14 をキル (最終キル率 93%)。同等として却下した 1 件 (M10, Pydantic str-Enum) はバイト一致する JSON 出力を持つことを文書化。`❌` 残存はゼロ。

### 解決

<details>
<summary>✓ M2 — 部分一致が等価チェックを置換 (adhoc subject 探索)</summary>

重複名を持つ 2 つの adhoc subject を登録し、それぞれが個別オブジェクトに解決されることを確認する新規テスト。部分一致ミュータントはこれを通らない。

検出テスト: `test_get_chart_info_adhoc_subject_exact_equality`.
</details>

<details>
<summary>≡ M10 — Pydantic str-Enum の同等化（同等のため却下）</summary>

観測可能な境界では両形式を区別できない。同等としてログに記録。

却下理由: Pydantic v2 は `DashboardFilterStatus.APPLIED` と `DashboardFilterStatus.APPLIED.value` をバイト一致する JSON に直列化する。`model_dump_json()` ラウンドトリップで実証済み。.
</details>

### 進捗

| 指標 | 当初 | 基盤後 | 初期ミューテーション | 最終 |
|---|---|---|---|---|
| テスト | 72 passed | 118 passed | 129 passed | 132 passed |
| 行カバレッジ | `29%` | `100%` | `90%` | `90%` |
| ブランチ | `10%` | `100%` | `84%` | `84%` |
| キル率 | N/A | N/A | `86% (12/14)` | `100% (13/13)` |
| 生存 | N/A | N/A | `2` | `0 (1 dismissed)` |

最終キル率の式: `kill / (total − dismissed)`。同等として却下されたミューテーションは分母から除外します。

変更内容:

| 領域 | 変更 | 結果 |
|---|---|---|
| tests/unit_tests/mcp_service/chart/tool/test_get_chart_info.py | adhoc subject 探索に等価アサーション 3 件追加 | M2 をキル。部分一致ミュータントはテスト失敗。 |

高品質なカバレッジに向けて残っていること:

| 領域 | 追加するテスト | 理由 |
|---|---|---|
| dashboard_id E2E フロー | 永続化ダッシュボードに対する結合テスト | 現状の E2E は `build_applied_dashboard_filters` をモック。実 DB を使った結合テストで DB スキーマ起因の回帰を検出可能。 |
| Enum 値保護 | `DashboardFilterStatus` 文字列値のスナップショットテスト | MCP コンシューマーを破壊するサイレントな enum リネームを検知。 |

テスト品質: Improvement で adhoc subject 探索の等価アサーション 3 件を追加し、ターゲットスイートは全て成功。

<details>
<summary>✓ 5 件のキャッチ（うち 1 件は新規修正）</summary>

<details>
<summary>✓ M1 — ダッシュボード前処理スキップ</summary>

検出テスト: `test_get_chart_info_with_dashboard_id_attaches_filters`.
</details>

<details>
<summary>✓ M3 — applied/unapplied 分類の喪失</summary>

検出テスト: `test_build_applied_dashboard_filters_buckets`.
</details>

<details>
<summary>✓ M4 — 空フィルタ返却</summary>

検出テスト: `test_get_chart_info_returns_filters`.
</details>

<details>
<summary>✓ M5 — owner_id を 1 固定化</summary>

検出テスト: `test_chart_helpers_uses_real_owner`.
</details>

</details>

補足:

- 最終スイート: 132 件成功、0 件失敗。実行中安定。
- 最終ミューテーション結果はフル再実行 (survivor-focused ではない)。
- ログ: `.devin/mutation-testing/pr-27-2026-05-13-mcp-dashboard-filters.md`
</details>

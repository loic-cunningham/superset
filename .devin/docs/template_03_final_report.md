# Template: Final PR Comment Report (Stage 3)

This template defines the exact structure for the final PR comment posted in Phase 12. **Follow this template exactly. Do not create a custom format.**

---

## Template

````md
## Mutation testing — {{feature_or_pr_title}}

`{{mutation_count}}` mutations · `{{initial_caught_count}}`→`{{final_caught_count}}` caught · `{{initial_survived_count}}`→`{{final_survived_count}}` survived · kill rate `{{initial_kill_rate}}`→`{{final_kill_rate}}`  
Tests: `{{baseline_result}}`→`{{final_result}}` · Target: {{targeted_suite_description}}

### Remaining uncaught mutations

<!-- If none remain, write this single line and omit the details block: -->
<!-- No surviving mutations remained after targeted fixes. -->

<!-- Otherwise, repeat this block for each final surviving mutation. -->

<details>
<summary>❌ {{surviving_mutation_name}}</summary>

| Finding | Details |
|---|---|
| Gap | {{short_english_gap}} |
| Mutation | {{what_code_change_was_made}} |
| Risk | {{why_this_matters_if_regressed}} |
</details>

### Summary

<!-- 2-3 lines max. Cover: what was found, what was fixed, what's left, and any important notes. The reader should not need to expand any details section to understand the outcome. -->

{{brief_scannable_summary_covering_findings_fixes_gaps_and_notes}}

### Coverage

| Metric | Initial | Final |
|---|---:|---:|
| Tests | {{initial_passed_tests}} passed | {{final_passed_tests}} passed |
| Line coverage | `{{initial_line_coverage_percent}}` | `{{final_line_coverage_percent}}` |
| Branch coverage | `{{initial_branch_coverage_percent}}` | `{{final_branch_coverage_percent}}` |
| Kill rate | `{{initial_kill_rate_percent}}` ({{initial_killed}}/{{total}}) | `{{final_kill_rate_percent}}` ({{final_killed}}/{{total}}) |
| Survived | {{initial_survived}} | {{final_survived}} |

<details>
<summary>Changes made</summary>

| Area | Change | Result |
|---|---|---|
| {{changed_area_1}} | {{brief_change_1}} | {{result_1}} |
| {{changed_area_2}} | {{brief_change_2}} | {{result_2}} |
</details>

<details>
<summary>What's left for high-quality coverage</summary>

| Area | Add | Why |
|---|---|---|
| {{gap_area_1}} | {{specific_test_to_add_1}} | {{short_reason_1}} |
| {{gap_area_2}} | {{specific_test_to_add_2}} | {{short_reason_2}} |
| {{gap_area_3}} | {{specific_test_to_add_3}} | {{short_reason_3}} |

Test quality: {{brief_at_a_glance_test_quality_comment}}.
</details>

<details>
<summary>✓ {{final_caught_count}} mutations caught ({{newly_fixed_count}} newly fixed)</summary>

<!-- Repeat this nested block for each caught or newly fixed mutation. -->

<details>
<summary>✓ {{caught_mutation_name}}</summary>

{{one_sentence_english_explanation}}

Caught by: {{test_names_or_assertions_that_caught_it}}.
</details>

</details>

<details>
<summary>Notes</summary>

- {{coverage_scope_comment}}
- {{mutation_score_comment}}
- {{main_surviving_mutation_pattern_comment}}
- Log: `{{mutation_testing_log_path}}`
</details>

<details>
<summary>JA</summary>

{{japanese_summary_translation}}

<!-- Translate all remaining uncaught mutations. If none, write: 修正後に生存ミューテーションなし。 -->

<details>
<summary>❌ {{japanese_surviving_mutation_name}}</summary>

| 観点 | 詳細 |
|---|---|
| ギャップ | {{short_japanese_gap}} |
| 変異内容 | {{japanese_mutation_description}} |
| リスク | {{japanese_risk_description}} |
</details>

変更内容:

| 領域 | 変更 | 結果 |
|---|---|---|
| {{japanese_changed_area_1}} | {{japanese_brief_change_1}} | {{japanese_result_1}} |
| {{japanese_changed_area_2}} | {{japanese_brief_change_2}} | {{japanese_result_2}} |

高品質なカバレッジに向けて残っていること:

| 領域 | 追加するテスト | 理由 |
|---|---|---|
| {{japanese_gap_area_1}} | {{japanese_specific_test_to_add_1}} | {{japanese_short_reason_1}} |
| {{japanese_gap_area_2}} | {{japanese_specific_test_to_add_2}} | {{japanese_short_reason_2}} |
| {{japanese_gap_area_3}} | {{japanese_specific_test_to_add_3}} | {{japanese_short_reason_3}} |

テスト品質: {{japanese_at_a_glance_test_quality_comment}}。

<details>
<summary>✓ {{final_caught_count}} 検出済みミューテーション</summary>

<details>
<summary>✓ {{japanese_caught_mutation_name}}</summary>

{{one_sentence_japanese_explanation}}

検出テスト: {{japanese_test_names_or_assertions}}。
</details>

</details>

| 状態 | テスト | 行 | ブランチ | kill rate | 生存 |
|---|---:|---:|---:|---:|---:|
| 初期 | {{initial_passed_tests}} | `{{initial_line_coverage_percent}}` | `{{initial_branch_coverage_percent}}` | `{{initial_kill_rate_percent}}` | {{initial_survived}} |
| 最終 | {{final_passed_tests}} | `{{final_line_coverage_percent}}` | `{{final_branch_coverage_percent}}` | `{{final_kill_rate_percent}}` | {{final_survived}} |

補足:

- {{japanese_coverage_scope_comment}}
- {{japanese_mutation_score_comment}}
- {{japanese_surviving_mutation_pattern_comment}}
- ログ: `{{mutation_testing_log_path}}`
</details>
````

---

## Style rules

- **Always visible:** header stats, remaining uncaught mutations, summary, coverage table.
- **Always collapsed (`<details>`):** changes made, what's left, caught mutations, notes, JA.
- Remaining uncaught mutations come first after the summary stats — they are the actionable items.
- Use `❌` for remaining uncaught mutation accordions, `✓` for caught.
- Keep everything brief. One sentence per mutation explanation.
- The Coverage table uses a compact Initial/Final column layout — no `<br>` tags or raw line counts.
- Default visible content is English only. All Japanese content goes in the bottom `JA` accordion.
- The `JA` section must include translations of **all** sections: summary, remaining uncaught mutations, changes made, what's left, caught mutations, coverage table, and notes.
- Use GitHub-native markdown only: tables, `<details><summary>` accordions, no screenshots, no external formatting dependencies.

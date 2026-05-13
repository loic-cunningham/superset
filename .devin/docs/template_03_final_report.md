# Template: Final PR Comment Report (Stage 3)

This template defines the exact structure for the final PR comment posted in Phase 12. **Follow this template exactly. Do not create a custom format.**

---

## Template

````md
## Mutation testing — {{feature_or_pr_title}}

`{{mutation_count}}` mutations · initial `{{initial_caught_count}}` caught / `{{initial_survived_count}}` survived · final `{{final_caught_count}}` caught / `{{final_survived_count}}` survived  
❌ Initial uncaught: `{{initial_survived_count}}` · Final uncaught: `{{final_survived_count}}` · ✓ Final verified caught: `{{final_caught_count}}`  
Baseline: `{{baseline_result}}` · Final: `{{final_result}}` · Target: {{targeted_suite_description}}

### Goal

Devin reviewed targeted coverage and mutation resistance, then added targeted tests/fixes for meaningful surviving mutations to bring the PR closer to high-quality behavioral coverage.

### Remaining uncaught mutations

<!-- If none remain, write this single line and omit the details block: -->
<!-- No surviving mutations remained after targeted fixes. -->

<!-- Otherwise, repeat this block for each final surviving mutation. Keep the summary line English-only. -->

<details>
<summary>❌ {{surviving_mutation_name}}</summary>

| Finding | Details |
|---|---|
| Gap | {{short_english_gap}} |
| Mutation | {{what_code_change_was_made}} |
| Risk | {{why_this_matters_if_regressed}} |

---

#### JA

| 観点 | 詳細 |
|---|---|
| ギャップ | {{short_japanese_gap}} |
| 変異内容 | {{japanese_mutation_description}} |
| リスク | {{japanese_risk_description}} |
</details>

### Fixed / verified caught mutations

<details>
<summary>{{final_caught_count}} mutations caught by the targeted suite</summary>

<!-- Repeat this nested block for each caught or newly fixed mutation. Use ✓ only here, not on the parent accordion. -->

<details>
<summary>✓ {{caught_mutation_name}}</summary>

{{one_sentence_english_explanation}}

Caught by: {{test_names_or_assertions_that_caught_it}}.

---

#### JA

{{one_sentence_japanese_explanation}}

検出テスト: {{japanese_test_names_or_assertions}}。
</details>

</details>

### Summary

{{brief_english_summary_of_initial_findings_and_final_state}}

### Changes made

| Area | Change | Result |
|---|---|---|
| {{changed_area_1}} | {{brief_change_1}} | {{result_1}} |
| {{changed_area_2}} | {{brief_change_2}} | {{result_2}} |

### What's left for high-quality coverage

| Area | Add | Why |
|---|---|---|
| {{gap_area_1}} | {{specific_test_to_add_1}} | {{short_reason_1}} |
| {{gap_area_2}} | {{specific_test_to_add_2}} | {{short_reason_2}} |
| {{gap_area_3}} | {{specific_test_to_add_3}} | {{short_reason_3}} |

Test quality: {{brief_at_a_glance_test_quality_comment}}.

### Coverage + mutation score

| State | Targeted suite | Line coverage | Branch coverage | Mutation kill rate | Survived |
|---|---:|---:|---:|---:|---:|
| Initial | `{{initial_suite_pass_rate}}`<br>{{initial_passed_tests}} / {{initial_total_tests}} tests | `{{initial_line_coverage_percent}}`<br>{{initial_covered_lines}} / {{initial_total_lines}} lines | `{{initial_branch_coverage_percent}}`<br>{{initial_covered_branches}} / {{initial_total_branches}} branches | `{{initial_kill_rate_percent}}`<br>{{initial_killed_mutations}} / {{total_mutations}} killed | `{{initial_survived_rate_percent}}`<br>{{initial_survived_mutations}} / {{total_mutations}} survived |
| Final | `{{final_suite_pass_rate}}`<br>{{final_passed_tests}} / {{final_total_tests}} tests | `{{final_line_coverage_percent}}`<br>{{final_covered_lines}} / {{final_total_lines}} lines | `{{final_branch_coverage_percent}}`<br>{{final_covered_branches}} / {{final_total_branches}} branches | `{{final_kill_rate_percent}}`<br>{{final_killed_mutations}} / {{total_mutations}} killed | `{{final_survived_rate_percent}}`<br>{{final_survived_mutations}} / {{total_mutations}} survived |

Comments:

- {{coverage_scope_comment}}
- {{mutation_score_comment}}
- {{main_surviving_mutation_pattern_comment}}
- Log: `{{mutation_testing_log_path}}`

<details>
<summary>JA</summary>

{{japanese_summary_translation}}

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

カバレッジとミューテーションスコア:

| 状態 | 対象テストスイート | 行カバレッジ | ブランチカバレッジ | ミューテーション kill rate | 生存 |
|---|---:|---:|---:|---:|---:|
| 初期 | `{{initial_suite_pass_rate}}`<br>{{initial_passed_tests}} / {{initial_total_tests}} テスト | `{{initial_line_coverage_percent}}`<br>{{initial_covered_lines}} / {{initial_total_lines}} 行 | `{{initial_branch_coverage_percent}}`<br>{{initial_covered_branches}} / {{initial_total_branches}} ブランチ | `{{initial_kill_rate_percent}}`<br>{{initial_killed_mutations}} / {{total_mutations}} 検出 | `{{initial_survived_rate_percent}}`<br>{{initial_survived_mutations}} / {{total_mutations}} 生存 |
| 最終 | `{{final_suite_pass_rate}}`<br>{{final_passed_tests}} / {{final_total_tests}} テスト | `{{final_line_coverage_percent}}`<br>{{final_covered_lines}} / {{final_total_lines}} 行 | `{{final_branch_coverage_percent}}`<br>{{final_covered_branches}} / {{final_total_branches}} ブランチ | `{{final_kill_rate_percent}}`<br>{{final_killed_mutations}} / {{total_mutations}} 検出 | `{{final_survived_rate_percent}}`<br>{{final_survived_mutations}} / {{total_mutations}} 生存 |

補足:

- {{japanese_coverage_scope_comment}}
- {{japanese_mutation_score_comment}}
- {{japanese_surviving_mutation_pattern_comment}}
- ログ: `{{mutation_testing_log_path}}`
</details>
````

---

## Style rules

- Default visible content is English only.
- Put remaining uncaught/surviving mutations first.
- Use `❌` for remaining uncaught mutation accordions.
- Use `✓` only for individual fixed/caught mutations, never on the parent accordion.
- Each expanded remaining uncaught finding has: English table (`Finding / Details`), divider (`---`), Japanese table under `#### JA`.
- Fixed/caught mutations are collapsed under one parent accordion.
- Bottom `JA` accordion translates: summary, changes made, high-quality coverage next steps, test-quality comment, coverage + mutation score table, and comments.
- Keep everything brief and at-a-glance.
- Include both initial and final state when fixes are made.
- Mention what Devin fixed to close the gaps.
- Use GitHub-native markdown only: tables, `<details><summary>` accordions, no screenshots, no external formatting dependencies.

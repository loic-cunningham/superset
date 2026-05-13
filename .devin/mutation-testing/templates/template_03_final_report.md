# Template: PR Comment Stages (template_03_final_report.md)

This template defines the **only** valid format for every PR comment posted during the mutation-testing workflow. The agent **MUST** post comments by calling `render_pr_comment.py` against a structured JSON payload. **Hand-writing a PR comment is forbidden** — see the handoff for the rationale.

There are **four comment shapes**, selected by the `mode` field in the JSON payload:

| Mode             | When posted                                              | Required? |
|------------------|----------------------------------------------------------|-----------|
| `status`         | Phase 1 (kickoff) when Foundation phase is **not** run.  | Yes (when foundation skipped) |
| `foundation`     | Phase 0b end, when Foundation phase **is** run.          | Yes (when foundation runs) |
| `initial`        | Phase 7 (initial mutation results checkpoint).           | Yes (always) |
| `final`          | Phase 12 (final report, after Improve + Verify).         | Yes (always) |

A run posts **exactly two PR comments** when foundation is skipped (`status` → `initial` is replaced by a single `initial`-only flow if you choose; in practice we still keep three — see handoff Phase 7) or three when foundation runs (`foundation` → `initial` → `final`).

> **Universal rule:** every comment, regardless of mode, **MUST** carry a full Japanese (`JA`) mirror inside a `<details><summary>JA</summary>…</details>` accordion. The renderer rejects payloads missing the `ja` block.

---

## Universal payload shape

```json
{
  "mode": "status|foundation|initial|final",
  "feature_or_pr_title": "feat(mcp): include applied dashboard filters in get_chart_info",
  "targeted_suite_description": "tests/unit_tests/mcp_service/chart/...",
  "log_path": ".devin/mutation-testing/pr-27-2026-05-13-mcp-dashboard-filters.md",
  "ja": { ... mode-specific Japanese mirror ... }
}
```

The fields below describe the mode-specific extras. The renderer reads the shared header values (title, target description, log path) on **every** mode.

---

## Mode: `status` — Phase 1 short status preamble

Posted when Phase 0 triage classifies coverage as **moderate** or **good** (Foundation is skipped). Tells the reviewer that Devin has begun reviewing tests and experimenting with mutations. Short, clean, minimal.

### Payload extras

```json
{
  "mode": "status",
  "summary": "Reviewing the PR's targeted test suite and experimenting with mutation notation against the changed behaviour. Initial mutation results, then a final report, will follow as separate comments.",
  "ja": {
    "summary": "該当PRのターゲットテストスイートをレビューし、変更箇所に対するミューテーション記法を検証中です。初期ミューテーション結果と最終レポートを別コメントで続けて投稿します。"
  }
}
```

### Rendered output

````md
## Mutation testing — {{feature_or_pr_title}}

**Status — in progress**

{{summary}}

<details>
<summary>JA</summary>

**ミューテーションテスト — 実行中**

{{ja.summary}}
</details>
````

---

## Mode: `foundation` — Phase 0b foundation work report

Posted when triage classifies coverage as **absent** or **very_low** and the Foundation phase (Phase 0b) runs. Announces that existing tests were too thin to mutation-test meaningfully, and reports what Devin wrote to fix that. Always followed by an `initial` comment after Phase 6.

### Payload extras

```json
{
  "mode": "foundation",
  "summary": "Existing tests covered only {{original_line_pct}} of changed-file lines with no coverage of {{N}} critical guarantees. Devin wrote {{tests_added}} foundation tests across {{files_added}} test files, bringing baseline coverage to {{foundation_line_pct}}/{{foundation_branch_pct}} line/branch before any mutations are applied. Initial mutation results will follow.",
  "test_quality": "Foundation tests assert each critical guarantee with a dedicated case and at least one negative case per branch.",
  "progression": {
    "columns": ["Original", "Foundation"],
    "rows": {
      "tests":        ["{{original_tests}}", "{{foundation_tests}}"],
      "line_pct":     ["{{original_line_pct}}",     "{{foundation_line_pct}}"],
      "branch_pct":   ["{{original_branch_pct}}",   "{{foundation_branch_pct}}"],
      "kill_rate":    ["N/A",                       "N/A"],
      "survived":     ["N/A",                       "N/A"]
    }
  },
  "foundation_tests": [
    {
      "file": "tests/.../test_foo.py",
      "added": 12,
      "covers": "X critical guarantees: A, B, C",
      "ja": {"file": "...", "added": 12, "covers": "..."}
    }
  ],
  "notes": [
    "Foundation phase was triggered by triage coverage of {{original_line_pct}} on changed files.",
    "Foundation tests commit: {{foundation_commit_sha}}."
  ],
  "ja": {
    "summary": "...",
    "test_quality": "...",
    "notes": ["...", "..."]
  }
}
```

### Rendered output

````md
## Mutation testing — {{feature_or_pr_title}}

**Foundation — test coverage uplift**

{{summary}}

### Progression

| Metric        | Original                | Foundation                |
|---------------|-------------------------|---------------------------|
| Tests         | {{original_tests}}      | {{foundation_tests}}      |
| Line coverage | `{{original_line_pct}}` | `{{foundation_line_pct}}` |
| Branch cov.   | `{{original_branch_pct}}` | `{{foundation_branch_pct}}` |
| Kill rate     | `N/A`                   | `N/A`                     |
| Survived      | `N/A`                   | `N/A`                     |

Kill rate is `N/A` at this stage — no mutations have been applied yet. Kill rate is reported in the next comment after the initial mutation pass.

<details>
<summary>Foundation tests added</summary>

| File | Tests added | Covers |
|------|---:|---|
| {{foundation_tests[i].file}} | {{foundation_tests[i].added}} | {{foundation_tests[i].covers}} |
</details>

<details>
<summary>Notes</summary>

- {{notes[i]}}
- Log: `{{log_path}}`
</details>

<details>
<summary>JA</summary>

**基盤 — テストカバレッジの底上げ**

{{ja.summary}}

### 進捗

| 指標 | 当初 | 基盤後 |
|---|---|---|
| テスト | {{original_tests}} | {{foundation_tests}} |
| 行カバレッジ | `{{original_line_pct}}` | `{{foundation_line_pct}}` |
| ブランチ | `{{original_branch_pct}}` | `{{foundation_branch_pct}}` |
| キル率 | `N/A` | `N/A` |
| 生存 | `N/A` | `N/A` |

ミューテーション未実行のためキル率は `N/A` です。次コメントで初期ミューテーション結果を報告します。

<details>
<summary>追加した基盤テスト</summary>

| ファイル | 追加テスト数 | カバー対象 |
|---|---:|---|
| {{ja.foundation_tests[i].file}} | {{ja.foundation_tests[i].added}} | {{ja.foundation_tests[i].covers}} |
</details>

補足:

- {{ja.notes[i]}}
- ログ: `{{log_path}}`
</details>
````

---

## Mode: `initial` — Phase 7 initial mutation results checkpoint

Posted immediately after the initial mutation pass (Phase 6). Lists every mutation that did not get killed, classified as either **pending fix** (Devin will add a test in Improve) or **`≡` dismissed** (functionally equivalent / no test could distinguish — explained in the row's reason).

The progression table has **three columns** (Original / Foundation / Initial-mutation) when Phase 0b ran, or **two columns** (Original / Initial-mutation) when it did not. **Never duplicate columns just to fill the table.** Cells that have no measurement are rendered as `N/A`.

### Payload extras

```json
{
  "mode": "initial",
  "foundation_was_run": true,
  "summary": "Initial mutation pass killed {{killed}}/{{total}} mutations ({{kill_rate}}). Remaining survivors are classified below — Devin will add tests for the {{pending_count}} pending items and dismiss the {{dismissed_count}} equivalent mutation(s).",
  "test_quality": "Mutation set spans {{n}} failure areas; gap/strength split is {{gap_count}}/{{total}}.",
  "progression": {
    "columns": ["Original", "Foundation", "Initial mutation"],
    "rows": {
      "tests":      ["{{original_tests}}", "{{foundation_tests}}", "{{initial_tests}}"],
      "line_pct":   ["{{original_line_pct}}", "{{foundation_line_pct}}", "{{initial_line_pct}}"],
      "branch_pct": ["{{original_branch_pct}}", "{{foundation_branch_pct}}", "{{initial_branch_pct}}"],
      "kill_rate":  ["N/A", "N/A", "{{initial_kill_rate}}"],
      "survived":   ["N/A", "N/A", "{{initial_survived}}"]
    }
  },
  "survivors": [
    {
      "id": "M2",
      "name": "Substring match replaces equality on adhoc subject lookup",
      "classification": "pending",
      "gap": "...",
      "mutation": "...",
      "risk": "...",
      "planned_test": "Assert exact-equality semantics with overlapping-substring inputs.",
      "ja": {
        "name": "...", "gap": "...", "mutation": "...", "risk": "...",
        "planned_test": "..."
      }
    },
    {
      "id": "M10",
      "name": "Pydantic str-Enum coercion preserves serialized JSON",
      "classification": "dismissed",
      "gap": "...",
      "mutation": "...",
      "risk": "None — the mutation produces byte-identical JSON output.",
      "dismissal_reason": "Pydantic v2 serializes both the str-Enum member and its `.value` to the same JSON string; no observable behavior differs. Verified empirically with model_dump_json() round-trip.",
      "ja": {
        "name": "...", "gap": "...", "mutation": "...", "risk": "...",
        "dismissal_reason": "..."
      }
    }
  ],
  "caught": [
    {"id": "M1", "name": "...", "caught_by": "test_..."}
    // omit ja inside caught entries on initial mode (collapsed accordion only shows names)
  ],
  "notes": [
    "Initial coverage and kill rate measured against the foundation tests committed in {{foundation_commit_sha}}."
  ],
  "ja": { "summary": "...", "test_quality": "...", "notes": ["..."] }
}
```

### Rendered output

````md
## Mutation testing — {{feature_or_pr_title}}

**Initial mutation results — checkpoint**

`{{total}}` mutations · `{{killed}}` caught · `{{survived}}` survived · kill rate `{{initial_kill_rate}}`

{{summary}}

### Progression

| Metric        | Original | Foundation | Initial mutation |
|---------------|----------|------------|------------------|
| Tests         | {{...}}  | {{...}}    | {{...}}          |
| Line coverage | `{{...}}` | `{{...}}` | `{{...}}`        |
| Branch cov.   | `{{...}}` | `{{...}}` | `{{...}}`        |
| Kill rate     | `N/A`    | `N/A`      | `{{initial_kill_rate}}` ({{killed}}/{{total}}) |
| Survived      | `N/A`    | `N/A`      | {{initial_survived}} |

### Survivors — to be resolved in final report

<!--
  REQUIRED INVARIANT: every survivor here must carry a `classification` of either
  `pending` (Devin will write a test in Improve) or `dismissed` (functionally
  equivalent — explained in the row's reason). Anything else is rejected by the
  renderer.
-->

<details>
<summary>{{id}} — {{name}} <code>pending</code></summary>

| Finding | Details |
|---|---|
| Gap | {{gap}} |
| Mutation | {{mutation}} |
| Risk | {{risk}} |
| Planned test | {{planned_test}} |
</details>

<details>
<summary>{{id}} — {{name}} <code>≡ dismissed</code></summary>

| Finding | Details |
|---|---|
| Gap | {{gap}} |
| Mutation | {{mutation}} |
| Risk | {{risk}} |
| Dismissal reason | {{dismissal_reason}} |
</details>

<details>
<summary>✓ {{caught.length}} mutations caught</summary>

- `{{id}}` — {{name}} (caught by {{caught_by}})
</details>

<details>
<summary>Notes</summary>

- {{notes[i]}}
- Log: `{{log_path}}`
</details>

<details>
<summary>JA</summary>

**初期ミューテーション結果 — チェックポイント**

… full Japanese mirror of every section above, including the progression table, every survivor's classification, the caught accordion, and the notes …
</details>
````

---

## Mode: `final` — Phase 12 final report

Posted after Improve (Phase 8) and Verify (Phase 9) complete. **Invariant: every mutation that survived the initial pass MUST appear here as either `✓ killed` (a new test now catches it) or `≡ dismissed` (functionally equivalent — explained).** The renderer **rejects** a `final` payload that still contains `pending` survivors.

The progression table has **four columns** when Phase 0b ran (Original / Foundation / Initial mutation / Final) or **three columns** when it did not (Original / Initial mutation / Final). Kill rate in the Final column uses the formula `killed / (total − dismissed)` so the rate is not penalised for mutations that cannot be killed by definition.

### Payload extras

```json
{
  "mode": "final",
  "foundation_was_run": true,
  "summary": "Final kill rate {{final_kill_rate}} ({{final_killed}}/{{total − dismissed}}). All {{initial_survived}} initial survivors are resolved: {{newly_killed}} now killed by added tests, {{dismissed}} dismissed as equivalent with documented reasons. No `❌` remains.",
  "test_quality": "Improvements add {{tests_added_in_improve}} targeted tests; suite stays green; coverage holds at {{final_line_pct}}/{{final_branch_pct}}.",
  "progression": {
    "columns": ["Original", "Foundation", "Initial mutation", "Final"],
    "rows": {
      "tests":      ["{{...}}", "{{...}}", "{{...}}", "{{...}}"],
      "line_pct":   ["{{...}}", "{{...}}", "{{...}}", "{{...}}"],
      "branch_pct": ["{{...}}", "{{...}}", "{{...}}", "{{...}}"],
      "kill_rate":  ["N/A",     "N/A",     "{{initial_kill_rate}}", "{{final_kill_rate}}"],
      "survived":   ["N/A",     "N/A",     "{{initial_survived}}",  "0 ({{dismissed_count}} dismissed)"]
    }
  },
  "resolved": [
    {
      "id": "M2",
      "name": "Substring match replaces equality on adhoc subject lookup",
      "resolution": "killed",
      "added_test": "test_get_chart_info_adhoc_subject_exact_equality",
      "explanation": "...",
      "ja": {"name": "...", "added_test": "...", "explanation": "..."}
    },
    {
      "id": "M10",
      "name": "Pydantic str-Enum coercion preserves serialized JSON",
      "resolution": "dismissed",
      "dismissal_reason": "...",
      "explanation": "...",
      "ja": {"name": "...", "dismissal_reason": "...", "explanation": "..."}
    }
  ],
  "caught_originally": [
    {"id": "M1", "name": "...", "caught_by": "...",
     "ja": {"name": "...", "caught_by": "..."}}
  ],
  "changes": [
    {"area": "...", "change": "...", "result": "...",
     "ja": {"area": "...", "change": "...", "result": "..."}}
  ],
  "gaps": [
    {"area": "...", "test": "...", "reason": "...",
     "ja": {"area": "...", "test": "...", "reason": "..."}}
  ],
  "notes": ["..."],
  "ja": { "summary": "...", "test_quality": "...", "notes": ["..."] }
}
```

### Rendered output

````md
## Mutation testing — {{feature_or_pr_title}}

**Final report**

`{{total}}` mutations · `{{final_killed}}` killed · `{{dismissed_count}}` dismissed · `0` remaining · final kill rate `{{final_kill_rate}}`  
Tests: `{{initial_tests}}`→`{{final_tests}}` · Target: {{targeted_suite_description}}

{{summary}}

### Resolved

<!--
  REQUIRED INVARIANT: every survivor from the `initial` comment appears here
  as `✓ killed` or `≡ dismissed`. The renderer rejects payloads that still
  carry `pending` items in `final` mode.
-->

<details>
<summary>✓ {{id}} — {{name}}</summary>

{{explanation}}

Caught by: `{{added_test}}`.
</details>

<details>
<summary>≡ {{id}} — {{name}} (dismissed as equivalent)</summary>

{{explanation}}

Dismissal reason: {{dismissal_reason}}.
</details>

### Progression

| Metric | Original | Foundation | Initial mutation | Final |
|---|---|---|---|---|
| Tests | {{...}} | {{...}} | {{...}} | {{...}} |
| Line coverage | `{{...}}` | `{{...}}` | `{{...}}` | `{{...}}` |
| Branch coverage | `{{...}}` | `{{...}}` | `{{...}}` | `{{...}}` |
| Kill rate | `N/A` | `N/A` | `{{initial_kill_rate}}` ({{initial_killed}}/{{total}}) | `{{final_kill_rate}}` ({{final_killed}}/{{total − dismissed_count}}) |
| Survived | `N/A` | `N/A` | {{initial_survived}} | 0 ({{dismissed_count}} dismissed) |

Final kill rate formula: `killed / (total − dismissed)` — dismissed mutations are excluded from the denominator because they are functionally equivalent and no test can distinguish them from the original code.

<details>
<summary>Changes made</summary>

| Area | Change | Result |
|---|---|---|
| {{changes[i].area}} | {{changes[i].change}} | {{changes[i].result}} |
</details>

<details>
<summary>What's left for high-quality coverage</summary>

| Area | Add | Why |
|---|---|---|
| {{gaps[i].area}} | {{gaps[i].test}} | {{gaps[i].reason}} |

Test quality: {{test_quality}}.
</details>

<details>
<summary>✓ {{total_caught_count}} mutations caught ({{newly_fixed_count}} newly fixed)</summary>

<details>
<summary>✓ {{caught_originally[i].name}}</summary>

Caught by: {{caught_originally[i].caught_by}}.
</details>
</details>

<details>
<summary>Notes</summary>

- {{notes[i]}}
- Log: `{{log_path}}`
</details>

<details>
<summary>JA</summary>

**最終レポート**

… full Japanese mirror of every section above (progression, resolved, changes, what's left, caught, notes) …
</details>
````

---

## Style rules

- **Always visible on every comment:** the header `## Mutation testing — {{title}}`, a one-line mode label (e.g. `**Final report**`), and the JA accordion at the bottom.
- **Always collapsed (`<details>`):** changes made, what's left, caught mutations, notes, JA.
- **Default visible content is English.** All Japanese content goes inside the bottom `<details><summary>JA</summary>…</details>` accordion. Never inline Japanese alongside English in the visible body.
- **Survivor classification is mandatory.** In `initial` mode, every survivor row carries exactly one of `classification: pending | dismissed` in its payload, rendered as the inline code badge `pending` or `≡ dismissed`. In `final` mode, every entry in `resolved[]` carries `resolution: killed | dismissed`. Anything else is a renderer error.
- **No `❌` in the `final` comment.** The `final` comment never renders a "Remaining uncaught" section. The invariant is "every initial survivor is killed or dismissed."
- **N/A for unmeasured cells.** Progression table cells that have no measurement at the comment's stage (e.g. kill rate before mutations have run) **MUST** be `N/A`. Duplicating a column to fill the table is forbidden.
- **GitHub-native markdown only:** tables, `<details><summary>` accordions, inline code. No screenshots, no external assets, no HTML beyond `<details>`/`<summary>`.
- **One sentence per mutation explanation.** Keep the visible body brief and scannable.
- **Mention what Devin fixed.** The `Resolved` section and the `Changes made` accordion together must make it obvious which tests Devin added and why.

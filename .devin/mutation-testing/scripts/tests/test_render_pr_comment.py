# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
"""
Tests for render_pr_comment.py — Stage 3 PR-comment renderer.

The renderer's contract is mandated by `template_03_final_report.md`. Each test
locks down one structural rule from that template so a regression that drops
or renames a section is caught.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

import render_pr_comment  # type: ignore[import-not-found]  # loaded via conftest


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _payload(**overrides) -> dict:
    """Return a structurally valid final-mode results payload."""
    base = {
        "feature_or_pr_title": "Example feature",
        "targeted_suite_description": "tests/x",
        "mode": "final",
        "log_path": ".devin/mutation-testing/pr-42-2026-01-02-example.md",
        "initial": {
            "passed_tests": 10,
            "failed_tests": 0,
            "line_pct": 50,
            "branch_pct": 40,
            "killed": 3,
            "survived": 2,
            "total": 5,
        },
        "final": {
            "passed_tests": 15,
            "failed_tests": 0,
            "line_pct": 95,
            "branch_pct": 90,
            "killed": 5,
            "survived": 0,
            "total": 5,
        },
        "surviving": [],
        "caught": [
            {
                "name": "Remove guard X",
                "explanation": "Deleting the guard makes test_a fail.",
                "caught_by": "test_a",
                "newly_fixed": True,
                "ja": {
                    "name": "ガードXを削除",
                    "explanation": "ガードを削除すると test_a が失敗。",
                    "caught_by": "test_a",
                },
            },
        ],
        "changes": [
            {
                "area": "validator",
                "change": "Added test for guard X",
                "result": "kills M1",
                "ja": {
                    "area": "バリデータ",
                    "change": "ガード X のテスト追加",
                    "result": "M1 を撃破",
                },
            },
        ],
        "gaps": [
            {
                "area": "parser",
                "test": "edge-case for empty input",
                "reason": "currently uncovered",
                "ja": {
                    "area": "パーサ",
                    "test": "空入力のエッジケース",
                    "reason": "現状未カバー",
                },
            },
        ],
        "summary": "All gaps fixed.",
        "test_quality": "strong",
        "notes": ["full rerun", "all green"],
        "ja": {
            "summary": "全ギャップ修正済み。",
            "test_quality": "強い",
            "notes": ["完全再実行", "全て緑"],
        },
    }
    for key, value in overrides.items():
        base[key] = value
    return base


# ---------------------------------------------------------------------------
# _kill_rate
# ---------------------------------------------------------------------------


def test_kill_rate_zero_total_returns_zero() -> None:
    assert render_pr_comment._kill_rate(0, 0) == 0


def test_kill_rate_full_returns_one_hundred() -> None:
    assert render_pr_comment._kill_rate(10, 10) == 100


def test_kill_rate_rounds_to_nearest_integer() -> None:
    # 7/3 ≈ 2.33 -> 2 ; 2/3 = 0.666 -> 67
    assert render_pr_comment._kill_rate(2, 3) == 67


# ---------------------------------------------------------------------------
# _validate
# ---------------------------------------------------------------------------


def test_validate_accepts_valid_final_payload() -> None:
    initial, final, mode = render_pr_comment._validate(_payload())
    assert mode == "final"
    assert initial["passed_tests"] == 10
    assert final["passed_tests"] == 15


def test_validate_rejects_unknown_mode() -> None:
    with pytest.raises(ValueError, match="mode must be"):
        render_pr_comment._validate(_payload(mode="bogus"))


def test_validate_rejects_missing_initial() -> None:
    payload = _payload()
    del payload["initial"]
    with pytest.raises(ValueError, match="initial"):
        render_pr_comment._validate(payload)


def test_validate_rejects_initial_missing_key() -> None:
    payload = _payload()
    del payload["initial"]["killed"]
    with pytest.raises(ValueError, match="missing keys"):
        render_pr_comment._validate(payload)


def test_validate_rejects_final_missing_when_mode_final() -> None:
    payload = _payload()
    del payload["final"]
    with pytest.raises(ValueError, match="'final' section required"):
        render_pr_comment._validate(payload)


def test_validate_rejects_final_missing_key_when_mode_final() -> None:
    payload = _payload()
    del payload["final"]["survived"]
    with pytest.raises(ValueError, match="'final' missing keys"):
        render_pr_comment._validate(payload)


def test_validate_mirrors_initial_into_final_in_checkpoint_mode() -> None:
    payload = _payload(mode="checkpoint")
    del payload["final"]
    initial, final, mode = render_pr_comment._validate(payload)
    assert mode == "checkpoint"
    # final must be a fresh dict equal to initial, not the same object.
    assert final == initial
    assert final is not initial


# ---------------------------------------------------------------------------
# Header / coverage table content
# ---------------------------------------------------------------------------


def test_header_includes_arrow_summary_stats() -> None:
    out = render_pr_comment.render(_payload())
    # `5` mutations · `3`→`5` caught · `2`→`0` survived · kill rate `60%`→`100%`
    assert "`5` mutations" in out
    assert "`3`→`5` caught" in out
    assert "`2`→`0` survived" in out
    assert "kill rate `60%`→`100%`" in out


def test_header_uses_initial_test_pass_count_first() -> None:
    out = render_pr_comment.render(_payload())
    assert "Tests: `10 passed`→`15 passed`" in out


def test_coverage_table_uses_initial_and_final_columns() -> None:
    out = render_pr_comment.render(_payload())
    assert "| Metric | Initial | Final |" in out
    assert "| Line coverage | `50%` | `95%` |" in out
    assert "| Branch coverage | `40%` | `90%` |" in out
    assert "| Kill rate | `60%` (3/5) | `100%` (5/5) |" in out


# ---------------------------------------------------------------------------
# Surviving / caught rendering
# ---------------------------------------------------------------------------


def test_no_surviving_renders_html_comment() -> None:
    out = render_pr_comment.render(_payload())
    assert "<!-- No surviving mutations remained after targeted fixes. -->" in out


def test_no_surviving_japanese_message_present() -> None:
    out = render_pr_comment.render(_payload())
    assert "修正後に生存ミューテーションなし。" in out


def test_surviving_mutation_renders_en_table_with_finding_columns() -> None:
    payload = _payload()
    payload["surviving"] = [
        {
            "name": "Skip render",
            "gap": "Pre-render skipped",
            "mutation": "remove call",
            "risk": "raw template runs",
            "ja": {
                "name": "レンダリングをスキップ",
                "gap": "レンダリングがスキップされる",
                "mutation": "呼び出しを削除",
                "risk": "生のテンプレートが実行される",
            },
        }
    ]
    out = render_pr_comment.render(payload)
    assert "<summary>❌ Skip render</summary>" in out
    assert "| Finding | Details |" in out
    assert "| Gap | Pre-render skipped |" in out
    assert "| Mutation | remove call |" in out
    assert "| Risk | raw template runs |" in out
    # JA table uses 観点/詳細 headings.
    assert "<summary>❌ レンダリングをスキップ</summary>" in out
    assert "| 観点 | 詳細 |" in out
    assert "| ギャップ | レンダリングがスキップされる |" in out


def test_caught_mutation_renders_newly_fixed_suffix_only_in_english() -> None:
    out = render_pr_comment.render(_payload())
    assert "<summary>✓ Remove guard X (newly fixed)</summary>" in out
    # Japanese suffix is the parenthesised CJK marker, not "(newly fixed)".
    assert "<summary>✓ ガードXを削除（新規修正）</summary>" in out
    assert "ガードXを削除 (newly fixed)" not in out


def test_caught_mutation_without_newly_fixed_has_no_suffix() -> None:
    payload = _payload()
    payload["caught"][0]["newly_fixed"] = False
    out = render_pr_comment.render(payload)
    assert "<summary>✓ Remove guard X</summary>" in out
    # The English (newly fixed) suffix only appears next to each mutation name;
    # the parent accordion still says "N newly fixed" but with a count of 0.
    assert "Remove guard X (newly fixed)" not in out
    assert "（新規修正）" not in out


def test_caught_summary_header_counts_newly_fixed() -> None:
    payload = _payload()
    payload["caught"].append(
        {
            "name": "Old kill",
            "explanation": "always caught",
            "caught_by": "test_b",
            "newly_fixed": False,
            "ja": {
                "name": "古い検出",
                "explanation": "常に検出",
                "caught_by": "test_b",
            },
        }
    )
    out = render_pr_comment.render(payload)
    # 5 caught, 1 newly fixed.
    assert "<summary>✓ 5 mutations caught (1 newly fixed)</summary>" in out


def test_caught_by_label_swaps_to_japanese_in_ja_block() -> None:
    out = render_pr_comment.render(_payload())
    assert "Caught by: test_a." in out
    # Japanese block uses the localized label.
    assert "検出テスト: test_a." in out


# ---------------------------------------------------------------------------
# Table rendering for changes / gaps
# ---------------------------------------------------------------------------


def test_changes_table_has_three_column_header() -> None:
    out = render_pr_comment.render(_payload())
    assert "| Area | Change | Result |" in out
    assert "| validator | Added test for guard X | kills M1 |" in out


def test_gaps_table_has_three_column_header() -> None:
    out = render_pr_comment.render(_payload())
    assert "| Area | Add | Why |" in out
    assert (
        "| parser | edge-case for empty input | currently uncovered |" in out
    )


def test_empty_table_renders_header_only() -> None:
    payload = _payload(changes=[], gaps=[])
    out = render_pr_comment.render(payload)
    # Header + separator still present even with no rows.
    assert "| Area | Change | Result |\n|---|---|---|\n</details>" in out
    assert "| Area | Add | Why |\n|---|---|---|" in out


# ---------------------------------------------------------------------------
# Notes / JA block / log_path
# ---------------------------------------------------------------------------


def test_log_path_appears_in_english_notes() -> None:
    out = render_pr_comment.render(_payload())
    assert (
        "- Log: `.devin/mutation-testing/pr-42-2026-01-02-example.md`"
        in out
    )


def test_log_path_appears_in_japanese_notes() -> None:
    out = render_pr_comment.render(_payload())
    assert (
        "- ログ: `.devin/mutation-testing/pr-42-2026-01-02-example.md`"
        in out
    )


def test_each_note_renders_as_bullet() -> None:
    out = render_pr_comment.render(_payload())
    assert "- full rerun" in out
    assert "- all green" in out
    assert "- 完全再実行" in out
    assert "- 全て緑" in out


def test_ja_block_contains_summary_and_test_quality() -> None:
    out = render_pr_comment.render(_payload())
    assert "全ギャップ修正済み。" in out
    assert "テスト品質: 強い" in out


def test_ja_summary_table_has_six_columns() -> None:
    out = render_pr_comment.render(_payload())
    assert "| 状態 | テスト | 行 | ブランチ | kill rate | 生存 |" in out
    assert "| 初期 | 10 | `50%` | `40%` | `60%` | 2 |" in out
    assert "| 最終 | 15 | `95%` | `90%` | `100%` | 0 |" in out


# ---------------------------------------------------------------------------
# main() entry point
# ---------------------------------------------------------------------------


def test_main_writes_output_to_file(tmp_path: Path) -> None:
    results_path = tmp_path / "results.json"
    out_path = tmp_path / "comment.md"
    results_path.write_text(json.dumps(_payload()))
    rc = render_pr_comment.main([str(results_path), "--out", str(out_path)])
    assert rc == 0
    text = out_path.read_text()
    assert "Mutation testing — Example feature" in text


def test_main_returns_two_on_invalid_payload(tmp_path: Path) -> None:
    results_path = tmp_path / "results.json"
    payload = _payload()
    del payload["initial"]
    results_path.write_text(json.dumps(payload))
    rc = render_pr_comment.main([str(results_path)])
    assert rc == 2


def test_render_does_not_mutate_input_payload() -> None:
    payload = _payload()
    snapshot = copy.deepcopy(payload)
    render_pr_comment.render(payload)
    assert payload == snapshot


# ---------------------------------------------------------------------------
# Coverage-gap and defense-in-depth tests added after initial mutation run
# ---------------------------------------------------------------------------


def test_render_with_empty_caught_renders_zero_count_header() -> None:
    """L134: when `caught` is empty and `final.killed=0` the accordion shows 0/0."""
    payload = _payload(caught=[])
    payload["final"]["killed"] = 0
    out = render_pr_comment.render(payload)
    assert "<summary>✓ 0 mutations caught (0 newly fixed)</summary>" in out
    # Japanese accordion also still rendered with the same zero count.
    assert "<summary>✓ 0 検出済みミューテーション</summary>" in out
    # Body of the EN caught accordion is empty (just a trailing newline)
    en_idx = out.find("✓ 0 mutations caught")
    en_close = out.index("</details>", en_idx + 1)
    inner = out[en_idx:en_close]
    assert "<details>" not in inner[len("✓ 0 mutations caught (0 newly fixed)</summary>\n\n"):]


def test_render_skips_caught_entry_missing_ja_block() -> None:
    """L139: caught entries without a `ja` block are silently skipped in JA."""
    payload = _payload()
    payload["caught"].append(
        {
            "name": "EnglishOnlyCaught",
            "explanation": "no ja block",
            "caught_by": "test_z",
            "newly_fixed": False,
            # intentionally no "ja" key
        }
    )
    out = render_pr_comment.render(payload)
    # English block sees both entries.
    assert "EnglishOnlyCaught" in out
    # The JA accordion starts at `<summary>JA</summary>`.
    ja_idx = out.find("<summary>JA</summary>")
    assert ja_idx > 0
    # The English-only entry must not leak into the JA portion of the output.
    assert "EnglishOnlyCaught" not in out[ja_idx:]


def test_render_skips_surviving_entry_missing_ja_block() -> None:
    """L167: surviving entries without a `ja` block are silently skipped in JA."""
    payload = _payload()
    payload["surviving"] = [
        {
            "name": "EnglishOnlySurvivor",
            "gap": "g",
            "mutation": "m",
            "risk": "r",
            # intentionally no "ja" key
        }
    ]
    out = render_pr_comment.render(payload)
    # English accordion sees the entry.
    assert "❌ EnglishOnlySurvivor" in out
    # Japanese accordion does NOT leak the English name.
    ja_idx = out.find("<summary>JA</summary>")
    assert ja_idx > 0
    assert "EnglishOnlySurvivor" not in out[ja_idx:]


def test_caught_summary_header_uses_final_killed_count() -> None:
    """Defense-in-depth: lock down that the EN/JA caught header uses final.killed."""
    payload = _payload()
    payload["final"]["killed"] = 7
    out = render_pr_comment.render(payload)
    # Counts come from final.killed and the newly_fixed entries in `caught`.
    assert "<summary>✓ 7 mutations caught (1 newly fixed)</summary>" in out
    assert "<summary>✓ 7 検出済みミューテーション</summary>" in out

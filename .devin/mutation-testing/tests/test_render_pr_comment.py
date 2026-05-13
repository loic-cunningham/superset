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
"""Tests for ``.devin/mutation-testing/scripts/render_pr_comment.py``.

These exercise the pure rendering helpers (``_kill_rate``,
``_render_surviving_block``, ``_render_caught_block``, ``_render_table``),
the JSON payload validator ``_validate``, and the end-to-end ``render``
output that drives the Stage 3 PR comment template.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest


def _state(**overrides: Any) -> dict:
    base = {
        "passed_tests": 10,
        "failed_tests": 0,
        "line_pct": 90,
        "branch_pct": 80,
        "killed": 5,
        "survived": 1,
        "total": 6,
    }
    base.update(overrides)
    return base


def _payload(**overrides: Any) -> dict:
    base: dict[str, Any] = {
        "feature_or_pr_title": "Demo PR",
        "targeted_suite_description": ".devin/mutation-testing/tests/",
        "mode": "final",
        "log_path": ".devin/mutation-testing/pr-28-2026-05-13-demo.md",
        "initial": _state(killed=4, survived=2, total=6),
        "final": _state(killed=6, survived=0, total=6),
        "surviving": [],
        "caught": [
            {
                "name": "Caught mutation",
                "explanation": "stops bad behavior",
                "caught_by": "tests/foo.py::test_bar",
                "newly_fixed": True,
                "ja": {
                    "name": "捕捉した変異",
                    "explanation": "悪い挙動を止める",
                    "caught_by": "tests/foo.py::test_bar",
                },
            }
        ],
        "changes": [
            {
                "area": "Tests",
                "change": "Added foo",
                "result": "Now caught",
                "ja": {"area": "テスト", "change": "fooを追加", "result": "検出済み"},
            }
        ],
        "gaps": [
            {
                "area": "Edge case",
                "test": "Assert on empty input",
                "reason": "Implicit contract",
                "ja": {
                    "area": "エッジケース",
                    "test": "空入力を検証",
                    "reason": "暗黙の契約",
                },
            }
        ],
        "summary": "Improved coverage",
        "test_quality": "strong",
        "notes": ["Targeted run", "8 mutations sampled"],
        "ja": {
            "summary": "カバレッジを改善",
            "test_quality": "強い",
            "notes": ["対象実行", "8 個のミューテーション"],
        },
    }
    base.update(overrides)
    return base


@pytest.mark.parametrize(
    "killed,total,expected",
    [
        (0, 0, 0),
        (3, 4, 75),
        (1, 3, 33),
        (5, 5, 100),
    ],
)
def test_kill_rate_handles_zero_division_and_rounding(
    render_pr_comment_module: ModuleType,
    killed: int,
    total: int,
    expected: int,
) -> None:
    assert render_pr_comment_module._kill_rate(killed, total) == expected


def test_validate_rejects_unknown_mode(render_pr_comment_module: ModuleType) -> None:
    payload = _payload(mode="draft")
    with pytest.raises(ValueError, match="mode must be"):
        render_pr_comment_module._validate(payload)


def test_validate_requires_initial(render_pr_comment_module: ModuleType) -> None:
    payload = _payload()
    del payload["initial"]
    with pytest.raises(ValueError, match="missing or non-dict 'initial'"):
        render_pr_comment_module._validate(payload)


def test_validate_reports_missing_initial_keys(
    render_pr_comment_module: ModuleType,
) -> None:
    payload = _payload(initial={"passed_tests": 1})
    with pytest.raises(ValueError, match="'initial' missing keys"):
        render_pr_comment_module._validate(payload)


def test_validate_requires_final_in_final_mode(
    render_pr_comment_module: ModuleType,
) -> None:
    payload = _payload()
    del payload["final"]
    with pytest.raises(ValueError, match="'final' section required when mode='final'"):
        render_pr_comment_module._validate(payload)


def test_validate_reports_missing_final_keys(
    render_pr_comment_module: ModuleType,
) -> None:
    payload = _payload(final={"passed_tests": 1, "failed_tests": 0})
    with pytest.raises(ValueError, match="'final' missing keys"):
        render_pr_comment_module._validate(payload)


def test_validate_checkpoint_mode_mirrors_initial_into_final(
    render_pr_comment_module: ModuleType,
) -> None:
    payload = _payload(mode="checkpoint")
    payload.pop("final", None)
    initial, final, mode = render_pr_comment_module._validate(payload)
    assert mode == "checkpoint"
    assert initial == final
    # Validator must return a copy, not the same dict instance, so callers
    # cannot accidentally mutate `initial` through `final`.
    final["passed_tests"] = 999
    assert initial["passed_tests"] != 999


def test_render_surviving_block_empty_returns_template_comment(
    render_pr_comment_module: ModuleType,
) -> None:
    out = render_pr_comment_module._render_surviving_block([])
    assert "No surviving mutations remained after targeted fixes" in out


def test_render_surviving_block_empty_japanese(
    render_pr_comment_module: ModuleType,
) -> None:
    out = render_pr_comment_module._render_surviving_block([], japanese=True)
    assert out == "修正後に生存ミューテーションなし。"


def test_render_surviving_block_renders_each_mutation(
    render_pr_comment_module: ModuleType,
) -> None:
    surviving = [
        {
            "name": "Skip escaping",
            "gap": "no test on escaping",
            "mutation": "Removed escape()",
            "risk": "SQL injection",
            "ja": {
                "name": "エスケープを省略",
                "gap": "エスケープの検証なし",
                "mutation": "escape() を削除",
                "risk": "SQL インジェクション",
            },
        }
    ]
    out = render_pr_comment_module._render_surviving_block(surviving)
    assert "❌ Skip escaping" in out
    assert "| Gap | no test on escaping |" in out
    assert "| Mutation | Removed escape() |" in out
    assert "| Risk | SQL injection |" in out

    ja = render_pr_comment_module._render_surviving_block(surviving, japanese=True)
    assert "❌ エスケープを省略" in ja
    assert "| ギャップ | エスケープの検証なし |" in ja
    assert "| 変異内容 | escape() を削除 |" in ja
    assert "| リスク | SQL インジェクション |" in ja


def test_render_caught_block_empty_returns_empty_string(
    render_pr_comment_module: ModuleType,
) -> None:
    assert render_pr_comment_module._render_caught_block([]) == ""


def test_render_caught_block_marks_newly_fixed_in_english(
    render_pr_comment_module: ModuleType,
) -> None:
    out = render_pr_comment_module._render_caught_block(
        [
            {
                "name": "Fixed mutation",
                "explanation": "kept the guard",
                "caught_by": "tests/foo.py::test_guard",
                "newly_fixed": True,
                "ja": {
                    "name": "修正済み変異",
                    "explanation": "ガードを維持",
                    "caught_by": "tests/foo.py::test_guard",
                },
            }
        ]
    )
    assert "✓ Fixed mutation (newly fixed)" in out
    assert "Caught by: tests/foo.py::test_guard." in out


def test_render_caught_block_does_not_mark_newly_fixed_in_japanese(
    render_pr_comment_module: ModuleType,
) -> None:
    out = render_pr_comment_module._render_caught_block(
        [
            {
                "name": "x",
                "explanation": "y",
                "caught_by": "z",
                "newly_fixed": True,
                "ja": {
                    "name": "JA",
                    "explanation": "説明",
                    "caught_by": "テスト",
                },
            }
        ],
        japanese=True,
    )
    assert "✓ JA（新規修正）" in out
    assert "検出テスト: テスト." in out
    assert "(newly fixed)" not in out


def test_render_table_renders_header_when_no_rows(
    render_pr_comment_module: ModuleType,
) -> None:
    out = render_pr_comment_module._render_table(
        [],
        headers=("Area", "Change", "Result"),
        keys=("area", "change", "result"),
    )
    assert out.startswith("| Area | Change | Result |")
    assert "|---|---|---|" in out


def test_render_table_falls_back_to_empty_string_for_missing_keys(
    render_pr_comment_module: ModuleType,
) -> None:
    out = render_pr_comment_module._render_table(
        [{"area": "A"}, {"area": "B", "change": "c", "result": "r"}],
        headers=("Area", "Change", "Result"),
        keys=("area", "change", "result"),
    )
    assert "| A |  |  |" in out
    assert "| B | c | r |" in out


def test_render_full_report_includes_all_template_sections(
    render_pr_comment_module: ModuleType,
) -> None:
    out = render_pr_comment_module.render(_payload())
    assert "## Mutation testing — Demo PR" in out
    assert "`6` mutations" in out  # initial total
    assert "`4`→`6` caught" in out
    assert "`2`→`0` survived" in out
    assert "kill rate `67%`→`100%`" in out
    assert "### Remaining uncaught mutations" in out
    assert "No surviving mutations remained after targeted fixes" in out
    assert "### Summary" in out
    assert "### Coverage" in out
    assert "| Tests | 10 passed | 10 passed |" in out
    assert "| Line coverage | `90%` | `90%` |" in out
    assert "| Branch coverage | `80%` | `80%` |" in out
    assert "<summary>Changes made</summary>" in out
    assert "<summary>What's left for high-quality coverage</summary>" in out
    assert "<summary>✓ 6 mutations caught (1 newly fixed)</summary>" in out
    assert "<summary>Notes</summary>" in out
    assert "- Targeted run" in out
    assert "- Log: `.devin/mutation-testing/pr-28-2026-05-13-demo.md`" in out
    assert "<summary>JA</summary>" in out
    assert "カバレッジを改善" in out
    assert "| 初期 | 10 | `90%` | `80%` | `67%` | 2 |" in out
    assert "| 最終 | 10 | `90%` | `80%` | `100%` | 0 |" in out


def test_render_checkpoint_mirrors_initial_to_final_columns(
    render_pr_comment_module: ModuleType,
) -> None:
    payload = _payload(mode="checkpoint")
    payload.pop("final", None)
    out = render_pr_comment_module.render(payload)
    # Both columns of every numeric row should reflect the initial state.
    assert "`4`→`4` caught" in out
    assert "`2`→`2` survived" in out
    assert "| Line coverage | `90%` | `90%` |" in out


def test_render_emits_surviving_section_when_present(
    render_pr_comment_module: ModuleType,
) -> None:
    payload = _payload(
        surviving=[
            {
                "name": "skip escaping",
                "gap": "no escape test",
                "mutation": "removed escape",
                "risk": "injection",
                "ja": {
                    "name": "エスケープ省略",
                    "gap": "エスケープ未検証",
                    "mutation": "escape を削除",
                    "risk": "インジェクション",
                },
            }
        ]
    )
    out = render_pr_comment_module.render(payload)
    assert "❌ skip escaping" in out
    assert "No surviving mutations remained" not in out
    # JA accordion also includes the surviving mutation.
    assert "❌ エスケープ省略" in out


def test_main_writes_rendered_file(
    render_pr_comment_module: ModuleType, tmp_path: Path
) -> None:
    payload_path = tmp_path / "results.json"
    out_path = tmp_path / "comment.md"
    payload_path.write_text(json.dumps(_payload()))
    rc = render_pr_comment_module.main([str(payload_path), "--out", str(out_path)])
    assert rc == 0
    body = out_path.read_text()
    assert "## Mutation testing — Demo PR" in body
    assert "<summary>JA</summary>" in body


def test_main_returns_two_when_payload_invalid(
    render_pr_comment_module: ModuleType,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    payload_path = tmp_path / "results.json"
    payload = _payload(mode="bogus")
    payload_path.write_text(json.dumps(payload))
    rc = render_pr_comment_module.main([str(payload_path)])
    assert rc == 2
    captured = capsys.readouterr()
    assert "mode must be" in captured.err

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
"""Foundation tests for ``.devin/mutation-testing/scripts/render_pr_comment.py``.

The renderer is the only sanctioned way to produce mutation-testing PR
comments. These tests pin down its invariants so that future edits cannot
silently drop the JA mirror, accept ``pending`` survivors in a final
comment, render a duplicated-column progression table, or report a
kill rate inconsistent with the bucketed survivors.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Module loading — the renderer lives at a hyphenated path that is not a
# regular Python package, so we load it via importlib.
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[3]
RENDERER_PATH = REPO_ROOT / ".devin/mutation-testing/scripts/render_pr_comment.py"


def _load_renderer():
    spec = importlib.util.spec_from_file_location(
        "render_pr_comment", RENDERER_PATH
    )
    assert spec and spec.loader, f"cannot load renderer at {RENDERER_PATH}"
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("render_pr_comment", module)
    spec.loader.exec_module(module)
    return module


renderer = _load_renderer()
render = renderer.render
RenderError = renderer.RenderError


# ---------------------------------------------------------------------------
# Reusable payload builders.
# ---------------------------------------------------------------------------


def _status_payload(**overrides: Any) -> dict:
    payload: dict = {
        "mode": "status",
        "feature_or_pr_title": "feat(x): demo",
        "summary": "Reviewing the targeted suite.",
        "ja": {"summary": "ターゲットスイートを確認中。"},
    }
    payload.update(overrides)
    return payload


def _progression(columns: list[str], cells_per_row: list[list[str]]) -> dict:
    keys = ("tests", "line_pct", "branch_pct", "kill_rate", "survived")
    rows = dict(zip(keys, cells_per_row))
    return {"columns": columns, "rows": rows}


def _foundation_payload(**overrides: Any) -> dict:
    payload: dict = {
        "mode": "foundation",
        "feature_or_pr_title": "feat(x): demo",
        "summary": "Devin wrote 12 foundation tests.",
        "log_path": ".devin/mutation-testing/pr-1.md",
        "progression": _progression(
            ["Original", "Foundation"],
            [
                ["10", "22"],     # tests
                ["29%", "92%"],   # line_pct
                ["10%", "85%"],   # branch_pct
                ["N/A", "N/A"],   # kill_rate
                ["N/A", "N/A"],   # survived
            ],
        ),
        "foundation_tests": [
            {
                "file": "tests/foo_test.py",
                "added": 12,
                "covers": "Guarantee A",
                "ja": {
                    "file": "tests/foo_test.py",
                    "added": 12,
                    "covers": "保証 A",
                },
            }
        ],
        "notes": ["Triage classified coverage as absent."],
        "ja": {
            "summary": "基盤テストを 12 件追加しました。",
            "notes": ["トリアージで未カバーと判定。"],
        },
    }
    payload.update(overrides)
    return payload


def _survivor(
    *,
    sid: str = "M2",
    classification: str = "pending",
    name: str = "Substring match replaces equality",
    extra: dict | None = None,
    extra_ja: dict | None = None,
) -> dict:
    entry: dict = {
        "id": sid,
        "name": name,
        "gap": "Equality not asserted",
        "mutation": "== replaced with substring `in`",
        "risk": "Unrelated values may match",
        "classification": classification,
        "ja": {
            "name": "完全一致が置換された",
            "gap": "等価性が検証されていない",
            "mutation": "`==` を `in` に置換",
            "risk": "無関係値が一致する",
        },
    }
    if classification == "pending":
        entry["planned_test"] = "Assert equality semantics."
        entry["ja"]["planned_test"] = "等価性を検証するテスト。"
    else:
        entry["dismissal_reason"] = "Verified equivalent via round-trip."
        entry["ja"]["dismissal_reason"] = "往復確認で同等と検証済み。"
    if extra:
        entry.update(extra)
    if extra_ja:
        entry["ja"].update(extra_ja)
    return entry


def _initial_payload(
    *, foundation_was_run: bool = True, survivors: list | None = None
) -> dict:
    if foundation_was_run:
        columns = ["Original", "Foundation", "Initial mutation"]
        rows_cells = [
            ["10", "22", "22"],
            ["29%", "92%", "92%"],
            ["10%", "85%", "85%"],
            ["N/A", "N/A", "86%"],
            ["N/A", "N/A", "2"],
        ]
    else:
        columns = ["Original", "Initial mutation"]
        rows_cells = [
            ["22", "22"],
            ["92%", "92%"],
            ["85%", "85%"],
            ["N/A", "86%"],
            ["N/A", "2"],
        ]
    return {
        "mode": "initial",
        "feature_or_pr_title": "feat(x): demo",
        "summary": "Initial pass killed 12/14.",
        "foundation_was_run": foundation_was_run,
        "log_path": ".devin/mutation-testing/pr-1.md",
        "progression": _progression(columns, rows_cells),
        "survivors": survivors if survivors is not None else [_survivor()],
        "caught": [
            {
                "id": "M1",
                "name": "Removed validation guard",
                "caught_by": "test_guard_present",
                "ja": {
                    "name": "ガードを除去",
                    "caught_by": "test_guard_present",
                },
            }
        ],
        "notes": ["Initial coverage measured against foundation tests."],
        "ja": {
            "summary": "初期パスで 12/14 を撃破。",
            "notes": ["基盤テストに対して測定。"],
        },
    }


def _resolved(
    *,
    rid: str = "M2",
    resolution: str = "killed",
    name: str = "Substring match replaces equality",
) -> dict:
    entry: dict = {
        "id": rid,
        "name": name,
        "resolution": resolution,
        "explanation": "New test pins equality semantics.",
        "ja": {
            "name": "完全一致が置換された",
            "explanation": "新規テストで等価性を固定。",
        },
    }
    if resolution == "killed":
        entry["added_test"] = "test_equality_strict"
        entry["ja"]["added_test"] = "test_equality_strict"
    else:
        entry["dismissal_reason"] = "Verified equivalent via round-trip."
        entry["ja"]["dismissal_reason"] = "往復確認で同等と検証済み。"
    return entry


def _final_payload(
    *,
    foundation_was_run: bool = True,
    resolved: list | None = None,
) -> dict:
    if foundation_was_run:
        columns = ["Original", "Foundation", "Initial mutation", "Final"]
        rows_cells = [
            ["10", "22", "22", "23"],
            ["29%", "92%", "92%", "98%"],
            ["10%", "85%", "85%", "92%"],
            ["N/A", "N/A", "86%", "100%"],
            ["N/A", "N/A", "2", "0 (1 dismissed)"],
        ]
    else:
        columns = ["Original", "Initial mutation", "Final"]
        rows_cells = [
            ["22", "22", "23"],
            ["92%", "92%", "98%"],
            ["85%", "85%", "92%"],
            ["N/A", "86%", "100%"],
            ["N/A", "2", "0 (1 dismissed)"],
        ]
    return {
        "mode": "final",
        "feature_or_pr_title": "feat(x): demo",
        "summary": "All initial survivors are resolved.",
        "foundation_was_run": foundation_was_run,
        "log_path": ".devin/mutation-testing/pr-1.md",
        "progression": _progression(columns, rows_cells),
        "resolved": resolved
        if resolved is not None
        else [_resolved(), _resolved(rid="M3", resolution="dismissed")],
        "caught_originally": [
            {
                "id": "M1",
                "name": "Removed validation guard",
                "caught_by": "test_guard_present",
                "ja": {
                    "name": "ガードを除去",
                    "caught_by": "test_guard_present",
                },
            }
        ],
        "changes": [
            {
                "area": "Tests",
                "change": "Added equality test",
                "result": "M2 killed",
                "ja": {
                    "area": "テスト",
                    "change": "等価性テストを追加",
                    "result": "M2 撃破",
                },
            }
        ],
        "gaps": [
            {
                "area": "Edge",
                "test": "Add boundary test",
                "reason": "Untested empty input",
                "ja": {
                    "area": "境界",
                    "test": "境界テストを追加",
                    "reason": "空入力が未検証",
                },
            }
        ],
        "test_quality": "Strong assertions on guarantees.",
        "notes": ["Final rerun was a full mutation pass."],
        "ja": {
            "summary": "初期の生存はすべて解決。",
            "test_quality": "保証に対する強い検証。",
            "notes": ["最終は全件再実行。"],
        },
    }


# ---------------------------------------------------------------------------
# Dispatcher tests
# ---------------------------------------------------------------------------


def test_render_unknown_mode_raises():
    payload = _status_payload(mode="bogus")
    with pytest.raises(RenderError, match="mode"):
        render(payload)


def test_render_missing_mode_raises():
    payload = _status_payload()
    payload.pop("mode")
    with pytest.raises(RenderError, match="mode"):
        render(payload)


# ---------------------------------------------------------------------------
# Mode: status
# ---------------------------------------------------------------------------


def test_status_happy_path_renders_header_and_ja():
    md = render(_status_payload())
    assert "## Mutation testing — feat(x): demo" in md
    assert "**Status — in progress**" in md
    assert "Reviewing the targeted suite." in md
    assert "<details>\n<summary>JA</summary>" in md
    assert "**ミューテーションテスト — 実行中**" in md
    assert "ターゲットスイートを確認中。" in md


def test_status_missing_ja_block_raises():
    payload = _status_payload()
    payload.pop("ja")
    with pytest.raises(RenderError, match="ja"):
        render(payload)


def test_status_empty_ja_block_raises():
    payload = _status_payload(ja={})
    with pytest.raises(RenderError, match="ja"):
        render(payload)


def test_status_missing_ja_summary_raises():
    payload = _status_payload(ja={"other": "x"})
    with pytest.raises(RenderError, match=r"ja.summary"):
        render(payload)


def test_status_missing_summary_raises():
    payload = _status_payload()
    payload.pop("summary")
    with pytest.raises(RenderError, match="summary"):
        render(payload)


def test_status_missing_title_raises():
    payload = _status_payload()
    payload.pop("feature_or_pr_title")
    with pytest.raises(RenderError, match="feature_or_pr_title"):
        render(payload)


# ---------------------------------------------------------------------------
# Mode: foundation
# ---------------------------------------------------------------------------


def test_foundation_happy_path_renders_progression_and_tests_table():
    md = render(_foundation_payload())
    assert "**Foundation — test coverage uplift**" in md
    # English progression table includes Original/Foundation columns.
    assert "| Metric | Original | Foundation |" in md
    # Tests row uses raw value, percentages get backtick wrap.
    assert "| Tests | 10 | 22 |" in md
    assert "| Line coverage | `29%` | `92%` |" in md
    # Foundation tests sub-table.
    assert "| `tests/foo_test.py` | 12 | Guarantee A |" in md
    # JA mirror present.
    assert "**基盤 — テストカバレッジの底上げ**" in md
    assert "| 指標 | 当初 | 基盤後 |" in md
    assert "| 保証 A |" in md
    # Log path appears in notes blocks.
    assert ".devin/mutation-testing/pr-1.md" in md


def test_foundation_rejects_columns_other_than_original_foundation():
    payload = _foundation_payload()
    payload["progression"]["columns"] = ["Original", "Final"]
    with pytest.raises(RenderError, match="progression.columns"):
        render(payload)


def test_foundation_rejects_three_columns():
    payload = _foundation_payload()
    payload["progression"] = _progression(
        ["Original", "Foundation", "Extra"],
        [
            ["10", "22", "22"],
            ["29%", "92%", "92%"],
            ["10%", "85%", "85%"],
            ["N/A", "N/A", "N/A"],
            ["N/A", "N/A", "N/A"],
        ],
    )
    with pytest.raises(RenderError, match="progression.columns"):
        render(payload)


def test_foundation_rejects_progression_row_length_mismatch():
    payload = _foundation_payload()
    # tests row has 1 cell but columns has 2 — should be rejected.
    payload["progression"]["rows"]["tests"] = ["10"]
    with pytest.raises(RenderError, match="tests"):
        render(payload)


def test_foundation_rejects_missing_progression_row_key():
    payload = _foundation_payload()
    del payload["progression"]["rows"]["branch_pct"]
    with pytest.raises(RenderError, match="branch_pct"):
        render(payload)


def test_foundation_rejects_empty_foundation_tests():
    payload = _foundation_payload(foundation_tests=[])
    with pytest.raises(RenderError, match="foundation_tests"):
        render(payload)


def test_foundation_rejects_foundation_tests_entry_missing_field():
    payload = _foundation_payload()
    payload["foundation_tests"] = [
        {
            "file": "x.py",
            "covers": "...",
            # missing `added`
            "ja": {"file": "x.py", "added": 1, "covers": "x"},
        }
    ]
    with pytest.raises(RenderError, match="file.*added.*covers|added"):
        render(payload)


def test_foundation_rejects_foundation_tests_entry_missing_ja_mirror():
    payload = _foundation_payload()
    payload["foundation_tests"] = [
        {"file": "x.py", "added": 1, "covers": "x"}
    ]
    with pytest.raises(RenderError):
        render(payload)


def test_foundation_rejects_missing_ja_block():
    payload = _foundation_payload()
    payload.pop("ja")
    with pytest.raises(RenderError, match="ja"):
        render(payload)


def test_foundation_rejects_missing_ja_summary():
    payload = _foundation_payload()
    payload["ja"] = {"notes": ["only notes"]}
    with pytest.raises(RenderError, match="summary"):
        render(payload)


def test_foundation_renders_when_no_notes_and_no_log_path():
    payload = _foundation_payload()
    payload.pop("notes", None)
    payload["log_path"] = ""
    payload["ja"].pop("notes", None)
    md = render(payload)
    # Should still render notes accordion without crashing.
    assert "Foundation tests added" in md


# ---------------------------------------------------------------------------
# Mode: initial — survivor classification
# ---------------------------------------------------------------------------


def test_initial_happy_path_with_foundation_columns():
    md = render(_initial_payload(foundation_was_run=True))
    assert "**Initial mutation results — checkpoint**" in md
    assert "| Metric | Original | Foundation | Initial mutation |" in md
    # Kill rate top header is derived from the last column of kill_rate row.
    assert "Kill rate `86%`" in md
    # Pending survivor renders with `pending` badge.
    assert "<code>pending</code>" in md
    assert "Planned test" in md
    assert "Caught by" not in md  # caught uses lowercase 'caught by' label
    assert "✓ 1 mutations caught" in md
    # JA accordion present with mirrored badge.
    assert "<code>保留</code>" in md
    assert "予定テスト" in md


def test_initial_happy_path_without_foundation_two_columns():
    md = render(_initial_payload(foundation_was_run=False))
    assert "| Metric | Original | Initial mutation |" in md
    # The 3-column shape must not leak.
    assert "Foundation |" not in md.split("Mutation testing")[1].split(
        "### Survivors"
    )[0]


def test_initial_rejects_three_columns_when_foundation_not_run():
    payload = _initial_payload(foundation_was_run=False)
    payload["progression"] = _progression(
        ["Original", "Foundation", "Initial mutation"],
        [
            ["10", "22", "22"],
            ["29%", "92%", "92%"],
            ["10%", "85%", "85%"],
            ["N/A", "N/A", "86%"],
            ["N/A", "N/A", "2"],
        ],
    )
    with pytest.raises(RenderError, match="progression.columns"):
        render(payload)


def test_initial_rejects_two_columns_when_foundation_run():
    payload = _initial_payload(foundation_was_run=True)
    payload["progression"] = _progression(
        ["Original", "Initial mutation"],
        [
            ["10", "22"],
            ["29%", "92%"],
            ["10%", "85%"],
            ["N/A", "86%"],
            ["N/A", "2"],
        ],
    )
    with pytest.raises(RenderError, match="progression.columns"):
        render(payload)


def test_initial_rejects_survivor_without_classification():
    payload = _initial_payload()
    survivor = _survivor()
    survivor.pop("classification")
    payload["survivors"] = [survivor]
    with pytest.raises(RenderError, match="classification"):
        render(payload)


def test_initial_rejects_survivor_with_invalid_classification():
    payload = _initial_payload()
    payload["survivors"] = [_survivor()]
    payload["survivors"][0]["classification"] = "unknown"
    with pytest.raises(RenderError, match="classification"):
        render(payload)


def test_initial_pending_survivor_requires_planned_test():
    payload = _initial_payload()
    survivor = _survivor(classification="pending")
    survivor.pop("planned_test")
    payload["survivors"] = [survivor]
    with pytest.raises(RenderError, match="planned_test"):
        render(payload)


def test_initial_dismissed_survivor_requires_dismissal_reason():
    payload = _initial_payload()
    survivor = _survivor(classification="dismissed")
    survivor.pop("dismissal_reason")
    payload["survivors"] = [survivor]
    with pytest.raises(RenderError, match="dismissal_reason"):
        render(payload)


def test_initial_survivor_requires_ja_mirror():
    payload = _initial_payload()
    survivor = _survivor()
    survivor.pop("ja")
    payload["survivors"] = [survivor]
    with pytest.raises(RenderError, match="ja"):
        render(payload)


def test_initial_survivor_requires_ja_planned_test_for_pending():
    payload = _initial_payload()
    survivor = _survivor(classification="pending")
    survivor["ja"].pop("planned_test")
    payload["survivors"] = [survivor]
    with pytest.raises(RenderError, match="planned_test"):
        render(payload)


def test_initial_survivor_requires_ja_dismissal_reason_for_dismissed():
    payload = _initial_payload()
    survivor = _survivor(classification="dismissed")
    survivor["ja"].pop("dismissal_reason")
    payload["survivors"] = [survivor]
    with pytest.raises(RenderError, match="dismissal_reason"):
        render(payload)


def test_initial_survivor_requires_ja_required_keys():
    """Each required English field must have a JA mirror counterpart."""
    for missing_key in ("name", "gap", "mutation", "risk"):
        payload = _initial_payload()
        survivor = _survivor()
        survivor["ja"].pop(missing_key)
        payload["survivors"] = [survivor]
        with pytest.raises(RenderError, match=missing_key):
            render(payload)


def test_initial_renders_dismissed_badge_and_reason():
    payload = _initial_payload(
        survivors=[_survivor(sid="M9", classification="dismissed")]
    )
    md = render(payload)
    assert "<code>≡ dismissed</code>" in md
    assert "Dismissal reason" in md
    assert "Verified equivalent via round-trip." in md
    # JA mirror
    assert "<code>≡ 同等のため却下</code>" in md
    assert "却下理由" in md


def test_initial_no_survivors_renders_placeholder():
    payload = _initial_payload(survivors=[])
    md = render(payload)
    assert "_No surviving mutations after the initial pass._" in md
    assert "初期ミューテーション後の生存なし。" in md


def test_initial_rejects_missing_ja_summary():
    payload = _initial_payload()
    payload["ja"] = {"notes": []}
    with pytest.raises(RenderError, match="summary"):
        render(payload)


def test_initial_rejects_missing_ja_block():
    payload = _initial_payload()
    payload.pop("ja")
    with pytest.raises(RenderError, match="ja"):
        render(payload)


def test_initial_renders_caught_block_with_id_and_test():
    md = render(_initial_payload())
    assert "`M1` — Removed validation guard" in md
    assert "caught by" in md
    assert "test_guard_present" in md
    # JA mirror block for caught
    assert "1 件キャッチ済み" in md


def test_initial_caught_empty_renders_placeholder():
    payload = _initial_payload()
    payload["caught"] = []
    md = render(payload)
    assert "_No mutations caught yet._" in md
    assert "キャッチされたミューテーションなし。" in md


def test_initial_rejects_non_list_survivors():
    payload = _initial_payload()
    payload["survivors"] = "not-a-list"
    with pytest.raises(RenderError, match="survivors"):
        render(payload)


def test_initial_targeted_suite_description_appears_when_provided():
    payload = _initial_payload()
    payload["targeted_suite_description"] = "tests/foo_test.py"
    md = render(payload)
    assert "Target: tests/foo_test.py" in md


# ---------------------------------------------------------------------------
# Mode: final — resolution enforcement & kill-rate formula
# ---------------------------------------------------------------------------


def test_final_happy_path_with_foundation_columns():
    md = render(_final_payload(foundation_was_run=True))
    assert "**Final report**" in md
    assert (
        "| Metric | Original | Foundation | Initial mutation | Final |" in md
    )
    # Killed-vs-dismissed bucketing in the header line.
    # total = len(resolved=2) + len(caught_originally=1) = 3
    # killed = newly_killed(1) + caught_originally(1) = 2; dismissed = 1.
    assert "`3` mutations" in md
    assert "`2` killed" in md
    assert "`1` dismissed" in md
    assert "`0` remaining" in md
    # Resolved entries use ✓ and ≡ badges.
    assert "✓ M2" in md
    assert "≡ M3" in md
    assert "(dismissed as equivalent)" in md
    # Final kill rate formula note is rendered.
    assert "Final kill rate formula: `killed / (total − dismissed)`" in md
    # Caught originally accordion present.
    assert "mutations caught" in md
    # JA accordion present.
    assert "**最終レポート**" in md


def test_final_rejects_pending_resolution_inside_resolved_list():
    payload = _final_payload()
    payload["resolved"] = [
        {
            "id": "M2",
            "name": "x",
            "resolution": "pending",
            "explanation": "x",
            "ja": {"name": "x", "explanation": "x"},
        }
    ]
    with pytest.raises(RenderError, match="resolution"):
        render(payload)


def test_final_killed_resolution_requires_added_test():
    payload = _final_payload()
    entry = _resolved()
    entry.pop("added_test")
    payload["resolved"] = [entry]
    with pytest.raises(RenderError, match="added_test"):
        render(payload)


def test_final_killed_resolution_requires_ja_added_test():
    payload = _final_payload()
    entry = _resolved()
    entry["ja"].pop("added_test")
    payload["resolved"] = [entry]
    with pytest.raises(RenderError, match="added_test"):
        render(payload)


def test_final_dismissed_resolution_requires_dismissal_reason():
    payload = _final_payload()
    entry = _resolved(resolution="dismissed")
    entry.pop("dismissal_reason")
    payload["resolved"] = [entry]
    with pytest.raises(RenderError, match="dismissal_reason"):
        render(payload)


def test_final_dismissed_resolution_requires_ja_dismissal_reason():
    payload = _final_payload()
    entry = _resolved(resolution="dismissed")
    entry["ja"].pop("dismissal_reason")
    payload["resolved"] = [entry]
    with pytest.raises(RenderError, match="dismissal_reason"):
        render(payload)


def test_final_resolved_requires_ja_mirror():
    payload = _final_payload()
    entry = _resolved()
    entry.pop("ja")
    payload["resolved"] = [entry]
    with pytest.raises(RenderError, match="ja"):
        render(payload)


def test_final_resolved_ja_requires_name_and_explanation():
    for missing_key in ("name", "explanation"):
        payload = _final_payload()
        entry = _resolved()
        entry["ja"].pop(missing_key)
        payload["resolved"] = [entry]
        with pytest.raises(RenderError, match=missing_key):
            render(payload)


def test_final_resolved_requires_id_name_explanation():
    for missing_key in ("id", "name", "explanation"):
        payload = _final_payload()
        entry = _resolved()
        entry.pop(missing_key)
        payload["resolved"] = [entry]
        with pytest.raises(RenderError, match=missing_key):
            render(payload)


def test_final_rejects_two_columns_when_foundation_run():
    payload = _final_payload(foundation_was_run=True)
    payload["progression"] = _progression(
        ["Original", "Initial mutation", "Final"],
        [
            ["10", "22", "23"],
            ["29%", "92%", "98%"],
            ["10%", "85%", "92%"],
            ["N/A", "86%", "100%"],
            ["N/A", "2", "0 (1 dismissed)"],
        ],
    )
    with pytest.raises(RenderError, match="progression.columns"):
        render(payload)


def test_final_rejects_four_columns_when_foundation_not_run():
    payload = _final_payload(foundation_was_run=False)
    payload["progression"] = _progression(
        ["Original", "Foundation", "Initial mutation", "Final"],
        [
            ["10", "22", "22", "23"],
            ["29%", "92%", "92%", "98%"],
            ["10%", "85%", "85%", "92%"],
            ["N/A", "N/A", "86%", "100%"],
            ["N/A", "N/A", "2", "0 (1 dismissed)"],
        ],
    )
    with pytest.raises(RenderError, match="progression.columns"):
        render(payload)


def test_final_three_column_shape_renders_when_foundation_not_run():
    md = render(_final_payload(foundation_was_run=False))
    assert "| Metric | Original | Initial mutation | Final |" in md


def test_final_no_resolved_renders_placeholder():
    payload = _final_payload(resolved=[])
    md = render(payload)
    assert "_No initial survivors — nothing to resolve._" in md
    assert "初期生存なし — 解決対象はありません。" in md


def test_final_rejects_invalid_resolution_value():
    payload = _final_payload()
    entry = _resolved()
    entry["resolution"] = "bogus"
    payload["resolved"] = [entry]
    with pytest.raises(RenderError, match="resolution"):
        render(payload)


def test_final_rejects_missing_ja_summary():
    payload = _final_payload()
    payload["ja"] = {"notes": []}
    with pytest.raises(RenderError, match="summary"):
        render(payload)


def test_final_renders_caught_originally_with_summary():
    md = render(_final_payload())
    assert "✓ 2 mutations caught (1 newly fixed)" in md
    assert "✓ M1 — Removed validation guard" in md


def test_final_caught_originally_empty_renders_placeholder():
    payload = _final_payload()
    payload["caught_originally"] = []
    md = render(payload)
    assert "_No mutations caught in the initial pass._" in md
    assert "初期キャッチなし。" in md


def test_final_changes_and_gaps_render_tables():
    md = render(_final_payload())
    assert "| Area | Change | Result |" in md
    assert "| Tests | Added equality test | M2 killed |" in md
    assert "| Area | Add | Why |" in md
    assert "| Edge | Add boundary test | Untested empty input |" in md


def test_final_empty_changes_and_gaps_still_render_headers():
    payload = _final_payload()
    payload["changes"] = []
    payload["gaps"] = []
    md = render(payload)
    assert "| Area | Change | Result |" in md
    assert "| Area | Add | Why |" in md


def test_final_kill_rate_cell_drives_header():
    """The header's final kill rate must come from the progression row,
    not from a duplicated source — ensures payload tampering shows up."""
    payload = _final_payload()
    payload["progression"]["rows"]["kill_rate"][-1] = "73%"
    md = render(payload)
    assert "final kill rate `73%`" in md


def test_final_targeted_suite_appears_when_provided():
    payload = _final_payload()
    payload["targeted_suite_description"] = "tests/foo_test.py"
    md = render(payload)
    assert "Target: tests/foo_test.py" in md


# ---------------------------------------------------------------------------
# Internal helpers — guarantees that drive several modes.
# ---------------------------------------------------------------------------


def test_kill_rate_zero_denominator_returns_na():
    assert renderer._kill_rate(0, 0) == "N/A"
    assert renderer._kill_rate(5, 0) == "N/A"


def test_kill_rate_rounds_to_percent():
    assert renderer._kill_rate(1, 2) == "50%"
    assert renderer._kill_rate(2, 3) == "67%"
    assert renderer._kill_rate(0, 4) == "0%"


def test_require_rejects_missing_and_empty():
    with pytest.raises(RenderError, match="missing"):
        renderer._require({}, "key")
    for empty in (None, "", []):
        with pytest.raises(RenderError, match="empty"):
            renderer._require({"k": empty}, "k")


def test_require_ja_rejects_non_dict():
    with pytest.raises(RenderError, match="ja"):
        renderer._require_ja({})
    with pytest.raises(RenderError, match="ja"):
        renderer._require_ja({"ja": "string-not-dict"})
    with pytest.raises(RenderError, match="ja"):
        renderer._require_ja({"ja": {}})


def test_validate_progression_rejects_non_dict():
    with pytest.raises(RenderError, match="progression"):
        renderer._validate_progression("not-a-mapping")


def test_validate_progression_rejects_non_list_columns():
    with pytest.raises(RenderError, match="columns"):
        renderer._validate_progression({"columns": "x", "rows": {}})


def test_validate_progression_rejects_non_dict_rows():
    with pytest.raises(RenderError, match="rows"):
        renderer._validate_progression(
            {"columns": ["A"], "rows": "not-a-mapping"}
        )


def test_foundation_rejects_non_list_foundation_tests():
    payload = _foundation_payload()
    payload["foundation_tests"] = "not-a-list"
    with pytest.raises(RenderError, match="foundation_tests"):
        render(payload)


def test_final_rejects_non_list_resolved():
    payload = _final_payload()
    payload["resolved"] = "not-a-list"
    with pytest.raises(RenderError, match="resolved"):
        render(payload)


def test_initial_survivor_requires_required_english_fields():
    """`id`, `name`, `gap`, `mutation`, `risk` are all required English fields."""
    for missing_key in ("id", "name", "gap", "mutation", "risk"):
        payload = _initial_payload()
        survivor = _survivor()
        survivor.pop(missing_key)
        payload["survivors"] = [survivor]
        with pytest.raises(RenderError, match=missing_key):
            render(payload)


def test_final_no_log_path_skips_log_lines():
    payload = _final_payload()
    payload["log_path"] = ""
    md = render(payload)
    assert "- Log:" not in md
    assert "- ログ:" not in md


def test_initial_no_log_path_skips_log_lines():
    payload = _initial_payload()
    payload["log_path"] = ""
    md = render(payload)
    assert "- Log:" not in md
    assert "- ログ:" not in md


def test_initial_test_quality_renders_accordion_when_provided():
    payload = _initial_payload()
    payload["test_quality"] = "Quality A"
    payload["ja"]["test_quality"] = "品質 A"
    md = render(payload)
    assert "Quality A" in md
    assert "品質 A" in md
    assert "Test quality" in md
    assert "テスト品質" in md


# ---------------------------------------------------------------------------
# CLI main()
# ---------------------------------------------------------------------------


def test_main_writes_out_file_and_returns_zero(tmp_path: Path):
    payload_path = tmp_path / "payload.json"
    out_path = tmp_path / "out.md"
    payload_path.write_text(json.dumps(_status_payload()))
    rc = renderer.main([str(payload_path), "--out", str(out_path)])
    assert rc == 0
    assert "## Mutation testing — feat(x): demo" in out_path.read_text()


def test_main_writes_to_stdout_when_no_out(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    payload_path = tmp_path / "payload.json"
    payload_path.write_text(json.dumps(_status_payload()))
    rc = renderer.main([str(payload_path)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "## Mutation testing — feat(x): demo" in captured.out


def test_main_returns_2_for_invalid_json(tmp_path: Path):
    payload_path = tmp_path / "broken.json"
    payload_path.write_text("{not json")
    rc = renderer.main([str(payload_path)])
    assert rc == 2


def test_main_returns_2_for_missing_file(tmp_path: Path):
    rc = renderer.main([str(tmp_path / "missing.json")])
    assert rc == 2


def test_main_returns_2_for_payload_validation_error(tmp_path: Path):
    payload = _status_payload()
    payload.pop("ja")
    payload_path = tmp_path / "payload.json"
    payload_path.write_text(json.dumps(payload))
    rc = renderer.main([str(payload_path)])
    assert rc == 2


# ---------------------------------------------------------------------------
# Defensive: payload mutation between calls should not leak state.
# ---------------------------------------------------------------------------


def test_render_does_not_mutate_input_payload():
    payload = _initial_payload()
    snapshot = copy.deepcopy(payload)
    render(payload)
    assert payload == snapshot

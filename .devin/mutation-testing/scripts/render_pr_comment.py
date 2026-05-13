#!/usr/bin/env python3
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
render_pr_comment.py — Render a mutation-testing PR comment from structured JSON.

This is the **only sanctioned way** to compose a PR comment for the
mutation-testing workflow. The agent assembles a JSON payload from
``mutation_runner.py``, ``coverage_summary.py``, and its own notes, then
this renderer produces the exact markdown shape mandated by
``template_03_final_report.md``.

Four comment shapes are supported via the ``mode`` field:

* ``status``     — Phase 1 kickoff comment when Foundation is **not** run.
* ``foundation`` — Phase 0b foundation report when Foundation **is** run.
* ``initial``    — Phase 7 initial-mutation-results checkpoint.
* ``final``      — Phase 12 final report.

Invariants enforced (the renderer exits with ``2`` and an explanatory
message on any violation):

* The ``ja`` block is present on every mode — no Japanese-less comments.
* Survivors in ``initial`` mode are classified as ``pending`` or
  ``dismissed`` (with required ``planned_test`` or ``dismissal_reason``).
* Survivors in ``final`` mode are resolved as ``killed`` or ``dismissed``
  — ``pending`` is rejected so no ``❌`` ever leaks into a final comment.
* Progression-table columns match the declared ``columns`` length on every
  row; agents cannot duplicate columns to fake an "Initial=Final" rendering.
* Kill rate is recomputed from the payload — ``killed / (total − dismissed)``
  on Final, ``killed / total`` everywhere else — so the displayed number is
  always consistent with the bucketed survivors.

Usage::

    render_pr_comment.py results.json [--out comment.md]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]

VALID_MODES = {"status", "foundation", "initial", "final"}
SURVIVOR_CLASSIFICATIONS = {"pending", "dismissed"}
RESOLUTION_TYPES = {"killed", "dismissed"}


class RenderError(ValueError):
    """Raised when a payload violates a structural invariant."""


def _require(payload: dict, key: str, *, kind: str = "key") -> Any:
    if key not in payload:
        raise RenderError(f"payload missing required {kind}: {key!r}")
    value = payload[key]
    if value in (None, "", []):
        raise RenderError(f"payload {kind} {key!r} is empty")
    return value


def _require_ja(payload: dict, *, label: str = "payload") -> dict:
    ja = payload.get("ja")
    if not isinstance(ja, dict) or not ja:
        raise RenderError(
            f"{label} missing required `ja` Japanese-mirror block "
            "(every comment must carry a JA mirror; hand-writing comments is "
            "forbidden — see template_03_final_report.md)"
        )
    return ja


def _kill_rate(killed: int, denom: int) -> str:
    if denom <= 0:
        return "N/A"
    return f"{round(killed / denom * 100)}%"


# ---------------------------------------------------------------------------
# Mode: status
# ---------------------------------------------------------------------------


def _render_status(payload: dict) -> str:
    title = _require(payload, "feature_or_pr_title")
    summary = _require(payload, "summary")
    ja = _require_ja(payload, label="status payload")
    if not ja.get("summary"):
        raise RenderError("status payload `ja.summary` is required")

    return (
        f"## Mutation testing — {title}\n\n"
        "**Status — in progress**\n\n"
        f"{summary}\n\n"
        "<details>\n<summary>JA</summary>\n\n"
        "**ミューテーションテスト — 実行中**\n\n"
        f"{ja['summary']}\n"
        "</details>\n"
    )


# ---------------------------------------------------------------------------
# Mode: foundation
# ---------------------------------------------------------------------------


_FOUNDATION_COLUMNS_EN = ("Original", "Foundation")
_FOUNDATION_COLUMNS_JA = ("当初", "基盤後")


def _validate_progression(
    progression: dict, *, expected_columns: tuple[str, ...] | None = None
) -> tuple[list[str], dict[str, list[str]]]:
    if not isinstance(progression, dict):
        raise RenderError("`progression` must be a mapping")
    cols = progression.get("columns")
    if not isinstance(cols, list) or not cols:
        raise RenderError("`progression.columns` must be a non-empty list")
    if expected_columns is not None and tuple(cols) != expected_columns:
        raise RenderError(
            f"`progression.columns` must equal {list(expected_columns)} for this "
            f"mode; got {cols}"
        )
    rows = progression.get("rows")
    if not isinstance(rows, dict):
        raise RenderError("`progression.rows` must be a mapping")
    required_row_keys = {"tests", "line_pct", "branch_pct", "kill_rate", "survived"}
    missing = required_row_keys - set(rows)
    if missing:
        raise RenderError(f"`progression.rows` missing keys: {sorted(missing)}")
    for key in required_row_keys:
        row = rows[key]
        if not isinstance(row, list) or len(row) != len(cols):
            raise RenderError(
                f"`progression.rows.{key}` must be a list of length "
                f"{len(cols)} (one cell per column)"
            )
    return cols, rows


def _render_progression_table(
    cols: list[str],
    rows: dict[str, list[str]],
    *,
    japanese: bool = False,
) -> str:
    if japanese:
        metric_labels = {
            "tests": "テスト",
            "line_pct": "行カバレッジ",
            "branch_pct": "ブランチ",
            "kill_rate": "キル率",
            "survived": "生存",
        }
        metric_header = "指標"
    else:
        metric_labels = {
            "tests": "Tests",
            "line_pct": "Line coverage",
            "branch_pct": "Branch coverage",
            "kill_rate": "Kill rate",
            "survived": "Survived",
        }
        metric_header = "Metric"

    header = "| " + " | ".join([metric_header, *cols]) + " |"
    sep = "|" + "|".join(["---"] * (len(cols) + 1)) + "|"
    body_lines: list[str] = [header, sep]
    for key in ("tests", "line_pct", "branch_pct", "kill_rate", "survived"):
        cells = []
        for cell in rows[key]:
            if cell == "N/A" or key == "tests":
                cells.append(str(cell))
            else:
                cells.append(f"`{cell}`")
        body_lines.append("| " + " | ".join([metric_labels[key], *cells]) + " |")
    return "\n".join(body_lines)


def _validate_foundation_tests(entries: list, *, japanese: bool) -> str:
    if not isinstance(entries, list) or not entries:
        raise RenderError("foundation payload `foundation_tests` must be non-empty")
    if japanese:
        lines = ["| ファイル | 追加テスト数 | カバー対象 |", "|---|---:|---|"]
    else:
        lines = ["| File | Tests added | Covers |", "|---|---:|---|"]
    for entry in entries:
        data = entry.get("ja") if japanese else entry
        if not data or not all(k in data for k in ("file", "added", "covers")):
            raise RenderError(
                "foundation_tests entry missing `file`/`added`/`covers` "
                f"(japanese={japanese})"
            )
        lines.append(f"| `{data['file']}` | {data['added']} | {data['covers']} |")
    return "\n".join(lines)


def _render_foundation(payload: dict) -> str:
    title = _require(payload, "feature_or_pr_title")
    summary = _require(payload, "summary")
    progression = _require(payload, "progression")
    cols, rows = _validate_progression(
        progression, expected_columns=_FOUNDATION_COLUMNS_EN
    )
    foundation_tests = _require(payload, "foundation_tests")
    notes = payload.get("notes") or []
    log_path = payload.get("log_path", "")

    ja = _require_ja(payload, label="foundation payload")
    for required in ("summary",):
        if not ja.get(required):
            raise RenderError(f"foundation payload `ja.{required}` is required")
    ja_progression = payload.get("ja_progression") or {
        "columns": list(_FOUNDATION_COLUMNS_JA),
        "rows": rows,
    }
    ja_cols, ja_rows = _validate_progression(
        ja_progression, expected_columns=_FOUNDATION_COLUMNS_JA
    )

    en_table = _render_progression_table(cols, rows)
    ja_table = _render_progression_table(ja_cols, ja_rows, japanese=True)

    en_tests_table = _validate_foundation_tests(foundation_tests, japanese=False)
    ja_tests_table = _validate_foundation_tests(foundation_tests, japanese=True)

    notes_block = "\n".join(f"- {n}" for n in notes)
    if log_path:
        notes_block += f"\n- Log: `{log_path}`"
    ja_notes = ja.get("notes") or []
    ja_notes_block = "\n".join(f"- {n}" for n in ja_notes)
    if log_path:
        ja_notes_block += f"\n- ログ: `{log_path}`"

    return (
        f"## Mutation testing — {title}\n\n"
        "**Foundation — test coverage uplift**\n\n"
        f"{summary}\n\n"
        "### Progression\n\n"
        f"{en_table}\n\n"
        "Kill rate is `N/A` at this stage — no mutations have been applied yet. "
        "Kill rate is reported in the next comment after the initial mutation pass.\n\n"
        "<details>\n<summary>Foundation tests added</summary>\n\n"
        f"{en_tests_table}\n</details>\n\n"
        "<details>\n<summary>Notes</summary>\n\n"
        f"{notes_block}\n</details>\n\n"
        "<details>\n<summary>JA</summary>\n\n"
        "**基盤 — テストカバレッジの底上げ**\n\n"
        f"{ja['summary']}\n\n"
        "### 進捗\n\n"
        f"{ja_table}\n\n"
        "ミューテーション未実行のため初期段階のキル率は `N/A` です。"
        "次コメントで初期ミューテーション結果を報告します。\n\n"
        "<details>\n<summary>追加した基盤テスト</summary>\n\n"
        f"{ja_tests_table}\n</details>\n\n"
        f"補足:\n\n{ja_notes_block}\n"
        "</details>\n"
    )


# ---------------------------------------------------------------------------
# Mode: initial
# ---------------------------------------------------------------------------


def _validate_survivor(entry: dict, *, mode: str) -> None:
    for key in ("id", "name", "gap", "mutation", "risk"):
        if not entry.get(key):
            raise RenderError(
                f"{mode} survivor missing required field {key!r}: {entry}"
            )
    classification = entry.get("classification")
    if classification not in SURVIVOR_CLASSIFICATIONS:
        raise RenderError(
            f"{mode} survivor {entry.get('id')!r} has invalid classification "
            f"{classification!r}; expected one of {sorted(SURVIVOR_CLASSIFICATIONS)}"
        )
    if classification == "pending" and not entry.get("planned_test"):
        raise RenderError(
            f"{mode} survivor {entry.get('id')!r} is classified `pending` but "
            "has no `planned_test`"
        )
    if classification == "dismissed" and not entry.get("dismissal_reason"):
        raise RenderError(
            f"{mode} survivor {entry.get('id')!r} is classified `dismissed` "
            "but has no `dismissal_reason`"
        )
    ja = entry.get("ja")
    if not isinstance(ja, dict):
        raise RenderError(
            f"{mode} survivor {entry.get('id')!r} missing `ja` mirror block"
        )
    for key in ("name", "gap", "mutation", "risk"):
        if not ja.get(key):
            raise RenderError(
                f"{mode} survivor {entry.get('id')!r} `ja` mirror missing {key!r}"
            )
    if classification == "pending" and not ja.get("planned_test"):
        raise RenderError(
            f"{mode} survivor {entry.get('id')!r} pending entry `ja.planned_test` "
            "is required"
        )
    if classification == "dismissed" and not ja.get("dismissal_reason"):
        raise RenderError(
            f"{mode} survivor {entry.get('id')!r} dismissed entry "
            "`ja.dismissal_reason` is required"
        )


def _render_survivor_block(entry: dict, *, japanese: bool) -> str:
    data = entry.get("ja") if japanese else entry
    classification = entry["classification"]
    if japanese:
        labels = {
            "Gap": "ギャップ",
            "Mutation": "変異内容",
            "Risk": "リスク",
            "Planned": "予定テスト",
            "Dismissed": "却下理由",
        }
        badge = (
            "<code>保留</code>"
            if classification == "pending"
            else "<code>≡ 同等のため却下</code>"
        )
    else:
        labels = {
            "Gap": "Gap",
            "Mutation": "Mutation",
            "Risk": "Risk",
            "Planned": "Planned test",
            "Dismissed": "Dismissal reason",
        }
        badge = (
            "<code>pending</code>"
            if classification == "pending"
            else "<code>≡ dismissed</code>"
        )

    rows = [
        f"| {labels['Gap']} | {data['gap']} |",
        f"| {labels['Mutation']} | {data['mutation']} |",
        f"| {labels['Risk']} | {data['risk']} |",
    ]
    if classification == "pending":
        rows.append(f"| {labels['Planned']} | {data['planned_test']} |")
    else:
        rows.append(f"| {labels['Dismissed']} | {data['dismissal_reason']} |")
    header_label = "観点" if japanese else "Finding"
    detail_label = "詳細" if japanese else "Details"
    table = (
        f"| {header_label} | {detail_label} |\n"
        "|---|---|\n"
        + "\n".join(rows)
    )
    summary = f"<summary>{entry['id']} — {data['name']} {badge}</summary>"
    return f"<details>\n{summary}\n\n{table}\n</details>"


def _render_caught_brief_block(caught: list[dict], *, japanese: bool) -> str:
    if not caught:
        return (
            "キャッチされたミューテーションなし。"
            if japanese
            else "_No mutations caught yet._"
        )
    bullets = []
    for entry in caught:
        data = entry.get("ja") if japanese and entry.get("ja") else entry
        caught_by = data.get("caught_by", "")
        by_label = "検出テスト" if japanese else "caught by"
        bullets.append(
            f"- `{entry['id']}` — {data.get('name', '')} ({by_label}: `{caught_by}`)"
        )
    return "\n".join(bullets)


_INITIAL_COLUMNS_FOUNDATION_EN = ("Original", "Foundation", "Initial mutation")
_INITIAL_COLUMNS_NO_FOUNDATION_EN = ("Original", "Initial mutation")
_INITIAL_COLUMNS_FOUNDATION_JA = ("当初", "基盤後", "初期ミューテーション")
_INITIAL_COLUMNS_NO_FOUNDATION_JA = ("当初", "初期ミューテーション")


def _render_initial(payload: dict) -> str:
    title = _require(payload, "feature_or_pr_title")
    summary = _require(payload, "summary")
    foundation_was_run = bool(payload.get("foundation_was_run"))
    expected_en = (
        _INITIAL_COLUMNS_FOUNDATION_EN
        if foundation_was_run
        else _INITIAL_COLUMNS_NO_FOUNDATION_EN
    )
    expected_ja = (
        _INITIAL_COLUMNS_FOUNDATION_JA
        if foundation_was_run
        else _INITIAL_COLUMNS_NO_FOUNDATION_JA
    )
    progression = _require(payload, "progression")
    cols, rows = _validate_progression(progression, expected_columns=expected_en)
    ja_progression = payload.get("ja_progression") or {
        "columns": list(expected_ja),
        "rows": rows,
    }
    ja_cols, ja_rows = _validate_progression(
        ja_progression, expected_columns=expected_ja
    )

    survivors = payload.get("survivors") or []
    if not isinstance(survivors, list):
        raise RenderError("`survivors` must be a list (may be empty)")
    for entry in survivors:
        _validate_survivor(entry, mode="initial")

    caught = payload.get("caught") or []
    notes = payload.get("notes") or []
    log_path = payload.get("log_path", "")
    targeted = payload.get("targeted_suite_description", "")
    test_quality = payload.get("test_quality", "")

    ja = _require_ja(payload, label="initial payload")
    if not ja.get("summary"):
        raise RenderError("initial payload `ja.summary` is required")

    # Top stats line derived from rows directly so it cannot drift.
    initial_kill_idx = len(cols) - 1
    initial_killed_total = rows["kill_rate"][initial_kill_idx]
    initial_survived = rows["survived"][initial_kill_idx]
    en_table = _render_progression_table(cols, rows)
    ja_table = _render_progression_table(ja_cols, ja_rows, japanese=True)

    survivor_blocks_en = "\n\n".join(
        _render_survivor_block(e, japanese=False) for e in survivors
    ) or "_No surviving mutations after the initial pass._"
    survivor_blocks_ja = "\n\n".join(
        _render_survivor_block(e, japanese=True) for e in survivors
    ) or "初期ミューテーション後の生存なし。"
    caught_block_en = _render_caught_brief_block(caught, japanese=False)
    caught_block_ja = _render_caught_brief_block(caught, japanese=True)

    notes_block = "\n".join(f"- {n}" for n in notes)
    if log_path:
        notes_block += f"\n- Log: `{log_path}`"
    ja_notes = ja.get("notes") or []
    ja_notes_block = "\n".join(f"- {n}" for n in ja_notes)
    if log_path:
        ja_notes_block += f"\n- ログ: `{log_path}`"

    targeted_line = (
        f"Target: {targeted}\n\n" if targeted else ""
    )
    return (
        f"## Mutation testing — {title}\n\n"
        "**Initial mutation results — checkpoint**\n\n"
        f"Kill rate `{initial_killed_total}` · Survivors `{initial_survived}`\n\n"
        f"{summary}\n\n"
        f"{targeted_line}"
        "### Progression\n\n"
        f"{en_table}\n\n"
        "### Survivors — to be resolved in final report\n\n"
        f"{survivor_blocks_en}\n\n"
        f"<details>\n<summary>✓ {len(caught)} mutations caught</summary>\n\n"
        f"{caught_block_en}\n</details>\n\n"
        + (
            "<details>\n<summary>Test quality</summary>\n\n"
            f"{test_quality}\n</details>\n\n"
            if test_quality
            else ""
        )
        + "<details>\n<summary>Notes</summary>\n\n"
        f"{notes_block}\n</details>\n\n"
        "<details>\n<summary>JA</summary>\n\n"
        "**初期ミューテーション結果 — チェックポイント**\n\n"
        f"キル率 `{initial_killed_total}` · 生存 `{initial_survived}`\n\n"
        f"{ja['summary']}\n\n"
        "### 進捗\n\n"
        f"{ja_table}\n\n"
        "### 生存ミューテーション — 最終レポートで解決\n\n"
        f"{survivor_blocks_ja}\n\n"
        f"<details>\n<summary>✓ {len(caught)} 件キャッチ済み</summary>\n\n"
        f"{caught_block_ja}\n</details>\n\n"
        + (
            f"<details>\n<summary>テスト品質</summary>\n\n"
            f"{ja.get('test_quality', '')}\n</details>\n\n"
            if ja.get("test_quality")
            else ""
        )
        + f"補足:\n\n{ja_notes_block}\n"
        "</details>\n"
    )


# ---------------------------------------------------------------------------
# Mode: final
# ---------------------------------------------------------------------------


def _validate_resolved(entry: dict) -> None:
    for key in ("id", "name", "explanation"):
        if not entry.get(key):
            raise RenderError(
                f"final resolved entry missing required field {key!r}: {entry}"
            )
    resolution = entry.get("resolution")
    if resolution not in RESOLUTION_TYPES:
        raise RenderError(
            f"final resolved entry {entry.get('id')!r} has invalid "
            f"resolution {resolution!r}; expected one of {sorted(RESOLUTION_TYPES)}"
        )
    if resolution == "killed" and not entry.get("added_test"):
        raise RenderError(
            f"final resolved entry {entry.get('id')!r} resolution=killed "
            "requires `added_test`"
        )
    if resolution == "dismissed" and not entry.get("dismissal_reason"):
        raise RenderError(
            f"final resolved entry {entry.get('id')!r} resolution=dismissed "
            "requires `dismissal_reason`"
        )
    ja = entry.get("ja")
    if not isinstance(ja, dict):
        raise RenderError(
            f"final resolved entry {entry.get('id')!r} missing `ja` mirror block"
        )
    for key in ("name", "explanation"):
        if not ja.get(key):
            raise RenderError(
                f"final resolved entry {entry.get('id')!r} `ja` missing {key!r}"
            )
    if resolution == "killed" and not ja.get("added_test"):
        raise RenderError(
            f"final resolved entry {entry.get('id')!r} `ja.added_test` is required"
        )
    if resolution == "dismissed" and not ja.get("dismissal_reason"):
        raise RenderError(
            f"final resolved entry {entry.get('id')!r} `ja.dismissal_reason` "
            "is required"
        )


def _render_resolved_block(entries: list[dict], *, japanese: bool) -> str:
    if not entries:
        return (
            "初期生存なし — 解決対象はありません。"
            if japanese
            else "_No initial survivors — nothing to resolve._"
        )
    pieces: list[str] = []
    for entry in entries:
        data = entry.get("ja") if japanese else entry
        if entry["resolution"] == "killed":
            badge = "✓"
            tail = (
                ("検出テスト" if japanese else "Caught by")
                + f": `{data['added_test']}`."
            )
        else:
            badge = "≡"
            tail = (
                ("却下理由" if japanese else "Dismissal reason")
                + f": {data['dismissal_reason']}."
            )
        suffix = (
            "（同等のため却下）"
            if japanese and entry["resolution"] == "dismissed"
            else " (dismissed as equivalent)"
            if entry["resolution"] == "dismissed"
            else ""
        )
        pieces.append(
            "<details>\n"
            f"<summary>{badge} {entry['id']} — {data['name']}{suffix}</summary>\n\n"
            f"{data['explanation']}\n\n"
            f"{tail}\n"
            "</details>"
        )
    return "\n\n".join(pieces)


def _render_caught_originally_block(
    caught: list[dict], *, japanese: bool
) -> str:
    if not caught:
        return (
            "初期キャッチなし。"
            if japanese
            else "_No mutations caught in the initial pass._"
        )
    pieces: list[str] = []
    for entry in caught:
        data = entry.get("ja") if japanese else entry
        caught_by_label = "検出テスト" if japanese else "Caught by"
        pieces.append(
            "<details>\n"
            f"<summary>✓ {entry['id']} — {data.get('name', '')}</summary>\n\n"
            f"{caught_by_label}: `{data.get('caught_by', '')}`.\n"
            "</details>"
        )
    return "\n\n".join(pieces)


def _render_table(
    rows: list[dict],
    headers: tuple[str, str, str],
    keys: tuple[str, str, str],
) -> str:
    if not rows:
        return f"| {headers[0]} | {headers[1]} | {headers[2]} |\n|---|---|---|"
    lines = [
        f"| {headers[0]} | {headers[1]} | {headers[2]} |",
        "|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row.get(keys[0], '')} | {row.get(keys[1], '')} | "
            f"{row.get(keys[2], '')} |"
        )
    return "\n".join(lines)


_FINAL_COLUMNS_FOUNDATION_EN = (
    "Original",
    "Foundation",
    "Initial mutation",
    "Final",
)
_FINAL_COLUMNS_NO_FOUNDATION_EN = ("Original", "Initial mutation", "Final")
_FINAL_COLUMNS_FOUNDATION_JA = ("当初", "基盤後", "初期ミューテーション", "最終")
_FINAL_COLUMNS_NO_FOUNDATION_JA = ("当初", "初期ミューテーション", "最終")


def _render_final(payload: dict) -> str:
    title = _require(payload, "feature_or_pr_title")
    summary = _require(payload, "summary")
    foundation_was_run = bool(payload.get("foundation_was_run"))
    expected_en = (
        _FINAL_COLUMNS_FOUNDATION_EN
        if foundation_was_run
        else _FINAL_COLUMNS_NO_FOUNDATION_EN
    )
    expected_ja = (
        _FINAL_COLUMNS_FOUNDATION_JA
        if foundation_was_run
        else _FINAL_COLUMNS_NO_FOUNDATION_JA
    )
    progression = _require(payload, "progression")
    cols, rows = _validate_progression(progression, expected_columns=expected_en)
    ja_progression = payload.get("ja_progression") or {
        "columns": list(expected_ja),
        "rows": rows,
    }
    ja_cols, ja_rows = _validate_progression(
        ja_progression, expected_columns=expected_ja
    )

    resolved = payload.get("resolved") or []
    if not isinstance(resolved, list):
        raise RenderError("`resolved` must be a list (may be empty)")
    for entry in resolved:
        _validate_resolved(entry)
    if any(e.get("resolution") not in RESOLUTION_TYPES for e in resolved):
        raise RenderError(
            "final mode rejects `pending` survivors; resolve every initial "
            "survivor as `killed` or `dismissed` before posting"
        )

    caught_originally = payload.get("caught_originally") or []
    changes = payload.get("changes") or []
    gaps = payload.get("gaps") or []
    notes = payload.get("notes") or []
    log_path = payload.get("log_path", "")
    test_quality = payload.get("test_quality", "")
    targeted = payload.get("targeted_suite_description", "")

    ja = _require_ja(payload, label="final payload")
    if not ja.get("summary"):
        raise RenderError("final payload `ja.summary` is required")

    # Derive header stats from progression rows.
    final_idx = len(cols) - 1
    initial_idx = final_idx - 1
    final_kill_rate_cell = rows["kill_rate"][final_idx]
    initial_tests = rows["tests"][initial_idx]
    final_tests = rows["tests"][final_idx]
    dismissed_count = sum(1 for e in resolved if e["resolution"] == "dismissed")
    newly_killed_count = sum(1 for e in resolved if e["resolution"] == "killed")
    total_caught_count = len(caught_originally) + newly_killed_count

    targeted_line = f" · Target: {targeted}" if targeted else ""

    en_table = _render_progression_table(cols, rows)
    ja_table = _render_progression_table(ja_cols, ja_rows, japanese=True)

    resolved_en = _render_resolved_block(resolved, japanese=False)
    resolved_ja = _render_resolved_block(resolved, japanese=True)
    caught_en = _render_caught_originally_block(caught_originally, japanese=False)
    caught_ja = _render_caught_originally_block(caught_originally, japanese=True)

    en_changes_table = _render_table(
        changes,
        headers=("Area", "Change", "Result"),
        keys=("area", "change", "result"),
    )
    en_gaps_table = _render_table(
        gaps,
        headers=("Area", "Add", "Why"),
        keys=("area", "test", "reason"),
    )
    ja_changes_table = _render_table(
        [c.get("ja", {}) for c in changes if c.get("ja")],
        headers=("領域", "変更", "結果"),
        keys=("area", "change", "result"),
    )
    ja_gaps_table = _render_table(
        [g.get("ja", {}) for g in gaps if g.get("ja")],
        headers=("領域", "追加するテスト", "理由"),
        keys=("area", "test", "reason"),
    )

    notes_block = "\n".join(f"- {n}" for n in notes)
    if log_path:
        notes_block += f"\n- Log: `{log_path}`"
    ja_notes = ja.get("notes") or []
    ja_notes_block = "\n".join(f"- {n}" for n in ja_notes)
    if log_path:
        ja_notes_block += f"\n- ログ: `{log_path}`"

    return (
        f"## Mutation testing — {title}\n\n"
        "**Final report**\n\n"
        f"`{len(resolved) + len(caught_originally)}` mutations · "
        f"`{total_caught_count}` killed · "
        f"`{dismissed_count}` dismissed · "
        f"`0` remaining · final kill rate `{final_kill_rate_cell}`  \n"
        f"Tests: `{initial_tests}`→`{final_tests}`{targeted_line}\n\n"
        f"{summary}\n\n"
        "### Resolved\n\n"
        "Every mutation that survived the initial pass is resolved below as "
        "`✓ killed` (a new test catches it) or `≡ dismissed` (functionally "
        "equivalent — explained).\n\n"
        f"{resolved_en}\n\n"
        "### Progression\n\n"
        f"{en_table}\n\n"
        "Final kill rate formula: `killed / (total − dismissed)`. Dismissed "
        "mutations are excluded from the denominator because they are "
        "functionally equivalent and no test can distinguish them from the "
        "original code.\n\n"
        "<details>\n<summary>Changes made</summary>\n\n"
        f"{en_changes_table}\n</details>\n\n"
        "<details>\n<summary>What's left for high-quality coverage</summary>\n\n"
        f"{en_gaps_table}\n\nTest quality: {test_quality}.\n</details>\n\n"
        f"<details>\n<summary>✓ {total_caught_count} mutations caught "
        f"({newly_killed_count} newly fixed)</summary>\n\n"
        f"{caught_en}\n\n</details>\n\n"
        "<details>\n<summary>Notes</summary>\n\n"
        f"{notes_block}\n</details>\n\n"
        "<details>\n<summary>JA</summary>\n\n"
        "**最終レポート**\n\n"
        f"`{len(resolved) + len(caught_originally)}` 件のミューテーション · "
        f"`{total_caught_count}` 件キル · "
        f"`{dismissed_count}` 件却下 · "
        f"`0` 件残存 · 最終キル率 `{final_kill_rate_cell}`\n\n"
        f"{ja['summary']}\n\n"
        "### 解決\n\n"
        f"{resolved_ja}\n\n"
        "### 進捗\n\n"
        f"{ja_table}\n\n"
        "最終キル率の式: `kill / (total − dismissed)`。"
        "同等として却下されたミューテーションは分母から除外します。\n\n"
        f"変更内容:\n\n{ja_changes_table}\n\n"
        f"高品質なカバレッジに向けて残っていること:\n\n{ja_gaps_table}\n\n"
        f"テスト品質: {ja.get('test_quality', test_quality)}\n\n"
        f"<details>\n<summary>✓ {total_caught_count} 件のキャッチ"
        f"（うち {newly_killed_count} 件は新規修正）</summary>\n\n"
        f"{caught_ja}\n\n</details>\n\n"
        f"補足:\n\n{ja_notes_block}\n"
        "</details>\n"
    )


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


_RENDERERS = {
    "status": _render_status,
    "foundation": _render_foundation,
    "initial": _render_initial,
    "final": _render_final,
}


def render(payload: dict) -> str:
    mode = payload.get("mode")
    if mode not in VALID_MODES:
        raise RenderError(
            f"`mode` must be one of {sorted(VALID_MODES)}, got {mode!r}"
        )
    return _RENDERERS[mode](payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("results", type=Path, help="path to results JSON")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="write the rendered markdown to this path (default: stdout)",
    )
    args = parser.parse_args(argv)

    try:
        payload = json.loads(args.results.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"render_pr_comment: cannot read {args.results}: {exc}", file=sys.stderr)
        return 2

    try:
        rendered = render(payload)
    except RenderError as exc:
        print(f"render_pr_comment: {exc}", file=sys.stderr)
        return 2

    if args.out:
        args.out.write_text(rendered)
        print(f"[render_pr_comment] wrote {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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
render_pr_comment.py — Render the Stage 3 PR comment (`template_03_final_report.md`)
from a structured JSON results blob.

This script exists to eliminate the class of bugs where a hand-written ~20 KB
PR comment silently drops a required section or accidentally uses a stale
format. The single source of truth is a small JSON results file that the
agent assembles from `mutation_runner.py`, `coverage_summary.py`, and its own
notes. The renderer turns that into the exact markdown shape mandated by
`template_03_final_report.md`.

Input JSON shape (see `_validate` for the canonical schema):

    {
      "feature_or_pr_title": "Block destructive DDL in execute_sql",
      "targeted_suite_description": "<paths joined by '+'>",
      "mode": "final",  // or "checkpoint"
      "log_path": ".devin/mutation-testing/pr-15-...md",

      "initial": {
        "passed_tests": 560, "failed_tests": 0,
        "line_pct": 95, "branch_pct": 94,
        "killed": 12, "survived": 4, "total": 16
      },
      "final": {                              // optional in checkpoint mode
        "passed_tests": 571, "failed_tests": 0,
        "line_pct": 95, "branch_pct": 94,
        "killed": 16, "survived": 0, "total": 16
      },

      "surviving": [                          // remaining uncaught after fixes
        {"name": "...", "gap": "...", "mutation": "...", "risk": "...",
         "ja": {"name": "...", "gap": "...", "mutation": "...",
                "risk": "..."}}
      ],
      "caught": [                             // every caught/newly-fixed mutation
        {"name": "...", "explanation": "...", "caught_by": "...",
         "newly_fixed": true,
         "ja": {"name": "...", "explanation": "...", "caught_by": "..."}}
      ],
      "changes": [                            // changes made
        {"area": "...", "change": "...", "result": "...",
         "ja": {"area": "...", "change": "...", "result": "..."}}
      ],
      "gaps": [                               // what's left for high-quality coverage
        {"area": "...", "test": "...", "reason": "...",
         "ja": {"area": "...", "test": "...", "reason": "..."}}
      ],

      "summary": "...",                       // English summary
      "test_quality": "...",                  // one-line at-a-glance comment
      "notes": ["...", "..."],                // bulleted notes

      "ja": {                                 // Japanese mirror
        "summary": "...",
        "test_quality": "...",
        "notes": ["...", "..."]
      }
    }

Usage:
    render_pr_comment.py results.json [--out comment.md]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _kill_rate(killed: int, total: int) -> int:
    return round(killed / total * 100) if total else 0


def _validate(payload: dict) -> tuple[dict, dict, str]:
    """Return (initial, final, mode); raise ValueError on shape errors."""
    mode = payload.get("mode", "final")
    if mode not in {"checkpoint", "final"}:
        raise ValueError(f"mode must be 'checkpoint' or 'final', got {mode!r}")

    initial = payload.get("initial")
    if not isinstance(initial, dict):
        raise ValueError("missing or non-dict 'initial' section")
    required_state_keys = {
        "passed_tests",
        "failed_tests",
        "line_pct",
        "branch_pct",
        "killed",
        "survived",
        "total",
    }
    missing = required_state_keys - set(initial)
    if missing:
        raise ValueError(f"'initial' missing keys: {sorted(missing)}")

    final = payload.get("final")
    if mode == "final":
        if not isinstance(final, dict):
            raise ValueError("'final' section required when mode='final'")
        missing = required_state_keys - set(final)
        if missing:
            raise ValueError(f"'final' missing keys: {sorted(missing)}")
    else:
        # In checkpoint mode, mirror initial into final for table formatting.
        final = dict(initial)

    return initial, final, mode


def _render_caught_block(caught: list[dict], *, japanese: bool = False) -> str:
    if not caught:
        return ""
    pieces: list[str] = []
    for entry in caught:
        data = entry.get("ja") if japanese else entry
        if not data:
            continue
        suffix = " (newly fixed)" if entry.get("newly_fixed") and not japanese else ""
        ja_suffix = "（新規修正）" if entry.get("newly_fixed") and japanese else ""
        head = f"<summary>✓ {data['name']}{ja_suffix or suffix}</summary>"
        explanation = data.get("explanation", "")
        caught_by_label = "検出テスト" if japanese else "Caught by"
        caught_by = data.get("caught_by", "")
        pieces.append(
            "<details>\n"
            f"{head}\n\n"
            f"{explanation}\n\n"
            f"{caught_by_label}: {caught_by}.\n"
            "</details>"
        )
    return "\n\n".join(pieces)


def _render_surviving_block(surviving: list[dict], *, japanese: bool = False) -> str:
    if not surviving:
        return (
            "修正後に生存ミューテーションなし。"
            if japanese
            else "<!-- No surviving mutations remained after targeted fixes. -->"
        )
    pieces: list[str] = []
    for entry in surviving:
        data = entry.get("ja") if japanese else entry
        if not data:
            continue
        if japanese:
            table = (
                "| 観点 | 詳細 |\n"
                "|---|---|\n"
                f"| ギャップ | {data['gap']} |\n"
                f"| 変異内容 | {data['mutation']} |\n"
                f"| リスク | {data['risk']} |"
            )
        else:
            table = (
                "| Finding | Details |\n"
                "|---|---|\n"
                f"| Gap | {data['gap']} |\n"
                f"| Mutation | {data['mutation']} |\n"
                f"| Risk | {data['risk']} |"
            )
        pieces.append(
            f"<details>\n<summary>❌ {data['name']}</summary>\n\n{table}\n</details>"
        )
    return "\n\n".join(pieces)


def _render_table(
    rows: list[dict], headers: tuple[str, str, str], keys: tuple[str, str, str]
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


def render(payload: dict) -> str:
    initial, final, mode = _validate(payload)

    initial_kill_rate = _kill_rate(initial["killed"], initial["total"])
    final_kill_rate = _kill_rate(final["killed"], final["total"])

    surviving = payload.get("surviving", [])
    caught = payload.get("caught", [])
    changes = payload.get("changes", [])
    gaps = payload.get("gaps", [])
    summary = payload.get("summary", "")
    notes = payload.get("notes", [])
    test_quality = payload.get("test_quality", "")

    ja = payload.get("ja", {})
    ja_changes = [c.get("ja", {}) for c in changes if c.get("ja")]
    ja_gaps = [g.get("ja", {}) for g in gaps if g.get("ja")]

    newly_fixed_count = sum(1 for c in caught if c.get("newly_fixed"))
    targeted = payload.get("targeted_suite_description", "")
    log_path = payload.get("log_path", "")

    header = (
        f"## Mutation testing — {payload.get('feature_or_pr_title', '')}\n\n"
        f"`{initial['total']}` mutations · "
        f"`{initial['killed']}`→`{final['killed']}` caught · "
        f"`{initial['survived']}`→`{final['survived']}` survived · "
        f"kill rate `{initial_kill_rate}%`→`{final_kill_rate}%`  \n"
        f"Tests: `{initial['passed_tests']} passed`→"
        f"`{final['passed_tests']} passed` · "
        f"Target: {targeted}"
    )

    coverage_table = (
        "| Metric | Initial | Final |\n"
        "|---|---:|---:|\n"
        f"| Tests | {initial['passed_tests']} passed | "
        f"{final['passed_tests']} passed |\n"
        f"| Line coverage | `{initial['line_pct']}%` | "
        f"`{final['line_pct']}%` |\n"
        f"| Branch coverage | `{initial['branch_pct']}%` | "
        f"`{final['branch_pct']}%` |\n"
        f"| Kill rate | `{initial_kill_rate}%` "
        f"({initial['killed']}/{initial['total']}) | "
        f"`{final_kill_rate}%` ({final['killed']}/{final['total']}) |\n"
        f"| Survived | {initial['survived']} | {final['survived']} |"
    )

    changes_table = _render_table(
        changes,
        headers=("Area", "Change", "Result"),
        keys=("area", "change", "result"),
    )
    gaps_table = _render_table(
        gaps,
        headers=("Area", "Add", "Why"),
        keys=("area", "test", "reason"),
    )
    ja_changes_table = _render_table(
        ja_changes,
        headers=("領域", "変更", "結果"),
        keys=("area", "change", "result"),
    )
    ja_gaps_table = _render_table(
        ja_gaps,
        headers=("領域", "追加するテスト", "理由"),
        keys=("area", "test", "reason"),
    )

    notes_block = "\n".join(f"- {n}" for n in notes)
    if log_path:
        notes_block += f"\n- Log: `{log_path}`"

    ja_notes = ja.get("notes", [])
    ja_notes_block = "\n".join(f"- {n}" for n in ja_notes)
    if log_path:
        ja_notes_block += f"\n- ログ: `{log_path}`"

    ja_summary_block = (
        f"<details>\n<summary>JA</summary>\n\n"
        f"{ja.get('summary', '')}\n\n"
        f"{_render_surviving_block(surviving, japanese=True)}\n\n"
        f"変更内容:\n\n{ja_changes_table}\n\n"
        f"高品質なカバレッジに向けて残っていること:\n\n{ja_gaps_table}\n\n"
        f"テスト品質: {ja.get('test_quality', '')}\n\n"
        f"<details>\n<summary>✓ {final['killed']} 検出済みミューテーション"
        "</summary>\n\n"
        f"{_render_caught_block(caught, japanese=True)}\n\n"
        f"</details>\n\n"
        "| 状態 | テスト | 行 | ブランチ | kill rate | 生存 |\n"
        "|---|---:|---:|---:|---:|---:|\n"
        f"| 初期 | {initial['passed_tests']} | `{initial['line_pct']}%` | "
        f"`{initial['branch_pct']}%` | `{initial_kill_rate}%` | "
        f"{initial['survived']} |\n"
        f"| 最終 | {final['passed_tests']} | `{final['line_pct']}%` | "
        f"`{final['branch_pct']}%` | `{final_kill_rate}%` | "
        f"{final['survived']} |\n\n"
        f"補足:\n\n{ja_notes_block}\n"
        "</details>"
    )

    body = (
        f"{header}\n\n"
        f"### Remaining uncaught mutations\n\n"
        f"{_render_surviving_block(surviving)}\n\n"
        f"### Summary\n\n{summary}\n\n"
        f"### Coverage\n\n{coverage_table}\n\n"
        f"<details>\n<summary>Changes made</summary>\n\n"
        f"{changes_table}\n</details>\n\n"
        f"<details>\n<summary>What's left for high-quality coverage</summary>\n\n"
        f"{gaps_table}\n\nTest quality: {test_quality}.\n</details>\n\n"
        f"<details>\n<summary>✓ {final['killed']} mutations caught "
        f"({newly_fixed_count} newly fixed)</summary>\n\n"
        f"{_render_caught_block(caught)}\n\n"
        f"</details>\n\n"
        f"<details>\n<summary>Notes</summary>\n\n{notes_block}\n</details>\n\n"
        f"{ja_summary_block}\n"
    )
    return body


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

    payload = json.loads(args.results.read_text())
    try:
        rendered = render(payload)
    except ValueError as exc:
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

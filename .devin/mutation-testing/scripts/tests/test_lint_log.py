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
Tests for lint_log.py — validation of the Stage 2 mutation-testing log file.

Each test covers exactly one validation rule from `template_02_mutation_testing.md`
so a regression that drops a check shows up as a single failing test.
"""

from __future__ import annotations

from pathlib import Path

import yaml

import lint_log  # type: ignore[import-not-found]  # loaded via conftest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


REQUIRED_SECTIONS_ORDER = [
    "PR understanding",
    "Triage decision",
    "Initial targeted coverage",
    "Initial mutation plan",
    "Initial mutation results",
    "Fix plan",
    "Changes made",
    "Final verification",
    "Final assessment",
    "What's left for high-quality coverage",
]


def _valid_meta(*, status: str = "completed") -> dict:
    """Return a deep-copyable dict satisfying every required key."""
    meta: dict = {
        "pr_id": 42,
        "pr_title": "feat: example",
        "run_date": "2026-01-02",
        "agent": "devin",
        "repo": "owner/repo",
        "branch": "devin/123-example",
        "base_branch": "master",
        "mode": "mutation-testing-and-test-improvement",
        "status": status,
        "triage": {
            "coverage_level": "absent",
            "foundation_needed": True,
        },
        "target": {
            "behavior": ["does the thing"],
            "implementation_files": ["a.py"],
            "test_files": ["test_a.py"],
        },
        "initial_state": {
            "targeted_tests": {
                "command": "pytest -q",
                "passed": 0,
                "failed": 0,
            },
            "coverage": {
                "line": {"percent": 0, "covered": 0, "total": 0},
                "branch": {"percent": 0, "covered": 0, "total": 0},
            },
            "mutation_testing": {
                "valid_mutations": 0,
                "killed": 0,
                "survived": 0,
                "kill_rate": 0,
            },
        },
        "final_state": {
            "targeted_tests": {
                "command": "pytest -q",
                "passed": 1,
                "failed": 0,
            },
            "coverage": {
                "line": {"percent": 50, "covered": 10, "total": 20},
                "branch": {"percent": 50, "covered": 5, "total": 10},
            },
            "mutation_testing": {
                "valid_mutations": 4,
                "killed": 4,
                "survived": 0,
                "kill_rate": 100,
                "rerun_type": "full",
            },
        },
        "commits": ["abc123"],
        "artifacts": {"pr_comment_url": ""},
    }
    return meta


def _valid_body() -> str:
    """Return body markdown containing every required H2 section in order."""
    lines = []
    for header in REQUIRED_SECTIONS_ORDER:
        lines.append(f"## {header}")
        lines.append("placeholder content.")
        lines.append("")
    return "\n".join(lines)


def _write_log(
    tmp_path: Path,
    *,
    name: str = "pr-42-2026-01-02-example.md",
    meta: dict | None = None,
    raw_front_matter: str | None = None,
    body: str | None = None,
) -> Path:
    path = tmp_path / name
    if raw_front_matter is not None:
        fm_text = raw_front_matter
    else:
        fm_text = yaml.safe_dump(meta if meta is not None else _valid_meta(),
                                 sort_keys=False)
    body_text = _valid_body() if body is None else body
    path.write_text(f"---\n{fm_text}---\n{body_text}\n")
    return path


# ---------------------------------------------------------------------------
# Filename validation
# ---------------------------------------------------------------------------


def test_filename_matching_pattern_passes(tmp_path: Path) -> None:
    log = _write_log(tmp_path, name="pr-42-2026-01-02-example.md")
    assert lint_log.lint(log) == []


def test_filename_with_wrong_pattern_fails(tmp_path: Path) -> None:
    log = _write_log(tmp_path, name="pr_42_2026_01_02.md")
    errors = lint_log.lint(log)
    assert any("does not match pattern" in e for e in errors)


def test_filename_with_uppercase_slug_fails(tmp_path: Path) -> None:
    log = _write_log(tmp_path, name="pr-42-2026-01-02-EXAMPLE.md")
    errors = lint_log.lint(log)
    assert any("does not match pattern" in e for e in errors)


def test_filename_without_slug_fails(tmp_path: Path) -> None:
    log = _write_log(tmp_path, name="pr-42-2026-01-02-.md")
    errors = lint_log.lint(log)
    assert any("does not match pattern" in e for e in errors)


# ---------------------------------------------------------------------------
# File existence and front matter parsing
# ---------------------------------------------------------------------------


def test_non_existent_file_reports_missing(tmp_path: Path) -> None:
    errors = lint_log.lint(tmp_path / "pr-1-2026-01-02-x.md")
    assert any("file does not exist" in e for e in errors)


def test_missing_front_matter_fails(tmp_path: Path) -> None:
    path = tmp_path / "pr-1-2026-01-02-x.md"
    path.write_text("just a body\n")
    errors = lint_log.lint(path)
    assert any("YAML front matter not found" in e for e in errors)


def test_unparseable_yaml_front_matter_fails(tmp_path: Path) -> None:
    path = tmp_path / "pr-1-2026-01-02-x.md"
    path.write_text("---\nkey: '\n---\nbody\n")
    errors = lint_log.lint(path)
    assert any("not parseable" in e for e in errors)


def test_non_mapping_front_matter_fails(tmp_path: Path) -> None:
    path = tmp_path / "pr-1-2026-01-02-x.md"
    # YAML list at the top — parses, but is not a mapping.
    path.write_text("---\n- a\n- b\n---\nbody\n")
    errors = lint_log.lint(path)
    assert any("must be a mapping" in e for e in errors)


# ---------------------------------------------------------------------------
# Required top-level keys
# ---------------------------------------------------------------------------


def test_missing_top_level_key_fails(tmp_path: Path) -> None:
    meta = _valid_meta()
    del meta["pr_id"]
    log = _write_log(tmp_path, meta=meta)
    errors = lint_log.lint(log)
    assert any("YAML missing keys" in e and "'pr_id'" in e for e in errors)


def test_invalid_status_value_fails(tmp_path: Path) -> None:
    meta = _valid_meta()
    meta["status"] = "halfway"
    log = _write_log(tmp_path, meta=meta)
    errors = lint_log.lint(log)
    assert any(
        "status must be in_progress|completed" in e for e in errors
    )


def test_in_progress_status_does_not_require_rerun_type(tmp_path: Path) -> None:
    meta = _valid_meta(status="in_progress")
    # Drop the rerun_type; allowed when status != completed.
    del meta["final_state"]["mutation_testing"]["rerun_type"]
    log = _write_log(tmp_path, meta=meta)
    errors = lint_log.lint(log)
    assert errors == []


# ---------------------------------------------------------------------------
# initial_state / final_state structure
# ---------------------------------------------------------------------------


def test_state_not_a_mapping_fails(tmp_path: Path) -> None:
    meta = _valid_meta()
    meta["initial_state"] = "not_a_mapping"
    log = _write_log(tmp_path, meta=meta)
    errors = lint_log.lint(log)
    assert any("initial_state must be a mapping" in e for e in errors)


def test_state_missing_subkey_fails(tmp_path: Path) -> None:
    meta = _valid_meta()
    del meta["initial_state"]["targeted_tests"]
    log = _write_log(tmp_path, meta=meta)
    errors = lint_log.lint(log)
    assert any(
        "initial_state missing keys" in e and "targeted_tests" in e
        for e in errors
    )


def test_state_coverage_missing_line_subkey_fails(tmp_path: Path) -> None:
    meta = _valid_meta()
    del meta["initial_state"]["coverage"]["line"]["total"]
    log = _write_log(tmp_path, meta=meta)
    errors = lint_log.lint(log)
    assert any(
        "initial_state.coverage.line missing keys" in e and "total" in e
        for e in errors
    )


def test_state_coverage_axis_not_mapping_fails(tmp_path: Path) -> None:
    meta = _valid_meta()
    meta["initial_state"]["coverage"]["line"] = "broken"
    log = _write_log(tmp_path, meta=meta)
    errors = lint_log.lint(log)
    assert any(
        "initial_state.coverage.line must be a mapping" in e for e in errors
    )


def test_state_coverage_object_not_a_mapping_fails(tmp_path: Path) -> None:
    """L117: the wrapping `coverage:` value itself must be a mapping."""
    meta = _valid_meta()
    meta["initial_state"]["coverage"] = "broken"
    log = _write_log(tmp_path, meta=meta)
    errors = lint_log.lint(log)
    assert any("initial_state.coverage must be a mapping" in e for e in errors)


def test_state_coverage_missing_axis_fails(tmp_path: Path) -> None:
    """L121: `coverage:` must contain both `line` and `branch` axes."""
    meta = _valid_meta()
    del meta["initial_state"]["coverage"]["branch"]
    log = _write_log(tmp_path, meta=meta)
    errors = lint_log.lint(log)
    assert any(
        "initial_state.coverage missing keys" in e and "branch" in e
        for e in errors
    )


def test_state_mutation_testing_object_not_a_mapping_fails(tmp_path: Path) -> None:
    """L135: the wrapping `mutation_testing:` value itself must be a mapping."""
    meta = _valid_meta()
    meta["initial_state"]["mutation_testing"] = "broken"
    log = _write_log(tmp_path, meta=meta)
    errors = lint_log.lint(log)
    assert any(
        "initial_state.mutation_testing must be a mapping" in e for e in errors
    )


def test_state_mutation_testing_missing_key_fails(tmp_path: Path) -> None:
    meta = _valid_meta()
    del meta["initial_state"]["mutation_testing"]["kill_rate"]
    log = _write_log(tmp_path, meta=meta)
    errors = lint_log.lint(log)
    assert any(
        "initial_state.mutation_testing missing keys" in e
        and "kill_rate" in e
        for e in errors
    )


# ---------------------------------------------------------------------------
# rerun_type enforcement when status is completed
# ---------------------------------------------------------------------------


def test_completed_status_without_rerun_type_fails(tmp_path: Path) -> None:
    meta = _valid_meta()
    del meta["final_state"]["mutation_testing"]["rerun_type"]
    log = _write_log(tmp_path, meta=meta)
    errors = lint_log.lint(log)
    assert any("rerun_type must be" in e for e in errors)


def test_completed_status_with_invalid_rerun_type_fails(tmp_path: Path) -> None:
    meta = _valid_meta()
    meta["final_state"]["mutation_testing"]["rerun_type"] = "partial"
    log = _write_log(tmp_path, meta=meta)
    errors = lint_log.lint(log)
    assert any("rerun_type must be" in e for e in errors)


def test_completed_status_with_survivor_focused_rerun_type_passes(
    tmp_path: Path,
) -> None:
    meta = _valid_meta()
    meta["final_state"]["mutation_testing"]["rerun_type"] = "survivor_focused"
    log = _write_log(tmp_path, meta=meta)
    assert lint_log.lint(log) == []


# ---------------------------------------------------------------------------
# Required section headings (order matters)
# ---------------------------------------------------------------------------


def test_missing_required_section_fails(tmp_path: Path) -> None:
    body = _valid_body().replace("## Fix plan\nplaceholder content.\n", "")
    log = _write_log(tmp_path, body=body)
    errors = lint_log.lint(log)
    assert any("missing required section: '## Fix plan'" in e for e in errors)


def test_all_required_sections_present_passes(tmp_path: Path) -> None:
    assert lint_log.lint(_write_log(tmp_path)) == []


def test_sections_out_of_order_fails(tmp_path: Path) -> None:
    # Swap two adjacent required sections to force an out-of-order failure.
    reordered = list(REQUIRED_SECTIONS_ORDER)
    reordered[0], reordered[1] = reordered[1], reordered[0]
    body_lines = []
    for header in reordered:
        body_lines.append(f"## {header}")
        body_lines.append("placeholder content.")
        body_lines.append("")
    log = _write_log(tmp_path, body="\n".join(body_lines))
    errors = lint_log.lint(log)
    assert any("out of order" in e for e in errors)


# ---------------------------------------------------------------------------
# main() entry point exit codes
# ---------------------------------------------------------------------------


def test_main_returns_zero_for_valid_log(tmp_path: Path) -> None:
    log = _write_log(tmp_path)
    assert lint_log.main([str(log)]) == 0


def test_main_returns_one_for_invalid_log(tmp_path: Path) -> None:
    log = _write_log(tmp_path, name="pr-bad-name.md")
    assert lint_log.main([str(log)]) == 1

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
"""Tests for ``.devin/mutation-testing/scripts/lint_log.py``.

These tests cover the validator's checks: filename pattern, YAML front
matter shape, status values, required section headings, and the
completed-state ``rerun_type`` rule.
"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType

import pytest

DEFAULT_TRIAGE = {
    "coverage_level": "good",
    "foundation_needed": False,
    "deselected_tests": [],
}
DEFAULT_TARGET = {
    "behavior": ["x"],
    "implementation_files": ["a.py"],
    "test_files": ["t.py"],
}
DEFAULT_STATE = {
    "targeted_tests": {"command": "pytest -q", "passed": 1, "failed": 0},
    "coverage": {
        "line": {"percent": 100, "covered": 1, "total": 1},
        "branch": {"percent": 100, "covered": 1, "total": 1},
    },
    "mutation_testing": {
        "valid_mutations": 1,
        "killed": 1,
        "survived": 0,
        "kill_rate": 100,
    },
}

REQUIRED_BODY_SECTIONS = [
    "PR understanding",
    "Triage decision",
    "Initial targeted coverage",
    "Weak spot analysis",
    "Initial mutation plan",
    "Initial mutation results",
    "Fix plan",
    "Changes made",
    "Final verification",
    "Final assessment",
    "What's left for high-quality coverage",
    "Mutation quality self-assessment",
]


def _yaml_dump(meta: dict) -> str:
    import yaml

    return yaml.safe_dump(meta, sort_keys=False)


def _make_meta(**overrides) -> dict:
    final_state = dict(DEFAULT_STATE)
    final_state["mutation_testing"] = {
        **DEFAULT_STATE["mutation_testing"],
        "rerun_type": "full",
    }
    meta = {
        "pr_id": 28,
        "pr_title": "demo",
        "run_date": "2026-05-13",
        "agent": "devin",
        "repo": "loic-cunningham/superset",
        "branch": "devin/x",
        "base_branch": "master",
        "mode": "mutation-testing-and-test-improvement",
        "status": "completed",
        "triage": DEFAULT_TRIAGE,
        "target": DEFAULT_TARGET,
        "initial_state": DEFAULT_STATE,
        "final_state": final_state,
        "commits": ["deadbeef"],
        "artifacts": {"pr_comment_url": "https://example/c/1"},
    }
    meta.update(overrides)
    return meta


def _make_body(sections: list[str] | None = None) -> str:
    sections = REQUIRED_BODY_SECTIONS if sections is None else sections
    return "# Log\n\n" + "\n".join(f"## {s}\n\nbody\n" for s in sections)


def _write_log(
    tmp_path: Path,
    *,
    filename: str = "pr-28-2026-05-13-demo.md",
    meta: dict | None = None,
    body: str | None = None,
    raw_front_matter: str | None = None,
) -> Path:
    meta = meta if meta is not None else _make_meta()
    body = body if body is not None else _make_body()
    front = raw_front_matter if raw_front_matter is not None else _yaml_dump(meta)
    path = tmp_path / filename
    path.write_text(f"---\n{front}---\n{body}")
    return path


def test_lint_accepts_valid_completed_log(
    lint_log_module: ModuleType, tmp_path: Path
) -> None:
    path = _write_log(tmp_path)
    assert lint_log_module.lint(path) == []


def test_lint_rejects_bad_filename(
    lint_log_module: ModuleType, tmp_path: Path
) -> None:
    path = _write_log(tmp_path, filename="not-a-pr-log.md")
    errors = lint_log_module.lint(path)
    assert any("does not match pattern" in e for e in errors)


def test_lint_filename_requires_iso_date(
    lint_log_module: ModuleType, tmp_path: Path
) -> None:
    path = _write_log(tmp_path, filename="pr-28-20260513-demo.md")
    errors = lint_log_module.lint(path)
    assert any("does not match pattern" in e for e in errors)


def test_lint_filename_slug_must_start_alphanumeric(
    lint_log_module: ModuleType, tmp_path: Path
) -> None:
    path = _write_log(tmp_path, filename="pr-28-2026-05-13--leading-dash.md")
    errors = lint_log_module.lint(path)
    assert any("does not match pattern" in e for e in errors)


def test_lint_missing_file(
    lint_log_module: ModuleType, tmp_path: Path
) -> None:
    errors = lint_log_module.lint(tmp_path / "pr-28-2026-05-13-missing.md")
    assert errors == [
        f"file does not exist: {tmp_path / 'pr-28-2026-05-13-missing.md'}"
    ]


def test_lint_rejects_missing_front_matter(
    lint_log_module: ModuleType, tmp_path: Path
) -> None:
    path = tmp_path / "pr-28-2026-05-13-demo.md"
    path.write_text("# Just a body\n\n## PR understanding\n")
    errors = lint_log_module.lint(path)
    assert any("YAML front matter not found" in e for e in errors)


def test_lint_rejects_unparseable_front_matter(
    lint_log_module: ModuleType, tmp_path: Path
) -> None:
    bad_yaml = "pr_id: 1\n  bad_indent: oops\n"
    path = _write_log(tmp_path, raw_front_matter=bad_yaml)
    errors = lint_log_module.lint(path)
    assert any("not parseable" in e for e in errors)


def test_lint_rejects_non_mapping_front_matter(
    lint_log_module: ModuleType, tmp_path: Path
) -> None:
    path = _write_log(tmp_path, raw_front_matter="- just\n- a\n- list\n")
    errors = lint_log_module.lint(path)
    assert any("must be a mapping" in e for e in errors)


def test_lint_reports_missing_top_keys(
    lint_log_module: ModuleType, tmp_path: Path
) -> None:
    meta = _make_meta()
    meta.pop("commits")
    meta.pop("artifacts")
    path = _write_log(tmp_path, meta=meta)
    errors = lint_log_module.lint(path)
    assert any(
        "YAML missing keys" in e and "commits" in e and "artifacts" in e
        for e in errors
    )


def test_lint_rejects_invalid_status(
    lint_log_module: ModuleType, tmp_path: Path
) -> None:
    meta = _make_meta(status="done")
    path = _write_log(tmp_path, meta=meta)
    errors = lint_log_module.lint(path)
    assert any("status must be in_progress|completed" in e for e in errors)


def test_lint_accepts_in_progress_status(
    lint_log_module: ModuleType, tmp_path: Path
) -> None:
    meta = _make_meta(status="in_progress")
    path = _write_log(tmp_path, meta=meta)
    assert lint_log_module.lint(path) == []


def test_lint_rejects_non_mapping_state(
    lint_log_module: ModuleType, tmp_path: Path
) -> None:
    meta = _make_meta(initial_state="not a mapping")
    path = _write_log(tmp_path, meta=meta)
    errors = lint_log_module.lint(path)
    assert any("initial_state must be a mapping" in e for e in errors)


def test_lint_reports_missing_state_subkeys(
    lint_log_module: ModuleType, tmp_path: Path
) -> None:
    meta = _make_meta(initial_state={"targeted_tests": {}})
    path = _write_log(tmp_path, meta=meta)
    errors = lint_log_module.lint(path)
    assert any(
        "initial_state missing keys" in e
        and "coverage" in e
        and "mutation_testing" in e
        for e in errors
    )


def test_lint_reports_missing_coverage_axis_keys(
    lint_log_module: ModuleType, tmp_path: Path
) -> None:
    state = {
        "targeted_tests": {},
        "coverage": {
            "line": {"percent": 50, "covered": 5},
            "branch": {"percent": 50, "covered": 5, "total": 10},
        },
        "mutation_testing": DEFAULT_STATE["mutation_testing"],
    }
    meta = _make_meta(initial_state=state)
    path = _write_log(tmp_path, meta=meta)
    errors = lint_log_module.lint(path)
    assert any(
        "initial_state.coverage.line missing keys" in e and "total" in e
        for e in errors
    )


def test_lint_reports_non_mapping_coverage(
    lint_log_module: ModuleType, tmp_path: Path
) -> None:
    state = {
        "targeted_tests": {},
        "coverage": "nope",
        "mutation_testing": DEFAULT_STATE["mutation_testing"],
    }
    meta = _make_meta(initial_state=state)
    path = _write_log(tmp_path, meta=meta)
    errors = lint_log_module.lint(path)
    assert any("initial_state.coverage must be a mapping" in e for e in errors)


def test_lint_reports_missing_mutation_testing_keys(
    lint_log_module: ModuleType, tmp_path: Path
) -> None:
    state = {
        "targeted_tests": {},
        "coverage": DEFAULT_STATE["coverage"],
        "mutation_testing": {"valid_mutations": 1, "killed": 1},
    }
    meta = _make_meta(initial_state=state)
    path = _write_log(tmp_path, meta=meta)
    errors = lint_log_module.lint(path)
    assert any(
        "initial_state.mutation_testing missing keys" in e
        and "survived" in e
        and "kill_rate" in e
        for e in errors
    )


def test_lint_requires_rerun_type_when_completed(
    lint_log_module: ModuleType, tmp_path: Path
) -> None:
    meta = _make_meta()
    meta["final_state"] = {
        **DEFAULT_STATE,
        "mutation_testing": DEFAULT_STATE["mutation_testing"],  # no rerun_type
    }
    path = _write_log(tmp_path, meta=meta)
    errors = lint_log_module.lint(path)
    assert any(
        "rerun_type must be 'full' or 'survivor_focused'" in e for e in errors
    )


def test_lint_in_progress_does_not_require_rerun_type(
    lint_log_module: ModuleType, tmp_path: Path
) -> None:
    meta = _make_meta(status="in_progress")
    meta["final_state"] = {
        **DEFAULT_STATE,
        "mutation_testing": DEFAULT_STATE["mutation_testing"],
    }
    path = _write_log(tmp_path, meta=meta)
    assert lint_log_module.lint(path) == []


@pytest.mark.parametrize("rerun_type", ["full", "survivor_focused"])
def test_lint_accepts_known_rerun_types(
    lint_log_module: ModuleType, tmp_path: Path, rerun_type: str
) -> None:
    meta = _make_meta()
    meta["final_state"] = {
        **DEFAULT_STATE,
        "mutation_testing": {
            **DEFAULT_STATE["mutation_testing"],
            "rerun_type": rerun_type,
        },
    }
    path = _write_log(tmp_path, meta=meta)
    assert lint_log_module.lint(path) == []


@pytest.mark.parametrize("missing_section", REQUIRED_BODY_SECTIONS)
def test_lint_requires_every_section_heading(
    lint_log_module: ModuleType,
    tmp_path: Path,
    missing_section: str,
) -> None:
    sections = [s for s in REQUIRED_BODY_SECTIONS if s != missing_section]
    body = _make_body(sections)
    path = _write_log(tmp_path, body=body)
    errors = lint_log_module.lint(path)
    assert any(
        f"missing required section: '## {missing_section}'" in e for e in errors
    )


def test_lint_weak_spot_analysis_is_required(
    lint_log_module: ModuleType, tmp_path: Path
) -> None:
    """``Weak spot analysis`` was added by PR #28 and must be enforced."""
    sections = [s for s in REQUIRED_BODY_SECTIONS if s != "Weak spot analysis"]
    body = _make_body(sections)
    path = _write_log(tmp_path, body=body)
    errors = lint_log_module.lint(path)
    assert any("Weak spot analysis" in e for e in errors)


def test_lint_mutation_quality_self_assessment_is_required(
    lint_log_module: ModuleType, tmp_path: Path
) -> None:
    """``Mutation quality self-assessment`` was added by PR #28."""
    sections = [
        s for s in REQUIRED_BODY_SECTIONS if s != "Mutation quality self-assessment"
    ]
    body = _make_body(sections)
    path = _write_log(tmp_path, body=body)
    errors = lint_log_module.lint(path)
    assert any("Mutation quality self-assessment" in e for e in errors)


def test_lint_detects_out_of_order_sections(
    lint_log_module: ModuleType, tmp_path: Path
) -> None:
    # Swap two required sections so order is violated.
    sections = REQUIRED_BODY_SECTIONS.copy()
    sections[0], sections[1] = sections[1], sections[0]
    body = _make_body(sections)
    path = _write_log(tmp_path, body=body)
    errors = lint_log_module.lint(path)
    assert any("is out of order" in e for e in errors)


def test_main_returns_zero_for_clean_log(
    lint_log_module: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _write_log(tmp_path)
    assert lint_log_module.main([str(path)]) == 0
    captured = capsys.readouterr()
    assert "OK" in captured.out


def test_main_returns_one_and_reports_each_error(
    lint_log_module: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    meta = _make_meta(status="done")
    path = _write_log(tmp_path, meta=meta)
    assert lint_log_module.main([str(path)]) == 1
    captured = capsys.readouterr()
    assert "FAIL" in captured.err
    assert "status must be in_progress|completed" in captured.err


def test_main_handles_multiple_paths(
    lint_log_module: ModuleType, tmp_path: Path
) -> None:
    good = _write_log(tmp_path, filename="pr-28-2026-05-13-good.md")
    bad = _write_log(
        tmp_path,
        filename="pr-29-2026-05-13-bad.md",
        meta=_make_meta(status="done"),
    )
    assert lint_log_module.main([str(good), str(bad)]) == 1

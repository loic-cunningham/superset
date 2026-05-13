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
Tests for mutation_runner.py — apply/run/restore engine.

The pure-Python helpers (`_apply_indent`, `_apply_mutation`,
`_parse_pytest_output`, `_classify`, `MutationResult.to_dict`) are exercised
directly. The subprocess + git boundary (`_run_one`, `main`) is exercised
through monkeypatched fakes so the tests never shell out.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import mutation_runner  # type: ignore[import-not-found]  # loaded via conftest


# ---------------------------------------------------------------------------
# _apply_indent
# ---------------------------------------------------------------------------


def test_apply_indent_zero_returns_text_unchanged() -> None:
    assert mutation_runner._apply_indent("hello\nworld\n", 0) == "hello\nworld\n"


def test_apply_indent_prefixes_non_empty_lines() -> None:
    out = mutation_runner._apply_indent("a\nb\n", 4)
    assert out == "    a\n    b\n"


def test_apply_indent_preserves_empty_lines() -> None:
    out = mutation_runner._apply_indent("a\n\nb\n", 2)
    # The middle blank line stays blank — no trailing whitespace added.
    assert out == "  a\n\n  b\n"


def test_apply_indent_handles_trailing_newline() -> None:
    out = mutation_runner._apply_indent("only\n", 3)
    assert out == "   only\n"


# ---------------------------------------------------------------------------
# _apply_mutation
# ---------------------------------------------------------------------------


@pytest.fixture
def repo_root_at_tmp(tmp_path: Path, monkeypatch) -> Path:
    """Point REPO_ROOT at tmp_path so relative_to() succeeds in error messages."""
    monkeypatch.setattr(mutation_runner, "REPO_ROOT", tmp_path)
    return tmp_path


def test_apply_mutation_replaces_unique_old(repo_root_at_tmp: Path) -> None:
    p = repo_root_at_tmp / "f.py"
    p.write_text("alpha\nbeta\ngamma\n")
    mutation_runner._apply_mutation(p, old="beta\n", new="BETA\n", indent=0)
    assert p.read_text() == "alpha\nBETA\ngamma\n"


def test_apply_mutation_aborts_when_old_not_found(repo_root_at_tmp: Path) -> None:
    p = repo_root_at_tmp / "f.py"
    p.write_text("alpha\n")
    with pytest.raises(RuntimeError, match="not found"):
        mutation_runner._apply_mutation(p, old="missing\n", new="X\n")


def test_apply_mutation_aborts_when_old_not_unique(repo_root_at_tmp: Path) -> None:
    p = repo_root_at_tmp / "f.py"
    p.write_text("dup\ndup\n")
    with pytest.raises(RuntimeError, match="must be unique"):
        mutation_runner._apply_mutation(p, old="dup\n", new="X\n")


def test_apply_mutation_respects_indent(repo_root_at_tmp: Path) -> None:
    p = repo_root_at_tmp / "f.py"
    p.write_text("    block_open\n    block_close\n")
    mutation_runner._apply_mutation(
        p, old="block_open\n", new="BLOCK_OPEN\n", indent=4
    )
    assert p.read_text() == "    BLOCK_OPEN\n    block_close\n"


# ---------------------------------------------------------------------------
# _parse_pytest_output
# ---------------------------------------------------------------------------


def test_parse_pytest_output_extracts_passed_only() -> None:
    out = "....\n12 passed in 0.5s\n"
    passed, failed, first = mutation_runner._parse_pytest_output(out)
    assert passed == 12
    assert failed == 0
    assert first is None


def test_parse_pytest_output_extracts_passed_and_failed() -> None:
    out = (
        "FAILED tests/x.py::test_alpha - assert 1 == 2\n"
        "10 passed, 2 failed in 0.5s\n"
    )
    passed, failed, first = mutation_runner._parse_pytest_output(out)
    assert (passed, failed) == (10, 2)
    assert first == "tests/x.py::test_alpha"


def test_parse_pytest_output_counts_errors_as_failures() -> None:
    out = "1 passed, 2 errors in 0.5s\n"
    passed, failed, first = mutation_runner._parse_pytest_output(out)
    # Errors must be counted as failures so a crashing mutation classifies KILLED.
    assert passed == 1
    assert failed == 2


def test_parse_pytest_output_counts_failed_and_errors_together() -> None:
    out = "3 passed, 1 failed, 1 error in 0.5s\n"
    passed, failed, first = mutation_runner._parse_pytest_output(out)
    assert passed == 3
    # 1 failed + 1 error = 2 reported failures.
    assert failed == 2


def test_parse_pytest_output_first_failing_is_first_match() -> None:
    out = (
        "FAILED tests/a.py::test_one\n"
        "FAILED tests/b.py::test_two\n"
        "0 passed, 2 failed in 0.5s\n"
    )
    _, _, first = mutation_runner._parse_pytest_output(out)
    assert first == "tests/a.py::test_one"


def test_parse_pytest_output_handles_empty_output() -> None:
    passed, failed, first = mutation_runner._parse_pytest_output("")
    assert (passed, failed) == (0, 0)
    assert first is None


# ---------------------------------------------------------------------------
# _classify
# ---------------------------------------------------------------------------


def test_classify_returns_killed_when_any_failure() -> None:
    assert mutation_runner._classify(passed=5, failed=1) == "killed"


def test_classify_returns_survived_when_only_passing() -> None:
    assert mutation_runner._classify(passed=5, failed=0) == "survived"


def test_classify_returns_error_when_no_passes_no_failures() -> None:
    # No tests ran (mutation broke collection) -> error, not survived.
    assert mutation_runner._classify(passed=0, failed=0) == "error"


# ---------------------------------------------------------------------------
# MutationResult.to_dict
# ---------------------------------------------------------------------------


def test_mutation_result_to_dict_contains_all_fields() -> None:
    r = mutation_runner.MutationResult(
        id="M1",
        description="d",
        file="f.py",
        status="killed",
        passed=5,
        failed=1,
        first_failing_test="tests/x.py::t",
    )
    d = r.to_dict()
    assert d == {
        "id": "M1",
        "description": "d",
        "file": "f.py",
        "status": "killed",
        "passed": 5,
        "failed": 1,
        "first_failing_test": "tests/x.py::t",
        "error": None,
    }


# ---------------------------------------------------------------------------
# _run_one — boundary integration with fake git + pytest
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_repo(tmp_path: Path, monkeypatch) -> Path:
    """Monkeypatch REPO_ROOT and git/test calls onto a tmp_path checkout."""
    target = tmp_path / "src" / "thing.py"
    target.parent.mkdir(parents=True)
    target.write_text("flag = True\n")

    monkeypatch.setattr(mutation_runner, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(mutation_runner, "_assert_tree_clean", lambda paths: None)

    def fake_restore(paths):
        # Truthful restore: re-write the original content.
        target.write_text("flag = True\n")

    monkeypatch.setattr(mutation_runner, "_restore", fake_restore)
    return tmp_path


def test_run_one_killed_status_when_tests_fail(fake_repo, monkeypatch) -> None:
    monkeypatch.setattr(
        mutation_runner,
        "_run_tests",
        lambda test_paths: (3, 1, "tests/x.py::t"),
    )
    mutation = {
        "id": "M1",
        "description": "flip flag",
        "file": "src/thing.py",
        "old": "flag = True\n",
        "new": "flag = False\n",
    }
    result = mutation_runner._run_one(
        mutation, ["tests/x.py"], ["src/thing.py"]
    )
    assert result.status == "killed"
    assert result.first_failing_test == "tests/x.py::t"
    # Tree restored to original content.
    assert (fake_repo / "src" / "thing.py").read_text() == "flag = True\n"


def test_run_one_survived_status_when_tests_pass(fake_repo, monkeypatch) -> None:
    monkeypatch.setattr(
        mutation_runner, "_run_tests", lambda test_paths: (3, 0, None)
    )
    mutation = {
        "id": "M2",
        "description": "noop",
        "file": "src/thing.py",
        "old": "flag = True\n",
        "new": "flag = False\n",
    }
    result = mutation_runner._run_one(
        mutation, ["tests/x.py"], ["src/thing.py"]
    )
    assert result.status == "survived"


def test_run_one_error_when_old_string_missing(fake_repo, monkeypatch) -> None:
    monkeypatch.setattr(
        mutation_runner, "_run_tests", lambda test_paths: (0, 0, None)
    )
    mutation = {
        "id": "M3",
        "description": "broken",
        "file": "src/thing.py",
        "old": "absent_token\n",
        "new": "anything\n",
    }
    result = mutation_runner._run_one(
        mutation, ["tests/x.py"], ["src/thing.py"]
    )
    assert result.status == "error"
    assert "not found" in (result.error or "")


def test_run_one_error_when_target_file_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(mutation_runner, "REPO_ROOT", tmp_path)
    mutation = {
        "id": "Mx",
        "description": "missing",
        "file": "src/missing.py",
        "old": "x",
        "new": "y",
    }
    result = mutation_runner._run_one(mutation, ["tests/x.py"], ["src/missing.py"])
    assert result.status == "error"
    assert "file not found" in (result.error or "")


# ---------------------------------------------------------------------------
# main() — end-to-end through monkeypatched _run_one
# ---------------------------------------------------------------------------


def _write_spec(tmp_path: Path, mutations: list[dict]) -> Path:
    import yaml

    spec = {
        "targets": [{"path": "src/thing.py"}],
        "test_paths": ["tests/x.py"],
        "mutations": mutations,
    }
    p = tmp_path / "spec.yaml"
    p.write_text(yaml.safe_dump(spec))
    return p


def test_main_writes_results_json(tmp_path: Path, monkeypatch, capsys) -> None:
    spec = _write_spec(
        tmp_path,
        [
            {
                "id": "M1",
                "description": "kill me",
                "file": "src/thing.py",
                "old": "x",
                "new": "y",
            },
            {
                "id": "M2",
                "description": "survive",
                "file": "src/thing.py",
                "old": "x",
                "new": "y",
            },
        ],
    )

    def fake_run_one(mutation, test_paths, target_paths):
        status = "killed" if mutation["id"] == "M1" else "survived"
        return mutation_runner.MutationResult(
            id=mutation["id"],
            description=mutation["description"],
            file=mutation["file"],
            status=status,
            passed=1,
            failed=1 if status == "killed" else 0,
            first_failing_test="t::a" if status == "killed" else None,
        )

    monkeypatch.setattr(mutation_runner, "_run_one", fake_run_one)
    results_path = tmp_path / "results.json"
    rc = mutation_runner.main([str(spec), "--results", str(results_path)])
    assert rc == 0
    data = json.loads(results_path.read_text())
    assert data["killed"] == 1
    assert data["survived"] == 1
    assert data["errored"] == 0
    # 1/2 valid mutations killed -> 50%.
    assert data["kill_rate"] == 50
    assert [r["id"] for r in data["results"]] == ["M1", "M2"]


def test_main_only_filter_runs_matching_mutations(
    tmp_path: Path, monkeypatch
) -> None:
    spec = _write_spec(
        tmp_path,
        [
            {
                "id": "M1",
                "description": "a",
                "file": "src/thing.py",
                "old": "x",
                "new": "y",
            },
            {
                "id": "M2",
                "description": "b",
                "file": "src/thing.py",
                "old": "x",
                "new": "y",
            },
        ],
    )
    seen: list[str] = []

    def fake_run_one(mutation, test_paths, target_paths):
        seen.append(mutation["id"])
        return mutation_runner.MutationResult(
            id=mutation["id"],
            description=mutation["description"],
            file=mutation["file"],
            status="killed",
            passed=1,
            failed=1,
            first_failing_test=None,
        )

    monkeypatch.setattr(mutation_runner, "_run_one", fake_run_one)
    results_path = tmp_path / "results.json"
    rc = mutation_runner.main(
        [str(spec), "--only", "M2", "--results", str(results_path)]
    )
    assert rc == 0
    assert seen == ["M2"]


def test_main_returns_two_on_invalid_spec(tmp_path: Path) -> None:
    import yaml

    p = tmp_path / "broken.yaml"
    p.write_text(yaml.safe_dump({"targets": [], "mutations": []}))  # no test_paths
    rc = mutation_runner.main([str(p)])
    assert rc == 2


def test_main_stops_on_error_without_continue_flag(
    tmp_path: Path, monkeypatch
) -> None:
    spec = _write_spec(
        tmp_path,
        [
            {
                "id": "Mx",
                "description": "error",
                "file": "src/thing.py",
                "old": "x",
                "new": "y",
            },
            {
                "id": "My",
                "description": "ok",
                "file": "src/thing.py",
                "old": "x",
                "new": "y",
            },
        ],
    )

    def fake_run_one(mutation, test_paths, target_paths):
        if mutation["id"] == "Mx":
            return mutation_runner.MutationResult(
                id="Mx",
                description="error",
                file="src/thing.py",
                status="error",
                passed=0,
                failed=0,
                first_failing_test=None,
                error="boom",
            )
        return mutation_runner.MutationResult(
            id=mutation["id"],
            description="ok",
            file="src/thing.py",
            status="killed",
            passed=1,
            failed=1,
            first_failing_test=None,
        )

    monkeypatch.setattr(mutation_runner, "_run_one", fake_run_one)
    results_path = tmp_path / "results.json"
    rc = mutation_runner.main([str(spec), "--results", str(results_path)])
    # Non-zero exit because an error happened.
    assert rc == 1
    data = json.loads(results_path.read_text())
    # Without --continue-on-error, run aborted after the first error.
    assert [r["id"] for r in data["results"]] == ["Mx"]
    assert data["errored"] == 1


def test_main_continue_on_error_runs_remaining(
    tmp_path: Path, monkeypatch
) -> None:
    spec = _write_spec(
        tmp_path,
        [
            {
                "id": "Mx",
                "description": "err",
                "file": "src/thing.py",
                "old": "x",
                "new": "y",
            },
            {
                "id": "My",
                "description": "ok",
                "file": "src/thing.py",
                "old": "x",
                "new": "y",
            },
        ],
    )

    def fake_run_one(mutation, test_paths, target_paths):
        if mutation["id"] == "Mx":
            return mutation_runner.MutationResult(
                id="Mx",
                description="err",
                file="src/thing.py",
                status="error",
                passed=0,
                failed=0,
                first_failing_test=None,
                error="boom",
            )
        return mutation_runner.MutationResult(
            id=mutation["id"],
            description="ok",
            file="src/thing.py",
            status="killed",
            passed=1,
            failed=1,
            first_failing_test=None,
        )

    monkeypatch.setattr(mutation_runner, "_run_one", fake_run_one)
    results_path = tmp_path / "results.json"
    rc = mutation_runner.main(
        [str(spec), "--continue-on-error", "--results", str(results_path)]
    )
    assert rc == 1  # error still produces non-zero exit
    data = json.loads(results_path.read_text())
    assert [r["id"] for r in data["results"]] == ["Mx", "My"]

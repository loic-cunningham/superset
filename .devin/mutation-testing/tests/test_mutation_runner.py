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
"""Tests for ``.devin/mutation-testing/scripts/mutation_runner.py``.

These exercise the pure helpers (``_apply_indent``, ``_apply_mutation``,
``_parse_pytest_output``, ``_classify``) and the JSON output shape produced
by ``main`` when ``--results`` is passed. They stay focused: the script's
real subprocess work (running ``run_targeted.sh``) is mocked through
``_run_tests`` so the tests do not require the Superset venv to behave a
particular way.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import ModuleType

import pytest


def test_apply_indent_zero_is_identity(mutation_runner_module: ModuleType) -> None:
    assert mutation_runner_module._apply_indent("hello\nworld\n", 0) == "hello\nworld\n"


def test_apply_indent_prepends_n_spaces_per_line(
    mutation_runner_module: ModuleType,
) -> None:
    text = "a\nb\nc"
    assert mutation_runner_module._apply_indent(text, 4) == "    a\n    b\n    c"


def test_apply_indent_skips_empty_lines(mutation_runner_module: ModuleType) -> None:
    """Empty lines must stay empty so YAML's trailing newline is preserved."""
    text = "a\n\nb\n"
    assert mutation_runner_module._apply_indent(text, 2) == "  a\n\n  b\n"


def test_apply_mutation_replaces_unique_match(
    mutation_runner_module: ModuleType, tmp_path: Path
) -> None:
    path = tmp_path / "src.py"
    path.write_text("alpha = 1\nbeta = 2\ngamma = 3\n")
    mutation_runner_module._apply_mutation(path, "beta = 2", "beta = 99")
    assert path.read_text() == "alpha = 1\nbeta = 99\ngamma = 3\n"


def test_apply_mutation_indent_aware(
    mutation_runner_module: ModuleType, tmp_path: Path
) -> None:
    path = tmp_path / "src.py"
    path.write_text("def f():\n    x = 1\n    y = 2\n")
    mutation_runner_module._apply_mutation(
        path, "y = 2\n", "y = 999\n", indent=4
    )
    assert path.read_text() == "def f():\n    x = 1\n    y = 999\n"


def test_apply_mutation_raises_when_old_string_missing(
    mutation_runner_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(mutation_runner_module, "REPO_ROOT", tmp_path)
    path = tmp_path / "src.py"
    original = "alpha = 1\n"
    path.write_text(original)
    with pytest.raises(RuntimeError, match="not found"):
        mutation_runner_module._apply_mutation(path, "beta = 2", "beta = 99")
    # The file must not be touched on failure.
    assert path.read_text() == original


def test_apply_mutation_raises_when_old_string_not_unique(
    mutation_runner_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(mutation_runner_module, "REPO_ROOT", tmp_path)
    path = tmp_path / "src.py"
    original = "x = 1\nx = 1\n"
    path.write_text(original)
    with pytest.raises(RuntimeError, match="appears 2 times"):
        mutation_runner_module._apply_mutation(path, "x = 1", "x = 2")
    assert path.read_text() == original


def test_parse_pytest_output_extracts_pass_and_fail_counts(
    mutation_runner_module: ModuleType,
) -> None:
    stdout = (
        "FAILED tests/foo.py::test_a - AssertionError\n"
        "FAILED tests/foo.py::test_b - AssertionError\n"
        "= 5 passed, 2 failed in 0.42s ="
    )
    passed, failed, first = mutation_runner_module._parse_pytest_output(stdout)
    assert (passed, failed) == (5, 2)
    assert first == "tests/foo.py::test_a"


def test_parse_pytest_output_counts_errors_as_failures(
    mutation_runner_module: ModuleType,
) -> None:
    stdout = "= 0 passed, 3 errors in 0.10s ="
    passed, failed, first = mutation_runner_module._parse_pytest_output(stdout)
    assert (passed, failed) == (0, 3)
    assert first is None


def test_parse_pytest_output_handles_passed_only(
    mutation_runner_module: ModuleType,
) -> None:
    stdout = "= 17 passed in 0.05s ="
    passed, failed, first = mutation_runner_module._parse_pytest_output(stdout)
    assert (passed, failed) == (17, 0)
    assert first is None


def test_parse_pytest_output_returns_zeros_when_summary_missing(
    mutation_runner_module: ModuleType,
) -> None:
    stdout = "something happened\nbut no summary line\n"
    assert mutation_runner_module._parse_pytest_output(stdout) == (0, 0, None)


def test_parse_pytest_output_first_failing_must_use_uppercase_failed(
    mutation_runner_module: ModuleType,
) -> None:
    """Only ``FAILED`` (uppercase) lines should contribute the failing test."""
    stdout = (
        "failed: nope\n"
        "FAILED tests/bar.py::test_real - AssertionError\n"
        "= 1 passed, 1 failed in 0.01s ="
    )
    _, _, first = mutation_runner_module._parse_pytest_output(stdout)
    assert first == "tests/bar.py::test_real"


@pytest.mark.parametrize(
    "passed,failed,expected",
    [
        (5, 0, "survived"),
        (5, 1, "killed"),
        (0, 1, "killed"),
        (0, 0, "error"),
    ],
)
def test_classify_obeys_priority_rules(
    mutation_runner_module: ModuleType,
    passed: int,
    failed: int,
    expected: str,
) -> None:
    assert mutation_runner_module._classify(passed, failed) == expected


def test_mutation_result_to_dict_round_trip(
    mutation_runner_module: ModuleType,
) -> None:
    result = mutation_runner_module.MutationResult(
        id="M1",
        description="d",
        file="f.py",
        status="killed",
        passed=2,
        failed=1,
        first_failing_test="t::a",
    )
    payload = result.to_dict()
    assert payload["status"] == "killed"
    assert payload["first_failing_test"] == "t::a"
    assert payload["error"] is None


def test_main_writes_results_json_with_kill_rate(
    mutation_runner_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Drive main() end-to-end with run_tests/restore/clean stubbed out."""
    monkeypatch.setattr(mutation_runner_module, "REPO_ROOT", tmp_path)
    src = tmp_path / "src.py"
    src.write_text("ORIG\n")
    spec = tmp_path / "spec.yaml"
    spec.write_text(
        "test_paths:\n"
        "  - dummy/path.py\n"
        "mutations:\n"
        "  - id: M1\n"
        f"    file: {src}\n"
        "    old: ORIG\n"
        "    new: MUT_A\n"
        "  - id: M2\n"
        f"    file: {src}\n"
        "    old: ORIG\n"
        "    new: MUT_B\n"
    )
    results_path = tmp_path / "results.json"

    runs = {"count": 0}

    def fake_run_tests(test_paths: list[str]):
        runs["count"] += 1
        # First mutation: killed (failed > 0). Second: survived.
        if runs["count"] == 1:
            return 3, 1, "tests/x.py::test_one"
        return 4, 0, None

    def fake_restore(paths: list[str]) -> None:
        src.write_text("ORIG\n")

    monkeypatch.setattr(mutation_runner_module, "_run_tests", fake_run_tests)
    monkeypatch.setattr(mutation_runner_module, "_assert_tree_clean", lambda paths: None)
    monkeypatch.setattr(mutation_runner_module, "_restore", fake_restore)

    rc = mutation_runner_module.main([str(spec), "--results", str(results_path)])
    assert rc == 0
    payload = json.loads(results_path.read_text())
    assert payload["killed"] == 1
    assert payload["survived"] == 1
    assert payload["errored"] == 0
    assert payload["kill_rate"] == 50
    ids = [r["id"] for r in payload["results"]]
    statuses = [r["status"] for r in payload["results"]]
    assert ids == ["M1", "M2"]
    assert statuses == ["killed", "survived"]
    assert payload["results"][0]["first_failing_test"] == "tests/x.py::test_one"


def test_main_only_filter_runs_selected_mutations(
    mutation_runner_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(mutation_runner_module, "REPO_ROOT", tmp_path)
    src = tmp_path / "src.py"
    src.write_text("ORIG\n")
    spec = tmp_path / "spec.yaml"
    spec.write_text(
        "test_paths:\n"
        "  - dummy/path.py\n"
        "mutations:\n"
        "  - id: M1\n"
        f"    file: {src}\n"
        "    old: ORIG\n"
        "    new: MUT_A\n"
        "  - id: M2\n"
        f"    file: {src}\n"
        "    old: ORIG\n"
        "    new: MUT_B\n"
    )
    results_path = tmp_path / "results.json"
    seen_ids: list[str] = []

    def fake_run_tests(_paths: list[str]):
        return 1, 0, None

    monkeypatch.setattr(mutation_runner_module, "_assert_tree_clean", lambda paths: None)
    monkeypatch.setattr(mutation_runner_module, "_restore", lambda paths: None)
    monkeypatch.setattr(mutation_runner_module, "_run_tests", fake_run_tests)

    orig_run_one = mutation_runner_module._run_one

    def tracking_run_one(mutation, test_paths, target_paths):
        seen_ids.append(mutation["id"])
        return orig_run_one(mutation, test_paths, target_paths)

    monkeypatch.setattr(mutation_runner_module, "_run_one", tracking_run_one)

    rc = mutation_runner_module.main(
        [str(spec), "--results", str(results_path), "--only", "M2"]
    )
    assert rc == 0
    assert seen_ids == ["M2"]
    payload = json.loads(results_path.read_text())
    assert [r["id"] for r in payload["results"]] == ["M2"]


def test_main_rejects_spec_missing_required_top_level_keys(
    mutation_runner_module: ModuleType,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    spec = tmp_path / "spec.yaml"
    spec.write_text("mutations: []\n")  # no test_paths
    rc = mutation_runner_module.main([str(spec)])
    assert rc == 2
    captured = capsys.readouterr()
    assert "spec must have 'mutations' and 'test_paths'" in captured.err


def test_run_one_returns_error_when_file_missing(
    mutation_runner_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(mutation_runner_module, "REPO_ROOT", tmp_path)
    result = mutation_runner_module._run_one(
        {"id": "M1", "file": str(tmp_path / "nope.py"), "old": "x", "new": "y"},
        test_paths=["t.py"],
        target_paths=[],
    )
    assert result.status == "error"
    assert result.error is not None and "file not found" in result.error

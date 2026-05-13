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
Tests for coverage_summary.py — pytest-cov JSON → mutation-testing-log JSON.

The pure data-shaping helpers (`_pct`, `_per_file_entries`) are exercised
directly. The subprocess-driven `main()` is exercised through the
`_run_pytest_with_coverage` boundary, which is monkeypatched to avoid
shelling out to pytest.
"""

from __future__ import annotations

import json
from pathlib import Path

import coverage_summary  # type: ignore[import-not-found]  # loaded via conftest


# ---------------------------------------------------------------------------
# _pct
# ---------------------------------------------------------------------------


def test_pct_rounds_half_to_even_or_up() -> None:
    # Built-in round uses banker's rounding; both 50.4 -> 50 and 49.6 -> 50.
    assert coverage_summary._pct(50.4) == 50
    assert coverage_summary._pct(49.6) == 50


def test_pct_returns_zero_for_zero() -> None:
    assert coverage_summary._pct(0) == 0


def test_pct_rounds_to_int() -> None:
    assert isinstance(coverage_summary._pct(33.3333), int)
    assert coverage_summary._pct(33.3333) == 33


# ---------------------------------------------------------------------------
# _per_file_entries
# ---------------------------------------------------------------------------


def _file_entry(
    *,
    percent_covered: float = 100.0,
    covered_lines: int = 5,
    num_statements: int = 5,
    num_branches: int | None = 4,
    covered_branches: int = 4,
    missing_lines: list[int] | None = None,
) -> dict:
    summary = {
        "percent_covered": percent_covered,
        "covered_lines": covered_lines,
        "num_statements": num_statements,
    }
    if num_branches is not None:
        summary["num_branches"] = num_branches
        summary["covered_branches"] = covered_branches
    return {
        "summary": summary,
        "missing_lines": missing_lines or [],
    }


def test_per_file_entries_sorted_by_path() -> None:
    cov_data = {
        "files": {
            "b.py": _file_entry(),
            "a.py": _file_entry(),
            "c.py": _file_entry(),
        }
    }
    paths = [e["path"] for e in coverage_summary._per_file_entries(cov_data)]
    assert paths == ["a.py", "b.py", "c.py"]


def test_per_file_entries_computes_branch_percent_when_branches_present() -> None:
    cov_data = {
        "files": {
            "a.py": _file_entry(num_branches=4, covered_branches=3),
        }
    }
    [entry] = coverage_summary._per_file_entries(cov_data)
    # 3/4 == 75
    assert entry["branch_percent"] == 75


def test_per_file_entries_branch_percent_none_when_no_branches() -> None:
    cov_data = {"files": {"a.py": _file_entry(num_branches=None)}}
    [entry] = coverage_summary._per_file_entries(cov_data)
    assert entry["branch_percent"] is None


def test_per_file_entries_includes_missing_lines_verbatim() -> None:
    cov_data = {
        "files": {
            "a.py": _file_entry(missing_lines=[10, 20, 30]),
        }
    }
    [entry] = coverage_summary._per_file_entries(cov_data)
    assert entry["missing_lines"] == [10, 20, 30]


def test_per_file_entries_line_percent_rounded() -> None:
    cov_data = {
        "files": {
            "a.py": _file_entry(percent_covered=83.6),
        }
    }
    [entry] = coverage_summary._per_file_entries(cov_data)
    assert entry["line_percent"] == 84


def test_per_file_entries_empty_files_returns_empty_list() -> None:
    assert coverage_summary._per_file_entries({"files": {}}) == []
    assert coverage_summary._per_file_entries({}) == []


# ---------------------------------------------------------------------------
# main() end-to-end with monkeypatched pytest runner
# ---------------------------------------------------------------------------


_FAKE_COV_DATA = {
    "totals": {
        "percent_covered": 87.5,
        "covered_lines": 7,
        "num_statements": 8,
        "covered_branches": 3,
        "num_branches": 4,
    },
    "files": {
        "a.py": {
            "summary": {
                "percent_covered": 90,
                "covered_lines": 9,
                "num_statements": 10,
                "covered_branches": 3,
                "num_branches": 4,
            },
            "missing_lines": [42],
        }
    },
}


def _patch_runner(monkeypatch, *, cov=_FAKE_COV_DATA, passed=12, failed=0) -> None:
    def fake(tests, cov_targets, extra_args):
        return passed, failed, cov, "pytest fake-cmd"

    monkeypatch.setattr(coverage_summary, "_run_pytest_with_coverage", fake)


def test_main_writes_expected_json_summary(tmp_path, monkeypatch) -> None:
    _patch_runner(monkeypatch)
    out = tmp_path / "summary.json"
    rc = coverage_summary.main(
        ["--tests", "tests/a.py", "--cov", "pkg.a", "--output", str(out)]
    )
    assert rc == 0
    data = json.loads(out.read_text())
    assert data["tests"] == {"passed": 12, "failed": 0}
    assert data["line"] == {"percent": 88, "covered": 7, "total": 8}
    assert data["branch"] == {"percent": 75, "covered": 3, "total": 4}
    assert data["per_file"][0]["path"] == "a.py"


def test_main_branch_block_zero_when_no_branches(tmp_path, monkeypatch) -> None:
    cov = {
        "totals": {
            "percent_covered": 100,
            "covered_lines": 4,
            "num_statements": 4,
            "covered_branches": 0,
            "num_branches": 0,
        },
        "files": {},
    }
    _patch_runner(monkeypatch, cov=cov)
    out = tmp_path / "summary.json"
    coverage_summary.main(
        ["--tests", "tests/a.py", "--cov", "pkg.a", "--output", str(out)]
    )
    data = json.loads(out.read_text())
    assert data["branch"] == {"percent": 0, "covered": 0, "total": 0}


def test_main_writes_to_stdout_when_no_output_flag(
    tmp_path, monkeypatch, capsys
) -> None:
    _patch_runner(monkeypatch)
    rc = coverage_summary.main(["--tests", "tests/a.py", "--cov", "pkg.a"])
    assert rc == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["line"]["percent"] == 88


def test_main_reports_failed_tests_count(tmp_path, monkeypatch) -> None:
    _patch_runner(monkeypatch, passed=10, failed=3)
    out = tmp_path / "summary.json"
    coverage_summary.main(
        ["--tests", "tests/a.py", "--cov", "pkg.a", "--output", str(out)]
    )
    data = json.loads(out.read_text())
    assert data["tests"] == {"passed": 10, "failed": 3}

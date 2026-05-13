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
"""Tests for ``.devin/mutation-testing/scripts/coverage_summary.py``.

The subprocess that invokes ``run_targeted.sh`` is mocked, so these tests
exercise the helpers (``_pct``, ``_per_file_entries``) and the
``main()`` JSON output shape that the mutation-testing log file consumes.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import ModuleType

import pytest


@pytest.mark.parametrize(
    "value,expected",
    [
        (0, 0),
        (0.4, 0),
        (0.5, 0),  # banker's rounding: round-half-to-even -> 0
        (0.6, 1),
        (1.5, 2),  # banker's rounding -> 2
        (2.5, 2),  # banker's rounding -> 2
        (99.49, 99),
        (99.51, 100),
    ],
)
def test_pct_rounds_to_integer(
    coverage_summary_module: ModuleType, value: float, expected: int
) -> None:
    assert coverage_summary_module._pct(value) == expected


def test_per_file_entries_handles_missing_branches(
    coverage_summary_module: ModuleType,
) -> None:
    data = {
        "files": {
            "a.py": {
                "summary": {
                    "percent_covered": 80.0,
                    "covered_lines": 8,
                    "num_statements": 10,
                    "num_branches": 0,
                    "covered_branches": 0,
                },
                "missing_lines": [3, 4],
            }
        }
    }
    [entry] = coverage_summary_module._per_file_entries(data)
    assert entry == {
        "path": "a.py",
        "line_percent": 80,
        "branch_percent": None,
        "covered_lines": 8,
        "total_lines": 10,
        "missing_lines": [3, 4],
    }


def test_per_file_entries_computes_branch_percent(
    coverage_summary_module: ModuleType,
) -> None:
    data = {
        "files": {
            "z.py": {
                "summary": {
                    "percent_covered": 50.0,
                    "covered_lines": 5,
                    "num_statements": 10,
                    "num_branches": 4,
                    "covered_branches": 3,
                },
                "missing_lines": [],
            },
            "a.py": {
                "summary": {
                    "percent_covered": 100.0,
                    "covered_lines": 1,
                    "num_statements": 1,
                    "num_branches": 2,
                    "covered_branches": 2,
                },
                "missing_lines": [],
            },
        }
    }
    entries = coverage_summary_module._per_file_entries(data)
    # Entries must be sorted by path (a.py before z.py).
    assert [e["path"] for e in entries] == ["a.py", "z.py"]
    assert entries[0]["branch_percent"] == 100
    assert entries[1]["branch_percent"] == 75


def test_per_file_entries_handles_empty_input(
    coverage_summary_module: ModuleType,
) -> None:
    assert coverage_summary_module._per_file_entries({}) == []
    assert coverage_summary_module._per_file_entries({"files": {}}) == []


def test_main_writes_expected_json_shape(
    coverage_summary_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_cov = {
        "totals": {
            "percent_covered": 87.6,
            "covered_lines": 88,
            "num_statements": 100,
            "covered_branches": 38,
            "num_branches": 50,
        },
        "files": {
            "p.py": {
                "summary": {
                    "percent_covered": 87.6,
                    "covered_lines": 88,
                    "num_statements": 100,
                    "num_branches": 50,
                    "covered_branches": 38,
                },
                "missing_lines": [11, 12],
            }
        },
    }

    def fake_run(tests, cov_targets, extra_args):
        return 7, 1, fake_cov, "pytest p.py --cov=p"

    monkeypatch.setattr(coverage_summary_module, "_run_pytest_with_coverage", fake_run)
    out = tmp_path / "cov.json"
    rc = coverage_summary_module.main(
        ["--tests", "tests/p_test.py", "--cov", "p", "--output", str(out)]
    )
    assert rc == 0
    payload = json.loads(out.read_text())
    assert payload["command"] == "pytest p.py --cov=p"
    assert payload["tests"] == {"passed": 7, "failed": 1}
    assert payload["line"] == {"percent": 88, "covered": 88, "total": 100}
    assert payload["branch"] == {"percent": 76, "covered": 38, "total": 50}
    assert payload["per_file"][0]["path"] == "p.py"
    assert payload["per_file"][0]["missing_lines"] == [11, 12]


def test_main_emits_zero_branch_block_when_no_branches(
    coverage_summary_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_cov = {
        "totals": {
            "percent_covered": 100.0,
            "covered_lines": 10,
            "num_statements": 10,
            "covered_branches": 0,
            "num_branches": 0,
        },
        "files": {},
    }

    def fake_run(tests, cov_targets, extra_args):
        return 1, 0, fake_cov, "pytest"

    monkeypatch.setattr(coverage_summary_module, "_run_pytest_with_coverage", fake_run)
    out = tmp_path / "cov.json"
    coverage_summary_module.main(["--tests", "t.py", "--cov", "m", "--output", str(out)])
    payload = json.loads(out.read_text())
    assert payload["branch"] == {"percent": 0, "covered": 0, "total": 0}

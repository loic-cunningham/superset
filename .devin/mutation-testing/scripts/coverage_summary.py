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
coverage_summary.py — Run pytest with coverage and emit a JSON summary in
exactly the shape the mutation-testing log file (`template_02_mutation_testing.md`)
and final PR comment expect.

This script is the canonical bridge between pytest-cov's verbose JSON output
and the `initial_state.coverage` / `final_state.coverage` YAML blocks used in
the structured mutation-testing log. The agent never has to do its own JSON
shaping or rounding.

Usage:
    coverage_summary.py \\
        --tests tests/unit_tests/sql/parse_tests.py \\
        --tests tests/unit_tests/mcp_service/sql_lab/tool/test_execute_sql.py \\
        --cov superset.sql.parse \\
        --cov superset.mcp_service.sql_lab.tool.execute_sql \\
        --output /tmp/coverage.json

Output JSON shape:

    {
      "command": "pytest <tests> --cov=<modules> --cov-branch ...",
      "tests": {"passed": int, "failed": int},
      "line": {"percent": int, "covered": int, "total": int},
      "branch": {"percent": int, "covered": int, "total": int},
      "per_file": [
        {"path": str, "line_percent": int, "branch_percent": int,
         "covered_lines": int, "total_lines": int, "missing_lines": [int, ...]}
      ]
    }
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _run_pytest_with_coverage(
    tests: list[str],
    cov_targets: list[str],
    extra_args: list[str],
) -> tuple[int, int, dict, str]:
    """Run pytest under coverage and return (passed, failed, cov_json, cmd_str)."""
    cov_json_path = Path(tempfile.mkstemp(prefix="cov-", suffix=".json")[1])
    cmd: list[str] = [
        str(REPO_ROOT / ".devin" / "mutation-testing" / "scripts" / "run_targeted.sh"),
        *tests,
    ]
    for target in cov_targets:
        cmd.append(f"--cov={target}")
    cmd += [
        "--cov-branch",
        "--cov-report=term",
        f"--cov-report=json:{cov_json_path}",
        "-q",
        "--tb=no",
        *extra_args,
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    stdout = proc.stdout
    # Parse the "N passed, M failed in T.TTs" summary line.
    passed = failed = 0
    for line in reversed(stdout.splitlines()):
        if "passed" in line or "failed" in line:
            m_passed = re.search(r"(\d+)\s+passed", line)
            m_failed = re.search(r"(\d+)\s+failed", line)
            if m_passed:
                passed = int(m_passed.group(1))
            if m_failed:
                failed = int(m_failed.group(1))
            if m_passed or m_failed:
                break
    if not cov_json_path.exists():
        print(stdout, file=sys.stderr)
        print(proc.stderr, file=sys.stderr)
        raise SystemExit(
            "coverage_summary: pytest finished but no coverage JSON was written"
        )
    cov_data = json.loads(cov_json_path.read_text())
    cov_json_path.unlink(missing_ok=True)
    return passed, failed, cov_data, " ".join(cmd)


def _pct(num: float | int) -> int:
    return int(round(num))


def _per_file_entries(cov_data: dict) -> list[dict]:
    out: list[dict] = []
    for path, file_data in sorted(cov_data.get("files", {}).items()):
        summary = file_data.get("summary", {})
        out.append(
            {
                "path": path,
                "line_percent": _pct(summary.get("percent_covered", 0)),
                "branch_percent": (
                    _pct(summary["covered_branches"] * 100 / summary["num_branches"])
                    if summary.get("num_branches")
                    else None
                ),
                "covered_lines": summary.get("covered_lines", 0),
                "total_lines": summary.get("num_statements", 0),
                "missing_lines": file_data.get("missing_lines", []),
            }
        )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--tests",
        action="append",
        required=True,
        help="pytest path(s) to run; repeat for multiple paths",
    )
    parser.add_argument(
        "--cov",
        action="append",
        required=True,
        dest="cov_targets",
        help="dotted module path(s) to measure coverage on; repeat for multiple",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="write the JSON summary to this path (default: stdout)",
    )
    parser.add_argument(
        "extra_pytest_args",
        nargs="*",
        help="forwarded to pytest after coverage flags",
    )
    args = parser.parse_args(argv)

    passed, failed, cov_data, cmd_str = _run_pytest_with_coverage(
        tests=args.tests,
        cov_targets=args.cov_targets,
        extra_args=args.extra_pytest_args,
    )

    totals = cov_data.get("totals", {})
    line_total = totals.get("num_statements", 0)
    branch_total = totals.get("num_branches", 0)
    summary = {
        "command": cmd_str,
        "tests": {"passed": passed, "failed": failed},
        "line": {
            "percent": _pct(totals.get("percent_covered", 0)),
            "covered": totals.get("covered_lines", 0),
            "total": line_total,
        },
        "branch": (
            {
                "percent": _pct(totals.get("covered_branches", 0) * 100 / branch_total),
                "covered": totals.get("covered_branches", 0),
                "total": branch_total,
            }
            if branch_total
            else {"percent": 0, "covered": 0, "total": 0}
        ),
        "per_file": _per_file_entries(cov_data),
    }

    payload = json.dumps(summary, indent=2) + "\n"
    if args.output:
        args.output.write_text(payload)
        print(f"[coverage_summary] wrote {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

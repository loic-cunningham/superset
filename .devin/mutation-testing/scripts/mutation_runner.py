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
mutation_runner.py — Apply mutations one at a time, run tests, classify, restore.

The canonical tool for the "measure" and "verify" phases of the mutation-testing
lifecycle. It prevents three classes of errors:

  1. Result mis-classification from loose grep on pytest output.
  2. Silent no-op mutations when the patch cannot be applied.
  3. Working-tree pollution when a restore step fails.

Mutation spec format (YAML)::

    targets:
      - path: superset/sql/parse.py
    test_paths:
      - tests/unit_tests/sql/parse_tests.py
    mutations:
      - id: M1
        description: Remove exp.Drop from destructive_nodes
        file: superset/sql/parse.py
        indent: 12        # prepend N spaces per line (YAML | strips them)
        old: |
          exp.Drop,
          exp.TruncateTable,
        new: |
          exp.TruncateTable,

Each mutation's ``old`` string must be unique in ``file`` after indentation is
applied. Non-unique or missing matches abort with ``error`` status.

Usage::

    mutation_runner.py spec.yaml \\
        --results /tmp/mutation-results.json \\
        [--only M11,M12,M13,M16] \\
        [--continue-on-error]

Exit code: 0 if every mutation ran (regardless of killed/survived);
non-zero if any mutation failed to apply or restore.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    print("mutation_runner: PyYAML is required (`pip install pyyaml`).", file=sys.stderr)
    raise SystemExit(2) from exc


REPO_ROOT = Path(__file__).resolve().parents[3]
RUN_TARGETED = REPO_ROOT / ".devin" / "mutation-testing" / "scripts" / "run_targeted.sh"


@dataclasses.dataclass
class MutationResult:
    id: str
    description: str
    file: str
    status: str  # "killed", "survived", "error"
    passed: int
    failed: int
    first_failing_test: str | None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def _git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def _assert_tree_clean(paths: list[str]) -> None:
    """Abort if any of *paths* has uncommitted edits."""
    status = _git("status", "--porcelain", "--", *paths)
    if status.strip():
        raise RuntimeError(
            "working tree is not clean for target paths:\n"
            f"{status}\n"
            "Commit, stash, or revert before running mutations."
        )


def _restore(paths: list[str]) -> None:
    """Hard-restore the listed paths to HEAD."""
    _git("checkout", "--", *paths)


def _apply_indent(text: str, indent: int) -> str:
    if not indent:
        return text
    prefix = " " * indent

    lines = text.split("\n")
    out = [prefix + line if line else line for line in lines]
    return "\n".join(out)


def _apply_mutation(file_path: Path, old: str, new: str, indent: int = 0) -> None:
    """Replace *old* with *new* in *file_path*.

    Aborts unless *old* (after indentation) appears exactly once.
    """
    old_indented = _apply_indent(old, indent)
    new_indented = _apply_indent(new, indent)
    text = file_path.read_text()
    count = text.count(old_indented)
    if count == 0:
        raise RuntimeError(
            f"mutation old-string not found in {file_path.relative_to(REPO_ROOT)}"
        )
    if count > 1:
        raise RuntimeError(
            f"mutation old-string appears {count} times in "
            f"{file_path.relative_to(REPO_ROOT)} (must be unique)"
        )
    file_path.write_text(text.replace(old_indented, new_indented, 1))


_FAILED_LINE_RE = re.compile(r"^FAILED\s+(\S+)")


def _parse_pytest_output(stdout: str) -> tuple[int, int, str | None]:
    """Parse pytest summary line into (passed, failed, first_failing_test)."""
    passed = failed = 0
    for line in reversed(stdout.splitlines()):
        if "passed" in line or "failed" in line or "error" in line:
            m_passed = re.search(r"(\d+)\s+passed", line)
            m_failed = re.search(r"(\d+)\s+failed", line)
            m_error = re.search(r"(\d+)\s+error", line)
            if m_passed:
                passed = int(m_passed.group(1))
            if m_failed:
                failed = int(m_failed.group(1))
            if m_error:
                # Errors (collection crashes, etc.) count as failures.
                failed += int(m_error.group(1))
            if m_passed or m_failed or m_error:
                break

    first_failing: str | None = None
    for line in stdout.splitlines():
        m = _FAILED_LINE_RE.match(line)
        if m:
            first_failing = m.group(1)
            break
    return passed, failed, first_failing


def _run_tests(test_paths: list[str]) -> tuple[int, int, str | None]:
    proc = subprocess.run(
        [str(RUN_TARGETED), *test_paths, "-q", "--tb=no"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    return _parse_pytest_output(proc.stdout + "\n" + proc.stderr)


def _classify(passed: int, failed: int) -> str:
    if failed > 0:
        return "killed"
    if passed > 0:
        return "survived"
    return "error"


def _run_one(
    mutation: dict[str, Any],
    test_paths: list[str],
    target_paths: list[str],
) -> MutationResult:
    file_path = (REPO_ROOT / mutation["file"]).resolve()
    if not file_path.exists():
        return MutationResult(
            id=mutation["id"],
            description=mutation.get("description", ""),
            file=mutation["file"],
            status="error",
            passed=0,
            failed=0,
            first_failing_test=None,
            error=f"file not found: {mutation['file']}",
        )

    _assert_tree_clean(target_paths)
    try:
        _apply_mutation(
            file_path,
            mutation["old"],
            mutation["new"],
            indent=int(mutation.get("indent", 0)),
        )
    except RuntimeError as exc:
        _restore(target_paths)
        return MutationResult(
            id=mutation["id"],
            description=mutation.get("description", ""),
            file=mutation["file"],
            status="error",
            passed=0,
            failed=0,
            first_failing_test=None,
            error=str(exc),
        )

    try:
        passed, failed, first_failing = _run_tests(test_paths)
    finally:
        _restore(target_paths)

        _assert_tree_clean(target_paths)

    return MutationResult(
        id=mutation["id"],
        description=mutation.get("description", ""),
        file=mutation["file"],
        status=_classify(passed, failed),
        passed=passed,
        failed=failed,
        first_failing_test=first_failing,
    )


def _print_table(results: list[MutationResult]) -> None:
    headers = ("ID", "Status", "Passed", "Failed", "First failing test")
    widths = [
        max(len(h), max((len(str(getattr(r, k))) for r in results), default=0))
        for h, k in zip(
            headers,
            ("id", "status", "passed", "failed", "first_failing_test"),
            strict=True,
        )
    ]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    print(fmt.format(*headers))
    print("  ".join("-" * w for w in widths))
    for r in results:
        print(
            fmt.format(
                r.id,
                r.status.upper(),
                r.passed,
                r.failed,
                r.first_failing_test or "",
            )
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("spec", type=Path, help="YAML mutation spec")
    parser.add_argument(
        "--results",
        type=Path,
        default=None,
        help="write the JSON results file (default: stdout-only)",
    )
    parser.add_argument(
        "--only",
        default="",
        help="comma-separated list of mutation IDs to run (default: all)",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="keep going after a mutation that fails to apply",
    )
    args = parser.parse_args(argv)

    spec = yaml.safe_load(args.spec.read_text())
    if "mutations" not in spec or "test_paths" not in spec:
        print(
            "mutation_runner: spec must have 'mutations' and 'test_paths' keys",
            file=sys.stderr,
        )
        return 2

    only = {x.strip() for x in args.only.split(",") if x.strip()}
    mutations = [m for m in spec["mutations"] if not only or m["id"] in only]
    test_paths = spec["test_paths"]
    target_paths = [
        t["path"] if isinstance(t, dict) else t for t in spec.get("targets", [])
    ]
    if not target_paths:
        # Default to the union of mutation files.
        target_paths = sorted({m["file"] for m in mutations})

    print(
        f"[mutation_runner] running {len(mutations)} mutation(s) against "
        f"{len(test_paths)} test path(s)",
        file=sys.stderr,
    )

    results: list[MutationResult] = []
    saw_error = False
    for m in mutations:
        print(
            f"[mutation_runner] {m['id']}: {m.get('description', '')}", file=sys.stderr
        )
        result = _run_one(m, test_paths, target_paths)
        results.append(result)
        if result.status == "error":
            saw_error = True
            print(
                f"[mutation_runner]   ERROR: {result.error}",
                file=sys.stderr,
            )
            if not args.continue_on_error:
                break
        else:
            tag = result.status.upper()
            tail = (
                f" (first failing: {result.first_failing_test})"
                if result.first_failing_test
                else ""
            )
            print(
                f"[mutation_runner]   {tag}: {result.passed} passed, "
                f"{result.failed} failed{tail}",
                file=sys.stderr,
            )

    print()
    _print_table(results)
    killed = sum(1 for r in results if r.status == "killed")
    survived = sum(1 for r in results if r.status == "survived")
    errored = sum(1 for r in results if r.status == "error")
    total_valid = killed + survived
    kill_rate = round(killed / total_valid * 100) if total_valid else 0
    print()
    print(
        f"Summary: {killed} killed, {survived} survived, {errored} errored "
        f"(kill rate {kill_rate}% of {total_valid} valid)"
    )

    if args.results:
        payload = {
            "killed": killed,
            "survived": survived,
            "errored": errored,
            "kill_rate": kill_rate,
            "results": [r.to_dict() for r in results],
        }
        args.results.write_text(json.dumps(payload, indent=2) + "\n")
        print(f"[mutation_runner] wrote {args.results}", file=sys.stderr)

    return 1 if saw_error else 0


if __name__ == "__main__":
    raise SystemExit(main())

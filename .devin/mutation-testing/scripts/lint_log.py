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
lint_log.py — Validate a mutation-testing log file against the Stage 2 template.

Checks:
  - Filename matches ``pr-<N>-<YYYY-MM-DD>-<slug>.md``.
  - YAML front matter is present, parsable, and contains all required keys.
  - Status is one of ``{in_progress, completed}``.
  - All required H2 section headings are present and in order.
  - ``final_state`` is fully populated when status is ``completed``.

Usage::

    lint_log.py .devin/mutation-testing/pr-15-2026-05-13-foo.md

Exit code: 0 if valid, 1 otherwise. Errors are printed to stderr.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    print("lint_log: PyYAML is required (`pip install pyyaml`).", file=sys.stderr)
    raise SystemExit(2) from exc


FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
FILENAME_RE = re.compile(r"^pr-(\d+)-(\d{4}-\d{2}-\d{2})-[a-z0-9][a-z0-9-]*\.md$")

REQUIRED_TOP_KEYS = {
    "pr_id",
    "pr_title",
    "run_date",
    "agent",
    "repo",
    "branch",
    "base_branch",
    "mode",
    "status",
    "triage",
    "target",
    "initial_state",
    "final_state",
    "commits",
    "artifacts",
}
REQUIRED_INITIAL_KEYS = {"targeted_tests", "coverage", "mutation_testing"}
REQUIRED_COVERAGE_KEYS = {"line", "branch"}
REQUIRED_LINE_KEYS = {"percent", "covered", "total"}
REQUIRED_MUTATION_KEYS = {"valid_mutations", "killed", "survived", "kill_rate"}

REQUIRED_SECTIONS = [
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


def _check_filename(path: Path, errors: list[str]) -> None:
    if not FILENAME_RE.match(path.name):
        errors.append(
            f"filename {path.name!r} does not match pattern "
            "'pr-<N>-<YYYY-MM-DD>-<slug>.md'"
        )


def _check_front_matter_shape(meta: dict[str, Any], errors: list[str]) -> None:
    missing = REQUIRED_TOP_KEYS - set(meta)
    if missing:
        errors.append(f"YAML missing keys: {sorted(missing)}")

    status = meta.get("status")
    if status not in {"in_progress", "completed"}:
        errors.append(f"status must be in_progress|completed, got {status!r}")

    for state_name in ("initial_state", "final_state"):
        state = meta.get(state_name)
        if not isinstance(state, dict):
            errors.append(f"{state_name} must be a mapping")
            continue
        missing = REQUIRED_INITIAL_KEYS - set(state)
        if missing:
            errors.append(f"{state_name} missing keys: {sorted(missing)}")
            continue
        cov = state.get("coverage")
        if not isinstance(cov, dict):
            errors.append(f"{state_name}.coverage must be a mapping")
        else:
            missing = REQUIRED_COVERAGE_KEYS - set(cov)
            if missing:
                errors.append(f"{state_name}.coverage missing keys: {sorted(missing)}")
            for axis in ("line", "branch"):
                axis_data = cov.get(axis)
                if not isinstance(axis_data, dict):
                    errors.append(f"{state_name}.coverage.{axis} must be a mapping")
                else:
                    missing = REQUIRED_LINE_KEYS - set(axis_data)
                    if missing:
                        errors.append(
                            f"{state_name}.coverage.{axis} missing keys: "
                            f"{sorted(missing)}"
                        )
        mt = state.get("mutation_testing")
        if not isinstance(mt, dict):
            errors.append(f"{state_name}.mutation_testing must be a mapping")
        else:
            missing = REQUIRED_MUTATION_KEYS - set(mt)
            if missing:
                errors.append(
                    f"{state_name}.mutation_testing missing keys: {sorted(missing)}"
                )

    if status == "completed":
        final = meta.get("final_state") or {}
        mt = final.get("mutation_testing") or {}
        if mt.get("rerun_type") not in {"full", "survivor_focused"}:
            errors.append(
                "final_state.mutation_testing.rerun_type must be "
                "'full' or 'survivor_focused' when status='completed'"
            )


def _check_sections(body: str, errors: list[str]) -> None:
    found: list[str] = re.findall(r"^##\s+(.+?)\s*$", body, re.MULTILINE)
    indices: dict[str, int] = {}
    for i, header in enumerate(found):
        indices.setdefault(header, i)
    last_seen = -1
    for required in REQUIRED_SECTIONS:
        if required not in indices:
            errors.append(f"missing required section: '## {required}'")
            continue
        idx = indices[required]
        if idx < last_seen:
            errors.append(
                f"section '## {required}' is out of order "
                "(should follow the previous required section)"
            )
        last_seen = idx


def lint(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"file does not exist: {path}"]
    _check_filename(path, errors)

    text = path.read_text()
    match = FRONT_MATTER_RE.match(text)
    if not match:
        errors.append("YAML front matter not found at start of file")
        return errors

    front, body = match.group(1), match.group(2)
    try:
        meta = yaml.safe_load(front) or {}
    except yaml.YAMLError as exc:
        errors.append(f"YAML front matter not parseable: {exc}")
        return errors

    if not isinstance(meta, dict):
        errors.append("YAML front matter must be a mapping")
        return errors

    _check_front_matter_shape(meta, errors)
    _check_sections(body, errors)
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", type=Path, nargs="+", help="log files to lint")
    args = parser.parse_args(argv)

    all_clean = True
    for path in args.paths:
        errs = lint(path)
        if errs:
            all_clean = False
            print(f"{path}: FAIL", file=sys.stderr)
            for err in errs:
                print(f"  - {err}", file=sys.stderr)
        else:
            print(f"{path}: OK")
    return 0 if all_clean else 1


if __name__ == "__main__":
    raise SystemExit(main())

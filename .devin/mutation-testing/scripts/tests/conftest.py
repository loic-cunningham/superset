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
Pytest configuration for the mutation-testing scripts test suite.

The scripts under .devin/mutation-testing/scripts/ are stand-alone command-line
tools, not a Python package. This conftest loads each script as an importable
module via importlib so the tests can call its functions directly without
shelling out to the script.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

SCRIPTS_DIR = Path(__file__).resolve().parents[1]


def _load_script_module(name: str, filename: str) -> ModuleType:
    """Load a single .py file under scripts/ as a top-level module."""
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not build import spec for {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


lint_log = _load_script_module("lint_log", "lint_log.py")
render_pr_comment = _load_script_module("render_pr_comment", "render_pr_comment.py")
coverage_summary = _load_script_module("coverage_summary", "coverage_summary.py")
mutation_runner = _load_script_module("mutation_runner", "mutation_runner.py")

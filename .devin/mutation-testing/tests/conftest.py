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
"""Pytest helpers for testing the .devin/mutation-testing/scripts modules.

The scripts live outside any Python package, so we load them via
``importlib`` so the tests can call their public functions directly.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"


def _load_script(name: str) -> ModuleType:
    """Load ``scripts/<name>.py`` as a top-level module named ``name``."""
    path = SCRIPTS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load script {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def lint_log_module() -> ModuleType:
    return _load_script("lint_log")


@pytest.fixture(scope="session")
def mutation_runner_module() -> ModuleType:
    return _load_script("mutation_runner")


@pytest.fixture(scope="session")
def render_pr_comment_module() -> ModuleType:
    return _load_script("render_pr_comment")


@pytest.fixture(scope="session")
def coverage_summary_module() -> ModuleType:
    return _load_script("coverage_summary")

#!/usr/bin/env bash
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
#
# run_targeted.sh — Activate the project venv, export required env vars, and
# run pytest against a focused set of test paths. This is the canonical entry
# point that mutation_runner.py invokes for every mutation, so each mutation
# run is byte-identical to every other run except for the patched source file.
#
# Usage:
#     ./.devin/mutation-testing/scripts/run_targeted.sh <pytest-args...>
#
# Example:
#     ./.devin/mutation-testing/scripts/run_targeted.sh \
#         tests/unit_tests/sql/parse_tests.py -q
#
# Why this script exists:
#     - Superset's MCP service transitively imports key_value, which eagerly
#       runs beartype.claw.beartype_this_package() and trips a circular
#       import. We export PY_KEY_VALUE_DISABLE_BEARTYPE=true (paired with the
#       patch applied by setup_env.sh) to suppress that.
#     - The venv must be sourced before pytest, otherwise the system Python
#       is used and modules are missing.
#     - Pre-existing test failures unrelated to the PR can be deselected via
#       the DEVIN_PYTEST_DESELECT env var (newline- or comma-separated).
#
# Exit code: pytest's exit code (0 on success, non-zero on failure).

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
VENV_DIR="${VENV_DIR:-${REPO_ROOT}/.venv}"

if [[ ! -d "$VENV_DIR" ]]; then
    echo "[run_targeted] ERROR: venv missing at $VENV_DIR. Run setup_env.sh first." >&2
    exit 2
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

export PY_KEY_VALUE_DISABLE_BEARTYPE="${PY_KEY_VALUE_DISABLE_BEARTYPE:-true}"
export PYTHONDONTWRITEBYTECODE="${PYTHONDONTWRITEBYTECODE:-1}"

deselect_args=()
if [[ -n "${DEVIN_PYTEST_DESELECT:-}" ]]; then
    # Split on newlines or commas.
    while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        deselect_args+=("--deselect" "$line")
    done < <(printf '%s\n' "$DEVIN_PYTEST_DESELECT" | tr ',' '\n')
fi

cd "$REPO_ROOT"
exec python -m pytest "${deselect_args[@]}" "$@"

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
# setup_env.sh — Prepare the local Python environment for running mutation
# testing on this Superset checkout.
#
# What this script does (idempotent):
#   1. Installs the system-level C build dependencies that Superset's wheels
#      need (mysqlclient, python-ldap).
#   2. Ensures a `.venv` exists at the repo root and installs the development
#      requirements with `uv` if available, falling back to plain `pip`.
#   3. Patches the `key_value` package's eager `beartype.claw.beartype_this_package`
#      call so it can be disabled via the `PY_KEY_VALUE_DISABLE_BEARTYPE` env var.
#      Without this patch, importing Superset's MCP modules can fail with a
#      `claw_state` circular import.
#   4. Upgrades `nh3` past 0.2.x because older builds fail to initialize twice
#      under recent CPython.
#
# Usage:
#     ./.devin/mutation-testing/scripts/setup_env.sh
#
# Exit codes:
#     0 — environment is ready
#     non-zero — one of the steps failed; details printed to stderr

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
VENV_DIR="${REPO_ROOT}/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3.11}"
LOG_PREFIX="[setup_env]"

log() { printf '%s %s\n' "$LOG_PREFIX" "$*" >&2; }
die() { printf '%s ERROR: %s\n' "$LOG_PREFIX" "$*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# 1. System packages
# ---------------------------------------------------------------------------
ensure_apt_packages() {
    local packages=(
        libmysqlclient-dev
        default-libmysqlclient-dev
        pkg-config
        libldap2-dev
        libsasl2-dev
    )
    local missing=()
    for pkg in "${packages[@]}"; do
        if ! dpkg -s "$pkg" >/dev/null 2>&1; then
            missing+=("$pkg")
        fi
    done
    if (( ${#missing[@]} == 0 )); then
        log "system packages already installed"
        return
    fi
    log "installing system packages: ${missing[*]}"
    if command -v sudo >/dev/null 2>&1; then
        sudo apt-get update -qq
        sudo apt-get install -y --no-install-recommends "${missing[@]}"
    else
        apt-get update -qq
        apt-get install -y --no-install-recommends "${missing[@]}"
    fi
}

# ---------------------------------------------------------------------------
# 2. Virtualenv + Python deps
# ---------------------------------------------------------------------------
ensure_venv() {
    if [[ ! -d "$VENV_DIR" ]]; then
        log "creating venv at $VENV_DIR (python: $PYTHON_BIN)"
        if command -v uv >/dev/null 2>&1; then
            uv venv "$VENV_DIR" --python "$PYTHON_BIN"
        else
            "$PYTHON_BIN" -m venv "$VENV_DIR"
        fi
    fi
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
    log "venv active: $(which python) ($(python --version 2>&1))"
}

install_python_deps() {
    # Only install if pytest isn't importable; mutation testing only needs the
    # development requirements, not a full app install.
    if python -c "import pytest" 2>/dev/null; then
        log "python dependencies appear to be installed (pytest importable)"
        return
    fi
    log "installing requirements/development.txt"
    if command -v uv >/dev/null 2>&1; then
        uv pip install -r "$REPO_ROOT/requirements/development.txt"
    else
        python -m pip install --upgrade pip
        python -m pip install -r "$REPO_ROOT/requirements/development.txt"
    fi
}

ensure_nh3_upgrade() {
    # nh3 0.2.x crashes with "PyO3 modules compiled for CPython 3.8 or older may
    # only be initialized once per interpreter process" under newer CPython.
    local current
    current="$(python -c 'import importlib.metadata as m; print(m.version("nh3"))' 2>/dev/null || true)"
    if [[ -z "$current" ]]; then
        log "nh3 not installed yet (will be installed transitively)"
        return
    fi
    if [[ "$current" == 0.2.* ]]; then
        log "upgrading nh3 from $current to a 0.3+ build"
        if command -v uv >/dev/null 2>&1; then
            uv pip install --upgrade 'nh3>=0.3.0'
        else
            python -m pip install --upgrade 'nh3>=0.3.0'
        fi
    else
        log "nh3 version $current is fine"
    fi
}

# ---------------------------------------------------------------------------
# 3. beartype/claw circular-import patch on key_value
# ---------------------------------------------------------------------------
patch_key_value_beartype() {
    local site_packages
    site_packages="$(python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
    local target="$site_packages/key_value/aio/__init__.py"
    if [[ ! -f "$target" ]]; then
        log "key_value not installed yet; skipping beartype patch"
        return
    fi
    if grep -q "PY_KEY_VALUE_DISABLE_BEARTYPE" "$target"; then
        log "key_value beartype patch already applied"
        return
    fi
    log "patching key_value to honor PY_KEY_VALUE_DISABLE_BEARTYPE"
    python - "$target" <<'PYEOF'
import pathlib
import re
import sys

path = pathlib.Path(sys.argv[1])
text = path.read_text()
needle = "from beartype.claw import beartype_this_package"
if needle not in text:
    print("[setup_env] WARN: expected beartype import not found; leaving file alone",
          file=sys.stderr)
    sys.exit(0)
# Wrap the eager beartype_this_package() call in an env-var guard.
pattern = re.compile(
    r"(from beartype\.claw import beartype_this_package\s*\n"
    r")(beartype_this_package\(\)\s*\n)"
)
replacement = (
    r"\1"
    r"import os as _os\n"
    r"if _os.environ.get('PY_KEY_VALUE_DISABLE_BEARTYPE', '').lower() not in {'1', 'true', 'yes'}:\n"
    r"    \2"
)
new_text, n = pattern.subn(replacement, text, count=1)
if n != 1:
    print("[setup_env] WARN: beartype call not in expected shape; leaving file alone",
          file=sys.stderr)
    sys.exit(0)
path.write_text(new_text)
print(f"[setup_env] patched {path}", file=sys.stderr)
PYEOF
}

# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
main() {
    ensure_apt_packages
    ensure_venv
    install_python_deps
    ensure_nh3_upgrade
    patch_key_value_beartype
    log "environment ready. Activate with: source $VENV_DIR/bin/activate"
    log "and always export: PY_KEY_VALUE_DISABLE_BEARTYPE=true"
}

main "$@"

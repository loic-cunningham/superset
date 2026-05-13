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
# fetch_templates.sh — Fetch mutation-testing templates from the default branch.
#
# Templates live under `.devin/docs/` on master. PR branches under test may
# not contain them, and local copies should not drift from what master
# enforces. This script fetches them fresh into a cache directory.
#
# Usage:
#     ./.devin/mutation-testing/scripts/fetch_templates.sh [destination-dir]
#
# Default destination: /tmp/mutation-testing-templates/
#
# Exit code: 0 on success, non-zero if git fetch or git show fails.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
DEST_DIR="${1:-/tmp/mutation-testing-templates}"
REMOTE="${MUTATION_TESTING_REMOTE:-origin}"
BRANCH="${MUTATION_TESTING_BRANCH:-master}"
LOG_PREFIX="[fetch_templates]"

FILES=(
    ".devin/docs/mutation_testing_agent_handoff.md"
    ".devin/docs/template_01_test_foundation.md"
    ".devin/docs/template_01_test_foundation.example.md"
    ".devin/docs/template_02_mutation_testing.md"
    ".devin/docs/template_02_mutation_testing.example.md"
    ".devin/docs/template_03_final_report.md"
    ".devin/docs/template_03_final_report.example.md"
)

log() { printf '%s %s\n' "$LOG_PREFIX" "$*" >&2; }

cd "$REPO_ROOT"
mkdir -p "$DEST_DIR"
log "fetching ${REMOTE}/${BRANCH}"
git fetch --quiet "$REMOTE" "$BRANCH"

for path in "${FILES[@]}"; do
    out="$DEST_DIR/$(basename "$path")"
    if git show "${REMOTE}/${BRANCH}:${path}" > "$out" 2>/dev/null; then
        log "  ${path} -> ${out}"
    else
        log "  WARN: ${path} missing on ${REMOTE}/${BRANCH}"
        rm -f "$out"
    fi
done

log "templates cached at $DEST_DIR"

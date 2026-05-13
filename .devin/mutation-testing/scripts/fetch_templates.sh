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
# Templates live under `.devin/mutation-testing/templates/` on master
# (canonical) with a legacy fallback to `.devin/docs/` for older branches
# under test. PR branches under test may not contain them, and local
# copies should not drift from what master enforces, so this script
# fetches them fresh into a cache directory each run.
#
# Usage:
#     ./.devin/mutation-testing/scripts/fetch_templates.sh [destination-dir]
#
# Default destination: /tmp/mutation-testing-templates/
#
# Exit code: 0 on success, non-zero if git fetch or git show fails or if
# a required template file cannot be located on either path.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
DEST_DIR="${1:-/tmp/mutation-testing-templates}"
REMOTE="${MUTATION_TESTING_REMOTE:-origin}"
BRANCH="${MUTATION_TESTING_BRANCH:-master}"
LOG_PREFIX="[fetch_templates]"

# Canonical location on master.
CANONICAL_DIR=".devin/mutation-testing/templates"
# Legacy fallback for older branches that still keep templates in docs.
LEGACY_DIR=".devin/docs"

FILES=(
    "mutation_testing_agent_handoff.md"
    "template_01_test_foundation.md"
    "template_01_test_foundation.example.md"
    "template_02_mutation_testing.md"
    "template_02_mutation_testing.example.md"
    "template_03_final_report.md"
    "template_03_final_report.example.md"
)

log() { printf '%s %s\n' "$LOG_PREFIX" "$*" >&2; }

cd "$REPO_ROOT"
mkdir -p "$DEST_DIR"
log "fetching ${REMOTE}/${BRANCH}"
git fetch --quiet "$REMOTE" "$BRANCH"

missing=0
for name in "${FILES[@]}"; do
    out="$DEST_DIR/$name"
    canonical="${CANONICAL_DIR}/${name}"
    legacy="${LEGACY_DIR}/${name}"
    if git show "${REMOTE}/${BRANCH}:${canonical}" > "$out" 2>/dev/null; then
        log "  ${canonical} -> ${out}"
    elif git show "${REMOTE}/${BRANCH}:${legacy}" > "$out" 2>/dev/null; then
        log "  ${legacy} -> ${out} (legacy path)"
    else
        log "  ERROR: ${name} missing on ${REMOTE}/${BRANCH} (checked ${canonical} and ${legacy})"
        rm -f "$out"
        missing=$((missing + 1))
    fi
done

if [[ $missing -gt 0 ]]; then
    log "FAIL: ${missing} template(s) could not be fetched"
    exit 1
fi

log "templates cached at $DEST_DIR"

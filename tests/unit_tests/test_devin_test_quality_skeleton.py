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
"""Structural tests for the Devin test-quality observability skeleton.

The PR introduces three artifacts that have no runtime entry point in the
Superset application but encode contractual behaviour for the cron-distillation
loop:

* ``.github/workflows/devin-cron-distill.yml`` — workflow that launches a
  Devin session against the committed mutation-testing logs.
* ``.devin/mutation-testing/templates/cron_distill_prompt.md`` — agent handoff
  consumed by that workflow.
* ``docs/test-quality/README.md`` — committed seed/snapshot of the
  test-quality dashboard.

These files are not executed by ``pytest``; the tests below assert the
structural invariants a regression could plausibly violate (workflow
trigger shape, request body keys, placeholder substitution, prompt template
sections, dashboard table contents, etc.) so mutation testing has something
to score against.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "devin-cron-distill.yml"
PROMPT_TEMPLATE_PATH = (
    REPO_ROOT
    / ".devin"
    / "mutation-testing"
    / "templates"
    / "cron_distill_prompt.md"
)
DASHBOARD_PATH = REPO_ROOT / "docs" / "test-quality" / "README.md"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def workflow_text() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def workflow_yaml(workflow_text: str) -> dict:
    return yaml.safe_load(workflow_text)


@pytest.fixture(scope="module")
def workflow_job(workflow_yaml: dict) -> dict:
    return workflow_yaml["jobs"]["launch-devin"]


@pytest.fixture(scope="module")
def workflow_triggers(workflow_yaml: dict) -> dict:
    # ``on:`` in YAML parses as the boolean key ``True`` because ``on`` is a
    # YAML truthy literal.
    return workflow_yaml[True]


@pytest.fixture(scope="module")
def prompt_template_text() -> str:
    return PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def dashboard_text() -> str:
    return DASHBOARD_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Workflow — triggers and inputs
# ---------------------------------------------------------------------------


def test_workflow_yaml_parses(workflow_yaml: dict) -> None:
    assert "jobs" in workflow_yaml
    assert "launch-devin" in workflow_yaml["jobs"]


def test_workflow_has_manual_dispatch_trigger(workflow_triggers: dict) -> None:
    assert "workflow_dispatch" in workflow_triggers


def test_workflow_dispatch_inputs(workflow_triggers: dict) -> None:
    inputs = workflow_triggers["workflow_dispatch"]["inputs"]
    assert set(inputs.keys()) == {"lookback_days", "notification_channels"}


def test_lookback_days_default(workflow_triggers: dict) -> None:
    lookback = workflow_triggers["workflow_dispatch"]["inputs"]["lookback_days"]
    assert lookback["default"] == "30"
    assert lookback["required"] is False
    assert lookback["type"] == "string"


def test_notification_channels_default_empty(workflow_triggers: dict) -> None:
    channels = workflow_triggers["workflow_dispatch"]["inputs"]["notification_channels"]
    assert channels["default"] == ""
    assert channels["required"] is False


# ---------------------------------------------------------------------------
# Workflow — job-level metadata
# ---------------------------------------------------------------------------


def test_job_runs_on_pinned_ubuntu(workflow_job: dict) -> None:
    assert workflow_job["runs-on"] == "ubuntu-24.04"


def test_job_has_short_timeout(workflow_job: dict) -> None:
    # Cron pass must not hang on slow API responses.
    assert workflow_job["timeout-minutes"] == 5


def test_job_uses_minimum_permissions(workflow_job: dict) -> None:
    assert workflow_job["permissions"] == {
        "contents": "read",
        "pull-requests": "read",
    }


# ---------------------------------------------------------------------------
# Workflow — steps
# ---------------------------------------------------------------------------


def test_steps_in_documented_order(workflow_job: dict) -> None:
    names = [step["name"] for step in workflow_job["steps"]]
    assert names == [
        "Checkout repository (logs + templates)",
        "Inventory committed PR logs",
        "Build distillation prompt",
        "Create Devin session",
    ]


def test_checkout_uses_sparse_checkout(workflow_job: dict) -> None:
    checkout = next(s for s in workflow_job["steps"] if s["name"].startswith("Checkout"))
    sparse_paths = checkout["with"]["sparse-checkout"].splitlines()
    assert ".devin/mutation-testing/" in sparse_paths
    assert "docs/test-quality/" in sparse_paths


def test_inventory_step_globs_pr_logs(workflow_job: dict) -> None:
    inventory = next(
        s for s in workflow_job["steps"] if s["name"] == "Inventory committed PR logs"
    )
    run = inventory["run"]
    assert "shopt -s nullglob" in run
    assert ".devin/mutation-testing/pr-*.md" in run
    assert "log_count=0" in run
    assert 'echo "log_count=${#logs[@]}" >> "$GITHUB_OUTPUT"' in run


# ---------------------------------------------------------------------------
# Workflow — inline JavaScript (Build prompt + Create session)
# ---------------------------------------------------------------------------


def test_build_prompt_reads_template_file(workflow_text: str) -> None:
    template_path = ".devin/mutation-testing/templates/cron_distill_prompt.md"
    assert template_path in workflow_text


def test_build_prompt_substitutes_notification_channels_globally(
    workflow_text: str,
) -> None:
    # Global regex flag matters so templates with multiple placeholders are
    # fully substituted.
    assert "/{{ NOTIFICATION_CHANNELS }}/g" in workflow_text


def test_devin_api_endpoint(workflow_text: str) -> None:
    assert "https://api.devin.ai/v3/organizations/" in workflow_text


def test_devin_api_required_secrets(workflow_text: str) -> None:
    assert "secrets.DEVIN_API_KEY" in workflow_text
    assert "secrets.DEVIN_ORG_ID" in workflow_text


def test_devin_api_call_uses_bearer_auth(workflow_text: str) -> None:
    assert "Authorization: `Bearer ${apiKey}`" in workflow_text


def test_devin_api_call_has_60_second_timeout(workflow_text: str) -> None:
    assert "DEVIN_API_TIMEOUT_MS = 60_000" in workflow_text
    assert "AbortSignal.timeout(DEVIN_API_TIMEOUT_MS)" in workflow_text


def test_request_body_documents_four_keys(workflow_text: str) -> None:
    # The Devin Sessions API contract: prompt + title + repos + tags.
    for key in ("prompt,", "title:", "repos:", "tags:"):
        assert key in workflow_text


def test_failure_paths_use_set_failed(workflow_text: str) -> None:
    # Missing template, missing secrets, timeout, network error, non-OK response.
    assert workflow_text.count("core.setFailed") >= 4


def test_secret_presence_guard_present(workflow_text: str) -> None:
    # The literal guard block must be there — counting `setFailed` alone
    # is too loose because the workflow has multiple failure paths.
    assert "if (!apiKey || !orgId) {" in workflow_text
    assert (
        "DEVIN_API_KEY and DEVIN_ORG_ID repository secrets are required."
        in workflow_text
    )


def test_session_url_added_to_run_summary(workflow_text: str) -> None:
    assert (
        "addHeading('Devin test-quality distillation session launched')"
        in workflow_text
    )
    assert "core.summary" in workflow_text


# ---------------------------------------------------------------------------
# Workflow — pinned action versions and inline-JS invariants
# ---------------------------------------------------------------------------

_PINNED_USES_RE = re.compile(
    r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+@(v\d+|[0-9a-f]{40})$"
)
_FLOATING_REFS = {"main", "master", "latest", "HEAD"}


def test_actions_are_pinned_to_specific_versions(workflow_job: dict) -> None:
    # Every step that uses an external action must be pinned to either a
    # SHA (40 hex chars) or a major version (`@vN`). Floating refs like
    # `@main` / `@latest` would introduce supply-chain drift.
    uses_values = [step["uses"] for step in workflow_job["steps"] if "uses" in step]
    assert uses_values, "expected at least one step to use an external action"
    for uses in uses_values:
        ref = uses.rsplit("@", 1)[-1] if "@" in uses else ""
        assert ref not in _FLOATING_REFS, (
            f"unpinned action ref: {uses!r} — floating refs are forbidden"
        )
        assert _PINNED_USES_RE.match(uses), (
            f"action {uses!r} is not pinned to @vN or a 40-char SHA"
        )


def test_request_body_contains_required_tags(workflow_text: str) -> None:
    # The Devin session tags array is the dashboard's index across runs.
    # Each documented tag must be present in the workflow source.
    for tag in (
        "'github-actions',",
        "'mutation-testing',",
        "'cron-distill',",
        "`repo-${context.repo.owner}-${context.repo.repo}`,",
    ):
        assert tag in workflow_text, f"missing required session tag: {tag!r}"


def test_session_title_capped_at_80_chars(workflow_text: str) -> None:
    # `.slice(0, 80)` is the cap applied to the constructed title — the
    # Devin Sessions API rejects overlong titles. A regression to a higher
    # cap (e.g. `.slice(0, 800)`) silently produces 4xx responses.
    assert ".slice(0, 80)" in workflow_text


def test_session_title_uses_iso_date_yyyy_mm_dd(workflow_text: str) -> None:
    # Title date must be `YYYY-MM-DD` (10 chars). Truncating to 8 chars
    # collapses the day component and breaks dashboard groupings.
    assert ".toISOString().slice(0,10)" in workflow_text


def test_devin_api_url_encodes_org_id(workflow_text: str) -> None:
    # Org IDs containing `/` or `?` would be treated as URL syntax without
    # `encodeURIComponent`; the request would route to the wrong endpoint.
    assert (
        "https://api.devin.ai/v3/organizations/${encodeURIComponent(orgId)}/sessions"
        in workflow_text
    )


def _step_by_name(job: dict, name: str) -> dict:
    for step in job["steps"]:
        if step.get("name") == name:
            return step
    raise AssertionError(f"step {name!r} not found")


def test_build_prompt_step_gated_on_log_count(workflow_job: dict) -> None:
    step = _step_by_name(workflow_job, "Build distillation prompt")
    assert step.get("if") == "steps.inventory.outputs.log_count != '0'"


def test_create_session_step_gated_on_log_count(workflow_job: dict) -> None:
    step = _step_by_name(workflow_job, "Create Devin session")
    assert step.get("if") == "steps.inventory.outputs.log_count != '0'"


def test_inventory_step_prints_each_log_file_name(workflow_job: dict) -> None:
    inventory = _step_by_name(workflow_job, "Inventory committed PR logs")
    # Per-file echo line must survive — the run summary depends on it for
    # operator-visible debugging of which files were distilled.
    assert 'printf \'  %s\\n\' "${logs[@]}"' in inventory["run"]


# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------


def test_prompt_template_has_notification_channels_placeholder(
    prompt_template_text: str,
) -> None:
    assert "{{ NOTIFICATION_CHANNELS }}" in prompt_template_text


def test_prompt_template_lists_supported_channels(prompt_template_text: str) -> None:
    for channel in ("slack:", "linear:", "teams:", "email:"):
        assert channel in prompt_template_text


def test_prompt_template_targets_github_wiki(prompt_template_text: str) -> None:
    assert "GitHub Wiki" in prompt_template_text
    assert ".wiki.git" in prompt_template_text


def test_prompt_template_does_not_open_a_pr(prompt_template_text: str) -> None:
    # The instruction must be unambiguous; lower-cased compare avoids
    # accidental case-only regressions.
    text = prompt_template_text.lower()
    assert "does **not** open a pull request" in text


def test_prompt_template_enumerates_wiki_page_sections(
    prompt_template_text: str,
) -> None:
    for needle in (
        "Headline numbers",
        "Per-PR snapshot table",
        "Mutation kill-rate trend chart",
        "Patterns we keep finding",
        "Recommended next actions",
    ):
        assert needle in prompt_template_text


# ---------------------------------------------------------------------------
# Dashboard seed (docs/test-quality/README.md)
# ---------------------------------------------------------------------------


def test_dashboard_has_mermaid_xychart(dashboard_text: str) -> None:
    assert "```mermaid" in dashboard_text
    assert "xychart-beta" in dashboard_text


def test_dashboard_links_to_cron_workflow(dashboard_text: str) -> None:
    assert "../../.github/workflows/devin-cron-distill.yml" in dashboard_text


def test_dashboard_links_to_each_committed_log(dashboard_text: str) -> None:
    assert "pr-30-2026-05-13-rls-double-apply.md" in dashboard_text
    assert "pr-31-2026-05-13-mcp-dashboard-filters.md" in dashboard_text


def test_dashboard_has_japanese_summary_block(dashboard_text: str) -> None:
    assert "<summary>JA — 日本語サマリー</summary>" in dashboard_text


def test_dashboard_lists_action_plan_items(dashboard_text: str) -> None:
    # Priority-prefixed rows like `| P1 |` / `| P2 |` give the action plan
    # structure; the seed snapshot ships with at least four items.
    p1_rows = dashboard_text.count("| P1 |")
    p2_rows = dashboard_text.count("| P2 |")
    assert p1_rows + p2_rows >= 4

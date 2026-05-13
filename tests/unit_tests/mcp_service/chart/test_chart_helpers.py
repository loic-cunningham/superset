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

from unittest.mock import MagicMock, patch

import pytest

from superset.mcp_service.chart.chart_helpers import (
    _match_adhoc_by_subject,
    _match_legacy_by_col,
    _resolve_filter_operator_and_value,
    build_applied_dashboard_filters,
    ChartNotOnDashboardError,
    extract_form_data_key_from_url,
    find_chart_by_identifier,
    get_cached_form_data,
)


def test_extract_form_data_key_from_url_with_key():
    url = "http://localhost:8088/explore/?form_data_key=abc123&slice_id=1"
    assert extract_form_data_key_from_url(url) == "abc123"


def test_extract_form_data_key_from_url_no_key():
    url = "http://localhost:8088/explore/?slice_id=1"
    assert extract_form_data_key_from_url(url) is None


def test_extract_form_data_key_from_url_none():
    assert extract_form_data_key_from_url(None) is None


def test_extract_form_data_key_from_url_empty():
    assert extract_form_data_key_from_url("") is None


def test_extract_form_data_key_from_url_multiple_params():
    url = "http://localhost:8088/explore/?slice_id=5&form_data_key=xyz789&other=val"
    assert extract_form_data_key_from_url(url) == "xyz789"


@patch("superset.daos.chart.ChartDAO.find_by_id")
def test_find_chart_by_identifier_int(mock_find):
    mock_chart = MagicMock()
    mock_chart.id = 42
    mock_find.return_value = mock_chart

    result = find_chart_by_identifier(42)
    mock_find.assert_called_once_with(42)
    assert result == mock_chart


@patch("superset.daos.chart.ChartDAO.find_by_id")
def test_find_chart_by_identifier_str_digit(mock_find):
    mock_chart = MagicMock()
    mock_find.return_value = mock_chart

    result = find_chart_by_identifier("123")
    mock_find.assert_called_once_with(123)
    assert result == mock_chart


@patch("superset.daos.chart.ChartDAO.find_by_id")
def test_find_chart_by_identifier_uuid(mock_find):
    mock_chart = MagicMock()
    mock_find.return_value = mock_chart

    uuid_str = "a1b2c3d4-5678-90ab-cdef-1234567890ab"
    result = find_chart_by_identifier(uuid_str)
    mock_find.assert_called_once_with(uuid_str, id_column="uuid")
    assert result == mock_chart


@patch("superset.daos.chart.ChartDAO.find_by_id")
def test_find_chart_by_identifier_not_found(mock_find):
    mock_find.return_value = None
    result = find_chart_by_identifier(999)
    assert result is None


@patch(
    "superset.commands.explore.form_data.get.GetFormDataCommand.run",
    return_value='{"viz_type": "table"}',
)
@patch("superset.commands.explore.form_data.get.GetFormDataCommand.__init__")
def test_get_cached_form_data_success(mock_init, mock_run):
    mock_init.return_value = None
    result = get_cached_form_data("test_key")
    assert result == '{"viz_type": "table"}'


@patch(
    "superset.commands.explore.form_data.get.GetFormDataCommand.run",
    side_effect=KeyError("not found"),
)
@patch("superset.commands.explore.form_data.get.GetFormDataCommand.__init__")
def test_get_cached_form_data_key_error(mock_init, mock_run):
    mock_init.return_value = None
    result = get_cached_form_data("bad_key")
    assert result is None


# ---------------------------------------------------------------------------
# _match_adhoc_by_subject
# ---------------------------------------------------------------------------


def test_match_adhoc_by_subject_returns_none_when_column_missing():
    """No column → cannot match; return None even if filters present."""
    adhoc = [{"subject": "state", "operator": "IN", "comparator": ["CA"]}]
    assert _match_adhoc_by_subject(adhoc, None) is None
    assert _match_adhoc_by_subject(adhoc, "") is None


def test_match_adhoc_by_subject_returns_none_when_filters_not_a_list():
    """Adhoc filters that are not a list (e.g. dict or None) → None."""
    assert _match_adhoc_by_subject(None, "state") is None
    assert _match_adhoc_by_subject({"subject": "state"}, "state") is None
    assert _match_adhoc_by_subject("not-a-list", "state") is None


def test_match_adhoc_by_subject_returns_operator_and_comparator_on_exact_match():
    """Match returns (operator, comparator) for the first filter whose subject equals column."""
    adhoc = [
        {"subject": "city", "operator": "==", "comparator": "SF"},
        {"subject": "state", "operator": "IN", "comparator": ["CA", "NV"]},
    ]
    assert _match_adhoc_by_subject(adhoc, "state") == ("IN", ["CA", "NV"])


def test_match_adhoc_by_subject_returns_none_when_no_subject_matches():
    """No filter has matching subject → None."""
    adhoc = [
        {"subject": "city", "operator": "==", "comparator": "SF"},
        {"subject": "region", "operator": "==", "comparator": "West"},
    ]
    assert _match_adhoc_by_subject(adhoc, "state") is None


def test_match_adhoc_by_subject_uses_exact_equality_not_substring():
    """A filter whose subject is a substring of column must NOT match."""
    adhoc = [{"subject": "stat", "operator": "==", "comparator": "ok"}]
    assert _match_adhoc_by_subject(adhoc, "state") is None


def test_match_adhoc_by_subject_rejects_substring_overlap():
    """Equality must be both-direction: column substring of subject must NOT match.

    Guards against a regression where exact `==` is relaxed to substring containment
    (e.g. `column in subject`), which would cross-pollinate filter values between
    columns that share a prefix/suffix (state ↔ metro_state).
    """
    adhoc_metro_subject = [
        {"subject": "metro_state", "operator": "IN", "comparator": ["NYC"]}
    ]
    assert _match_adhoc_by_subject(adhoc_metro_subject, "state") is None

    adhoc_state_subject = [
        {"subject": "state", "operator": "IN", "comparator": ["CA"]}
    ]
    assert _match_adhoc_by_subject(adhoc_state_subject, "metro_state") is None


def test_match_adhoc_by_subject_returns_first_match_when_duplicates():
    """First matching filter wins (in-order iteration)."""
    adhoc = [
        {"subject": "state", "operator": "==", "comparator": "CA"},
        {"subject": "state", "operator": "IN", "comparator": ["CA", "NV"]},
    ]
    assert _match_adhoc_by_subject(adhoc, "state") == ("==", "CA")


def test_match_adhoc_by_subject_skips_non_dict_entries():
    """Non-dict entries in adhoc_filters list are skipped, not raised."""
    adhoc = [
        "not-a-dict",
        None,
        {"subject": "state", "operator": "IN", "comparator": ["CA"]},
    ]
    assert _match_adhoc_by_subject(adhoc, "state") == ("IN", ["CA"])


def test_match_adhoc_by_subject_missing_operator_or_comparator_returns_none_pair():
    """A matching filter without operator/comparator returns (None, None)."""
    adhoc = [{"subject": "state"}]
    assert _match_adhoc_by_subject(adhoc, "state") == (None, None)


# ---------------------------------------------------------------------------
# _match_legacy_by_col
# ---------------------------------------------------------------------------


def test_match_legacy_by_col_returns_none_when_column_missing():
    legacy = [{"col": "state", "op": "IN", "val": ["CA"]}]
    assert _match_legacy_by_col(legacy, None) is None
    assert _match_legacy_by_col(legacy, "") is None


def test_match_legacy_by_col_returns_none_when_not_a_list():
    assert _match_legacy_by_col(None, "state") is None
    assert _match_legacy_by_col({"col": "state"}, "state") is None
    assert _match_legacy_by_col("not-a-list", "state") is None


def test_match_legacy_by_col_returns_op_and_val_on_exact_match():
    legacy = [
        {"col": "city", "op": "==", "val": "SF"},
        {"col": "state", "op": "IN", "val": ["CA", "NV"]},
    ]
    assert _match_legacy_by_col(legacy, "state") == ("IN", ["CA", "NV"])


def test_match_legacy_by_col_no_match_returns_none():
    legacy = [{"col": "city", "op": "==", "val": "SF"}]
    assert _match_legacy_by_col(legacy, "state") is None


def test_match_legacy_by_col_uses_exact_equality_not_substring():
    legacy = [{"col": "stat", "op": "==", "val": "ok"}]
    assert _match_legacy_by_col(legacy, "state") is None


def test_match_legacy_by_col_returns_first_match_when_duplicates():
    legacy = [
        {"col": "state", "op": "==", "val": "CA"},
        {"col": "state", "op": "IN", "val": ["CA", "NV"]},
    ]
    assert _match_legacy_by_col(legacy, "state") == ("==", "CA")


def test_match_legacy_by_col_skips_non_dict_entries():
    legacy = [
        "not-a-dict",
        None,
        {"col": "state", "op": "IN", "val": ["CA"]},
    ]
    assert _match_legacy_by_col(legacy, "state") == ("IN", ["CA"])


# ---------------------------------------------------------------------------
# _resolve_filter_operator_and_value
# ---------------------------------------------------------------------------


def test_resolve_filter_operator_and_value_returns_none_pair_for_empty_extra_form_data():
    assert _resolve_filter_operator_and_value(None, "state") == (None, None)
    assert _resolve_filter_operator_and_value({}, "state") == (None, None)


def test_resolve_filter_operator_and_value_dispatches_to_adhoc_first():
    """Adhoc match wins over legacy and time_range."""
    extra = {
        "adhoc_filters": [
            {"subject": "state", "operator": "IN", "comparator": ["CA"]}
        ],
        "filters": [{"col": "state", "op": "==", "val": "WRONG"}],
        "time_range": "Last week",
    }
    assert _resolve_filter_operator_and_value(extra, "state") == ("IN", ["CA"])


def test_resolve_filter_operator_and_value_dispatches_to_legacy_when_no_adhoc_match():
    """Legacy filters are consulted when adhoc has no matching subject."""
    extra = {
        "adhoc_filters": [
            {"subject": "city", "operator": "==", "comparator": "SF"}
        ],
        "filters": [{"col": "state", "op": "IN", "val": ["CA"]}],
    }
    assert _resolve_filter_operator_and_value(extra, "state") == ("IN", ["CA"])


def test_resolve_filter_operator_and_value_falls_back_to_time_range_when_no_column_match():
    """When no column-matching filter, time_range is returned with operator='TIME_RANGE'."""
    extra = {"time_range": "Last 7 days"}
    assert _resolve_filter_operator_and_value(extra, "state") == (
        "TIME_RANGE",
        "Last 7 days",
    )


def test_resolve_filter_operator_and_value_time_range_used_when_column_is_none():
    """Temporal filters have no target column; column=None falls to time_range."""
    extra = {"time_range": "Last month"}
    assert _resolve_filter_operator_and_value(extra, None) == (
        "TIME_RANGE",
        "Last month",
    )


def test_resolve_filter_operator_and_value_returns_none_pair_when_nothing_resolves():
    extra = {"adhoc_filters": [], "filters": []}
    assert _resolve_filter_operator_and_value(extra, "state") == (None, None)


def test_resolve_filter_operator_and_value_empty_time_range_falls_through():
    """An empty time_range string is falsy and should not be returned."""
    extra = {"time_range": ""}
    assert _resolve_filter_operator_and_value(extra, "state") == (None, None)


# ---------------------------------------------------------------------------
# build_applied_dashboard_filters
# ---------------------------------------------------------------------------


def _mock_dashboard(
    *,
    slice_ids: list[int],
    native_filter_configuration=None,
    position_json: dict | None = None,
):
    """Build a mock Dashboard with the given slices and JSON metadata."""
    from superset.utils import json as utils_json

    metadata = {}
    if native_filter_configuration is not None:
        metadata["native_filter_configuration"] = native_filter_configuration

    dashboard = MagicMock()
    dashboard.slices = [MagicMock(id=sid) for sid in slice_ids]
    dashboard.json_metadata = utils_json.dumps(metadata)
    dashboard.position_json = utils_json.dumps(position_json or {})
    return dashboard


def _patches_for_build(dashboard, raise_for_access=None):
    """Context for build_applied_dashboard_filters with a mocked DB and SM."""
    from contextlib import ExitStack

    stack = ExitStack()
    query_mock = MagicMock()
    query_mock.filter_by.return_value.one_or_none.return_value = dashboard
    stack.enter_context(
        patch("superset.db.session.query", return_value=query_mock)
    )
    sm_patch = patch(
        "superset.security_manager.raise_for_access",
        side_effect=raise_for_access,
    )
    stack.enter_context(sm_patch)
    return stack


def test_build_applied_dashboard_filters_raises_when_dashboard_missing():
    from superset.commands.dashboard.exceptions import DashboardNotFoundError

    with _patches_for_build(dashboard=None):
        with pytest.raises(DashboardNotFoundError):
            build_applied_dashboard_filters(dashboard_id=999, chart_id=1)


def test_build_applied_dashboard_filters_propagates_security_exception():
    from superset.exceptions import SupersetSecurityException

    dashboard = _mock_dashboard(slice_ids=[1])
    sec_exc = SupersetSecurityException(MagicMock())
    with _patches_for_build(dashboard, raise_for_access=sec_exc):
        with pytest.raises(SupersetSecurityException):
            build_applied_dashboard_filters(dashboard_id=1, chart_id=1)


def test_build_applied_dashboard_filters_raises_when_chart_not_on_dashboard():
    dashboard = _mock_dashboard(slice_ids=[2, 3, 4])
    with _patches_for_build(dashboard):
        with pytest.raises(ChartNotOnDashboardError) as exc_info:
            build_applied_dashboard_filters(dashboard_id=10, chart_id=1)
    assert "Chart 1" in str(exc_info.value)
    assert "dashboard 10" in str(exc_info.value)


def test_build_applied_dashboard_filters_empty_when_no_native_filters():
    dashboard = _mock_dashboard(slice_ids=[1], native_filter_configuration=[])
    with _patches_for_build(dashboard):
        result = build_applied_dashboard_filters(dashboard_id=1, chart_id=1)
    assert result == []


def test_build_applied_dashboard_filters_empty_when_metadata_missing():
    """No json_metadata at all defaults to empty list."""
    dashboard = MagicMock()
    dashboard.slices = [MagicMock(id=1)]
    dashboard.json_metadata = None
    dashboard.position_json = None
    with _patches_for_build(dashboard):
        result = build_applied_dashboard_filters(dashboard_id=1, chart_id=1)
    assert result == []


def test_build_applied_dashboard_filters_returns_empty_when_native_filter_config_not_a_list():
    from superset.utils import json as utils_json

    dashboard = MagicMock()
    dashboard.slices = [MagicMock(id=1)]
    dashboard.json_metadata = utils_json.dumps(
        {"native_filter_configuration": {"oops": "not-a-list"}}
    )
    dashboard.position_json = utils_json.dumps({})
    with _patches_for_build(dashboard):
        result = build_applied_dashboard_filters(dashboard_id=1, chart_id=1)
    assert result == []


def test_build_applied_dashboard_filters_handles_position_json_not_a_dict():
    """A non-dict position_json should be replaced with {}, not crash."""
    from superset.utils import json as utils_json

    dashboard = MagicMock()
    dashboard.slices = [MagicMock(id=1)]
    dashboard.json_metadata = utils_json.dumps(
        {
            "native_filter_configuration": [
                {
                    "id": "NATIVE_FILTER-abc",
                    "type": "NATIVE_FILTER",
                    "name": "State",
                    "filterType": "filter_select",
                    "chartsInScope": [1],
                    "targets": [{"column": {"name": "state"}}],
                    "defaultDataMask": {
                        "filterState": {"value": ["CA"]},
                        "extraFormData": {
                            "filters": [
                                {"col": "state", "op": "IN", "val": ["CA"]}
                            ]
                        },
                    },
                }
            ]
        }
    )
    dashboard.position_json = utils_json.dumps(["not", "a", "dict"])
    with _patches_for_build(dashboard):
        result = build_applied_dashboard_filters(dashboard_id=1, chart_id=1)
    # chartsInScope present → in scope → 1 filter emitted
    assert len(result) == 1
    assert result[0].id == "NATIVE_FILTER-abc"


def test_build_applied_dashboard_filters_skips_divider_filters():
    """DIVIDER native filters are layout-only and must be excluded."""
    dashboard = _mock_dashboard(
        slice_ids=[1],
        native_filter_configuration=[
            {
                "id": "DIVIDER-1",
                "type": "DIVIDER",
                "name": "Section break",
            }
        ],
    )
    with _patches_for_build(dashboard):
        result = build_applied_dashboard_filters(dashboard_id=1, chart_id=1)
    assert result == []


def test_build_applied_dashboard_filters_skips_divider_even_when_in_scope():
    """DIVIDER filters are excluded even when chartsInScope includes the chart.

    Pins the `type == \"DIVIDER\"` early-continue independently of the scope check:
    if the scope check alone were relied on, removing the DIVIDER guard would still
    let layout-only entries leak into AppliedDashboardFilter output.
    """
    dashboard = _mock_dashboard(
        slice_ids=[1],
        native_filter_configuration=[
            {
                "id": "DIVIDER-1",
                "type": "DIVIDER",
                "name": "Section break",
                "chartsInScope": [1],
                "targets": [{"column": {"name": "state"}}],
                "defaultDataMask": {
                    "filterState": {"value": ["CA"]},
                    "extraFormData": {
                        "filters": [{"col": "state", "op": "IN", "val": ["CA"]}]
                    },
                },
            }
        ],
    )
    with _patches_for_build(dashboard):
        result = build_applied_dashboard_filters(dashboard_id=1, chart_id=1)
    assert result == []


def test_build_applied_dashboard_filters_skips_filters_not_in_scope():
    """Filters whose chartsInScope excludes the chart are skipped."""
    dashboard = _mock_dashboard(
        slice_ids=[1],
        native_filter_configuration=[
            {
                "id": "NATIVE_FILTER-1",
                "type": "NATIVE_FILTER",
                "name": "Excluded filter",
                "filterType": "filter_select",
                "chartsInScope": [2, 3],  # chart 1 NOT included
                "targets": [{"column": {"name": "state"}}],
                "defaultDataMask": {
                    "filterState": {"value": ["CA"]},
                    "extraFormData": {
                        "filters": [{"col": "state", "op": "IN", "val": ["CA"]}]
                    },
                },
            }
        ],
    )
    with _patches_for_build(dashboard):
        result = build_applied_dashboard_filters(dashboard_id=1, chart_id=1)
    assert result == []


def test_build_applied_dashboard_filters_skips_non_dict_entries():
    """Non-dict entries in the native_filter_configuration list are skipped."""
    dashboard = _mock_dashboard(
        slice_ids=[1], native_filter_configuration=["not-a-dict", None, 42]
    )
    with _patches_for_build(dashboard):
        result = build_applied_dashboard_filters(dashboard_id=1, chart_id=1)
    assert result == []


def test_build_applied_dashboard_filters_applied_filter_with_legacy_extra_form_data():
    """Legacy `filters` array contributes op/val for AppliedDashboardFilter."""
    dashboard = _mock_dashboard(
        slice_ids=[1],
        native_filter_configuration=[
            {
                "id": "NATIVE_FILTER-1",
                "type": "NATIVE_FILTER",
                "name": "State filter",
                "filterType": "filter_select",
                "chartsInScope": [1],
                "targets": [{"column": {"name": "state"}}],
                "defaultDataMask": {
                    "filterState": {"value": ["CA"]},
                    "extraFormData": {
                        "filters": [{"col": "state", "op": "IN", "val": ["CA"]}]
                    },
                },
            }
        ],
    )
    with _patches_for_build(dashboard):
        result = build_applied_dashboard_filters(dashboard_id=1, chart_id=1)
    assert len(result) == 1
    flt = result[0]
    assert flt.id == "NATIVE_FILTER-1"
    assert flt.name == "State filter"
    assert flt.filter_type == "filter_select"
    assert flt.column == "state"
    assert flt.operator == "IN"
    assert flt.value == ["CA"]
    assert flt.status == "applied"


def test_build_applied_dashboard_filters_applied_filter_with_adhoc_form_data():
    """Adhoc filters contribute operator/comparator for AppliedDashboardFilter."""
    dashboard = _mock_dashboard(
        slice_ids=[1],
        native_filter_configuration=[
            {
                "id": "NATIVE_FILTER-2",
                "type": "NATIVE_FILTER",
                "name": "City filter",
                "filterType": "filter_select",
                "chartsInScope": [1],
                "targets": [{"column": {"name": "city"}}],
                "defaultDataMask": {
                    "filterState": {"value": ["SF"]},
                    "extraFormData": {
                        "adhoc_filters": [
                            {
                                "subject": "city",
                                "operator": "==",
                                "comparator": "SF",
                            }
                        ]
                    },
                },
            }
        ],
    )
    with _patches_for_build(dashboard):
        result = build_applied_dashboard_filters(dashboard_id=1, chart_id=1)
    assert len(result) == 1
    assert result[0].operator == "=="
    assert result[0].value == "SF"
    assert result[0].status == "applied"


def test_build_applied_dashboard_filters_time_range_filter():
    """Temporal filter without a target column gets operator='TIME_RANGE'."""
    dashboard = _mock_dashboard(
        slice_ids=[1],
        native_filter_configuration=[
            {
                "id": "NATIVE_FILTER-3",
                "type": "NATIVE_FILTER",
                "name": "Time range",
                "filterType": "filter_time",
                "chartsInScope": [1],
                "targets": [{}],  # no column
                "defaultDataMask": {
                    "filterState": {"value": "Last 7 days"},
                    "extraFormData": {"time_range": "Last 7 days"},
                },
            }
        ],
    )
    with _patches_for_build(dashboard):
        result = build_applied_dashboard_filters(dashboard_id=1, chart_id=1)
    assert len(result) == 1
    assert result[0].column is None
    assert result[0].operator == "TIME_RANGE"
    assert result[0].value == "Last 7 days"
    assert result[0].status == "applied"


def test_build_applied_dashboard_filters_not_applied_when_no_default():
    """Filter without a static default has status='not_applied' (operator/value None)."""
    dashboard = _mock_dashboard(
        slice_ids=[1],
        native_filter_configuration=[
            {
                "id": "NATIVE_FILTER-4",
                "type": "NATIVE_FILTER",
                "name": "Region",
                "filterType": "filter_select",
                "chartsInScope": [1],
                "targets": [{"column": {"name": "region"}}],
                "defaultDataMask": {},  # no filterState.value, no extraFormData
            }
        ],
    )
    with _patches_for_build(dashboard):
        result = build_applied_dashboard_filters(dashboard_id=1, chart_id=1)
    assert len(result) == 1
    assert result[0].status == "not_applied"
    assert result[0].operator is None
    assert result[0].value is None


def test_build_applied_dashboard_filters_default_to_first_item_status():
    """defaultToFirstItem filters get a special 'not_applied_uses_default…' status."""
    dashboard = _mock_dashboard(
        slice_ids=[1],
        native_filter_configuration=[
            {
                "id": "NATIVE_FILTER-5",
                "type": "NATIVE_FILTER",
                "name": "Default-first",
                "filterType": "filter_select",
                "chartsInScope": [1],
                "controlValues": {"defaultToFirstItem": True},
                "targets": [{"column": {"name": "state"}}],
                "defaultDataMask": {},
            }
        ],
    )
    with _patches_for_build(dashboard):
        result = build_applied_dashboard_filters(dashboard_id=1, chart_id=1)
    assert len(result) == 1
    assert result[0].status == "not_applied_uses_default_to_first_item_prequery"


def test_build_applied_dashboard_filters_status_is_string_not_enum():
    """status must be the .value (str), not the DashboardFilterStatus enum object."""
    dashboard = _mock_dashboard(
        slice_ids=[1],
        native_filter_configuration=[
            {
                "id": "NATIVE_FILTER-6",
                "type": "NATIVE_FILTER",
                "name": "Region",
                "filterType": "filter_select",
                "chartsInScope": [1],
                "targets": [{"column": {"name": "region"}}],
                "defaultDataMask": {},
            }
        ],
    )
    with _patches_for_build(dashboard):
        result = build_applied_dashboard_filters(dashboard_id=1, chart_id=1)
    assert isinstance(result[0].status, str)


def test_build_applied_dashboard_filters_omits_filters_not_in_scope_via_scope_path():
    """Without chartsInScope, scope.rootPath + position_json is used; out-of-scope is omitted."""
    from superset.utils import json as utils_json

    dashboard = MagicMock()
    dashboard.slices = [MagicMock(id=1)]
    dashboard.json_metadata = utils_json.dumps(
        {
            "native_filter_configuration": [
                {
                    "id": "NATIVE_FILTER-7",
                    "type": "NATIVE_FILTER",
                    "name": "Region",
                    "filterType": "filter_select",
                    "scope": {"rootPath": ["TAB_other"], "excluded": []},
                    "targets": [{"column": {"name": "region"}}],
                    "defaultDataMask": {
                        "filterState": {"value": "EMEA"},
                        "extraFormData": {
                            "filters": [
                                {"col": "region", "op": "==", "val": "EMEA"}
                            ]
                        },
                    },
                }
            ]
        }
    )
    dashboard.position_json = utils_json.dumps(
        {
            "CHART-1": {
                "type": "CHART",
                "meta": {"chartId": 1},
                "parents": ["TAB_main"],
            }
        }
    )
    with _patches_for_build(dashboard):
        result = build_applied_dashboard_filters(dashboard_id=1, chart_id=1)
    assert result == []


def test_build_applied_dashboard_filters_target_column_as_plain_string():
    """Some legacy filter configs use targets[0].column as a string, not a dict."""
    dashboard = _mock_dashboard(
        slice_ids=[1],
        native_filter_configuration=[
            {
                "id": "NATIVE_FILTER-8",
                "type": "NATIVE_FILTER",
                "name": "Region",
                "filterType": "filter_select",
                "chartsInScope": [1],
                "targets": [{"column": "region"}],
                "defaultDataMask": {
                    "filterState": {"value": "EMEA"},
                    "extraFormData": {
                        "filters": [
                            {"col": "region", "op": "==", "val": "EMEA"}
                        ]
                    },
                },
            }
        ],
    )
    with _patches_for_build(dashboard):
        result = build_applied_dashboard_filters(dashboard_id=1, chart_id=1)
    assert len(result) == 1
    assert result[0].column == "region"
    assert result[0].operator == "=="


def test_build_applied_dashboard_filters_multiple_filters_preserves_order():
    """Multiple in-scope native filters → one AppliedDashboardFilter each, in order."""
    dashboard = _mock_dashboard(
        slice_ids=[1],
        native_filter_configuration=[
            {
                "id": "F-A",
                "type": "NATIVE_FILTER",
                "name": "A",
                "filterType": "filter_select",
                "chartsInScope": [1],
                "targets": [{"column": {"name": "a"}}],
                "defaultDataMask": {
                    "filterState": {"value": ["x"]},
                    "extraFormData": {
                        "filters": [{"col": "a", "op": "IN", "val": ["x"]}]
                    },
                },
            },
            {
                "id": "F-B",
                "type": "NATIVE_FILTER",
                "name": "B",
                "filterType": "filter_select",
                "chartsInScope": [1],
                "targets": [{"column": {"name": "b"}}],
                "defaultDataMask": {
                    "filterState": {"value": ["y"]},
                    "extraFormData": {
                        "filters": [{"col": "b", "op": "IN", "val": ["y"]}]
                    },
                },
            },
        ],
    )
    with _patches_for_build(dashboard):
        result = build_applied_dashboard_filters(dashboard_id=1, chart_id=1)
    assert [f.id for f in result] == ["F-A", "F-B"]
    assert [f.column for f in result] == ["a", "b"]

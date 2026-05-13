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

from typing import Any
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


def test_match_adhoc_by_subject_returns_operator_and_comparator():
    adhoc = [
        {"subject": "country", "operator": "==", "comparator": "US"},
        {"subject": "region", "operator": "IN", "comparator": ["EMEA"]},
    ]
    assert _match_adhoc_by_subject(adhoc, "region") == ("IN", ["EMEA"])


def test_match_adhoc_by_subject_returns_first_match():
    adhoc = [
        {"subject": "region", "operator": "==", "comparator": "US"},
        {"subject": "region", "operator": "IN", "comparator": ["EMEA"]},
    ]
    assert _match_adhoc_by_subject(adhoc, "region") == ("==", "US")


def test_match_adhoc_by_subject_no_match_returns_none():
    adhoc = [{"subject": "country", "operator": "==", "comparator": "US"}]
    assert _match_adhoc_by_subject(adhoc, "region") is None


def test_match_adhoc_by_subject_skips_non_dict_entries():
    adhoc = [
        "not a dict",
        None,
        {"subject": "region", "operator": "IN", "comparator": ["EMEA"]},
    ]
    assert _match_adhoc_by_subject(adhoc, "region") == ("IN", ["EMEA"])


def test_match_adhoc_by_subject_none_column_returns_none():
    adhoc = [{"subject": "region", "operator": "IN", "comparator": ["EMEA"]}]
    assert _match_adhoc_by_subject(adhoc, None) is None


def test_match_adhoc_by_subject_non_list_input_returns_none():
    assert _match_adhoc_by_subject({"subject": "region"}, "region") is None
    assert _match_adhoc_by_subject(None, "region") is None
    assert _match_adhoc_by_subject("string", "region") is None


def test_match_adhoc_by_subject_missing_operator_or_comparator():
    """Match still returns the tuple even if operator/comparator are missing."""
    adhoc = [{"subject": "region"}]
    assert _match_adhoc_by_subject(adhoc, "region") == (None, None)


def test_match_adhoc_by_subject_requires_exact_equality_not_substring():
    """A column that is a substring of a subject must not falsely match."""
    adhoc = [
        {"subject": "regional_code", "operator": "==", "comparator": "X"},
        {"subject": "region_id", "operator": "IN", "comparator": ["Y"]},
    ]
    # 'region' is a substring of both subjects but not equal to either.
    assert _match_adhoc_by_subject(adhoc, "region") is None


def test_match_adhoc_by_subject_prefers_exact_over_substring_neighbor():
    """When both an exact-match and a substring-neighbor exist, exact match wins."""
    adhoc = [
        {"subject": "regional_code", "operator": "==", "comparator": "WRONG"},
        {"subject": "region", "operator": "IN", "comparator": ["RIGHT"]},
    ]
    assert _match_adhoc_by_subject(adhoc, "region") == ("IN", ["RIGHT"])


# ---------------------------------------------------------------------------
# _match_legacy_by_col
# ---------------------------------------------------------------------------


def test_match_legacy_by_col_returns_op_and_val():
    legacy = [
        {"col": "country", "op": "==", "val": "US"},
        {"col": "region", "op": "IN", "val": ["EMEA"]},
    ]
    assert _match_legacy_by_col(legacy, "region") == ("IN", ["EMEA"])


def test_match_legacy_by_col_no_match_returns_none():
    legacy = [{"col": "country", "op": "==", "val": "US"}]
    assert _match_legacy_by_col(legacy, "region") is None


def test_match_legacy_by_col_skips_non_dict_entries():
    legacy = [
        42,
        None,
        {"col": "region", "op": "==", "val": "US"},
    ]
    assert _match_legacy_by_col(legacy, "region") == ("==", "US")


def test_match_legacy_by_col_none_column_returns_none():
    legacy = [{"col": "region", "op": "IN", "val": ["EMEA"]}]
    assert _match_legacy_by_col(legacy, None) is None


def test_match_legacy_by_col_non_list_input_returns_none():
    assert _match_legacy_by_col({"col": "region"}, "region") is None
    assert _match_legacy_by_col(None, "region") is None


# ---------------------------------------------------------------------------
# _resolve_filter_operator_and_value
# ---------------------------------------------------------------------------


def test_resolve_returns_none_none_when_extra_form_data_falsy():
    assert _resolve_filter_operator_and_value(None, "region") == (None, None)
    assert _resolve_filter_operator_and_value({}, "region") == (None, None)


def test_resolve_prefers_adhoc_over_legacy_and_time_range():
    extra = {
        "adhoc_filters": [
            {"subject": "region", "operator": "IN", "comparator": ["EMEA"]}
        ],
        "filters": [{"col": "region", "op": "==", "val": "US"}],
        "time_range": "Last 7 days",
    }
    assert _resolve_filter_operator_and_value(extra, "region") == ("IN", ["EMEA"])


def test_resolve_falls_back_to_legacy_when_adhoc_does_not_match():
    extra = {
        "adhoc_filters": [
            {"subject": "country", "operator": "==", "comparator": "US"}
        ],
        "filters": [{"col": "region", "op": "IN", "val": ["EMEA"]}],
    }
    assert _resolve_filter_operator_and_value(extra, "region") == ("IN", ["EMEA"])


def test_resolve_falls_back_to_time_range_when_no_column_match():
    extra = {
        "adhoc_filters": [{"subject": "other", "operator": "==", "comparator": "x"}],
        "filters": [{"col": "other", "op": "==", "val": "x"}],
        "time_range": "Last 7 days",
    }
    # column is None to mimic temporal filters
    assert _resolve_filter_operator_and_value(extra, None) == ("TIME_RANGE", "Last 7 days")


def test_resolve_time_range_used_when_column_not_in_filters():
    extra = {"time_range": "No filter"}
    assert _resolve_filter_operator_and_value(extra, "region") == (
        "TIME_RANGE",
        "No filter",
    )


def test_resolve_returns_none_when_no_matches_and_no_time_range():
    extra = {
        "adhoc_filters": [{"subject": "other", "operator": "==", "comparator": "x"}],
        "filters": [{"col": "other", "op": "==", "val": "x"}],
    }
    assert _resolve_filter_operator_and_value(extra, "region") == (None, None)


def test_resolve_does_not_substring_match_adhoc_subject():
    """`region` must not erroneously match adhoc subject `region_id`."""
    extra = {
        "adhoc_filters": [{"subject": "region_id", "operator": "==", "comparator": "X"}],
        "time_range": "Last 7 days",
    }
    # If the adhoc match used substring, it would short-circuit to ("==", "X").
    # The expected behavior is no adhoc match, then no legacy match, then the
    # time_range fallback is returned for a non-temporal column.
    assert _resolve_filter_operator_and_value(extra, "region") == (
        "TIME_RANGE",
        "Last 7 days",
    )


# ---------------------------------------------------------------------------
# build_applied_dashboard_filters
# ---------------------------------------------------------------------------


def _make_dashboard_mock(
    *,
    slice_ids: list[int] | None = None,
    json_metadata: str | None = None,
    position_json: str | None = None,
):
    """Build a Dashboard-like mock."""
    dashboard = MagicMock()
    dashboard.id = 45
    dashboard.json_metadata = json_metadata
    dashboard.position_json = position_json
    dashboard.slices = [MagicMock(id=sid) for sid in (slice_ids or [])]
    return dashboard


def _patch_dashboard_query(dashboard):
    """Patch db.session.query(Dashboard).filter_by(id=...).one_or_none() chain."""
    query = MagicMock()
    query.filter_by.return_value.one_or_none.return_value = dashboard
    session = MagicMock()
    session.query.return_value = query
    return patch("superset.db.session", session)


@patch("superset.security_manager.raise_for_access")
def test_build_applied_dashboard_filters_dashboard_missing(mock_raise):
    from superset.commands.dashboard.exceptions import DashboardNotFoundError

    with _patch_dashboard_query(None):
        with pytest.raises(DashboardNotFoundError):
            build_applied_dashboard_filters(99, 10)
    mock_raise.assert_not_called()


@patch("superset.security_manager.raise_for_access")
def test_build_applied_dashboard_filters_access_check_called(mock_raise):
    dashboard = _make_dashboard_mock(slice_ids=[10])
    with _patch_dashboard_query(dashboard):
        build_applied_dashboard_filters(45, 10)
    mock_raise.assert_called_once_with(dashboard=dashboard)


@patch("superset.security_manager.raise_for_access")
def test_build_applied_dashboard_filters_security_exception_propagates(mock_raise):
    from superset.exceptions import SupersetSecurityException
    from superset.errors import SupersetError, SupersetErrorType, ErrorLevel

    err = SupersetError(
        message="nope",
        error_type=SupersetErrorType.DASHBOARD_SECURITY_ACCESS_ERROR,
        level=ErrorLevel.ERROR,
    )
    mock_raise.side_effect = SupersetSecurityException(err)
    dashboard = _make_dashboard_mock(slice_ids=[10])
    with _patch_dashboard_query(dashboard):
        with pytest.raises(SupersetSecurityException):
            build_applied_dashboard_filters(45, 10)


@patch("superset.security_manager.raise_for_access")
def test_build_applied_dashboard_filters_chart_not_on_dashboard(mock_raise):
    dashboard = _make_dashboard_mock(slice_ids=[20, 30])
    with _patch_dashboard_query(dashboard):
        with pytest.raises(ChartNotOnDashboardError) as exc_info:
            build_applied_dashboard_filters(45, 10)
    assert "Chart 10 is not on dashboard 45" in str(exc_info.value)


@patch("superset.security_manager.raise_for_access")
def test_build_applied_dashboard_filters_chart_on_dashboard_no_filters(mock_raise):
    """Chart is on dashboard, no native_filter_configuration."""
    dashboard = _make_dashboard_mock(slice_ids=[10], json_metadata="{}")
    with _patch_dashboard_query(dashboard):
        result = build_applied_dashboard_filters(45, 10)
    assert result == []


@patch("superset.security_manager.raise_for_access")
def test_build_applied_dashboard_filters_native_filter_config_not_list(mock_raise):
    """If native_filter_configuration is not a list, returns []."""
    metadata = '{"native_filter_configuration": "oops"}'
    dashboard = _make_dashboard_mock(slice_ids=[10], json_metadata=metadata)
    with _patch_dashboard_query(dashboard):
        result = build_applied_dashboard_filters(45, 10)
    assert result == []


def _native_filter(
    *,
    flt_id: str = "NATIVE_FILTER-1",
    name: str = "Region Filter",
    filter_type: str = "filter_select",
    column: str | None = "region",
    flt_type: str = "NATIVE_FILTER",
    charts_in_scope: list[int] | None = None,
    default_value: list[str] | None = None,
    extra_form_data: dict[str, Any] | None = None,
    default_to_first_item: bool = False,
) -> dict[str, Any]:
    flt: dict[str, Any] = {
        "id": flt_id,
        "name": name,
        "type": flt_type,
        "filterType": filter_type,
        "targets": [{"datasetId": 1, "column": {"name": column}}]
        if column
        else [],
        "scope": {"rootPath": ["ROOT_ID"], "excluded": []},
        "controlValues": {"defaultToFirstItem": default_to_first_item},
        "defaultDataMask": {},
    }
    if charts_in_scope is not None:
        flt["chartsInScope"] = charts_in_scope
    if default_value is not None:
        flt["defaultDataMask"]["filterState"] = {"value": default_value}
        if extra_form_data is None:
            extra_form_data = {
                "filters": [{"col": column, "op": "IN", "val": default_value}]
            }
    if extra_form_data is not None:
        flt["defaultDataMask"]["extraFormData"] = extra_form_data
    return flt


@patch("superset.security_manager.raise_for_access")
def test_build_applied_dashboard_filters_divider_skipped(mock_raise):
    from superset.utils import json

    flt = _native_filter(flt_type="DIVIDER", charts_in_scope=[10])
    metadata = json.dumps({"native_filter_configuration": [flt]})
    dashboard = _make_dashboard_mock(slice_ids=[10], json_metadata=metadata)
    with _patch_dashboard_query(dashboard):
        result = build_applied_dashboard_filters(45, 10)
    assert result == []


@patch("superset.security_manager.raise_for_access")
def test_build_applied_dashboard_filters_out_of_scope_skipped(mock_raise):
    from superset.utils import json

    flt = _native_filter(charts_in_scope=[20])
    metadata = json.dumps({"native_filter_configuration": [flt]})
    dashboard = _make_dashboard_mock(slice_ids=[10], json_metadata=metadata)
    with _patch_dashboard_query(dashboard):
        result = build_applied_dashboard_filters(45, 10)
    assert result == []


@patch("superset.security_manager.raise_for_access")
def test_build_applied_dashboard_filters_non_dict_filter_skipped(mock_raise):
    """A non-dict entry in native_filter_configuration must be skipped, not crash."""
    from superset.utils import json

    metadata = json.dumps({"native_filter_configuration": ["not-a-filter", None]})
    dashboard = _make_dashboard_mock(slice_ids=[10], json_metadata=metadata)
    with _patch_dashboard_query(dashboard):
        result = build_applied_dashboard_filters(45, 10)
    assert result == []


@patch("superset.security_manager.raise_for_access")
def test_build_applied_dashboard_filters_applied_legacy_filter(mock_raise):
    from superset.utils import json

    flt = _native_filter(
        charts_in_scope=[10],
        default_value=["EMEA"],
    )
    metadata = json.dumps({"native_filter_configuration": [flt]})
    dashboard = _make_dashboard_mock(slice_ids=[10], json_metadata=metadata)
    with _patch_dashboard_query(dashboard):
        result = build_applied_dashboard_filters(45, 10)
    assert len(result) == 1
    af = result[0]
    assert af.id == "NATIVE_FILTER-1"
    assert af.name == "Region Filter"
    assert af.filter_type == "filter_select"
    assert af.column == "region"
    assert af.operator == "IN"
    assert af.value == ["EMEA"]
    assert af.status == "applied"


@patch("superset.security_manager.raise_for_access")
def test_build_applied_dashboard_filters_applied_adhoc_filter(mock_raise):
    from superset.utils import json

    extra = {
        "adhoc_filters": [
            {"subject": "region", "operator": "==", "comparator": "EMEA"}
        ]
    }
    flt = _native_filter(
        charts_in_scope=[10],
        default_value=["EMEA"],
        extra_form_data=extra,
    )
    metadata = json.dumps({"native_filter_configuration": [flt]})
    dashboard = _make_dashboard_mock(slice_ids=[10], json_metadata=metadata)
    with _patch_dashboard_query(dashboard):
        result = build_applied_dashboard_filters(45, 10)
    assert len(result) == 1
    assert result[0].operator == "=="
    assert result[0].value == "EMEA"


@patch("superset.security_manager.raise_for_access")
def test_build_applied_dashboard_filters_temporal_time_range(mock_raise):
    from superset.utils import json

    extra = {"time_range": "Last 7 days"}
    flt = _native_filter(
        flt_id="NATIVE_FILTER-2",
        name="Time Filter",
        filter_type="filter_time",
        column=None,
        charts_in_scope=[10],
        default_value=["Last 7 days"],
        extra_form_data=extra,
    )
    metadata = json.dumps({"native_filter_configuration": [flt]})
    dashboard = _make_dashboard_mock(slice_ids=[10], json_metadata=metadata)
    with _patch_dashboard_query(dashboard):
        result = build_applied_dashboard_filters(45, 10)
    assert len(result) == 1
    assert result[0].column is None
    assert result[0].operator == "TIME_RANGE"
    assert result[0].value == "Last 7 days"


@patch("superset.security_manager.raise_for_access")
def test_build_applied_dashboard_filters_not_applied_status(mock_raise):
    """A filter without a static default is included with status=not_applied."""
    from superset.utils import json

    flt = _native_filter(charts_in_scope=[10])
    metadata = json.dumps({"native_filter_configuration": [flt]})
    dashboard = _make_dashboard_mock(slice_ids=[10], json_metadata=metadata)
    with _patch_dashboard_query(dashboard):
        result = build_applied_dashboard_filters(45, 10)
    assert len(result) == 1
    assert result[0].status == "not_applied"
    assert result[0].operator is None
    assert result[0].value is None


@patch("superset.security_manager.raise_for_access")
def test_build_applied_dashboard_filters_default_to_first_item_status(mock_raise):
    from superset.utils import json

    flt = _native_filter(charts_in_scope=[10], default_to_first_item=True)
    metadata = json.dumps({"native_filter_configuration": [flt]})
    dashboard = _make_dashboard_mock(slice_ids=[10], json_metadata=metadata)
    with _patch_dashboard_query(dashboard):
        result = build_applied_dashboard_filters(45, 10)
    assert len(result) == 1
    assert result[0].status == "not_applied_uses_default_to_first_item_prequery"


@patch("superset.security_manager.raise_for_access")
def test_build_applied_dashboard_filters_position_json_not_dict(mock_raise):
    """Non-dict position_json must fall back to {} and not crash."""
    from superset.utils import json

    flt = _native_filter(charts_in_scope=[10], default_value=["EMEA"])
    metadata = json.dumps({"native_filter_configuration": [flt]})
    dashboard = _make_dashboard_mock(
        slice_ids=[10],
        json_metadata=metadata,
        position_json='["not", "a", "dict"]',
    )
    with _patch_dashboard_query(dashboard):
        result = build_applied_dashboard_filters(45, 10)
    # Filter is in scope via chartsInScope so it still appears.
    assert len(result) == 1


@patch("superset.security_manager.raise_for_access")
def test_build_applied_dashboard_filters_multiple_filters_in_order(mock_raise):
    """Multiple in-scope filters preserve their order in the output list."""
    from superset.utils import json

    f1 = _native_filter(
        flt_id="F1",
        name="First",
        charts_in_scope=[10],
        default_value=["A"],
    )
    f2 = _native_filter(
        flt_id="F2",
        name="Second",
        charts_in_scope=[10],
        column="country",
        default_value=["US"],
    )
    metadata = json.dumps({"native_filter_configuration": [f1, f2]})
    dashboard = _make_dashboard_mock(slice_ids=[10], json_metadata=metadata)
    with _patch_dashboard_query(dashboard):
        result = build_applied_dashboard_filters(45, 10)
    assert [r.id for r in result] == ["F1", "F2"]


@patch("superset.security_manager.raise_for_access")
def test_build_applied_dashboard_filters_uses_scope_root_path(mock_raise):
    """When chartsInScope is absent, scope.rootPath plus position_json drives scope."""
    from superset.utils import json

    flt = _native_filter(default_value=["EMEA"])
    flt.pop("chartsInScope", None)
    metadata = json.dumps({"native_filter_configuration": [flt]})
    position = {
        "CHART-10": {
            "type": "CHART",
            "meta": {"chartId": 10},
            "parents": ["ROOT_ID"],
        },
    }
    dashboard = _make_dashboard_mock(
        slice_ids=[10],
        json_metadata=metadata,
        position_json=json.dumps(position),
    )
    with _patch_dashboard_query(dashboard):
        result = build_applied_dashboard_filters(45, 10)
    assert len(result) == 1
    assert result[0].id == "NATIVE_FILTER-1"

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
Unit tests for get_chart_info MCP tool privacy behavior.
"""

import importlib
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastmcp import Client

from superset.mcp_service.app import mcp
from superset.mcp_service.chart.schemas import (
    AppliedDashboardFilter,
    ChartFiltersInfo,
    ChartInfo,
    extract_filters_from_form_data,
    GetChartInfoRequest,
    sanitize_chart_info_for_llm_context,
)
from superset.mcp_service.utils.sanitization import (
    LLM_CONTEXT_CLOSE_DELIMITER,
    LLM_CONTEXT_ESCAPED_CLOSE_DELIMITER,
    LLM_CONTEXT_OPEN_DELIMITER,
)
from superset.utils import json

get_chart_info_module = importlib.import_module(
    "superset.mcp_service.chart.tool.get_chart_info"
)


def _wrapped(value: str) -> str:
    """Return the expected LLM-context wrapper for assertions."""
    return f"{LLM_CONTEXT_OPEN_DELIMITER}\n{value}\n{LLM_CONTEXT_CLOSE_DELIMITER}"


@pytest.fixture
def mcp_server():
    return mcp


@pytest.fixture(autouse=True)
def mock_auth():
    with patch("superset.mcp_service.auth.get_user_from_request") as mock_get_user:
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = "admin"
        mock_get_user.return_value = mock_user
        yield


def _make_chart_info() -> ChartInfo:
    form_data = {
        "viz_type": "table",
        "datasource": "12__table",
        "datasource_name": "vehicle_sales",
        "filters": [{"col": "state", "op": "IN", "val": ["CA"]}],
    }
    return ChartInfo(
        id=123,
        slice_name="Vehicle Sales",
        viz_type="table",
        datasource_name="vehicle_sales",
        datasource_type="table",
        filters=extract_filters_from_form_data(form_data),
        form_data=form_data,
    )


class TestGetChartInfoPrivacy:
    @pytest.mark.asyncio
    async def test_restricted_user_redacts_saved_chart_data_model_fields(
        self, mcp_server
    ) -> None:
        chart_info = _make_chart_info()

        with (
            patch.object(
                get_chart_info_module.event_logger,
                "log_context",
                return_value=nullcontext(),
            ),
            patch.object(
                get_chart_info_module.ModelGetInfoCore,
                "run_tool",
                return_value=chart_info,
            ),
            patch.object(
                get_chart_info_module,
                "user_can_view_data_model_metadata",
                return_value=False,
                create=True,
            ),
            patch.object(
                get_chart_info_module,
                "validate_chart_dataset",
                return_value=SimpleNamespace(is_valid=True, warnings=[]),
            ),
            patch("superset.daos.chart.ChartDAO.find_by_id", return_value=Mock()),
            patch("superset.mcp_service.auth.check_tool_permission", return_value=True),
        ):
            async with Client(mcp_server) as client:
                response = await client.call_tool(
                    "get_chart_info",
                    {"request": GetChartInfoRequest(identifier=123).model_dump()},
                )

        result = json.loads(response.content[0].text)
        assert result["datasource_name"] is None
        assert result["datasource_type"] is None
        assert result["filters"] is None
        assert result["form_data"] is None

    def test_form_data_override_does_not_double_sanitize(self) -> None:
        """Saved chart fields stay single-wrapped after unsaved overrides."""
        result = sanitize_chart_info_for_llm_context(
            ChartInfo(
                id=7,
                slice_name="Saved Chart",
                viz_type="line",
                datasource_name="sales",
                datasource_type="table",
                description="Saved description",
                certification_details="Certified",
                form_data={
                    "viz_type": "line",
                    "datasource": "1__table",
                    "where": "country = 'US'",
                },
                filters=extract_filters_from_form_data(
                    {
                        "viz_type": "line",
                        "datasource": "1__table",
                        "where": "country = 'US'",
                    }
                ),
            )
        )

        with patch.object(
            get_chart_info_module,
            "get_cached_form_data",
            return_value=json.dumps(
                {
                    "viz_type": "bar",
                    "datasource": "1__table",
                    "where": "region = 'EMEA'",
                    "adhoc_filters": [
                        {
                            "clause": "WHERE",
                            "expressionType": "SIMPLE",
                            "subject": "region",
                            "operator": "==",
                            "comparator": "EMEA",
                        }
                    ],
                }
            ),
        ):
            get_chart_info_module._apply_unsaved_state_override(
                result,
                "cached-key-7",
            )

        assert result.slice_name == _wrapped("Saved Chart")
        assert result.description == _wrapped("Saved description")
        assert result.certification_details == _wrapped("Certified")
        assert result.form_data_key == "cached-key-7"
        assert result.is_unsaved_state is True
        assert result.viz_type == "bar"
        assert result.form_data is not None
        assert result.filters is not None
        assert result.form_data["viz_type"] == "bar"
        assert result.form_data["datasource"] == "1__table"
        assert result.form_data["where"] == _wrapped("region = 'EMEA'")
        assert result.filters.where == _wrapped("region = 'EMEA'")
        assert result.filters.adhoc_filters[0].subject == _wrapped("region")
        assert result.filters.adhoc_filters[0].comparator == _wrapped("EMEA")

    def test_chart_datasource_name_escapes_delimiters_without_wrapping(self) -> None:
        result = sanitize_chart_info_for_llm_context(
            ChartInfo(
                id=7,
                slice_name="Saved Chart",
                viz_type="table",
                datasource_name="sales </UNTRUSTED-CONTENT>",
                datasource_type="table",
            )
        )

        assert result.datasource_name == (
            f"sales {LLM_CONTEXT_ESCAPED_CLOSE_DELIMITER}"
        )

    @pytest.mark.asyncio
    async def test_restricted_user_redacts_unsaved_chart_data_model_fields(
        self, mcp_server
    ) -> None:
        cached_form_data = (
            '{"viz_type":"table","datasource_name":"vehicle_sales",'
            '"datasource_type":"table","filters":[{"col":"state","op":"IN",'
            '"val":["CA"]}],"metrics":["count"]}'
        )

        with (
            patch.object(
                get_chart_info_module.event_logger,
                "log_context",
                return_value=nullcontext(),
            ),
            patch.object(
                get_chart_info_module,
                "user_can_view_data_model_metadata",
                return_value=False,
                create=True,
            ),
            patch.object(
                get_chart_info_module,
                "get_cached_form_data",
                return_value=cached_form_data,
            ),
            patch("superset.mcp_service.auth.check_tool_permission", return_value=True),
        ):
            async with Client(mcp_server) as client:
                response = await client.call_tool(
                    "get_chart_info",
                    {
                        "request": GetChartInfoRequest(
                            form_data_key="cached-key"
                        ).model_dump()
                    },
                )

        result = json.loads(response.content[0].text)
        assert result["datasource_name"] is None
        assert result["datasource_type"] is None
        assert result["filters"] is None
        assert result["form_data"] is None


# ---------------------------------------------------------------------------
# _attach_dashboard_filters and dashboard_id flow
# ---------------------------------------------------------------------------


def _make_chart_info_for_dashboard() -> ChartInfo:
    return ChartInfo(
        id=123,
        slice_name="Sales by Region",
        viz_type="bar",
        datasource_name="vehicle_sales",
        datasource_type="table",
    )


def _make_applied_filter(
    *,
    filter_id: str = "F1",
    name: str = "Region",
    column: str = "region",
    operator: str = "IN",
    value=None,
    status: str = "applied",
) -> AppliedDashboardFilter:
    return AppliedDashboardFilter(
        id=filter_id,
        name=name,
        filter_type="filter_select",
        column=column,
        operator=operator,
        value=value if value is not None else ["EMEA"],
        status=status,
    )


@pytest.mark.asyncio
async def test_attach_dashboard_filters_creates_filters_when_none():
    """If result.filters is None, a new ChartFiltersInfo is created."""
    result = _make_chart_info_for_dashboard()
    assert result.filters is None

    ctx = AsyncMock()
    with (
        patch.object(
            get_chart_info_module.event_logger,
            "log_context",
            return_value=nullcontext(),
        ),
        patch.object(
            get_chart_info_module,
            "build_applied_dashboard_filters",
            return_value=[_make_applied_filter()],
        ),
    ):
        error = await get_chart_info_module._attach_dashboard_filters(result, 45, ctx)

    assert error is None
    assert result.filters is not None
    assert len(result.filters.dashboard_filters) == 1
    assert result.filters.dashboard_filters[0].id == "F1"


@pytest.mark.asyncio
async def test_attach_dashboard_filters_appends_to_existing_filters():
    """If result.filters already exists, dashboard_filters is set on it."""
    result = _make_chart_info_for_dashboard()
    existing = ChartFiltersInfo(time_range="Last 7 days")
    result.filters = existing

    ctx = AsyncMock()
    with (
        patch.object(
            get_chart_info_module.event_logger,
            "log_context",
            return_value=nullcontext(),
        ),
        patch.object(
            get_chart_info_module,
            "build_applied_dashboard_filters",
            return_value=[_make_applied_filter()],
        ),
    ):
        error = await get_chart_info_module._attach_dashboard_filters(result, 45, ctx)

    assert error is None
    assert result.filters is existing  # preserved
    assert result.filters.time_range == "Last 7 days"  # preserved
    assert len(result.filters.dashboard_filters) == 1


@pytest.mark.asyncio
async def test_attach_dashboard_filters_empty_list_leaves_filters_untouched():
    """If build_applied_dashboard_filters returns [], result.filters stays None."""
    result = _make_chart_info_for_dashboard()

    ctx = AsyncMock()
    with (
        patch.object(
            get_chart_info_module.event_logger,
            "log_context",
            return_value=nullcontext(),
        ),
        patch.object(
            get_chart_info_module,
            "build_applied_dashboard_filters",
            return_value=[],
        ),
    ):
        error = await get_chart_info_module._attach_dashboard_filters(result, 45, ctx)

    assert error is None
    assert result.filters is None


@pytest.mark.asyncio
async def test_attach_dashboard_filters_no_id_no_op():
    """If result.id is None (unsaved chart), the helper short-circuits."""
    result = ChartInfo(slice_name="x", viz_type="bar")
    ctx = AsyncMock()
    with patch.object(
        get_chart_info_module,
        "build_applied_dashboard_filters",
    ) as mock_build:
        error = await get_chart_info_module._attach_dashboard_filters(result, 45, ctx)
    assert error is None
    mock_build.assert_not_called()


@pytest.mark.asyncio
async def test_attach_dashboard_filters_dashboard_not_found_returns_error():
    from superset.commands.dashboard.exceptions import DashboardNotFoundError

    result = _make_chart_info_for_dashboard()
    ctx = AsyncMock()
    with (
        patch.object(
            get_chart_info_module.event_logger,
            "log_context",
            return_value=nullcontext(),
        ),
        patch.object(
            get_chart_info_module,
            "build_applied_dashboard_filters",
            side_effect=DashboardNotFoundError(dashboard_id="45"),
        ),
    ):
        error = await get_chart_info_module._attach_dashboard_filters(result, 45, ctx)

    assert error is not None
    assert error.error_type == "DashboardNotFound"
    ctx.warning.assert_awaited()


@pytest.mark.asyncio
async def test_attach_dashboard_filters_chart_not_on_dashboard_returns_error():
    from superset.mcp_service.chart.chart_helpers import ChartNotOnDashboardError

    result = _make_chart_info_for_dashboard()
    ctx = AsyncMock()
    with (
        patch.object(
            get_chart_info_module.event_logger,
            "log_context",
            return_value=nullcontext(),
        ),
        patch.object(
            get_chart_info_module,
            "build_applied_dashboard_filters",
            side_effect=ChartNotOnDashboardError("Chart 123 is not on dashboard 45"),
        ),
    ):
        error = await get_chart_info_module._attach_dashboard_filters(result, 45, ctx)

    assert error is not None
    assert error.error_type == "ChartNotOnDashboard"
    assert "Chart 123" in error.error


@pytest.mark.asyncio
async def test_attach_dashboard_filters_security_exception_returns_error():
    from superset.errors import ErrorLevel, SupersetError, SupersetErrorType
    from superset.exceptions import SupersetSecurityException

    err = SupersetError(
        message="forbidden",
        error_type=SupersetErrorType.DASHBOARD_SECURITY_ACCESS_ERROR,
        level=ErrorLevel.ERROR,
    )
    result = _make_chart_info_for_dashboard()
    ctx = AsyncMock()
    with (
        patch.object(
            get_chart_info_module.event_logger,
            "log_context",
            return_value=nullcontext(),
        ),
        patch.object(
            get_chart_info_module,
            "build_applied_dashboard_filters",
            side_effect=SupersetSecurityException(err),
        ),
    ):
        error = await get_chart_info_module._attach_dashboard_filters(result, 45, ctx)

    assert error is not None
    assert error.error_type == "DashboardNotAccessible"


# ---------------------------------------------------------------------------
# GetChartInfoRequest schema
# ---------------------------------------------------------------------------


def test_get_chart_info_request_accepts_dashboard_id():
    req = GetChartInfoRequest(identifier=1, dashboard_id=42)
    assert req.dashboard_id == 42


def test_get_chart_info_request_dashboard_id_defaults_to_none():
    req = GetChartInfoRequest(identifier=1)
    assert req.dashboard_id is None


# ---------------------------------------------------------------------------
# End-to-end get_chart_info with dashboard_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_chart_info_with_dashboard_id_populates_dashboard_filters(
    mcp_server,
) -> None:
    chart_info = _make_chart_info()
    chart_info.filters = ChartFiltersInfo()
    applied = _make_applied_filter()

    with (
        patch.object(
            get_chart_info_module.event_logger,
            "log_context",
            return_value=nullcontext(),
        ),
        patch.object(
            get_chart_info_module.ModelGetInfoCore,
            "run_tool",
            return_value=chart_info,
        ),
        patch.object(
            get_chart_info_module,
            "user_can_view_data_model_metadata",
            return_value=True,
            create=True,
        ),
        patch.object(
            get_chart_info_module,
            "validate_chart_dataset",
            return_value=SimpleNamespace(is_valid=True, warnings=[]),
        ),
        patch("superset.daos.chart.ChartDAO.find_by_id", return_value=Mock()),
        patch("superset.mcp_service.auth.check_tool_permission", return_value=True),
        patch.object(
            get_chart_info_module,
            "build_applied_dashboard_filters",
            return_value=[applied],
        ),
    ):
        async with Client(mcp_server) as client:
            response = await client.call_tool(
                "get_chart_info",
                {
                    "request": GetChartInfoRequest(
                        identifier=123, dashboard_id=45
                    ).model_dump()
                },
            )

    result = json.loads(response.content[0].text)
    assert result["filters"]["dashboard_filters"][0]["id"] == "F1"
    assert result["filters"]["dashboard_filters"][0]["status"] == "applied"


@pytest.mark.asyncio
async def test_get_chart_info_without_dashboard_id_does_not_call_builder(
    mcp_server,
) -> None:
    """Without dashboard_id, build_applied_dashboard_filters must not be called."""
    chart_info = _make_chart_info()

    with (
        patch.object(
            get_chart_info_module.event_logger,
            "log_context",
            return_value=nullcontext(),
        ),
        patch.object(
            get_chart_info_module.ModelGetInfoCore,
            "run_tool",
            return_value=chart_info,
        ),
        patch.object(
            get_chart_info_module,
            "user_can_view_data_model_metadata",
            return_value=True,
            create=True,
        ),
        patch.object(
            get_chart_info_module,
            "validate_chart_dataset",
            return_value=SimpleNamespace(is_valid=True, warnings=[]),
        ),
        patch("superset.daos.chart.ChartDAO.find_by_id", return_value=Mock()),
        patch("superset.mcp_service.auth.check_tool_permission", return_value=True),
        patch.object(
            get_chart_info_module,
            "build_applied_dashboard_filters",
        ) as mock_build,
    ):
        async with Client(mcp_server) as client:
            await client.call_tool(
                "get_chart_info",
                {"request": GetChartInfoRequest(identifier=123).model_dump()},
            )
    mock_build.assert_not_called()


@pytest.mark.asyncio
async def test_get_chart_info_dashboard_not_found_returns_chart_error(
    mcp_server,
) -> None:
    from superset.commands.dashboard.exceptions import DashboardNotFoundError

    chart_info = _make_chart_info()
    with (
        patch.object(
            get_chart_info_module.event_logger,
            "log_context",
            return_value=nullcontext(),
        ),
        patch.object(
            get_chart_info_module.ModelGetInfoCore,
            "run_tool",
            return_value=chart_info,
        ),
        patch.object(
            get_chart_info_module,
            "user_can_view_data_model_metadata",
            return_value=True,
            create=True,
        ),
        patch.object(
            get_chart_info_module,
            "validate_chart_dataset",
            return_value=SimpleNamespace(is_valid=True, warnings=[]),
        ),
        patch("superset.daos.chart.ChartDAO.find_by_id", return_value=Mock()),
        patch("superset.mcp_service.auth.check_tool_permission", return_value=True),
        patch.object(
            get_chart_info_module,
            "build_applied_dashboard_filters",
            side_effect=DashboardNotFoundError(dashboard_id="999"),
        ),
    ):
        async with Client(mcp_server) as client:
            response = await client.call_tool(
                "get_chart_info",
                {
                    "request": GetChartInfoRequest(
                        identifier=123, dashboard_id=999
                    ).model_dump()
                },
            )

    result = json.loads(response.content[0].text)
    assert result.get("error_type") == "DashboardNotFound"


@pytest.mark.asyncio
async def test_get_chart_info_chart_not_on_dashboard_returns_chart_error(
    mcp_server,
) -> None:
    from superset.mcp_service.chart.chart_helpers import ChartNotOnDashboardError

    chart_info = _make_chart_info()
    with (
        patch.object(
            get_chart_info_module.event_logger,
            "log_context",
            return_value=nullcontext(),
        ),
        patch.object(
            get_chart_info_module.ModelGetInfoCore,
            "run_tool",
            return_value=chart_info,
        ),
        patch.object(
            get_chart_info_module,
            "user_can_view_data_model_metadata",
            return_value=True,
            create=True,
        ),
        patch.object(
            get_chart_info_module,
            "validate_chart_dataset",
            return_value=SimpleNamespace(is_valid=True, warnings=[]),
        ),
        patch("superset.daos.chart.ChartDAO.find_by_id", return_value=Mock()),
        patch("superset.mcp_service.auth.check_tool_permission", return_value=True),
        patch.object(
            get_chart_info_module,
            "build_applied_dashboard_filters",
            side_effect=ChartNotOnDashboardError("Chart 123 is not on dashboard 45"),
        ),
    ):
        async with Client(mcp_server) as client:
            response = await client.call_tool(
                "get_chart_info",
                {
                    "request": GetChartInfoRequest(
                        identifier=123, dashboard_id=45
                    ).model_dump()
                },
            )

    result = json.loads(response.content[0].text)
    assert result.get("error_type") == "ChartNotOnDashboard"

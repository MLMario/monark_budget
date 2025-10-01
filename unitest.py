import json
from datetime import date, datetime, timedelta
from typing import Any, Optional
from unittest.mock import AsyncMock

import pytest
from langgraph.graph import START, END, StateGraph

from services.api.app.agent.nodes import (
    import_data_node,
    coordinator_node,
    daily_overspend_alert_node,
    import_current_month_txn_node,
    import_previous_month_txn_node,
    eow_period_report_node,
    eom_period_report_node,
)
from services.api.app.agent.state import (
    BudgetAgentState,
    DailyAlertOverspend,
    DailyAlertSuspiciousTransaction,
    ProcessFlag,
    RunMeta,
)
from services.api.app.agent.agent_utilities import task_management
from config import Settings

SAMPLE_CURRENT_MONTH_BUDGET_ROWS = [
    {
        "actual_amount": 550.0,
        "category_budget_variability": "flexible",
        "category_group_name": "Food",
        "category_group_type": "expense",
        "category_name": "Dining Out",
        "month": "2024-05-01",
        "planned_cash_flow_amount": 400.0,
        "remaining_amount": -150.0,
        "remaining_amount_percent": -37.5,
    },
    {
        "actual_amount": 320.0,
        "category_budget_variability": "flexible",
        "category_group_name": "Shopping",
        "category_group_type": "expense",
        "category_name": "Clothing",
        "month": "2024-05-01",
        "planned_cash_flow_amount": 200.0,
        "remaining_amount": -120.0,
        "remaining_amount_percent": -60.0,
    }
]

SAMPLE_PAST_MONTH_BUDGET_ROWS = [
    {
        "actual_amount": 480.0,
        "category_budget_variability": "flexible",
        "category_group_name": "Food",
        "category_group_type": "expense",
        "category_name": "Dining Out",
        "month": "2024-04-01",
        "planned_cash_flow_amount": 400.0,
        "remaining_amount": -80.0,
        "remaining_amount_percent": -20.0,
    }
]

SAMPLE_CURRENT_MONTH_TRANSACTIONS = [
    {
        "amount": 75.5,
        "category_id": "cat_food_dining_out",
        "category_name": "Dining Out",
        "createdAt": "2024-05-03T12:00:00Z",
        "description": "Dinner at Bistro",
        "merchant_id": "m123",
        "merchant_name": "Bistro",
        "transaction_id": "t123",
        "updatedAt": "2024-05-03T12:30:00Z",
    },
    {
        "amount": 45.0,
        "category_id": "cat_food_dining_out",
        "category_name": "Dining Out",
        "createdAt": "2024-05-05T18:00:00Z",
        "description": "Pizza Place",
        "merchant_id": "m124",
        "merchant_name": "Pizza Hut",
        "transaction_id": "t124",
        "updatedAt": "2024-05-05T18:30:00Z",
    }
]

SAMPLE_PREVIOUS_MONTH_TRANSACTIONS = [
    {
        "amount": 65.0,
        "category_id": "cat_food_dining_out",
        "category_name": "Dining Out",
        "createdAt": "2024-04-10T12:00:00Z",
        "description": "Restaurant",
        "merchant_id": "m125",
        "merchant_name": "Cheesecake Factory",
        "transaction_id": "t125",
        "updatedAt": "2024-04-10T12:30:00Z",
    }
]

SAMPLE_LAST_DAY_TRANSACTIONS = [
    {
        "amount": 15.5,
        "category_id": "cat_food_coffee",
        "category_name": "Coffee",
        "createdAt": "2024-05-03T08:00:00Z",
        "description": "Morning coffee",
        "merchant_id": "m126",
        "merchant_name": "Starbucks",
        "transaction_id": "t126",
        "updatedAt": "2024-05-03T08:30:00Z",
    }
]

CURRENT_OVERSPEND_JSON = json.dumps(SAMPLE_CURRENT_MONTH_BUDGET_ROWS)
PAST_OVERSPEND_JSON = json.dumps(SAMPLE_PAST_MONTH_BUDGET_ROWS)
FAKE_ALERT_TEXT = "Overspend alert: Dining Out over plan by $150.00."
FAKE_PERIOD_REPORT_TEXT = "Period report with spending analysis and recommendations."


class FakeAsyncMongoDBClient:
    """Fake MongoDB client that tracks which month was requested."""

    def __init__(self):
        self.budget_calls = []
        self.txn_calls = []

    async def import_budget_data(self, month: str, filter_query: Optional[Any] = None) -> str:
        self.budget_calls.append(month)
        # Return current or past month budget based on month parameter
        if month.startswith("2024-05"):
            return json.dumps(SAMPLE_CURRENT_MONTH_BUDGET_ROWS)
        elif month.startswith("2024-04"):
            return json.dumps(SAMPLE_PAST_MONTH_BUDGET_ROWS)
        return json.dumps([])

    async def import_transaction_data(self, start_date: str, end_date: str) -> str:
        self.txn_calls.append((start_date, end_date))
        # Return appropriate transactions based on date range
        if start_date.startswith("2024-05"):
            # Current month or last day
            if start_date == end_date:
                return json.dumps(SAMPLE_LAST_DAY_TRANSACTIONS)
            return json.dumps(SAMPLE_CURRENT_MONTH_TRANSACTIONS)
        elif start_date.startswith("2024-04"):
            return json.dumps(SAMPLE_PREVIOUS_MONTH_TRANSACTIONS)
        return json.dumps([])

    def close_connection(self):
        pass


def fake_filter_overspent_categories(budget_json: str) -> str:
    """Filter to return only overspent categories."""
    budget_data = json.loads(budget_json)
    filtered_data = [
        budget_record for budget_record in budget_data
        if budget_record.get('remaining_amount', 0) < -5
    ]
    if not filtered_data:
        return ''
    return json.dumps(filtered_data, default=str)


async def fake_call_llm(*args, **kwargs) -> str:
    return FAKE_ALERT_TEXT


async def fake_call_llm_reasoning(*args, **kwargs) -> str:
    """Fake LLM reasoning call that returns different content based on context."""
    prompt_obj = kwargs.get('prompt_obj')
    if prompt_obj and hasattr(prompt_obj, 'name'):
        if prompt_obj.name == 'txn_analysis':
            return "Drivers of spend: frequent dining out\nRecommendations: set weekly limit"
        elif prompt_obj.name == 'period_report':
            return FAKE_PERIOD_REPORT_TEXT
    return "Default LLM response"


def make_initial_state(today: date = date(2024, 5, 4)) -> BudgetAgentState:
    """Create initial state for testing."""
    return BudgetAgentState(
        run_meta=RunMeta(run_id="test-run", today=today, tz="UTC"),
        current_month_budget=None,
        past_month_budget=None,
        current_month_txn=None,
        previous_month_txn=None,
        last_day_txn=[],
        current_month_overspend_budget_data=None,
        past_month_overspend_budget_data=None,
        daily_overspend_alert=DailyAlertOverspend(),
        daily_suspicious_transactions=[],
        daily_alert_suspicious_transaction=DailyAlertSuspiciousTransaction(),
        period_report=None,
        process_flag=ProcessFlag(),
        email_info=None,
        task_info='daily_tasks',
    )


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def fake_mongo_client():
    """Fixture that provides a fresh FakeAsyncMongoDBClient for each test."""
    return FakeAsyncMongoDBClient()


# =====================================================
# Test: task_management routing logic
# =====================================================

def test_task_management_daily_tasks(monkeypatch):
    """Test task_management returns 'daily_tasks' on regular days."""
    # Mock datetime to return a Wednesday (not Monday, not first of month)
    fake_today = datetime(2024, 5, 15, 10, 0, 0)  # May 15, 2024 (Wednesday)

    class FakeDatetime:
        @staticmethod
        def now():
            return fake_today

        @staticmethod
        def strftime(fmt):
            return fake_today.strftime(fmt)

    monkeypatch.setattr("services.api.app.agent.agent_utilities.datetime", FakeDatetime)

    result = task_management()
    assert result == "daily_tasks"


def test_task_management_eow_tasks(monkeypatch):
    """Test task_management returns 'eow_tasks' on Monday (not first of month)."""
    # Mock datetime to return a Monday that's not first of month
    fake_today = datetime(2024, 5, 6, 10, 0, 0)  # May 6, 2024 (Monday)

    class FakeDatetime:
        @staticmethod
        def now():
            return fake_today

        @staticmethod
        def strftime(fmt):
            return fake_today.strftime(fmt)

    monkeypatch.setattr("services.api.app.agent.agent_utilities.datetime", FakeDatetime)

    result = task_management()
    assert result == "eow_tasks"


def test_task_management_eom_tasks(monkeypatch):
    """Test task_management returns 'eom_tasks' on first of month (not Monday)."""
    # Mock datetime to return first of month that's not Monday
    fake_today = datetime(2024, 5, 1, 10, 0, 0)  # May 1, 2024 (Wednesday)

    class FakeDatetime:
        @staticmethod
        def now():
            return fake_today

        @staticmethod
        def strftime(fmt):
            return fake_today.strftime(fmt)

    monkeypatch.setattr("services.api.app.agent.agent_utilities.datetime", FakeDatetime)

    result = task_management()
    assert result == "eom_tasks"


def test_task_management_eom_priority(monkeypatch):
    """Test that EOM takes precedence when it's both Monday AND first of month."""
    # Mock datetime to return first Monday of month
    fake_today = datetime(2024, 7, 1, 10, 0, 0)  # July 1, 2024 (Monday)

    class FakeDatetime:
        @staticmethod
        def now():
            return fake_today

        @staticmethod
        def strftime(fmt):
            return fake_today.strftime(fmt)

    monkeypatch.setattr("services.api.app.agent.agent_utilities.datetime", FakeDatetime)

    result = task_management()
    assert result == "eom_tasks"  # EOM takes precedence


# =====================================================
# Test: import_data_node
# =====================================================

@pytest.mark.anyio("asyncio")
async def test_import_data_node_imports_both_months(monkeypatch, fake_mongo_client):
    """Test that import_data_node imports both current and past month budget data."""
    monkeypatch.setattr(
        "services.api.app.agent.nodes.AsyncMongoDBClient",
        lambda: fake_mongo_client,
    )
    monkeypatch.setattr(
        "services.api.app.agent.nodes.filter_overspent_categories",
        fake_filter_overspent_categories,
    )

    initial_state = make_initial_state(date(2024, 5, 4))

    final_state = await import_data_node(initial_state)

    # Check that budget data for both months was requested
    assert len(fake_mongo_client.budget_calls) == 2
    assert any(call.startswith("2024-05") for call in fake_mongo_client.budget_calls)
    assert any(call.startswith("2024-04") for call in fake_mongo_client.budget_calls)

    # Check that both budget states are populated
    assert final_state.current_month_budget is not None
    assert final_state.past_month_budget is not None

    # Check overspend data for both months
    assert final_state.current_month_overspend_budget_data is not None
    assert final_state.past_month_overspend_budget_data is not None


@pytest.mark.anyio("asyncio")
async def test_import_data_node_no_overspend(monkeypatch, fake_mongo_client):
    """Test import_data_node when there's no overspending."""

    # Mock budget with no overspending
    no_overspend_budget = [
        {
            "actual_amount": 300.0,
            "category_budget_variability": "flexible",
            "category_group_name": "Food",
            "category_group_type": "expense",
            "category_name": "Dining Out",
            "month": "2024-05-01",
            "planned_cash_flow_amount": 400.0,
            "remaining_amount": 100.0,
            "remaining_amount_percent": 25.0,
        }
    ]

    class NoOverspendMongoClient:
        async def import_budget_data(self, month: str, filter_query: Optional[Any] = None) -> str:
            return json.dumps(no_overspend_budget)

        async def import_transaction_data(self, start_date: str, end_date: str) -> str:
            return json.dumps([])

        def close_connection(self):
            pass

    monkeypatch.setattr(
        "services.api.app.agent.nodes.AsyncMongoDBClient",
        NoOverspendMongoClient,
    )
    monkeypatch.setattr(
        "services.api.app.agent.nodes.filter_overspent_categories",
        fake_filter_overspent_categories,
    )

    initial_state = make_initial_state()
    final_state = await import_data_node(initial_state)

    assert final_state.current_month_overspend_budget_data == "No Data, User hasn't overspent"
    assert final_state.past_month_overspend_budget_data == "No Data, User hasn't overspent"


# =====================================================
# Test: import_current_month_txn_node (EOW)
# =====================================================

@pytest.mark.anyio("asyncio")
async def test_import_current_month_txn_node(monkeypatch, fake_mongo_client):
    """Test import_current_month_txn_node imports current month transactions."""
    monkeypatch.setattr(
        "services.api.app.agent.nodes.AsyncMongoDBClient",
        lambda: fake_mongo_client,
    )

    initial_state = make_initial_state(date(2024, 5, 6))

    final_state = await import_current_month_txn_node(initial_state)

    # Check that only current month transactions were imported
    assert final_state.current_month_txn is not None
    assert final_state.current_month_txn != "No Data, User hasn't done any transaction this month"

    # Verify the transaction data
    txn_data = json.loads(final_state.current_month_txn)
    assert len(txn_data) == 2
    assert txn_data[0]["transaction_id"] == "t123"


@pytest.mark.anyio("asyncio")
async def test_import_current_month_txn_node_no_data(monkeypatch):
    """Test import_current_month_txn_node when no transactions exist."""

    class EmptyMongoClient:
        async def import_transaction_data(self, start_date: str, end_date: str) -> str:
            return ""

        def close_connection(self):
            pass

    monkeypatch.setattr(
        "services.api.app.agent.nodes.AsyncMongoDBClient",
        EmptyMongoClient,
    )

    initial_state = make_initial_state()
    final_state = await import_current_month_txn_node(initial_state)

    assert final_state.current_month_txn == "No Data, User hasn't done any transaction this month"


# =====================================================
# Test: import_previous_month_txn_node (EOM)
# =====================================================

@pytest.mark.anyio("asyncio")
async def test_import_previous_month_txn_node(monkeypatch, fake_mongo_client):
    """Test import_previous_month_txn_node imports previous month transactions."""
    monkeypatch.setattr(
        "services.api.app.agent.nodes.AsyncMongoDBClient",
        lambda: fake_mongo_client,
    )

    initial_state = make_initial_state(date(2024, 5, 1))

    final_state = await import_previous_month_txn_node(initial_state)

    # Check that only previous month transactions were imported
    assert final_state.previous_month_txn is not None
    assert final_state.previous_month_txn != "No Data, User hasn't done any transaction last month"

    # Verify the transaction data
    txn_data = json.loads(final_state.previous_month_txn)
    assert len(txn_data) == 1
    assert txn_data[0]["transaction_id"] == "t125"


# =====================================================
# Test: eow_period_report_node
# =====================================================

@pytest.mark.anyio("asyncio")
async def test_eow_period_report_node(monkeypatch):
    """Test EOW period report node with current month data."""
    monkeypatch.setattr(
        "services.api.app.agent.nodes.call_llm_reasoning",
        fake_call_llm_reasoning,
    )

    # Create state with current month overspend and transactions
    state = make_initial_state()
    state.current_month_overspend_budget_data = CURRENT_OVERSPEND_JSON
    state.current_month_txn = json.dumps(SAMPLE_CURRENT_MONTH_TRANSACTIONS)

    final_state = await eow_period_report_node(state)

    assert final_state.period_report is not None
    assert final_state.period_report == FAKE_PERIOD_REPORT_TEXT
    assert final_state.process_flag.period_report_done is True


@pytest.mark.anyio("asyncio")
async def test_eow_period_report_node_no_overspend(monkeypatch):
    """Test EOW period report when there's no overspending."""
    state = make_initial_state()
    state.current_month_overspend_budget_data = "No Data, User hasn't overspent"

    final_state = await eow_period_report_node(state)

    assert final_state.period_report == "Good Job! You haven't overspent in any category this week, keep it up!"
    assert final_state.process_flag.period_report_done is True


# =====================================================
# Test: eom_period_report_node
# =====================================================

@pytest.mark.anyio("asyncio")
async def test_eom_period_report_node(monkeypatch):
    """Test EOM period report node with previous month data."""
    monkeypatch.setattr(
        "services.api.app.agent.nodes.call_llm_reasoning",
        fake_call_llm_reasoning,
    )

    # Create state with past month overspend and transactions
    state = make_initial_state()
    state.past_month_overspend_budget_data = PAST_OVERSPEND_JSON
    state.previous_month_txn = json.dumps(SAMPLE_PREVIOUS_MONTH_TRANSACTIONS)

    final_state = await eom_period_report_node(state)

    assert final_state.period_report is not None
    assert final_state.period_report == FAKE_PERIOD_REPORT_TEXT
    assert final_state.process_flag.period_report_done is True


@pytest.mark.anyio("asyncio")
async def test_eom_period_report_node_no_overspend(monkeypatch):
    """Test EOM period report when there's no overspending."""
    state = make_initial_state()
    state.past_month_overspend_budget_data = "No Data, User hasn't overspent"

    final_state = await eom_period_report_node(state)

    assert final_state.period_report == "Good Job! You haven't overspent in any category last month, keep it up!"
    assert final_state.process_flag.period_report_done is True


# =====================================================
# Test: coordinator_node routing
# =====================================================

@pytest.mark.anyio("asyncio")
async def test_coordinator_node_daily_tasks(monkeypatch):
    """Test coordinator routes to daily_tasks on regular day."""
    monkeypatch.setattr(
        "services.api.app.agent.nodes.task_management",
        lambda: "daily_tasks",
    )

    state = make_initial_state()
    final_state = await coordinator_node(state)

    assert final_state.task_info == "daily_tasks"


@pytest.mark.anyio("asyncio")
async def test_coordinator_node_eow_tasks(monkeypatch):
    """Test coordinator routes to eow_tasks on Monday."""
    monkeypatch.setattr(
        "services.api.app.agent.nodes.task_management",
        lambda: "eow_tasks",
    )

    state = make_initial_state()
    final_state = await coordinator_node(state)

    assert final_state.task_info == "eow_tasks"


@pytest.mark.anyio("asyncio")
async def test_coordinator_node_eom_tasks(monkeypatch):
    """Test coordinator routes to eom_tasks on first of month."""
    monkeypatch.setattr(
        "services.api.app.agent.nodes.task_management",
        lambda: "eom_tasks",
    )

    state = make_initial_state()
    final_state = await coordinator_node(state)

    assert final_state.task_info == "eom_tasks"


# =====================================================
# Test: daily_overspend_alert_node
# =====================================================

@pytest.mark.anyio("asyncio")
async def test_daily_overspend_alert_node(monkeypatch):
    """Test daily overspend alert uses current month data."""
    monkeypatch.setattr(
        "services.api.app.agent.nodes.call_llm",
        fake_call_llm,
    )

    state = make_initial_state()
    state.current_month_overspend_budget_data = CURRENT_OVERSPEND_JSON

    final_state = await daily_overspend_alert_node(state)

    assert final_state.daily_overspend_alert.text == FAKE_ALERT_TEXT
    assert final_state.process_flag.daily_overspend_alert_done is True


# =====================================================
# Edge case tests
# =====================================================

@pytest.mark.anyio("asyncio")
async def test_edge_case_year_boundary_december_to_january(monkeypatch, fake_mongo_client):
    """Test date calculations work correctly at year boundary (Dec to Jan)."""
    # January 1, 2025 - should look back to December 2024
    monkeypatch.setattr(
        "services.api.app.agent.nodes.AsyncMongoDBClient",
        lambda: fake_mongo_client,
    )

    # We need to mock datetime for the node
    fake_today = datetime(2025, 1, 1, 10, 0, 0)

    class FakeDatetime:
        @staticmethod
        def now():
            return fake_today

        @staticmethod
        def strftime(fmt):
            return fake_today.strftime(fmt)

        def __new__(cls, *args, **kwargs):
            if args:
                return datetime(*args, **kwargs)
            return fake_today

    monkeypatch.setattr("services.api.app.agent.nodes.datetime", FakeDatetime)

    state = make_initial_state(date(2025, 1, 1))

    final_state = await import_previous_month_txn_node(state)

    # Should request December 2024 data
    assert len(fake_mongo_client.txn_calls) == 1
    start_date, end_date = fake_mongo_client.txn_calls[0]
    assert start_date.startswith("2024-12-01")
    assert end_date.startswith("2024-12-31")


@pytest.mark.anyio("asyncio")
async def test_edge_case_empty_transaction_list(monkeypatch):
    """Test nodes handle empty transaction lists gracefully."""

    class EmptyMongoClient:
        async def import_transaction_data(self, start_date: str, end_date: str) -> str:
            return json.dumps([])

        def close_connection(self):
            pass

    monkeypatch.setattr(
        "services.api.app.agent.nodes.AsyncMongoDBClient",
        EmptyMongoClient,
    )

    state = make_initial_state()
    final_state = await import_current_month_txn_node(state)

    # Should handle empty list gracefully
    assert final_state.current_month_txn is not None
    txn_data = json.loads(final_state.current_month_txn)
    assert txn_data == []


@pytest.mark.anyio("asyncio")
async def test_edge_case_february_leap_year(monkeypatch, fake_mongo_client):
    """Test date calculations work correctly in February of a leap year."""
    # March 1, 2024 (leap year) - should look back to February 29, 2024
    fake_today = datetime(2024, 3, 1, 10, 0, 0)

    class FakeDatetime:
        @staticmethod
        def now():
            return fake_today

        @staticmethod
        def strftime(fmt):
            return fake_today.strftime(fmt)

        def __new__(cls, *args, **kwargs):
            if args:
                return datetime(*args, **kwargs)
            return fake_today

    monkeypatch.setattr("services.api.app.agent.nodes.datetime", FakeDatetime)
    monkeypatch.setattr(
        "services.api.app.agent.nodes.AsyncMongoDBClient",
        lambda: fake_mongo_client,
    )

    state = make_initial_state(date(2024, 3, 1))

    final_state = await import_previous_month_txn_node(state)

    # Should request February 2024 data (leap year with 29 days)
    assert len(fake_mongo_client.txn_calls) == 1
    start_date, end_date = fake_mongo_client.txn_calls[0]
    assert start_date.startswith("2024-02-01")
    assert end_date.startswith("2024-02-29")


# =====================================================
# Integration tests with live LLM (optional)
# =====================================================

@pytest.mark.anyio("asyncio")
async def test_eow_report_with_live_llm(monkeypatch, fake_mongo_client, capsys):
    """Test EOW report with live LLM (skipped if no credentials)."""
    try:
        api_key = Settings.GROQ_API_KEY.get_secret_value()
    except Exception as exc:
        pytest.skip(f"Live LLM credentials unavailable: {exc}")

    if not api_key:
        pytest.skip("Live LLM credentials unavailable: GROQ_API_KEY empty")

    monkeypatch.setattr(
        "services.api.app.agent.nodes.AsyncMongoDBClient",
        lambda: fake_mongo_client,
    )
    monkeypatch.setattr(
        "services.api.app.agent.nodes.filter_overspent_categories",
        fake_filter_overspent_categories,
    )

    # Setup state with overspend data
    state = make_initial_state()
    state.current_month_overspend_budget_data = CURRENT_OVERSPEND_JSON
    state.current_month_txn = json.dumps(SAMPLE_CURRENT_MONTH_TRANSACTIONS)

    print("[LIVE EOW] Testing with real LLM...")

    try:
        final_state = await eow_period_report_node(state)
    except Exception as exc:
        pytest.skip(f"Live LLM request failed: {exc}")

    print("[LIVE EOW] Period report:", final_state.period_report)

    assert final_state.period_report is not None
    assert final_state.period_report != FAKE_PERIOD_REPORT_TEXT  # Should be real LLM output
    assert final_state.process_flag.period_report_done is True

    captured = capsys.readouterr()
    assert "[LIVE EOW] Testing with real LLM" in captured.out


@pytest.mark.anyio("asyncio")
async def test_eom_report_with_live_llm(monkeypatch, fake_mongo_client, capsys):
    """Test EOM report with live LLM (skipped if no credentials)."""
    try:
        api_key = Settings.GROQ_API_KEY.get_secret_value()
    except Exception as exc:
        pytest.skip(f"Live LLM credentials unavailable: {exc}")

    if not api_key:
        pytest.skip("Live LLM credentials unavailable: GROQ_API_KEY empty")

    monkeypatch.setattr(
        "services.api.app.agent.nodes.AsyncMongoDBClient",
        lambda: fake_mongo_client,
    )
    monkeypatch.setattr(
        "services.api.app.agent.nodes.filter_overspent_categories",
        fake_filter_overspent_categories,
    )

    # Setup state with past month overspend data
    state = make_initial_state()
    state.past_month_overspend_budget_data = PAST_OVERSPEND_JSON
    state.previous_month_txn = json.dumps(SAMPLE_PREVIOUS_MONTH_TRANSACTIONS)

    print("[LIVE EOM] Testing with real LLM...")

    try:
        final_state = await eom_period_report_node(state)
    except Exception as exc:
        pytest.skip(f"Live LLM request failed: {exc}")

    print("[LIVE EOM] Period report:", final_state.period_report)

    assert final_state.period_report is not None
    assert final_state.period_report != FAKE_PERIOD_REPORT_TEXT  # Should be real LLM output
    assert final_state.process_flag.period_report_done is True

    captured = capsys.readouterr()
    assert "[LIVE EOM] Testing with real LLM" in captured.out

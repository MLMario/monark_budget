import json
from datetime import date
from typing import Any

import pytest
from langgraph.graph import END, START, StateGraph

from config import Settings
from services.api.app.agent.nodes import (
    coordinator_node,
    daily_overspend_alert_node,
    import_data_node,
)
from services.api.app.agent.state import (
    BudgetAgentState,
    DailyAlertOverspend,
    DailyAlertSuspiciousTransaction,
    ProcessFlag,
    ReportCategory,
    RunMeta,
)

SAMPLE_BUDGET_ROWS = [
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
    }
]

SAMPLE_TRANSACTIONS = [
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
    }
]

OVESPEND_JSON = json.dumps(SAMPLE_BUDGET_ROWS)
FAKE_ALERT_TEXT = "Overspend alert: Dining Out over plan by $150.00."


class FakeAsyncMongoDBClient:
    async def import_budget_data(self, filter_query: Any) -> str:
        return json.dumps(SAMPLE_BUDGET_ROWS)

    async def import_transaction_data(self, start_date: str, end_date: str) -> str:
        return json.dumps(SAMPLE_TRANSACTIONS)

    def close_connection(self) -> None:
        pass


async def fake_call_llm(*args, **kwargs) -> str:
    return FAKE_ALERT_TEXT


def build_partial_budget_graph() -> Any:
    graph_builder = StateGraph(BudgetAgentState)
    graph_builder.add_node("import_data_node", import_data_node)
    graph_builder.add_node("coordinator_node", coordinator_node)
    graph_builder.add_node("daily_overspend_alert_node", daily_overspend_alert_node)
    graph_builder.add_edge(START, "import_data_node")
    graph_builder.add_edge("import_data_node", "coordinator_node")
    graph_builder.add_edge("coordinator_node", "daily_overspend_alert_node")
    graph_builder.add_edge("daily_overspend_alert_node", END)
    return graph_builder.compile()


def make_initial_state() -> BudgetAgentState:
    return BudgetAgentState(
        run_meta=RunMeta(run_id="test-run", today=date(2024, 5, 4), tz="UTC"),
        current_month_budget=None,
        current_month_txn=None,
        previous_month_txn=None,
        last_day_txn=[],
        overspend_budget_data=None,
        daily_overspend_alert=DailyAlertOverspend(),
        daily_suspicious_transactions=[],
        daily_alert_suspicious_transaction=DailyAlertSuspiciousTransaction(),
        period_report=None,
        process_flag=ProcessFlag(),
        email_info=None,
    )


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio("asyncio")
async def test_budget_nodes_graph(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "services.api.app.agent.nodes.AsyncMongoDBClient",
        FakeAsyncMongoDBClient,
    )
    monkeypatch.setattr(
        "services.api.app.agent.nodes.filter_overspent_categories",
        lambda budget_json: OVESPEND_JSON,
    )
    monkeypatch.setattr(
        "services.api.app.agent.nodes.call_llm",
        fake_call_llm,
    )

    initial_state = make_initial_state()

    app = build_partial_budget_graph()

    print("Initial state overspend data:", initial_state.overspend_budget_data)
    final_state = await app.ainvoke(initial_state)
    if not isinstance(final_state, BudgetAgentState):
        final_state = BudgetAgentState.model_validate(final_state)
    print("Updated current_month_budget:", final_state.current_month_budget)
    print("Updated overspend_budget_data:", final_state.overspend_budget_data)
    print("Updated last_day_txn:", final_state.last_day_txn)
    print("Daily overspend alert text:", final_state.daily_overspend_alert.text)

    captured = capsys.readouterr()
    assert "Initial state overspend data: None" in captured.out
    assert "Updated current_month_budget:" in captured.out
    assert "Updated last_day_txn:" in captured.out
    assert "t123" in captured.out

    assert final_state.current_month_budget is not None
    overspend_payload = json.loads(final_state.overspend_budget_data)
    assert overspend_payload["overspend_categories"] == SAMPLE_BUDGET_ROWS
    last_day_payload = [json.loads(item) for item in final_state.last_day_txn]
    assert last_day_payload == SAMPLE_TRANSACTIONS
    assert final_state.daily_overspend_alert.text == FAKE_ALERT_TEXT


@pytest.mark.anyio("asyncio")
async def test_budget_nodes_graph_live_llm(monkeypatch, capsys) -> None:
    try:
        api_key = Settings.GROQ_API_KEY.get_secret_value()
    except Exception as exc:  # pragma: no cover - configuration-dependent
        pytest.skip(f"Live LLM credentials unavailable: {exc}")

    if not api_key:  # pragma: no cover - configuration-dependent
        pytest.skip("Live LLM credentials unavailable: GROQ_API_KEY empty")

    monkeypatch.setattr(
        "services.api.app.agent.nodes.AsyncMongoDBClient",
        FakeAsyncMongoDBClient,
    )
    # Reuse the deterministic overspend payload to control test data while using the real LLM.
    monkeypatch.setattr(
        "services.api.app.agent.nodes.filter_overspent_categories",
        lambda budget_json: OVESPEND_JSON,
    )

    app = build_partial_budget_graph()

    initial_state = make_initial_state()
    print("[LIVE] Initial state overspend data:", initial_state.overspend_budget_data)

    try:
        final_state = await app.ainvoke(initial_state)
    except Exception as exc:  # pragma: no cover - external dependency failure
        pytest.skip(f"Live LLM request failed: {exc}")

    if not isinstance(final_state, BudgetAgentState):
        final_state = BudgetAgentState.model_validate(final_state)

    print("[LIVE] Updated current_month_budget:", final_state.current_month_budget)
    print("[LIVE] Updated overspend_budget_data:", final_state.overspend_budget_data)
    print("[LIVE] Updated last_day_txn:", final_state.last_day_txn)
    print("[LIVE] Daily overspend alert text:", final_state.daily_overspend_alert.text)

    captured = capsys.readouterr()
    assert "[LIVE] Initial state overspend data:" in captured.out
    assert "[LIVE] Updated current_month_budget:" in captured.out
    assert "[LIVE] Daily overspend alert text:" in captured.out

    overspend_payload = json.loads(final_state.overspend_budget_data)
    assert overspend_payload["overspend_categories"] == SAMPLE_BUDGET_ROWS
    last_day_payload = [json.loads(item) for item in final_state.last_day_txn]
    assert last_day_payload == SAMPLE_TRANSACTIONS

    assert final_state.daily_overspend_alert.text
    assert final_state.daily_overspend_alert.text != "No Reminders Today"

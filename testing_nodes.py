"""End-to-end harness that runs the agent nodes with live services.

This script mirrors the control flow from `agent_graph.py` and prints rich state
information after each node executes so the full pipeline can be inspected
manually. It intentionally relies on real MongoDB and Groq access, so ensure
those credentials are configured before running it.
"""

import asyncio
import json
from datetime import date, datetime
from typing import Any

from services.api.app.agent.state import (
    BudgetAgentState,
    DailyAlertOverspend,
    DailyAlertSuspiciousTransaction,
    ProcessFlag,
    RunMeta,
)
from services.api.app.agent.nodes import (
    coordinator_node,
    daily_overspend_alert_node,
    daily_suspicious_transaction_alert_node,
    import_data_node,
    import_txn_data_for_period_report_node,
    period_report_node,
)


def _print_section(title: str) -> None:
    line = "=" * 100
    print(f"\n{line}\n{title}\n{line}")


def _print_key_value(label: str, value: Any, *, indent: int = 2) -> None:
    prefix = " " * indent
    print(f"{prefix}{label}: {value}")


def _print_json_payload(label: str, payload: Any, *, indent: int = 2, max_chars: int = 2000) -> None:
    prefix = " " * indent

    if payload in (None, ""):
        print(f"{prefix}{label}: <empty>")
        return

    if isinstance(payload, str):
        data_str = payload
        try:
            parsed = json.loads(payload)
            data_str = json.dumps(parsed, indent=2, default=str)
        except json.JSONDecodeError:
            pass
    else:
        data_str = json.dumps(payload, indent=2, default=str)

    if len(data_str) > max_chars:
        preview = data_str[: max_chars - 3] + "..."
    else:
        preview = data_str

    print(f"{prefix}{label}:\n{prefix}{preview}")


def _build_initial_state() -> BudgetAgentState:
    now = datetime.now()
    return BudgetAgentState(
        run_meta=RunMeta(
            run_id=f"manual-harness-{now.strftime('%Y%m%d-%H%M%S')}",
            today=date.today(),
            tz="UTC",
        ),
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
        task_info="daily_tasks",
    )


def _describe_last_day_transactions(state: BudgetAgentState) -> None:
    if not state.last_day_txn:
        _print_key_value("Last day transactions", "<none>")
        return

    print("  Last day transactions (JSON strings):")
    for idx, txn_json in enumerate(state.last_day_txn, start=1):
        prefix = f"    {idx}. "
        try:
            parsed = json.loads(txn_json)
            pretty = json.dumps(parsed, indent=2, default=str)
        except json.JSONDecodeError:
            pretty = txn_json
        print(prefix + pretty.replace("\n", f"\n{' ' * len(prefix)}"))


def _summarize_budget(state: BudgetAgentState) -> None:
    if not state.current_month_budget:
        _print_key_value("Current month budget", "<empty>")
        return

    try:
        budget_payload = json.loads(state.current_month_budget)
    except json.JSONDecodeError:
        _print_key_value("Current month budget", "<invalid JSON>")
        return

    if isinstance(budget_payload, dict):
        budget_rows = budget_payload.get("current_month_budget", [])
    elif isinstance(budget_payload, list):
        budget_rows = budget_payload
    else:
        budget_rows = []

    _print_key_value("Budget categories", len(budget_rows))
    preview = budget_rows[:3]
    _print_json_payload("Budget sample", preview)


def _summarize_overspend(state: BudgetAgentState) -> None:
    if not state.overspend_budget_data:
        _print_key_value("Overspend data", "<empty>")
        return

    if isinstance(state.overspend_budget_data, str) and state.overspend_budget_data.startswith("No Data"):
        _print_key_value("Overspend data", state.overspend_budget_data)
        return

    try:
        overspend_payload = json.loads(state.overspend_budget_data)
    except json.JSONDecodeError:
        _print_key_value("Overspend data", "<invalid JSON>")
        return

    if isinstance(overspend_payload, dict):
        overspend_rows = overspend_payload.get("overspend_categories", [])
    elif isinstance(overspend_payload, list):
        overspend_rows = overspend_payload
    else:
        overspend_rows = []

    _print_key_value("Overspent categories", len(overspend_rows))
    preview = overspend_rows[:5]
    _print_json_payload("Overspend sample", preview)


def _summarize_period_transactions(state: BudgetAgentState) -> None:
    _print_json_payload("Current month transactions", state.current_month_txn)
    _print_json_payload("Previous month transactions", state.previous_month_txn)


async def main() -> None:
    _print_section("Initializing budget agent state")
    state = _build_initial_state()
    _print_json_payload("Initial state", state.model_dump())

    _print_section("Step 1: Running import_data_node")
    state = await import_data_node(state)
    _summarize_budget(state)
    _summarize_overspend(state)
    _describe_last_day_transactions(state)

    _print_section("Step 2: Running coordinator_node")
    state = await coordinator_node(state)
    _print_key_value("Task routing decision", state.task_info)

    ran_period_tasks = False

    _print_section("Step 3: Running daily task nodes")
    state = await daily_overspend_alert_node(state)
    _print_key_value("Daily overspend alert", state.daily_overspend_alert.text)
    _print_key_value("Overspend alert flag", state.process_flag.daily_overspend_alert_done)

    state = await daily_suspicious_transaction_alert_node(state)
    _print_key_value(
        "Suspicious transactions alert",
        state.daily_alert_suspicious_transaction.text,
    )
    _print_key_value(
        "Suspicious alert flag",
        state.process_flag.daily_suspicious_transaction_alert_done,
    )

    if state.task_info == "both_tasks":
        ran_period_tasks = True
        _print_section("Step 4: Running period task nodes")
        state = await import_txn_data_for_period_report_node(state)
        _summarize_period_transactions(state)

        state = await period_report_node(state)
        _print_json_payload("Period report output", state.period_report)
        _print_key_value("Period report flag", state.process_flag.period_report_done)
    else:
        _print_section("Step 4: Period tasks skipped")
        _print_key_value("Reason", "Coordinator routed daily tasks only")

    _print_section("Workflow complete")
    _print_key_value("Task info", state.task_info)
    _print_key_value("Daily overspend alert flag", state.process_flag.daily_overspend_alert_done)
    _print_key_value(
        "Suspicious transaction alert flag", state.process_flag.daily_suspicious_transaction_alert_done
    )
    _print_key_value("Period report flag", state.process_flag.period_report_done)
    if ran_period_tasks:
        _print_json_payload("Final period report", state.period_report)


if __name__ == "__main__":
    asyncio.run(main())

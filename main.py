"""Production entry point to run the budget agent graph once."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from services.api.app.agent.agent_graph import create_budget_graph
from services.api.app.agent.state import (
    BudgetAgentState,
    DailyAlertOverspend,
    DailyAlertSuspiciousTransaction,
    ProcessFlag,
    RunMeta,
)


def _build_initial_state() -> BudgetAgentState:
    now = datetime.now(timezone.utc)
    return BudgetAgentState(
        run_meta=RunMeta(
            run_id=f"budget-agent-run-{now.strftime('%Y%m%d-%H%M%S')}",
            today=now.date(),
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
    )


async def run_agent() -> BudgetAgentState:
    graph = create_budget_graph()
    app = graph.compile()

    initial_state = _build_initial_state()
    logging.info("Starting agent run with run_id=%s", initial_state.run_meta.run_id)

    result = await app.ainvoke(initial_state)
    if not isinstance(result, BudgetAgentState):
        result = BudgetAgentState.model_validate(result)

    logging.info(
        "Agent completed; task route=%s, flags=%s",
        result.task_info,
        result.process_flag.model_dump(),
    )
    return result


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )

    try:
        final_state = asyncio.run(run_agent())
    except KeyboardInterrupt:  # pragma: no cover - interactive convenience
        logging.warning("Agent run interrupted by user")
        return

    email_info = final_state.email_info
    print("\n=== Agent run summary ===")
    print(f"Task route: {final_state.task_info}")
    print("Process flags:", final_state.process_flag.model_dump())
    if email_info:
        print("Email subject:", email_info.subject)
        snippet = email_info.body[:400].replace("\n", " ") + (
            "..." if len(email_info.body) > 400 else ""
        )
        print("Email preview:", snippet)
    else:
        print("No email info captured.")


if __name__ == "__main__":
    main()

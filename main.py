"""Production entry point to run the budget agent graph once."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from services.api.app.agent.agent_graph import create_budget_graph
from services.api.app.agent.state import (
    BudgetAgentState,
    DailyAlertOverspend,
    DailyAlertSuspiciousTransaction,
    ProcessFlag,
    RunMeta,
)
from services.api.app.logging_config import get_logger, set_correlation_id, setup_logging

# Initialize structured logging
setup_logging()
logger = get_logger(__name__)


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
    """
    Run the budget agent graph with error handling.

    Returns:
        Final agent state

    Raises:
        Exception: On unrecoverable agent execution failures
    """
    try:
        logger.info("Initializing budget agent graph")
        graph = create_budget_graph()
        app = graph.compile()

        initial_state = _build_initial_state()

        # Set correlation ID for request tracing
        set_correlation_id(initial_state.run_meta.run_id)

        logger.info(
            "Starting agent run",
            extra={
                "run_id": initial_state.run_meta.run_id,
                "today": str(initial_state.run_meta.today),
                "timezone": initial_state.run_meta.tz,
            },
        )

        result = await app.ainvoke(initial_state)
        if not isinstance(result, BudgetAgentState):
            result = BudgetAgentState.model_validate(result)

        logger.info(
            "Agent completed successfully",
            extra={
                "task_route": result.task_info,
                "process_flags": result.process_flag.model_dump(),
            },
        )
        return result
    except Exception as exc:
        logger.error("Agent execution failed", exc_info=True, extra={"error": str(exc)})
        raise


def main() -> None:
    """
    Main entry point with comprehensive error handling.

    Implements graceful degradation:
    - Catches keyboard interrupts for clean shutdown
    - Logs all errors with stack traces
    - Provides user-friendly error messages
    """
    logger.info("Budget Agent starting")

    try:
        final_state = asyncio.run(run_agent())
    except KeyboardInterrupt:  # pragma: no cover - interactive convenience
        logger.warning("Agent run interrupted by user")
        return
    except Exception as exc:
        logger.error("Fatal error during agent run", exc_info=True, extra={"error": str(exc)})
        print("\n=== Agent run FAILED ===")
        print(f"Error: {exc}")
        print("Check logs for details.")
        return

    # Display summary
    email_info = final_state.email_info
    logger.info("Displaying agent run summary")

    print("\n=== Agent run summary ===")
    print(f"Task route: {final_state.task_info}")
    print("Process flags:", final_state.process_flag.model_dump())

    if email_info:
        logger.info(
            "Email generated",
            extra={
                "subject": email_info.subject,
                "body_length": len(email_info.body),
            },
        )
        print("Email subject:", email_info.subject)
        snippet = email_info.body[:400].replace("\n", " ") + (
            "..." if len(email_info.body) > 400 else ""
        )
        print("Email preview:", snippet)
    else:
        logger.info("No email generated")
        print("No email info captured.")

    logger.info("Budget Agent completed successfully")


if __name__ == "__main__":
    main()

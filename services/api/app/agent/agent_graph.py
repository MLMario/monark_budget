from typing import Dict, Any, Literal
import logging
from datetime import datetime
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from .state import BudgetAgentState
from .nodes import (
    import_data_node,
    coordinator_node,
    daily_overspend_alert_node,
    daily_suspicious_transaction_alert_node,
    import_current_month_txn_node,
    import_previous_month_txn_node,
    eow_period_report_node,
    eom_period_report_node,
    email_node
)
from .agent_utilities import task_management
from services.api.pipelines.mongo_client import MongoDBClient

logger = logging.getLogger(__name__)


def create_budget_graph() -> StateGraph:

    graph_builder = StateGraph(BudgetAgentState)

    """
    Nodes:
    1) Data Import Node:
        - Get transactions and budget data from MongoDB (Mongo DB is updated by a daily pipeline that pulls data from MonarchMoney using credentials stored in config)
        - Imports current month and past month budget + overspend data
        - Process yesterday transactions and updates them on state

    2) Coordinator Node:
        - Checks if it's EOW (Monday), EOM (first day of month), or regular day
        - Routes to appropriate workflow: "daily_tasks", "eow_tasks", or "eom_tasks"
        - Priority: EOM > EOW > Daily (if both EOW and EOM, EOM takes precedence)

    Daily Tasks (Always Run):

    1) Daily Overspend Alert Node:
        - Input: current_month_overspend_budget_data from state
        - Action: LLM analyzes overspend categories and generates DailyOverspendAlert instances
        - Output: Updates state daily_overspend_alert instance
        - Updates process_flag.daily_overspend_alert_done = True

    2) Daily Suspicious Transaction Alert Node:
        - Input: last_day_txn from state
        - Action1: LLM evaluates each transaction for suspicious activity
        - Action2: Creates fictional funny story about the transactions
        - Output: Updates state daily_alert_suspicious_transaction instance
        - Updates process_flag.daily_suspicious_transaction_alert_done = True

    EOW Tasks (Mondays only):

    1) Import Current Month Txn Node:
        - Imports current month transactions (first day of current month to yesterday)
        - Updates state.current_month_txn

    2) EOW Period Report Node:
        - Input: current_month_overspend_budget_data, current_month_txn from state
        - Action: LLM analyzes current month overspent categories with current month transactions
        - Output: Updates state period_report with EOW analysis
        - Updates process_flag.period_report_done = True

    EOM Tasks (First day of month only):

    1) Import Previous Month Txn Node:
        - Imports previous month transactions (first day to last day of previous month)
        - Updates state.previous_month_txn

    2) EOM Period Report Node:
        - Input: past_month_overspend_budget_data, previous_month_txn from state
        - Action: LLM analyzes previous month overspent categories with previous month transactions
        - Output: Updates state period_report with EOM analysis
        - Updates process_flag.period_report_done = True

    """

    # Add nodes to graph
    graph_builder.add_node("import_data_node", import_data_node)
    graph_builder.add_node("daily_overspend_alert_node", daily_overspend_alert_node)
    graph_builder.add_node("daily_suspicious_transaction_alert_node", daily_suspicious_transaction_alert_node)
    graph_builder.add_node("coordinator_node", coordinator_node)

    # EOW nodes
    graph_builder.add_node("import_current_month_txn_node", import_current_month_txn_node)
    graph_builder.add_node("eow_period_report_node", eow_period_report_node)

    # EOM nodes
    graph_builder.add_node("import_previous_month_txn_node", import_previous_month_txn_node)
    graph_builder.add_node("eom_period_report_node", eom_period_report_node)

    # Email node
    graph_builder.add_node("email_node", email_node)

    # Define edges - Daily flow (always runs)
    graph_builder.add_edge(START, "import_data_node")
    graph_builder.add_edge("import_data_node", "daily_overspend_alert_node")
    graph_builder.add_edge("daily_overspend_alert_node", "daily_suspicious_transaction_alert_node")
    graph_builder.add_edge("daily_suspicious_transaction_alert_node", "coordinator_node")

    # Conditional routing from coordinator
    graph_builder.add_conditional_edges("coordinator_node",
                                        task_management,
                                         {
                                            "daily_tasks": "email_node",
                                            "eow_tasks": "import_current_month_txn_node",
                                            "eom_tasks": "import_previous_month_txn_node"
                                         }
                                         )

    # EOW flow
    graph_builder.add_edge("import_current_month_txn_node", "eow_period_report_node")
    graph_builder.add_edge("eow_period_report_node", "email_node")

    # EOM flow
    graph_builder.add_edge("import_previous_month_txn_node", "eom_period_report_node")
    graph_builder.add_edge("eom_period_report_node", "email_node")

    # End
    graph_builder.add_edge("email_node", END)

    return graph_builder


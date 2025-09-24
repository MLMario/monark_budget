from typing import Dict, Any, Literal
import logging
from datetime import datetime
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from .state import BudgetAgentState


logger = logging.getLogger(__name__)


def create_budget_graph() -> StateGraph:

    graph_builder = StateGraph(BudgetAgentState)

    """
    Nodes: 
    1) Data Import Node: 
        - Get transactions and budget data from MongoDB (Mongo DB is updated by a daily pipeline that pulls data from MonarchMoney using credentials stored in config)
        - Process OverspendBudgetData and yesterday transactions and updates them on state
    2) Coordinator Node:
        - Checks if it's EOW or EOM and if so, runs both daily tasks and period report tasks, otherwise only runs daily tasks
    Daily Tasks:

    1) Daily Overspend Alert Node: 
        - Input: OverspendBudgetData from state
        - Action: LLM analyzes overspend categories and generates DailyOverspendAlert instances for each overspend category
        - Output: Updates state daily_overspend_alert instance (kind = "daily_overspend_alert", text = "you have overspent in the following categories ...")

        - Updates process_flag.daily_overspend_alert_done = True

    2) Daily Suspicious Transaction Alert Node:
        - Input: last_day_txn from state
        - Action1 : LLM looks at last_day_txn AND LOOPS THROUGH EACH LAST_DAY_TRANSACTION , LLM will evaluate if a txn is suspicious or not and adds to state daily_suspicious_transactions (a list)
        - Action 2: Once action 1 is done, we call a second LLM  to write a fictional funny story where characters Alicia, Mario or Both them go through the day and do this transactions and 
        how they learn their lesson on not doing it again!

        Output: Updates state daily_alert_suspicious_transaction instance (kind = "daily_suspicious_transaction_alert", text = "funny story")

        - Updates process_flag.daily_suspicious_transaction_alert_done = True

    Period Tasks (EOW or EOM):
    1) Period Report Node:
        - Input: current_month_budget, current_month_txn, previous_month_txn from state
        - Action:
             LLM Loops through  OverspendBudgetData.overspend_categories, create a report_category instance, 
             from previous and current month transactions it fetches all transaction of the same category
        - Output: Updates state period_report instance (period = "month", categories_in_report = [...], report_summary = "...", drivers = "...", recommended_actions = "...", report_funny_quip = "...")
        
        - Updates process_flag.period_report_done = True
        
    
    """


    graph_builder.add_node("import_data_node", import_data_node)
    graph_builder.add_node("coordinator_node", coordinator_node)
    graph_builder.add_node("daily_overspend_alert_node", daily_overspend_alert_node)
    graph_builder.add_node("daily_suspicious_transaction_alert_node", daily_suspicious_transaction_alert_node)
    graph_builder.add_node("period_report_node", period_report_node)
    graph_builder.add_node("wait_node", wait_node)
    graph_builder.add_node("policy_enforcer_node", policy_enforcer_node)
    graph_builder.add_edge("error_handler_node", error_handler_node)

    graph_builder.add_edge(START, "import_data_node")
    graph_builder.add_edge("import_data_node", "coordinator_node")

    graph_builder.add_conditional_edges(
        "coordinator_node",
        task_management_function,
        {
            "daily_tasks": "daily_overspend_alert_node",
            "both_tasks": ["daily_overspend_alert_node", "period_report_node"]
        }

    )

    graph_builder.add_edge("daily_overspend_alert_node","daily_suspicious_transaction_alert_node")
    graph_builder.add_edge("daily_suspicious_transaction_alert_node","wait_node")

    graph_builder.add_edge("period_report_node", "wait_node")

    graph_builder.add_conditional_edges("wait_node",
                                        wait_asses_function,
                                         {
                                            "wait": "wait_node",
                                            "proceed": "policy_enforcer_node"
                                         }
                                         )

    graph_builder.add_edge("policy_enforcer_node", END)


    return graph_builder


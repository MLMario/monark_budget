from services.api.app.agent import state
from services.api.pipelines.mongo_client import MongoDBClient

from services.api.app.agent.state import BudgetAgentState, BudgetData, BudgetRow, OverspendBudgetData, TransactionRow
from services.api.app.agent.agent_utilities import filter_overspent_categories

import logging
from datetime import datetime,timedelta
import json

logger = logging.getLogger(__name__)

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

def import_data_node(state: BudgetAgentState) -> BudgetAgentState:

    #Create MongoDB Client to Import Data 
    mongo_client = MongoDBClient() 

    logger.info("Importing Budget Data from MongoDB [START]")
    budget_json = mongo_client.import_budget_data()
    
    # Data Model Validation Processing (Implicit given the use of Pydantic models)
    budget_list_data = json.loads(budget_json)
    budget_rows = [BudgetRow(**row) for row in budget_list_data]
    pydantic_budget_model = BudgetData(current_month_budget=budget_rows)
    state.current_month_budget = pydantic_budget_model.model_dump_json()
    logger.info("Importing Budget Data from MongoDB [DONE]")


    logger.info("Filtering Overspent Categories [START]")

    overspend_json = filter_overspent_categories(budget_json) 

    # Data Model Validation Processing (Implicit given the use of Pydantic models)
    overspend_list_data = json.loads(overspend_json)
    overspend_rows = [BudgetRow(**row) for row in overspend_list_data]
    pydantic_overspend_budget_model = OverspendBudgetData(overspend_categories=overspend_rows)

    # we want the budget data as one json string so that model can look at it all at once, it will not evaluate each category but make an alert message summary
    state.overspend_budget_data = pydantic_overspend_budget_model.model_dump_json()
    logger.info("Filtering Overspent Categories [DONE]")


    logger.info("Importing Last Day Transaction Data from MongoDB [START]")

    last_day = datetime.now() - timedelta(days=1)
    last_day_str = last_day.strftime('%Y-%m-%d')

    transactions_json = mongo_client.import_transaction_data(start_date=last_day_str, end_date=last_day_str)
    
    # Convert JSON string to TransactionRow objects
    transactions_list_data = json.loads(transactions_json)
    pydantic_transactions_model = [TransactionRow(**txn) for txn in transactions_list_data]
    state.last_day_txn = [txn.model_dump_json() for txn in pydantic_transactions_model] # Keeping as a list since the LLM model should iterate through each transaction

    logger.info("Importing Last Day Transaction Data from MongoDB [DONE]")

    return state

#it just so that it re-route tasks depending on the day
def coordinator_node(state: BudgetAgentState) -> BudgetAgentState:

    return state

def daily_overspend_alert_node(state: BudgetAgentState) -> BudgetAgentState:

    """ 
    - Input: OverspendBudgetData from state
    - Action: LLM analyzes overspend categories and generates DailyOverspendAlert instances for each overspend category
    - Output: Updates state daily_overspend_alert instance (kind = "daily_overspend_alert", text = "you have overspent in the following categories ...")

    - Updates process_flag.daily_overspend_alert_done = True
    
    """

    overspend_budget_str = state.overspend_budget_data




    return state

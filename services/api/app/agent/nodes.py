from services.api.app.agent import state
from services.api.pipelines.mongo_client import AsyncMongoDBClient

from services.api.app.agent.state import BudgetAgentState, BudgetData, BudgetRow, OverspendBudgetData, TransactionRow, DailyAlertOverspend, DailyAlertSuspiciousTransaction, DailySuspiciousTransaction
from services.api.app.agent.agent_utilities import filter_overspent_categories, call_llm, task_management

from services.api.app.domain.prompts import (
    BUDGET_ALERT_PROMPT,
    SUSPICIOUS_TXN_PROMPT,
    SUSPICIOUS_TXN_STORY_PROMPT
    )
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

async def import_data_node(state: BudgetAgentState) -> BudgetAgentState:

    #Create MongoDB Client to Import Data 
    mongo_client = AsyncMongoDBClient() 

    logger.info("Importing Budget Data from MongoDB [START]")
    budget_json = await mongo_client.import_budget_data(filter_query={'category_group_type': 'expense'})
    
    # Data Model Validation Processing (Implicit given the use of Pydantic models)
    budget_list_data = json.loads(budget_json)
    budget_rows = [BudgetRow(**row) for row in budget_list_data]
    pydantic_budget_model = BudgetData(current_month_budget=budget_rows)
    state.current_month_budget = pydantic_budget_model.model_dump_json()
    logger.info("Importing Budget Data from MongoDB [DONE]")


    logger.info("Filtering Overspent Categories [START]")

    overspend_json = filter_overspent_categories(budget_json) 

    if not overspend_json:
        state.overspend_budget_data = "No Data, User hasn't overspent"
    else:
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

    transactions_json = await mongo_client.import_transaction_data(start_date=last_day_str, end_date=last_day_str)
    
    # Convert JSON string to TransactionRow objects
    transactions_list_data = json.loads(transactions_json)
    pydantic_transactions_model = [TransactionRow(**txn) for txn in transactions_list_data]
    state.last_day_txn = [txn.model_dump_json() for txn in pydantic_transactions_model] # Keeping as a list since the LLM model should iterate through each transaction

    logger.info("Importing Last Day Transaction Data from MongoDB [DONE]")

    return state

#it just so that it re-route tasks depending on the day
async def coordinator_node(state: BudgetAgentState) -> BudgetAgentState:


    state.task_info = task_management()

    return state

async def daily_overspend_alert_node(state: BudgetAgentState) -> BudgetAgentState:

    """ 
    - Input: OverspendBudgetData from state
    - Action: LLM analyzes overspend categories and generates DailyOverspendAlert instances for each overspend category
    - Output: Updates state daily_overspend_alert instance (kind = "daily_overspend_alert", text = "you have overspent in the following categories ...")

    - Updates process_flag.daily_overspend_alert_done = True
    
    """

    overspend_budget_data = state.overspend_budget_data

    response_text = await call_llm(
        temperature=0.8,
        prompt_obj = BUDGET_ALERT_PROMPT,
        budget_data = overspend_budget_data
    )

    state.daily_overspend_alert = DailyAlertOverspend(
        kind="daily_overspend_alert",
        text= response_text
    )

    state.process_flag.daily_overspend_alert_done = True

    return state

async def daily_suspicious_transaction_alert_node(state: BudgetAgentState) -> BudgetAgentState:

    """ 
    - Input: last_day_txn from state
    - Action1 : LLM looks at last_day_txn AND LOOPS THROUGH EACH LAST_DAY_TRANSACTION , LLM will evaluate if a txn is suspicious or not and adds to state daily_suspicious_transactions (a list)
    - Action 2: Once action 1 is done, we call a second LLM  to write a fictional funny story based on all suspicious transactions

    Output: Updates state daily_alert_suspicious_transaction instance (kind = "daily_suspicious_transaction_alert", text = "funny story")

    - Updates process_flag.daily_suspicious_transaction_alert_done = True

    """

    last_day_txn = state.last_day_txn

    if not last_day_txn:

        state.daily_alert_suspicious_transaction =  DailyAlertSuspiciousTransaction(
            kind="daily_suspicious_transaction_alert",
            text="No Transactions to Review Today"
        )
        state.process_flag.daily_suspicious_transaction_alert_done = True
        return state

    suspicious_transactions = []

    for txn_data in last_day_txn:

        txn_model = TransactionRow.model_validate_json(txn_data)

        response_text = await call_llm(
            temperature= 0.9,
            prompt_obj = SUSPICIOUS_TXN_PROMPT,
            transaction= txn_data
        )

        try: 
           response_dict = json.loads(response_text)
           response_is_json = True

        except:
           response_is_json = False
           logger.error(f"Failed to decode JSON from response: {response_text}")

        if response_is_json: 
            txn_type = response_dict.get("type", "not_suspicious")

            suspicious_txn = DailySuspiciousTransaction(
                txn_type= txn_type,
                suspicious_transaction = txn_model
            )


            if suspicious_txn.txn_type == "suspicious":
                suspicious_transactions.append(suspicious_txn)
       
        else:
            logger.error(f"Skipping transaction due to invalid JSON response: {response_text}")

    if not suspicious_transactions:
        state.daily_alert_suspicious_transaction = DailyAlertSuspiciousTransaction(
            kind="daily_suspicious_transaction_alert",
            text="No 'Funny' Transactions Today"
        )
        state.process_flag.daily_suspicious_transaction_alert_done = True
        return state

    else:

        suspicious_transactions_json = [json.loads(txn_data.model_dump_json()) for txn_data in suspicious_transactions]

        suspicious_transactions_str = json.dumps(suspicious_transactions_json, indent=2)

        response_story = await call_llm(
            temperature=0.7,
            prompt_obj = SUSPICIOUS_TXN_STORY_PROMPT,
            transactions = suspicious_transactions_str
            )
        
        state.daily_alert_suspicious_transaction = DailyAlertSuspiciousTransaction(
            kind="daily_suspicious_transaction_alert",
            text= response_story
        )
        state.process_flag.daily_suspicious_transaction_alert_done = True

        return state
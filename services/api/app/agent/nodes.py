from services.api.app.agent import state
from services.api.pipelines.mongo_client import AsyncMongoDBClient
from .agent_utilities import SendEmail
from services.api.app.domain.prompts import Prompt

from services.api.app.agent.state import (
    BudgetAgentState, BudgetData, BudgetRow,
      OverspendBudgetData, TransactionRow,
      DailyAlertOverspend, DailyAlertSuspiciousTransaction,
      DailySuspiciousTransaction, ReportCategory, EmailInfo
)
from services.api.app.agent.agent_utilities import filter_overspent_categories, call_llm,call_llm_reasoning, task_management,clean_llm_output, extract_json_text, validate_html

from services.api.app.domain.prompts import (
    BUDGET_ALERT_PROMPT,
    SUSPICIOUS_TXN_PROMPT,
    SUSPICIOUS_TXN_STORY_PROMPT,
    TXN_ANALYSIS_PROMPT,
    PERIOD_REPORT_PROMPT,
    SYSTEM_PROMPT,
    HTNML_AGENT_PROMPT
)
import logging
from datetime import datetime,timedelta
from config import Settings
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

    last_day_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    transactions_json = await mongo_client.import_transaction_data(start_date=last_day_date, end_date=last_day_date)
    
    # Convert JSON string to TransactionRow objects
    transactions_list_data = json.loads(transactions_json)
    pydantic_transactions_model = [TransactionRow(**txn) for txn in transactions_list_data]
    state.last_day_txn = [txn.model_dump_json() for txn in pydantic_transactions_model] # Keeping as a list since the LLM model should iterate through each transaction

    logger.info("Importing Last Day Transaction Data from MongoDB [DONE]")
    mongo_client.close_connection()

    return state

#it just so that it re-route tasks depending on the day
async def coordinator_node(state: BudgetAgentState) -> BudgetAgentState:


    state.task_info = task_management()

    return state

async def daily_overspend_alert_node(state: BudgetAgentState) -> BudgetAgentState:

    overspend_budget_data = state.overspend_budget_data

    response_text = await call_llm(
        temperature=0.8,
        prompt_obj = BUDGET_ALERT_PROMPT,
        budget_data = overspend_budget_data,
        max_tokens=700
    )

    state.daily_overspend_alert = DailyAlertOverspend(
        kind="daily_overspend_alert",
        text= response_text
    )

    state.process_flag.daily_overspend_alert_done = True

    return state

async def daily_suspicious_transaction_alert_node(state: BudgetAgentState) -> BudgetAgentState:

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

        response_text = await call_llm_reasoning(
            system_prompt= SYSTEM_PROMPT.prompt + """ 
            Respond only with JSON using this format:
                    {
                    "type": "positive|not_compliant"
                    }
            
            """,
            temperature = 0.8,
            prompt_obj = SUSPICIOUS_TXN_PROMPT,
            transaction = txn_data,
            max_tokens=400,
            model = Settings.GROQ_OPENAI_20B_MODE,
            reasoning_format='hidden',
            response_format='text',
            reasoning_effort = 'medium'
        )

        clean_response = clean_llm_output(response_text) 
        json_text = extract_json_text(clean_response)

        try: 
           
           response_dict = json.loads(json_text)
           response_is_json = True

        except json.JSONDecodeError as exc:
           response_is_json = False
           logger.error("Failed to decode JSON response: %s; raw text=%r", exc, json_text)


        if response_is_json: 
            
            txn_type = response_dict.get("type", "not_compliant")

            if txn_type == "not_compliant":

                suspicious_txn = DailySuspiciousTransaction(
                    txn_type=txn_type,
                    suspicious_transaction=txn_model
                )

                
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
            model=Settings.GROQ_LLAMA_VERSATILE,
            temperature = 0.7,
            prompt_obj = SUSPICIOUS_TXN_STORY_PROMPT,
            suspicious_transactions = suspicious_transactions_str
            )
        
        state.daily_alert_suspicious_transaction = DailyAlertSuspiciousTransaction(
            kind="daily_suspicious_transaction_alert",
            text= response_story
        )
        state.process_flag.daily_suspicious_transaction_alert_done = True

        return state
    

async def import_txn_data_for_period_report_node(state: BudgetAgentState) -> BudgetAgentState:

    
    mongo_client = AsyncMongoDBClient() 

    logger.info("Importing Last Day Transaction Data from MongoDB [START]")

    last_day = datetime.now() - timedelta(days=1)
    last_day_date = last_day.strftime('%Y-%m-%d')

    start_month= last_day.replace(day=1)
    start_month_date = start_month.strftime('%Y-%m-%d')

    this_month_txn = await mongo_client.import_transaction_data(start_date=start_month_date, end_date=last_day_date)
    
    last_month_end = start_month - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)

    last_month_start_date = last_month_start.strftime('%Y-%m-%d')
    last_month_end_date = last_month_end.strftime('%Y-%m-%d')

    this_month_txn = await mongo_client.import_transaction_data(start_date=start_month_date, end_date=last_day_date)
    last_month_txn = await mongo_client.import_transaction_data(start_date=last_month_start_date, end_date=last_month_end_date)

    if not this_month_txn:
        raise ValueError("No transaction data found for the this month period.")

    if not last_month_txn:
        raise ValueError("No transaction data found for the last month period.")
    
    # This month transactions

    if  this_month_txn:
        this_month_transactions_list_data = json.loads(this_month_txn)

        pydantic_this_month_transactions_model = [TransactionRow(**txn) for txn in this_month_transactions_list_data]
        this_month_txn_dicts = [json.loads(txn.model_dump_json()) for txn in pydantic_this_month_transactions_model] # Keeping as a list since the LLM model should iterate through each transaction
        state.current_month_txn = json.dumps(this_month_txn_dicts, indent=2)
    else:
        state.current_month_txn = "No Data, User hasn't done any transaction this month"

    if last_month_txn:
        last_month_transactions_list_data = json.loads(last_month_txn)
        pydantic_last_month_transactions_model = [TransactionRow(**txn) for txn in last_month_transactions_list_data]
        last_month_txn_dicts = [json.loads(txn.model_dump_json()) for txn in pydantic_last_month_transactions_model] # Keeping as a list since the LLM model should iterate through each transaction
        state.previous_month_txn = json.dumps(last_month_txn_dicts, indent=2)
    else:
        state.previous_month_txn = "No Data, User hasn't done any transaction last month"
   
    mongo_client.close_connection()
    
    return state

async def period_report_node(state: BudgetAgentState) -> BudgetAgentState:
    """ 
    - Input: current_month_budget, current_month_txn, previous_month_txn from state
    - Action:
         LLM Loops through  OverspendBudgetData.overspend_categories, create a report_category instance, 
         from previous and current month transactions it fetches all transaction of the same category
    - Output: Updates state period_report instance (period = "month", categories_in_report = [...], report_summary = "...", drivers = "...", recommended_actions = "...", report_funny_quip = "...")
    
    - Updates process_flag.period_report_done = True
    
    """
    if state.overspend_budget_data != "No Data, User hasn't overspent":
        over_spend_budget = json.loads(state.overspend_budget_data).get("overspend_categories","")
    else:
        over_spend_budget = state.overspend_budget_data



    analysis_responses = []

    if over_spend_budget != "No Data, User hasn't overspent":

        over_spend_budget = json.loads(state.overspend_budget_data).get("overspend_categories","")

        if state.current_month_txn != "No Data, User hasn't done any transaction this month":
            current_month_txn = json.loads(state.current_month_txn)
        else: 
            current_month_txn = state.current_month_txn

        if state.previous_month_txn != "No Data, User hasn't done any transaction last month":
            previous_month_txn = json.loads(state.previous_month_txn)
        else:
            previous_month_txn = state.previous_month_txn
        
        for record in over_spend_budget:

            logger.info("Processing category: %s", record.get('category_name'))

            category_name = record.get('category_name')
            logger.info("Period Report Task: Starting Analysis of Category %s", record.get('category_name'))

            # Filter transactions for the current category
            current_month_category_txn = [txn_record for txn_record in current_month_txn if txn_record.get('category_name') == category_name]
            previous_month_category_txn = [txn_record for txn_record in previous_month_txn if txn_record.get('category_name') == category_name]

            response_text = await call_llm_reasoning(
                model = Settings.GROQ_OPENAI_20B_MODE,
                temperature = 0.8,
                prompt_obj = TXN_ANALYSIS_PROMPT,
                this_month_txn = json.dumps(current_month_category_txn, indent=2),
                last_month_txn = json.dumps(previous_month_category_txn, indent=2),
                max_tokens=600,
                reasoning_effort='high',
                reasoning_format='hidden'
            )

            response_text_cleaned = clean_llm_output(response_text)

            logger.info("Period Report Task: Category Analysis Complete for %s", record.get('category_name'))
            logger.info("Period Report Task: LLM Category Analysis Response: %s", response_text_cleaned)

            #model validation and processing
            response_model = ReportCategory(
                category_budget_variability=record.get("category_budget_variability"),
                category_name=category_name,
                category_group_name=record.get("category_group_name"),
                overspent_amount=record.get("remaining_amount", 0) * -1,  # Convert to positive overspend amount
                llm_response=response_text_cleaned
            )

            analysis_responses.append(response_model)

        periodo_report_data_input = json.dumps([json.loads(ReportCategory.model_dump_json(response)) for response in analysis_responses], indent=2)

        print(periodo_report_data_input)

        response_period_report = await call_llm_reasoning(
            model = Settings.GROQ_OPENAI_20B_MODE,
            temperature = 0.8,
            prompt_obj=PERIOD_REPORT_PROMPT,
            max_tokens= 4020 ,
            periodo_report_data_input = periodo_report_data_input,
            reasoning_effort='high',
            reasoning_format = 'hidden'
        )

        state.period_report = response_period_report
        state.process_flag.period_report_done = True

    else:
        state.period_report = "Good Job! You haven't overspent in any category this period, keep it up!"

        state.process_flag.period_report_done = True

    return state 


async def email_node(state: BudgetAgentState) -> BudgetAgentState:

    email_body_parts = []

    if state.process_flag.daily_overspend_alert_done and state.daily_overspend_alert:
        email_body_parts.append(f"--- Daily Overspend Alert ---\n{state.daily_overspend_alert.text}\n")

    if state.process_flag.daily_suspicious_transaction_alert_done and state.daily_alert_suspicious_transaction:
        email_body_parts.append(f"--- Daily Suspicious Transaction Alert ---\n{state.daily_alert_suspicious_transaction.text}\n")

    if state.process_flag.period_report_done and state.period_report:
        email_body_parts.append(f"--- Period Report ---\n{state.period_report}\n")

    email_body = "\n".join(email_body_parts) if email_body_parts else "No alerts or reports available."

    EMAIL_BODY_PROMPT = Prompt(
        name="email_body_prompt",
        prompt=email_body
        )

    response_text = await call_llm_reasoning(
            temperature=0.8,
            system_prompt = HTNML_AGENT_PROMPT.prompt,
            prompt_obj=EMAIL_BODY_PROMPT,
            max_tokens= 6020 ,
            model = Settings.GROQ_OPENAI_20B_MODE,
            reasoning_effort = 'medium',
            reasoning_format = 'hidden',
                )

    response_html, is_html = validate_html(response_text)

    if not is_html:
        logger.error("Generated email content is not valid HTML.")


    email_info = EmailInfo(
        to='mariogj1987@gmail.com, aliciaayanez@gmail.com',
        subject="Your Budget Alerts and Reports From your Friendly Budget Assistant",
        body=response_html,
        from_= Settings.SMTP_USER
    )

    send_email = SendEmail(email_info)

    await send_email.send_email_async(is_html=is_html)

    state.email_info = email_info

    return state

        


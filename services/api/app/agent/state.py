


"""

States I Need

#data
- budget 
- PeriodTransactions (can be curretn period (month ) or previous period) 


#helpers for the flow 
- period_flag
- overspend categories (filter down categoires to only include overspend categories)
- yesterday transaction (only transactions from yesterday)
- completion flags (daily budget alert, daily suspicious transaction alert, weekly / monthly report alert)

#output

- daily overspend alert  
- daily suspicious transaction alert
- End of Week or End of Month spend analysis report 


"""

from typing import Dict, List, Optional, Union, Literal
from pydantic import BaseModel, Field
from datetime import date

class RunMeta(BaseModel):
    run_id: str
    today: date
    tz: str

class BudgetRow(BaseModel):

    actual_amount: float
    category_budget_variability: Optional[Literal["fixed", "flexible", "income","goals","expense"]] = None
    category_group_name:str
    category_group_type: str
    category_name: str
    month: date
    planned_cash_flow_amount: float = 0
    remaining_amount: float = 0
    remaining_amount_percent: Optional[float] = None

class TransactionRow(BaseModel):
    amount: float
    category_id: str
    category_name:str
    createdAt: str
    description: str
    merchant_id: str
    merchant_name: str
    transaction_id: str
    updatedAt: str

class BudgetData(BaseModel):
    current_month_budget: List[BudgetRow]

class DailyOverspendCategory(BaseModel):
    category_budget_variability: Optional[Literal["fixed", "flexible", "income","goals","expense"]] = None
    category_group_name: str 
    category_name: str
    planned_cash_flow_amount: float
    actual_amount: float
    remaining_amount: float
    overspent_amount: float

class OverspendBudgetData(BaseModel):
    overspend_categories: List[DailyOverspendCategory] = []

class DailyAlertOverspend(BaseModel):
    kind: str = "daily_overspend_alert"
    text: str = "No Reminders Today"

class DailySuspiciousTransaction(BaseModel):
    funny_quip: str
    suspicious_transaction: TransactionRow

class DailyAlertSuspiciousTransaction(BaseModel):
    kind: str = "daily_suspicious_transaction_alert"
    text: str = "No Suspicious Transactions Today"

class ReportCategory(BaseModel):
    category_budget_variability: Optional[Literal["fixed", "flexible", "income","goals","expense"]] = None
    category_name: str
    category_group_name: str
    overspent_amount: float
    drivers: Optional[str] = None
    recommended_actions: Optional[str] = None

class PeriodReport(BaseModel): 
    period: str
    categories_in_report: List[ReportCategory] = []
    report_summary: Optional[str] = None
    drivers: Optional[str] = None
    recommended_actions: Optional[str] = None
    report_funny_quip: Optional[str] = None

class PeriodInfo(BaseModel):
    is_end_of_period: bool = False
    type: Literal[ "week", "month"]
    start: date 
    end: date

class EmailInfo(BaseModel):
    to: str
    subject: str
    body: str

class ProcessFlag(BaseModel):
    daily_overspend_alert_done: bool = False
    daily_suspicious_transaction_alert_done: bool = False
    period_report_done: bool = False   

class BudgetAgentState(BaseModel):

    run_meta: RunMeta
    
# Agent imports data
    # imports from Mongo Db
    current_month_budget: Optional[BudgetData] = None
    current_month_txn: List[TransactionRow] = []
    previous_month_txn: List[TransactionRow] = []

    #Filtters last day txn, identifies over spend categories
    last_day_txn: List[TransactionRow] = [] #filter last day transactions adds them o a list last_day_txn
    overspend_budget_data: OverspendBudgetData # cycles through each budget cateory, checks if its overspend, if so, it creates DailyOverspendCategory instance and adds to list OverspendBudgetData.overspend_categories

    #Agent Evaluates Period

    period_info: PeriodInfo #will need helper function to determine if its end of week or month

    # For Every Day:

    # agent takes overspend_budget_data and outputs a DailyAlertOverspend
    # input: overspend_budget_data
    # agent looks at overspend_budget_data AS ONE INPUT and uses prompt to create a DailyAlertOverspend with kind = "daily_overspend_alert", text = "you have overspent in the following categories ..."
    daily_overspend_alert: DailyAlertOverspend
    # set ProcessFlag.daily_overspend_alert_done = True

    # Agent identifies suspicious transactions from last day txn
    # input: last_day_txn
    # Action: LLM looks at last_day_txn AND LOOPS THROUGH EACH LAST DAY TRANSACTION , LLM will evaluate if a txn is suspicious or not and adds to state:
    # DailySuspiciousTransaction 

    daily_suspicious_transactions: list[DailySuspiciousTransaction] = []

    # we call an LLM to write a fictional funny story where characters Alicia, Mario or Both them go through the day and do this transactions and how they learn their lesson on not doing it again!
    # here the temperature can be higher to make it more fun
    # kinds = "daily_suspicious_transaction_alert", text = "funny story about suspicious transactions"

    daily_alert_suspicious_transaction: DailyAlertSuspiciousTransaction
    # set ProcessFlag.daily_suspicious_transaction_alert_done = True
    # Action: LLM looks at last day txn and uses prompt to evaluate if a txn is suspicious or not and adds to state a DailySuspiciousTransaction instance
    

    # For End of Week or End of Month:

    #Action:
        # LLM Loops through  OverspendBudgetData.overspend_categories, create a ReportCategory instance, from previous and current month transactions it feches all transaction of the same category
        # and feeds into LLM, LLM outputs drivers and recommended actions PER ReportCategory instance, as we loop through categories we update the ReportCategory instance
        # and add to a list of PeriodReport.categories_in_report and PeriodReport.period from PeriodInfo.type (period_info.type)

        # in the same node we pass PeriodReport.categories_in_report to an LLM to add PeriodReport.summary , PeriodReport.drivers, PeriodReport.recommended_actions, PeriodReport.funny_quip 

        # output: PeriodReport instance
        # opnce it finishes updates flag of period report done

    report_category: ReportCategory

    period_report: PeriodReport

    process_flag: ProcessFlag = Field(default_factory=ProcessFlag)

    #After both process are done we go to the 

    email_info: Optional[EmailInfo] = None








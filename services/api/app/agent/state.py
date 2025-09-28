


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
    category_budget_variability: Optional[Literal["fixed", "flexible", "income","goals","expense","non_monthly"]] = None
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
    description: Optional[str] = None
    merchant_id: str
    merchant_name: str
    transaction_id: str
    updatedAt: str

class BudgetData(BaseModel):
    current_month_budget: List[BudgetRow] = []

class OverspendBudgetData(BaseModel):
    overspend_categories: List[BudgetRow] = []

class DailyAlertOverspend(BaseModel):
    kind: str = "daily_overspend_alert"
    text: str = "No Reminders Today"

class DailySuspiciousTransaction(BaseModel):
    txn_type: str
    suspicious_transaction: TransactionRow

class DailyAlertSuspiciousTransaction(BaseModel):
    kind: str = "daily_suspicious_transaction_alert"
    text: str = "No Suspicious Transactions Today"

class ReportCategory(BaseModel):
    category_budget_variability: Optional[Literal["fixed", "flexible", "income","goals","expense","non_monthly"]] = None
    category_name: str
    category_group_name: str
    overspent_amount: float
    llm_response: Optional[str] = None

class EmailInfo(BaseModel):
    to: str
    subject: str
    body: str
    from_: str

class ProcessFlag(BaseModel):
    daily_overspend_alert_done: bool = False
    daily_suspicious_transaction_alert_done: bool = False
    period_report_done: bool = False   

class BudgetAgentState(BaseModel):

    run_meta: RunMeta
    
# Agent imports data
    # imports from Mongo Db
    current_month_budget: Optional[str] = None
    current_month_txn: Optional[str] = None
    previous_month_txn: Optional[str] = None

    last_day_txn: List[str] = [] #filter last day transactions adds them o a list last_day_txn
    overspend_budget_data: Optional[str] = None # cycles through each budget cateory, checks if its overspend, if so, it creates DailyOverspendCategory instance and adds to list OverspendBudgetData.overspend_categories

    daily_overspend_alert: DailyAlertOverspend

    daily_suspicious_transactions: list[DailySuspiciousTransaction] = []


    daily_alert_suspicious_transaction: DailyAlertSuspiciousTransaction

    period_report: Optional[str] = None

    process_flag: ProcessFlag = Field(default_factory=ProcessFlag)

    email_info: Optional[EmailInfo] = None


    task_info: str = 'daily_tasks'





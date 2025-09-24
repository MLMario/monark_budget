
from services.api.pipelines.monarchmoney import MonarchMoney, RequireMFAException
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

"""
MONARK FUNCTIONS
get_accounts - gets all the accounts linked to Monarch Money
get_account_holdings - gets all of the securities in a brokerage or similar type of account
get_account_type_options - all account types and their subtypes available in Monarch Money-
get_account_history - gets all daily account history for the specified account
get_institutions -- gets institutions linked to Monarch Money
get_budgets — all the budgets and the corresponding actual amounts
get_subscription_details - gets the Monarch Money account's status (e.g. paid or trial)
get_recurring_transactions - gets the future recurring transactions, including merchant and account details
get_transactions_summary - gets the transaction summary data from the transactions page
get_transactions - gets transaction data, defaults to returning the last 100 transactions; can also be searched by date range
get_transaction_categories - gets all of the categories configured in the account
get_transaction_category_groups all category groups configured in the account-
get_transaction_details - gets detailed transaction data for a single transaction
get_transaction_splits - gets transaction splits for a single transaction
get_transaction_tags - gets all of the tags configured in the account
get_cashflow - gets cashflow data (by category, category group, merchant and a summary)
get_cashflow_summary - gets cashflow summary (income, expense, savings, savings rate)
is_accounts_refresh_complete - gets the status of a running account refresh

"""

class MonarkImport:

    def __init__(self):
        self.monarch: Optional[MonarchMoney] = None
        self.imports: Dict[str, Any] = {}
        self._logged_in: bool = False
        self.monarch = MonarchMoney()
    
    def _ensures_is_logged_in(self):

        if not self._logged_in or self.monarch is None:
            print("Must be logged in before using method :).")

    async def monarch_login(
            self, pw: str, user: str, mfa_code: str = None) -> bool: 

        try:
            
            await self.monarch.login(user, pw)

            self._logged_in = True 
            print("Logged in to MonarchMoney successfully.")
            return True

        except RequireMFAException as mfa:
            print(f"Multi-factor authentication required: {mfa}")
            await self.monarch.multi_factor_authenticate(user, pw, mfa_code)

            self._logged_in = True 
            print("Logged in to MonarchMoney successfully with MFA.")

            return True

        except Exception as e:
            print(f"Error initializing MonarchMoney: {e}")
            self._logged_in = False
            return False

    async def get_txn(self):
        
        
        self._ensures_is_logged_in()
    
        today = datetime.now()
        end_date = today - timedelta(days=1)  # Yesterday
        
        first_of_current_month = today.replace(day=1)
        first_of_previous_month = (first_of_current_month - timedelta(days=1)).replace(day=1)
        start_date_str = first_of_previous_month.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        
        transactions = await self.monarch.get_transactions(
            start_date=start_date_str, 
            end_date=end_date_str, 
            limit=1000
        )
        self.imports["transactions"] = transactions

        return transactions

    async def get_bdgt(self):

        self._ensures_is_logged_in()
        budget = await self.monarch.get_budgets()
        self.imports["budget"] = budget

        return budget


async def monark_import(pw, user):

    data = MonarkImport()

    await data.monarch_login( pw = pw, user=user)

    transactions = await data.get_txn()
    budget = await data.get_bdgt()

    imports  = {
        "transactions" : transactions,
        "budget": budget
    }


    return imports
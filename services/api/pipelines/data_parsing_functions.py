import pandas as pd
from datetime import datetime
import json
from datetime import datetime, timedelta


def parse_budget_data(budget_data):
    """
    Parse budget data into structured DataFrames
    """
    
    # Part 1: Parse categoryGroups into categories DataFrame

    categories_data = []
    
    # 1. Create a dataframe with category group and category 

    for category_group in budget_data['categoryGroups']:
        group_id = category_group['id']
        group_name = category_group['name']
        group_type = category_group.get('type', None)  # income/expense
        group_budget_variability = category_group.get('budgetVariability', None)
        
        # Process each category within the group
        for category in category_group.get('categories', []):
            categories_data.append({
                'category_group_id': group_id,
                'category_group_name': group_name,
                'category_group_type': group_type,
                'category_group_budget_variability': group_budget_variability,
                'category_id': category['id'],
                'category_name': category['name'],
                'category_budget_variability': category.get('budgetVariability', None),
                'exclude_from_budget': category.get('excludeFromBudget', False)
            })
    
    categories_df = pd.DataFrame(categories_data)
    
    # 2. Remove rows where excludeFromBudget is True
    categories_df = categories_df[categories_df['exclude_from_budget'] == False]
    
    # 3. Remove types that are not income or expense
    categories_df = categories_df[categories_df['category_group_type'].isin(['income', 'expense'])]
    
    
    # Part 2: Parse monthlyAmountsByCategory into budget amounts DataFrame
        
    budget_amounts_data = []
    
    # 1. Create a dataframe with category id, month, plannedCashFlowAmount, actualAmount and remainingAmount

    for category_budget in budget_data['budgetData']['monthlyAmountsByCategory']:

        category_id = category_budget['category']['id']
        
        # Process each month's data
        for monthly_amount in category_budget.get('monthlyAmounts', []):
            month = monthly_amount.get('month')
            
            budget_amounts_data.append({
                'category_id': category_id,
                'month': month,
                'planned_cash_flow_amount': monthly_amount.get('plannedCashFlowAmount', 0),
                'actual_amount': monthly_amount.get('actualAmount', 0),
                'remaining_amount': monthly_amount.get('remainingAmount', 0)
            })
    
    
    budget_amounts_df = pd.DataFrame(budget_amounts_data)
    
   
    # 3. Left join budget amounts with categories on category_id
    complete_budget_df= categories_df.merge(
        budget_amounts_df, 
        on='category_id', 
        how='left'
    )
    
    # 4. remove categories where both bugeted and actual amounts are zero or NaN
    complete_budget_df = complete_budget_df[~((complete_budget_df['planned_cash_flow_amount'].fillna(0) == 0) & (complete_budget_df['actual_amount'].fillna(0) == 0))]

        # Select only the required columns
    columns_to_keep = [
        'category_group_type', 
        'category_budget_variability', 
        'category_group_name', 
        'category_name',
        'month', 
        'planned_cash_flow_amount', 
        'actual_amount', 
        'remaining_amount'
    ]
    
    # Filter columns
    simplified_df = complete_budget_df[columns_to_keep].copy()

    simplified_df['remaining_amount_percent'] = simplified_df['remaining_amount'] / simplified_df['planned_cash_flow_amount'].replace([float('inf'), -float('inf')], 0).fillna(0)
    simplified_df['remaining_amount_percent'] = simplified_df['remaining_amount_percent'].round(4)

    simplified_df['sort_type'] = simplified_df['category_group_type'].map({
        'income': 0, 
        'expense': 1
    })
    
    # Sort by type first (income=0, expense=1), then by budget variability
    simplified_df = simplified_df.sort_values([
        'sort_type', 
        'category_budget_variability'
    ]).reset_index(drop=True)
    
    # Remove the temporary sorting column
    simplified_df = simplified_df.drop('sort_type', axis=1)

    simplified_json = simplified_df.to_json(orient='records')
    
    return simplified_json

def parse_transaction_data(transactions_data):
    """
    Parse transaction data into a structured DataFrame
    
    Creates DataFrame with columns:
    - transaction_id (from id)
    - amount
    - description (plaidName)
    - category_id 
    - category_name
    - merchant_id
    - merchant_name
    - createdAt
    - updatedAt
    - account_name

    Filters to keep only transactions from current and previous day
    """
    
    # Get the results from the nested structure
    transaction_results = transactions_data.get('allTransactions', {}).get('results', [])
    
    transactions_list = []
    
    for transaction in transaction_results:
        # Extract basic transaction info
        transaction_id = transaction.get('id')
        amount = transaction.get('amount', 0)
        description = transaction.get('plaidName', '')
        
        # Extract timestamps
        created_at = transaction.get('createdAt')
        updated_at = transaction.get('updatedAt')
        
        # Extract category info (safely handle missing category)
        category = transaction.get('category', {})
        category_id = category.get('id', None) if category else None
        category_name = category.get('name', None) if category else None
        
        # Extract merchant info (safely handle missing merchant)
        merchant = transaction.get('merchant', {})
        merchant_id = merchant.get('id', None) if merchant else None
        merchant_name = merchant.get('name', None) if merchant else None

        # Extract account info (safely handle missing account)
        account = transaction.get('account', {})
        account_name = account.get('displayName', None) if account else None

        # Add to list
        transactions_list.append({
            'transaction_id': transaction_id,
            'amount': amount,
            'description': description,
            'category_id': category_id,
            'category_name': category_name,
            'merchant_id': merchant_id,
            'merchant_name': merchant_name,
            'createdAt': created_at,
            'updatedAt': updated_at,
            'account_name': account_name
        })
    
    
    transactions_df = pd.DataFrame(transactions_list)

    exclude_account_strings = ['1375', '1305', '4585', '003', '3131', '4160', '4932', '9429', '5972', '2665']
    
    # Create mask to exclude accounts containing any of the specified strings
    mask = ~transactions_df['account_name'].str.contains('|'.join(exclude_account_strings), case=False, na=False)
    
    filtered_transactions_df = transactions_df[mask]

    transactions_json = filtered_transactions_df.to_json(orient='records')
    
    return transactions_json


# Add this at the end of data_parsing_functions.py to test if the file loads properly
if __name__ != "__main__":
    print("data_parsing_functions.py loaded successfully")
    print("parse_budget_data function available:", 'parse_budget_data' in globals())
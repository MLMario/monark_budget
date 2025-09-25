import json
from datetime import datetime,timedelta

def filter_overspent_categories(budget_json: str) -> str:

    budget_data = json.loads(budget_json)
    
    filtered_data = [
        budget_record for budget_record in budget_data if budget_record.get('remaining_amount', 0) < 0
    ]
    
    # Return as JSON string
    return json.dumps(filtered_data, default=str)

def task_mangement_functions():

    today = datetime.now()
    is_monday = today.weekday() == 0  # Monday is 0 and Sunday is 6

    yesterday = today - timedelta(days=1)  # Yesterday's date

    is_first_day_of_month = today.month != yesterday.month

    return "both_tasks" if (is_monday or is_first_day_of_month) else "daily_tasks"
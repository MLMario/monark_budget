import json
from datetime import datetime,timedelta
from groq import AsyncGroq
from config import Settings

def filter_overspent_categories(budget_json: str) -> str:

    budget_data = json.loads(budget_json)
    
    filtered_data = [
        budget_record for budget_record in budget_data if budget_record.get('remaining_amount', 0) < -5
    ]
    
    # Return empty object string if no overspent categories
    if not filtered_data:
        return ''
    
    # Return as JSON string
    return json.dumps(filtered_data, default=str)

def task_management():

    today = datetime.now()
    is_monday = today.weekday() == 0  # Monday is 0 and Sunday is 6

    yesterday = today - timedelta(days=1)  # Yesterday's date

    is_first_day_of_month = today.month != yesterday.month

    return "both_tasks" if (is_monday or is_first_day_of_month) else "daily_tasks"


def get_async_groq_client():
    return AsyncGroq(api_key=Settings.GROQ_API_KEY.get_secret_value())

async def call_llm(
        temperature = 0.7,
        prompt_obj = None,
          **kwargs):

    client = AsyncGroq(api_key=Settings.GROQ_API_KEY.get_secret_value())
    
    formatted_prompt = prompt_obj.prompt.format(**kwargs)
    
    completion = await client.chat.completions.create(
        model=Settings.GROQ_LLAMA_VERSATILE,

        messages=[
            {"role": "user", 
             "content": formatted_prompt}
             ],
        temperature = temperature,

        max_tokens = 300
    )
    
    return completion.choices[0].message.content
    



import json
from datetime import datetime,timedelta
from groq import AsyncGroq
from config import Settings
from services.api.app.domain.prompts import SYSTEM_PROMPT
import re

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

async def call_llm(
        temperature=0.7,
        system_prompt = SYSTEM_PROMPT.prompt,
        prompt_obj=None,
        max_tokens=4020,
        model = Settings.GROQ_LLAMA_VERSATILE,
        api_key = Settings.GROQ_API_KEY.get_secret_value(),
        **kwargs):

    client = AsyncGroq(
        api_key=Settings.GROQ_API_KEY.get_secret_value()
        )
    
    formatted_prompt = prompt_obj.prompt.format(**kwargs)
    
    completion = await client.chat.completions.create(
        model= model,

        messages=[{
                "role": "system",
                "content": system_prompt
        }
            ,{
                "role": "user",
                "content": formatted_prompt
            }
        ],
        temperature=temperature,

        max_tokens=max_tokens
    )
    
    return completion.choices[0].message.content
    

async def call_llm_reasoning(
        temperature=0.7,
        system_prompt = SYSTEM_PROMPT.prompt,
        prompt_obj=None,
        max_tokens= 4020 ,
        model = Settings.GROQ_QWEN_REASONING,
        api_key = Settings.GROQ_API_KEY.get_secret_value(),
        reasoning = 'high',
        **kwargs):

    client = AsyncGroq(
        api_key=Settings.GROQ_API_KEY.get_secret_value()
        )
    
    formatted_prompt = prompt_obj.prompt.format(**kwargs)
    
    completion = await client.chat.completions.create(
        model= model,

        messages=[{
                "role": "system",
                "content": system_prompt
        }
            ,{
                "role": "user",
                "content": formatted_prompt
            }
        ],
        temperature=temperature,

        max_tokens=max_tokens
    )
    
    return completion.choices[0].message.content

def clean_llm_output(raw_text: str) -> str:
    """
    Remove code fences, <think>...</think> blocks and simple 'json:' prefixes,
    then return the stripped remainder.
    """
    if not raw_text:
        return ""

    s = raw_text.strip()

    # remove triple-backtick code fences (```json\n...\n```)
    s = re.sub(r"```(?:\w+)?\n", "", s)
    s = s.replace("```", "")

    # remove <think> ... </think> blocks (case-insensitive, dot matches newline)
    s = re.sub(r"<think>.*?</think>", "", s, flags=re.I | re.S)

    # remove leading 'json:' or 'json =' etc.
    s = re.sub(r"^\s*json\s*[:=]\s*", "", s, flags=re.I)

    return s.strip()


def extract_json_text(cleaned_text: str):
    """
    Find the first JSON object or array in the cleaned text, return (json_text, parsed_obj).
    If parsing fails, parsed_obj is None and json_text contains the candidate substring.
    """
    # find first {...} or [...] block
    m = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", cleaned_text)
    if not m:
        return cleaned_text, None

    json_text = m.group(1).strip()

    return json_text

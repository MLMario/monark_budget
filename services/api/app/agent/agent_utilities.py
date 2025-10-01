import json
import re
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from html.parser import HTMLParser

from groq import AsyncGroq

from config import Settings
from services.api.app.domain.prompts import SYSTEM_PROMPT


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

def task_management(_state=None):

    today = datetime.now()
    is_monday = today.weekday() == 0  # Monday is 0 and Sunday is 6

    yesterday = today - timedelta(days=1)  # Yesterday's date

    is_first_day_of_month = today.month != yesterday.month

    # EOM takes precedence over EOW
    if is_first_day_of_month:
        return "eom_tasks"
    elif is_monday:
        return "eow_tasks"
    else:
        return "daily_tasks"

def is_first_day_of_month(state=None) -> bool:
    today = datetime.now()
    yesterday = today - timedelta(days=1)

    return today.month != yesterday.month
    yesterday = today - timedelta(days=1)

async def call_llm(
        temperature=0.7,
        system_prompt = SYSTEM_PROMPT.prompt,
        prompt_obj=None,
        max_tokens=4020,
        model = Settings.GROQ_LLAMA_VERSATILE,
        api_key = Settings.GROQ_API_KEY.get_secret_value(),
        response_format = 'text',
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

        max_tokens=max_tokens,
        response_format=  {'type': response_format}
    )
    
    return completion.choices[0].message.content
    

async def call_llm_reasoning(
        temperature=0.7,
        system_prompt = SYSTEM_PROMPT.prompt,
        prompt_obj=None,
        max_tokens= 4020 ,
        model = Settings.GROQ_QWEN_REASONING,
        api_key = Settings.GROQ_API_KEY.get_secret_value(),
        reasoning_effort = 'default',
        reasoning_format = 'hidden',
        response_format = 'text',
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
        temperature = temperature,
        reasoning_effort = reasoning_effort,
        max_tokens = max_tokens,
        reasoning_format = reasoning_format,
        response_format =  {'type': response_format}

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
        return cleaned_text

    json_text = m.group(1).strip()

    return json_text



class SendEmail:

    def __init__(self,EmailINfo):
        self.from_ = EmailINfo.from_
        self.to = EmailINfo.to
        self.subject = EmailINfo.subject
        self.body = EmailINfo.body
        self.ADDRESS = Settings.SMTP_USER
        self.PASSWORD = Settings.SMTP_PASSWORD.get_secret_value()
    
    async def send_email_async(self, is_html=False):

        msg = EmailMessage()
        msg['Subject'] = self.subject
        msg['From'] = self.from_ 
        msg['To'] = self.to

        if not is_html:
            msg.set_content(self.body)
        else:
            msg.add_alternative(self.body, subtype="html")

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()  # upgrade the connection to TLS
            server.ehlo()

            server.login(self.ADDRESS, self.PASSWORD)
            server.send_message(msg)

import re

class HTMLValidator(HTMLParser):
    def __init__(self):
        super().__init__()
        self.valid_html = True
        self.error_msg = ""
    
    def error(self, message):
        self.valid_html = False
        self.error_msg = message

def validate_html(text: str) -> str:
    """
    Check if the input text is valid HTML. If valid, return as-is.
    If invalid or plain text, return the original string.
    """
    if not text or not text.strip():
        return text, False
    
    # Quick check: if it doesn't contain HTML tags, return as-is
    if not re.search(r'<[^>]+>', text):
        return text, False
    
    validator = HTMLValidator()
    try:
        validator.feed(text)
        validator.close()
        # If we get here without exceptions and valid_html is True, it's valid HTML
        if validator.valid_html:
            return text, True
        else:
            
            return text, False
    except Exception as exc:
        
        return text, False
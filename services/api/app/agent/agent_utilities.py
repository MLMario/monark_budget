import json
import re
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from html.parser import HTMLParser
from typing import Optional

from groq import AsyncGroq

from config import Settings
from services.api.app.domain.prompts import SYSTEM_PROMPT


def filter_overspent_categories(budget_json: str) -> str:

    budget_data = json.loads(budget_json)

    filtered_data = [
        budget_record
        for budget_record in budget_data
        if budget_record.get("remaining_amount", 0) < -5
    ]

    # Return empty object string if no overspent categories
    if not filtered_data:
        return ""

    # Return as JSON string
    return json.dumps(filtered_data, default=str)


def parse_and_validate_transactions(
    transactions_json: Optional[str], no_data_message: str
) -> str:
    """
    Parse transaction JSON, validate through Pydantic models, and return formatted JSON string.

    This helper function encapsulates the repeated pattern of:
    1. Parsing JSON string
    2. Validating each transaction through TransactionRow Pydantic model
    3. Converting back to JSON format for LLM consumption

    Args:
        transactions_json: JSON string containing transaction data, or None
        no_data_message: Message to return if no data available

    Returns:
        JSON string of validated transactions or no_data_message if None/empty
    """
    from services.api.app.agent.state import TransactionRow

    if not transactions_json:
        return no_data_message

    transactions_list_data = json.loads(transactions_json)
    pydantic_transactions_model = [
        TransactionRow(**txn) for txn in transactions_list_data
    ]
    txn_dicts = [
        json.loads(txn.model_dump_json()) for txn in pydantic_transactions_model
    ]
    return json.dumps(txn_dicts, indent=2)


def task_management(_state=None) -> str:
    """
    Determine if period report tasks should run based on current day.

    Returns "both_tasks" if it's Monday or first day of month, otherwise "daily_tasks".
    """
    today = datetime.now()
    is_monday = today.weekday() == 0  # Monday is 0 and Sunday is 6

    yesterday = today - timedelta(days=1)  # Yesterday's date

    is_first_day_of_month = today.month != yesterday.month

    return "both_tasks" if (is_monday or is_first_day_of_month) else "daily_tasks"


async def call_llm(
    temperature: float = 0.7,
    system_prompt: str = SYSTEM_PROMPT.prompt,
    prompt_obj=None,
    max_tokens: int = 4020,
    model: str = Settings.GROQ_LLAMA_VERSATILE,
    api_key: str = Settings.GROQ_API_KEY.get_secret_value(),
    response_format: str = "text",
    **kwargs
) -> str:

    client = AsyncGroq(api_key=Settings.GROQ_API_KEY.get_secret_value())

    formatted_prompt = prompt_obj.prompt.format(**kwargs)

    completion = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": formatted_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": response_format},
    )

    return completion.choices[0].message.content


async def call_llm_reasoning(
    temperature: float = 0.7,
    system_prompt: str = SYSTEM_PROMPT.prompt,
    prompt_obj=None,
    max_tokens: int = 4020,
    model: str = Settings.GROQ_QWEN_REASONING,
    api_key: str = Settings.GROQ_API_KEY.get_secret_value(),
    reasoning_effort: str = "default",
    reasoning_format: str = "hidden",
    response_format: str = "text",
    **kwargs
) -> str:

    client = AsyncGroq(api_key=Settings.GROQ_API_KEY.get_secret_value())

    formatted_prompt = prompt_obj.prompt.format(**kwargs)

    completion = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": formatted_prompt},
        ],
        temperature=temperature,
        reasoning_effort=reasoning_effort,
        max_tokens=max_tokens,
        reasoning_format=reasoning_format,
        response_format={"type": response_format},
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

    def __init__(self, EmailINfo):
        self.from_ = EmailINfo.from_
        self.to = EmailINfo.to
        self.subject = EmailINfo.subject
        self.body = EmailINfo.body
        self.ADDRESS = Settings.SMTP_USER
        self.PASSWORD = Settings.SMTP_PASSWORD.get_secret_value()

    async def send_email_async(self, is_html: bool = False) -> None:

        msg = EmailMessage()
        msg["Subject"] = self.subject
        msg["From"] = self.from_
        msg["To"] = self.to

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


class HTMLValidator(HTMLParser):
    def __init__(self):
        super().__init__()
        self.valid_html: bool = True
        self.error_msg: str = ""

    def error(self, message: str) -> None:
        self.valid_html = False
        self.error_msg = message


def validate_html(text: str) -> tuple[str, bool]:
    """
    Check if the input text is valid HTML. If valid, return as-is.
    If invalid or plain text, return the original string.
    """
    if not text or not text.strip():
        return text, False

    # Quick check: if it doesn't contain HTML tags, return as-is
    if not re.search(r"<[^>]+>", text):
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
    except Exception:

        return text, False

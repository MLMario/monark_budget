import json
import re
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from html.parser import HTMLParser
from typing import Optional

from groq import AsyncGroq
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import Settings
from services.api.app.domain.prompts import SYSTEM_PROMPT
from services.api.app.exceptions import (
    EmailError,
    LLMError,
    LLMResponseError,
    LLMTimeoutError,
)


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


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((LLMError, LLMTimeoutError)),
    reraise=True,
)
async def call_llm(
    temperature: float = 0.7,
    system_prompt: str = SYSTEM_PROMPT.prompt,
    prompt_obj=None,
    max_tokens: int = 4020,
    model: str = Settings.GROQ_LLAMA_VERSATILE,
    api_key: str = Settings.GROQ_API_KEY.get_secret_value(),
    response_format: str = "text",
    timeout: int = 60,
    **kwargs
) -> str:
    """
    Call LLM API with retry logic and timeout handling.

    Args:
        temperature: Sampling temperature (0-1)
        system_prompt: System prompt for the LLM
        prompt_obj: Prompt object with .prompt attribute
        max_tokens: Maximum tokens to generate
        model: Model identifier
        api_key: API key for authentication
        response_format: Response format (text or json_object)
        timeout: Request timeout in seconds (default: 60)
        **kwargs: Additional parameters to format the prompt

    Returns:
        LLM response content

    Raises:
        LLMError: On LLM API failures
        LLMTimeoutError: On timeout
        LLMResponseError: On invalid response format
    """
    try:
        client = AsyncGroq(
            api_key=Settings.GROQ_API_KEY.get_secret_value(), timeout=timeout
        )

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

        if not completion.choices or not completion.choices[0].message.content:
            raise LLMResponseError("LLM returned empty response")

        return completion.choices[0].message.content

    except TimeoutError as exc:
        raise LLMTimeoutError(f"LLM request timed out after {timeout}s") from exc
    except (LLMError, LLMTimeoutError, LLMResponseError):
        # Re-raise our custom exceptions without wrapping
        raise
    except Exception as exc:
        # Catch all other exceptions and wrap as LLMError for retry logic
        raise LLMError(f"LLM API call failed: {exc}") from exc


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((LLMError, LLMTimeoutError)),
    reraise=True,
)
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
    timeout: int = 90,
    **kwargs
) -> str:
    """
    Call LLM reasoning API with retry logic and timeout handling.

    Args:
        temperature: Sampling temperature (0-1)
        system_prompt: System prompt for the LLM
        prompt_obj: Prompt object with .prompt attribute
        max_tokens: Maximum tokens to generate
        model: Model identifier
        api_key: API key for authentication
        reasoning_effort: Reasoning effort level
        reasoning_format: Reasoning format (hidden/visible)
        response_format: Response format (text or json_object)
        timeout: Request timeout in seconds (default: 90, higher for reasoning)
        **kwargs: Additional parameters to format the prompt

    Returns:
        LLM response content

    Raises:
        LLMError: On LLM API failures
        LLMTimeoutError: On timeout
        LLMResponseError: On invalid response format
    """
    try:
        client = AsyncGroq(
            api_key=Settings.GROQ_API_KEY.get_secret_value(), timeout=timeout
        )

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

        if not completion.choices or not completion.choices[0].message.content:
            raise LLMResponseError("LLM returned empty response")

        return completion.choices[0].message.content

    except TimeoutError as exc:
        raise LLMTimeoutError(f"LLM request timed out after {timeout}s") from exc
    except (LLMError, LLMTimeoutError, LLMResponseError):
        # Re-raise our custom exceptions without wrapping
        raise
    except Exception as exc:
        # Catch all other exceptions and wrap as LLMError for retry logic
        raise LLMError(f"LLM API call failed: {exc}") from exc


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

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(EmailError),
        reraise=True,
    )
    async def send_email_async(self, is_html: bool = False) -> None:
        """
        Send email with retry logic.

        Args:
            is_html: Whether the email body is HTML

        Raises:
            EmailError: On email sending failures after retries
        """
        try:
            msg = EmailMessage()
            msg["Subject"] = self.subject
            msg["From"] = self.from_
            msg["To"] = self.to

            if not is_html:
                msg.set_content(self.body)
            else:
                msg.add_alternative(self.body, subtype="html")

            with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
                server.ehlo()
                server.starttls()  # upgrade the connection to TLS
                server.ehlo()

                server.login(self.ADDRESS, self.PASSWORD)
                server.send_message(msg)

        except smtplib.SMTPException as exc:
            raise EmailError(f"SMTP error sending email: {exc}") from exc
        except TimeoutError as exc:
            raise EmailError(f"Email sending timed out: {exc}") from exc
        except Exception as exc:
            raise EmailError(f"Failed to send email: {exc}") from exc


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

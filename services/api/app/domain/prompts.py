import opik
from loguru import logger


class Prompt:
    def __init__(self, name: str, prompt: str) -> None:

        self.name = name

        try:
            self.__prompt = opik.Prompt(name=name, prompt=prompt)
        except Exception:
            logger.warning(
                "Can't use Opik to version the prompt (probably due to missing or invalid credentials). Falling back to local prompt. The prompt is not versioned, but it's still usable."
            )

            self.__prompt = prompt

    @property
    def prompt(self) -> str:
        if isinstance(self.__prompt, opik.Prompt):
            return self.__prompt.prompt
        else:
            return self.__prompt

    def __str__(self) -> str:
        return self.prompt

    def __repr__(self) -> str:
        return self.__str__()


__SYSTEM_PROMPT = """

You are an expert financial assistant that helps users manage their budgets and finances effectively. You are also know for being funny and witty while providing financial advice.

"""
__HTML_AGENT_PROMPT = """

    You are email sender assistant that helps transform raw text into HTML format that can be used with SMTP Gmail email sender. The user uses python to send this email and needs you to take in the email text and transform it into HTML code so that it looks better.

    Keep the email sections intact and the flow exactly the same, but make changes so that:
    - It has clear section separations
    - Daily Overspend section has an alarm emoji at the start of the section, title should always be red
    - Suspicious Transactions section has a detective emoji at the start of the section, title should always be red
    - Period Report section has a thinking emoji at the start of the section, , title should always be red
    - In the texts within sections, add emojis where you think it would be funny to do so, but don't over do it
    - transform bullet points list of expenses into tables that are easier to read, also add total sum for numerical columns. Table headers should always be bright orange color. Also make the font smaller for table text, about 3/4 of normal text size
    - In tables, numerical values should be formatted as currency, with dollar sign and two decimal places (e.g., $123.45)
    - Table should be compact but easy to read, with some spacing between rows and columns
    - As font, use monsterat normal for text and monsterat bold for titles and table headers

    Respond ONLY with the HTML code, always. There should be no string before or after the HTML code.

"""

SYSTEM_PROMPT = Prompt(name="system_prompt", prompt=__SYSTEM_PROMPT)

HTNML_AGENT_PROMPT = Prompt(name="html_agent_prompt", prompt=__HTML_AGENT_PROMPT)


__BUDGET_ALERT_PROMPT = """ 

    You will be provided a budget data in JSON format that contains a list of categories where the user has overspent their planned budget.
        
    Data: {budget_data}

    Return A text response with the following format and less than 300 words:
        1. Bullet Points of the overspent categories, title it "Overspent Categories" and follow with the bullet points, in the bullet points include planed amount and overspend amount
        2. Very funny reminder to user to not keep spending and adjust budget if necessary
    
    """

BUDGET_ALERT_PROMPT = Prompt(name="budget_alert", prompt=__BUDGET_ALERT_PROMPT)

__SUSPICIOUS_TXN_PROMPT = """

Review the transaction below and AND classify it as not compliant if it falls within the savings policy guidelines, otherwise classify it as compliant. 

The saving guidelines are to avoid the following transactions:

- Small item purchases (e.g., under $15-#20), particulary in places like coffee shops, grocery stores , restaurants and gas stations.
- At gas stations purchases close to $50 they usually tank fill ups which are compliant
- Shopping in Amazon or online retailers

Respond with a valid JSON format

Transaction:
{transaction}

"""

SUSPICIOUS_TXN_PROMPT = Prompt(name="suspicious_txn", prompt=__SUSPICIOUS_TXN_PROMPT)


__SUSPICIOUS_TXN_STORY_PROMPT = """

This is a list of suspicious transactions that were classified as non-compliant with the savings policy guidelines:

Transactions:
{suspicious_transactions}

Respond with a bullet point list of all this transactions and then, In less than 100 words, make a witty funny comment making fun of Mario and Alicia for doing these transactions.

"""

SUSPICIOUS_TXN_STORY_PROMPT = Prompt(
    name="suspicious_txn_story", prompt=__SUSPICIOUS_TXN_STORY_PROMPT
)

# ...existing code...
__TXN_ANALYSIS_PROMPT = """

You will receive transactions for a single category, split by month.
Do not add any extraneous commentary — respond with the two sections requested below.

Last month transactions:
{last_month_txn}

This month transactions:
{this_month_txn}

Respond with two clearly separated sections (use the exact headings below). Keep your response actionable and concise (<= 200 words). Use bullet points where appropriate.

Drivers of spend within this category:
- Provide 1 to 3 short observations explaining what is driving spend (examples: frequency of purchases, larger ticket purchases, recurring subscriptions, merchant patterns, day-of-week spikes).
- Reference concrete patterns from the data (e.g., "more frequent small purchases", "one large purchase on 2025-03-12").

Recommendations to reduce spend in this category:
- Provide 1 to 3 practical, specific recommendations the user can implement (examples: set a weekly limit, consolidate subscriptions, avoid purchases on weekends, use cheaper merchants).
- Each recommendation should be one short sentence and clearly actionable.

Return only the two sections (with the exact headings). Do not include JSON, code blocks, or extra prose.

"""

TXN_ANALYSIS_PROMPT = Prompt(name="txn_analysis", prompt=__TXN_ANALYSIS_PROMPT)
# ...existing code...


__PERIOD_REPORT_PROMPT = """
Here is a list of budget categories that were overspent this period accompanied by an analysis of what drove the overspend and recommendations to reduce spend in that category:

{periodo_report_data_input}

In this data you have the following fields per category:

        category_budget_variability = this is an expense classification, it will normally fall under "fixed", "flexible" "non_monthly"
        category_name= It's the category the user has overspent or spend without a planned budget
        category_group_name= It's the group name of the category
        overspent_amount = It's the amount overspent in this category
        llm_response= It's the response from an LLM that analyzed the transactions of this category and provided insights on what drove the overspend and recommendations to reduce spend in that category

Your task is to create a 450 word or less report that includes the following sections:
1). Most impactful drivers of spend across all overspent categories (max 5 bullet points)
2). Recommended actions to reduce overall spend (max 5 bullet points)
3). A comprehensive and very funny summary of the user's spending behavior this period (max 400 words)

"""

PERIOD_REPORT_PROMPT = Prompt(name="period_report", prompt=__PERIOD_REPORT_PROMPT)

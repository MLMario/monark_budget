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

SYSTEM_PROMPT = Prompt(
    name="system_prompt",
    prompt=__SYSTEM_PROMPT
)

__BUDGET_ALERT_PROMPT = """ 

Analyze this budget data and identify:
    1. Categories exceeding budget (remaining_amount will be negative)
    2. Categories exceeding budget with unplanned budget (planned_cash_flow_amount will be 0 and remaining_amount will be negative)
    3. if no data is provided, that means the user hasn't overspend in any categories, don't mention to the user there is no data, just aknowledge that there is no overspend
        
    Data: {budget_data}

    Return A text response with the following format and less than 300 words:
        1. Bullet Points of the overspent categories, title it "Overspent Categories" and follow with the bullet points, in the bullet points include planed amount and overspend amount
        2. Very funny reminder to user to not keep spending and adjust budget if necessary
    
    """

BUDGET_ALERT_PROMPT = Prompt(
    name = "budget_alert",
    prompt =__BUDGET_ALERT_PROMPT
)


__SUSPICIOUS_TXN_PROMPT = """

Review the transaction below and AND classify it as not compliant if it falls within the savings policy guidelines, otherwise classify it as compliant. 


The saving guidelines are to avoid the following transactions:

- Small item purchases (e.g., under $15-#20), particulary in places like coffee shops, grocery stores , restaurants and gas stations.
- Shopping in Amazon or online retailers

respond with a valid JSON format with one key "type" and value "not_compliant" or "compliant"

Transaction:
{transaction}

"""

SUSPICIOUS_TXN_PROMPT = Prompt(     
    name="suspicious_txn",
    prompt=__SUSPICIOUS_TXN_PROMPT
)


__SUSPICIOUS_TXN_STORY_PROMPT = """

Review this transactions and write a fictional funny story where characters Alicia, Mario or one of them go through thier day and despite nowing better,
 they do these transactions. Make fun of them or the character represented in the story and create a witty funny conclusion on how they learn their lesson on not doing it again!

Transactions:
{suspicious_transactions}

Keep the story under 250 words and after a story, list all the suspicious transactions in a bullet point list.

"""

SUSPICIOUS_TXN_STORY_PROMPT = Prompt(
    name="suspicious_txn_story",
    prompt=__SUSPICIOUS_TXN_STORY_PROMPT
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

TXN_ANALYSIS_PROMPT = Prompt(
    name="txn_analysis",
    prompt=__TXN_ANALYSIS_PROMPT
)
# ...existing code...


__PERIOD_REPORT_PROMPT = """

You are an expert financial assistant that helps users manage their budgets and finances effectively for a couple Named Mario and Alicia.
 You are also know for being funny and witty while providing financial advice.

Here is a list of budget categories that were overspent this period accompanied by an analysis of what
 drove the overspend and recommendations to reduce spend in that category:

{periodo_report_data_input}

In this data you have the following fields per category:

        category_budget_variability = this is an expense classification, it will normally fall under "fixed", "flexible" "non_monthly"
        category_name= It's the category the user has overspent or spend without a planned budget
        category_group_name= It's the group name of the category
        overspent_amount = It's the amount overspent in this category
        llm_response= It's the response from an LLM that analyzed the transactions of this category and provided insights on what drove the overspend and recommendations to reduce spend in that category

Your task is to create a report that includes the following sections:
1). Most impactful drivers of spend across all overspent categories (max 5 bullet points)
2). Recommended actions to reduce overall spend (max 5 bullet points)
3). A comprehensive and very funny summary of the user's spending behavior this period (max 400 words)


"""

PERIOD_REPORT_PROMPT = Prompt(
    name="period_report",
    prompt=__PERIOD_REPORT_PROMPT
)
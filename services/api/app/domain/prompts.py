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
    

__BUDGET_ALERT_PROMPT = """ 

Analyze this budget data and identify:
    1. Categories exceeding budget (remaining_amount will be negative)
    2. Categories exceeding budget with unplanned budget (planned_cash_flow_amount will be 0 and remaining_amount will be negative)
    3. if no data is provided, that means the user hasn't overspend in any categories, don't mention to the user there is no data, just aknowledge that there is no overspend
        
    Data: {budget_data}

    Return A text response with the following format and less than 200 words:
        1. Bullet Points of the overspent categories, title it "Overspent Categories" and follow with the bullet points, in the bullet points include planed amount and overspend amount
        2. Very funny reminder to user to not keep spending and adjust budget if necessary
    
    """

BUDGET_ALERT_PROMPT = Prompt(
    name = "budget_alert",
    prompt =__BUDGET_ALERT_PROMPT
)


__SUSPICIOUS_TXN_PROMPT = """

Review the transaction below and AND classify it as suspicious or not suspicious,are transaction that fall outside the spending policy guidelines, the guidelines are the following:

- Small item purchases (e.g., under $15-#20), particulary in places like coffee shops, grocery stores , restaurants and gas stations.
- Shopping in Amazon or online retailers

respond only with valid JSON:
{
  "type": "suspicious" | "not_suspicious"
}

Transaction:
{{transaction}}

"""

SUSPICIOUS_TXN_PROMPT = Prompt(     
    name="suspicious_txn",
    prompt=__SUSPICIOUS_TXN_PROMPT
)


__SUSPICIOUS_TXN_STORY_PROMPT = """

Review this transactions and write a fictional funny story where characters Alicia, Mario or one of them go through thier day and despite nowing better,
 they do these transactions. Make fun of them or the character represented in the story and create a witty funny conclusion on how they learn their lesson on not doing it again!

Transactions:
{{suspicious_transactions}}

Keep the story under 250 words and after a story, list all the suspicious transactions in a bullet point list.




"""

SUSPICIOUS_TXN_STORY_PROMPT = Prompt(
    name="suspicious_txn_story",
    prompt=__SUSPICIOUS_TXN_STORY_PROMPT
)
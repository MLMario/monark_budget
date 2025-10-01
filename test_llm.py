"""
Simple test file to test the call_llm function with BUDGET_ALERT_PROMPT
"""

import sys
import os
import asyncio
from groq import AsyncGroq
from config import Settings
import logging


# Add the services/api/app path to Python path for imports

logger = logging.getLogger(__name__)

sys.path.append(os.path.join(os.path.dirname(__file__), 'services', 'api'))

from app.agent.agent_utilities import call_llm_reasoning

async def test_llm():


    formatted_prompt = """
Here is a list of budget categories that were overspent this period accompanied by an analysis of what drove the overspend and recommendations to reduce spend in that category:

[
  {
    "category_budget_variability": "fixed",
    "category_name": "Garbage",
    "category_group_name": "Bills & Utilities",
    "overspent_amount": 97.0,
    "llm_response": ""
  },
  {
    "category_budget_variability": "fixed",
    "category_name": "Internet & Cable",
    "category_group_name": "Bills & Utilities",
    "overspent_amount": 99.0,
    "llm_response": ""
  },
  {
    "category_budget_variability": "fixed",
    "category_name": "Child Care",
    "category_group_name": "Children",
    "overspent_amount": 424.0,
    "llm_response": ""
  },
  {
    "category_budget_variability": "fixed",
    "category_name": "Child Activities",
    "category_group_name": "Children",
    "overspent_amount": 161.0,
    "llm_response": "Drivers of spend within this category:\n- One large purchase of $160.68 on 2025-09-25 at Scouting Registration.\n- No recurring or small purchases observed.\n- The transaction took place on a Thursday, aligning with typical registration deadlines.\n\nRecommendations to reduce spend in this category:\n- Set a monthly budget for child activities to cap spending.\n- Look for cheaper or free scouting alternatives or community programs.\n- Ask about payment plans or early registration discounts to spread the cost."
  },
  {
    "category_budget_variability": "fixed",
    "category_name": "Fitness",
    "category_group_name": "Health & Wellness",
    "overspent_amount": 469.0,
    "llm_response": "Drivers of spend within this category:\n- Two large one\u2011time payments: \u00a3297 at Goodlife and \u00a3175 at Copa Soccer Training.\n- Both purchases occurred on Tuesdays, suggesting a potential recurring billing schedule.\n- No frequent small purchases; spend is driven by a few high\u2011ticket items.\n\nRecommendations to reduce spend in this category:\n- Negotiate a lower rate with Goodlife or find a cheaper gym membership.\n- Pause or reduce the frequency of the soccer training sessions if not essential.\n- Set a monthly fitness budget and log all expenses in a finance app."
  },
  {
    "category_budget_variability": "fixed",
    "category_name": "Insurance",
    "category_group_name": "Financial",
    "overspent_amount": 24.0,
    "llm_response": "Drivers of spend within this category:\n- One $24.0 insurance payment on 2025\u201109\u201105.\n- Likely a monthly premium for an individual plan.\n\nRecommendations to reduce spend in this category:\n- Review the plan to confirm you still need all covered items.\n- Shop other insurers for a lower monthly rate.\n- Bundle this insurance with other policies for a discount."
  },
  {
    "category_budget_variability": "flexible",
    "category_name": "Gas",
    "category_group_name": "Auto & Transport",
    "overspent_amount": 72.0,
    "llm_response": ""
  },
  {
    "category_budget_variability": "flexible",
    "category_name": "Groceries",
    "category_group_name": "Food & Dining",
    "overspent_amount": 486.0,
    "llm_response": ""
  },
  {
    "category_budget_variability": "flexible",
    "category_name": "Restaurants & Bars",
    "category_group_name": "Food & Dining",
    "overspent_amount": 37.0,
    "llm_response": ""
  },
  {
    "category_budget_variability": "flexible",
    "category_name": "Personal",
    "category_group_name": "Travel & Lifestyle",
    "overspent_amount": 267.0,
    "llm_response": ""
  },
  {
    "category_budget_variability": "flexible",
    "category_name": "Pets",
    "category_group_name": "Travel & Lifestyle",
    "overspent_amount": 66.0,
    "llm_response": "Drivers of spend within this category:\n- Two small, frequent purchases at PetSmart ($23.0 and $6.22) in a two\u2011day span.\n- One larger, likely recurring expense at Embrace Pet Insurance ($36.61) in mid\u2011September.\n\nRecommendations to reduce spend in this category:\n- Set a weekly spending limit for PetSmart to curb impulse buys.\n- Compare pet\u2011insurance quotes and negotiate a lower premium or switch to a cheaper provider.\n- Use coupons or bulk\u2011buy options at PetSmart to lower unit costs."
  },
  {
    "category_budget_variability": "flexible",
    "category_name": "Shopping",
    "category_group_name": "Shopping",
    "overspent_amount": 229.0,
    "llm_response": ""
  },
  {
    "category_budget_variability": "flexible",
    "category_name": "Business",
    "category_group_name": "Education",
    "overspent_amount": 46.0,
    "llm_response": ""
  },
  {
    "category_budget_variability": "flexible",
    "category_name": "Miscellaneous",
    "category_group_name": "Education",
    "overspent_amount": 127.0,
    "llm_response": "Drivers of spend within this category:\n- Three purchases in September: $76.80 at Reclaim Ai on 2025\u201109\u201117, $39.98 at Xtreme on 2025\u201109\u201130, and $10.00 at Github on 2025\u201109\u201122.\n- Spending is spread over a 13\u2011day span, indicating irregular, not daily or weekly, patterns.\n- The category includes diverse merchants, suggesting no single recurring subscription is driving the spend.\n\nRecommendations to reduce spend in this category:\n- Set a monthly miscellaneous budget of $50 and track each purchase against it.\n- Evaluate the necessity of each service; consider canceling or replacing the Reclaim Ai subscription if a cheaper alternative exists.\n- Review small purchases (e.g., Github) and limit them to essential or free tools when possible."
  },
  {
    "category_budget_variability": "non_monthly",
    "category_name": "Auto Maintenance",
    "category_group_name": "Auto & Transport",
    "overspent_amount": 480.0,
    "llm_response": "Drivers of spend within this category:\n- One large purchase of $498.75 at Toyota Walnut Creek on 2025\u201109\u201130.\n- Two smaller recurring purchases: $17.47 at Shell on 2025\u201109\u201129 and $14.00 at Bear Car Wash on 2025\u201109\u201119.\n- The bulk of the spend is driven by the single major maintenance fee; routine fueling and washing add minor amounts.\n\nRecommendations to reduce spend in this category:\n- Set a weekly budget limit of $50 for auto maintenance and stick to it.\n- Get quotes from multiple repair shops before booking a big service.\n- Use a car wash subscription or wash your car at home to cut the $14 fee."
  },
  {
    "category_budget_variability": "non_monthly",
    "category_name": "Travel & Vacation",
    "category_group_name": "Travel & Lifestyle",
    "overspent_amount": 272.0,
    "llm_response": "Drivers of spend within this category:\n- Two large purchases: \u2013$100.00 on 2025\u201109\u201102 and \u2013$172.50 on 2025\u201109\u201123.\n- No frequent small purchases; spending concentrated in a single trip.\n- Merchant pattern shows one travel booking platform (Airbnb) and a generic flight provider.\n\nRecommendations to reduce spend in this category:\n- Set a monthly travel budget and track each trip against it.  \n- Book flights and accommodation together via package deals to lock in lower rates.  \n- Use travel reward points or discount sites to offset costs before checkout."
  },
  {
    "category_budget_variability": "non_monthly",
    "category_name": "Electronics",
    "category_group_name": "Shopping",
    "overspent_amount": 105.0,
    "llm_response": "Drivers of spend within this category:\n- Two Apple purchases of $9.99 on 2025-09-05 and one on 2025-09-01, all on Fridays, suggest recurring small subscriptions.\n- A larger Apple purchase of 
$39.99 on 2025-09-05 on the same day hints at a one\u2011time or upgrade.\n- Microsoft\u2019s $11.99 14\u2011day trial on 2025-09-22 is a single Friday purchase, likely a trial subscription.\n\nRecommendations to reduce spend in this category:\n- Review and cancel any unused Apple 9.99 subscriptions via the Apple ID settings.\n- Set a weekly electronics budget of $50 and alert yourself when a purchase approaches that limit.\n- Shop for similar electronics at discount retailers or wait for sales to reduce cost."
  },
  {
    "category_budget_variability": "non_monthly",
    "category_name": "Medical",
    "category_group_name": "Health & Wellness",
    "overspent_amount": 768.0,
    "llm_response": "Drivers of spend within this category:\n- One large purchase of $600 at Pleasanthill dominates the month.\n- Frequent small pharmacy purchases at CVS ($42.89) and Walgreens ($8.53) show a pattern of regular medication refills.\n- Medical service payments to BayAreaSurgicalSpeciali ($20.0), John Muir Health ($50.0), and Laboratory Corporation ($15.3) indicate multiple visits or tests.\n\nRecommendations to reduce spend in this category:\n- Set a weekly pharmacy budget and track each refill to stay within it.\n- Review and cancel any unnecessary medical service subscriptions or repeat tests.\n- Compare prices or ask for generic options at each provider to lower costs."
  },
  {
    "category_budget_variability": "non_monthly",
    "category_name": "Financial Fees",
    "category_group_name": "Financial",
    "overspent_amount": 39.0,
    "llm_response": ""
  }
]

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

    client = AsyncGroq(
        api_key=Settings.GROQ_API_KEY.get_secret_value()
        )
        
    completion = await client.chat.completions.create(
        model= Settings.GROQ_OPENAI_120B_MODE,

        messages=[{
                "role": "system",
                "content": "You are an expert financial assistant that helps users manage their budgets and finances effectively. You are also know for being funny and witty while providing financial advice."
        }
            ,{
                "role": "user",
                "content": formatted_prompt
            }
        ],
        temperature = 0.8,
        reasoning_effort = 'high',
        max_tokens = 8020,
        reasoning_format = 'hidden',
        response_format =  {'type': 'text'}

    )

    print(completion)


    return completion.choices[0].message.content


if __name__ == "__main__":
    asyncio.run(test_llm())


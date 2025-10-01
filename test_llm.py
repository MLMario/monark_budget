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


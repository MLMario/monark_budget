"""
Simple test file to test the call_llm function with BUDGET_ALERT_PROMPT
"""

import asyncio
import json
import os
import sys

# Add the services/api/app path to Python path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'services', 'api'))

from app.agent.agent_utilities import call_llm, filter_overspent_categories
from app.domain.prompts import BUDGET_ALERT_PROMPT
from pipelines.mongo_client import AsyncMongoDBClient


async def test_llm():
    """Test the call_llm function with BUDGET_ALERT_PROMPT"""
    
    print("Testing call_llm function with BUDGET_ALERT_PROMPT...")
    print("=" * 50)
    
    try:
        # Sample budget data for testing
        # Create MongoDB Client to Import Data
        mongo_client = AsyncMongoDBClient() 

        budget_json = await mongo_client.import_budget_data(filter_query={'category_group_type': 'expense'})
        
        overspent_json = filter_overspent_categories(budget_json)
        
        for record in json.loads(overspent_json):
            print(record.get('category_name'), record.get('remaining_amount'))

        print("Formatted Prompt:")
        print("-" * 30)
        print(BUDGET_ALERT_PROMPT.prompt[:500] + "..." if len(BUDGET_ALERT_PROMPT.prompt) > 500 else BUDGET_ALERT_PROMPT.prompt)
        print("-" * 30)
        print("\nSending request to LLM...")

        response = await call_llm(prompt_obj = BUDGET_ALERT_PROMPT, budget_data = overspent_json, temperature=0.7,max_tokens=600)

        print(f"\nLLM Response:")
        print("=" * 40)
        print(response)

        print("=" * 40)
        print("\n✓ BUDGET_ALERT_PROMPT test: PASSED")
        
    except Exception as e:
        print(f"\n✗ BUDGET_ALERT_PROMPT test: FAILED")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_llm())


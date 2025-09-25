"""
Simple test file to test the call_llm function with BUDGET_ALERT_PROMPT
"""

import sys
import os
import asyncio
import json

# Add the services/api/app path to Python path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'services', 'api', 'app'))

from agent.agent_utilities import call_llm
from domain.prompts import BUDGET_ALERT_PROMPT

async def test_llm():
    """Test the call_llm function with BUDGET_ALERT_PROMPT"""
    
    print("Testing call_llm function with BUDGET_ALERT_PROMPT...")
    print("=" * 50)
    
    try:
        # Sample budget data for testing
        sample_budget_data = [
            {
                "category_name": "Groceries",
                "category_group_name": "Food",
                "remaining_amount": -150.00,
                "planned_cash_flow_amount": 400.00,
                "actual_amount": 550.00
            },
            {
                "category_name": "Dining Out", 
                "category_group_name": "Food",
                "remaining_amount": -75.50,
                "planned_cash_flow_amount": 200.00,
                "actual_amount": 275.50
            },
            {
                "category_name": "Emergency Fund",
                "category_group_name": "Savings",
                "remaining_amount": -300.00,
                "planned_cash_flow_amount": 0.00,
                "actual_amount": 300.00
            }
        ]
        
        # Format the prompt with sample data
        formatted_prompt = BUDGET_ALERT_PROMPT.prompt.format(
            budget_data=json.dumps(sample_budget_data, indent=2)
        )
        
        print("Formatted Prompt:")
        print("-" * 30)
        print(formatted_prompt[:500] + "..." if len(formatted_prompt) > 500 else formatted_prompt)
        print("-" * 30)
        print("\nSending request to LLM...")

        response = await call_llm(prompt_obj = BUDGET_ALERT_PROMPT, budget_data = "No Data, User hasn't overspent", temperature=0.8)

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

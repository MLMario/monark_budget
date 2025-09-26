"""
Testing file for import_data_node functionality

This test validates:
1. Data model validations (BudgetAgentState)
2. Budget data retrieval from MongoDB
3. Overspend filtering functionality
4. Previous day transaction filtering

Run this file to ensure the import_data_node works correctly.
"""

import sys
import os
from datetime import date, datetime, timedelta
import json
import asyncio

# Add the services/api/app path to Python path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'services', 'api', 'app'))

from agent.state import (  # type: ignore[import-not-found]
    BudgetAgentState,
    RunMeta,
    BudgetData,
    BudgetRow,
    TransactionRow,
    OverspendBudgetData,
    ProcessFlag,
    DailyAlertSuspiciousTransaction,
    DailyAlertOverspend,
    ReportCategory,
    PeriodReport,
)
from agent.nodes import (  # type: ignore[import-not-found]
    import_data_node,
    coordinator_node,
    daily_suspicious_transaction_alert_node,
)
from agent import nodes as agent_nodes  # type: ignore[import-not-found]
from agent.agent_utilities import filter_overspent_categories  # type: ignore[import-not-found]

async def test_import_data_node():
    """Test the import_data_node function comprehensively"""
    
    print("=" * 60)
    print("TESTING IMPORT_DATA_NODE FUNCTIONALITY")
    print("=" * 60)
    
    # Create a test state with required RunMeta
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    run_meta = RunMeta(
        run_id=f"test_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        today=today,
        tz="UTC"
    )
    
    # Initialize BudgetAgentState with required fields
    try:
        state = BudgetAgentState(
            run_meta=run_meta,
            overspend_budget_data=None,
            daily_overspend_alert=DailyAlertOverspend(),
            daily_suspicious_transactions=[],
            daily_alert_suspicious_transaction=DailyAlertSuspiciousTransaction(),
            report_category=ReportCategory(
                category_name="test",
                category_group_name="test",
                overspent_amount=0.0,
            ),
            period_report=PeriodReport(period="test", categories_in_report=[]),
            process_flag=ProcessFlag(),
            email_info=None,
            task_info="daily_tasks",
        )
        print("✓ BudgetAgentState model validation: PASSED")
        print(f"  - Run ID: {state.run_meta.run_id}")
        print(f"  - Today: {state.run_meta.today}")
        print(f"  - Timezone: {state.run_meta.tz}")
        
    except Exception as e:
        print("✗ BudgetAgentState model validation: FAILED")
        print(f"  Error: {e}")
        return False
    
    print("\n" + "-" * 40)
    print("RUNNING IMPORT_DATA_NODE")
    print("-" * 40)
    
    try:
        # Run the import_data_node function
        updated_state = await import_data_node(state)
        print("✓ import_data_node execution: PASSED")
        
        # Test 1: Budget data retrieval
        print("\n1. BUDGET DATA VALIDATION:")
        if updated_state.current_month_budget is not None:
            # Parse JSON string back to object for validation
            budget_data = BudgetData.model_validate_json(updated_state.current_month_budget)
            budget_count = len(budget_data.current_month_budget)
            print(f"✓ Budget data retrieved: {budget_count} budget categories")
            
            # Validate that all categories are expenses
            expense_count = sum(1 for row in budget_data.current_month_budget if row.category_group_type == 'expense')
            if expense_count == budget_count:
                print(f"✓ All categories are expenses: {expense_count}/{budget_count}")
            else:
                print(f"✗ Mixed category types found: {expense_count} expenses out of {budget_count} total")
            
            # Show first few budget items for validation
            if budget_count > 0:
                print("  Sample budget categories:")
                for i, budget_row in enumerate(budget_data.current_month_budget[:3]):
                    print(f"    {i+1}. {budget_row.category_name} ({budget_row.category_group_type}) - Remaining: ${budget_row.remaining_amount:.2f}")
        else:
            print("✗ Budget data not retrieved")
            
        # Test 2: Overspend filtering validation
        print("\n2. OVERSPEND FILTERING VALIDATION:")
        if updated_state.overspend_budget_data is not None:
            # Parse JSON string back to object for validation
            overspend_data = OverspendBudgetData.model_validate_json(updated_state.overspend_budget_data)
            overspend_count = len(overspend_data.overspend_categories)
            print(f"✓ Overspent categories found: {overspend_count}")
            
            if overspend_count > 0:
                print("  Overspent categories:")
                for i, overspend_cat in enumerate(overspend_data.overspend_categories[:5]):
                    print(f"    {i+1}. {overspend_cat.category_name} - Overspent: ${abs(overspend_cat.remaining_amount):.2f}")
            else:
                print("  No overspent categories found (this is good!)")
        else:
            print("✗ Overspend data not available")
            
        # Test 3: Previous day transaction filtering
        print("\n3. PREVIOUS DAY TRANSACTION FILTERING:")
        last_day_txn_count = len(updated_state.last_day_txn)
        print(f"✓ Previous day transactions: {last_day_txn_count}")
        
        if last_day_txn_count > 0:
            print(f"  Transactions from {yesterday}:")
            for i, txn_json in enumerate(updated_state.last_day_txn[:3]):
                # Parse JSON string back to object for display
                txn = TransactionRow.model_validate_json(txn_json)
                print(f"    {i+1}. {txn.merchant_name} - ${txn.amount:.2f} ({txn.category_name})")
        else:
            print(f"  No transactions found for {yesterday}")
            
        # Test 4: Data model integrity
        print("\n4. DATA MODEL INTEGRITY:")
        
        # Check required fields are populated
        checks = [
            ("run_meta", updated_state.run_meta is not None),
            ("overspend_budget_data", updated_state.overspend_budget_data is not None),
            ("task_info", updated_state.task_info in {"daily_tasks", "both_tasks"}),
            ("process_flag", updated_state.process_flag is not None),
        ]
        
        all_passed = True
        for field_name, check_result in checks:
            status = "✓" if check_result else "✗"
            print(f"  {status} {field_name}: {'VALID' if check_result else 'INVALID'}")
            if not check_result:
                all_passed = False
                
        print("\n5. SUMMARY:")
        if all_passed:
            print("✓ ALL TESTS PASSED - import_data_node is working correctly!")
        else:
            print("✗ SOME TESTS FAILED - check the issues above")
            
        return all_passed
        
    except Exception as e:
        print("✗ import_data_node execution: FAILED")
        print(f"  Error: {e}")
        print(f"  Error type: {type(e).__name__}")
        import traceback
        print("  Full traceback:")
        traceback.print_exc()
        return False

def test_filter_overspent_categories():
    """Test the filter_overspent_categories utility function"""
    
    print("\n" + "=" * 60)
    print("TESTING FILTER_OVERSPENT_CATEGORIES UTILITY")
    print("=" * 60)
    
    # Create test budget data with some overspent and some non-overspent categories
    test_budget_data = [
        {
            "category_name": "Groceries",
            "remaining_amount": -50.0,  # Overspent
            "actual_amount": 350.0,
            "planned_cash_flow_amount": 300.0
        },
        {
            "category_name": "Gas",
            "remaining_amount": 25.0,   # Not overspent
            "actual_amount": 75.0,
            "planned_cash_flow_amount": 100.0
        },
        {
            "category_name": "Dining Out",
            "remaining_amount": -15.0,  # Overspent
            "actual_amount": 115.0,
            "planned_cash_flow_amount": 100.0
        },
        {
            "category_name": "Entertainment",
            "remaining_amount": 10.0,   # Not overspent
            "actual_amount": 40.0,
            "planned_cash_flow_amount": 50.0
        }
    ]
    
    # Convert to JSON string
    budget_json = json.dumps(test_budget_data)
    
    print(f"Original budget categories: {len(test_budget_data)}")
    print("Categories with negative remaining_amount (overspent):")
    for cat in test_budget_data:
        if cat["remaining_amount"] < 0:
            print(f"  - {cat['category_name']}: ${cat['remaining_amount']:.2f}")
    
    # Test the filter function
    try:
        filtered_json = filter_overspent_categories(budget_json)
        filtered_data = json.loads(filtered_json)
        
        print(f"\nFiltered budget categories: {len(filtered_data)}")
        print("Remaining categories (overspent only):")
        for cat in filtered_data:
            print(f"  - {cat['category_name']}: ${cat['remaining_amount']:.2f}")
            
        # Validate that only overspent categories remain
        overspent_only = all(cat["remaining_amount"] < 0 for cat in filtered_data)
        if overspent_only:
            print("\n✓ filter_overspent_categories: PASSED")
            print("  All filtered categories have negative remaining_amount")
        else:
            print("\n✗ filter_overspent_categories: FAILED")
            print("  Some filtered categories do not have negative remaining_amount")
            
        return overspent_only
        
    except Exception as e:
        print(f"\n✗ filter_overspent_categories: FAILED")
        print(f"  Error: {e}")
        return False

async def test_coordinator_node():
    """Test the coordinator_node updates task_info based on task_management."""

    print("=" * 60)
    print("TESTING COORDINATOR NODE FUNCTIONALITY")
    print("=" * 60)

    today = datetime.now().date()
    original_task_management = agent_nodes.task_management

    scenarios = [
        ("Daily tasks path", "daily_tasks"),
        ("Both tasks path", "both_tasks"),
    ]

    all_passed = True

    try:
        for description, return_value in scenarios:
            agent_nodes.task_management = lambda rv=return_value: rv

            state = BudgetAgentState(
                run_meta=RunMeta(
                    run_id=f"coordinator_test_{return_value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    today=today,
                    tz="UTC",
                ),
                current_month_budget=None,
                current_month_txn=[],
                previous_month_txn=[],
                last_day_txn=[],
                overspend_budget_data=None,
                daily_overspend_alert=DailyAlertOverspend(),
                daily_suspicious_transactions=[],
                daily_alert_suspicious_transaction=DailyAlertSuspiciousTransaction(),
                report_category=ReportCategory(
                    category_name="test",
                    category_group_name="test",
                    overspent_amount=0.0,
                ),
                period_report=PeriodReport(period="test", categories_in_report=[]),
                process_flag=ProcessFlag(),
                email_info=None,
                task_info="initial_state",
            )

            updated_state = await coordinator_node(state)
            passed = updated_state.task_info == return_value

            if passed:
                print(f"✓ {description}: task_info updated to '{return_value}'")
            else:
                print(
                    f"✗ {description}: expected task_info '{return_value}' but found '{updated_state.task_info}'"
                )

            all_passed = all_passed and passed

    except Exception as e:
        print(f"\n✗ coordinator_node: FAILED")
        print(f"  Error: {e}")
        all_passed = False

    finally:
        agent_nodes.task_management = original_task_management

    if all_passed:
        print("\n✓ coordinator_node task routing: ALL TESTS PASSED")
    else:
        print("\n✗ coordinator_node task routing: SOME TESTS FAILED")

    return all_passed


async def test_daily_suspicious_transaction_alert_node():
    """Test daily_suspicious_transaction_alert_node end-to-end with mocked LLM responses."""

    print("\n" + "=" * 60)
    print("TESTING DAILY_SUSPICIOUS_TRANSACTION_ALERT_NODE")
    print("=" * 60)

    today = date.today()

    def build_base_state(last_day_txn_json: list[str]) -> BudgetAgentState:
        return BudgetAgentState(
            run_meta=RunMeta(
                run_id=f"daily_suspicious_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                today=today,
                tz="UTC",
            ),
            current_month_budget=None,
            current_month_txn=[],
            previous_month_txn=[],
            last_day_txn=last_day_txn_json,
            overspend_budget_data=None,
            daily_overspend_alert=DailyAlertOverspend(),
            daily_suspicious_transactions=[],
            daily_alert_suspicious_transaction=DailyAlertSuspiciousTransaction(),
            report_category=ReportCategory(
                category_name="test",
                category_group_name="test",
                overspent_amount=0.0,
            ),
            period_report=PeriodReport(period="test", categories_in_report=[]),
            process_flag=ProcessFlag(),
            email_info=None,
            task_info="daily_tasks",
        )

    async def fake_call_llm(*args, **kwargs):
        if "transaction" in kwargs:
            txn_payload = json.loads(kwargs["transaction"])
            is_suspicious = txn_payload.get("amount", 0) > 500
            response = {
                "funny_quip": "Big spender alert!" if is_suspicious else "All clear.",
                "type": "suspicious" if is_suspicious else "not_suspicious",
            }
            return json.dumps(response)
        if "transactions" in kwargs:
            try:
                suspicious_list = json.loads(kwargs["transactions"])
            except json.JSONDecodeError:
                suspicious_list = []
            return f"Story time for {len(suspicious_list)} suspicious transaction(s)!"
        return json.dumps({})

    original_call_llm = agent_nodes.call_llm
    agent_nodes.call_llm = fake_call_llm

    try:
        print("- Scenario 1: Suspicious transactions present")
        suspicious_amount = TransactionRow(
            amount=725.0,
            category_id="cat_high",
            category_name="Luxury Shopping",
            createdAt="2024-05-03T08:00:00Z",
            description="Designer Store",
            merchant_id="m999",
            merchant_name="Luxury Boutique",
            transaction_id="txn_suspicious",
            updatedAt="2024-05-03T09:00:00Z",
        )
        normal_amount = TransactionRow(
            amount=45.0,
            category_id="cat_coffee",
            category_name="Coffee Shops",
            createdAt="2024-05-03T10:00:00Z",
            description="Morning Latte",
            merchant_id="m111",
            merchant_name="Cafe Delight",
            transaction_id="txn_normal",
            updatedAt="2024-05-03T10:05:00Z",
        )

        state_with_suspicious = build_base_state(
            [suspicious_amount.model_dump_json(), normal_amount.model_dump_json()]
        )

        updated_state = await daily_suspicious_transaction_alert_node(state_with_suspicious)

        story_text = updated_state.daily_alert_suspicious_transaction.text
        story_passed = "Story time" in story_text and "1 suspicious" in story_text
        flag_passed = updated_state.process_flag.daily_suspicious_transaction_alert_done is True

        if story_passed and flag_passed:
            print("  ✓ Suspicious transaction path: PASSED")
            print(f"    Story output: {story_text}")
        else:
            print("  ✗ Suspicious transaction path: FAILED")
            print(f"    Story output: {story_text}")

        print("- Scenario 2: No suspicious transactions")
        low_amount = TransactionRow(
            amount=15.0,
            category_id="cat_snack",
            category_name="Snacks",
            createdAt="2024-05-03T11:00:00Z",
            description="Snack Stop",
            merchant_id="m222",
            merchant_name="Snack Shack",
            transaction_id="txn_snack",
            updatedAt="2024-05-03T11:05:00Z",
        )

        state_no_suspicious = build_base_state([low_amount.model_dump_json()])
        updated_state_no_suspicious = await daily_suspicious_transaction_alert_node(state_no_suspicious)

        no_story_text = updated_state_no_suspicious.daily_alert_suspicious_transaction.text
        no_story_passed = no_story_text == "No 'Funny' Transactions Today"
        no_flag_passed = (
            updated_state_no_suspicious.process_flag.daily_suspicious_transaction_alert_done is True
        )

        if no_story_passed and no_flag_passed:
            print("  ✓ No suspicious transaction path: PASSED")
        else:
            print("  ✗ No suspicious transaction path: FAILED")
            print(f"    Message: {no_story_text}")

        all_passed = story_passed and flag_passed and no_story_passed and no_flag_passed
        return all_passed

    finally:
        agent_nodes.call_llm = original_call_llm

async def main():
    print("Starting comprehensive testing of import_data_node...")
    
    # Test the utility function first
    filter_test_passed = test_filter_overspent_categories()
    
    # Test the coordinator node
    coordinator_test_passed = await test_coordinator_node()
    
    # Test the main import function
    import_test_passed = await test_import_data_node()

    # Test the suspicious transaction alert node
    suspicious_alert_test_passed = await test_daily_suspicious_transaction_alert_node()
    
    print("\n" + "=" * 60)
    print("FINAL TEST RESULTS")
    print("=" * 60)
    print(f"Filter utility test: {'PASSED' if filter_test_passed else 'FAILED'}")
    print(f"Coordinator node test: {'PASSED' if coordinator_test_passed else 'FAILED'}")
    print(f"Import data node test: {'PASSED' if import_test_passed else 'FAILED'}")
    print(f"Daily suspicious alert node test: {'PASSED' if suspicious_alert_test_passed else 'FAILED'}")
    
    if (
        filter_test_passed
        and coordinator_test_passed
        and import_test_passed
        and suspicious_alert_test_passed
    ):
        print("\n🎉 ALL TESTS PASSED! The nodes are ready for production.")
    else:
        print("\n⚠️ SOME TESTS FAILED. Please review the issues above.")

if __name__ == "__main__":
    asyncio.run(main())

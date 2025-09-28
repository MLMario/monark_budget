# Monark Budget: An Intelligent Financial Companion

## The Problem: When Budgeting Becomes a Chore

Like many couples, my wife and I found ourselves trapped in the endless cycle of traditional expense tracking. We'd dutifully log into our budgeting app, squint at colorful pie charts, and wonder: *"Okay, we overspent this month... but why? And what can we actually do about it?"*

The problem wasn't just that budget tracking was tedious—it was that it felt impersonal and reactive. We'd discover we'd blown our budget at some point and had to manually analyze our spend to understand which txn actually drove us to spend more than we expected. We wanted something that would not only tell us *what* was happening with our money, but *why* it was happening and *what we could do* to improve our financial habits in a way that felt personalized to our unique spending patterns and goals.

## The Solution: Meet Your AI Budget Agent

Enter **Monark Budget**—an intelligent agent that transforms budget and raw financial data into personalized, actionable insights. Instead of static reports and generic advice, we built an AI companion that understands our spending personality, catches our bad habits in real-time, and delivers insights with the perfect blend of humor and helpfulness. Or well, at least I we tried to, this is still and MVP and has lots of room for improvement, personalization and learning abilities over time.

### What Our Agent Delivers

**1. Daily Overspend Alerts**  
Every morning, our agent analyzes our current month's spending and sends personalized alerts when we've already exceeded budget limits in specific categories. No more discovering at month-end that we blew through our coffee shop budget two weeks ago.

**2. Daily Transaction Reviews**  
The agent reviews yesterday's purchases against our personal savings guidelines (like our notorious weakness for Amazon impulse buys) and creates witty, personalized stories featuring us as characters learning lessons about our spending habits. Think financial advice meets creative storytelling.

**3. Weekly & End-of-Month Intelligence Reports**  
When it's time for deeper analysis, our agent compares current and previous month transactions, identifies spending drivers, and provides targeted recommendations for categories where we've overspent. These aren't generic tips—they're data-driven insights specific to our patterns.

## The Journey: Building an AI Budget Agent

### Chapter 1: Cracking the Monarch Money Vault

Our first challenge? Monarch Money doesn't offer a public API, but it's where all our financial data lives. We needed to become digital detectives.

The solution lives in [`services/api/pipelines/monarchmoney.py`](services/api/pipelines/monarchmoney.py), where we updated monarymoney python package to be able to:
- Handles authentication with device IDs and credentials to sidestep current Email OTP (monarymoney cannot handle this)
- Manages session persistence using pickle files
- Executes GraphQL queries to extract budget and transaction data
- Gracefully handles rate limiting and session expiration

```python
# The core data extraction happens through GraphQL queries
async def get_budgets(self) -> str:
    query = """
    query GetBudgetData($filters: BudgetSummaryFilters!) {
        budgetSummary(filters: $filters) {
            # ... detailed budget fields
        }
    }
    """
```

This isn't web scraping—it's reverse-engineering their internal API to create a reliable data pipeline.

### Chapter 2: Embracing the MongoDB Life

With data flowing from Monarch, we needed somewhere free and flexible to store it. MongoDB became our financial data warehouse, managed through [`services/api/pipelines/mongo_client.py`](services/api/pipelines/mongo_client.py).

Our MongoDB setup features:
- **Async operations** using Motor for non-blocking database interactions
- **Smart filtering** with date ranges and category queries
- **Full refresh patterns** ensuring data consistency
- **Connection management** that properly closes resources

```python
class AsyncMongoDBClient:
    async def import_budget_data(self, filter_query: Optional[dict] = None):
        cursor = self.budgets_collection.find(filter_query, {"_id": 0})
        documents = await cursor.to_list(length=None)
        return json.dumps(documents, default=str)
```

The beauty is in its simplicity—clean JSON in, structured queries out.

### Chapter 3: Automating the Data Pipeline

Manual data updates? Not in this household. We built [`services/api/pipelines/data_import_pipeline.py`](services/api/pipelines/data_import_pipeline.py) to handle the entire extract-transform-load process:

```python
async def run_pipeline():
    mm = MonarchMoney()
    await mm.login()
    
    # Extract fresh budget and transaction data
    budget_data = await mm.get_budgets()
    transaction_data = await mm.get_transactions(limit=2000)
    
    # Transform and validate through Pydantic models
    budget_objects = [BudgetRow(**budget) for budget in budget_json]
    
    # Load into MongoDB
    mongo_client.export_budget_data(budget_objects)
```

The pipeline runs daily via GitHub Actions at 6 AM PST, ensuring our agent always has fresh data to analyze.

### Chapter 4: Building the AI Brain with LangGraph

Here's where things get interesting. We used LangGraph to create a sophisticated agent workflow in [`services/api/app/agent/agent_graph.py`](services/api/app/agent/agent_graph.py) that processes our financial data through a series of intelligent nodes:

**The Agent Workflow:**
```python
# 1. Data Import Node - Fetches and processes MongoDB data
graph_builder.add_node("import_data_node", import_data_node)

# 2. Daily Analysis Nodes
graph_builder.add_node("daily_overspend_alert_node", daily_overspend_alert_node)
graph_builder.add_node("daily_suspicious_transaction_alert_node", daily_suspicious_transaction_alert_node)

# 3. Coordinator Node - Decides if we need period reports
graph_builder.add_node("coordinator_node", coordinator_node)

# 4. Period Analysis Nodes (for weekly/monthly reports)
graph_builder.add_node("period_report_node", period_report_node)

# 5. Email Node - Delivers personalized insights
graph_builder.add_node("email_node", email_node)
```

**The Intelligence Layer:**
Our agent utilities in [`services/api/app/agent/agent_utilities.py`](services/api/app/agent/agent_utilities.py) leverage Groq's LLMs for:
- **Overspend analysis** using the Llama model for budget interpretation
- **Transaction classification** with reasoning models that identify "suspicious" purchases
- **Storytelling** that transforms dry transaction data into engaging narratives
- **Period reporting** that compares months and identifies spending patterns

```python
async def call_llm_reasoning(
    temperature=0.7,
    prompt_obj=None,
    model=Settings.GROQ_QWEN_REASONING,
    reasoning_format='hidden',
    **kwargs
):
    # AI-powered analysis with hidden reasoning chains
    completion = await client.chat.completions.create(
        model=model,
        messages=[...],
        reasoning_format=reasoning_format
    )
```

**The Node Logic:**
Each node in [`services/api/app/agent/nodes.py`](services/api/app/agent/nodes.py) handles specific intelligence tasks:
- **Daily overspend alerts** analyze budget vs. actual spending
- **Suspicious transaction detection** applies our personal savings rules
- **Period reports** perform month-over-month transaction analysis
- **Email generation** creates HTML-formatted insights with personality

### Chapter 5: Orchestrating Everything with Main

The final piece was [`main.py`](main.py)—a clean entry point that brings everything together:

```python
async def run_agent() -> BudgetAgentState:
    graph = create_budget_graph()
    app = graph.compile()
    
    initial_state = _build_initial_state()
    result = await app.ainvoke(initial_state)
    
    return result
```

This creates our agent's initial state (run metadata, empty alerts, process flags), compiles the LangGraph workflow, and executes the entire intelligence pipeline in one clean async call.

**GitHub Actions Integration:**
The crown jewel is our [`.github/workflows/daily_budget_data_git_pipeline.yml`](.github/workflows/daily_budget_data_git_pipeline.yml) that:
1. Runs the data import pipeline to refresh our MongoDB
2. Waits 2 minutes for data to settle
3. Executes `main.py` to run our AI agent
4. Delivers personalized financial insights to our inboxes

```yaml
- name: Start Agent Pipeline
  run: |
    python -m main
```

## The Result: Financial Intelligence, Delivered

Every day, we wake up to emails that don't just tell us we overspent—they tell us *why* we overspent, *what patterns* led to it, and *how we can do better*. Our agent has become like having a witty financial advisor who knows our habits, celebrates our wins, and gently roasts us for our Amazon addiction.

This isn't just automation—it's augmented financial intelligence that transforms the chore of budget tracking into an engaging, personalized experience that actually helps us make better money decisions.
# Monark Budget Agent: Your AI-Powered Financial Companion

## The Problem: When Budgeting Becomes a Chore

Like many couples, my wife and I found ourselves trapped in the endless cycle of traditional expense tracking. We'd dutifully log into our budgeting app, squint at colorful pie charts, and wonder: *"Okay, we overspent this month... but why? And what can we actually do about it?"*

The problem wasn't just that budget tracking was tedious—it was that it felt impersonal and reactive. We'd discover we'd blown our budget at some point and had to manually analyze our spending to understand which transaction actually drove us to spend more than we expected. We wanted something that would not only tell us *what* was happening with our money, but *why* it was happening and *what we could do* to improve our financial habits in a way that felt personalized to our unique spending patterns and goals.

## The Solution: Meet Your AI Budget Agent

Enter **Monark Budget**—an intelligent agent that transforms raw financial data into personalized, actionable insights delivered straight to your inbox. Instead of static reports and generic advice, we built an AI companion that understands spending patterns, catches bad habits in real-time, and delivers insights with the perfect blend of humor and helpfulness. This is an MVP with lots of room for improvement, personalization, and learning abilities over time.

### What Our Agent Delivers

**1. Daily Overspend Alerts**
Every morning, the agent analyzes your current month's spending and sends personalized alerts when you've already exceeded budget limits in specific categories. No more discovering at month-end that you blew through your dining budget two weeks ago.

**2. Daily Suspicious Transaction Reviews**
The agent reviews yesterday's purchases against your personal savings guidelines and creates witty, personalized stories featuring you as the protagonist learning lessons about spending habits. Think financial advice meets creative storytelling—powered by AI reasoning models.

**3. Weekly & End-of-Month Intelligence Reports**
When it's time for deeper analysis (Mondays for weekly, first of month for monthly), the agent compares budget data with transaction history, identifies spending drivers, and provides targeted recommendations for overspent categories. These aren't generic tips—they're data-driven insights specific to your patterns.

## The Journey: Building an AI Budget Agent

### Chapter 1: Cracking the Monarch Money Vault

Our first challenge? Monarch Money doesn't offer a public API, but it's where all our financial data lives. We needed to become digital detectives.

The solution lives in our [custom monarchmoney python package](services/api/pipelines/monarchmoney.py). We extended an existing open-source package called [monarchmoney](https://github.com/hammem/monarchmoney) that handles login, session management, and GraphQL queries. However, it was outdated and incompatible with current Monarch Money authentication flows, so we had to update it ourselves.

The main challenge was bypassing the Email OTP identification step triggered when logging in from an unrecognized device. After exploration and testing, we implemented a "hacky" but effective fix: adding our Chrome browser's `Device-UUID` into the authentication header during login. This approach:
- Tricks Monarch into recognizing our script as a trusted device
- Requires manual updates only when the device ID expires (roughly every few months)
- Currently limits the system to single-user usage

Not elegant, but it works. Sometimes pragmatism beats perfection.

**How It Works:**

The authentication system ([monarchmoney.py](services/api/pipelines/monarchmoney.py)) handles:
- **Custom headers** including `Device-UUID` to bypass OTP verification
- **Session persistence** using pickle files to avoid repeated logins
- **Token validation** to reuse existing sessions when available
- **GraphQL client setup** with proper authentication headers for all API calls

Once authenticated, we extract budget and transaction data through Monarch's internal GraphQL API:
```python
async def get_budgets(self) -> dict:
    # Fetches budget data with category breakdowns
    # Returns: actual amounts, planned amounts, remaining amounts

async def get_transactions(self, limit: int = 100) -> list:
    # Fetches transaction history with merchant details
    # Returns: amounts, categories, merchants, timestamps
```

The entire authentication and data extraction flow is orchestrated in [import_functions.py](services/api/pipelines/import_functions.py), which manages the MonarchMoney client lifecycle and data retrieval operations.

### Chapter 2: Embracing the MongoDB Life

With data flowing from Monarch, we needed somewhere free and flexible to store it. MongoDB became our financial data warehouse, managed through [mongo_client.py](services/api/pipelines/mongo_client.py).

**Why MongoDB?**
- Free tier (MongoDB Atlas) is generous enough for personal use
- Flexible schema perfect for evolving financial data models
- Async support (Motor) for non-blocking operations in our agent
- JSON-native storage works seamlessly with Pydantic models

**Our Two-Client Approach:**

We use two MongoDB clients for different purposes:

1. **MongoDBClient** (sync) - Used in the data import pipeline for bulk operations:
   - Connects using standard PyMongo
   - Performs full collection refreshes (delete all → insert all)
   - Runs in [data_import_pipeline.py](services/api/pipelines/data_import_pipeline.py)

2. **AsyncMongoDBClient** (async) - Used in agent nodes for filtered queries:
   - Connects using Motor (async driver)
   - Performs filtered queries with date ranges and category filters
   - Runs during agent execution in [nodes.py](services/api/app/agent/nodes.py)

**Data Validation Flow:**

Every piece of data goes through Pydantic validation (JSON → Pydantic → JSON). This might seem redundant, but it ensures data consistency and catches errors early:

```python
# Fetch from MongoDB
budget_json = await mongo_client.import_budget_data(
    filter_query={'category_group_type': 'expense'}
)

# Validate through Pydantic models
budget_rows = [BudgetRow(**row) for row in json.loads(budget_json)]
validated_budget = BudgetData(current_month_budget=budget_rows)

# Store validated JSON in agent state
state.current_month_budget = validated_budget.model_dump_json()
```

This approach has saved us from numerous data inconsistencies and makes debugging much easier.


### Chapter 3: Automating the Data Pipeline

Manual data updates? Not happening. We built an [automated ETL pipeline](services/api/pipelines/data_import_pipeline.py) to handle the entire extract-transform-load process:

**The Pipeline Flow:**

1. **Extract** - Authenticate with Monarch Money and fetch fresh data
2. **Transform** - Parse raw GraphQL responses into structured Pydantic models
3. **Load** - Perform full MongoDB collection refresh with validated data

```python
async def run_pipeline():
    # Authenticate and extract
    mm = MonarchMoney()
    await mm.login()
    budget_data = await mm.get_budgets()
    transaction_data = await mm.get_transactions(limit=2000)

    # Transform and validate
    budget_objects = parse_budget_data(budget_data)
    transaction_objects = parse_transaction_data(transaction_data)

    # Load into MongoDB
    mongo_client.export_budget_data(budget_objects)
    mongo_client.export_transaction_data(transaction_objects)
```

**Automated Execution:**

The pipeline runs daily via [GitHub Actions](.github/workflows/daily_budget_data_git_pipeline.yml) at 6 AM PST:
- ✅ Free (within GitHub Actions free tier)
- ✅ Reliable (automated retries on failure)
- ✅ Secure (credentials stored as GitHub secrets)
- ✅ Observable (execution logs for debugging)

This ensures our agent always analyzes the most current financial data without any manual intervention.

### Chapter 4: Building the AI Brain with LangGraph

Here's where things get interesting. We used LangGraph to orchestrate a stateful AI workflow defined in [agent_graph.py](services/api/app/agent/agent_graph.py). Think of it as a flowchart where each node performs specific financial analysis tasks, and the graph intelligently routes between them.

**The Agent Workflow:**

```
START → Import Data → Daily Overspend Alert → Daily Transaction Review →
Coordinator → [Conditional Routing] → Period Report → Email → END
```

The workflow is built with these nodes:

1. **import_data_node** - Fetches budget data and yesterday's transactions from MongoDB
2. **daily_overspend_alert_node** - Generates alerts for overspent categories
3. **daily_suspicious_transaction_alert_node** - Reviews each transaction and creates witty stories
4. **coordinator_node** - Routes workflow based on calendar (daily, EOW Monday, EOM first day)
5. **import_current_month_txn_node** - Fetches transaction data for weekly reports (EOW path)
6. **import_previous_month_txn_node** - Fetches transaction data for monthly reports (EOM path)
7. **eow_period_report_node** - Generates weekly analysis report
8. **eom_period_report_node** - Generates monthly analysis report
9. **email_node** - Converts all alerts/reports to HTML and sends email

**The Intelligence Layer:**

The magic happens through LLM calls powered by Groq's API ([agent_utilities.py](services/api/app/agent/agent_utilities.py)):

- **Overspend Alerts** - LLM crafts personalized messages listing overspent categories
- **Transaction Classification** - Reasoning models identify "suspicious" purchases outside savings guidelines
- **Narrative Storytelling** - Transforms boring transaction data into engaging, witty stories
- **Period Reports** - Analyzes each overspent category individually, then synthesizes final insights

We use two types of LLM calls:

```python
# Standard generation (for alerts & storytelling)
await call_llm(
    prompt_obj=PROMPT_TEMPLATE,
    model="llama-3.3-70b-versatile",
    temperature=0.7
)

# Reasoning models (for transaction analysis & reports)
await call_llm_reasoning(
    prompt_obj=ANALYSIS_PROMPT,
    model="openai/gpt-oss-120b",
    reasoning_format='hidden',  # Uses chain-of-thought internally
    reasoning_effort='high'
)
```

Is this the most efficient implementation? No. But it works, and sometimes shipping beats perfecting. Future iterations will optimize token usage and parallelize LLM calls.

### Chapter 5: Orchestrating Everything with Main

The final piece is [main.py](main.py)—a clean entry point that orchestrates the entire system:

```python
async def run_agent() -> BudgetAgentState:
    # Create and compile the LangGraph workflow
    graph = create_budget_graph()
    app = graph.compile()

    # Initialize agent state with current timestamp and empty data
    initial_state = _build_initial_state()

    # Execute the workflow and return final state
    result = await app.ainvoke(initial_state)

    return result
```

That's it. One function call executes the entire intelligence pipeline: data import → daily analysis → conditional routing → period reports → email delivery.

**The Daily Automation:**

The crown jewel is our [GitHub Actions workflow](.github/workflows/daily_budget_data_git_pipeline.yml) that runs every morning at 6 AM PST:

```yaml
name: Daily Budget Agent Pipeline
on:
  schedule:
    - cron: '0 14 * * *'  # 6 AM PST = 14:00 UTC

jobs:
  run-agent:
    runs-on: ubuntu-latest
    steps:
      - name: Import Fresh Data
        run: python -m services.api.pipelines.data_import_pipeline

      - name: Wait for MongoDB Persistence
        run: sleep 120

      - name: Run AI Agent
        run: python -m main
```

This ensures we wake up every day to fresh, personalized financial insights—no manual work required.

## The Result: Financial Intelligence, Delivered

Every day, we wake up to emails that don't just tell us we overspent—they tell us *why* we overspent, *what patterns* led to it, and *how we can do better*. The agent has become like having a witty financial advisor who knows your habits, celebrates your wins, and gently roasts you for bad spending decisions.

This isn't just automation—it's augmented financial intelligence that transforms the chore of budget tracking into an engaging, personalized experience that actually helps make better money decisions.

**Sample Email Output:**

<img src="IMG_1010.jpeg" alt="Daily Alert Email" width="25%">
<img src="IMG_1011.jpeg" alt="Period Report Email" width="25%">

The emails combine:
- 📊 **Data-driven alerts** with specific overspend amounts and percentages
- 📖 **Narrative storytelling** that makes transaction reviews entertaining
- 💡 **Actionable recommendations** based on actual spending patterns
- 🎭 **Personality and humor** that keeps financial advice engaging

## Building an AI Agent with AI: The 80-Hour Learning Journey

The objective of this project wasn't just to create something useful—it was to learn. As the developer behind this project, I built this entire system using AI as a learning tool, not a code generator. After many trials and errors, I found the sweet spot where I remained deeply challenged and had to think through infrastructure and solutions myself, while still leveraging AI effectively.

**My AI-Assisted Learning Framework:**

**1. Strategic Planning & Architecture**
I used AI to understand what I needed to implement and how to design the system. This wasn't about getting code—it was about understanding system architecture, data flow patterns, and technology choices. The AI became my brainstorming partner for the big picture.

**2. Deep Knowledge Acquisition**
Whenever I hit knowledge gaps, I didn't just ask for specific snippets. Instead, I used AI to deep dive into entire concepts. Learning LangGraph wasn't just about building this workflow—it was about understanding agent systems as a paradigm. This broader context has empowered me to keep building and experimenting beyond this project.

**3. Strategic Decision Making**
I treated AI as a thinking partner for architectural decisions. How should I structure agent nodes? What email sending options exist? What's the tradeoff between MongoDB and PostgreSQL? These conversations sharpened my technical judgment and helped me make informed choices.

**4. Bug Detection (Not Solutions)**
I used AI to identify potential pitfalls, then solved problems myself. This forced me to truly understand the codebase, error patterns, and debugging strategies. The satisfaction of fixing an issue after wrestling with it for hours? Priceless... sometimes. Most of the time it was frustrating, but that's where the learning happened.

**5. Test Script Generation**
Let's be honest—writing test scripts is tedious. AI excelled at generating comprehensive test cases ([unitest.py](unitest.py)), mock data, and validation scripts. This freed me to focus on understanding testing patterns rather than writing boilerplate.

**The Result?**

80 hours of intense learning that left me with both a working product *and* genuine knowledge in:
- ✅ Async Python programming
- ✅ GraphQL API integration
- ✅ LangGraph agent workflows
- ✅ MongoDB data modeling
- ✅ AI agent design patterns
- ✅ GitHub Actions CI/CD

I could have built this faster by copy-pasting AI-generated code, but I would have learned nothing. Instead, I used AI as the ultimate learning accelerator—challenging me to think deeper while handling the grunt work.

---

## What's Next?

This project is complete as an MVP, but there's room for improvement:

**Potential Enhancements:**
- 🔐 Multi-user authentication (OAuth instead of device ID hack)
- 💾 Agent state persistence for learning from past recommendations
- 🔄 Retry logic and error recovery for LLM calls
- ⚡ Parallel LLM processing to reduce execution time
- 📧 Dynamic recipient configuration
- 💰 Cost optimization through intelligent caching

For now, this serves its purpose: delivering daily financial insights with personality. If you have recommendations or want to contribute, feel free to open an issue or submit a pull request!

**Technical Documentation:** See [readme_technical.md](readme_technical.md) for detailed architecture, setup instructions, and developer workflows.




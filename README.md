# Agent for Money Monark Budget: An Intelligent Financial Companion

## The Problem: When Budgeting Becomes a Chore

Like many couples, my wife and I found ourselves trapped in the endless cycle of traditional expense tracking. We'd dutifully log into our budgeting app, squint at colorful pie charts, and wonder: *"Okay, we overspent this month... but why? And what can we actually do about it?"*

The problem wasn't just that budget tracking was tedious—it was that it felt impersonal and reactive. We'd discover we'd blown our budget at some point and had to manually analyze our spending to understand which transaction actually drove us to spend more than we expected. We wanted something that would not only tell us *what* was happening with our money, but *why* it was happening and *what we could do* to improve our financial habits in a way that felt personalized to our unique spending patterns and goals.

## The Solution: Meet Your AI Budget Agent

Enter **Monark Budget**—an intelligent agent that transforms budget and raw financial data into personalized, actionable insights. Instead of static reports and generic advice, we built an AI companion that understands our spending personality, catches our bad habits in real-time, and delivers insights with the perfect blend of humor and helpfulness. Or well, at least we tried to—this is still an MVP and has lots of room for improvement, personalization, and learning abilities over time.

### What Our Agent Delivers

**1. Daily Overspend Alerts**  
Every morning, our agent analyzes our current month's spending and sends personalized alerts when we've already exceeded budget limits in specific categories. No more discovering at month-end that we blew through our coffee shop budget two weeks ago.

**2. Daily Transaction Reviews**  
The agent reviews yesterday's purchases against our personal savings guidelines (like our notorious weakness for Amazon impulse buys) and creates witty, personalized stories featuring us as characters learning lessons about our spending habits. Think financial advice meets creative storytelling.

**3. Weekly & End-of-Month Intelligence Reports**  
When it's time for deeper analysis, our agent compares current and previous month transactions, identifies spending drivers, and provides targeted recommendations for categories where we've overspent. These aren't generic tips—they're data-driven insights specific to our patterns.

## The Journey: Building an AI Budget Agent

### Chapter 1: Cracking the Monarch Money Vault

Our first challenge? Monarch Money Budget App doesn't offer a public API, but it's where all our financial data lives. We needed to become digital detectives.

The solution lives in [this adjusted monarchmoney python package](services/api/pipelines/monarchmoney.py). This package updates an already existing package called...you guessed it, [monarchmoney](https://github.com/hammem/monarchmoney). This package can handle login, session management, and GraphQL queries of several kinds, but sadly, it's outdated and doesn't work well with the current Monarch Money Budget App, so I had no choice but to update it myself. The main issue was that it needed a method to bypass a new Email OTP identification step that's triggered when attempting login from a device Monarch Money doesn't recognize. It also needed updates to reflect the latest version of GraphQL, but that was relatively straightforward to do. The main problem was the email OTP step. After much exploration and ideation, I decided to disgrace myself and implement a 'hacky' fix. Basically, adding our personal chrome browser device_id into the auth header during the login step solved that issue. This will require a manual update at some point, but fortunately, it should only happen once every few months. Unfortunately, it means only we can use this product. 

**Authentication & Session Management:**
The MonarchMoney class initializes with custom headers including `Device-UUID` to bypass device recognition:

```python
def __init__(self, session_file: str = SESSION_FILE, timeout: int = 10, token: Optional[str] = None):
    self._headers = {
        "Accept": "application/json",
        "Client-Platform": "web", 
        "Content-Type": "application/json",
        "User-Agent": "MonarchMoneyAPI (https://github.com/hammem/monarchmoney)",
        'Device-UUID': Settings.MONARK_DD_ID.get_secret_value()  # Critical for bypassing OTP
    }
    if token:
        self._headers["Authorization"] = f"Token {token}"
```

**Login Flow:**
The login process handles session persistence and token validation:

```python
async def login(self, email: str = None, password: str = None, use_saved_session: bool = True):
    if use_saved_session and os.path.exists(self._session_file):
        self.load_session(self._session_file)
        if await self._validate_token():
            return  # Use existing session
    
    await self._login_user(email, password, mfa_secret_key)
    if save_session:
        self.save_session(self._session_file)  # Pickle session for reuse
```

**GraphQL Client Setup:**
All data extraction happens through a properly configured GraphQL client that includes our authentication headers:

```python
def _get_graphql_client(self) -> Client:
    if not self._token and "Authorization" not in self._headers:
        raise LoginFailedException("Make sure you call login() first!")
    
    transport = AIOHTTPTransport(
        url=MonarchMoneyEndpoints.getGraphQL(),
        headers=self._headers,  # Includes Device-UUID and Authorization
        timeout=self._timeout,
    )
    return Client(transport=transport, fetch_schema_from_transport=False)

async def gql_call(self, operation: str, graphql_query: DocumentNode, variables: Dict = {}):
    req = GraphQLRequest(graphql_query, operation_name=operation, variable_values=variables)
    async with self._get_graphql_client() as session:
        return await session.execute(req)
```

**Data Extraction Queries:**
The core budget data extraction leverages Monarch's internal GraphQL schema:

```python
async def get_budgets(self) -> str:
    query = gql("""
        query GetBudgetData($filters: BudgetSummaryFilters!) {
            budgetSummary(filters: $filters) {
                categoryGroups {
                    categories {
                        id name actualAmount plannedAmount remainingAmount
                        # ... detailed budget fields
                    }
                }
            }
        }
    """)
    return await self.gql_call("GetBudgetData", query, variables)
```

### Chapter 2: Embracing the MongoDB Life

With data flowing from Monarch, we needed somewhere free and flexible to store it. MongoDB became our financial data warehouse, managed through [`services/api/pipelines/mongo_client.py`](services/api/pipelines/mongo_client.py).

Our MongoDB setup features:
- **Async operations** using Motor for daily data import and exports, and Async Motor for data import within node execution
- **Filtering** with date ranges and category queries enabled
- **Pydantic Data Validation** ensuring data consistency
- **Connection management** that properly closes resources

Motor Client creation to use in daily data import from monarch and exporting to Mongo DB
```python
class MongoDBClient:
    def __init__(self):
        self.client = MongoClient(Settings.MONGO_URL.get_secret_value())
        self.db = self.client[Settings.MONGO_DB]
        self.budgets_collection = self.db['budget']
        self.transactions_collection = self.db['transactions']
```

Async Client creation to fetch data from MongoDB within node execution
```python
class AsyncMongoDBClient:
    def __init__(self):
        self.client = AsyncIOMotorClient(Settings.MONGO_URL.get_secret_value())
        self.db = self.client[Settings.MONGO_DB]
        self.budgets_collection = self.db['budget']
        self.transactions_collection = self.db['transactions']

```

Imported data goes from JSON to Pydantic back to JSON—seems redundant but it will help raise errors if there are errors in the data. 

```python
    #Create MongoDB Client to Import Data 
    mongo_client = AsyncMongoDBClient() 
    budget_json = await mongo_client.import_budget_data(filter_query={'category_group_type': 'expense'})
    
    # Data Model Validation Processing (Implicit given the use of Pydantic models)
    budget_list_data = json.loads(budget_json)
    budget_rows = [BudgetRow(**row) for row in budget_list_data]
    pydantic_budget_model = BudgetData(current_month_budget=budget_rows)
    state.current_month_budget = pydantic_budget_model.model_dump_json()
```


### Chapter 3: Automating the Data Pipeline

Manual data updates? Not in this household. We built [`this automated pipeline script`](services/api/pipelines/data_import_pipeline.py) to handle the entire extract-transform-load process:

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

The pipeline runs daily via GitHub Actions at 6 AM PST, ensuring our agent always has fresh data to analyze (And it's free!)

### Chapter 4: Building the AI Brain with LangGraph

Here's where things get interesting. We used LangGraph to create a simple agent workflow using [`graphs`](services/api/app/agent/agent_graph.py). This automated workflow processes our financial data through a series of intelligent nodes:

**The Agent Workflow:**
```python
# 1. Data Import Node - Fetches and processes MongoDB data
graph_builder.add_node("import_data_node", import_data_node)

# 2. Daily Analysis Nodes
graph_builder.add_node("daily_overspend_alert_node", daily_overspend_alert_node)
graph_builder.add_node("daily_suspicious_transaction_alert_node", daily_suspicious_transaction_alert_node)

# 3. Coordinator Node - Decides if we need period reports (aka, is it EOW or EOM?)
graph_builder.add_node("coordinator_node", coordinator_node)

# 4. Import Transaction Data Needed for Analysis
graph_builder.add_node('import_txn_data_for_period_report_node', import_txn_data_for_period_report_node)

# 5. Analysis Node (for weekly/monthly reports)
graph_builder.add_node("period_report_node", period_report_node)

# 6. Email Node - Crafts the email in HTML code and sends it
graph_builder.add_node("email_node", email_node)
```

**The Intelligence Layer:**

The intelligence layer is mostly based on calls to LLM models using Groq API and can be observed within the [`nodes code`](services/api/app/agent/nodes.py). The process leverages many [utility functions](services/api/app/agent/agent_utilities.py) but they are not 'agent capabilities'—meaning they are not tools that an agent can decide to use or not. Initially we had planned to add tools for analysis the agent could use, like creating summaries and statistics for categories and transactions, but we will leave that for future iterations.  

Overall, we use LLM for: 
- **Overspend Alerts** LLM crafts a personalized, funny alert message and lists all categories above budget 
- **Transaction classification** using reasoning models to identify transactions that are 'suspicious'—meaning they're likely to be outside our money-saving guidelines
- **Storytelling** that transforms dry transaction data into engaging, funny narratives
- **Period reporting** for looking at historical data for spending categories—it analyzes each category independently and then crafts one final report putting everything together with top drivers and recommendations. 

We basically call LLM for all these tasks with various settings and processes—if you look through the code... please don't judge us, we know the process is relatively inefficient and wastes a bit of money, but to our credit, iterating on efficiency didn't feel as urgent as actually getting something to work. 

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

![Email 1](IMG_1010.jpeg)
![Email 2](IMG_1011.jpeg)


## It took me 80 hours to build an AI agent using AI! wait what?

The objective of this project wasn't just to create something useful for us—it was to learn. As the husband (and coder) in this duo, I built this entire product using AI only as a tool to learn and help with auxiliary tasks. After many trials and errors, I found the sweet spot where I remained deeply challenged and had to think through infrastructure and solutions myself, while still leveraging AI effectively.

**My AI-Assisted Learning Framework:**

**1. Strategic Planning & Architecture**  
I asked the AI what I needed to implement this project and how to think about designing it. This wasn't about getting code—it was about understanding system architecture, data flow patterns, and technology choices. The AI became my brainstorming partner for the big picture.

**2. Deep Knowledge Acquisition**  
Whenever I hit knowledge gaps, I didn't just ask for the specific snippet I needed. Instead, I used AI to deep dive into entire concepts. For example, learning LangGraph was not just for my workflow, but as a paradigm for building agent systems. This broader context has empowered me and inspired me to keep building agents for the sake of learning, even though it won't help me with my future day-to-day work as a Data Scientist (but who knows! AI engineering on the horizon? haha)

**3. Strategic Decision Making**  
I treated AI as a thinking partner, sharing my plans and discussing the best strategies for implementing processes and choosing tools. How should I structure my agent nodes? What email sending options do I have? What's the tradeoff between MongoDB and PostgreSQL? These conversations sharpened my technical judgment.

**4. Bug Detection (Not Solutions)**  
Instead of waiting for things to break, I used AI to help identify potential pitfalls and then attempted to solve the problems myself. This forced me to truly understand the codebase, error patterns, and debugging strategies. The satisfaction of fixing an issue after wrestling with it for hours? Priceless... sometimes. Most of the time it was Hell Incarnated in my brain.  

**5. Test Script Generation**  
Let's be honest—writing test scripts is tedious. I'm human, and that stuff is boring. AI excelled at generating comprehensive test cases, mock data, and validation scripts, so why not?

**The Result?** 80 hours of intense learning that left me with both a working product *and* genuine knowledge in async Python, GraphQL, LangGraph, MongoDB, and AI agent design. I could have built this faster by copy-pasting AI-generated code, but I would have learned nothing. Instead, I used AI as the ultimate learning accelerator—challenging me to think deeper while handling the grunt work.

For now, I will pass over to other exciting projects, but there is still a lot of room for improvement. Send me any recs, recommendations on how to improve this product if you like




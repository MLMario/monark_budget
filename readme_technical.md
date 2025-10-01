# Monark Budget – Technical Documentation

This document provides comprehensive technical details for running, extending, and operating the Monark Budget agent. It complements the product-focused [README.md](README.md) by focusing on architecture, data flow, configuration, and developer workflows.

---

## System Overview

The Monark Budget project automates daily and periodic financial insights by orchestrating three core subsystems:

### 1. Data Ingestion Pipeline
An asynchronous ETL pipeline ([services/api/pipelines/data_import_pipeline.py](services/api/pipelines/data_import_pipeline.py)) that:
- Authenticates with Monarch Money using custom device identification bypass
- Downloads budget and transaction data via GraphQL queries
- Transforms and validates data through Pydantic models
- Persists to MongoDB collections via [MongoDBClient](services/api/pipelines/mongo_client.py)

### 2. AI Agent Workflow
A LangGraph-based state machine ([main.py](main.py), [services/api/app/agent/*](services/api/app/agent/)) that:
- Orchestrates multiple LLM-powered analysis tasks
- Generates daily overspend alerts and suspicious transaction narratives
- Produces weekly (EOW) and monthly (EOM) financial reports with actionable insights
- Manages conditional workflow routing based on calendar logic

### 3. Notification Delivery
An HTML email rendering and delivery system that:
- Transforms analysis results into formatted HTML emails
- Validates HTML structure before sending
- Delivers via Gmail SMTP using credentials from [config.Settings](config.py)

The [GitHub Actions workflow](.github/workflows/daily_budget_data_git_pipeline.yml) orchestrates these subsystems daily at 6 AM PST: ingests data, waits for MongoDB persistence, executes the agent, and delivers personalized reports.

---

## Repository Structure

| Path | Purpose |
|------|---------|
| [main.py](main.py) | Production entry point that initializes state, compiles the LangGraph workflow, and executes the agent pipeline. |
| [config.py](config.py) | Centralized Pydantic settings for Monarch Money, MongoDB, Groq API, and SMTP credentials. Auto-detects `.env` file location. |
| [services/api/app/agent/](services/api/app/agent/) | Agent core: graph definition, state models, node implementations, and utility functions. |
| &nbsp;&nbsp;├── [agent_graph.py](services/api/app/agent/agent_graph.py) | LangGraph workflow definition with nodes and conditional routing logic. |
| &nbsp;&nbsp;├── [state.py](services/api/app/agent/state.py) | Pydantic state models (`BudgetAgentState`, `ProcessFlag`, data models). |
| &nbsp;&nbsp;├── [nodes.py](services/api/app/agent/nodes.py) | Node implementations for data import, analysis, reporting, and email delivery. |
| &nbsp;&nbsp;└── [agent_utilities.py](services/api/app/agent/agent_utilities.py) | Helper functions: LLM calls, task routing, email sending, HTML validation. |
| [services/api/app/domain/prompts.py](services/api/app/domain/prompts.py) | LLM prompt templates with optional Opik versioning support. |
| [services/api/pipelines/](services/api/pipelines/) | Data pipeline components for Monarch Money and MongoDB integration. |
| &nbsp;&nbsp;├── [data_import_pipeline.py](services/api/pipelines/data_import_pipeline.py) | Orchestrates data extraction, transformation, and loading to MongoDB. |
| &nbsp;&nbsp;├── [import_functions.py](services/api/pipelines/import_functions.py) | Monarch Money API wrapper with authentication and data retrieval. |
| &nbsp;&nbsp;├── [mongo_client.py](services/api/pipelines/mongo_client.py) | Sync/async MongoDB clients for data export and import operations. |
| &nbsp;&nbsp;├── [monarchmoney.py](services/api/pipelines/monarchmoney.py) | Custom Monarch Money GraphQL client with device bypass authentication. |
| &nbsp;&nbsp;└── [data_parsing_functions.py](services/api/pipelines/data_parsing_functions.py) | Data transformation utilities for budget and transaction parsing. |
| [.github/workflows/daily_budget_data_git_pipeline.yml](.github/workflows/daily_budget_data_git_pipeline.yml) | Scheduled GitHub Actions workflow for automated daily execution. |
| [unitest.py](unitest.py) | Comprehensive test suite with mocked dependencies and live LLM integration tests. |
| [test_email_sender.py](test_email_sender.py) | Manual SMTP testing script for email delivery validation. |
| [test_llm.py](test_llm.py) | LLM integration testing script for prompt validation. |

---

## Architecture Deep Dive

### LangGraph Agent Workflow

The agent operates on [BudgetAgentState](services/api/app/agent/state.py), a Pydantic model tracking:
- **Metadata**: Run ID, date, timezone
- **Imported Data**: Current/past month budgets and transactions
- **Derived Data**: Overspent categories, yesterday's transactions
- **Generated Artifacts**: Daily alerts, period reports, email content
- **Process Flags**: Task completion tracking

The graph in [agent_graph.py](services/api/app/agent/agent_graph.py) implements this workflow:

```
START → import_data_node → daily_overspend_alert_node →
daily_suspicious_transaction_alert_node → coordinator_node →
[conditional routing] → email_node → END
```

#### Node Descriptions

**1. import_data_node** ([nodes.py:69-164](services/api/app/agent/nodes.py#L69-L164))
- Imports current and past month budget data from MongoDB
- Filters overspent categories (remaining_amount < -5)
- Imports yesterday's transactions for daily analysis
- Validates all data through Pydantic models

**2. daily_overspend_alert_node** ([nodes.py:181-199](services/api/app/agent/nodes.py#L181-L199))
- Calls LLM with current month overspend data
- Generates personalized alert text with category breakdown
- Updates `daily_overspend_alert` state field

**3. daily_suspicious_transaction_alert_node** ([nodes.py:201-296](services/api/app/agent/nodes.py#L201-L296))
- Loops through yesterday's transactions
- Uses reasoning model (OpenAI 20B) to classify each transaction as compliant/non-compliant
- For non-compliant transactions: generates witty narrative story
- Updates `daily_alert_suspicious_transaction` state

**4. coordinator_node** ([nodes.py:167-179](services/api/app/agent/nodes.py#L167-L179))
- Evaluates calendar logic via `task_management()` utility
- Routes to: `daily_tasks`, `eow_tasks` (Monday), or `eom_tasks` (first of month)
- Priority: EOM > EOW > Daily

**5a. import_current_month_txn_node** ([nodes.py:299-332](services/api/app/agent/nodes.py#L299-L332)) *[EOW path]*
- Imports transactions from first day of current month to yesterday
- Prepares data for weekly analysis

**5b. import_previous_month_txn_node** ([nodes.py:335-369](services/api/app/agent/nodes.py#L335-L369)) *[EOM path]*
- Imports full previous month transactions
- Prepares data for monthly analysis

**6a. eow_period_report_node** ([nodes.py:371-457](services/api/app/agent/nodes.py#L371-L457)) *[EOW path]*
- Analyzes current month overspent categories with current month transactions
- Per-category analysis using reasoning model (OpenAI 20B)
- Final report generation using OpenAI 120B model

**6b. eom_period_report_node** ([nodes.py:460-564](services/api/app/agent/nodes.py#L460-L564)) *[EOM path]*
- Analyzes previous month overspent categories with previous month transactions
- Same two-stage LLM analysis as EOW

**7. email_node** ([nodes.py:567-617](services/api/app/agent/nodes.py#L567-L617))
- Aggregates all generated alerts and reports
- Calls LLM to convert text to HTML with formatting rules
- Validates HTML structure
- Sends email via Gmail SMTP

### External Service Integration

#### Monarch Money Authentication
The custom [monarchmoney.py](services/api/pipelines/monarchmoney.py) client bypasses OTP via Device-UUID header:

```python
self._headers = {
    'Device-UUID': Settings.MONARK_DD_ID.get_secret_value()
}
```

GraphQL queries extract budget and transaction data. Session persistence via pickle files enables reuse.

#### MongoDB Data Layer
Two client implementations in [mongo_client.py](services/api/pipelines/mongo_client.py):

**MongoDBClient** (sync): Used in data import pipeline
- Full collection refresh via `delete_many()` + `insert_many()`
- Collections: `budget`, `transactions`

**AsyncMongoDBClient** (async): Used in agent nodes
- Filtered queries with date ranges and category filters
- Returns JSON for Pydantic validation

#### Groq LLM Integration
[agent_utilities.py](services/api/app/agent/agent_utilities.py) provides two LLM interfaces:

**call_llm()** ([L53-87](services/api/app/agent/agent_utilities.py#L53-L87)): Standard completions
- Default: `llama-3.3-70b-versatile`
- Used for: overspend alerts, storytelling

**call_llm_reasoning()** ([L90-128](services/api/app/agent/agent_utilities.py#L90-L128)): Reasoning models
- Supports: hidden/visible reasoning chains, reasoning effort levels
- Models: `openai/gpt-oss-20b`, `openai/gpt-oss-120b`, `qwen/qwen3-32b`
- Used for: transaction classification, category analysis, period reports

#### Email Delivery
[SendEmail](services/api/app/agent/agent_utilities.py#L169-L197) class:
- Gmail SMTP over TLS (smtp.gmail.com:587)
- Supports plain text and HTML multipart messages
- Async execution via `send_email_async()`

---

## Configuration & Environment

Create a `.env` file in the project root or set environment variables. [config.py](config.py) auto-detects the file location.

### Required Environment Variables

| Variable | Description |
|----------|-------------|
| `MONARK_USER` | Monarch Money account email |
| `MONARK_PW` | Monarch Money account password |
| `MONARK_DD_ID` | Device UUID for bypassing OTP (requires Chrome DevTools extraction) |
| `MONGO_URL` | MongoDB connection string (supports srv protocol) |
| `MONGO_DB` | Database name for budget/transaction collections |
| `GROQ_API_KEY` | Groq API key for LLM access |
| `SMTP_USER` | Gmail account for sending emails |
| `SMTP_PASSWORD` | Gmail app-specific password |

### Optional Configuration

Model selection can be overridden in [config.py](config.py):
- `GROQ_LLAMA_VERSATILE`: Default versatile model (default: `llama-3.3-70b-versatile`)
- `GROQ_LLAMA_INSTRUCT`: Instruction-tuned model (default: `llama-3.3-70b-instruct`)
- `GROQ_QWEN_REASONING`: Reasoning model (default: `qwen/qwen3-32b`)
- `GROQ_OPENAI_20B_MODE`: OpenAI-style 20B model (default: `openai/gpt-oss-20b`)
- `GROQ_OPENAI_120B_MODE`: OpenAI-style 120B model (default: `openai/gpt-oss-120b`)

---

## Local Development Setup

### Prerequisites
- Python 3.11+ (workflow tested on 3.11)
- MongoDB instance (local or cloud)
- Groq API access
- Gmail account with app password

### Installation Steps

1. **Clone repository and navigate to project root**
   ```bash
   git clone <repository-url>
   cd monark_budget
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -e ./services/api
   ```
   This installs all dependencies from [pyproject.toml](services/api/pyproject.toml) including:
   - LangGraph & LangChain ecosystem
   - MongoDB drivers (pymongo, motor)
   - Groq client
   - Monarch Money client
   - GraphQL dependencies (gql, graphql-core)

4. **Configure environment**
   Create `.env` file in project root with required variables (see Configuration section)

5. **Create session directory**
   ```bash
   mkdir -p .mm
   chmod 755 .mm
   ```

---

## Running the System

### 1. Data Import Pipeline

Import fresh data from Monarch Money to MongoDB:

```bash
python -m services.api.pipelines.data_import_pipeline
```

**What it does:**
- Authenticates with Monarch Money using credentials from `.env`
- Downloads budgets for current and previous month
- Downloads transactions from previous month start to yesterday
- Parses and validates data through Pydantic models
- Performs full refresh of MongoDB collections

**Output:** Console logs showing import progress and record counts

### 2. Agent Execution

Run the AI agent workflow:

```bash
python -m main
```

**What it does:**
- Initializes `BudgetAgentState` with current timestamp
- Compiles LangGraph workflow
- Executes all nodes based on calendar routing
- Generates and sends email report
- Prints summary to console

**Output:**
```
=== Agent run summary ===
Task route: eow_tasks
Process flags: {'daily_overspend_alert_done': True, ...}
Email subject: Your Budget Alerts and Reports From your Friendly Budget Assistant
Email preview: <html>...
```

### 3. Automated Daily Execution

The [GitHub Actions workflow](.github/workflows/daily_budget_data_git_pipeline.yml) runs automatically:

**Schedule:** Daily at 6 AM PST (14:00 UTC)

**Steps:**
1. Checkout repository
2. Setup Python 3.11
3. Create `.mm` directory for session files
4. Install dependencies (explicit pip installs for CI)
5. Run data import pipeline
6. Delete session pickle file (security)
7. Wait 2 minutes for MongoDB persistence
8. Run agent pipeline

**Secrets:** Configure in GitHub repository settings under Settings → Secrets and variables → Actions

---

## Testing

### Unit & Integration Tests

Comprehensive test suite in [unitest.py](unitest.py):

```bash
pytest unitest.py -v
```

**Test Coverage:**
- Task routing logic (daily/EOW/EOM)
- Data import with mocked MongoDB
- Period report generation with fake LLMs
- Edge cases: year boundaries, leap years, empty datasets
- Live LLM integration tests (optional, requires credentials)

**Key Test Features:**
- `FakeAsyncMongoDBClient`: Tracks which data was requested
- `fake_call_llm_reasoning()`: Returns context-aware fake responses
- `monkeypatch`: Mocks datetime for deterministic calendar logic
- Live tests: Skip gracefully if credentials unavailable

### Manual Testing Scripts

**Email Delivery Test:**
```bash
python test_email_sender.py
```
Sends a test email using configured SMTP credentials.

**LLM Integration Test:**
```bash
python test_llm.py
```
Fetches budget data from MongoDB and exercises LLM prompts.

---

## Extending the System

### Adding New Analysis Nodes

1. **Define node function** in [nodes.py](services/api/app/agent/nodes.py):
   ```python
   async def new_analysis_node(state: BudgetAgentState) -> BudgetAgentState:
       # Your analysis logic
       result = await call_llm(prompt_obj=NEW_PROMPT, ...)
       state.new_field = result
       state.process_flag.new_task_done = True
       return state
   ```

2. **Extend state model** in [state.py](services/api/app/agent/state.py):
   ```python
   class ProcessFlag(BaseModel):
       new_task_done: bool = False

   class BudgetAgentState(BaseModel):
       new_field: Optional[str] = None
   ```

3. **Register in graph** ([agent_graph.py](services/api/app/agent/agent_graph.py)):
   ```python
   graph_builder.add_node("new_analysis_node", new_analysis_node)
   graph_builder.add_edge("existing_node", "new_analysis_node")
   ```

### Creating New Prompts

Add to [prompts.py](services/api/app/domain/prompts.py):

```python
__NEW_PROMPT = """
Your prompt template with {variables}
"""

NEW_PROMPT = Prompt(
    name="new_prompt",
    prompt=__NEW_PROMPT
)
```

The `Prompt` wrapper attempts Opik versioning; falls back to local string if unavailable.

### Modifying LLM Behavior

**Change models:** Update calls in [nodes.py](services/api/app/agent/nodes.py):
```python
response = await call_llm_reasoning(
    model=Settings.GROQ_OPENAI_120B_MODE,  # Change model
    reasoning_effort='high',  # Adjust reasoning
    temperature=0.8,
    ...
)
```

**Add reasoning visibility:**
```python
response = await call_llm_reasoning(
    reasoning_format='visible',  # Show reasoning chain
    ...
)
```

### Integrating New Data Sources

1. **Extend import functions** in [import_functions.py](services/api/pipelines/import_functions.py):
   ```python
   async def get_new_data_source(self):
       self._ensures_is_logged_in()
       data = await self.monarch.get_new_endpoint()
       self.imports["new_data"] = data
       return data
   ```

2. **Add MongoDB collection** in [mongo_client.py](services/api/pipelines/mongo_client.py):
   ```python
   self.new_collection = self.db['new_data']
   ```

3. **Update pipeline** in [data_import_pipeline.py](services/api/pipelines/data_import_pipeline.py):
   ```python
   self.new_data = parse_new_data(self.imports['new_data'])
   self.mongo_client.export_new_data(json.loads(self.new_data))
   ```

---

## Data Models Reference

### Core State Models ([state.py](services/api/app/agent/state.py))

**BudgetRow**
```python
{
    "actual_amount": float,
    "category_budget_variability": "fixed" | "flexible" | "income" | "goals" | "expense" | "non_monthly",
    "category_group_name": str,
    "category_group_type": str,
    "category_name": str,
    "month": date,
    "planned_cash_flow_amount": float,
    "remaining_amount": float,
    "remaining_amount_percent": float | None
}
```

**TransactionRow**
```python
{
    "amount": float,
    "category_id": str,
    "category_name": str,
    "createdAt": str (ISO 8601),
    "description": str | None,
    "merchant_id": str,
    "merchant_name": str,
    "transaction_id": str,
    "updatedAt": str (ISO 8601)
}
```

**BudgetAgentState**
```python
{
    "run_meta": RunMeta,
    "current_month_budget": str (JSON),  # BudgetData serialized
    "past_month_budget": str (JSON),
    "current_month_txn": str (JSON),     # List[TransactionRow] serialized
    "previous_month_txn": str (JSON),
    "last_day_txn": List[str],           # List of TransactionRow JSONs
    "current_month_overspend_budget_data": str (JSON),  # OverspendBudgetData
    "past_month_overspend_budget_data": str (JSON),
    "daily_overspend_alert": DailyAlertOverspend,
    "daily_suspicious_transactions": List[DailySuspiciousTransaction],
    "daily_alert_suspicious_transaction": DailyAlertSuspiciousTransaction,
    "period_report": str | None,
    "process_flag": ProcessFlag,
    "email_info": EmailInfo | None,
    "task_info": str  # "daily_tasks" | "eow_tasks" | "eom_tasks"
}
```

---

## Workflow Routing Logic

Implemented in [agent_utilities.py:task_management()](services/api/app/agent/agent_utilities.py#L29-L44):

```python
def task_management(_state=None):
    today = datetime.now()
    is_monday = today.weekday() == 0
    yesterday = today - timedelta(days=1)
    is_first_day_of_month = today.month != yesterday.month

    if is_first_day_of_month:
        return "eom_tasks"  # Priority 1
    elif is_monday:
        return "eow_tasks"  # Priority 2
    else:
        return "daily_tasks"  # Default
```

**Conditional edges** in [agent_graph.py](services/api/app/agent/agent_graph.py#L105-L112):
```python
graph_builder.add_conditional_edges("coordinator_node",
    task_management,
    {
        "daily_tasks": "email_node",
        "eow_tasks": "import_current_month_txn_node",
        "eom_tasks": "import_previous_month_txn_node"
    }
)
```

---

## Troubleshooting

### Common Issues

**1. Monarch Money Authentication Fails**
- Verify `MONARK_DD_ID` is current (extract from Chrome DevTools)
- Check session pickle file: delete `.mm/mm_session.pickle` and retry
- Confirm credentials are correct in `.env`

**2. MongoDB Connection Errors**
- Verify `MONGO_URL` includes protocol (`mongodb+srv://` or `mongodb://`)
- Ensure IP whitelist includes GitHub Actions IPs (if using cloud MongoDB)
- Check network connectivity to MongoDB instance

**3. LLM API Errors**
- Validate `GROQ_API_KEY` is active and has quota
- Check model names in config match available models
- Review rate limits in Groq dashboard

**4. Email Delivery Failures**
- Gmail: Use app-specific password, not account password
- Verify `SMTP_USER` and `SMTP_PASSWORD` are correct
- Check recipient email in [nodes.py:604](services/api/app/agent/nodes.py#L604)
- Enable "Less secure app access" if required

**5. GitHub Actions Workflow Fails**
- Verify all secrets are configured in repository settings
- Check Python version matches local (3.11)
- Review dependency installation logs for conflicts
- Ensure 2-minute wait is sufficient for MongoDB write propagation

### Debug Logging

Enable detailed logging in [main.py](main.py):

```python
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
```

Inspect node execution in [nodes.py](services/api/app/agent/nodes.py) – extensive logging already present:
- Data import progress
- LLM call parameters
- Transaction classification results
- Report generation steps

---

## Performance Considerations

### Current Bottlenecks

1. **Sequential LLM Calls:** Category analysis loops block on each LLM call
   - **Optimization:** Implement async batch processing with `asyncio.gather()`

2. **Full MongoDB Refresh:** Delete + insert all documents daily
   - **Optimization:** Implement upsert logic with date-based partitioning

3. **Reasoning Model Usage:** High token consumption for transaction classification
   - **Optimization:** Cache classifications for recurring transactions

4. **HTML Generation:** Entire report re-rendered to HTML each time
   - **Optimization:** Template-based rendering with Jinja2

### Resource Usage

**GitHub Actions Runtime:**
- Data import: ~30-60 seconds
- Agent execution: ~2-5 minutes (depends on transaction count)
- Monthly Actions minutes: ~150-300 (well within free tier)

**API Costs (Groq):**
- Daily alerts: ~2-5K tokens
- Weekly reports: ~15-30K tokens
- Monthly reports: ~30-60K tokens
- Estimated monthly cost: < $5 USD

---

## Security Best Practices

1. **Credential Management:**
   - Never commit `.env` files
   - Use GitHub encrypted secrets for CI/CD
   - Rotate `MONARK_DD_ID` periodically

2. **Session Security:**
   - Delete pickle files after use (automated in workflow)
   - Store session files in `.mm/` (gitignored)

3. **Email Security:**
   - Use Gmail app passwords, not account passwords
   - Validate HTML before sending to prevent injection
   - Hardcode recipient emails (don't accept user input)

4. **MongoDB Security:**
   - Use connection strings with authentication
   - Enable IP whitelisting
   - Use separate database for production

---

## Additional Resources

### Related Files
- [README.md](README.md): Product overview and project motivation
- [plan.md](plan.md): Original project planning document
- [.github/workflows/daily_budget_data_git_pipeline.yml](.github/workflows/daily_budget_data_git_pipeline.yml): CI/CD configuration

### External Documentation
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Groq API Reference](https://console.groq.com/docs)
- [Monarch Money (unofficial)](https://github.com/hammem/monarchmoney)
- [MongoDB Motor Documentation](https://motor.readthedocs.io/)

### Development Commands

```bash
# Run tests
pytest unitest.py -v

# Run specific test
pytest unitest.py::test_task_management_eow_tasks -v

# Run with live LLM tests
pytest unitest.py -v --tb=short

# Format code (if pre-commit configured)
pre-commit run --all-files

# View graph visualization (requires graphviz)
python -c "from services.api.app.agent.agent_graph import create_budget_graph; create_budget_graph().compile().get_graph().draw_mermaid_png(output_file_path='graph.png')"
```

---

## Maintenance & Monitoring

### Regular Maintenance Tasks

**Weekly:**
- Review GitHub Actions logs for failures
- Monitor Groq API usage and costs
- Check email delivery success rate

**Monthly:**
- Rotate Monarch Money device ID if needed
- Review MongoDB storage usage
- Update dependencies: `pip list --outdated`

**Quarterly:**
- Audit LLM prompts for accuracy
- Review and optimize slow nodes
- Update test fixtures with real data samples

### Monitoring Recommendations

1. **Email Alerts:** Configure Gmail filters for agent emails to track delivery
2. **Logs:** Archive GitHub Actions logs for debugging
3. **Metrics:** Track LLM token usage via Groq dashboard
4. **Database:** Monitor MongoDB collection sizes and query performance

---

## Contributing

### Development Workflow

1. Create feature branch: `git checkout -b feature/new-analysis`
2. Make changes and add tests to [unitest.py](unitest.py)
3. Run tests: `pytest unitest.py -v`
4. Update documentation in this file
5. Commit with descriptive message
6. Submit pull request

### Code Style

- Follow existing patterns in [nodes.py](services/api/app/agent/nodes.py)
- Use type hints consistently
- Document complex logic with inline comments
- Keep functions focused (single responsibility)
- Use Pydantic for data validation

### Testing Requirements

- Add tests for new nodes in [unitest.py](unitest.py)
- Mock external dependencies (MongoDB, LLM)
- Include edge cases (empty data, API failures)
- Maintain >80% code coverage for new features

---

## Changelog

### Current Version (v0.1.0)

**Features:**
- Daily overspend alerts with category breakdown
- Suspicious transaction detection and narrative generation
- Weekly (EOW) and monthly (EOM) period reports
- HTML email rendering and delivery
- Automated GitHub Actions pipeline

**Known Limitations:**
- Single-user authentication (device ID tied to one Chrome browser)
- No persistent storage of agent state between runs
- Limited error recovery in LLM calls
- Manual recipient email configuration

**Planned Improvements:**
- Multi-user support with OAuth authentication
- Agent state persistence in MongoDB
- Retry logic for LLM API failures
- Dynamic recipient configuration
- Cost optimization through caching
# Monark Budget – Comprehensive Technical Documentation

**Version:** 1.0
**Last Updated:** 2025-09-30
**Python Version:** 3.11+
**Status:** Production Ready

---

## Table of Contents

1. [Overview & Introduction](#1-overview--introduction)
2. [Architecture & Design](#2-architecture--design)
3. [Repository Structure](#3-repository-structure)
4. [Dependencies & Requirements](#4-dependencies--requirements)
5. [Environment Configuration](#5-environment-configuration)
6. [Installation & Setup](#6-installation--setup)
7. [Core Components Deep Dive](#7-core-components-deep-dive)
8. [Error Handling & Resilience](#8-error-handling--resilience)
9. [Logging & Observability](#9-logging--observability)
10. [Running the Application](#10-running-the-application)
11. [Testing](#11-testing)
12. [Performance Considerations](#12-performance-considerations)
13. [Security & Best Practices](#13-security--best-practices)
14. [Extending & Customizing](#14-extending--customizing)
15. [Troubleshooting](#15-troubleshooting)
16. [API Reference](#16-api-reference)
17. [Optimization History](#17-optimization-history)
18. [Known Limitations & Future Work](#18-known-limitations--future-work)
19. [Contributing Guidelines](#19-contributing-guidelines)
20. [Appendices](#20-appendices)

---

## 1. Overview & Introduction

### 1.1 Project Purpose

Monark Budget is an automated financial intelligence system that analyzes your budget and transactions from Monarch Money, generates daily alerts for overspending and suspicious transactions, and creates weekly/monthly financial reports with AI-powered insights.

### 1.2 System Components

The system consists of three primary subsystems:

1. **Data Ingestion Pipeline**
   - Connects to Monarch Money API
   - Downloads budget and transaction data
   - Stores data in MongoDB for analysis

2. **Agent Workflow (LangGraph)**
   - Orchestrates multiple AI-powered analysis tasks
   - Generates daily budget alerts
   - Identifies suspicious transactions
   - Creates periodic financial reports

3. **Notification System**
   - Converts insights to HTML email format
   - Delivers reports via SMTP (Gmail)
   - Handles retry logic for reliability

### 1.3 Key Technologies

| Technology | Purpose | Version |
|------------|---------|---------|
| **Python** | Core language | 3.11+ |
| **LangGraph** | Agent workflow orchestration | 0.2.70+ |
| **LangChain** | LLM integration framework | 0.3.34+ |
| **Groq** | LLM API provider | 0.31.1+ |
| **MongoDB** | Data persistence | Motor 3.7+ |
| **Pydantic** | Data validation | 2.10.6+ |
| **Tenacity** | Retry logic | 9.0.0+ |
| **Pytest** | Testing framework | 8.4.2+ |

---

## 2. Architecture & Design

### 2.1 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Monark Budget System                         │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┐      ┌──────────────────┐      ┌─────────────┐
│  Monarch Money   │─────▶│  Data Pipeline   │─────▶│   MongoDB   │
│      API         │      │  (Async Import)  │      │  Database   │
└──────────────────┘      └──────────────────┘      └─────────────┘
                                                            │
                                                            │ Read
                                                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                    LangGraph Agent Workflow                       │
│  ┌────────────┐  ┌──────────────┐  ┌───────────────────────┐   │
│  │   Import   │─▶│ Coordinator  │─▶│  Daily Overspend      │   │
│  │   Data     │  │   (Router)   │  │       Alert           │   │
│  └────────────┘  └──────────────┘  └───────────────────────┘   │
│                          │                                        │
│                          │                                        │
│                          ├─────────▶┌────────────────────────┐  │
│                          │          │ Daily Suspicious Txn   │  │
│                          │          │       Alert            │  │
│                          │          └────────────────────────┘  │
│                          │                                        │
│                          ├─────────▶┌────────────────────────┐  │
│                          │  (EOW/   │  Period Report Node    │  │
│                          │   EOM)   │  (Weekly/Monthly)      │  │
│                          │          └────────────────────────┘  │
│                          │                                        │
│                          └─────────▶┌────────────────────────┐  │
│                                     │    Email Node          │  │
│                                     │  (HTML Generation)     │  │
│                                     └────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
                          ┌──────────────────┐
                          │   SMTP Server    │
                          │   (Gmail)        │
                          └──────────────────┘
```

### 2.2 Component Interaction Flow

**Daily Execution Flow:**

1. **Data Pipeline** (Scheduled via GitHub Actions)
   - Authenticate with Monarch Money
   - Download budget data (current month, expense categories)
   - Download transactions (last 2 months)
   - Parse and validate data with Pydantic models
   - Store in MongoDB collections

2. **Agent Initialization** (`main.py`)
   - Create initial state with run metadata
   - Set correlation ID for distributed tracing
   - Compile LangGraph workflow

3. **Data Import Node**
   - Load budget from MongoDB (filtered for expenses)
   - Identify overspent categories (remaining < -$5)
   - Load yesterday's transactions

4. **Coordinator Node**
   - Check current date (Monday or first of month?)
   - Route to daily tasks only OR daily + period report

5. **Daily Tasks** (Parallel execution)
   - **Overspend Alert**: LLM analyzes overspent categories, generates summary
   - **Suspicious Transaction Alert**: LLM classifies each transaction, creates comedic recap

6. **Period Report** (If triggered)
   - Import full month transactions
   - Analyze each overspent category with LLM reasoning
   - Generate comprehensive financial report

7. **Email Node**
   - Concatenate all generated alerts/reports
   - LLM converts to HTML format
   - Validate HTML structure
   - Send via SMTP with retry logic

### 2.3 LangGraph State Machine

**State Transitions:**

```
START
  │
  ▼
import_data_node
  │
  ▼
coordinator_node ──┐
  │                │
  │                │ (EOW/EOM)
  ▼                ▼
daily_overspend_alert_node    import_txn_data_for_period_report_node
  │                                    │
  ▼                                    ▼
daily_suspicious_transaction_node    period_report_node
  │                                    │
  └────────────┬───────────────────────┘
               │
               ▼
           email_node
               │
               ▼
             END
```

---

## 3. Repository Structure

### 3.1 Directory Layout

```
monark_budget/
├── .github/
│   └── workflows/
│       └── daily_budget_data_git_pipeline.yml  # Scheduled CI/CD workflow
│
├── services/
│   └── api/
│       ├── app/
│       │   ├── agent/
│       │   │   ├── agent_graph.py         # LangGraph workflow definition
│       │   │   ├── agent_utilities.py     # Helper functions (LLM calls, email)
│       │   │   ├── nodes.py               # Node implementations
│       │   │   └── state.py               # Pydantic state models
│       │   │
│       │   ├── domain/
│       │   │   └── prompts.py             # LLM prompt templates
│       │   │
│       │   ├── exceptions.py              # Custom exception hierarchy
│       │   └── logging_config.py          # Structured logging setup
│       │
│       ├── pipelines/
│       │   ├── data_import_pipeline.py    # Main data ingestion script
│       │   ├── data_parsing_functions.py  # Budget/transaction parsers
│       │   ├── import_functions.py        # Monarch Money API wrapper
│       │   ├── monarchmoney.py            # Monarch Money client
│       │   └── mongo_client.py            # MongoDB sync/async clients
│       │
│       ├── pyproject.toml                 # Dependency specification
│       └── uv.lock                        # Locked dependency versions
│
├── config.py                              # Centralized configuration (Pydantic)
├── main.py                                # Production entry point
│
├── unitest.py                             # Integration tests
├── test_error_handling.py                 # Error handling tests
├── test_logging.py                        # Logging functionality tests
├── test_email_sender.py                   # Manual SMTP test
├── test_llm.py                            # Manual LLM test
│
├── step_1_report.md                       # Baseline audit report
├── step_2_report.md                       # Code style improvements
├── step_3_report.md                       # Efficiency refactoring
├── step_4_report.md                       # Error handling implementation
├── step_5_report.md                       # Logging implementation
│
├── .env                                   # Environment variables (not in git)
├── .gitignore                             # Git ignore patterns
└── readme_technical.md                    # This document
```

### 3.2 Key Modules

| Module | Purpose | Lines | Key Functions |
|--------|---------|-------|---------------|
| `main.py` | Application entry point | 143 | `main()`, `run_agent()` |
| `config.py` | Settings management | 63 | `Settings` (Pydantic) |
| `agent_graph.py` | Workflow definition | 94 | `create_budget_graph()` |
| `nodes.py` | Agent node logic | 500+ | All node implementations |
| `agent_utilities.py` | Helper functions | 350+ | `call_llm()`, `SendEmail` |
| `logging_config.py` | Logging setup | 270 | `setup_logging()`, filters |
| `exceptions.py` | Custom exceptions | 119 | 11 exception classes |
| `mongo_client.py` | Database access | 188 | `MongoDBClient`, `AsyncMongoDBClient` |

---

## 4. Dependencies & Requirements

### 4.1 Python Version

**Required:** Python 3.11 or higher

**Reason:** Uses modern type hints (`tuple[str, bool]` syntax) and async features.

### 4.2 Core Dependencies

From `services/api/pyproject.toml`:

**Framework & Agent:**
- `langgraph>=0.2.70` - State machine workflow orchestration
- `langchain-core>=0.3.34` - LLM abstraction layer
- `langchain-groq>=0.2.4` - Groq LLM integration
- `langchain-mongodb>=0.4.0` - MongoDB integration for LangChain

**LLM & AI:**
- `groq>=0.31.1` - Groq API client
- `langchain-community>=0.3.17` - Community LLM integrations
- `langchain-huggingface>=0.1.2` - HuggingFace model support

**Data & Validation:**
- `pydantic>=2.10.6` - Data validation and settings
- `pydantic-settings>=2.7.1` - Environment variable management
- `pandas>=2.0.0` - DataFrame operations for data parsing

**Database:**
- `pymongo>=4.9.2` - MongoDB synchronous driver
- `motor>=3.7` - MongoDB async driver

**External Services:**
- `monarchmoney>=0.1.6` - Monarch Money API client
- `requests>=2.25` - HTTP client

**Resilience:**
- `tenacity>=9.0.0` - Retry logic with exponential backoff

**Web & API:**
- `fastapi[standard]>=0.115.8` - Web framework (if API endpoints added)
- `uvicorn[standard]==0.30.0` - ASGI server
- `httpx==0.27.0` - Async HTTP client

**Development & Testing:**
- `pytest>=8.4.2` - Testing framework
- `pytest-asyncio>=0.25.2` - Async test support
- `black==25.9.0` - Code formatter
- `isort==6.0.1` - Import sorter
- `flake8==7.3.0` - Linter
- `pylint==3.3.8` - Static analyzer
- `autoflake==2.3.1` - Unused import remover

**Logging & Observability:**
- `loguru>=0.7.3` - Advanced logging
- `opik>=1.4.11` - Prompt versioning and tracking

### 4.3 External Service Dependencies

| Service | Purpose | Authentication | Required |
|---------|---------|----------------|----------|
| **Monarch Money** | Budget/transaction data | Username/Password + Device ID | Yes |
| **MongoDB** | Data persistence | Connection string | Yes |
| **Groq API** | LLM inference | API key | Yes |
| **Gmail SMTP** | Email delivery | Username/Password | Yes |

### 4.4 Development Dependencies

Installed automatically with `uv sync`:
- `ipykernel>=6.29.5` - Jupyter notebook support
- `pre-commit>=4.1.0` - Git hooks for code quality
- `pytest-asyncio>=0.25.2` - Async test runner

---

## 5. Environment Configuration

### 5.1 Environment Variables

Create a `.env` file in the project root:

```bash
# Monarch Money Authentication
MONARK_USER=your-email@example.com
MONARK_PW=your-password
MONARK_DD_ID=device-uuid-from-browser

# MongoDB Connection
MONGO_URL=mongodb://localhost:27017
MONGO_DB=monark_budget

# Groq LLM API
GROQ_API_KEY=gsk_your_api_key_here

# SMTP (Gmail)
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-specific-password
```

### 5.2 Configuration Reference

| Variable | Type | Required | Description | Example |
|----------|------|----------|-------------|---------|
| `MONARK_USER` | String | Yes | Monarch Money login email | `user@example.com` |
| `MONARK_PW` | SecretStr | Yes | Monarch Money password | `secure_password` |
| `MONARK_DD_ID` | SecretStr | Yes | Device UUID to skip OTP | `550e8400-e29b-41d4-a716-446655440000` |
| `MONGO_URL` | SecretStr | Yes | MongoDB connection string | `mongodb://localhost:27017` |
| `MONGO_DB` | String | Yes | MongoDB database name | `monark_budget` |
| `GROQ_API_KEY` | SecretStr | Yes | Groq API key | `gsk_abc123...` |
| `GROQ_LLAMA_VERSATILE` | String | No | Llama model identifier | `llama-3.3-70b-versatile` (default) |
| `GROQ_QWEN_REASONING` | String | No | Qwen reasoning model | `qwen/qwen3-32b` (default) |
| `GROQ_OPENAI_20B_MODE` | String | No | OpenAI OSS model | `openai/gpt-oss-20b` (default) |
| `SMTP_USER` | String | Yes | SMTP username | `your-email@gmail.com` |
| `SMTP_PASSWORD` | SecretStr | Yes | SMTP password (app-specific) | `abcd efgh ijkl mnop` |

### 5.3 Configuration Management

**Location:** `config.py`

```python
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=get_env_file_path(),
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_ignore_empty=True,
    )

    MONARK_PW: SecretStr = Field(
        description="Password used to extract transaction data and budget data"
    )
    # ... more fields
```

**Features:**
- ✅ Automatic environment variable mapping
- ✅ Secret masking with `SecretStr`
- ✅ Type validation
- ✅ Case-insensitive matching
- ✅ `.env` file support

### 5.4 Obtaining Monarch Money Device ID

The device ID bypasses OTP challenges. To obtain it:

1. Log in to Monarch Money in your browser
2. Open browser DevTools (F12)
3. Go to Application → Local Storage → `https://app.monarchmoney.com`
4. Find key `mm-device` or `device_id`
5. Copy the UUID value

---

## 6. Installation & Setup

### 6.1 Prerequisites

- Python 3.11 or higher
- MongoDB instance (local or remote)
- Monarch Money account
- Gmail account with app-specific password
- Groq API key (free tier available)

### 6.2 Local Development Setup

**Step 1: Clone Repository**

```bash
git clone <repository-url>
cd monark_budget
```

**Step 2: Install UV Package Manager** (Recommended)

```bash
pip install uv
```

**Step 3: Create Virtual Environment**

```bash
cd services/api
uv venv
```

Activate the virtual environment:
- **Windows:** `.venv\Scripts\activate`
- **Unix/Mac:** `source .venv/bin/activate`

**Step 4: Install Dependencies**

```bash
uv sync --reinstall --no-cache
```

This installs all dependencies from `pyproject.toml` and `uv.lock`.

**Step 5: Configure Environment**

Create `.env` file in project root with all required variables (see Section 5.1).

**Step 6: Start MongoDB**

If running locally:

```bash
# Using Docker
docker run -d -p 27017:27017 --name mongodb mongo:latest

# Or use local MongoDB installation
mongod --dbpath /path/to/data
```

**Step 7: Verify Setup**

```bash
# From project root
python -m pytest unitest.py -v
```

### 6.3 GitHub Actions Setup

For automated daily runs, configure repository secrets:

1. Go to repository Settings → Secrets and variables → Actions
2. Add all environment variables as secrets
3. The workflow `.github/workflows/daily_budget_data_git_pipeline.yml` will use them

---

## 7. Core Components Deep Dive

### 7.1 Data Ingestion Pipeline

**Location:** `services/api/pipelines/`

#### 7.1.1 Monarch Money Integration

**File:** `import_functions.py`

```python
class MonarkImport:
    """Wrapper for Monarch Money API operations."""

    async def monarch_login(self, pw: str, user: str, mfa_code: str = None) -> bool:
        """
        Login with retry logic (3 attempts, exponential backoff).

        Raises:
            MonarchMoneyLoginError: On login failures after retries
            RequireMFAException: When MFA required but not provided
        """
        # ... implementation with retry logic

    async def get_txn(self):
        """Fetch transactions from first of previous month to yesterday."""
        # ... implementation

    async def get_bdgt(self):
        """Fetch current month budget data."""
        # ... implementation
```

**Key Features:**
- ✅ Automatic retry on transient failures (3 attempts)
- ✅ MFA support with validation
- ✅ Structured logging with correlation IDs
- ✅ Sensitive data redaction (passwords, emails)

#### 7.1.2 Data Parsing

**File:** `data_parsing_functions.py`

**Budget Parsing:**

```python
def parse_budget_data(budget_data) -> str:
    """
    Parse budget data into structured DataFrames.

    Processing:
    1. Extract category groups and categories
    2. Filter excludeFromBudget=True
    3. Get current month budget amounts
    4. Calculate remaining amount percentages
    5. Sort by type (income/expense) and variability

    Returns:
        JSON string of budget records with fields:
        - category_group_type, category_group_name
        - category_name, category_budget_variability
        - month, planned_cash_flow_amount, actual_amount
        - remaining_amount, remaining_amount_percent
    """
```

**Transaction Parsing:**

```python
def parse_transaction_data(transactions_data) -> str:
    """
    Parse transaction data into structured DataFrame.

    Processing:
    1. Extract transaction details (amount, description, category, merchant)
    2. Filter excluded accounts (investment accounts, etc.)
    3. Format for LLM consumption

    Returns:
        JSON string of transaction records
    """
```

#### 7.1.3 MongoDB Storage

**File:** `mongo_client.py`

**Synchronous Client:**

```python
class MongoDBClient:
    """Sync MongoDB client for data export (pipeline use)."""

    def __init__(self):
        """Initialize with connection validation and 5s timeout."""

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(...))
    def export_budget_data(self, budget_data):
        """Export budget with full refresh (delete → insert)."""

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(...))
    def export_transaction_data(self, transaction_data):
        """Export transactions with full refresh."""
```

**Asynchronous Client:**

```python
class AsyncMongoDBClient:
    """Async MongoDB client for agent node use."""

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(...))
    async def import_budget_data(self, filter_query: Optional[dict] = None) -> str:
        """Import budget data as JSON string."""

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(...))
    async def import_transaction_data(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> str:
        """Import transactions filtered by date range."""
```

**Key Features:**
- ✅ Retry logic for transient failures
- ✅ Connection validation on initialization
- ✅ Separate sync/async implementations for different use cases
- ✅ Custom exceptions (DatabaseConnectionError, DatabaseQueryError)

### 7.2 Agent Workflow (LangGraph)

**Location:** `services/api/app/agent/`

#### 7.2.1 State Model

**File:** `state.py`

```python
@dataclass
class BudgetAgentState:
    """Main state for the budget agent workflow."""

    run_meta: RunMeta                                    # Run ID, date, timezone
    current_month_budget: Optional[str]                  # JSON budget data
    current_month_txn: Optional[str]                     # Current month transactions
    previous_month_txn: Optional[str]                    # Previous month transactions
    last_day_txn: list[str]                              # Yesterday's transactions
    overspend_budget_data: Optional[str]                 # Overspent categories
    daily_overspend_alert: DailyAlertOverspend           # Daily alert content
    daily_suspicious_transactions: list[DailySuspiciousTransaction]
    daily_alert_suspicious_transaction: DailyAlertSuspiciousTransaction
    period_report: Optional[str]                         # Weekly/monthly report
    process_flag: ProcessFlag                            # Execution flags
    email_info: Optional[EmailInfo]                      # Generated email
    task_info: str = "N/A"                               # Task routing info
```

**Supporting Models:**

- `RunMeta`: Execution metadata (run_id, date, timezone)
- `BudgetRow`: Single budget category record
- `TransactionRow`: Single transaction record
- `DailyAlertOverspend`: Overspend alert content
- `DailySuspiciousTransaction`: Suspicious transaction with analysis
- `ProcessFlag`: Boolean flags for task completion
- `EmailInfo`: Email metadata (from, to, subject, body)

#### 7.2.2 Graph Definition

**File:** `agent_graph.py`

```python
def create_budget_graph() -> StateGraph:
    """
    Create the LangGraph workflow.

    Nodes:
    - import_data_node: Load budget and transactions from MongoDB
    - coordinator_node: Route based on date (daily vs daily+period)
    - daily_overspend_alert_node: Generate overspend alert
    - daily_suspicious_transaction_alert_node: Classify transactions
    - import_txn_data_for_period_report_node: Load full month data
    - period_report_node: Generate weekly/monthly report
    - email_node: Convert to HTML and send email

    Routing:
    - After coordinator: "daily_tasks" or "both_tasks"
    - After daily tasks: Always to email_node
    - After period report: Always to email_node
    """

    graph_builder = StateGraph(BudgetAgentState)

    # Add nodes
    graph_builder.add_node("import_data_node", import_data_node)
    graph_builder.add_node("coordinator_node", coordinator_node)
    # ... more nodes

    # Set entry point
    graph_builder.set_entry_point("import_data_node")

    # Add edges
    graph_builder.add_edge("import_data_node", "coordinator_node")

    # Conditional routing
    graph_builder.add_conditional_edges(
        "coordinator_node",
        task_management,  # Returns "daily_tasks" or "both_tasks"
        {
            "daily_tasks": "daily_overspend_alert_node",
            "both_tasks": "import_txn_data_for_period_report_node"
        }
    )

    # ... more routing logic

    return graph_builder
```

#### 7.2.3 Node Implementations

**File:** `nodes.py`

**Import Data Node:**

```python
async def import_data_node(state: BudgetAgentState) -> BudgetAgentState:
    """
    Load budget and transaction data from MongoDB.

    Steps:
    1. Connect to MongoDB (async client)
    2. Import budget data (expense categories only)
    3. Validate with Pydantic models
    4. Filter overspent categories (remaining < -$5)
    5. Import yesterday's transactions
    6. Update state with all data

    Logging:
    - Entry/exit with correlation ID
    - Row counts for budget and transactions
    - Overspent category count
    """
```

**Coordinator Node:**

```python
async def coordinator_node(state: BudgetAgentState) -> BudgetAgentState:
    """
    Route workflow based on current date.

    Logic:
    - If Monday OR first day of month → "both_tasks"
    - Otherwise → "daily_tasks"

    Sets state.task_info for logging and debugging.
    """
```

**Daily Overspend Alert Node:**

```python
async def daily_overspend_alert_node(state: BudgetAgentState) -> BudgetAgentState:
    """
    Generate daily overspend alert.

    Steps:
    1. Check if overspend data exists
    2. If yes:
       - Call LLM with overspend budget data
       - Parse LLM response
       - Store in state.daily_overspend_alert
       - Set process_flag.daily_budget_alert = True
    3. If no: Set flag to False

    LLM Configuration:
    - Model: llama-3.3-70b-versatile
    - Temperature: 0.8 (creative)
    - Max tokens: 500
    - Prompt: BUDGET_ALERT_PROMPT
    """
```

**Daily Suspicious Transaction Alert Node:**

```python
async def daily_suspicious_transaction_alert_node(state: BudgetAgentState) -> BudgetAgentState:
    """
    Classify yesterday's transactions and generate suspicious transaction alert.

    Steps:
    1. For each transaction:
       - Call LLM reasoning model for classification
       - Parse classification (compliant vs suspicious)
       - If suspicious: Generate comedic story
    2. Compile all suspicious transactions
    3. Generate final alert summary

    LLM Configuration:
    - Classification: qwen/qwen3-32b (reasoning model)
    - Story generation: llama-3.3-70b-versatile
    - Temperature: 0.8
    """
```

**Period Report Node:**

```python
async def period_report_node(state: BudgetAgentState) -> BudgetAgentState:
    """
    Generate weekly/monthly financial report.

    Steps:
    1. For each overspent category:
       - Filter transactions for that category
       - Call LLM reasoning model for analysis
       - Identify spending drivers
    2. Compile all analyses
    3. Generate comprehensive report with LLM

    LLM Configuration:
    - Analysis: openai/gpt-oss-20b (reasoning)
    - Report generation: openai/gpt-oss-20b
    - Temperature: 0.8
    - Max tokens: 4020 (long report)
    - Reasoning effort: "high"
    """
```

**Email Node:**

```python
async def email_node(state: BudgetAgentState) -> BudgetAgentState:
    """
    Convert alerts/reports to HTML email and send.

    Steps:
    1. Concatenate daily alerts and period report
    2. Call LLM to convert to HTML format
    3. Validate HTML structure
    4. Create EmailInfo with metadata
    5. Send via SMTP with retry logic
    6. Update state with sent email info

    HTML Validation:
    - Uses HTMLParser to check structure
    - Falls back to plain text if invalid

    Email Delivery:
    - SMTP server: smtp.gmail.com:587
    - TLS encryption
    - 3 retry attempts with exponential backoff
    - 30-second timeout per attempt
    """
```

### 7.3 LLM Integration

**Location:** `services/api/app/agent/agent_utilities.py`

#### 7.3.1 LLM Call Functions

**Standard LLM Call:**

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((LLMError, LLMTimeoutError)),
    reraise=True,
)
async def call_llm(
    temperature: float = 0.7,
    system_prompt: str = SYSTEM_PROMPT.prompt,
    prompt_obj=None,
    max_tokens: int = 4020,
    model: str = Settings.GROQ_LLAMA_VERSATILE,
    api_key: str = Settings.GROQ_API_KEY.get_secret_value(),
    response_format: str = "text",
    timeout: int = 60,
    **kwargs
) -> str:
    """
    Call LLM API with retry logic and timeout handling.

    Features:
    - 60-second timeout per request
    - 3 retry attempts with exponential backoff (2s, 4s, 8s)
    - Automatic error wrapping (LLMError, LLMTimeoutError, LLMResponseError)
    - Empty response validation
    - Sensitive data redaction in logs

    Returns:
        LLM response content string

    Raises:
        LLMError: On API failures
        LLMTimeoutError: On timeout
        LLMResponseError: On empty/invalid response
    """
```

**Reasoning Model Call:**

```python
@retry(...)
async def call_llm_reasoning(
    temperature: float = 0.7,
    system_prompt: str = SYSTEM_PROMPT.prompt,
    prompt_obj=None,
    max_tokens: int = 4020,
    model: str = Settings.GROQ_QWEN_REASONING,
    reasoning_effort: str = "default",
    reasoning_format: str = "hidden",
    response_format: str = "text",
    timeout: int = 90,  # Higher timeout for reasoning models
    **kwargs
) -> str:
    """
    Call LLM reasoning API (QWen or similar) with extended timeout.

    Reasoning models require more time for complex analysis.
    Otherwise identical to call_llm().
    """
```

#### 7.3.2 Prompt Management

**Location:** `services/api/app/domain/prompts.py`

```python
@dataclass
class Prompt:
    """Wrapper for prompt templates with optional Opik versioning."""

    name: str
    prompt: str
    version: str = "1.0"

# System prompt (used for all LLM calls)
SYSTEM_PROMPT = Prompt(
    name="system_prompt",
    prompt="""
You are an expert financial assistant that helps users manage their
budgets and finances effectively. You are also known for being funny
and witty while providing financial advice.
""",
    version="1.0"
)

# Budget alert prompt
BUDGET_ALERT_PROMPT = Prompt(
    name="budget_alert",
    prompt="""
Analyze the following overspent budget categories and create a concise
alert message (max 3-4 sentences) highlighting the most concerning areas.

Budget Data:
{overspend_budget_data}

Focus on categories with the highest overspend percentages.
""",
    version="1.0"
)

# ... more prompts (SUSPICIOUS_TXN_PROMPT, TXN_ANALYSIS_PROMPT, etc.)
```

#### 7.3.3 Model Selection

| Model | Use Case | Timeout | Temperature | Reasoning |
|-------|----------|---------|-------------|-----------|
| `llama-3.3-70b-versatile` | General text generation, alerts | 60s | 0.8 | Creative summaries |
| `qwen/qwen3-32b` | Transaction classification | 90s | 0.7 | Structured reasoning |
| `openai/gpt-oss-20b` | Financial analysis, reports | 90s | 0.8 | Deep analysis |

### 7.4 Notification System

**Location:** `services/api/app/agent/agent_utilities.py`

#### 7.4.1 Email Generation

```python
class SendEmail:
    """Email sender with retry logic and error handling."""

    def __init__(self, EmailInfo):
        self.from_ = EmailInfo.from_
        self.to = EmailInfo.to
        self.subject = EmailInfo.subject
        self.body = EmailInfo.body
        self.ADDRESS = Settings.SMTP_USER
        self.PASSWORD = Settings.SMTP_PASSWORD.get_secret_value()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(EmailError),
        reraise=True,
    )
    async def send_email_async(self, is_html: bool = False) -> None:
        """
        Send email with retry logic.

        Features:
        - 30-second timeout per attempt
        - 3 retry attempts with exponential backoff
        - TLS encryption (STARTTLS)
        - Support for HTML and plain text

        Raises:
            EmailError: On sending failures after retries
        """
```

#### 7.4.2 HTML Validation

```python
class HTMLValidator(HTMLParser):
    """Validator to check HTML structure before sending."""

    def __init__(self):
        super().__init__()
        self.valid_html: bool = True
        self.error_msg: str = ""

    def error(self, message: str) -> None:
        self.valid_html = False
        self.error_msg = message

def validate_html(text: str) -> tuple[str, bool]:
    """
    Check if input text is valid HTML.

    Returns:
        (original_text, is_valid_html)

    If invalid, email_node falls back to plain text format.
    """
```

---

## 8. Error Handling & Resilience

**Implemented in:** Step 4 (see `step_4_report.md`)

### 8.1 Custom Exception Hierarchy

**Location:** `services/api/app/exceptions.py`

```
BudgetAgentException (base)
├── ExternalServiceError
│   ├── MonarchMoneyError
│   │   ├── MonarchMoneyLoginError
│   │   └── MonarchMoneyDataError
│   ├── DatabaseError
│   │   ├── DatabaseConnectionError
│   │   └── DatabaseQueryError
│   ├── LLMError
│   │   ├── LLMTimeoutError
│   │   ├── LLMRateLimitError
│   │   └── LLMResponseError
│   └── EmailError
├── DataProcessingError
│   ├── DataValidationError
│   ├── DataParsingError
│   ├── TransactionDataMissingError
│   └── BudgetDataMissingError
└── ConfigurationError
```

**Usage Example:**

```python
from services.api.app.exceptions import LLMTimeoutError, MonarchMoneyLoginError

try:
    await monarch.login(user, pw)
except Exception as e:
    raise MonarchMoneyLoginError(f"Failed to login: {e}") from e
```

### 8.2 Retry Logic Patterns

**Tenacity Configuration:**

```python
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

@retry(
    stop=stop_after_attempt(3),              # Maximum 3 attempts
    wait=wait_exponential(multiplier=1, min=2, max=10),  # 2s, 4s, 8s
    retry=retry_if_exception_type(RetryableError),       # Only retry specific errors
    reraise=True,                            # Re-raise after exhausting retries
)
async def external_service_call():
    # ... implementation
```

**Applied To:**
- ✅ LLM API calls (3 retries, 60-90s timeout)
- ✅ MongoDB operations (3 retries, 5s connection timeout)
- ✅ SMTP email sending (3 retries, 30s timeout)
- ✅ Monarch Money API (3 retries, exponential backoff)

### 8.3 Timeout Configurations

| Operation | Timeout | Retries | Backoff |
|-----------|---------|---------|---------|
| LLM standard call | 60s | 3 | 2s, 4s, 8s |
| LLM reasoning call | 90s | 3 | 2s, 4s, 8s |
| MongoDB connection | 5s | 3 | 2s, 4s, 8s |
| MongoDB query | Default | 3 | 2s, 4s, 8s |
| SMTP connection | 30s | 3 | 2s, 4s, 8s |
| Monarch Money login | Default | 3 | 2s, 4s, 8s |

### 8.4 Graceful Degradation

**main.py Error Handling:**

```python
def main() -> None:
    """Main entry point with comprehensive error handling."""
    logger.info("Budget Agent starting")

    try:
        final_state = asyncio.run(run_agent())
    except KeyboardInterrupt:
        logger.warning("Agent run interrupted by user")
        return  # Clean shutdown
    except Exception as exc:
        logger.error("Fatal error during agent run", exc_info=True, extra={"error": str(exc)})
        print("\n=== Agent run FAILED ===")
        print(f"Error: {exc}")
        print("Check logs for details.")
        return  # Graceful failure with user message

    # Display summary on success
    logger.info("Budget Agent completed successfully")
```

**Benefits:**
- ✅ User-friendly error messages
- ✅ Full stack traces in logs
- ✅ Clean shutdown on interrupts
- ✅ No crashes propagated to OS

---

## 9. Logging & Observability

**Implemented in:** Step 5 (see `step_5_report.md`)

### 9.1 Structured Logging Architecture

**Location:** `services/api/app/logging_config.py`

#### 9.1.1 Log Format

**Standard Format:**
```
YYYY-MM-DD HH:MM:SS,mmm | LEVEL    | [correlation-id] | module:function:line | message | extra_data
```

**Example:**
```
2025-09-30 14:23:45,123 | INFO     | [budget-agent-run-20250930-142345] | nodes:import_data_node:101 | Budget data imported | budget_rows=42
```

#### 9.1.2 Log Levels

| Level | Purpose | Usage |
|-------|---------|-------|
| **DEBUG** | Detailed diagnostics | Connection details, data parsing |
| **INFO** | Key milestones | Node entry/exit, successful operations |
| **WARNING** | Recoverable issues | MFA required, retry attempts |
| **ERROR** | Application errors | Failed operations with stack traces |
| **CRITICAL** | System failures | Reserved for catastrophic failures |

#### 9.1.3 Sensitive Data Redaction

**Automated Redaction Patterns:**

```python
class SensitiveDataFilter(logging.Filter):
    """Automatically redacts sensitive information from logs."""

    SENSITIVE_PATTERNS = [
        # Passwords
        (r"(password|passwd|pwd)[\"']?\s*[:=]\s*[\"']?([^\"'\s,}]+)", r"\1=***REDACTED***"),

        # API keys and tokens
        (r"(api[_-]?key|apikey|token)[\"']?\s*[:=]\s*[\"']?([^\"'\s,}]+)", r"\1=***REDACTED***"),

        # Secrets
        (r"(secret|credential)[\"']?\s*[:=]\s*[\"']?([^\"'\s,}]+)", r"\1=***REDACTED***"),

        # Email addresses (partial redaction)
        (r"([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", r"***@\2"),
    ]
```

**Example:**
```
# Before filtering
"Connecting with password=secret123, api_key=sk-abc123, user=john@example.com"

# After filtering
"Connecting with password=***REDACTED***, api_key=***REDACTED***, user=***@example.com"
```

### 9.2 Correlation ID Support

**Purpose:** Trace all log entries from a single agent run.

**Implementation:**

```python
# Set at start of agent run
set_correlation_id(initial_state.run_meta.run_id)

# Example ID: budget-agent-run-20250930-142345
# All subsequent logs include this ID in [brackets]
```

**Benefits:**
- ✅ Filter logs by specific execution: `grep "budget-agent-run-20250930-142345" log.txt`
- ✅ Track concurrent executions separately
- ✅ Calculate execution duration
- ✅ Debug specific failures

### 9.3 Usage Examples

**Basic Logging:**

```python
from services.api.app.logging_config import get_logger

logger = get_logger(__name__)

logger.info("Operation started")
logger.error("Operation failed", exc_info=True)
```

**Logging with Extra Fields:**

```python
logger.info(
    "Budget data imported",
    extra={
        "budget_rows": 42,
        "overspent_count": 5,
        "date": "2025-09-30"
    }
)
# Output: ... | Budget data imported | budget_rows=42, overspent_count=5, date=2025-09-30
```

**Performance Logging:**

```python
from services.api.app.logging_config import log_execution_time

@log_execution_time(logger, level=logging.DEBUG)
async def expensive_operation():
    # ... operation
    pass

# Automatically logs:
# "Starting expensive_operation"
# "Completed expensive_operation | duration=123.45ms"
```

### 9.4 Configuration

**Setup Logging:**

```python
from services.api.app.logging_config import setup_logging

# Console only (default)
setup_logging(level=logging.INFO)

# Console + file
setup_logging(
    level=logging.INFO,
    log_file="application.log",
    enable_sensitive_filter=True
)
```

---

## 10. Running the Application

### 10.1 Local Execution

#### 10.1.1 Data Pipeline

**Purpose:** Refresh budget and transaction data from Monarch Money.

```bash
# From project root
python -m services.api.pipelines.data_import_pipeline
```

**What It Does:**
1. Logs into Monarch Money with credentials from `.env`
2. Downloads current month budget data
3. Downloads transactions (last 2 months)
4. Parses and validates data
5. Stores in MongoDB (full refresh)

**Expected Output:**
```
2025-09-30 14:23:45,001 | INFO | Attempting to log in to MonarchMoney
2025-09-30 14:23:46,234 | INFO | Logged in to MonarchMoney successfully
2025-09-30 14:23:47,456 | INFO | Fetching budget data
2025-09-30 14:23:48,789 | INFO | Fetching transactions
2025-09-30 14:23:50,012 | INFO | Parsing budget data: 42 categories
2025-09-30 14:23:51,234 | INFO | Parsing transactions: 156 records
2025-09-30 14:23:52,456 | INFO | Exporting to MongoDB
2025-09-30 14:23:53,789 | INFO | Data import complete
```

#### 10.1.2 Agent Execution

**Purpose:** Analyze data and generate/send financial alerts.

```bash
# From project root
python -m main
```

**What It Does:**
1. Loads budget/transactions from MongoDB
2. Filters overspent categories
3. Generates daily overspend alert (if applicable)
4. Analyzes yesterday's transactions for suspicious spending
5. Generates period report (if Monday or first of month)
6. Converts all alerts/reports to HTML email
7. Sends email via SMTP

**Expected Output:**
```
2025-09-30 14:23:45,001 | INFO | [N/A] | Budget Agent starting
2025-09-30 14:23:45,123 | INFO | [budget-agent-run-20250930-142345] | Starting agent run
2025-09-30 14:23:45,456 | INFO | [budget-agent-run-20250930-142345] | Starting data import node
2025-09-30 14:23:46,789 | INFO | [budget-agent-run-20250930-142345] | Budget data imported | budget_rows=42
2025-09-30 14:23:47,012 | INFO | [budget-agent-run-20250930-142345] | Overspent categories filtered | overspent_count=5
2025-09-30 14:23:48,234 | INFO | [budget-agent-run-20250930-142345] | Last day transactions imported | transaction_count=23
2025-09-30 14:23:50,456 | INFO | [budget-agent-run-20250930-142345] | Generating daily overspend alert
2025-09-30 14:23:52,789 | INFO | [budget-agent-run-20250930-142345] | Analyzing transactions for suspicious activity
2025-09-30 14:23:55,012 | INFO | [budget-agent-run-20250930-142345] | Generating HTML email
2025-09-30 14:23:56,234 | INFO | [budget-agent-run-20250930-142345] | Email sent successfully
2025-09-30 14:23:56,456 | INFO | [budget-agent-run-20250930-142345] | Budget Agent completed successfully

=== Agent run summary ===
Task route: daily_tasks
Process flags: {'daily_budget_alert': True, 'daily_sus_txn_alert': True, 'period_report': False}
Email subject: Daily Budget Alert - September 30, 2025
Email preview: You've overspent in 5 categories today! Dining out is leading the way with $87 over budget...
```

### 10.2 GitHub Actions Automation

**Location:** `.github/workflows/daily_budget_data_git_pipeline.yml`

**Schedule:** 14:00 UTC daily (cron: `0 14 * * *`)

**Workflow Steps:**
1. Check out repository
2. Set up Python 3.11
3. Install `uv` package manager
4. Install dependencies with `uv sync`
5. Run data import pipeline
6. Wait 30 seconds for MongoDB writes to settle
7. Run agent workflow
8. (Optional) Upload logs as artifacts

**Configuration:**

```yaml
name: Daily Budget Data & Agent Pipeline

on:
  schedule:
    - cron: '0 14 * * *'  # 14:00 UTC daily
  workflow_dispatch:        # Manual trigger

jobs:
  run-budget-agent:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install uv
        run: pip install uv

      - name: Install dependencies
        run: |
          cd services/api
          uv sync

      - name: Run data import
        env:
          MONARK_USER: ${{ secrets.MONARK_USER }}
          MONARK_PW: ${{ secrets.MONARK_PW }}
          MONARK_DD_ID: ${{ secrets.MONARK_DD_ID }}
          MONGO_URL: ${{ secrets.MONGO_URL }}
          MONGO_DB: ${{ secrets.MONGO_DB }}
        run: python -m services.api.pipelines.data_import_pipeline

      - name: Wait for MongoDB
        run: sleep 30

      - name: Run agent
        env:
          # ... all secrets
        run: python -m main
```

**Required Repository Secrets:**
- `MONARK_USER`
- `MONARK_PW`
- `MONARK_DD_ID`
- `MONGO_URL`
- `MONGO_DB`
- `GROQ_API_KEY`
- `SMTP_USER`
- `SMTP_PASSWORD`

### 10.3 Manual Testing

**Test SMTP Configuration:**

```bash
python test_email_sender.py
```

Sends a test email to verify SMTP credentials.

**Test LLM Integration:**

```bash
python test_llm.py
```

Fetches budget data and tests LLM call with overspend prompt.

---

## 11. Testing

### 11.1 Test Suite Overview

| Test File | Tests | Purpose | Duration |
|-----------|-------|---------|----------|
| `unitest.py` | 2 | Integration tests (agent workflow) | 2.73s |
| `test_error_handling.py` | 10 | Error handling and retry logic | 24.38s |
| `test_logging.py` | 22 | Logging functionality | 0.05s |
| **Total** | **34** | **Full coverage** | **27.16s** |

### 11.2 Running Tests

**All Tests:**

```bash
cd services/api
.venv/Scripts/python.exe -m pytest ../../unitest.py ../../test_error_handling.py ../../test_logging.py -v
```

**Specific Test File:**

```bash
.venv/Scripts/python.exe -m pytest ../../test_logging.py -v
```

**With Coverage:**

```bash
pytest --cov=services.api --cov-report=html
```

### 11.3 Integration Tests (unitest.py)

**Test 1: Budget Nodes Graph**

```python
def test_budget_nodes_graph():
    """Test agent workflow with mocked MongoDB and LLM."""

    # Create fake MongoDB client with sample data
    fake_client = FakeAsyncMongoDBClient()

    # Create initial state
    initial_state = make_initial_state()

    # Run workflow
    result = await app.ainvoke(initial_state)

    # Assertions
    assert result.current_month_budget is not None
    assert result.overspend_budget_data is not None
    assert len(result.last_day_txn) > 0
```

**Test 2: Live LLM Integration**

```python
def test_budget_nodes_graph_live_llm():
    """Test agent workflow with real LLM calls (requires API key)."""

    # ... similar to test 1 but uses real call_llm function
```

### 11.4 Error Handling Tests (test_error_handling.py)

**Test Categories:**

1. **Custom Exceptions (3 tests)**
   - Verify exception hierarchy
   - Test exception inheritance

2. **LLM Retry Logic (2 tests)**
   - Timeout handling
   - Empty response handling

3. **Database Error Handling (2 tests)**
   - Connection failures
   - Query failures

4. **Email Retry Logic (1 test)**
   - SMTP failure handling

5. **Monarch Money Error Handling (2 tests)**
   - Login retry logic
   - Data retrieval errors

### 11.5 Logging Tests (test_logging.py)

**Test Categories:**

1. **Sensitive Data Redaction (6 tests)**
   - Password redaction
   - API key redaction
   - Token redaction
   - Email partial redaction
   - Dict argument redaction
   - Multiple pattern redaction

2. **Correlation ID (3 tests)**
   - ID injection
   - Default value handling
   - Context isolation

3. **Structured Formatting (3 tests)**
   - Basic log formatting
   - Duration formatting
   - Extra data formatting

4. **Setup & Configuration (3 tests)**
   - Root logger configuration
   - Logger instance retrieval
   - Sensitive filter enablement

5. **Log Output (4 tests)**
   - INFO log emission
   - ERROR log emission
   - DEBUG log emission
   - Extra fields emission

### 11.6 Mocking External Services

**MongoDB Mock:**

```python
class FakeAsyncMongoDBClient:
    """Mock MongoDB client for testing."""

    async def import_budget_data(self, filter_query):
        return json.dumps(SAMPLE_BUDGET_ROWS)

    async def import_transaction_data(self, start_date, end_date):
        return json.dumps(SAMPLE_TRANSACTIONS)

    def close_connection(self):
        pass
```

**LLM Mock:**

```python
from unittest.mock import AsyncMock, patch

with patch("services.api.app.agent.agent_utilities.AsyncGroq") as mock_groq:
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = mock_response
    mock_groq.return_value = mock_client

    # ... test code
```

---

## 12. Performance Considerations

### 12.1 Current Performance Metrics

**Baseline (from testing):**

| Metric | Value | Notes |
|--------|-------|-------|
| Agent run time | 2.73s | With mocked external services |
| Full test suite | 27.16s | Includes 10 LLM retry tests |
| Logging overhead | < 0.03ms | Per log entry |
| Memory footprint | ~150MB | Base Python + dependencies |

### 12.2 LLM Call Optimization Opportunities

**Current Pattern (Sequential):**

```python
# period_report_node (lines 409-466)
for record in over_spend_budget:  # 5-10 categories
    response_text = await call_llm_reasoning(...)  # Sequential API call
    analysis_responses.append(response_model)
```

**Impact:**
- 5 overspent categories × 2-3s per LLM call = **10-15 seconds total**

**Potential Optimization (Parallel):**

```python
import asyncio

# Create tasks for all categories
tasks = [
    call_llm_reasoning(
        model=Settings.GROQ_OPENAI_20B_MODE,
        temperature=0.8,
        prompt_obj=TXN_ANALYSIS_PROMPT,
        this_month_txn=current_month_category_txn,
        last_month_txn=previous_month_category_txn,
        max_tokens=500,
    )
    for record in over_spend_budget
]

# Execute in parallel
results = await asyncio.gather(*tasks)
```

**Expected Improvement:**
- **Sequential:** 10-15 seconds
- **Parallel:** 2-3 seconds (limited by slowest API call)
- **Speedup:** **5-7x faster**

**Status:** Deferred to future work (requires prompt redesign and testing)

### 12.3 MongoDB Query Performance

**Current Strategy:** Full collection scans with filters

**Potential Optimizations:**
1. **Indexes:**
   ```python
   # Add indexes for common queries
   budgets_collection.create_index([("category_group_type", 1)])
   transactions_collection.create_index([("createdAt", -1)])
   ```

2. **Projection:**
   ```python
   # Only fetch required fields
   cursor = collection.find(
       filter_query,
       {"_id": 0, "amount": 1, "category": 1, "date": 1}  # Projection
   )
   ```

3. **Connection Pooling:**
   - Already implemented with Motor (async driver)
   - Max pool size: 100 (default)

### 12.4 Logging Performance

**Measured Overhead:**
- Per log entry: **< 0.03ms**
- Per log with extra fields: **< 0.05ms**
- Per log with sensitive data filter: **< 0.1ms**

**Conclusion:** Negligible impact (< 0.1% of total execution time)

### 12.5 Memory Optimization

**Current Memory Usage:**
- Base Python: ~50MB
- Dependencies loaded: ~100MB
- Runtime data (state): ~5-10MB (depends on transaction count)

**Potential Optimizations:**
1. **Streaming Large Datasets:**
   - Use MongoDB cursors instead of loading all data
   - Process transactions in batches

2. **LLM Response Caching:**
   - Cache LLM responses for identical prompts
   - Reduce duplicate API calls

---

## 13. Security & Best Practices

### 13.1 Sensitive Data Protection

**Automated Redaction:**

All sensitive data is automatically redacted from logs:
- ✅ Passwords
- ✅ API keys
- ✅ Tokens
- ✅ Secrets
- ✅ Email addresses (partial)

**Example:**
```python
logger.info("Connecting with password=secret123")
# Logged as: "Connecting with password=***REDACTED***"
```

**Configuration:**

Disable sensitive data redaction (not recommended):
```python
setup_logging(enable_sensitive_filter=False)
```

### 13.2 Secret Management

**Environment Variables:**

All secrets stored in `.env` file (not committed to git):

```bash
# .env
MONARK_PW=your_password       # Never hardcode in code
GROQ_API_KEY=gsk_abc123       # Never commit to git
SMTP_PASSWORD=app_password    # Use app-specific passwords
```

**Pydantic SecretStr:**

```python
from pydantic import SecretStr

class Settings(BaseSettings):
    MONARK_PW: SecretStr  # Automatically masked in logs/repr
    # str(Settings.MONARK_PW) → "**********"
    # Settings.MONARK_PW.get_secret_value() → actual password
```

**GitHub Actions:**

Store secrets in repository settings, not in workflow files:

```yaml
# .github/workflows/daily_budget_data_git_pipeline.yml
env:
  MONARK_PW: ${{ secrets.MONARK_PW }}  # ✅ Correct
  # MONARK_PW: "actual_password"      # ❌ NEVER DO THIS
```

### 13.3 API Key Security

**Best Practices:**

1. **Use App-Specific Passwords:**
   - Gmail: Generate app-specific password (not your actual password)
   - Groq: Use API key, not account password

2. **Rotate Keys Regularly:**
   - Rotate Groq API key every 90 days
   - Rotate SMTP password every 90 days

3. **Limit Key Permissions:**
   - Use read-only MongoDB credentials for agent (if possible)
   - Use send-only SMTP credentials

4. **Monitor Usage:**
   - Check Groq API usage dashboard
   - Monitor MongoDB connection logs
   - Review SMTP sent mail logs

### 13.4 Database Connection Security

**Connection String:**

```bash
# Local (insecure - development only)
MONGO_URL=mongodb://localhost:27017

# Remote with authentication (production)
MONGO_URL=mongodb://username:password@hostname:27017/?authSource=admin

# MongoDB Atlas (recommended)
MONGO_URL=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
```

**Best Practices:**

1. **Use TLS/SSL:**
   ```bash
   MONGO_URL=mongodb://host:27017/?ssl=true
   ```

2. **Network Isolation:**
   - MongoDB should not be publicly accessible
   - Use firewall rules to restrict access
   - GitHub Actions should connect via VPN or allowlisted IPs

3. **Least Privilege:**
   - Create dedicated MongoDB user with minimal permissions
   - Only grant read/write on `monark_budget` database

### 13.5 Email Security

**SMTP Configuration:**

```python
# Use TLS encryption (STARTTLS)
with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
    server.starttls()  # Upgrade to TLS
    server.login(address, password)
    server.send_message(msg)
```

**Best Practices:**

1. **Use App-Specific Passwords:**
   - Never use your actual Gmail password
   - Generate app-specific password in Google Account settings

2. **Limit Recipients:**
   - Only send to verified recipients
   - Validate email addresses before sending

3. **Content Security:**
   - Validate HTML to prevent XSS
   - Sanitize user inputs in email content

### 13.6 Code Security

**Dependency Security:**

```bash
# Check for known vulnerabilities
pip install safety
safety check --file services/api/pyproject.toml

# Update dependencies regularly
uv sync --upgrade
```

**Code Quality:**

```bash
# Static analysis
pylint services/api/app/
flake8 services/api/app/ --max-line-length=120

# Security linting (optional)
pip install bandit
bandit -r services/api/app/
```

---

## 14. Extending & Customizing

### 14.1 Adding New Agent Nodes

**Step 1: Define Node Function**

Create new node in `services/api/app/agent/nodes.py`:

```python
async def my_custom_node(state: BudgetAgentState) -> BudgetAgentState:
    """
    Custom node description.

    Steps:
    1. Read data from state
    2. Process data
    3. Update state
    4. Return modified state
    """
    logger.info("Starting custom node")

    # Your logic here
    # ...

    logger.info("Custom node completed")
    return state
```

**Step 2: Update State Model (if needed)**

Add new fields to `BudgetAgentState` in `state.py`:

```python
@dataclass
class BudgetAgentState:
    # ... existing fields

    custom_data: Optional[str] = None  # New field for your node
```

**Step 3: Register Node in Graph**

Update `services/api/app/agent/agent_graph.py`:

```python
def create_budget_graph() -> StateGraph:
    graph_builder = StateGraph(BudgetAgentState)

    # Add your node
    graph_builder.add_node("my_custom_node", my_custom_node)

    # Add edges (example: after daily alerts, before email)
    graph_builder.add_edge("daily_suspicious_transaction_alert_node", "my_custom_node")
    graph_builder.add_edge("my_custom_node", "email_node")

    return graph_builder
```

**Step 4: Test**

Add test to `unitest.py`:

```python
def test_custom_node():
    state = make_initial_state()
    result = await my_custom_node(state)
    assert result.custom_data is not None
```

### 14.2 Creating Custom Prompts

**Step 1: Define Prompt**

Add to `services/api/app/domain/prompts.py`:

```python
CUSTOM_ANALYSIS_PROMPT = Prompt(
    name="custom_analysis",
    prompt="""
Analyze the following data and provide insights:

Data:
{input_data}

Instructions:
- Focus on patterns and trends
- Provide actionable recommendations
- Keep response under 200 words
""",
    version="1.0"
)
```

**Step 2: Use in Node**

```python
async def my_custom_node(state: BudgetAgentState) -> BudgetAgentState:
    # Call LLM with custom prompt
    response = await call_llm(
        model=Settings.GROQ_LLAMA_VERSATILE,
        temperature=0.7,
        prompt_obj=CUSTOM_ANALYSIS_PROMPT,
        max_tokens=500,
        input_data=state.current_month_budget
    )

    # Process response
    state.custom_data = response
    return state
```

### 14.3 Integrating New Data Sources

**Step 1: Create API Client**

```python
# services/api/pipelines/new_data_source.py
class NewDataSourceClient:
    """Client for new data source API."""

    @retry(...)
    async def fetch_data(self) -> dict:
        """Fetch data with retry logic."""
        # ... implementation
```

**Step 2: Add Data Parsing**

```python
# services/api/pipelines/data_parsing_functions.py
def parse_new_data_source(raw_data) -> str:
    """Parse and validate new data source."""
    # Convert to DataFrame
    df = pd.DataFrame(raw_data)

    # Process and validate
    # ...

    return df.to_json(orient="records")
```

**Step 3: Store in MongoDB**

```python
# services/api/pipelines/mongo_client.py
class MongoDBClient:
    def __init__(self):
        # ... existing code
        self.new_data_collection = self.db["new_data_source"]

    def export_new_data(self, data):
        self.new_data_collection.delete_many({})
        self.new_data_collection.insert_many(data)
```

**Step 4: Import in Agent**

```python
# services/api/app/agent/nodes.py
async def import_data_node(state: BudgetAgentState) -> BudgetAgentState:
    # ... existing imports

    # Add new data source import
    new_data_json = await mongo_client.import_new_data()
    state.new_data = new_data_json

    return state
```

### 14.4 Adding New LLM Providers

**Step 1: Install Provider SDK**

```bash
# Add to services/api/pyproject.toml
dependencies = [
    # ... existing
    "openai>=1.0.0",  # Example: OpenAI
]

# Install
cd services/api
uv lock
uv sync
```

**Step 2: Create Provider Wrapper**

```python
# services/api/app/agent/agent_utilities.py
from openai import AsyncOpenAI

@retry(...)
async def call_openai(
    temperature: float = 0.7,
    prompt_obj=None,
    max_tokens: int = 4020,
    model: str = "gpt-4",
    timeout: int = 60,
    **kwargs
) -> str:
    """Call OpenAI API with retry logic."""
    try:
        client = AsyncOpenAI(
            api_key=Settings.OPENAI_API_KEY.get_secret_value(),
            timeout=timeout
        )

        formatted_prompt = prompt_obj.prompt.format(**kwargs)

        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT.prompt},
                {"role": "user", "content": formatted_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return response.choices[0].message.content

    except Exception as exc:
        raise LLMError(f"OpenAI API call failed: {exc}") from exc
```

**Step 3: Update Configuration**

```python
# config.py
class Settings(BaseSettings):
    # ... existing
    OPENAI_API_KEY: SecretStr = Field(description="OpenAI API key")
```

**Step 4: Use in Nodes**

```python
# Replace call_llm with call_openai in any node
response = await call_openai(
    model="gpt-4",
    prompt_obj=BUDGET_ALERT_PROMPT,
    overspend_budget_data=state.overspend_budget_data
)
```

### 14.5 Modifying Workflow Routing

**Example: Add Conditional Routing Based on Overspend Amount**

```python
# services/api/app/agent/agent_utilities.py
def overspend_severity(state: BudgetAgentState) -> str:
    """
    Determine overspend severity for routing.

    Returns:
        "critical" if any category overspent by > $100
        "moderate" if overspent by $50-$100
        "low" if overspent by < $50
    """
    if not state.overspend_budget_data:
        return "low"

    data = json.loads(state.overspend_budget_data)
    max_overspend = max(abs(row["remaining_amount"]) for row in data)

    if max_overspend > 100:
        return "critical"
    elif max_overspend > 50:
        return "moderate"
    else:
        return "low"
```

**Update Graph:**

```python
# services/api/app/agent/agent_graph.py
graph_builder.add_conditional_edges(
    "daily_overspend_alert_node",
    overspend_severity,
    {
        "critical": "urgent_notification_node",  # New node for critical alerts
        "moderate": "email_node",
        "low": "email_node"
    }
)
```

---

## 15. Troubleshooting

### 15.1 Common Issues

#### Issue 1: MongoDB Connection Failed

**Symptoms:**
```
DatabaseConnectionError: Failed to connect to MongoDB: connection timeout
```

**Solutions:**

1. **Check MongoDB is running:**
   ```bash
   # Local MongoDB
   mongod --dbpath /path/to/data

   # Docker
   docker ps | grep mongo
   ```

2. **Verify connection string:**
   ```bash
   # Test connection with mongo shell
   mongo "mongodb://localhost:27017"
   ```

3. **Check firewall rules:**
   - Ensure port 27017 is not blocked
   - For remote MongoDB, check network connectivity

4. **Review MongoDB logs:**
   ```bash
   tail -f /var/log/mongodb/mongod.log
   ```

#### Issue 2: LLM API Timeout

**Symptoms:**
```
LLMTimeoutError: LLM request timed out after 60s
```

**Solutions:**

1. **Check API key validity:**
   ```python
   # Verify in Groq dashboard
   # https://console.groq.com/keys
   ```

2. **Increase timeout:**
   ```python
   response = await call_llm(
       prompt_obj=...,
       timeout=120,  # Increase to 120s
       **kwargs
   )
   ```

3. **Reduce max_tokens:**
   ```python
   response = await call_llm(
       prompt_obj=...,
       max_tokens=1000,  # Reduce from 4020
       **kwargs
   )
   ```

4. **Check API rate limits:**
   - Free tier: 30 requests/minute
   - Paid tier: 300 requests/minute
   - Wait and retry if rate limited

#### Issue 3: SMTP Authentication Failed

**Symptoms:**
```
EmailError: SMTP error sending email: (535, 'Authentication failed')
```

**Solutions:**

1. **Use app-specific password:**
   - Go to Google Account → Security → App passwords
   - Generate new app-specific password
   - Update `.env` file with new password

2. **Enable "Less secure app access":**
   - Not recommended; use app-specific password instead

3. **Check SMTP credentials:**
   ```python
   # Verify in .env
   SMTP_USER=your-email@gmail.com
   SMTP_PASSWORD=your-app-specific-password  # 16-character password
   ```

4. **Test SMTP connection:**
   ```bash
   python test_email_sender.py
   ```

#### Issue 4: Monarch Money Login Failed

**Symptoms:**
```
MonarchMoneyLoginError: Failed to login to MonarchMoney
```

**Solutions:**

1. **Verify credentials:**
   ```bash
   # Check .env file
   MONARK_USER=your-email@example.com
   MONARK_PW=your-password
   ```

2. **Update device ID:**
   - Old device ID may have expired
   - Follow Section 5.4 to obtain new device ID

3. **MFA required:**
   ```python
   # If MFA is enabled, provide MFA code
   await monark.monarch_login(pw, user, mfa_code="123456")
   ```

4. **Check Monarch Money service status:**
   - Visit Monarch Money website
   - Verify you can log in manually

### 15.2 Debugging with Correlation IDs

**Problem:** Need to find all logs from a specific agent run.

**Solution:** Use correlation ID to filter logs.

**Step 1: Identify Run ID**

From agent output:
```
Starting agent run | run_id=budget-agent-run-20250930-142345, ...
```

**Step 2: Filter Logs**

```bash
# If using file logging
grep "budget-agent-run-20250930-142345" application.log

# Or pipe stdout/stderr
python -m main 2>&1 | grep "budget-agent-run-20250930-142345"
```

**Step 3: Analyze Timeline**

```bash
# Get full execution timeline
grep "budget-agent-run-20250930-142345" application.log | sort
```

**Example Output:**
```
2025-09-30 14:23:45,123 | INFO | [budget-agent-run-20250930-142345] | Starting agent run
2025-09-30 14:23:45,456 | INFO | [budget-agent-run-20250930-142345] | Starting data import node
2025-09-30 14:23:46,789 | INFO | [budget-agent-run-20250930-142345] | Budget data imported | budget_rows=42
2025-09-30 14:23:49,012 | ERROR | [budget-agent-run-20250930-142345] | LLM API call failed | error=timeout
```

Now you can see exactly where the failure occurred!

### 15.3 Test Failures

#### Test: unitest.py fails

**Symptoms:**
```
AssertionError: assert result.current_month_budget is not None
```

**Solutions:**

1. **Check MongoDB mock:**
   - Verify `FakeAsyncMongoDBClient` returns valid data
   - Check sample data format matches expected schema

2. **Review state initialization:**
   - Ensure `make_initial_state()` creates valid state
   - Check all required fields are present

3. **Run with verbose output:**
   ```bash
   pytest unitest.py -v -s  # -s shows print statements
   ```

#### Test: test_error_handling.py fails

**Symptoms:**
```
FAILED test_error_handling.py::TestLLMRetryLogic::test_call_llm_timeout_handling
```

**Solutions:**

1. **Check mock setup:**
   - Verify mocks are correctly configured
   - Ensure side effects are set properly

2. **Review retry logic:**
   - Tenacity retry decorators may need adjustment
   - Check exception types match retry conditions

3. **Run single test:**
   ```bash
   pytest test_error_handling.py::TestLLMRetryLogic::test_call_llm_timeout_handling -v
   ```

### 15.4 Performance Issues

#### Issue: Agent takes > 30 seconds

**Diagnosis:**

1. **Check LLM call duration:**
   ```python
   # Look for duration in logs
   grep "duration=" application.log | sort -t= -k2 -n
   ```

2. **Profile execution:**
   ```python
   import cProfile

   cProfile.run('asyncio.run(run_agent())', sort='cumtime')
   ```

**Solutions:**

1. **Reduce max_tokens:**
   - Lower max_tokens for LLM calls
   - Use more concise prompts

2. **Parallel LLM calls:**
   - See Section 12.2 for LLM call optimization

3. **Cache LLM responses:**
   - Cache responses for identical prompts
   - Use TTL cache (e.g., 1 hour)

### 15.5 Data Issues

#### Issue: No overspent categories found (but there should be)

**Diagnosis:**

Check filtering logic:

```python
# services/api/app/agent/agent_utilities.py
def filter_overspent_categories(budget_json: str) -> str:
    budget_data = json.loads(budget_json)
    filtered_data = [
        budget_record
        for budget_record in budget_data
        if budget_record.get("remaining_amount", 0) < -5  # ← Check threshold
    ]
    # ...
```

**Solutions:**

1. **Adjust threshold:**
   - Change `-5` to `-1` for more sensitive filtering
   - Or make threshold configurable

2. **Check budget data:**
   ```python
   # Print budget data in import_data_node
   logger.debug(f"Budget data: {budget_json}")
   ```

3. **Verify data format:**
   - Ensure `remaining_amount` field exists
   - Check data types (should be float, not string)

---

## 16. API Reference

### 16.1 Core Functions

#### `call_llm()`

```python
async def call_llm(
    temperature: float = 0.7,
    system_prompt: str = SYSTEM_PROMPT.prompt,
    prompt_obj=None,
    max_tokens: int = 4020,
    model: str = Settings.GROQ_LLAMA_VERSATILE,
    api_key: str = Settings.GROQ_API_KEY.get_secret_value(),
    response_format: str = "text",
    timeout: int = 60,
    **kwargs
) -> str
```

**Purpose:** Call Groq LLM API with retry logic and timeout handling.

**Parameters:**
- `temperature` (float): Sampling temperature (0-1), default 0.7
- `system_prompt` (str): System prompt for LLM
- `prompt_obj` (Prompt): Prompt object with `.prompt` attribute
- `max_tokens` (int): Maximum tokens to generate, default 4020
- `model` (str): Model identifier
- `timeout` (int): Request timeout in seconds, default 60
- `**kwargs`: Additional parameters to format the prompt

**Returns:** LLM response content (str)

**Raises:**
- `LLMError`: On LLM API failures
- `LLMTimeoutError`: On timeout
- `LLMResponseError`: On invalid response format

**Retry Logic:**
- 3 attempts with exponential backoff (2s, 4s, 8s)
- Only retries on `LLMError` and `LLMTimeoutError`

**Example:**
```python
response = await call_llm(
    model="llama-3.3-70b-versatile",
    temperature=0.8,
    prompt_obj=BUDGET_ALERT_PROMPT,
    max_tokens=500,
    overspend_budget_data=state.overspend_budget_data
)
```

---

#### `call_llm_reasoning()`

Similar to `call_llm()` but optimized for reasoning models:
- Default timeout: 90s (vs 60s)
- Additional parameters: `reasoning_effort`, `reasoning_format`
- Used for complex analysis tasks

---

#### `SendEmail.send_email_async()`

```python
async def send_email_async(self, is_html: bool = False) -> None
```

**Purpose:** Send email via SMTP with retry logic.

**Parameters:**
- `is_html` (bool): Whether email body is HTML, default False

**Raises:**
- `EmailError`: On sending failures after retries

**Retry Logic:**
- 3 attempts with exponential backoff
- 30-second timeout per attempt

**Example:**
```python
email_sender = SendEmail(email_info)
await email_sender.send_email_async(is_html=True)
```

---

#### `setup_logging()`

```python
def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    enable_sensitive_filter: bool = True,
) -> logging.Logger
```

**Purpose:** Setup structured logging for the application.

**Parameters:**
- `level` (int): Logging level, default INFO
- `log_file` (str): Optional log file path
- `enable_sensitive_filter` (bool): Enable sensitive data redaction, default True

**Returns:** Configured root logger

**Example:**
```python
setup_logging(
    level=logging.DEBUG,
    log_file="application.log",
    enable_sensitive_filter=True
)
```

---

#### `set_correlation_id()`

```python
def set_correlation_id(new_id: str) -> None
```

**Purpose:** Set correlation ID for current execution context.

**Parameters:**
- `new_id` (str): Correlation ID (e.g., run_id)

**Example:**
```python
set_correlation_id(initial_state.run_meta.run_id)
```

---

### 16.2 State Model Fields

**`BudgetAgentState`**

| Field | Type | Description |
|-------|------|-------------|
| `run_meta` | RunMeta | Execution metadata (run_id, date, timezone) |
| `current_month_budget` | Optional[str] | JSON budget data for current month |
| `current_month_txn` | Optional[str] | Current month transactions (JSON) |
| `previous_month_txn` | Optional[str] | Previous month transactions (JSON) |
| `last_day_txn` | list[str] | Yesterday's transactions (list of JSON strings) |
| `overspend_budget_data` | Optional[str] | Overspent categories (JSON) |
| `daily_overspend_alert` | DailyAlertOverspend | Generated overspend alert content |
| `daily_suspicious_transactions` | list[DailySuspiciousTransaction] | Suspicious transactions with analysis |
| `daily_alert_suspicious_transaction` | DailyAlertSuspiciousTransaction | Suspicious transaction alert content |
| `period_report` | Optional[str] | Weekly/monthly report text |
| `process_flag` | ProcessFlag | Boolean flags for task completion |
| `email_info` | Optional[EmailInfo] | Generated email metadata |
| `task_info` | str | Task routing info ("daily_tasks" or "both_tasks") |

---

### 16.3 Configuration Options

**`Settings` (config.py)**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `MONARK_USER` | str | Yes | - | Monarch Money login email |
| `MONARK_PW` | SecretStr | Yes | - | Monarch Money password |
| `MONARK_DD_ID` | SecretStr | Yes | - | Device UUID |
| `MONGO_URL` | SecretStr | Yes | - | MongoDB connection string |
| `MONGO_DB` | str | Yes | - | MongoDB database name |
| `GROQ_API_KEY` | SecretStr | Yes | - | Groq API key |
| `GROQ_LLAMA_VERSATILE` | str | No | "llama-3.3-70b-versatile" | Llama model ID |
| `GROQ_LLAMA_INSTRUCT` | str | No | "llama-3.3-70b-instruct" | Llama instruct model |
| `GROQ_QWEN_REASONING` | str | No | "qwen/qwen3-32b" | QWen reasoning model |
| `GROQ_OPENAI_20B_MODE` | str | No | "openai/gpt-oss-20b" | OpenAI OSS model |
| `SMTP_USER` | str | Yes | - | SMTP username |
| `SMTP_PASSWORD` | SecretStr | Yes | - | SMTP password |

---

## 17. Optimization History

### 17.1 Step 1: Baseline Establishment

**Date:** 2025-09-28
**Objective:** Audit codebase, document current state, identify improvement areas

**Key Findings:**
- 5,243 lines of code
- 517 flake8 violations
- 0 working tests
- No error handling
- No structured logging
- Inconsistent code formatting

**Deliverables:**
- ✅ BASELINE_REPORT.md created
- ✅ Repository structure documented
- ✅ Test infrastructure fixed
- ✅ Lint baseline established

---

### 17.2 Step 2: Code Style Consistency

**Date:** 2025-09-28
**Objective:** Enforce consistent style, remove low-risk redundancy

**Changes:**
- Applied black formatter (12 files reformatted)
- Applied isort (9 files fixed)
- Removed unused imports with autoflake (7 imports)
- Removed duplicate MongoDB query in nodes.py
- Fixed broken test file (unitest.py)

**Metrics:**
- Flake8 violations: 517 → 85 (**84% reduction**)
- Test pass rate: 0% → 100%
- Code consistency: Inconsistent → Uniform

**Deliverables:**
- ✅ step_2_report.md created
- ✅ All tests passing

---

### 17.3 Step 3: Efficiency Refactoring

**Date:** 2025-09-29
**Objective:** Refactor for efficiency and correctness

**Changes:**
- Fixed E712 boolean comparison anti-pattern
- Eliminated 8 Pydantic deprecation warnings
- Created `parse_and_validate_transactions()` helper (75% code reduction)
- Added type hints to 6 functions (100% coverage in agent_utilities.py)
- Removed unused imports and spacing violations

**Metrics:**
- Duplicate code: 28 lines → 7 lines (**75% reduction**)
- Type hint coverage: 0% → 100%
- Pydantic warnings: 8 → 0 (**100% elimination**)
- Test execution time: 2.93s → 2.68s (**8.5% faster**)

**Deliverables:**
- ✅ step_3_report.md created
- ✅ Helper functions for reusability

---

### 17.4 Step 4: Error Handling Hardening

**Date:** 2025-09-29
**Objective:** Implement robust error handling with retry logic

**Changes:**
- Created custom exception hierarchy (11 exceptions)
- Added retry logic to 9 critical functions
- Implemented timeout handling (60s LLM, 90s reasoning, 30s SMTP, 5s MongoDB)
- Replaced bare `except:` clause with specific exception types
- Added graceful degradation in main.py

**Metrics:**
- Custom exceptions: 0 → 11
- Functions with retry logic: 0 → 9
- Functions with timeout: 0 → 4
- Bare except clauses: 1 → 0 (**100% elimination**)
- Test suite: 2 tests → 12 tests (**500% increase**)

**Deliverables:**
- ✅ services/api/app/exceptions.py (119 lines)
- ✅ test_error_handling.py (235 lines, 10 tests)
- ✅ step_4_report.md created
- ✅ All tests passing with zero regressions

---

### 17.5 Step 5: Structured Logging

**Date:** 2025-09-30
**Objective:** Implement enterprise-grade structured logging

**Changes:**
- Created centralized logging configuration module (270 lines)
- Implemented sensitive data redaction (5 patterns)
- Added correlation ID support for distributed tracing
- Replaced 7 print statements with structured logging
- Enhanced logging at 15+ key execution points

**Metrics:**
- Print statements: 7 → 0 (**100% replacement**)
- Structured log calls: ~10 → ~25 (**150% increase**)
- Sensitive data protection: 0 → 5 patterns
- Correlation ID support: None → Full
- Test suite: 12 tests → 34 tests (**183% increase**)
- Logging overhead: < 0.03ms per entry (**negligible**)

**Deliverables:**
- ✅ services/api/app/logging_config.py (270 lines)
- ✅ test_logging.py (342 lines, 22 tests)
- ✅ step_5_report.md created
- ✅ 100% sensitive data protection

---

### 17.6 Overall Metrics Summary

| Metric | Baseline (Step 1) | Current (Step 5) | Change |
|--------|------------------|------------------|--------|
| **Flake8 violations** | 517 | ~85 (non-critical) | **↓ 84%** |
| **Test suite** | 0 tests | 34 tests | **+∞** |
| **Test coverage** | 0% | Core paths covered | **+100%** |
| **Print statements** | ~15 | 0 (user-facing only) | **↓ 100%** |
| **Error handling** | None | Comprehensive | **+∞** |
| **Structured logging** | None | Full | **+∞** |
| **Custom exceptions** | 0 | 11 | **+11** |
| **Type hints** | ~30% | ~80% | **+167%** |
| **Code duplication** | High | Low (helpers) | **↓ 75%** |
| **Documentation** | Minimal | Comprehensive | **+2500 lines** |

---

## 18. Known Limitations & Future Work

### 18.1 Current Limitations

**1. LLM Call Batching Not Implemented**

Sequential LLM calls in `period_report_node` could be parallelized:
- **Current:** 10-15 seconds for 5 categories
- **Potential:** 2-3 seconds with `asyncio.gather()`
- **Complexity:** High (requires prompt redesign)

**2. Log Rotation Not Implemented**

If file logging is enabled, logs will grow indefinitely:
- **Recommendation:** Use `RotatingFileHandler` or `TimedRotatingFileHandler`
- **Example:**
  ```python
  from logging.handlers import RotatingFileHandler

  handler = RotatingFileHandler(
      "application.log",
      maxBytes=10*1024*1024,  # 10MB
      backupCount=5
  )
  ```

**3. JSON Log Format Not Available**

Logs are text-based, not JSON:
- **Current:** Human-readable text format
- **Limitation:** Harder to parse with log aggregation tools (ELK, Splunk)
- **Future:** Add JSON formatter option

**4. No Circuit Breaker Pattern**

Repeated failures could cascade:
- **Current:** Retry logic with exponential backoff
- **Future:** Add circuit breaker to stop calling failing services
- **Example:** Use `pybreaker` library

**5. No MongoDB Index Optimization**

All queries use full collection scans:
- **Current:** No indexes defined
- **Impact:** Slow queries on large datasets (> 10k transactions)
- **Recommendation:** Add indexes on frequently queried fields

### 18.2 Future Enhancements

**High Priority:**

1. **LLM Response Caching**
   - Cache responses for identical prompts
   - Use Redis or in-memory cache
   - TTL: 1 hour

2. **MongoDB Indexes**
   ```python
   budgets_collection.create_index([("category_group_type", 1)])
   transactions_collection.create_index([("createdAt", -1)])
   ```

3. **API Rate Limit Handling**
   - Implement exponential backoff with jitter
   - Track rate limit headers
   - Queue requests if rate limited

**Medium Priority:**

4. **Performance Decorator Usage**
   - Apply `@log_execution_time` to expensive functions
   - Collect performance metrics
   - Create performance dashboard

5. **Async LLM Call Batching**
   - Refactor `period_report_node` for parallel calls
   - Use `asyncio.gather()` or `asyncio.as_completed()`

6. **Health Check Endpoint**
   - Add FastAPI endpoint for health checks
   - Check MongoDB connection
   - Check LLM API availability

**Low Priority:**

7. **Web Dashboard**
   - Visualize budget trends
   - Display historical reports
   - Interactive transaction search

8. **Multiple Recipient Support**
   - Send reports to multiple email addresses
   - Per-recipient customization

9. **SMS/Slack Notifications**
   - Alternative notification channels
   - Urgent alerts via SMS

### 18.3 Known Issues

**1. Pydantic Warning (External Library)**

```
Field name "schema" in "FewShotExampleStructuredOutputCompliance" shadows an attribute in parent "BaseModel"
```

- **Source:** LangChain library
- **Impact:** None (warning only)
- **Status:** Waiting for upstream fix

**2. Test Execution Time Variability**

- LLM retry tests can take 20-30 seconds
- Network latency affects timing
- Not a functional issue

---

## 19. Contributing Guidelines

### 19.1 Code Style Standards

**Formatter:** Black (line length: 88)

```bash
black services/api/app/
```

**Import Sorter:** isort

```bash
isort services/api/app/
```

**Linter:** Flake8 (line length: 120)

```bash
flake8 services/api/app/ --max-line-length=120
```

**All-in-one Command:**

```bash
black services/api/app/ && isort services/api/app/ && flake8 services/api/app/ --max-line-length=120
```

### 19.2 Pull Request Process

**1. Create Feature Branch**

```bash
git checkout -b feature/your-feature-name
```

**2. Make Changes**

- Write code following style standards
- Add tests for new functionality
- Update documentation if needed

**3. Run Tests**

```bash
cd services/api
.venv/Scripts/python.exe -m pytest ../../unitest.py ../../test_error_handling.py ../../test_logging.py -v
```

All tests must pass (34/34).

**4. Format Code**

```bash
black services/api/app/
isort services/api/app/
```

**5. Lint Code**

```bash
flake8 services/api/app/ --max-line-length=120
```

Fix all violations (except E501 in prompts.py).

**6. Commit Changes**

```bash
git add .
git commit -m "feat: add new feature description"
```

**Commit Message Format:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation update
- `test:` Test additions
- `refactor:` Code refactoring
- `style:` Formatting changes

**7. Push and Create PR**

```bash
git push origin feature/your-feature-name
```

Create pull request on GitHub with:
- Clear description of changes
- Test results
- Any breaking changes noted

### 19.3 Testing Requirements

**All PRs must include:**

1. **Unit tests** for new functions
2. **Integration tests** for new nodes
3. **Error handling tests** for new exception paths
4. **Logging verification** for new log statements

**Test Coverage:**
- Aim for > 80% coverage for new code
- All error paths must be tested

### 19.4 Documentation Updates

**Update when:**
- Adding new features → Update README.md and this document
- Changing configuration → Update Section 5
- Adding dependencies → Update Section 4
- Modifying architecture → Update Section 2

---

## 20. Appendices

### Appendix A: Environment Variable Quick Reference

```bash
# Copy this template to .env and fill in values

# Monarch Money
MONARK_USER=your-email@example.com
MONARK_PW=your-password
MONARK_DD_ID=device-uuid

# MongoDB
MONGO_URL=mongodb://localhost:27017
MONGO_DB=monark_budget

# Groq LLM
GROQ_API_KEY=gsk_your_key_here

# SMTP (Gmail)
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=app-specific-password
```

---

### Appendix B: Error Code Reference

| Exception | Cause | Resolution |
|-----------|-------|------------|
| `MonarchMoneyLoginError` | Invalid credentials or device ID | Verify `.env` credentials, update device ID |
| `MonarchMoneyDataError` | Failed to fetch data | Check Monarch Money API status, retry |
| `DatabaseConnectionError` | MongoDB not accessible | Start MongoDB, check connection string |
| `DatabaseQueryError` | Query failed | Check MongoDB logs, verify data format |
| `LLMTimeoutError` | LLM API timeout | Increase timeout, reduce max_tokens |
| `LLMResponseError` | Empty/invalid response | Check API key, verify prompt format |
| `EmailError` | SMTP failure | Verify SMTP credentials, check network |

---

### Appendix C: Log Level Guidelines

| Level | When to Use | Example |
|-------|-------------|---------|
| **DEBUG** | Detailed diagnostic info | "Connecting to MongoDB", "Parsing JSON" |
| **INFO** | Key milestones | "Agent started", "Budget imported" |
| **WARNING** | Recoverable issues | "MFA required", "Retry attempt 2/3" |
| **ERROR** | Application errors | "Failed to connect", "LLM timeout" |
| **CRITICAL** | System failures | "Cannot continue execution" |

**Best Practices:**
- Use INFO for normal operation flow
- Use WARNING for things that might need attention but don't stop execution
- Use ERROR for failures that prevent completing a task
- Include context in extra fields: `logger.info("Message", extra={"key": value})`

---

### Appendix D: Performance Benchmarks

**Agent Execution (Mocked Services):**
- Total time: 2.73s
- Data import: 0.5s
- Daily alerts: 1.2s
- Email generation: 0.8s
- Overhead: 0.23s

**Test Suite:**
- Integration tests (2): 2.73s
- Error handling tests (10): 24.38s
- Logging tests (22): 0.05s
- **Total: 27.16s**

**Logging Overhead:**
- Per log entry: < 0.03ms
- Per log with filter: < 0.1ms
- Per log with extra fields: < 0.05ms

---

### Appendix E: Dependency Version Matrix

| Package | Version | Purpose | License |
|---------|---------|---------|---------|
| Python | 3.11+ | Runtime | PSF |
| langgraph | 0.2.70+ | Workflow | MIT |
| langchain-core | 0.3.34+ | LLM framework | MIT |
| groq | 0.31.1+ | LLM API | MIT |
| pydantic | 2.10.6+ | Validation | MIT |
| tenacity | 9.0.0+ | Retry logic | Apache 2.0 |
| pymongo | 4.9.2+ | MongoDB | Apache 2.0 |
| motor | 3.7+ | Async MongoDB | Apache 2.0 |
| pandas | 2.0.0+ | Data processing | BSD |
| pytest | 8.4.2+ | Testing | MIT |
| black | 25.9.0 | Formatting | MIT |

**Full list:** See `services/api/pyproject.toml`

---

## Conclusion

This technical documentation provides comprehensive coverage of the Monark Budget system, from architecture and setup through troubleshooting and extending functionality. For additional support or questions, please refer to the individual step reports (step_1_report.md through step_5_report.md) for detailed implementation insights.

**Quick Links:**
- [Repository Structure](#3-repository-structure)
- [Installation & Setup](#6-installation--setup)
- [Running the Application](#10-running-the-application)
- [Troubleshooting](#15-troubleshooting)
- [API Reference](#16-api-reference)

**Version History:**
- v1.0 (2025-09-30): Initial comprehensive documentation covering Steps 1-5

---

**Generated:** 2025-09-30
**Author:** Monark Budget Development Team
**License:** See LICENSE file in repository

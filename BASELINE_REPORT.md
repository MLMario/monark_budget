# Baseline Understanding Report - Monark Budget Agent

**Report Date:** 2025-09-30
**Branch:** vibe_code_experiment
**Python Version:** 3.11.9
**Total Lines of Code:** 5,243 lines (excluding .venv)

---

## 1. Repository Structure & Key Modules

### 1.1 Project Architecture

```
monark_budget/
├── main.py                    # Production entry point - runs agent graph once
├── config.py                  # Centralized Pydantic settings & secrets management
├── services/
│   ├── api/
│   │   ├── app/
│   │   │   ├── agent/
│   │   │   │   ├── agent_graph.py      # LangGraph workflow definition
│   │   │   │   ├── nodes.py            # Node implementations (data import, alerts, reports)
│   │   │   │   ├── state.py            # Pydantic state models
│   │   │   │   └── agent_utilities.py  # Helper functions (LLM calls, email, filters)
│   │   │   └── domain/
│   │   │       └── prompts.py          # LLM prompt templates
│   │   └── pipelines/
│   │       ├── data_import_pipeline.py # Daily data extraction from Monarch Money
│   │       ├── monarchmoney.py         # Custom Monarch Money API client
│   │       ├── mongo_client.py         # MongoDB sync & async clients
│   │       ├── import_functions.py     # Data import helpers
│   │       └── data_parsing_functions.py # Data parsing & transformation
├── test_*.py, unitest.py      # Test files (some outdated)
└── .github/workflows/         # GitHub Actions for daily automation
```

### 1.2 Key Entry Points

1. **`main.py`** - Production entry point that compiles and executes the agent graph
2. **`services/api/pipelines/data_import_pipeline.py`** - Data ingestion from Monarch Money to MongoDB
3. **`.github/workflows/daily_budget_data_git_pipeline.yml`** - Daily automation at 6 AM PST

### 1.3 Core Modules

| Module | Purpose | Key Functions |
|--------|---------|---------------|
| **agent_graph.py** | LangGraph workflow orchestration | `create_budget_graph()` - builds state machine |
| **nodes.py** | Agent node implementations | `import_data_node()`, `daily_overspend_alert_node()`, `period_report_node()`, `email_node()` |
| **state.py** | Pydantic state models | `BudgetAgentState`, `BudgetRow`, `TransactionRow`, `EmailInfo` |
| **agent_utilities.py** | Helper functions | `call_llm()`, `call_llm_reasoning()`, `SendEmail`, `filter_overspent_categories()` |
| **monarchmoney.py** | Custom Monarch Money client | Login, session management, GraphQL queries |
| **mongo_client.py** | Database layer | `MongoDBClient` (sync), `AsyncMongoDBClient` (async) |

---

## 2. Data Flows & External Dependencies

### 2.1 Data Flow Architecture

```
Monarch Money (GraphQL API)
          ↓
  [data_import_pipeline.py]
          ↓
      MongoDB Atlas
    (budget, transactions)
          ↓
    [import_data_node]
          ↓
   LangGraph Agent Nodes
   (LLM processing via Groq)
          ↓
     [email_node]
          ↓
   Gmail SMTP → User Inbox
```

### 2.2 External Dependencies

#### APIs & Services
- **Monarch Money** - Financial data source (GraphQL API, requires custom Device-UUID for OTP bypass)
- **MongoDB Atlas** - Data persistence (collections: `budget`, `transactions`)
- **Groq LLM API** - AI processing (models: llama-3.3-70b-versatile, qwen3-32b, gpt-oss-20b)
- **Gmail SMTP** - Email delivery (smtp.gmail.com:587)
- **GitHub Actions** - Daily automation scheduler

#### Environment Variables Required
```
MONARK_USER         # Monarch Money email
MONARK_PW           # Monarch Money password
MONARK_DD_ID        # Device UUID (to bypass OTP)
MONGO_URL           # MongoDB connection string
MONGO_DB            # MongoDB database name
GROQ_API_KEY        # Groq API key
SMTP_USER           # Gmail SMTP username
SMTP_PASSWORD       # Gmail app password
```

#### Key Python Dependencies
```
langgraph>=0.2.70              # Agent workflow orchestration
langchain-groq>=0.2.4          # Groq LLM integration
pymongo>=4.9.2, motor>=3.7     # MongoDB sync & async
monarchmoney>=0.1.6            # Monarch Money API
pydantic>=2.10.6               # Data validation
pandas>=2.0.0                  # Data processing
loguru>=0.7.3                  # Logging (minimal usage)
```

### 2.3 Data Models

**BudgetRow**: `actual_amount`, `category_name`, `category_group_name`, `planned_cash_flow_amount`, `remaining_amount`, `month`

**TransactionRow**: `amount`, `category_name`, `merchant_name`, `transaction_id`, `createdAt`, `description`

**Agent State**: Stores `current_month_budget`, `current_month_txn`, `previous_month_txn`, `last_day_txn`, `overspend_budget_data`, alerts, reports

---

## 3. Test Coverage, Linting Tools & Logging

### 3.1 Test Infrastructure

**Test Files Found:**
- `unitest.py` - LangGraph node tests (pytest-based, **currently broken** - imports non-existent `PeriodInfo`)
- `test_llm.py` - LLM integration test
- `test_email_sender.py` - SMTP email test
- `testing_nodes.py` - Development test script
- `.pytest_cache/` - Pytest artifacts present

**Test Framework:** pytest 8.4.2 with plugins (anyio, langsmith, opik)

**Current Test Status:** ❌ FAILING
```
ERROR: ImportError: cannot import name 'PeriodInfo' from 'services.api.app.agent.state'
```
The test file references deprecated/removed state models that no longer exist in the codebase.

### 3.2 Linting & Code Quality Tools

**Installed Tools:**
- ✅ `black==25.9.0` - Code formatter
- ✅ `isort==6.0.1` - Import sorter
- ✅ `flake8==7.3.0` - Style guide enforcement
- ✅ `pylint==3.3.8` - Static analysis
- ✅ `autoflake==2.3.1` - Unused import remover
- ✅ `pre-commit>=4.1.0` - Git hooks (not configured)

**Baseline Linting Results:**

**Black Formatting:** ❌ 12 files need reformatting
- `main.py`, `config.py`
- All 10 files in `services/api/`

**Isort:** ❌ Import order issues
- `main.py`, `config.py` incorrectly sorted

**Flake8 (Project Files Only):**
- **config.py**: 49 issues (E251 spacing, F401 unused imports, W291 trailing whitespace)
- **services/api/**: 468 issues (E501 line length, E302/E303 blank lines, W293 whitespace, F401 unused imports)

**Critical Errors:** ✅ 0 (no E9, F63, F7, F82 errors)

### 3.3 Logging Mechanisms

**Current Implementation:**
- ✅ `loguru>=0.7.3` installed but **minimally used**
- Standard `logging` module used in:
  - `main.py` - Basic INFO level logging
  - `agent_graph.py` - Logger initialized but unused
  - `nodes.py` - Logger initialized but unused

**Logging Gaps:**
- ❌ No structured logging framework configured
- ❌ No correlation IDs for request tracing
- ❌ Sensitive data (passwords, tokens) not explicitly redacted
- ❌ Many `print()` statements used instead of logging
- ❌ No centralized logging configuration

---

## 4. Known Pain Points & Bug Reports

### 4.1 Identified Issues from Code Analysis

**Critical:**
1. **Broken Tests** - `unitest.py` imports non-existent `PeriodInfo` model
2. **Device UUID Dependency** - Monarch Money authentication requires manual device ID updates (acknowledged "hacky fix")
3. **Missing Package Management** - No `pip` in venv, relies on `uv` which isn't consistently used

**Medium Priority:**
4. **Code Formatting Inconsistency** - 12 files fail black/isort checks
5. **Unused Imports** - 16 F401 violations across project files
6. **Error Handling Gaps** - Bare `except` clause in `agent_utilities.py:220`
7. **Hard-coded Values** - Email addresses, model names scattered throughout

**Low Priority:**
8. **Line Length Violations** - 53 lines exceed 120 characters
9. **Trailing Whitespace** - 177 violations across project
10. **Missing Docstrings** - No module/function documentation

### 4.2 Recent Commit History Issues

Last 5 commits show pattern of:
- "made small changes in prompt to reduce email length" (repeated 3x)
- "improvement in node logic to handle no transaction data"

**Indicates:**
- Iterative prompt tuning without systematic approach
- Reactive fixes for edge cases (no transaction data)

### 4.3 Configuration Issues

**Git Status:** Uncommitted changes in `pyproject.toml` and `uv.lock` (170 insertions)
- Suggests ongoing dependency management work

---

## 5. Performance Metrics Snapshot

### 5.1 Codebase Metrics

| Metric | Value |
|--------|-------|
| Total Python LOC | 5,243 lines |
| Number of Python files | 17 (excluding tests) |
| Test files | 4 |
| Configuration files | 3 (pyproject.toml, .env, config.py) |

### 5.2 Complexity Indicators

**Node Execution Flow:**
```
START → import_data_node → daily_overspend_alert_node →
daily_suspicious_transaction_alert_node → coordinator_node →
[conditional: both_tasks|daily_tasks] →
[if both_tasks: import_txn_data_for_period_report_node → period_report_node] →
email_node → END
```

**LLM Call Patterns:**
- Multiple sequential LLM calls per node (inefficient)
- No caching or batching strategy
- Acknowledged in README: "we know the process is relatively inefficient and wastes a bit of money"

### 5.3 Resource Dependencies

**MongoDB Collections:**
- `budget` - Full refresh daily (delete_many + insert_many)
- `transactions` - Full refresh daily (up to 2000 records)

**GitHub Actions:**
- Runs daily at 14:00 UTC (6 AM PST)
- ~2 minute wait between data import and agent execution
- Manual dependency installation (no caching)

---

## 6. Baseline Test Execution Results

### 6.1 Automated Test Suite

**Command:** `pytest unitest.py -v`

**Result:** ❌ **FAILED - Collection Error**

```
ERROR: ImportError: cannot import name 'PeriodInfo' from 'services.api.app.agent.state'
```

**Root Cause:** Test file references deprecated state models removed in recent refactor

**Impact:**
- No automated validation of agent nodes
- No regression testing capability
- Cannot establish baseline pass/fail status

### 6.2 Linting Execution

**Flake8 (Critical Errors Only):** ✅ **PASS** (0 critical errors)

**Flake8 (Full Analysis):** ❌ **FAIL** (517 total violations)
- config.py: 49 issues
- services/api/: 468 issues

**Black Formatting:** ❌ **FAIL** (12 files need reformatting)

**Isort:** ❌ **FAIL** (2 files incorrectly sorted)

### 6.3 Manual Execution Test

**Attempted:** Dry-run of `main.py`

**Result:** ❌ **FAILED**
```
ModuleNotFoundError: No module named 'services'
```

**Cause:** Python path configuration issue - venv doesn't include project root

---

## 7. Risk Assessment & Recommendations

### 7.1 High Priority Risks

| Risk | Impact | Mitigation Required |
|------|--------|-------------------|
| **No Working Tests** | Cannot validate changes | Fix `unitest.py` imports, establish test baseline |
| **Manual Device ID Dependency** | System breaks when Monarch updates auth | Implement proper OAuth or session refresh |
| **Bare Exception Handling** | Silent failures | Add explicit exception types & logging |
| **No Structured Logging** | Difficult to debug production issues | Implement centralized logging with correlation IDs |

### 7.2 Medium Priority Improvements

- **Code Quality**: Run black, isort, autoflake to fix 517+ style violations
- **Dependency Management**: Standardize on uv or pip, document in README
- **Error Handling**: Replace bare `except` with specific exception types
- **Documentation**: Add docstrings to all public functions/classes

### 7.3 Low Priority Optimizations

- **LLM Efficiency**: Implement batching and caching strategies
- **MongoDB**: Consider incremental updates vs full refresh
- **Configuration**: Move hard-coded values to config/environment

---

## 8. Comparison Point for Future Steps

### 8.1 Baseline Established

✅ **Completed:**
- Repository structure catalogued
- Data flows documented
- External dependencies identified
- Test infrastructure reviewed
- Linting tools executed
- Known issues flagged

❌ **Unable to Complete:**
- Automated test suite baseline (tests broken)
- Performance metrics (cannot execute main.py)

### 8.2 Next Steps (Per Optimization Plan)

**Step 2: Style & Redundancy**
1. Run `black .` and `isort .` to fix formatting
2. Run `autoflake --remove-all-unused-imports --in-place --recursive .`
3. Fix `unitest.py` import errors
4. Re-run test suite to establish baseline

**Step 3: Efficiency & Correctness**
1. Profile LLM call patterns
2. Fix bare exception handling
3. Add missing error cases

**Step 4: Error Handling**
1. Review all external API interactions
2. Add retry logic for Monarch Money, MongoDB, Groq
3. Centralize exception definitions

**Step 5: Structured Logging**
1. Configure loguru as primary logger
2. Add correlation IDs to agent runs
3. Replace all `print()` statements
4. Implement sensitive data redaction

---

## Appendix: Tool Versions & Environment

**Python:** 3.11.9
**Package Manager:** uv (pip unavailable in venv)
**Virtual Environment:** `services/api/.venv/`
**Git Branch:** vibe_code_experiment
**Uncommitted Changes:** services/api/pyproject.toml, services/api/uv.lock

**Key Package Versions:**
- pytest: 8.4.2
- black: 25.9.0
- flake8: 7.3.0
- pylint: 3.3.8
- langgraph: 0.6.7
- langchain-groq: 0.3.8

---

**Report Generated By:** Claude Code Baseline Analysis Agent
**Methodology:** Automated repository audit, static analysis, test execution, dependency review

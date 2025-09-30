# Monark Budget – Technical Documentation

This document captures the engineering details needed to run, extend, and operate the Monark Budget agent. It complements the product-focused `README.md` by focusing on architecture, data flow, configuration, and developer workflows.

## System Overview

The Monark Budget project automates daily and periodic financial insights by combining three subsystems:

1. **Data ingestion** – An asynchronous pipeline (`services/api/pipelines/data_import_pipeline.py`) logs into Monarch Money, downloads the most recent budget and transaction data, and writes it to MongoDB via the `MongoDBClient` helpers.【F:services/api/pipelines/data_import_pipeline.py†L1-L52】【F:services/api/pipelines/import_functions.py†L1-L87】【F:services/api/pipelines/mongo_client.py†L1-L56】
2. **Agent workflow** – A LangGraph state machine (`main.py`, `services/api/app/agent/*`) orchestrates multiple LLM-backed tasks to analyse the stored data, author daily alerts, and optionally compile weekly/monthly reports.【F:main.py†L1-L66】【F:services/api/app/agent/agent_graph.py†L1-L94】【F:services/api/app/agent/nodes.py†L1-L217】
3. **Notification delivery** – A mailer node renders the compiled insights as HTML and delivers them over SMTP using credentials managed in `config.Settings`.【F:services/api/app/agent/nodes.py†L218-L310】【F:services/api/app/agent/agent_utilities.py†L1-L174】【F:config.py†L1-L78】

The GitHub Actions workflow `.github/workflows/daily_budget_data_git_pipeline.yml` stitches these pieces into a daily run: ingest data, wait for persistence, execute the agent, and send the report.【F:.github/workflows/daily_budget_data_git_pipeline.yml†L1-L83】

## Repository Layout

| Path | Purpose |
| --- | --- |
| `main.py` | Production entry point that compiles and runs the LangGraph workflow once per invocation.【F:main.py†L1-L66】 |
| `config.py` | Centralised pydantic settings object; reads secrets for Monarch Money, MongoDB, Groq, and SMTP integrations.【F:config.py†L1-L78】 |
| `services/api/app/agent/` | LangGraph graph definition, state models, and node implementations that encapsulate each agent task.【F:services/api/app/agent/agent_graph.py†L1-L94】【F:services/api/app/agent/state.py†L1-L109】【F:services/api/app/agent/nodes.py†L1-L310】 |
| `services/api/app/domain/prompts.py` | Prompt templates wrapped with optional Opik versioning for each LLM call.【F:services/api/app/domain/prompts.py†L1-L142】 |
| `services/api/pipelines/` | Data-import helpers for Monarch Money and MongoDB, plus utility parsers for ingestion workflows.【F:services/api/pipelines/data_import_pipeline.py†L1-L52】【F:services/api/pipelines/import_functions.py†L1-L87】【F:services/api/pipelines/mongo_client.py†L1-L56】 |
| `.github/workflows/daily_budget_data_git_pipeline.yml` | Scheduled CI job that refreshes data and executes the agent on GitHub-hosted runners.【F:.github/workflows/daily_budget_data_git_pipeline.yml†L1-L83】 |
| `test_*.py` | Developer-oriented scripts to manually exercise SMTP and LLM integrations; they require the same secrets as production runs.【F:test_email_sender.py†L1-L37】【F:test_llm.py†L1-L47】 |

## Runtime Architecture

### LangGraph state & transitions

The agent operates on the `BudgetAgentState` Pydantic model defined in `state.py`, which stores metadata, imported datasets, generated artefacts, and process flags.【F:services/api/app/agent/state.py†L1-L109】 The graph assembled in `agent_graph.py` wires nodes in the following order:

1. `import_data_node` loads the latest budget snapshot and previous-day transactions, filters overspent categories, and initialises the state.【F:services/api/app/agent/nodes.py†L1-L104】
2. `daily_overspend_alert_node` summarises overspent categories via LLM and marks the corresponding flag.【F:services/api/app/agent/nodes.py†L114-L135】
3. `daily_suspicious_transaction_alert_node` classifies each transaction with a reasoning model, builds a comedic recap for any non-compliant spend, and updates the daily alert status.【F:services/api/app/agent/nodes.py†L137-L198】
4. `coordinator_node` inspects the calendar and decides whether the run should include the period report pathway (Mondays and month transitions).【F:services/api/app/agent/nodes.py†L106-L112】【F:services/api/app/agent/agent_utilities.py†L20-L36】
5. If required, `import_txn_data_for_period_report_node` fetches month-to-date and prior-month transactions, preparing them for report generation.【F:services/api/app/agent/nodes.py†L200-L246】
6. `period_report_node` iterates overspent categories, calls the reasoning model for driver analysis, and compiles the multi-section report text.【F:services/api/app/agent/nodes.py†L248-L298】
7. `email_node` concatenates any generated artefacts, asks an LLM to convert the message into HTML, validates the markup, and dispatches the email.【F:services/api/app/agent/nodes.py†L300-L310】

### External services

* **Monarch Money** – Accessed via the adjusted client in `services/api/pipelines/monarchmoney.py` through the helper functions in `import_functions.py`. Authentication requires device and credential secrets to bypass OTP.【F:services/api/pipelines/import_functions.py†L1-L87】
* **MongoDB** – Budget and transaction collections back the agent state. `MongoDBClient` performs batch exports while `AsyncMongoDBClient` supports asynchronous reads used inside LangGraph nodes.【F:services/api/pipelines/mongo_client.py†L1-L56】
* **Groq LLM API** – Both `call_llm` and `call_llm_reasoning` wrap Groq chat completions with configurable models, reasoning modes, and prompt formatting.【F:services/api/app/agent/agent_utilities.py†L38-L118】
* **SMTP (Gmail)** – Email delivery uses `SendEmail.send_email_async` with TLS over `smtp.gmail.com:587`, leveraging credentials loaded from `Settings`.【F:services/api/app/agent/agent_utilities.py†L132-L173】【F:config.py†L53-L78】

## Environment Configuration

Create a `.env` file in the project root (or set environment variables) with the fields consumed by `Settings`. All secrets must be provisioned for both the ingestion pipeline and the agent to succeed.【F:config.py†L1-L78】

| Variable | Description |
| --- | --- |
| `MONARK_USER` / `MONARK_PW` | Monarch Money login used to pull transactions and budgets. |
| `MONARK_DD_ID` | Device UUID required to skip the OTP challenge during login. |
| `MONGO_URL` / `MONGO_DB` | Connection string and database name for the MongoDB instance storing imported data. |
| `GROQ_API_KEY` | Token for Groq’s LLM APIs used across all agent prompts. |
| `SMTP_USER` / `SMTP_PASSWORD` | Credentials for the Gmail SMTP account that distributes the reports. |

## Local Development Setup

1. **Install Python 3.11+.** The workflows and `pyproject.toml` target Python ≥3.11.【F:services/api/pyproject.toml†L1-L39】
2. **Create a virtual environment** and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e ./services/api
   ```
   Installing the package from `services/api` pulls the dependencies declared in `pyproject.toml` (LangGraph, LangChain, Mongo, Groq, etc.).【F:services/api/pyproject.toml†L1-L39】
3. **Provide configuration** by placing the `.env` file next to `config.py` or in the project root as described above.【F:config.py†L1-L44】
4. **Start supporting services** (MongoDB instance, internet access for Groq and Monarch Money, SMTP access) before running the pipelines.

## Running Data & Agent Pipelines

### 1. Refresh Monarch Money data

The import pipeline is meant to be run asynchronously so the Mongo collections contain the latest budget and transaction documents:

```bash
python -m services.api.pipelines.data_import_pipeline
```
This command logs into Monarch Money, downloads budgets and transactions, and replaces the Mongo collections with the fresh documents.【F:services/api/pipelines/data_import_pipeline.py†L1-L52】【F:services/api/pipelines/mongo_client.py†L7-L24】

### 2. Execute the agent

Once Mongo is populated, invoke the agent entry point:

```bash
python -m main
```
`main.py` builds the `BudgetAgentState`, compiles the LangGraph, and runs it to completion, printing a short summary and delegating email delivery to the final node.【F:main.py†L1-L66】【F:services/api/app/agent/agent_graph.py†L1-L94】

### 3. Automated daily run

GitHub Actions orchestrates the above steps on a schedule (14:00 UTC) using repository secrets, waits for Mongo writes to settle, and then runs the agent. Review `.github/workflows/daily_budget_data_git_pipeline.yml` when modifying dependencies or runtime steps.【F:.github/workflows/daily_budget_data_git_pipeline.yml†L1-L83】

## Testing & Verification

* `test_email_sender.py` – Sends a plain-text test email using the configured SMTP credentials. Use cautiously to avoid spamming real inboxes.【F:test_email_sender.py†L1-L37】
* `test_llm.py` – Pulls budget data from Mongo, filters overspent categories, and exercises the `call_llm` helper with the overspend prompt for manual verification.【F:test_llm.py†L1-L47】

Both scripts expect the same `.env` configuration as the main application.

## Extending the System

* **Adding new tasks** – Implement a node in `services/api/app/agent/nodes.py`, extend `BudgetAgentState` if new artefacts are required, and register the node plus any conditional routing in `agent_graph.py`.
* **Modifying prompts** – Update the prompt templates in `services/api/app/domain/prompts.py`. The `Prompt` wrapper will attempt to version prompts with Opik when credentials are available; otherwise it falls back to local strings.【F:services/api/app/domain/prompts.py†L1-L38】
* **Integrating new data sources** – Extend the ingestion pipeline to call additional endpoints via `MonarkImport`, then persist the results to MongoDB through `MongoDBClient` or dedicated collections.【F:services/api/pipelines/import_functions.py†L1-L87】【F:services/api/pipelines/mongo_client.py†L1-L56】

Keep the GitHub Actions workflow in sync with any new dependencies to ensure scheduled runs remain green.【F:.github/workflows/daily_budget_data_git_pipeline.yml†L33-L76】


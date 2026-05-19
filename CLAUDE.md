# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
python -m pytest tests/ -v

# Run tests for a specific phase
python -m pytest tests/test_foundation.py -v
python -m pytest tests/test_risk_analyst.py -v
python -m pytest tests/test_compliance_officer.py -v

# Run a single test
python -m pytest tests/test_risk_analyst.py::TestRiskAnalystAgent::test_agent_initialization -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html

# Start Jupyter notebooks
jupyter notebook notebooks/
```

## Architecture

This is a multi-agent AI system for automating Suspicious Activity Report (SAR) processing in financial compliance. The data flow is:

```
CSV Data -> DataLoader -> CaseData -> RiskAnalystAgent -> RiskAnalystOutput
                                                     -> Human Review Gate
                                                     -> ComplianceOfficerAgent -> ComplianceOfficerOutput -> SAR Filing
```

### Source Modules (`src/`)

- **`foundation_sar.py`** — Core Pydantic schemas and utilities. Contains `CustomerData`, `AccountData`, `TransactionData`, `CaseData`, `RiskAnalystOutput`, `ComplianceOfficerOutput`, `ExplainabilityLogger`, and `DataLoader`. This is the dependency of both agents and must be implemented first.

- **`risk_analyst_agent.py`** — `RiskAnalystAgent` uses Chain-of-Thought prompting to classify suspicious activity into one of: `Structuring`, `Sanctions`, `Fraud`, `Money_Laundering`, `Other`. Takes a `CaseData` object, calls OpenAI, returns `RiskAnalystOutput`.

- **`compliance_officer_agent.py`** — `ComplianceOfficerAgent` uses ReACT (Reasoning + Action) prompting to generate regulatory SAR narratives (<=120 words) from `RiskAnalystOutput`. Returns `ComplianceOfficerOutput`.

### Key Schema Relationships

- `CaseData` aggregates one `CustomerData`, a list of `AccountData`, and a list of `TransactionData`.
- `DataLoader.create_case_from_data()` filters accounts and transactions by `customer_id`/`account_id` automatically.
- Both agents accept an `openai_client` and `explainability_logger` in their constructors. **The tests expect these stored as `self.client` and `self.logger`** (not `self.openai_client` / `self.explainability_logger`).

### Test Contracts (critical for passing tests)

The test suite (`tests/test_risk_analyst.py`) enforces these specifics:

- `RiskAnalystAgent.__init__` must store `openai_client` as `self.client` and `explainability_logger` as `self.logger`.
- `analyze_case` API call must use `temperature=0.3` and `max_tokens=1000`.
- `_extract_json_from_response("")` must raise `ValueError` with message `"No JSON content found"`.
- When JSON parsing fails, `analyze_case` must raise `ValueError("Failed to parse Risk Analyst JSON output")` and log `reasoning="JSON parsing failed"`.
- The agent must expose `_format_accounts(accounts)` and `_format_transactions(transactions)` as separate methods (not merged into `_format_case_for_prompt`). Transaction format must be: `"1. YYYY-MM-DD: <type> $<amount>"`.

### Test Skip Logic

Tests auto-skip when a module is not yet implemented. The skip guard checks:
1. `system_prompt` exists, has length > 50, and contains no `"TODO"`.
2. `analyze_case` raises an exception (or returns non-None) when called.
3. `_extract_json_from_response` method exists.

### Data

`data/customers.csv`, `data/accounts.csv`, `data/transactions.csv` contain 150 customers, 200+ accounts, and 500+ transactions with synthetic suspicious patterns for local testing.

### Outputs

Generated SAR documents and audit logs go to `outputs/filed_sars/` and `outputs/audit_logs/`. `ExplainabilityLogger` writes append-only JSONL to the specified log file path and also keeps entries in `self.entries` list for test assertions.

### Environment

Requires `OPENAI_API_KEY` in a `.env` file (Vocareum keys start with `voc-`; base URL is `https://openai.vocareum.com/v1`). Use `python-dotenv` `load_dotenv()` at module level.
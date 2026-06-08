# Foundation SAR - Core Data Schemas and Utilities

import json
import pandas as pd
from datetime import date,datetime, timezone
from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field, field_validator,ValidationInfo
import uuid
import os


"""
def parse_date_field(value, field_name: str) -> str:
    #Validates yyyy-mm-dd format and returns the string as-is.
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string in yyyy-mm-dd format")
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"{field_name} must be in yyyy-mm-dd format (e.g. 1990-06-15)")
    return value
"""

class CustomerData(BaseModel):
    """Customer information schema with validation"""

    customer_id: str = Field(..., description="Unique identifier like 'CUST_0001'")
    name: str = Field(..., min_length=3, max_length=100, description="Full customer name like 'John Smith'")
    date_of_birth: date = Field(..., description="Date in YYYY-MM-DD format like '1985-03-15'")
    ssn_last_4: str = Field(..., exclude=True, min_length=4, max_length=4, description="Last 4 digits like '1234'")

    @field_validator("ssn_last_4", mode="before")
    @classmethod
    def coerce_ssn_to_str(cls, v) -> str:
        """Coerce int/float SSN values loaded by pandas into zero-padded 4-char strings."""
        if isinstance(v, float):
            v = int(v)
        if isinstance(v, int):
            return str(v).zfill(4)
        return str(v)
    address: str = Field(..., description="Full address like '123 Main St, City, ST 12345'")
    customer_since: date = Field(..., description="Date in YYYY-MM-DD format like '2010-01-  15'")
    risk_rating: Literal['Low', 'Medium', 'High'] = Field(..., description="Risk assessment — Low, Medium, or High")
    phone: Optional[str] = Field(None, description="Phone number like '555-123-4567'")
    occupation: Optional[str] = Field(None, description="Job title like 'Software Engineer'")
    annual_income: Optional[int] = Field(None, description="Yearly income like 75000")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        parts = v.strip().split()
        if len(parts) < 2:
            raise ValueError("Name must include both a first and last name")
        return " ".join(
            "-".join(word.capitalize() for word in part.split("-"))
            for part in parts
        )

    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, v: date) -> date:
        if v >= date.today():
            raise ValueError("date_of_birth must be in the past")
        return v

    @field_validator("customer_since")
    @classmethod
    def validate_customer_since(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("customer_since cannot be future date")
        return v

    @field_validator("risk_rating", mode="before")
    @classmethod
    def normalise_risk_rating(cls, v) -> str:
        if isinstance(v, str):
            return v.strip().capitalize()
        return v


class AccountData(BaseModel):
    """Account information schema with validation"""
    
    account_id: str = Field(..., description="Unique identifier like 'CUST_0001_ACC_1'")
    customer_id: str = Field(..., description="Must match CustomerData.customer_id")
    account_type: Literal['Checking', 'Savings', 'Money_Market', 'Business_Checking'] = Field(..., description="Type like 'Checking', 'Savings', or 'Money_Market'")
    opening_date: date = Field(..., description="Date in YYYY-MM-DD format like '2010-01-15'")
    current_balance: float = Field(..., description="Current balance (can be negative for overdrafts)")
    average_monthly_balance: float = Field(..., description="Average monthly balance")          
    status: Literal['Active', 'Closed', 'Suspended'] = Field(..., description="Status like 'Active', 'Closed', or 'Suspended'")

    @field_validator("customer_id")
    @classmethod
    def customer_must_exist(cls, v: str, info: ValidationInfo) -> str:
        if info.context is None:
            return v  # no context provided — skip the check

        valid_ids: set[str] = info.context.get("valid_customer_ids", set())

        if v not in valid_ids:
            raise ValueError(f"customer_id '{v}' does not exist in CustomerData")
        return v

    @field_validator("account_type", "status", mode="before")
    @classmethod
    def normalise_enum_fields(cls, v) -> str:
        """Handles case variations: 'checking' → 'Checking', 'ACTIVE' → 'Active'."""
        if isinstance(v, str):
            normalized = v.strip().lower()
            if normalized == "money_market":
                return "Money_Market"
            if normalized == "business_checking":
                return "Business_Checking"
            return v.strip().capitalize()
        return v

    @field_validator("opening_date")
    @classmethod
    def validate_opening_date(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("opening_date cannot be a future date")
        return v

class TransactionData(BaseModel):
    """Transaction information schema with validation """
    
    transaction_id: str = Field(..., description="Unique identifier like 'TXN_B24455F3'")
    account_id: str = Field(..., description="unique account identifier like 'CUST_0001_ACC_1'")
    transaction_date: date = Field(..., description="Date in YYYY-MM-DD format")
    transaction_type: str = Field(..., description="Type like 'Cash_Deposit', 'Wire_Transfer'")
    amount: float = Field(..., description="Transaction amount (negative for withdrawals)")
    description: str = Field(..., description="Description like 'Cash deposit at branch'")
    method: Literal['ATM', 'Electronic', 'Online', 'Branch', 'Mobile', 'Cash', 'Wire'] = Field(..., description="The Transaction method")
    counterparty: Optional[str] = Field(None, description="Other party in transaction")
    location: Optional[str] = Field(None, description="Transaction location or branch")

    @field_validator("transaction_date")
    @classmethod
    def validate_transaction_date(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("transaction_date cannot be a future date")
        if v.year < 1900:
            raise ValueError("transaction_date is unreasonably old")
        return v

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v == 0:
            raise ValueError("transaction amount cannot be zero")
        if abs(v) > 1_000_000_000:
            raise ValueError("transaction amount exceeds reasonable bounds (>$1B)")
        return v

    @field_validator("counterparty", "location", mode="before")
    @classmethod
    def coerce_nan_to_none(cls, v):
        """Convert pandas NaN values to None before Pydantic type checking."""
        if v is None:
            return None
        try:
            import math
            if isinstance(v, float) and math.isnan(v):
                return None
        except (TypeError, ValueError):
            pass
        return v if v != "" else None

    @field_validator("account_id")
    @classmethod
    def account_must_exist(cls, v: str, info: ValidationInfo) -> str:
        if info.context is None:
            return v  # no context provided — skip the check

        valid_ids: set[str] = info.context.get("valid_account_ids", set())

        if v not in valid_ids:
            raise ValueError(f"account_id '{v}' does not exist in AccountData")
        return v
   
class CaseData(BaseModel):
    """Unified case object combining all data sources""" 

    case_id: str = Field(..., description="Unique case identifier (generate with uuid)")
    customer: CustomerData = Field(..., description="Customer information object")
    accounts: List[AccountData] = Field(..., description="List of customer's accounts")
    transactions: List[TransactionData] = Field(..., description="List of suspicious transactions")
    case_created_at: str = Field(..., description="ISO timestamp when case was created")
    data_sources: Dict[str, str] = Field(..., description="Source tracking with keys like: 'customer_source', 'account_source', 'transaction_source'")          

    @field_validator('transactions')
    @classmethod
    def validate_transactions(cls, v: List[TransactionData], info: ValidationInfo) -> List[TransactionData]:
        if not v:
            raise ValueError("Case must include at least one transaction")
        
        if info.context is None:
            return v
        accounts: List[AccountData] = info.context.get("accounts", [])
        account_ids = {acc.account_id for acc in accounts}
        
        for txn in v:
            if txn.account_id not in account_ids:
                raise ValueError(f"Transaction {txn.transaction_id} references account_id '{txn.account_id}' which is not in the case accounts")
        
        return v

class RiskAnalystOutput(BaseModel):
    """Risk Analyst agent structured output"""
    
    classification: Literal['Structuring', 'Sanctions', 'Fraud', 'Money_Laundering', 'Other'] = Field(..., description="Type of suspicious activity")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence level between 0.0 and 1.0")
    reasoning: str = Field(..., max_length=500, description="Detailed reasoning for risk assessment")
    key_indicators: List[str] = Field(..., description="List of key indicators that contributed to the risk assessment")
    risk_level: Literal['Low', 'Medium', 'High', 'Critical'] = Field(..., description="Overall risk level assessment")

class ComplianceOfficerOutput(BaseModel):
    """Compliance Officer agent structured output"""

    reasoning_phase: Optional[str] = Field(
        None,
        description="ReACT REASONING phase: classification review, regulatory requirements, citations, and narrative plan"
    )
    action_phase: Optional[str] = Field(
        None,
        description="ReACT ACTION phase: drafting decisions and verification steps taken"
    )
    narrative: str = Field(..., max_length=1000, description="Regulatory narrative text (max 1000 chars for ≤200 words)")
    narrative_reasoning: str = Field(..., max_length=500, description="Reasoning for narrative construction (max 500 chars)")
    regulatory_citations: List[str] = Field(..., description="List of relevant regulations")
    completeness_check: bool = Field(..., description="Whether narrative meets all requirements")

    @field_validator("reasoning_phase", "action_phase")
    @classmethod
    def validate_phase_content(cls, v: Optional[str]) -> Optional[str]:
        """When present, ensure each ReACT phase field contains substantive content."""
        if v is not None and not v.strip():
            raise ValueError("ReACT phase field cannot be blank — provide substantive content or omit the field")
        return v.strip() if v else v


# ===== IMPLEMENT AUDIT LOGGING =====

class ExplainabilityLogger:
    """Simple audit logging for compliance trails"""
    
    def __init__(self, log_file: str = "sar_audit.jsonl"):
        # TODO: Initialize with log_file path and empty entries list
        self.log_file = log_file
        self.entries = []
      
    
    def log_agent_action(self, 
                         agent_type: str, 
                         action: str, case_id: str, 
                        input_data: Dict, 
                        output_data: Dict, 
                        reasoning: str, 
                        execution_time_ms: float, 
                        success: bool = True, 
                        error_message: Optional[str] = None):
        """Log an agent action with essential context"""

        entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'case_id': case_id,
            'agent_type': agent_type,
            'action': action,
            'input_summary': str(input_data),
            'output_summary': str(output_data),
            'reasoning': reasoning,
            'execution_time_ms': execution_time_ms,
            'success': success,
            'error_message': error_message
        }

        self.entries.append(entry)

        with open(self.log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')


# ===== TODO: IMPLEMENT DATA LOADER =====

class DataLoader:
    """Simple loader that creates case objects from CSV data"""

    def __init__(self, explainability_logger: ExplainabilityLogger):
        # Step from __init__: just store the logger
        self.logger = explainability_logger

    def create_case_from_data(
        self,
        customer_data: Dict,
        account_data: List[Dict],
        transaction_data: List[Dict]
    ) -> CaseData:

        # start the clock
        start_time = datetime.now()

        # Unique ID for this case
        case_id = str(uuid.uuid4())

        try:
            #validate and create the customer object
            customer = CustomerData.model_validate(customer_data)

            # filter accounts that belong to this customer
            customer_accounts_raw = [
                acc for acc in account_data
                if acc["customer_id"] == customer.customer_id
            ]

            #create AccountData objects from filtered accounts
            accounts = [
                AccountData.model_validate(
                    acc,
                    context={"valid_customer_ids": {customer.customer_id}}
                )
                for acc in customer_accounts_raw
            ]

            # build a set of this customer's account IDs
            account_ids = {acc.account_id for acc in accounts}

            #filter transactions that belong to those accounts
            customer_transactions_raw = [
                txn for txn in transaction_data
                if txn["account_id"] in account_ids
            ]

            # TransactionData objects
            transactions = [
                TransactionData.model_validate(txn)
                for txn in customer_transactions_raw
            ]

            if not transactions:
                execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
                self.logger.log_agent_action(
                    agent_type="DataLoader",
                    action="create_case_from_data",
                    case_id=case_id,
                    input_data={"customer_id": customer.customer_id},
                    output_data={},
                    reasoning="No transactions found for customer — cannot create SAR case",
                    execution_time_ms=execution_time_ms,
                    success=False,
                    error_message="No matching transactions found"
                )
                raise ValueError(
                    f"No transactions found for customer '{customer.customer_id}' "
                    "— cannot create a SAR case without transaction data"
                )

            
            case = CaseData(
                case_id=case_id,
                customer=customer,
                accounts=accounts,
                transactions=transactions,
                case_created_at=datetime.now(timezone.utc).isoformat(),
                data_sources={
                    "customer_source":    f"csv_extract_{datetime.now().strftime('%Y%m%d')}",
                    "account_source":     f"csv_extract_{datetime.now().strftime('%Y%m%d')}",
                    "transaction_source": f"csv_extract_{datetime.now().strftime('%Y%m%d')}"
                }
            )

          
            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # log success
            self.logger.log_agent_action(
                agent_type="DataLoader",
                action="create_case",
                case_id=case_id,
                input_data={
                    "customer_id":    customer.customer_id,
                    "num_accounts":   len(accounts),
                    "num_transactions": len(transactions)
                },
                output_data={
                    "case_id": case_id,
                    "status":  "created"
                },
                reasoning=(
                    f"Loaded {len(accounts)} account(s) and "
                    f"{len(transactions)} transaction(s) "
                    f"for customer {customer.customer_id}"
                ),
                execution_time_ms=execution_time_ms,
                success=True
            )

            
            return case

        except Exception as e:
            # Log failure then re-raise so the caller knows something went wrong
            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            self.logger.log_agent_action(
                agent_type="DataLoader",
                action="create_case",
                case_id=case_id,
                input_data={"customer_data": customer_data},
                output_data={},
                reasoning="Case creation failed — see error_message",
                execution_time_ms=execution_time_ms,
                success=False,
                error_message=str(e)
            )

            raise

# ===== HELPER FUNCTIONS (PROVIDED) =====

def load_csv_data(data_dir: str = "data/") -> tuple:
    """Helper function to load all CSV files with dtype coercion and NaN handling.

    Returns:
        tuple: (customers_df, accounts_df, transactions_df)
    """
    try:
        customers_df = pd.read_csv(
            f"{data_dir}/customers.csv",
            dtype={"ssn_last_4": str}
        )
        customers_df["phone"] = customers_df["phone"].fillna("")

        accounts_df = pd.read_csv(f"{data_dir}/accounts.csv")

        transactions_df = pd.read_csv(f"{data_dir}/transactions.csv")
        transactions_df["counterparty"] = transactions_df["counterparty"].fillna("")
        transactions_df["location"] = transactions_df["location"].fillna("")

        return customers_df, accounts_df, transactions_df
    except FileNotFoundError as e:
        raise FileNotFoundError(f"CSV file not found: {e}")
    except Exception as e:
        raise Exception(f"Error loading CSV data: {e}")

if __name__ == "__main__":
    print("🏗️  Foundation SAR Module")
    print("Core data schemas and utilities for SAR processing")
    print("\n📋 TODO Items:")
    print("• Implement Pydantic schemas based on CSV data")
    print("• Create ExplainabilityLogger for audit trails")
    print("• Build DataLoader for case object creation")
    print("• Add comprehensive error handling")
    print("• Write unit tests for all components")

# Foundation SAR - Core Data Schemas and Utilities
# TODO: Implement core Pydantic schemas and data processing utilities

"""
This module contains the foundational components for SAR processing:

1. Pydantic Data Schemas:
   - CustomerData: Customer profile information
   - AccountData: Account details and balances  
   - TransactionData: Individual transaction records
   - CaseData: Unified case combining all data sources
   - RiskAnalystOutput: Risk analysis results
   - ComplianceOfficerOutput: Compliance narrative results

2. Utility Classes:
   - ExplainabilityLogger: Audit trail logging
   - DataLoader: Combines fragmented data into case objects

YOUR TASKS:
- Study the data files in data/ folder
- Design Pydantic schemas that match the CSV structure
- Implement validation rules for financial data
- Create a DataLoader that builds unified case objects
- Add proper error handling and logging
"""

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
    ssn_last_4: str = Field(..., exclude=True,  min_length=4, max_length=4,description="Last 4 digits like '1234'")
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
            if v.strip().lower() == "money_market":
                return "Money_Market"
            return v.strip().capitalize()
        return v

    @field_validator("opening_date")
    @classmethod
    def validate_opening_date(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("opening_date cannot be a future date")
        return v

class TransactionData(BaseModel):
    """Transaction information schema with validation
    
    REQUIRED FIELDS (examine data/transactions.csv):
    - transaction_id: str = Unique identifier like "TXN_B24455F3"
    - account_id: str = Must match AccountData.account_id
    - transaction_date: date = Date in YYYY-MM-DD format
    - transaction_type: str = Type like "Cash_Deposit", "Wire_Transfer"
    - amount: float = Transaction amount (negative for withdrawals)
    - description: str = Description like "Cash deposit at branch"
    - method: str = Method like "Wire", "ACH", "ATM", "Teller"
    
    OPTIONAL FIELDS:
    - counterparty: Optional[str] = Other party in transaction
    - location: Optional[str] = Transaction location or branch
    
    HINT: amount can be negative for debits/withdrawals
    HINT: Use descriptive field descriptions for clarity
    """
    # TODO: Implement the TransactionData schema
    pass

class CaseData(BaseModel):
    """Unified case object combining all data sources""" 
    # TODO: Implement the CaseData schema with validation
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
        
        accounts: List[AccountData] = info.context.get("accounts", [])
        account_ids = {acc.account_id for acc in accounts}
        
        for txn in v:
            if txn.account_id not in account_ids:
                raise ValueError(f"Transaction {txn.transaction_id} references account_id '{txn.account_id}' which is not in the case accounts")
        
        return v

class RiskAnalystOutput(BaseModel):
    """Risk Analyst agent structured output
    
    REQUIRED FIELDS (for Chain-of-Thought agent output):
    - classification: Literal['Structuring', 'Sanctions', 'Fraud', 'Money_Laundering', 'Other']
    - confidence_score: float = Confidence between 0.0 and 1.0 (use ge=0.0, le=1.0)
    - reasoning: str = Step-by-step analysis reasoning (max 500 chars)
    - key_indicators: List[str] = List of suspicious indicators found
    - risk_level: Literal['Low', 'Medium', 'High', 'Critical'] = Risk assessment
    
    HINT: Use Literal types to restrict classification and risk_level values
    HINT: Use Field(..., ge=0.0, le=1.0) for confidence_score validation
    HINT: Use Field(..., max_length=500) for reasoning length limit
    """
    # TODO: Implement the RiskAnalystOutput schema
    pass

class ComplianceOfficerOutput(BaseModel):
    """Compliance Officer agent structured output
    
    REQUIRED FIELDS (for ReACT agent output):
    - narrative: str = Regulatory narrative text (max 1000 chars for ≤200 words)
    - narrative_reasoning: str = Reasoning for narrative construction (max 500 chars)
    - regulatory_citations: List[str] = List of relevant regulations like:
      * "31 CFR 1020.320 (BSA)"
      * "12 CFR 21.11 (SAR Filing)"
      * "FinCEN SAR Instructions"
    - completeness_check: bool = Whether narrative meets all requirements
    
    HINT: Use Field(..., max_length=1000) for narrative length limit
    HINT: Use Field(..., max_length=500) for reasoning length limit
    HINT: Use bool type for completeness_check
    """
    # TODO: Implement the ComplianceOfficerOutput schema
    pass

# ===== TODO: IMPLEMENT AUDIT LOGGING =====

class ExplainabilityLogger:
    """Simple audit logging for compliance trails

    ATTRIBUTES:
    - log_file: str = Path to JSONL log file (default: "sar_audit.jsonl")
    - entries: List = In-memory storage of log entries

    METHODS:
    - log_agent_action(): Logs agent actions with structured data
    
    LOG ENTRY STRUCTURE (use this exact format):
    {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'case_id': case_id,
        'agent_type': agent_type,  # "DataLoader", "RiskAnalyst", "ComplianceOfficer"
        'action': action,          # "create_case", "analyze_case", "generate_narrative"
        'input_summary': str(input_data),
        'output_summary': str(output_data),
        'reasoning': reasoning,
        'execution_time_ms': execution_time_ms,
        'success': success,        # True/False
        'error_message': error_message  # None if success=True
    }
    
    HINT: Write each entry as JSON + newline to create JSONL format
    HINT: Use 'a' mode to append to log file
    HINT: Store entries in self.entries list AND write to file
    """
    
    def __init__(self, log_file: str = "sar_audit.jsonl"):
        # TODO: Initialize with log_file path and empty entries list
        pass
    
    def log_agent_action(self, agent_type: str, action: str, case_id: str, 
                        input_data: Dict, output_data: Dict, reasoning: str, 
                        execution_time_ms: float, success: bool = True, 
                        error_message: Optional[str] = None):
        """Log an agent action with essential context
        
        IMPLEMENTATION STEPS:
        1. Create entry dictionary with all fields (see structure above)
        2. Add entry to self.entries list
        3. Write entry to log file as JSON line
        
        HINT: Use json.dumps(entry) + '\n' for JSONL format
        HINT: Use datetime.now(timezone.utc).isoformat() for timestamp
        HINT: Convert input_data and output_data to strings with str()
        """
        # TODO: Implement logging with structured entry creation and file writing
        pass

# ===== TODO: IMPLEMENT DATA LOADER =====

class DataLoader:
    """Simple loader that creates case objects from CSV data
    
    ATTRIBUTES:
    - logger: ExplainabilityLogger = For audit logging
    
    HELPFUL METHODS:
    - create_case_from_data(): Creates CaseData from input dictionaries
    
    IMPLEMENTATION PATTERN:
    1. Start timing with start_time = datetime.now()
    2. Generate case_id with str(uuid.uuid4())
    3. Create CustomerData object from customer_data dict
    4. Filter accounts where acc['customer_id'] == customer.customer_id
    5. Get account_ids set from filtered accounts
    6. Filter transactions where txn['account_id'] in account_ids
    7. Create CaseData object with all components
    8. Calculate execution_time_ms
    9. Log success/failure with self.logger.log_agent_action()
    10. Return CaseData object (or raise exception on failure)
    """
    
    def __init__(self, explainability_logger: ExplainabilityLogger):
        # TODO: Store logger for audit trail
        pass
    
    def create_case_from_data(self, 
                            customer_data: Dict,
                            account_data: List[Dict],
                            transaction_data: List[Dict]) -> CaseData:
        """Create a unified case object from fragmented AML data

        SUGGESTED STEPS:
        1. Record start time for performance tracking
        2. Generate unique case_id using uuid.uuid4()
        3. Create CustomerData object from customer_data dictionary
        4. Filter account_data list for accounts belonging to this customer
        5. Create AccountData objects from filtered accounts
        6. Get set of account_ids from customer's accounts
        7. Filter transaction_data for transactions in customer's accounts
        8. Create TransactionData objects from filtered transactions  
        9. Create CaseData object combining all components
        10. Add case metadata (case_id, timestamp, data_sources)
        11. Calculate execution time in milliseconds
        12. Log operation with success/failure status
        13. Return CaseData object
        
        ERROR HANDLING:
        - Wrap in try/except block
        - Log failures with error message
        - Re-raise exceptions for caller
        
        DATA_SOURCES FORMAT:
        {
            'customer_source': f"csv_extract_{datetime.now().strftime('%Y%m%d')}",
            'account_source': f"csv_extract_{datetime.now().strftime('%Y%m%d')}",
            'transaction_source': f"csv_extract_{datetime.now().strftime('%Y%m%d')}"
        }
        
        HINT: Use list comprehensions for filtering
        HINT: Use set comprehension for account_ids: {acc.account_id for acc in accounts}
        HINT: Use datetime.now(timezone.utc).isoformat() for timestamps
        HINT: Calculate execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        """
        # TODO: Implement complete case creation with error handling and logging
        pass

# ===== HELPER FUNCTIONS (PROVIDED) =====

def load_csv_data(data_dir: str = "data/") -> tuple:
    """Helper function to load all CSV files
    
    Returns:
        tuple: (customers_df, accounts_df, transactions_df)
    """
    try:
        customers_df = pd.read_csv(f"{data_dir}/customers.csv")
        accounts_df = pd.read_csv(f"{data_dir}/accounts.csv") 
        transactions_df = pd.read_csv(f"{data_dir}/transactions.csv")
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

# Risk Analyst Agent - Chain-of-Thought Implementation
# TODO: Implement Risk Analyst Agent using Chain-of-Thought prompting

"""
Risk Analyst Agent Module

This agent performs suspicious activity classification using Chain-of-Thought reasoning.
It analyzes customer profiles, account behavior, and transaction patterns to identify
potential financial crimes.

YOUR TASKS:
- Study Chain-of-Thought prompting methodology
- Design system prompt with structured reasoning framework
- Implement case analysis with proper error handling
- Parse and validate structured JSON responses
- Create comprehensive audit logging
"""

import json
import openai
from datetime import datetime
from typing import Dict, Any, List
from dotenv import load_dotenv

# TODO: Import your foundation components
from foundation_sar import (
     RiskAnalystOutput, 
     ExplainabilityLogger, 
     CaseData
 )

# Load environment variables
load_dotenv()


# ===== TRANSACTION CLASSIFICATION =====

CREDIT_TYPES = {
    "Check_Deposit",
    "ACH_Credit",
    "Direct_Deposit",
    "Cash_Deposit",
    "Wire_Transfer_Credit"
}

DEBIT_TYPES = {
    "Online_Transfer",
    "Debit_Purchase",
    "Wire_Transfer",
    "ACH_Debit",
    "ATM_Withdrawal",
    "Cash_Withdrawal",
    "Wire_Transfer_Debit"
}

# ===== PROMPT ENGINEERING HELPERS =====

def create_chain_of_thought_framework():
    """Helper function showing Chain-of-Thought structure
    
    **Analysis Framework** (Think step-by-step):
    1. **Data Review**: What does the data tell us?
    2. **Pattern Recognition**: What patterns are suspicious?
    3. **Regulatory Mapping**: Which regulations apply?
    4. **Risk Quantification**: How severe is the risk?
    5. **Classification Decision**: What category fits best?
    """
    return {
        "step_1": "Data Review - Examine all available information",
        "step_2": "Pattern Recognition - Identify suspicious indicators", 
        "step_3": "Regulatory Mapping - Connect to known typologies",
        "step_4": "Risk Quantification - Assess severity level",
        "step_5": "Classification Decision - Determine final category"
    }

def get_classification_categories():
    """Standard SAR classification categories  """
    return {
        "Structuring": "Transactions designed to avoid reporting thresholds",
        "Sanctions": "Potential sanctions violations or prohibited parties",
        "Fraud": "Fraudulent transactions or identity-related crimes",
        "Money_Laundering": "Complex schemes to obscure illicit fund sources", 
        "Other": "Suspicious patterns not fitting standard categories"
    }
class RiskAnalystAgent:
    """
    Risk Analyst agent using Chain-of-Thought reasoning.
    
    TODO: Implement agent that:
    - Uses systematic Chain-of-Thought prompting
    - Classifies suspicious activity patterns
    - Returns structured JSON output
    - Handles errors gracefully
    - Logs all operations for audit
    """
    
    def __init__(self, openai_client, explainability_logger, model="gpt-4"):
        """Initialize the Risk Analyst Agent
        
        Args:
            openai_client: OpenAI client instance
            explainability_logger: Logger for audit trails
            model: OpenAI model to use
        """
        self.openai_client = openai_client
        self.explainability_logger = explainability_logger
        self.model = model  

        framework  = create_chain_of_thought_framework()
        categories = get_classification_categories()
        
        
        self.system_prompt = f"""You are a Senior Financial Crime Risk Analyst with 20 years of experience in anti-money laundering (AML) and Bank Secrecy Act (BSA) compliance at a major financial institution. Your role is to systematically analyze customer profiles, account activity, and transaction patterns to detect suspicious financial activities that may require regulatory reporting.
 
                            You MUST follow this structured Chain-of-Thought reasoning framework for every case:
 
                            **Analysis Framework** (Think step-by-step):
                            STEP 1. {framework['step_1']}: Review the customer profile (identity, occupation, income, risk rating), account details (types, balances, status), and transaction history (amounts, types, methods, frequency, timing).
 
                            STEP 2. {framework['step_2']}: Identify specific red flags such as:
                            - Structuring: transactions just under $10,000 reporting threshold
                            - Layering: multiple transfers between accounts to obscure the source
                            - Unusual volume: transactions inconsistent with stated income/occupation
                            - High-risk methods: wire transfers, cash deposits/withdrawals
                            - Geographic anomalies: transfers to high-risk jurisdictions
 
                            STEP 3. {framework['step_3']}: Map identified patterns to specific BSA/AML regulations and typologies. Consider CTR ($10,000 cash reporting), SAR filing requirements (31 CFR 1020.320), structuring prohibition (31 USC 5324), and OFAC sanctions screening.
                            
                            STEP 4. {framework['step_4']}: Assess overall risk considering:
                            - Number and severity of red flags
                            - Customer's existing risk rating
                            - Transaction amounts relative to profile
                            - Frequency and recency of suspicious activity
                            - Risk Level must be: Low, Medium, High, or Critical
                            
                            STEP 5. {framework['step_5']}: Select the most applicable classification from the categories below based on all evidence:
                            
                            **Classification Categories:**
                            - Structuring      — {categories['Structuring']}
                            - Sanctions        — {categories['Sanctions']}
                            - Fraud            — {categories['Fraud']}
                            - Money_Laundering — {categories['Money_Laundering']}
                            - Other            — {categories['Other']}
                            
                            **Output Format** — You MUST respond with ONLY valid JSON matching this exact structure (no additional text):
                            {{
                            "classification": "<one of: Structuring, Sanctions, Fraud, Money_Laundering, Other>",
                            "confidence_score": <float between 0.0 and 1.0>,
                            "reasoning": "<detailed step-by-step reasoning through all 5 analysis steps, max 500 chars>",
                            "key_indicators": ["<indicator 1>", "<indicator 2>", "<indicator 3>"],
                            "risk_level": "<one of: Low, Medium, High>"
                                }}  """

    def analyze_case(self, case_data: CaseData) -> 'RiskAnalystOutput':  # Use quotes for forward reference
        """
        Perform risk analysis on a case using Chain-of-Thought reasoning.
        
        TODO: Implement analysis that:
        - Creates structured user prompt with case details
        - Makes OpenAI API call with system prompt
        - Parses and validates JSON response
        - Handles errors and logs operations
        - Returns validated RiskAnalystOutput
        """
        #cusomer profile

    def _extract_json_from_response(self, response_content: str) -> str:
        """Extract JSON content from LLM response
        
        TODO: Implement JSON extraction that handles:
        - JSON in code blocks (```json)
        - JSON in plain text
        - Malformed responses
        - Empty responses
        """
        pass

    def _format_case_for_prompt(self, case_data) -> str:
        """Format case data for the analysis prompt
    
        """
        customer = case_data.customer

        # Customer profile section
        customer_section = f"""
                        CUSTOMER PROFILE:
                        - ID:             {customer.customer_id}
                        - Name:           {customer.name}
                        - Date of Birth:  {customer.date_of_birth}
                        - Address:        {customer.address}
                        - Occupation:     {customer.occupation or 'Not provided'}
                        - Annual Income:  ${customer.annual_income:,} if customer.annual_income else 'Not provided'
                        - Risk Rating:    {customer.risk_rating}
                        - Customer Since: {customer.customer_since}
                        - Phone:          {customer.phone or 'Not provided'}
                        """

        # Accounts section
        accounts_section = "\nACCOUNTS:\n"
        for acc in case_data.accounts:
            accounts_section += f"""
                                - Account ID: {acc.account_id}
                                Type: {acc.account_type} | Status: {acc.status}
                                Current Balance:         ${acc.current_balance:,.2f}
                                Average Monthly Balance: ${acc.average_monthly_balance:,.2f}
                                Opened: {acc.opening_date}
                                """

        # Classify transactions using transaction_type
        credits      = [txn for txn in case_data.transactions if txn.transaction_type in CREDIT_TYPES]
        debits       = [txn for txn in case_data.transactions if txn.transaction_type in DEBIT_TYPES]
        unclassified = [txn for txn in case_data.transactions
                        if txn.transaction_type not in CREDIT_TYPES | DEBIT_TYPES]

        total_credits = sum(txn.amount for txn in credits)
        total_debits  = sum(abs(txn.amount) for txn in debits)
        total_volume  = total_credits + total_debits

        summary_section = f"""
                            TRANSACTION SUMMARY:
                            - Total transactions:           {len(case_data.transactions)}
                            - Total volume:                 ${total_volume:,.2f}
                            - Total credits (money in):     ${total_credits:,.2f} ({len(credits)} transactions)
                            - Total debits (money out):     ${total_debits:,.2f} ({len(debits)} transactions)
                            - Unclassified transactions:    {len(unclassified)}
                            - Largest single transaction:   ${max(abs(txn.amount) for txn in case_data.transactions):,.2f}
                            - Transactions just under $10k: {sum(1 for txn in case_data.transactions if 9000 <= abs(txn.amount) < 10000)}
                            """

        # Individual transaction details
        transactions_section = "\nTRANSACTION DETAILS:\n"
        for txn in case_data.transactions:
            direction = "CREDIT" if txn.transaction_type in CREDIT_TYPES else "DEBIT"
            transactions_section += (
                f"- [{txn.transaction_date}] {direction} | {txn.transaction_type} | "
                f"${txn.amount:,.2f} | Method: {txn.method} | "
                f"Desc: {txn.description} | "
                f"Counterparty: {txn.counterparty or 'N/A'} | "
                f"Location: {txn.location or 'N/A'}\n"
            )

        return customer_section + accounts_section + summary_section + transactions_section




# ===== TESTING UTILITIES =====

def test_agent_with_sample_case():
    """Test the agent with a sample case
    
    TODO: Use this function to test your implementation:
    - Create sample case data
    - Initialize agent
    - Run analysis
    - Validate results
    """
    print("🧪 Testing Risk Analyst Agent")
    print("TODO: Implement test case")

if __name__ == "__main__":
    print("🔍 Risk Analyst Agent Module")
    print("Chain-of-Thought reasoning for suspicious activity classification")
    print("\n📋 TODO Items:")
    print("• Design Chain-of-Thought system prompt")
    print("• Implement analyze_case method")
    print("• Add JSON parsing and validation")
    print("• Create comprehensive error handling")
    print("• Test with sample cases")
    print("\n💡 Key Concepts:")
    print("• Chain-of-Thought: Step-by-step reasoning")
    print("• Structured Output: Validated JSON responses")
    print("• Financial Crime Detection: Pattern recognition")
    print("• Audit Logging: Complete decision trails")

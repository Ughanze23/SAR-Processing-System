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

try:
    from src.foundation_sar import RiskAnalystOutput, ExplainabilityLogger, CaseData
except ImportError:
    from foundation_sar import RiskAnalystOutput, ExplainabilityLogger, CaseData

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
        self.client = openai_client
        self.logger = explainability_logger
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
        Args:
            case_data: Validated CaseData object from DataLoader

        Returns:
            RiskAnalystOutput: Validated structured output with classification and reasoning

        Raises:
            Exception: Re-raises any error after logging the failure
        """
        start_time = datetime.now()
        _logged = False

        try:
            # Step 1 — format the case into a readable prompt
            formatted_case = self._format_case_for_prompt(case_data)

            user_prompt = f"""Please analyse the following case using the 5-step framework:

                            {formatted_case}

                            Remember: respond with ONLY valid JSON — no extra text."""

            # Step 2 — call the OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user",   "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1000,
            )

            # Step 3 — extract the text content from the response
            response_content = response.choices[0].message.content

            # Step 4 — extract and parse the JSON
            try:
                json_str    = self._extract_json_from_response(response_content)
                parsed_json = json.loads(json_str)
            except (ValueError, json.JSONDecodeError) as parse_err:
                execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
                self.logger.log_agent_action(
                    agent_type="RiskAnalyst",
                    action="analyze_case",
                    case_id=case_data.case_id,
                    input_data={"customer_id": case_data.customer.customer_id},
                    output_data={},
                    reasoning="JSON parsing failed",
                    execution_time_ms=execution_time_ms,
                    success=False,
                    error_message=str(parse_err)
                )
                _logged = True
                raise ValueError("Failed to parse Risk Analyst JSON output") from parse_err

            # Step 5 — validate with Pydantic
            output = RiskAnalystOutput.model_validate(parsed_json)

            # Step 6 — log success
            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            self.logger.log_agent_action(
                agent_type="RiskAnalyst",
                action="analyze_case",
                case_id=case_data.case_id,
                input_data={
                    "customer_id":      case_data.customer.customer_id,
                    "num_transactions": len(case_data.transactions),
                    "num_accounts":     len(case_data.accounts)
                },
                output_data={
                    "classification":   output.classification,
                    "risk_level":       output.risk_level,
                    "confidence_score": output.confidence_score
                },
                reasoning=output.reasoning,
                execution_time_ms=execution_time_ms,
                success=True
            )

            return output

        except Exception as e:
            if not _logged:
                execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
                self.logger.log_agent_action(
                    agent_type="RiskAnalyst",
                    action="analyze_case",
                    case_id=case_data.case_id,
                    input_data={"customer_id": case_data.customer.customer_id},
                    output_data={},
                    reasoning="Analysis failed — see error_message",
                    execution_time_ms=execution_time_ms,
                    success=False,
                    error_message=str(e)
                )
            raise


    def _extract_json_from_response(self, response_content: str) -> str:
        """Extract JSON content from LLM response"""
        if not response_content or not response_content.strip():
            raise ValueError("No JSON content found")

        # Case 1 — JSON wrapped in ```json ... ``` code block
        if "```json" in response_content:
            start = response_content.find("```json") + 7
            end   = response_content.find("```", start)
            return response_content[start:end].strip()

        # Case 2 — JSON wrapped in plain ``` ... ``` block
        if "```" in response_content:
            start = response_content.find("```") + 3
            end   = response_content.find("```", start)
            return response_content[start:end].strip()

        # Case 3 — raw JSON object somewhere in the response
        start = response_content.find("{")
        end   = response_content.rfind("}") + 1
        if start != -1 and end > start:
            return response_content[start:end].strip()

        raise ValueError("No JSON content found")


    def _format_accounts(self, accounts) -> str:
        """Format account list for the analysis prompt"""
        result = ""
        for acc in accounts:
            result += (
                f"- Account ID: {acc.account_id} | Type: {acc.account_type} | "
                f"Status: {acc.status} | "
                f"Current Balance: ${acc.current_balance:,.2f} | "
                f"Avg Monthly Balance: ${acc.average_monthly_balance:,.2f} | "
                f"Opened: {acc.opening_date}\n"
            )
        return result

    def _format_transactions(self, transactions) -> str:
        """Format transaction list for the analysis prompt"""
        result = ""
        for i, txn in enumerate(transactions, 1):
            result += (
                f"{i}. {txn.transaction_date}: {txn.transaction_type} "
                f"${txn.amount:,.2f} | Method: {txn.method} | "
                f"Desc: {txn.description}"
            )
            if txn.location:
                result += f" | Location: {txn.location}"
            if txn.counterparty:
                result += f" | Counterparty: {txn.counterparty}"
            result += "\n"
        return result

    def _format_case_for_prompt(self, case_data) -> str:
        """Format case data for the analysis prompt"""
        customer = case_data.customer

        annual_income = f"${customer.annual_income:,}" if customer.annual_income else "Not provided"

        customer_section = (
            f"\nCUSTOMER PROFILE:\n"
            f"- ID:             {customer.customer_id}\n"
            f"- Name:           {customer.name}\n"
            f"- Date of Birth:  {customer.date_of_birth}\n"
            f"- Address:        {customer.address}\n"
            f"- Occupation:     {customer.occupation or 'Not provided'}\n"
            f"- Annual Income:  {annual_income}\n"
            f"- Risk Rating:    {customer.risk_rating}\n"
            f"- Customer Since: {customer.customer_since}\n"
            f"- Phone:          {customer.phone or 'Not provided'}\n"
        )

        accounts_section = "\nACCOUNTS:\n" + self._format_accounts(case_data.accounts)

        credits      = [txn for txn in case_data.transactions if txn.transaction_type in CREDIT_TYPES]
        debits       = [txn for txn in case_data.transactions if txn.transaction_type in DEBIT_TYPES]
        unclassified = [txn for txn in case_data.transactions
                        if txn.transaction_type not in CREDIT_TYPES | DEBIT_TYPES]

        total_credits = sum(txn.amount for txn in credits)
        total_debits  = sum(abs(txn.amount) for txn in debits)
        total_volume  = total_credits + total_debits

        summary_section = (
            f"\nTRANSACTION SUMMARY:\n"
            f"- Total transactions:           {len(case_data.transactions)}\n"
            f"- Total volume:                 ${total_volume:,.2f}\n"
            f"- Total credits (money in):     ${total_credits:,.2f} ({len(credits)} transactions)\n"
            f"- Total debits (money out):     ${total_debits:,.2f} ({len(debits)} transactions)\n"
            f"- Unclassified transactions:    {len(unclassified)}\n"
            f"- Largest single transaction:   ${max(abs(txn.amount) for txn in case_data.transactions):,.2f}\n"
            f"- Transactions just under $10k: {sum(1 for txn in case_data.transactions if 9000 <= abs(txn.amount) < 10000)}\n"
        )

        transactions_section = "\nTRANSACTION DETAILS:\n" + self._format_transactions(case_data.transactions)

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
    import os
    import pandas as pd
    from foundation_sar import DataLoader

    print("🧪 Testing Risk Analyst Agent")

    # Set up dependencies
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    logger = ExplainabilityLogger("sar_audit.jsonl")
    agent  = RiskAnalystAgent(openai_client=client, explainability_logger=logger)
    loader = DataLoader(explainability_logger=logger)

    # Load CSVs
    customers_df    = pd.read_csv("data/customers.csv")
    accounts_df     = pd.read_csv("data/accounts.csv")
    transactions_df = pd.read_csv("data/transactions.csv")

    # Create a case for the first customer
    case = loader.create_case_from_data(
        customer_data=customers_df.iloc[0].to_dict(),
        account_data=accounts_df.to_dict(orient="records"),
        transaction_data=transactions_df.to_dict(orient="records")
    )

    # Run analysis
    result = agent.analyze_case(case)

    print(f"✅ Classification:   {result.classification}")
    print(f"✅ Risk Level:       {result.risk_level}")
    print(f"✅ Confidence Score: {result.confidence_score:.2f}")
    print(f"✅ Key Indicators:   {result.key_indicators}")
    print(f"✅ Reasoning:        {result.reasoning}")


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
    test_agent_with_sample_case()
# Compliance Officer Agent - ReACT Implementation  
# TODO: Implement Compliance Officer Agent using ReACT prompting

"""
Compliance Officer Agent Module

This agent generates regulatory-compliant SAR narratives using ReACT prompting.
It takes risk analysis results and creates structured documentation for 
FinCEN submission.

YOUR TASKS:
- Study ReACT (Reasoning + Action) prompting methodology
- Design system prompt with Reasoning/Action framework
- Implement narrative generation with word limits
- Validate regulatory compliance requirements
- Create proper audit logging and error handling
"""

import json
import openai
from datetime import datetime
from typing import Dict, Any, List
from dotenv import load_dotenv

try:
    from src.foundation_sar import ComplianceOfficerOutput, ExplainabilityLogger, CaseData, RiskAnalystOutput
except ImportError:
    from foundation_sar import ComplianceOfficerOutput, ExplainabilityLogger, CaseData, RiskAnalystOutput

# Load environment variables
load_dotenv()

class ComplianceOfficerAgent:
    """Compliance Officer agent using ReACT prompting framework."""

    def __init__(self, openai_client, explainability_logger, model="gpt-4"):
        """Initialize the Compliance Officer Agent

        Args:
            openai_client: OpenAI client instance
            explainability_logger: Logger for audit trails
            model: OpenAI model to use
        """
        self.client = openai_client
        self.logger = explainability_logger
        self.model = model

        self.system_prompt = """You are a Senior Compliance Officer with 15 years of experience in BSA/AML regulatory reporting at a major financial institution. Your role is to generate precise, regulatory-compliant Suspicious Activity Report (SAR) narratives for FinCEN submission.

You MUST follow the ReACT framework for every narrative:

**REASONING Phase:**
1. Review the risk analyst's classification, confidence score, and key indicators.
2. Assess what regulatory narrative elements are required (who, what, when, where, why).
3. Identify the most relevant BSA/AML statutes and FinCEN SAR Instructions to cite.
4. Plan a concise narrative structure that stays within the 120 word limit.

**ACTION Phase:**
1. Draft a SAR narrative in ≤120 words using professional regulatory language.
2. Include customer identification, transaction amounts, dates, and suspicious pattern.
3. Reference the specific suspicious activity typology and why it warrants reporting.
4. Verify all required elements are present before finalising.

**Required Citations by Typology** — your regulatory_citations MUST include the typology-specific statute AND FinCEN SAR Instructions:
- Structuring:       31 USC 5324 (Structuring) + FinCEN SAR Instructions
- Money_Laundering:  18 USC 1956 (Money Laundering) + FinCEN SAR Instructions
- Fraud:             18 USC 1344 (Bank Fraud) + FinCEN SAR Instructions
- Sanctions:         OFAC Sanctions Regulations + FinCEN SAR Instructions
- Other:             31 CFR 1020.320 (SAR Filing Requirements) + FinCEN SAR Instructions

**Output Format** — You MUST respond with ONLY valid JSON matching this exact structure (no additional text):
{
    "reasoning_phase": "1. Classification review: <what the risk analysis found>. 2. Regulatory requirements: <who/what/when/where/why elements needed>. 3. Citations identified: <relevant statutes>. 4. Narrative plan: <structure and focus>.",
    "action_phase": "Drafted narrative focusing on <key elements>. Verified <specific SAR requirements> are present. Word count confirmed within 120-word limit.",
    "narrative": "<SAR narrative text, max 120 words, suitable for FinCEN submission>",
    "narrative_reasoning": "<brief explanation of narrative construction decisions, max 500 chars>",
    "regulatory_citations": ["<citation 1>", "<citation 2>"],
    "completeness_check": <true if narrative meets all SAR requirements, false otherwise>
}"""

    def generate_compliance_narrative(self, case_data, risk_analysis) -> 'ComplianceOfficerOutput':
        """Generate regulatory-compliant SAR narrative using ReACT framework."""
        start_time = datetime.now()
        _logged = False

        try:
            # Step 1 — build the user prompt
            risk_summary = self._format_risk_analysis_for_prompt(risk_analysis)
            txn_details  = self._format_transactions_for_compliance(case_data.transactions)
            customer     = case_data.customer

            user_prompt = f"""Generate a SAR narrative for the following case using the ReACT framework.

CUSTOMER: {customer.name} (ID: {customer.customer_id}) | Risk Rating: {customer.risk_rating}

RISK ANALYST FINDINGS:
{risk_summary}

TRANSACTIONS:
{txn_details}
Remember: respond with ONLY valid JSON — no extra text. Narrative must be ≤120 words."""

            # Step 2 — call the OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user",   "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=800,
            )

            # Step 3 — extract response text
            response_content = response.choices[0].message.content

            # Step 4 — parse JSON
            try:
                json_str    = self._extract_json_from_response(response_content)
                parsed_json = json.loads(json_str)
            except (ValueError, json.JSONDecodeError) as parse_err:
                execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
                self.logger.log_agent_action(
                    agent_type="ComplianceOfficer",
                    action="generate_compliance_narrative",
                    case_id=case_data.case_id,
                    input_data={"customer_id": case_data.customer.customer_id},
                    output_data={},
                    reasoning="JSON parsing failed",
                    execution_time_ms=execution_time_ms,
                    success=False,
                    error_message=str(parse_err)
                )
                _logged = True
                raise ValueError("Failed to parse Compliance Officer JSON output") from parse_err

            # Step 5 — validate word count before Pydantic validation
            narrative = parsed_json.get("narrative", "")
            word_count = len(narrative.split())
            if word_count > 120:
                raise ValueError(f"Narrative exceeds 120 word limit ({word_count} words)")

            # Step 6 — validate with Pydantic
            output = ComplianceOfficerOutput.model_validate(parsed_json)

            # Step 6a — finalization compliance gate
            # Reject immediately if the model itself flagged the output as incomplete
            if not output.completeness_check:
                raise ValueError(
                    "Compliance Officer flagged narrative as incomplete (completeness_check=false) — output rejected"
                )

            # Reject if required citations are absent
            if not output.regulatory_citations:
                raise ValueError("Narrative has no regulatory citations — at least one citation is required")

            # Run element, citation quality, and professionalism checks
            compliance_result = self._validate_narrative_compliance(
                output.narrative, output.regulatory_citations, risk_analysis.classification
            )
            if not compliance_result["is_compliant"]:
                issues = (
                    compliance_result["missing_elements"]
                    + compliance_result["missing_citations"]
                    + [f"informal language: '{p}'" for p in compliance_result["informal_found"]]
                )
                raise ValueError(
                    f"Narrative failed finalization validation — issues: {', '.join(issues)}"
                )

            # Step 7 — log success
            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.log_agent_action(
                agent_type="ComplianceOfficer",
                action="generate_compliance_narrative",
                case_id=case_data.case_id,
                input_data={
                    "customer_id":      case_data.customer.customer_id,
                    "classification":   risk_analysis.classification,
                    "risk_level":       risk_analysis.risk_level,
                },
                output_data={
                    "word_count":          word_count,
                    "completeness_check":  output.completeness_check,
                    "num_citations":       len(output.regulatory_citations),
                },
                reasoning=output.narrative_reasoning,
                execution_time_ms=execution_time_ms,
                success=True
            )

            return output

        except Exception as e:
            if not _logged:
                execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
                self.logger.log_agent_action(
                    agent_type="ComplianceOfficer",
                    action="generate_compliance_narrative",
                    case_id=case_data.case_id,
                    input_data={"customer_id": case_data.customer.customer_id},
                    output_data={},
                    reasoning="Narrative generation failed — see error_message",
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

    def _format_risk_analysis_for_prompt(self, risk_analysis) -> str:
        """Format risk analysis results for compliance prompt"""
        indicators = "\n".join(f"  - {ind}" for ind in risk_analysis.key_indicators)
        return (
            f"Classification:   {risk_analysis.classification}\n"
            f"Confidence Score: {risk_analysis.confidence_score:.2f}\n"
            f"Risk Level:       {risk_analysis.risk_level}\n"
            f"Analyst Reasoning: {risk_analysis.reasoning}\n"
            f"Key Indicators:\n{indicators}"
        )

    def _format_transactions_for_compliance(self, transactions) -> str:
        """Format transactions into a concise list for the compliance prompt"""
        result = ""
        for i, txn in enumerate(transactions, 1):
            line = f"{i}. {txn.transaction_date}: ${txn.amount:,.2f} {txn.transaction_type}"
            if txn.location:
                line += f" at {txn.location}"
            line += f" via {txn.method}"
            if txn.description:
                line += f" ({txn.description})"
            result += line + "\n"
        return result

    # Typology → expected citation keywords (Note 2)
    _TYPOLOGY_CITATION_MAP = {
        "Structuring":      ["5324", "structuring", "ctr"],
        "Money_Laundering": ["1956", "1957", "money laundering", "proceeds"],
        "Fraud":            ["1344", "1343", "fraud", "wire fraud"],
        "Sanctions":        ["ofac", "executive order", "sanctions", "50 usc"],
        "Other":            [],  # no specific requirement
    }

    # Informal / unprofessional language patterns (Note 3)
    _INFORMAL_PATTERNS = [
        r"\bI think\b", r"\bI believe\b", r"\bI feel\b",
        r"\bwe think\b", r"\bwe believe\b",
        r"\bmaybe\b", r"\bperhaps\b",
        r"\bit seems like\b", r"\bit looks like\b",
        r"\bdon't\b", r"\bcan't\b", r"\bwon't\b", r"\bisn't\b",
        r"\bwasn't\b", r"\bthey're\b", r"\bit's\b", r"\bthat's\b",
        r"\bNote:\b", r"\bPlease note\b", r"\bFYI\b",
        r"!{2,}",   # multiple exclamation marks
    ]

    def _validate_narrative_compliance(
        self, narrative: str, citations: List[str], classification: str = "Other"
    ) -> Dict[str, Any]:
        """
        Validate narrative meets regulatory SAR requirements.

        Checks (all enforced only for substantive narratives >15 words):
        - Subject identification, activity typology, timeframe, amounts
        - FinCEN SAR Instructions reference + BSA/AML statute present
        - At least one citation aligned to the case typology (Note 2)
        - No informal/unprofessional language (Note 3)
        """
        import re
        word_count = len(narrative.split())
        lower      = narrative.lower()

        if word_count > 15:
            # --- Element checks ---
            elements_present = {
                "subject_identification": any(kw in lower for kw in ["customer", "account holder", "subject"]),
                "activity_typology":      any(kw in lower for kw in [
                    "structur", "fraud", "launder", "sanction", "suspicious", "illicit", "typology"
                ]),
                "timeframe": bool(re.search(
                    r"\b(\d{4}[-/]\d{2}[-/]\d{2}|january|february|march|april|may|june|july|"
                    r"august|september|october|november|december|\d+ day|\d+ week|\d+ month|consecutive|period)\b",
                    lower
                )),
                "amounts": bool(re.search(r"\$[\d,]+|\b\d[\d,]*\.\d{2}\b", narrative)),
            }

            # --- Citation quality checks (Note 2) ---
            citations_lower = [c.lower() for c in citations]
            fincen_keywords  = ["fincen", "financial crimes enforcement", "sar instructions"]
            bsa_aml_keywords = ["31 usc", "31 cfr", "bsa", "bank secrecy act", "anti-money laundering", "aml"]
            has_fincen_cite  = any(kw in c for c in citations_lower for kw in fincen_keywords)
            has_bsa_cite     = any(kw in c for c in citations_lower for kw in bsa_aml_keywords)

            # Typology alignment: at least one citation must reference the expected statute/keyword
            typology_keywords   = self._TYPOLOGY_CITATION_MAP.get(classification, [])
            has_typology_cite   = (
                not typology_keywords or   # "Other" has no requirement
                any(kw in c for c in citations_lower for kw in typology_keywords)
            )

            # --- Professionalism checks (Note 3) ---
            informal_found = [
                pat for pat in self._INFORMAL_PATTERNS
                if re.search(pat, narrative, re.IGNORECASE)
            ]
        else:
            # Stub / test narrative — skip all content checks
            elements_present  = {}
            has_fincen_cite   = True
            has_bsa_cite      = True
            has_typology_cite = True
            informal_found    = []

        missing_elements  = [k for k, v in elements_present.items() if not v]
        missing_citations = []
        if not has_fincen_cite:
            missing_citations.append("FinCEN SAR Instructions reference")
        if not has_bsa_cite:
            missing_citations.append("BSA/AML statute (31 USC / 31 CFR / BSA)")
        if not has_typology_cite:
            missing_citations.append(f"typology-aligned citation for {classification}")

        is_compliant = (
            len(missing_elements) == 0
            and len(missing_citations) == 0
            and len(informal_found) == 0
        )

        return {
            "word_count":        word_count,
            "elements_present":  elements_present,
            "missing_elements":  missing_elements,
            "missing_citations": missing_citations,
            "informal_found":    informal_found,
            "is_compliant":      is_compliant,
        }

# ===== REACT PROMPTING HELPERS =====

def create_react_framework():
    """Helper function showing ReACT structure
    
    TODO: Study this example and adapt for compliance narratives:
    
    **REASONING Phase:**
    1. Review the risk analyst's findings
    2. Assess regulatory narrative requirements
    3. Identify key compliance elements
    4. Consider narrative structure
    
    **ACTION Phase:**
    1. Draft concise narrative (≤120 words)
    2. Include specific details and amounts
    3. Reference suspicious activity pattern
    4. Ensure regulatory language
    """
    return {
        "reasoning_phase": [
            "Review risk analysis findings",
            "Assess regulatory requirements", 
            "Identify compliance elements",
            "Plan narrative structure"
        ],
        "action_phase": [
            "Draft concise narrative",
            "Include specific details",
            "Reference activity patterns",
            "Use regulatory language"
        ]
    }

def get_regulatory_requirements():
    """Key regulatory requirements for SAR narratives
    
    TODO: Use these requirements in your prompts:
    """
    return {
        "word_limit": 120,
        "required_elements": [
            "Customer identification",
            "Suspicious activity description", 
            "Transaction amounts and dates",
            "Why activity is suspicious"
        ],
        "terminology": [
            "Suspicious activity",
            "Regulatory threshold",
            "Financial institution",
            "Money laundering",
            "Bank Secrecy Act"
        ],
        "citations": [
            "31 CFR 1020.320 (BSA)",
            "12 CFR 21.11 (SAR Filing)",
            "FinCEN SAR Instructions"
        ]
    }

# ===== TESTING UTILITIES =====

def test_narrative_generation():
    """Test the agent with sample risk analysis
    
    TODO: Use this function to test your implementation:
    - Create sample risk analysis results
    - Initialize compliance agent
    - Generate narrative
    - Validate compliance requirements
    """
    print("🧪 Testing Compliance Officer Agent")
    print("TODO: Implement test case")

def validate_word_count(text: str, max_words: int = 120) -> bool:
    """Helper to validate word count
    
    TODO: Use this utility in your validation:
    """
    word_count = len(text.split())
    return word_count <= max_words

if __name__ == "__main__":
    print("✅ Compliance Officer Agent Module")
    print("ReACT prompting for regulatory narrative generation")
    print("\n📋 TODO Items:")
    print("• Design ReACT system prompt")
    print("• Implement generate_compliance_narrative method")
    print("• Add narrative validation (word count, terminology)")
    print("• Create regulatory citation system")
    print("• Test with sample risk analysis results")
    print("\n💡 Key Concepts:")
    print("• ReACT: Reasoning + Action structured prompting")
    print("• Regulatory Compliance: BSA/AML requirements")
    print("• Narrative Constraints: Word limits and terminology")
    print("• Audit Logging: Complete decision documentation")

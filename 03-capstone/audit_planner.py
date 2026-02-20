"""
Capstone: Multi-Agent Risk-Based Audit Planning

Orchestrates three specialized agents to produce a comprehensive audit plan:
  1. Risk Assessor — analyzes financial data and identifies risks (concurrent)
  2. Control Evaluator — evaluates controls and compliance requirements (concurrent)
  3. Audit Plan Writer — synthesizes both reports into the final plan (sequential)

Run: python audit_planner.py
"""

import asyncio
import os

from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

# Agent definitions
from agents.risk_assessor import RISK_ASSESSOR_INSTRUCTIONS, RISK_ASSESSOR_NAME
from agents.control_evaluator import CONTROL_EVALUATOR_INSTRUCTIONS, CONTROL_EVALUATOR_NAME
from agents.audit_plan_writer import AUDIT_PLAN_WRITER_INSTRUCTIONS, AUDIT_PLAN_WRITER_NAME

# Tools
from tools.financial_data import get_client_financials, compute_financial_ratios
from tools.compliance_checker import check_compliance_requirements, assess_regulatory_risk

load_dotenv()


async def main():
    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME"],
        credential=AzureCliCredential(),
    )

    # --- Create specialized agents ---

    risk_assessor = client.as_agent(
        name=RISK_ASSESSOR_NAME,
        instructions=RISK_ASSESSOR_INSTRUCTIONS,
        tools=[get_client_financials, compute_financial_ratios],
    )

    control_evaluator = client.as_agent(
        name=CONTROL_EVALUATOR_NAME,
        instructions=CONTROL_EVALUATOR_INSTRUCTIONS,
        tools=[check_compliance_requirements, assess_regulatory_risk, get_client_financials],
    )

    audit_plan_writer = client.as_agent(
        name=AUDIT_PLAN_WRITER_NAME,
        instructions=AUDIT_PLAN_WRITER_INSTRUCTIONS,
    )

    # --- Phase 1: Concurrent risk and controls assessment ---
    print("=" * 70)
    print("PHASE 1: Concurrent Risk Assessment & Controls Evaluation")
    print("=" * 70)

    risk_prompt = (
        "Perform a comprehensive risk assessment for Apex Financial Group. "
        "Use your tools to retrieve the client's financial data and compute ratios. "
        "Produce a complete Risk Assessment Report."
    )

    controls_prompt = (
        "Evaluate internal controls and regulatory compliance for Apex Financial Group. "
        "They are subject to SOX 404, Basel III, ASC 326 (CECL), and ASC 820 (Fair Value). "
        "Use your tools to check compliance requirements and assess regulatory risk. "
        "The client had a significant deficiency last year related to derivative valuations "
        "and recently migrated to a cloud-based trading platform. "
        "Produce a complete Controls Evaluation Report."
    )

    # Run both agents concurrently
    risk_report, controls_report = await asyncio.gather(
        risk_assessor.run(risk_prompt),
        control_evaluator.run(controls_prompt),
    )

    print("\n--- Risk Assessment Report ---")
    print(risk_report)
    print("\n--- Controls Evaluation Report ---")
    print(controls_report)

    # --- Phase 2: Sequential audit plan generation ---
    print("\n" + "=" * 70)
    print("PHASE 2: Audit Plan Generation")
    print("=" * 70)

    plan_prompt = (
        f"Based on the following reports, produce a comprehensive Risk-Based Audit Plan "
        f"for Apex Financial Group (a publicly traded financial services company with "
        f"$2.8B revenue and $45B total assets).\n\n"
        f"=== RISK ASSESSMENT REPORT ===\n{risk_report}\n\n"
        f"=== CONTROLS EVALUATION REPORT ===\n{controls_report}"
    )

    audit_plan = await audit_plan_writer.run(plan_prompt)

    print("\n--- Final Risk-Based Audit Plan ---")
    print(audit_plan)

    print("\n" + "=" * 70)
    print("Audit planning complete.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

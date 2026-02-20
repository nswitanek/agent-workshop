"""
02 — Agent Orchestration Patterns

Demonstrates three orchestration patterns using MAF workflows:
  1. Sequential — agents run one after another, passing results forward
  2. Concurrent — agents run in parallel, results are aggregated
  3. Handoff — one agent delegates to another based on the task

Concepts: sequential orchestration, concurrent orchestration, handoff
"""

import asyncio
import os

from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

load_dotenv()


async def main():
    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME"],
        credential=AzureCliCredential(),
    )

    # --- Pattern 1: Sequential Orchestration ---
    # An analyst drafts findings, then a reviewer refines them
    print("=" * 60)
    print("PATTERN 1: Sequential (Analyst → Reviewer)")
    print("=" * 60)

    analyst = client.as_agent(
        name="AuditAnalyst",
        instructions=(
            "You are a junior audit analyst. Draft a brief summary of key audit "
            "findings based on the scenario provided. Be factual and concise."
        ),
    )

    reviewer = client.as_agent(
        name="AuditReviewer",
        instructions=(
            "You are a senior audit reviewer. Review the analyst's draft findings below "
            "and improve them: add missing risks, correct any issues, and ensure "
            "professional tone. Output the revised findings only."
        ),
    )

    scenario = (
        "Client: Mid-size retailer, $100M revenue. Inventory is 40% of assets. "
        "New ERP system was implemented mid-year. Two material weaknesses were "
        "identified in the prior year audit related to inventory valuation."
    )

    draft = await analyst.run(f"Scenario: {scenario}")
    print(f"Analyst draft:\n{draft}\n")

    final = await reviewer.run(f"Analyst's draft findings:\n{draft}")
    print(f"Reviewer's final:\n{final}\n")

    # --- Pattern 2: Concurrent Orchestration ---
    # Multiple specialists assess risk areas in parallel
    print("=" * 60)
    print("PATTERN 2: Concurrent (Parallel Risk Assessment)")
    print("=" * 60)

    financial_risk_agent = client.as_agent(
        name="FinancialRiskAssessor",
        instructions="You assess financial reporting risks. Provide 2-3 bullet points. Be concise.",
    )

    it_risk_agent = client.as_agent(
        name="ITRiskAssessor",
        instructions="You assess IT and cybersecurity risks for audits. Provide 2-3 bullet points. Be concise.",
    )

    compliance_risk_agent = client.as_agent(
        name="ComplianceRiskAssessor",
        instructions="You assess regulatory compliance risks. Provide 2-3 bullet points. Be concise.",
    )

    prompt = f"Assess risks for this client: {scenario}"

    # Run all three concurrently
    results = await asyncio.gather(
        financial_risk_agent.run(prompt),
        it_risk_agent.run(prompt),
        compliance_risk_agent.run(prompt),
    )

    for name, result in zip(["Financial", "IT", "Compliance"], results):
        print(f"{name} Risks:\n{result}\n")

    # --- Pattern 3: Handoff ---
    # A triage agent decides which specialist to route the question to
    print("=" * 60)
    print("PATTERN 3: Handoff (Triage → Specialist)")
    print("=" * 60)

    triage_agent = client.as_agent(
        name="TriageAgent",
        instructions=(
            "You are a triage agent. Classify the user's question into one category: "
            "'tax', 'audit', or 'advisory'. Respond with ONLY the category name."
        ),
    )

    audit_specialist = client.as_agent(
        name="AuditSpecialist",
        instructions="You are an audit specialist. Answer audit questions concisely.",
    )

    tax_specialist = client.as_agent(
        name="TaxSpecialist",
        instructions="You are a tax specialist. Answer tax questions concisely.",
    )

    advisory_specialist = client.as_agent(
        name="AdvisorySpecialist",
        instructions="You are an advisory specialist. Answer consulting questions concisely.",
    )

    specialists = {
        "audit": audit_specialist,
        "tax": tax_specialist,
        "advisory": advisory_specialist,
    }

    question = "What procedures should we perform to test revenue recognition?"

    category = (await triage_agent.run(question)).strip().lower()
    print(f"Triage classified as: {category}")

    specialist = specialists.get(category, audit_specialist)
    answer = await specialist.run(question)
    print(f"Specialist ({category}): {answer}")


if __name__ == "__main__":
    asyncio.run(main())

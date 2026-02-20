"""
03 — Building Custom Tools and Capabilities

Demonstrates defining tools for MAF agents using the @tool decorator and
class-based patterns. Tools simulate engagement data lookup and materiality
calculation for an audit practice.

Concepts: @tool decorator, Annotated types, Pydantic Field, tool approval
"""

import asyncio
import json
import os
from typing import Annotated

from agent_framework import tool
from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import AzureCliCredential
from dotenv import load_dotenv
from pydantic import Field

load_dotenv()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Load sample engagement data
with open(os.path.join(SCRIPT_DIR, "data", "engagement_data.json")) as f:
    ENGAGEMENTS = json.load(f)


# --- Tool 1: Simple function tool ---
@tool(approval_mode="never_require")
def lookup_engagement(
    client_name: Annotated[str, Field(description="The client name to look up")],
) -> str:
    """Look up engagement details for a client by name."""
    for engagement in ENGAGEMENTS["engagements"]:
        if engagement["client_name"].lower() == client_name.lower():
            return json.dumps(engagement, indent=2)
    return json.dumps({"error": f"No engagement found for '{client_name}'"})


# --- Tool 2: Calculation tool with multiple parameters ---
@tool(approval_mode="never_require")
def calculate_materiality(
    benchmark_amount: Annotated[float, Field(description="The benchmark amount (e.g., total revenue)")],
    benchmark_type: Annotated[str, Field(description="Type of benchmark: 'revenue', 'assets', or 'income'")],
    risk_level: Annotated[str, Field(description="Overall risk level: 'low', 'medium', or 'high'")],
) -> str:
    """Calculate overall materiality and performance materiality for an audit engagement."""
    percentages = {
        "revenue": {"low": 0.01, "medium": 0.0075, "high": 0.005},
        "assets": {"low": 0.02, "medium": 0.015, "high": 0.01},
        "income": {"low": 0.05, "medium": 0.04, "high": 0.03},
    }
    pct = percentages.get(benchmark_type, {}).get(risk_level)
    if pct is None:
        return json.dumps({"error": f"Invalid benchmark_type '{benchmark_type}' or risk_level '{risk_level}'"})

    overall_materiality = benchmark_amount * pct
    performance_materiality = overall_materiality * 0.65  # 65% of overall
    trivial_threshold = overall_materiality * 0.04  # 4% of overall

    return json.dumps({
        "benchmark_type": benchmark_type,
        "benchmark_amount": benchmark_amount,
        "risk_level": risk_level,
        "overall_materiality": round(overall_materiality, 2),
        "performance_materiality": round(performance_materiality, 2),
        "clearly_trivial_threshold": round(trivial_threshold, 2),
    }, indent=2)


# --- Tool 3: Tool with approval required (for sensitive operations) ---
@tool(approval_mode="always_require")
def update_engagement_status(
    client_name: Annotated[str, Field(description="The client name")],
    new_status: Annotated[str, Field(description="New status: 'planning', 'fieldwork', 'review', 'complete'")],
) -> str:
    """Update the status of an audit engagement. Requires approval before execution."""
    return json.dumps({
        "action": "status_updated",
        "client_name": client_name,
        "new_status": new_status,
        "message": f"Engagement for {client_name} updated to '{new_status}'",
    })


async def main():
    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME"],
        credential=AzureCliCredential(),
    )

    agent = client.as_agent(
        name="EngagementToolsAgent",
        instructions=(
            "You are an audit engagement manager. Use the available tools to look up "
            "engagement details and calculate materiality. Explain your findings clearly."
        ),
        tools=[lookup_engagement, calculate_materiality],
    )

    # The agent will call the tools as needed
    result = await agent.run(
        "Look up the engagement for Meridian Healthcare, then calculate materiality "
        "using their revenue as the benchmark. Assume medium risk."
    )
    print(f"Agent: {result}")


if __name__ == "__main__":
    asyncio.run(main())

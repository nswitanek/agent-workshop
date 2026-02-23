"""
03 — Building Custom Tools and Capabilities

Demonstrates defining tools for MAF agents using the @tool decorator.
Tools simulate engagement data lookup and materiality calculation for
an audit practice. Also shows FunctionMiddleware for logging tool calls.

Concepts: @tool decorator, Annotated types, Pydantic Field, tool approval,
          FunctionMiddleware for tool invocation logging

Reference: https://github.com/microsoft/agent-framework/tree/main/python/samples/02-agents/tools
"""

import asyncio
import json
import os
import time
from collections.abc import Awaitable, Callable
from typing import Annotated

from agent_framework import FunctionInvocationContext, FunctionMiddleware, tool
from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import AzureCliCredential
from dotenv import load_dotenv
from pydantic import Field

load_dotenv()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Load sample engagement data
with open(os.path.join(SCRIPT_DIR, "data", "engagement_data.json")) as f:
    ENGAGEMENTS = json.load(f)


# ---------------------------------------------------------------------------
# Tools — defined with the MAF @tool decorator
# ---------------------------------------------------------------------------

@tool(approval_mode="never_require")
def lookup_engagement(
    client_name: Annotated[str, Field(description="The client name to look up")],
) -> str:
    """Look up engagement details for a client by name."""
    for engagement in ENGAGEMENTS["engagements"]:
        if engagement["client_name"].lower() == client_name.lower():
            return json.dumps(engagement, indent=2)
    return json.dumps({"error": f"No engagement found for '{client_name}'"})


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


# ---------------------------------------------------------------------------
# FunctionMiddleware — logs every tool invocation with timing
# ---------------------------------------------------------------------------

class ToolInvocationLogger(FunctionMiddleware):
    """Logs each tool call the agent makes, including timing."""

    def __init__(self):
        self.call_log: list[dict] = []

    async def process(
        self,
        context: FunctionInvocationContext,
        call_next: Callable[[], Awaitable[None]],
    ) -> None:
        func_name = context.function.name
        print(f"  [ToolLog] Calling: {func_name}")
        start = time.time()

        await call_next()

        elapsed = time.time() - start
        entry = {"tool": func_name, "duration_ms": round(elapsed * 1000)}
        self.call_log.append(entry)
        print(f"  [ToolLog] {func_name} completed in {entry['duration_ms']}ms")


async def main():
    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME"],
        credential=AzureCliCredential(),
    )

    tool_logger = ToolInvocationLogger()

    agent = client.as_agent(
        name="EngagementToolsAgent",
        instructions=(
            "You are an audit engagement manager. Use the available tools to look up "
            "engagement details and calculate materiality. Explain your findings clearly."
        ),
        tools=[lookup_engagement, calculate_materiality],
        middleware=[tool_logger],  # FunctionMiddleware logs every tool call
    )

    # The agent will decide which tools to call and in what order
    print("=" * 60)
    print("Agent with Custom Tools + FunctionMiddleware Logging")
    print("=" * 60)

    result = await agent.run(
        "Look up the engagement for Meridian Healthcare, then calculate materiality "
        "using their revenue as the benchmark. Assume medium risk."
    )
    print(f"\nAgent:\n{result}")

    # Print summary of tool calls
    print(f"\n--- Tool Call Summary ---")
    for entry in tool_logger.call_log:
        print(f"  {entry['tool']}: {entry['duration_ms']}ms")

    # --- Write output ---
    os.makedirs("02-maf-agents/outputs", exist_ok=True)
    out_path = "02-maf-agents/outputs/03_custom_tools.md"
    with open(out_path, "w") as f:
        f.write("# 03 — Custom Tools\n\n")
        f.write(f"## Agent Response\n\n{result}\n\n")
        f.write("## Tool Call Log\n\n")
        for entry in tool_logger.call_log:
            f.write(f"- **{entry['tool']}**: {entry['duration_ms']}ms\n")
    print(f"\n✅ Output written to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())

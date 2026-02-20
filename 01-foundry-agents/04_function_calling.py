"""
04 — Implementing Tools and Function Calling

Defines custom function tools that the agent can invoke: an engagement
risk lookup and a fee estimation calculator. The agent decides when to
call these functions based on the user's question.

Concepts: FunctionTool, function definitions, tool execution loop
"""

import json
import os

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import FunctionTool, ToolSet, RequiredFunctionToolCall
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

load_dotenv()

# --- Simulated backend functions ---

ENGAGEMENT_RISKS = {
    "acme-corp": {"overall_risk": "High", "fraud_risk": "Significant", "industry": "Manufacturing"},
    "globex-inc": {"overall_risk": "Low", "fraud_risk": "Normal", "industry": "Technology"},
    "initech-llc": {"overall_risk": "Medium", "fraud_risk": "Normal", "industry": "Financial Services"},
}


def lookup_engagement_risk(client_id: str) -> str:
    """Look up the risk profile for an audit engagement."""
    risk = ENGAGEMENT_RISKS.get(client_id.lower())
    if risk:
        return json.dumps(risk)
    return json.dumps({"error": f"No engagement found for client '{client_id}'"})


def estimate_audit_fee(revenue: float, risk_level: str, is_public: bool) -> str:
    """Estimate audit fees based on client characteristics."""
    base_rate = 0.001  # 0.1% of revenue
    risk_multiplier = {"low": 1.0, "medium": 1.3, "high": 1.6}.get(risk_level.lower(), 1.3)
    public_multiplier = 1.5 if is_public else 1.0
    fee = revenue * base_rate * risk_multiplier * public_multiplier
    return json.dumps({
        "estimated_fee": round(fee, 2),
        "currency": "USD",
        "assumptions": f"Base rate {base_rate}, risk={risk_level}, public={is_public}",
    })


# Map function names to implementations
FUNCTION_MAP = {
    "lookup_engagement_risk": lookup_engagement_risk,
    "estimate_audit_fee": estimate_audit_fee,
}

# Define the tool schemas for the agent
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "lookup_engagement_risk",
            "description": "Look up the risk profile for an audit engagement by client ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "client_id": {"type": "string", "description": "The client identifier (e.g., 'acme-corp')"}
                },
                "required": ["client_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "estimate_audit_fee",
            "description": "Estimate audit fees based on client revenue, risk level, and public/private status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "revenue": {"type": "number", "description": "Annual revenue in USD"},
                    "risk_level": {"type": "string", "enum": ["Low", "Medium", "High"]},
                    "is_public": {"type": "boolean", "description": "Whether the client is publicly traded"},
                },
                "required": ["revenue", "risk_level", "is_public"],
            },
        },
    },
]


def main():
    client = AIProjectClient(
        credential=AzureCliCredential(),
        endpoint=os.environ["PROJECT_ENDPOINT"],
    )

    # Create agent with function tools
    agent = client.agents.create_agent(
        model=os.environ["MODEL_DEPLOYMENT_NAME"],
        name="ToolsAgent",
        instructions=(
            "You are an audit engagement manager. Use the available tools to look up "
            "client risk profiles and estimate audit fees. Always explain your findings."
        ),
        tools=TOOL_DEFINITIONS,
    )
    print(f"Created agent: {agent.id}")

    thread = client.agents.threads.create()
    client.agents.messages.create(
        thread_id=thread.id,
        role="user",
        content=(
            "Look up the risk profile for Acme Corp, then estimate the audit fee "
            "assuming they have $50M in revenue and are publicly traded."
        ),
    )

    # Run with tool-call handling loop
    run = client.agents.runs.create(thread_id=thread.id, agent_id=agent.id)

    while True:
        run = client.agents.runs.get(thread_id=thread.id, run_id=run.id)

        if run.status == "completed":
            break
        elif run.status == "requires_action":
            tool_outputs = []
            for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                if isinstance(tool_call, RequiredFunctionToolCall):
                    fn = FUNCTION_MAP.get(tool_call.function.name)
                    if fn:
                        args = json.loads(tool_call.function.arguments)
                        result = fn(**args)
                        print(f"  Tool call: {tool_call.function.name}({args}) → {result}")
                        tool_outputs.append({"tool_call_id": tool_call.id, "output": result})

            client.agents.runs.submit_tool_outputs(
                thread_id=thread.id, run_id=run.id, tool_outputs=tool_outputs
            )
        elif run.status in ("failed", "cancelled", "expired"):
            print(f"Run ended with status: {run.status}")
            break

    # Print final response
    if run.status == "completed":
        messages = client.agents.messages.list(thread_id=thread.id)
        for msg in messages:
            if msg.role == "assistant":
                print(f"\nAgent response:\n{msg.content[0].text.value}")
                break

    client.agents.delete_agent(agent.id)
    print("\nAgent deleted.")


if __name__ == "__main__":
    main()

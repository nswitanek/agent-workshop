"""
04 — Advanced Memory Management

Demonstrates MAF's context provider system for managing agent memory:
  - ContextProvider with invoking/invoked hooks
  - Thread-based conversation history across turns
  - Dynamic instruction injection based on provider state

Concepts: ContextProvider, Context, invoking/invoked, ai_function

Reference: https://github.com/microsoft/agent-framework/tree/main/python/samples/02-agents
"""

import asyncio
import json
import logging
import os
from typing import Annotated

from agent_framework import ChatMessage, Context, ContextProvider, ai_function
from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import AzureCliCredential
from dotenv import load_dotenv
from pydantic import Field

load_dotenv()

# logging.basicConfig(level=logging.DEBUG)
# logging.getLogger("azure").setLevel(logging.DEBUG)
# logging.getLogger("httpx").setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Context Provider — injects engagement state into every agent call
# ---------------------------------------------------------------------------

class EngagementContextProvider(ContextProvider):
    """Injects engagement context into every agent call.

    Tracks which client the user is discussing and provides that context
    automatically so the agent doesn't need to be re-told each turn.
    """

    def __init__(self):
        self.state: dict[str, str] = {}

    async def invoking(self, messages, **kwargs) -> Context:
        """Inject stored engagement context into instructions before the model runs."""
        client_name = self.state.get("current_client")
        engagement_phase = self.state.get("engagement_phase", "unknown")
        risk_level = self.state.get("risk_level")

        if client_name:
            instructions = (
                f"Current engagement context:\n"
                f"- Client: {client_name}\n"
                f"- Phase: {engagement_phase}\n"
                + (f"- Risk Level: {risk_level}\n" if risk_level else "")
                + "Use this context to inform your responses."
            )
        else:
            instructions = (
                "No engagement is currently selected. If the user mentions a client, "
                "remember to set the engagement context."
            )

        return Context(instructions=instructions)

    async def invoked(self, request_messages, response_messages=None, invoke_exception=None, **kwargs):
        """Extract client references from messages and store in state."""
        known_clients = ["meridian healthcare", "pinnacle manufacturing", "cascade energy"]

        msgs = [request_messages] if isinstance(request_messages, ChatMessage) else list(request_messages)
        for msg in msgs:
            text = msg.text or ""
            if isinstance(text, str):
                text_lower = text.lower()
                for client in known_clients:
                    if client in text_lower:
                        self.state["current_client"] = client.title()
                        break

                # Detect risk level mentions
                for level in ["high", "medium", "low"]:
                    if f"{level} risk" in text_lower:
                        self.state["risk_level"] = level.capitalize()
                        break

        # Also scan response messages for phase-setting tool results
        if response_messages:
            resp_msgs = [response_messages] if isinstance(response_messages, ChatMessage) else list(response_messages)
            for msg in resp_msgs:
                text = msg.text or ""
                if isinstance(text, str) and "phase_set" in text:
                    try:
                        data = json.loads(text)
                        if "phase_set" in data:
                            self.state["engagement_phase"] = data["phase_set"]
                    except (json.JSONDecodeError, TypeError):
                        pass


# ---------------------------------------------------------------------------
# Tool — lets the agent explicitly set the engagement phase
# ---------------------------------------------------------------------------

@ai_function
def set_engagement_phase(
    phase: Annotated[str, Field(description="The engagement phase: 'planning', 'fieldwork', 'review', 'complete'")],
) -> str:
    """Set the current engagement phase."""
    return json.dumps({"phase_set": phase})


async def main():
    client = AzureOpenAIResponsesClient(
        endpoint=os.environ.get("AZURE_AI_PROJECT_ENDPOINT") or os.environ["PROJECT_ENDPOINT"],
        deployment_name=os.environ.get("AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME") or os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-5-mini"),
        credential=AzureCliCredential(),
    )

    context_provider = EngagementContextProvider()

    agent = client.create_agent(
        name="MemoryAgent",
        instructions=(
            "You are an audit engagement assistant with memory of the current engagement. "
            "Use the engagement context to provide relevant advice. Be concise."
        ),
        context_providers=[context_provider],
        tools=[set_engagement_phase],
    )

    # Create a thread — conversation history persists across turns
    thread = agent.get_new_thread()

    output_lines: list[str] = []

    # Turn 1: Mention a client — the context provider will remember it
    print("=" * 60)
    print("Turn 1: Establish engagement context")
    print("=" * 60)
    msg1 = "I'm starting work on the Meridian Healthcare engagement. What should I focus on first?"
    result = await agent.run(msg1, thread=thread)
    print(f"User: {msg1}")
    print(f"Agent: {result.text}\n")
    output_lines.append(f"### Turn 1\n**User:** {msg1}\n\n**Agent:** {result.text}")

    # Turn 2: Follow-up — the agent knows which client we're discussing
    print("=" * 60)
    print("Turn 2: Add risk context (agent remembers the client)")
    print("=" * 60)
    msg2 = "It's a high risk engagement. What additional procedures should we plan?"
    result = await agent.run(msg2, thread=thread)
    print(f"User: {msg2}")
    print(f"Agent: {result.text}\n")
    output_lines.append(f"### Turn 2\n**User:** {msg2}\n\n**Agent:** {result.text}")

    # Turn 3: The agent still remembers the client and risk level
    print("=" * 60)
    print("Turn 3: Agent demonstrates accumulated context")
    print("=" * 60)
    msg3 = "Summarize the engagement context we've built up so far."
    result = await agent.run(msg3, thread=thread)
    print(f"User: {msg3}")
    print(f"Agent: {result.text}\n")
    output_lines.append(f"### Turn 3\n**User:** {msg3}\n\n**Agent:** {result.text}")

    # Inspect the provider state
    state_dump = json.dumps(context_provider.state, indent=2)
    print("--- Provider State ---")
    print(state_dump)

    # --- Write output ---
    os.makedirs("02-maf-agents/outputs", exist_ok=True)
    out_path = "02-maf-agents/outputs/04_memory.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# 04 — Memory (Context Providers + Threads)\n\n")
        f.write("\n\n---\n\n".join(output_lines))
        f.write(f"\n\n## Provider State\n\n```json\n{state_dump}\n```\n")
    print(f"\n✅ Output written to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())

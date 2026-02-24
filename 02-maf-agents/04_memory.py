"""
04 — Advanced Memory Management

Demonstrates MAF's context provider system for managing agent memory:
  - BaseContextProvider with before_run/after_run hooks
  - AgentSession for persisting conversation history across turns
  - Dynamic instruction injection based on session state

Concepts: BaseContextProvider, AgentSession, SessionContext, before_run/after_run

Reference: https://github.com/microsoft/agent-framework/tree/main/python/samples/02-agents
"""

import asyncio
import json
import logging
import os
from typing import Annotated, Any

from agent_framework import AgentSession, BaseContextProvider, SessionContext, SupportsAgentRun, tool
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

class EngagementContextProvider(BaseContextProvider):
    """Injects engagement context from session state into every agent call.

    Tracks which client the user is discussing and provides that context
    automatically so the agent doesn't need to be re-told each turn.
    """

    SOURCE_ID = "engagement_context"

    def __init__(self):
        super().__init__(source_id=self.SOURCE_ID)

    async def before_run(
        self,
        *,
        agent: SupportsAgentRun,
        session: AgentSession,
        context: SessionContext,
        state: dict[str, Any],
    ) -> None:
        """Inject stored engagement context into instructions before the model runs."""
        client_name = state.get("current_client")
        engagement_phase = state.get("engagement_phase", "unknown")
        risk_level = state.get("risk_level")

        if client_name:
            context.extend_instructions(
                self.source_id,
                f"Current engagement context:\n"
                f"- Client: {client_name}\n"
                f"- Phase: {engagement_phase}\n"
                + (f"- Risk Level: {risk_level}\n" if risk_level else "")
                + "Use this context to inform your responses.",
            )
        else:
            context.extend_instructions(
                self.source_id,
                "No engagement is currently selected. If the user mentions a client, "
                "remember to set the engagement context.",
            )

    async def after_run(
        self,
        *,
        agent: SupportsAgentRun,
        session: AgentSession,
        context: SessionContext,
        state: dict[str, Any],
    ) -> None:
        """Extract client references from user messages and store in state."""
        known_clients = ["meridian healthcare", "pinnacle manufacturing", "cascade energy"]

        for msg in context.input_messages:
            text = msg.text if hasattr(msg, "text") else ""
            if isinstance(text, str):
                text_lower = text.lower()
                for client in known_clients:
                    if client in text_lower:
                        state["current_client"] = client.title()
                        break

                # Detect risk level mentions
                for level in ["high", "medium", "low"]:
                    if f"{level} risk" in text_lower:
                        state["risk_level"] = level.capitalize()
                        break


# ---------------------------------------------------------------------------
# Tool — lets the agent explicitly set the engagement phase
# ---------------------------------------------------------------------------

@tool(approval_mode="never_require")
def set_engagement_phase(
    phase: Annotated[str, Field(description="The engagement phase: 'planning', 'fieldwork', 'review', 'complete'")],
) -> str:
    """Set the current engagement phase."""
    return json.dumps({"phase_set": phase})


async def main():
    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME"],
        credential=AzureCliCredential(),
    )

    agent = client.as_agent(
        name="MemoryAgent",
        instructions=(
            "You are an audit engagement assistant with memory of the current engagement. "
            "Use the engagement context to provide relevant advice. Be concise."
        ),
        context_providers=[EngagementContextProvider()],
        tools=[set_engagement_phase],
    )

    # Create a session — state persists across turns via AgentSession
    session = agent.create_session()

    output_lines: list[str] = []

    # Turn 1: Mention a client — the context provider will remember it
    print("=" * 60)
    print("Turn 1: Establish engagement context")
    print("=" * 60)
    msg1 = "I'm starting work on the Meridian Healthcare engagement. What should I focus on first?"
    result = await agent.run(msg1, session=session)
    print(f"User: {msg1}")
    print(f"Agent: {result}\n")
    output_lines.append(f"### Turn 1\n**User:** {msg1}\n\n**Agent:** {result}")

    # Turn 2: Follow-up — the agent knows which client we're discussing
    print("=" * 60)
    print("Turn 2: Add risk context (agent remembers the client)")
    print("=" * 60)
    msg2 = "It's a high risk engagement. What additional procedures should we plan?"
    result = await agent.run(msg2, session=session)
    print(f"User: {msg2}")
    print(f"Agent: {result}\n")
    output_lines.append(f"### Turn 2\n**User:** {msg2}\n\n**Agent:** {result}")

    # Turn 3: The agent still remembers the client and risk level
    print("=" * 60)
    print("Turn 3: Agent demonstrates accumulated context")
    print("=" * 60)
    msg3 = "Summarize the engagement context we've built up so far."
    result = await agent.run(msg3, session=session)
    print(f"User: {msg3}")
    print(f"Agent: {result}\n")
    output_lines.append(f"### Turn 3\n**User:** {msg3}\n\n**Agent:** {result}")

    # Inspect the session state
    provider_state = session.state.get(EngagementContextProvider.SOURCE_ID, {})
    state_dump = json.dumps(provider_state, indent=2)
    print(f"--- Session State (provider: {EngagementContextProvider.SOURCE_ID}) ---")
    print(state_dump)

    # --- Write output ---
    os.makedirs("02-maf-agents/outputs", exist_ok=True)
    out_path = "02-maf-agents/outputs/04_memory.md"
    with open(out_path, "w") as f:
        f.write("# 04 — Memory (Context Providers + Sessions)\n\n")
        f.write("\n\n---\n\n".join(output_lines))
        f.write(f"\n\n## Session State\n\n```json\n{state_dump}\n```\n")
    print(f"\n✅ Output written to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())

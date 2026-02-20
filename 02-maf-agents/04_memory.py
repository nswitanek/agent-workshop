"""
04 — Advanced Memory Management

Demonstrates MAF's context provider system for managing agent memory:
  - BaseContextProvider to inject dynamic context per turn
  - Session state for persisting engagement context across turns
  - Using session state from tools

Concepts: BaseContextProvider, AgentSession, session state, before_run/after_run
"""

import asyncio
import json
import os
from typing import Any

from agent_framework import AgentSession, BaseContextProvider, SessionContext, tool
from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import AzureCliCredential
from dotenv import load_dotenv
from pydantic import Field
from typing import Annotated

load_dotenv()


class EngagementContextProvider(BaseContextProvider):
    """Injects engagement context from session state into every agent call.

    Tracks which client the user is discussing and provides that context
    automatically so the agent doesn't need to be re-told.
    """

    DEFAULT_SOURCE_ID = "engagement_context"

    async def before_run(
        self,
        *,
        agent: Any,
        session: AgentSession | None,
        context: SessionContext,
        state: dict[str, Any],
    ) -> None:
        """Inject stored engagement context into instructions."""
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
        agent: Any,
        session: AgentSession | None,
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

    # Create a session — state persists across turns
    session = agent.create_session()

    # Turn 1: Mention a client — the context provider will remember it
    print("Turn 1:")
    result = await agent.run(
        "I'm starting work on the Meridian Healthcare engagement. What should I focus on first?",
        session=session,
    )
    print(f"Agent: {result}\n")

    # Turn 2: Follow-up — the agent knows which client we're discussing
    print("Turn 2:")
    result = await agent.run(
        "It's a high risk engagement. What additional procedures should we plan?",
        session=session,
    )
    print(f"Agent: {result}\n")

    # Turn 3: The agent still remembers the client and risk level
    print("Turn 3:")
    result = await agent.run(
        "Summarize the engagement context we've built up so far.",
        session=session,
    )
    print(f"Agent: {result}\n")

    # Inspect the session state
    provider_state = session.state.get("engagement_context", {})
    print(f"Session state: {json.dumps(provider_state, indent=2)}")


if __name__ == "__main__":
    asyncio.run(main())

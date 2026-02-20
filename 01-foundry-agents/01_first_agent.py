"""
01 — Creating Your First Foundry Agent

Creates a minimal agent using the Azure AI Projects SDK, sends a single
message, and prints the response. This is the simplest possible agent.

Concepts: AIProjectClient, agent creation, threads, runs, messages
"""

import os

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import AgentStreamEvent
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

load_dotenv()


def main():
    # Connect to your Azure AI Foundry project
    client = AIProjectClient(
        credential=AzureCliCredential(),
        endpoint=os.environ["PROJECT_ENDPOINT"],
    )

    # Create an agent with basic instructions
    agent = client.agents.create_agent(
        model=os.environ["MODEL_DEPLOYMENT_NAME"],
        name="AssuranceAssistant",
        instructions="You are a helpful assistant for an assurance practice at a professional services firm.",
    )
    print(f"Created agent: {agent.id}")

    # Create a conversation thread
    thread = client.agents.threads.create()

    # Send a user message
    client.agents.messages.create(
        thread_id=thread.id,
        role="user",
        content="What are the key phases of a financial statement audit?",
    )

    # Run the agent and stream the response
    print("\nAgent response:")
    with client.agents.runs.stream(thread_id=thread.id, agent_id=agent.id) as stream:
        for event_type, event_data, _ in stream:
            if event_type == AgentStreamEvent.THREAD_MESSAGE_DELTA:
                for part in event_data.delta.content:
                    if hasattr(part, "text") and part.text:
                        print(part.text.value, end="", flush=True)
    print()

    # Clean up
    client.agents.delete_agent(agent.id)
    print("\nAgent deleted.")


if __name__ == "__main__":
    main()

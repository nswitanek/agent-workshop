"""
01 — Creating Your First Foundry Agent

Creates a minimal agent using the Azure AI Agents SDK, sends a single
message, and prints the response. This is the simplest possible agent.

Concepts: AgentsClient, agent creation, threads, runs, messages
"""

import os
from pathlib import Path

from azure.ai.agents import AgentsClient
from azure.ai.agents.models import AgentStreamEvent
from azure.core.credentials import AzureKeyCredential
from azure.core.pipeline.policies import AzureKeyCredentialPolicy
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

load_dotenv()

OUTPUTS_DIR = Path(__file__).parent / "outputs"


def main():
    # Connect to your Azure AI Foundry project
    # Use API key if provided, otherwise fall back to Azure CLI auth
    api_key = os.environ.get("AZURE_AI_API_KEY")
    if api_key:
        key_cred = AzureKeyCredential(api_key)
        client = AgentsClient(
            endpoint=os.environ["PROJECT_ENDPOINT"],
            credential=key_cred,
            authentication_policy=AzureKeyCredentialPolicy(key_cred, "api-key"),
        )
    else:
        client = AgentsClient(
            endpoint=os.environ["PROJECT_ENDPOINT"],
            credential=AzureCliCredential(),
        )

    # Create an agent with basic instructions
    agent = client.create_agent(
        model=os.environ["MODEL_DEPLOYMENT_NAME"],
        name="AssuranceAssistant",
        instructions="You are a helpful assistant for an assurance practice at a professional services firm.",
    )
    print(f"Created agent: {agent.id}")

    # Create a conversation thread
    thread = client.threads.create()

    # Send a user message
    client.messages.create(
        thread_id=thread.id,
        role="user",
        content="What are the key phases of a financial statement audit?",
    )

    # Run the agent and stream the response, saving to markdown file
    OUTPUTS_DIR.mkdir(exist_ok=True)
    output_file = OUTPUTS_DIR / "01_first_agent.md"
    response_chunks: list[str] = []

    print("\nAgent response:")
    with client.runs.stream(thread_id=thread.id, agent_id=agent.id) as stream:
        for event_type, event_data, _ in stream:
            if event_type == AgentStreamEvent.THREAD_MESSAGE_DELTA:
                for part in event_data.delta.content:
                    if hasattr(part, "text") and part.text:
                        text = part.text.value
                        print(text, end="", flush=True)
                        response_chunks.append(text)
    print()

    # Write the full response to a markdown file
    output_file.write_text("".join(response_chunks), encoding="utf-8")
    print(f"\nResponse saved to {output_file}")

    # Clean up
    client.delete_agent(agent.id)
    print("Agent deleted.")


if __name__ == "__main__":
    main()

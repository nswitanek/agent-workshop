"""
01 — Introduction to MAF: Hello Agent

Creates a minimal agent using the Microsoft Agent Framework, demonstrating
both non-streaming and streaming responses.

Concepts: AzureOpenAIResponsesClient, as_agent(), run(), streaming
"""

import asyncio
import os

from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

load_dotenv()


async def main():
    # Initialize the client
    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME"],
        credential=AzureCliCredential(),
    )

    # Create an agent with a professional services persona
    agent = client.as_agent(
        name="AssuranceAdvisor",
        instructions=(
            "You are an AI advisor for the assurance practice of a major accounting firm. "
            "Provide clear, professional guidance on audit and assurance topics. "
            "Keep responses concise."
        ),
    )

    # Non-streaming: get the complete response at once
    result = await agent.run("What are the three lines of defense in risk management?")
    print(f"Agent: {result}")

    # Streaming: receive tokens as they are generated
    print("\nAgent (streaming): ", end="", flush=True)
    async for chunk in agent.run(
        "Give a one-sentence definition of 'audit risk'.", stream=True
    ):
        if chunk.text:
            print(chunk.text, end="", flush=True)
    print()


if __name__ == "__main__":
    asyncio.run(main())

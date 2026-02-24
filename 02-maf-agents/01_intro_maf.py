"""
01 — Introduction to MAF: Hello Agent

Creates a minimal agent using the Microsoft Agent Framework, demonstrating
both non-streaming and streaming responses, and AgentSession for conversation
history.

Concepts: AzureOpenAIResponsesClient, as_agent(), run(), streaming, AgentSession

Reference: https://github.com/microsoft/agent-framework/tree/main/python/samples/01-get-started
"""

import asyncio
import logging
import os

from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

load_dotenv()

# logging.basicConfig(level=logging.DEBUG)
# logging.getLogger("azure").setLevel(logging.DEBUG)
# logging.getLogger("httpx").setLevel(logging.WARNING)


async def main():
    # Initialize the Azure OpenAI Responses client
    # This wraps the OpenAI Responses API with Azure identity + Agent Framework
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

    output_lines: list[str] = []

    # --- Part 1: Non-streaming response ---
    print("=" * 60)
    print("Part 1: Non-streaming (complete response at once)")
    print("=" * 60)
    result = await agent.run("What are the three lines of defense in risk management?")
    print(f"Agent: {result}\n")
    output_lines.append(f"## Part 1: Non-streaming\n\n{result}")

    # --- Part 2: Streaming response ---
    print("=" * 60)
    print("Part 2: Streaming (tokens arrive as generated)")
    print("=" * 60)
    streaming_text = ""
    print("Agent: ", end="", flush=True)
    async for chunk in agent.run(
        "Give a one-sentence definition of 'audit risk'.", stream=True
    ):
        if chunk.text:
            print(chunk.text, end="", flush=True)
            streaming_text += chunk.text
    print("\n")
    output_lines.append(f"## Part 2: Streaming\n\n{streaming_text}")

    # --- Part 3: Session-based multi-turn conversation ---
    print("=" * 60)
    print("Part 3: Multi-turn conversation with AgentSession")
    print("=" * 60)

    # create_session() returns an AgentSession that tracks conversation history
    session = agent.create_session()

    turns = [
        "What is the purpose of an audit opinion?",
        "What are the different types?",
        "Which is the most common?",
    ]

    session_lines: list[str] = []
    for user_msg in turns:
        print(f"User: {user_msg}")
        result = await agent.run(user_msg, session=session)
        print(f"Agent: {result}\n")
        session_lines.append(f"**User:** {user_msg}\n\n**Agent:** {result}")

    output_lines.append("## Part 3: Multi-turn (AgentSession)\n\n" + "\n\n---\n\n".join(session_lines))

    # --- Write output ---
    os.makedirs("02-maf-agents/outputs", exist_ok=True)
    out_path = "02-maf-agents/outputs/01_intro_maf.md"
    with open(out_path, "w") as f:
        f.write("# 01 — Introduction to MAF\n\n")
        f.write("\n\n".join(output_lines))
    print(f"✅ Output written to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())

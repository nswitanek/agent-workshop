"""
02 — Configuring Instructions and System Prompts

Demonstrates how system prompts shape agent behavior. Creates two agents
with different instruction styles for the same assurance domain and
compares their responses.

Concepts: instructions, persona definition, domain-specific prompting
"""

import os
from pathlib import Path

from azure.ai.agents import AgentsClient
from azure.ai.agents.models import AgentStreamEvent
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

load_dotenv()

OUTPUTS_DIR = Path(__file__).parent / "outputs"

# A concise, general-purpose instruction set
BASIC_INSTRUCTIONS = """\
You are an assistant for a professional services firm's assurance practice.
Answer questions about auditing clearly and concisely.
"""

# A detailed, role-specific instruction set with guardrails
DETAILED_INSTRUCTIONS = """\
You are a Senior Audit Manager AI assistant at a Big Four accounting firm.

Your role:
- Provide guidance on audit methodology aligned with PCAOB and AICPA standards
- Help staff plan and execute audit engagements
- Ensure responses reference applicable professional standards (e.g., AS 2201, AU-C 315)

Guardrails:
- Never provide legal advice — recommend consulting the firm's legal counsel
- Always caveat that professional judgment is required for engagement-specific decisions
- Do not disclose confidential client information

Tone: Professional, precise, and educational.
"""


def run_agent(client, instructions, label, question):
    """Helper to create an agent, ask a question, and stream the response."""
    agent = client.create_agent(
        model=os.environ["MODEL_DEPLOYMENT_NAME"],
        name=f"AuditAssistant-{label}",
        instructions=instructions,
    )
    print(f"[{label}] Agent created: {agent.id}")

    thread = client.threads.create()
    client.messages.create(thread_id=thread.id, role="user", content=question)

    response_chunks: list[str] = []
    print(f"[{label}] Streaming response:")
    with client.runs.stream(thread_id=thread.id, agent_id=agent.id) as stream:
        for event_type, event_data, _ in stream:
            if event_type == AgentStreamEvent.THREAD_MESSAGE_DELTA:
                for part in event_data.delta.content:
                    if hasattr(part, "text") and part.text:
                        text = part.text.value
                        print(text, end="", flush=True)
                        response_chunks.append(text)
    print("\n")

    client.delete_agent(agent.id)
    return "".join(response_chunks)


def main():
    client = AgentsClient(
        endpoint=os.environ["PROJECT_ENDPOINT"],
        credential=AzureCliCredential(),
    )

    question = "How should we assess the risk of material misstatement for a new audit client?"

    OUTPUTS_DIR.mkdir(exist_ok=True)
    output_parts: list[str] = []

    print("=" * 60)
    print("BASIC INSTRUCTIONS")
    print("=" * 60)
    basic_response = run_agent(client, BASIC_INSTRUCTIONS, "Basic", question)
    output_parts.append(f"# System Prompts Comparison\n\n## Question\n\n{question}\n")
    output_parts.append(f"## Basic Instructions\n\n{basic_response}\n")

    print("=" * 60)
    print("DETAILED INSTRUCTIONS")
    print("=" * 60)
    detailed_response = run_agent(client, DETAILED_INSTRUCTIONS, "Detailed", question)
    output_parts.append(f"## Detailed Instructions\n\n{detailed_response}\n")

    output_file = OUTPUTS_DIR / "02_system_prompts.md"
    output_file.write_text("\n".join(output_parts), encoding="utf-8")
    print(f"\nResponses saved to {output_file}")


if __name__ == "__main__":
    main()

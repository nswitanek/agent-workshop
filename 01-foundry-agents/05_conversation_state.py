"""
05 — Working with Memory and Conversation State

Demonstrates multi-turn conversations using threads. The agent remembers
context from previous messages within the same thread, enabling follow-up
questions about an ongoing audit engagement discussion.

Concepts: threads as memory, multi-turn conversations, conversation state
"""

import os

from azure.ai.projects import AIProjectClient
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

load_dotenv()


def chat(client, agent_id, thread_id, message):
    """Send a message and get the agent's response."""
    client.agents.messages.create(
        thread_id=thread_id,
        role="user",
        content=message,
    )

    run = client.agents.runs.create_and_process(thread_id=thread_id, agent_id=agent_id)

    if run.status == "completed":
        messages = client.agents.messages.list(thread_id=thread_id)
        for msg in messages:
            if msg.role == "assistant":
                return msg.content[0].text.value
    return f"[Run status: {run.status}]"


def main():
    client = AIProjectClient(
        credential=AzureCliCredential(),
        endpoint=os.environ["PROJECT_ENDPOINT"],
    )

    agent = client.agents.create_agent(
        model=os.environ["MODEL_DEPLOYMENT_NAME"],
        name="ConversationAgent",
        instructions=(
            "You are a senior audit manager helping plan an engagement. "
            "Remember details the user shares about the client and engagement "
            "throughout the conversation. Be concise."
        ),
    )

    # Create a single thread — this is the agent's "memory" for the conversation
    thread = client.agents.threads.create()

    # Multi-turn conversation — the agent remembers context across turns
    conversation = [
        "We have a new audit client: TechVentures Inc. They're a mid-cap public SaaS company with $200M revenue.",
        "What are the key risk areas we should focus on for this type of client?",
        "Good points. The client also recently acquired a smaller company. How does that affect our audit plan?",
        "Can you summarize what we've discussed about TechVentures so far?",
    ]

    for i, message in enumerate(conversation, 1):
        print(f"\n{'='*60}")
        print(f"Turn {i}")
        print(f"{'='*60}")
        print(f"User: {message}")
        response = chat(client, agent.id, thread.id, message)
        print(f"\nAgent: {response}")

    # Show that thread state persists — list all messages
    print(f"\n{'='*60}")
    print("FULL THREAD HISTORY")
    print(f"{'='*60}")
    messages = client.agents.messages.list(thread_id=thread.id)
    for msg in reversed(list(messages)):
        print(f"[{msg.role}] {msg.content[0].text.value[:100]}...")

    client.agents.delete_agent(agent.id)
    print("\nAgent deleted.")


if __name__ == "__main__":
    main()

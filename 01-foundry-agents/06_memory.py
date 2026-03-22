"""
06 — Long-Term Memory with the Foundry Agent Memory Service (Preview)

Demonstrates the Foundry Agent Memory Service — persistent, cross-session
memory that lets an agent remember user preferences and past conversations.
This is the Foundry equivalent of Dataverse-backed memory in Copilot Studio.

The example shows two approaches:
  Part A: Memory Store APIs — direct control over storing and retrieving memories
  Part B: Memory Search Tool — attach memory to an agent for automatic read/write

Scenario: An assurance practice where the agent remembers auditor preferences,
client engagement context, and past research across sessions.

Concepts: MemorySearchTool, memory stores, scopes, user profiles, chat summaries

Reference: https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/memory-usage
"""

import os
import time
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    MemorySearchOptions,
    MemorySearchTool,
    MemoryStoreDefaultDefinition,
    MemoryStoreDefaultOptions,
    PromptAgentDefinition,
)
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

OUTPUTS_DIR = Path(__file__).parent / "outputs"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MEMORY_STORE_NAME = "audit-assistant-memory"

AGENT_INSTRUCTIONS = """\
You are a Senior Audit Manager AI assistant at a professional services firm.

You have long-term memory that persists across sessions. Use it to:
- Remember the auditor's preferences (communication style, focus areas, standards)
- Recall past engagement details and client context
- Build on previous research and recommendations

When you recall memories from prior sessions, mention that you remember them.
Be professional, precise, and reference applicable standards when relevant.
"""


# ---------------------------------------------------------------------------
# Part A: Memory Store APIs — Direct Control
# ---------------------------------------------------------------------------

def create_memory_store(project_client: AIProjectClient) -> None:
    """Create a memory store configured for assurance practice use cases."""
    chat_model = os.environ["MODEL_DEPLOYMENT_NAME"]
    embedding_model = os.environ.get(
        "EMBEDDING_MODEL_DEPLOYMENT_NAME", "text-embedding-3-small"
    )

    options = MemoryStoreDefaultOptions(
        chat_summary_enabled=True,
        user_profile_enabled=True,
        user_profile_details=(
            "Auditor preferences for audit methodology, preferred communication "
            "style, areas of specialization, regulatory focus (PCAOB, AICPA, IFRS), "
            "and engagement history context. Avoid storing sensitive client "
            "financials, personally identifiable information, or credentials."
        ),
    )

    definition = MemoryStoreDefaultDefinition(
        chat_model=chat_model,
        embedding_model=embedding_model,
        options=options,
    )

    memory_store = project_client.memory_stores.create(
        name=MEMORY_STORE_NAME,
        definition=definition,
        description="Long-term memory for Audit Research Assistant — stores auditor preferences and engagement context",
    )
    print(f"Created memory store: {memory_store.name}")


def store_memories_via_api(project_client: AIProjectClient, scope: str) -> None:
    """Store memories from simulated past conversations using the direct API."""
    # Simulate a past session where the auditor shared preferences
    past_conversation = [
        {
            "role": "user",
            "content": (
                "I focus primarily on technology and SaaS company audits. "
                "I prefer concise responses that reference PCAOB standards. "
                "I always want to see materiality thresholds discussed early."
            ),
            "type": "message",
        },
        {
            "role": "assistant",
            "content": (
                "Noted — I'll tailor recommendations for technology/SaaS audits, "
                "keep responses concise with PCAOB standard references, and "
                "prioritize materiality thresholds in planning discussions."
            ),
            "type": "message",
        },
        {
            "role": "user",
            "content": (
                "We're working on the TechVentures Inc. engagement — they're a "
                "mid-cap public SaaS company with $200M revenue. Key risks "
                "include revenue recognition under ASC 606 and a recent acquisition."
            ),
            "type": "message",
        },
    ]

    print("\nStoring memories from simulated past session...")
    update_poller = project_client.memory_stores.begin_update_memories(
        name=MEMORY_STORE_NAME,
        scope=scope,
        items=past_conversation,
        update_delay=0,  # Process immediately (in production, use a longer delay)
    )

    update_result = update_poller.result()
    print(f"Stored {len(update_result.memory_operations)} memory operations:")
    for operation in update_result.memory_operations:
        print(f"  - {operation.kind}: {operation.memory_item.content[:80]}...")


def search_memories_via_api(project_client: AIProjectClient, scope: str) -> list[str]:
    """Search for stored memories using the direct API."""
    # Retrieve static user profile memories (no query needed)
    print("\n--- Static User Profile Memories ---")
    static_result = project_client.memory_stores.search_memories(
        name=MEMORY_STORE_NAME,
        scope=scope,
        options=MemorySearchOptions(max_memories=10),
    )
    memories_found = []
    for memory in static_result.memories:
        content = memory.memory_item.content
        print(f"  [{memory.memory_item.memory_id[:8]}] {content}")
        memories_found.append(content)

    # Retrieve contextual memories based on a query
    print("\n--- Contextual Memories (query: TechVentures audit risks) ---")
    query = {
        "role": "user",
        "content": "What do we know about the TechVentures engagement?",
        "type": "message",
    }
    contextual_result = project_client.memory_stores.search_memories(
        name=MEMORY_STORE_NAME,
        scope=scope,
        items=[query],
        options=MemorySearchOptions(max_memories=5),
    )
    for memory in contextual_result.memories:
        content = memory.memory_item.content
        print(f"  [{memory.memory_item.memory_id[:8]}] {content}")
        if content not in memories_found:
            memories_found.append(content)

    return memories_found


# ---------------------------------------------------------------------------
# Part B: Memory Search Tool — Agent-Managed Memory
# ---------------------------------------------------------------------------

def run_agent_with_memory(project_client: AIProjectClient, scope: str) -> str:
    """Create an agent with the MemorySearchTool and run a multi-session demo."""
    # Create memory search tool — the agent reads/writes memory automatically
    memory_tool = MemorySearchTool(
        memory_store_name=MEMORY_STORE_NAME,
        scope=scope,
        update_delay=1,  # 1 second for demo (use 300+ in production)
    )

    # Create the agent with memory tool attached
    agent = project_client.agents.create_version(
        agent_name="AuditMemoryAgent",
        definition=PromptAgentDefinition(
            model=os.environ["MODEL_DEPLOYMENT_NAME"],
            instructions=AGENT_INSTRUCTIONS,
            tools=[memory_tool],
        ),
        description="Audit assistant with long-term memory",
    )
    print(f"\nCreated agent: {agent.name} (version: {agent.version})")

    # Use the OpenAI-compatible conversations API
    openai_client = project_client.get_openai_client()

    # --- Session 1: Establish preferences ---
    print("\n" + "=" * 60)
    print("SESSION 1: Establish auditor preferences")
    print("=" * 60)

    conv1 = openai_client.conversations.create()
    response1 = openai_client.responses.create(
        input=(
            "I specialize in financial services audits and always want "
            "to discuss going-concern risk early in the engagement. "
            "I prefer structured responses with bullet points."
        ),
        conversation=conv1.id,
        extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
    )
    print(f"User: I specialize in financial services audits...")
    print(f"Agent: {response1.output_text}")

    # Wait for memories to be stored
    print("\nWaiting for memories to be stored...")
    time.sleep(5)

    # --- Session 2: New conversation — agent should remember preferences ---
    print("\n" + "=" * 60)
    print("SESSION 2: New conversation — does the agent remember?")
    print("=" * 60)

    conv2 = openai_client.conversations.create()
    response2 = openai_client.responses.create(
        input=(
            "I have a new audit client: Regional Bank Corp, a mid-size "
            "commercial bank with $2B in assets. Help me plan the engagement."
        ),
        conversation=conv2.id,
        extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
    )
    print(f"User: I have a new audit client: Regional Bank Corp...")
    print(f"Agent: {response2.output_text}")

    # Wait for follow-up memories
    time.sleep(5)

    # --- Session 3: Reference both past sessions ---
    print("\n" + "=" * 60)
    print("SESSION 3: Reference prior context")
    print("=" * 60)

    conv3 = openai_client.conversations.create()
    response3 = openai_client.responses.create(
        input="What do you remember about my preferences and ongoing engagements?",
        conversation=conv3.id,
        extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
    )
    print(f"User: What do you remember about my preferences and ongoing engagements?")
    print(f"Agent: {response3.output_text}")

    # Clean up agent
    project_client.agents.delete("AuditMemoryAgent")
    print("\nAgent deleted.")

    return response3.output_text


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    project_client = AIProjectClient(
        endpoint=os.environ["PROJECT_ENDPOINT"],
        credential=DefaultAzureCredential(),
    )

    scope = "auditor_demo_user"

    # --- Part A: Memory Store APIs ---
    print("=" * 60)
    print("PART A: Memory Store APIs — Direct Control")
    print("=" * 60)

    # Create the memory store (skip if it already exists)
    try:
        existing = project_client.memory_stores.get(MEMORY_STORE_NAME)
        print(f"Memory store already exists: {existing.name}")
    except Exception:
        create_memory_store(project_client)

    # Store memories from a simulated past session
    store_memories_via_api(project_client, scope)

    # Search for stored memories
    memories = search_memories_via_api(project_client, scope)

    # --- Part B: Agent with Memory Tool ---
    print("\n" + "=" * 60)
    print("PART B: Memory Search Tool — Agent-Managed Memory")
    print("=" * 60)

    final_response = run_agent_with_memory(project_client, scope)

    # --- Save output ---
    OUTPUTS_DIR.mkdir(exist_ok=True)
    output_file = OUTPUTS_DIR / "06_memory.md"
    output_parts = [
        "# Long-Term Memory Results\n",
        "## Part A: Stored Memories\n",
    ]
    for mem in memories:
        output_parts.append(f"- {mem}")
    output_parts.append(f"\n## Part B: Agent with Memory (Session 3 Response)\n\n{final_response}\n")

    output_file.write_text("\n".join(output_parts), encoding="utf-8")
    print(f"\nResults saved to {output_file}")

    # --- Cleanup ---
    print("\nCleaning up...")
    project_client.memory_stores.delete_scope(
        name=MEMORY_STORE_NAME, scope=scope
    )
    print(f"Deleted memories for scope: {scope}")

    project_client.memory_stores.delete(MEMORY_STORE_NAME)
    print(f"Deleted memory store: {MEMORY_STORE_NAME}")


if __name__ == "__main__":
    main()

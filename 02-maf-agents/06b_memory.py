"""
06b — Long-Term Memory with Microsoft Agent Framework

Parallel to Foundry Agents Exercise 06 (Foundry SDK memory), this exercise demonstrates
long-term, cross-session memory using MAF's context provider architecture.

  Part A: LocalPersistentMemoryProvider — file-backed memory that always works
           (no cloud dependency, great for development and testing)

Key insight: MAF's ContextProvider is service-agnostic. Any memory backend
(local files, Redis, Mem0, Foundry) can be plugged in by implementing
invoking() and invoked() hooks — your agent code doesn't change.

To swap in Foundry Memory Service, replace LocalPersistentMemoryProvider with
FoundryMemoryProvider (see Part B notes at the end).

Concepts: ContextProvider, Context, AgentThread, persistent memory, scope

Reference: https://github.com/microsoft/agent-framework/tree/main/python
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any, MutableSequence, Sequence

from agent_framework import ChatMessage, Context, ContextProvider
from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

load_dotenv()

SCRIPT_DIR = Path(__file__).parent
OUTPUTS_DIR = SCRIPT_DIR / "outputs"
DATA_DIR = SCRIPT_DIR / "data"

AGENT_INSTRUCTIONS = """\
You are a Senior Audit Manager AI assistant at a professional services firm.

You have long-term memory that persists across sessions. Use it to:
- Remember the auditor's preferences (communication style, focus areas, standards)
- Recall past engagement details and client context
- Build on previous research and recommendations

When you recall memories from prior sessions, explicitly mention what you remember.
Be professional, precise, and reference applicable standards when relevant.
"""


# ---------------------------------------------------------------------------
# Part A: Local Persistent Memory Provider (file-backed, always works)
# ---------------------------------------------------------------------------

class LocalPersistentMemoryProvider(ContextProvider):
    """A memory provider that persists memories to a local JSON file.

    Implements the ContextProvider pattern (invoking/invoked) — the same
    pattern used by FoundryMemoryProvider, Mem0ContextProvider, and
    RedisContextProvider. This version uses a local file instead of a
    cloud service.

    Memory types stored:
      - user_profile: key-value facts extracted from conversation
      - chat_summaries: summaries of past conversations
    """

    def __init__(self, memory_file: str | Path, scope: str = "default"):
        self.memory_file = Path(memory_file)
        self.scope = scope
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)

    def _load_memories(self) -> dict:
        if self.memory_file.exists():
            return json.loads(self.memory_file.read_text(encoding="utf-8"))
        return {}

    def _save_memories(self, data: dict) -> None:
        self.memory_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    async def invoking(
        self,
        messages: ChatMessage | MutableSequence[ChatMessage],
        **kwargs: Any,
    ) -> Context:
        """Load stored memories and return them as additional instructions."""
        all_memories = self._load_memories()
        scope_memories = all_memories.get(self.scope, {})
        profile = scope_memories.get("user_profile", {})
        summaries = scope_memories.get("chat_summaries", [])

        if profile or summaries:
            parts = ["## Memories from previous sessions\n"]
            if profile:
                parts.append("### User Profile")
                for key, value in profile.items():
                    parts.append(f"- **{key}**: {value}")
                parts.append("")
            if summaries:
                parts.append("### Past Conversation Summaries")
                for s in summaries[-5:]:
                    parts.append(f"- {s}")
            return Context(instructions="\n".join(parts))

        return Context(instructions="No memories from previous sessions.")

    async def invoked(
        self,
        request_messages: ChatMessage | Sequence[ChatMessage],
        response_messages: ChatMessage | Sequence[ChatMessage] | None = None,
        invoke_exception: Exception | None = None,
        **kwargs: Any,
    ) -> None:
        """Extract facts from the conversation and persist them to file."""
        if invoke_exception:
            return

        all_memories = self._load_memories()
        if self.scope not in all_memories:
            all_memories[self.scope] = {"user_profile": {}, "chat_summaries": []}
        scope_data = all_memories[self.scope]

        msgs = [request_messages] if isinstance(request_messages, ChatMessage) else list(request_messages)
        for msg in msgs:
            text = msg.text or ""
            if not text:
                continue
            tl = text.lower()

            if any(k in tl for k in ["prefer", "i like", "i always"]):
                scope_data["user_profile"]["preferences"] = text.strip()
            if any(k in tl for k in ["specialize", "focus on"]):
                scope_data["user_profile"]["specialization"] = text.strip()
            if any(k in tl for k in ["engagement", "audit client", "working on", "starting"]):
                scope_data["user_profile"]["current_engagement"] = text.strip()
            if any(std in tl for std in ["pcaob", "aicpa", "ifrs", "isa"]):
                scope_data["user_profile"]["standards_focus"] = text.strip()

        # Store a brief summary of this turn
        user_texts = [m.text.strip() for m in msgs if m.text and m.text.strip()]
        if user_texts:
            scope_data["chat_summaries"].append("; ".join(user_texts)[:200])
            scope_data["chat_summaries"] = scope_data["chat_summaries"][-20:]

        self._save_memories(all_memories)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    credential = AzureCliCredential()
    project_endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT") or os.environ.get("PROJECT_ENDPOINT", "")
    deployment = os.environ.get("AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME") or os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-4o")

    # Derive the OpenAI-compatible base URL from the Foundry project endpoint
    base = project_endpoint.split("/api/projects/")[0] if "/api/projects/" in project_endpoint else project_endpoint
    base_url = f"{base}/openai/v1/"

    client = AzureOpenAIResponsesClient(
        base_url=base_url,
        deployment_name=deployment,
        credential=credential,
    )

    output_lines: list[str] = []
    memory_file = DATA_DIR / "local_memories.json"

    print("=" * 60)
    print("Long-Term Memory via MAF ContextProvider (file-backed)")
    print("=" * 60)

    memory_provider = LocalPersistentMemoryProvider(
        memory_file=memory_file, scope="auditor_demo_user",
    )

    agent = client.create_agent(
        name="AuditMemoryAgent-Local",
        instructions=AGENT_INSTRUCTIONS,
        context_providers=[memory_provider],
    )

    # --- Session 1: Establish preferences ---
    print("\n--- Session 1: Establish preferences ---")
    thread1 = agent.get_new_thread()
    msg1 = (
        "I specialize in technology and SaaS company audits. "
        "I prefer concise responses with PCAOB standard references. "
        "I always want materiality thresholds discussed early."
    )
    print(f"User: {msg1}")
    result1 = await agent.run(msg1, thread=thread1)
    print(f"Agent: {result1}\n")
    output_lines.append(f"### Session 1\n**User:** {msg1}\n\n**Agent:** {result1}")

    # --- Session 2: New thread — agent should remember via file ---
    print("--- Session 2: New thread — does the agent remember? ---")
    thread2 = agent.get_new_thread()
    msg2 = (
        "I'm starting the TechVentures Inc. engagement — "
        "they're a mid-cap SaaS company. Help me plan."
    )
    print(f"User: {msg2}")
    result2 = await agent.run(msg2, thread=thread2)
    print(f"Agent: {result2}\n")
    output_lines.append(f"### Session 2\n**User:** {msg2}\n\n**Agent:** {result2}")

    # --- Session 3: Verify accumulated memory ---
    print("--- Session 3: Verify accumulated memory ---")
    thread3 = agent.get_new_thread()
    msg3 = "What do you remember about my preferences and engagements?"
    print(f"User: {msg3}")
    result3 = await agent.run(msg3, thread=thread3)
    print(f"Agent: {result3}\n")
    output_lines.append(f"### Session 3\n**User:** {msg3}\n\n**Agent:** {result3}")

    # Show stored memories
    memories = json.loads(memory_file.read_text(encoding="utf-8"))
    memories_json = json.dumps(memories, indent=2)
    print(f"--- Stored memories ({memory_file}) ---")
    print(memories_json)

    # --- Save output ---
    OUTPUTS_DIR.mkdir(exist_ok=True)
    out_path = OUTPUTS_DIR / "06b_memory.md"
    parts = [
        "# 06b — Long-Term Memory with MAF\n",
        "## Local Persistent Memory (file-backed)\n",
        "\n\n---\n\n".join(output_lines),
        f"\n\n## Stored Memories\n\n```json\n{memories_json}\n```\n",
        "\n## Swapping to FoundryMemoryProvider\n\n",
        "Replace `LocalPersistentMemoryProvider` with `FoundryMemoryProvider` — "
        "the agent code stays identical:\n\n"
        "```python\n"
        "from agent_framework.azure import FoundryMemoryProvider\n\n"
        "memory_provider = FoundryMemoryProvider(\n"
        "    project_client=project_client,\n"
        "    memory_store_name='my-store',\n"
        "    scope='user_123',\n"
        "    update_delay=0,\n"
        ")\n"
        "```\n\n"
        "Requires RBAC setup — see `01-foundry-agents/06_memory.md`.\n",
    ]
    out_path.write_text("\n".join(parts), encoding="utf-8")
    print(f"\n✅ Output written to {out_path}")

    # Clean up
    if memory_file.exists():
        memory_file.unlink()
        print(f"Cleaned up {memory_file}")


if __name__ == "__main__":
    asyncio.run(main())

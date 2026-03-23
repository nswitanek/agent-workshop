# Exercise 6b: Long-Term Memory with Microsoft Agent Framework

In Exercise 06 you explored the **Foundry Memory Service** for persistent, cross-session memory. This exercise demonstrates the same concept using MAF's **ContextProvider** architecture — a pluggable memory system where you can swap backends without changing your agent code.

## What You'll Learn

- How MAF's `ContextProvider` pattern separates memory logic from agent logic
- How to build a **custom persistent memory provider** backed by a local file
- How the same pattern powers `FoundryMemoryProvider`, `Mem0ContextProvider`, and `RedisContextProvider`
- How to swap memory backends without changing agent code

## Key Concept: The ContextProvider Pattern

MAF uses a hooks-based pattern for injecting context into agent calls:

```
┌─────────────────────────────────────────────────────────┐
│  User sends message                                     │
│       ↓                                                 │
│  ContextProvider.invoking(messages) → Context            │
│       ↓                                                 │
│  Agent runs with: instructions + Context.instructions   │
│       ↓                                                 │
│  ContextProvider.invoked(request, response)              │
│       ↓                                                 │
│  Response returned to user                              │
└─────────────────────────────────────────────────────────┘
```

| Hook | When | Purpose |
|------|------|---------|
| `invoking()` | Before model call | Load memories, return `Context(instructions=...)` to inject |
| `invoked()` | After model call | Extract facts from conversation, persist to storage |
| `thread_created()` | New thread created | Optional initialization (e.g., load user profile) |

Any memory backend can be plugged in by implementing these hooks. Your agent code stays identical:

```python
# Swap LocalPersistentMemoryProvider ↔ FoundryMemoryProvider ↔ RedisContextProvider
agent = client.create_agent(
    name="MyAgent",
    instructions="...",
    context_providers=[memory_provider],  # ← only this line changes
)
```

## Comparison: Memory Approaches

| Approach | Backend | Persistence | Semantic Search | Cloud Required |
|----------|---------|-------------|-----------------|----------------|
| **Exercise 04** (`04_memory.py`) | In-process dict | Session only | No | No |
| **Exercise 06** (`06_memory.py`) | Foundry Memory Service | Cross-session | Yes (embeddings) | Yes |
| **Exercise 06b** — Part A | Local JSON file | Cross-session | No (keyword) | No |
| **Exercise 06b** — FoundryMemoryProvider | Foundry Memory Service | Cross-session | Yes | Yes |
| MAF `Mem0ContextProvider` | Mem0 platform/OSS | Cross-session | Yes | Depends |
| MAF `RedisContextProvider` | Redis + RediSearch | Cross-session | Yes (hybrid) | Self-hosted |

## Prerequisites

- The same `.env` configuration from the MAF exercises (`AZURE_AI_PROJECT_ENDPOINT`, `AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME`)
- `agent-framework[azure]` installed (already in `requirements.txt`)

## Code Walkthrough (`06b_memory.py`)

### Part A: LocalPersistentMemoryProvider

A custom `ContextProvider` that persists memories to a local JSON file. This always works — no cloud dependency, no RBAC setup needed.

#### How it works

1. **`invoking()`** — Reads the JSON file, formats stored user profile facts and conversation summaries as instructions, returns a `Context` object
2. **`invoked()`** — Extracts facts from the user's message (preferences, specializations, engagement mentions, standards references) and appends them to the JSON file

```python
class LocalPersistentMemoryProvider(ContextProvider):

    async def invoking(self, messages, **kwargs) -> Context:
        # Load memories from file → inject as instructions
        memories = self._load_memories()
        return Context(instructions="User prefers concise PCAOB responses...")

    async def invoked(self, request_messages, response_messages, **kwargs):
        # Extract facts → save to file
        self._save_memories(extracted_facts)
```

#### Memory storage format

```json
{
  "auditor_demo_user": {
    "user_profile": {
      "specialization": "I specialize in technology and SaaS company audits...",
      "preferences": "I prefer concise responses with PCAOB standard references...",
      "standards_focus": "...",
      "current_engagement": "TechVentures Inc. — mid-cap SaaS company..."
    },
    "chat_summaries": [
      "Session 1 summary...",
      "Session 2 summary..."
    ]
  }
}
```

### The Demo: Three Sessions

The script runs three separate sessions (new `AgentThread` each time) to demonstrate cross-session memory:

| Session | What happens | What to observe |
|---------|-------------|-----------------|
| **1** | User states preferences (SaaS audits, PCAOB, materiality) | Agent acknowledges; facts saved to file |
| **2** | User starts new engagement (TechVentures) | Agent remembers preferences from Session 1, tailors response |
| **3** | User asks "What do you remember?" | Agent lists all accumulated facts from Sessions 1 and 2 |

### Part B: Swapping to FoundryMemoryProvider

To use the Foundry Memory Service instead of local files, replace one line:

```python
# Before (local file)
memory_provider = LocalPersistentMemoryProvider(
    memory_file="data/local_memories.json",
    scope="auditor_demo_user",
)

# After (Foundry cloud)
from agent_framework.azure import FoundryMemoryProvider

memory_provider = FoundryMemoryProvider(
    project_client=project_client,
    memory_store_name="my-store",
    scope="auditor_demo_user",
    update_delay=0,  # use 300+ in production
)
```

The agent code is identical — only the provider changes. The `FoundryMemoryProvider` adds:
- **Semantic search** over memories using embeddings
- **User profile extraction** via LLM summarization
- **Incremental updates** with debouncing to reduce costs

> **Note:** FoundryMemoryProvider requires the same RBAC setup described in `01-foundry-agents/06_memory.md` (managed identity + "Azure AI User" + "Cognitive Services OpenAI User" roles). See that exercise for prerequisites.

## Running the Exercise

```bash
cd 02-maf-agents
python 06b_memory.py
```

Expected output:
- Session 1: Agent acknowledges preferences
- Session 2: Agent references your preferences when planning the TechVentures engagement
- Session 3: Agent summarizes everything it remembers
- Stored memories JSON printed at the end
- Local memory file cleaned up automatically

## Exercises to Try

1. **Add more memory types.** Extend the `invoked()` method to detect and store additional fact types (risk levels, materiality thresholds, team members mentioned).

2. **Add semantic search.** Instead of injecting all memories, use keyword matching or a simple TF-IDF to select only relevant memories for each query.

3. **Swap to FoundryMemoryProvider.** If you have the RBAC setup from Exercise 06, replace the local provider with `FoundryMemoryProvider` and compare the behavior.

4. **Combine multiple providers.** MAF supports multiple context providers — try using `LocalPersistentMemoryProvider` for user profile AND an `InMemoryHistoryProvider` for conversation history:
   ```python
   context_providers=[memory_provider, InMemoryHistoryProvider()]
   ```

## Key Takeaways

- MAF's `ContextProvider` is **service-agnostic** — the same pattern works with local files, Foundry, Mem0, Redis, or any custom backend
- **`invoking()`** loads context before the model runs; **`invoked()`** stores context after
- The agent code **never changes** when you swap memory backends — only the provider instance changes
- Local file persistence is great for **development and testing**; cloud backends add **semantic search and scalability**
- Multiple providers can run simultaneously — each contributes its own `Context` to the agent

## Next Steps

- → [`05_guardrails.py`](./05_guardrails.py) — Implementing guardrails and safety with MAF middleware
- → [`01-foundry-agents/07_evaluations.py`](../01-foundry-agents/07_evaluations.py) — Evaluating agent quality

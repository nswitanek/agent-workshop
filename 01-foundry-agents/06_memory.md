# Exercise 6: Long-Term Memory with the Foundry Agent Memory Service (Preview)

In this exercise, you'll move beyond single-conversation threads and give your
agent **persistent memory** — the ability to remember facts and preferences
across sessions, just like a human colleague would.

## What You'll Learn

- How the **Foundry Agent Memory Service** stores and retrieves information across conversations
- How to create and configure a **memory store** with user profiles and chat summaries
- How to use the **direct memory APIs** to store and search memories programmatically
- How to attach a **MemorySearchTool** to an agent for automatic memory management
- How this compares to **Copilot Studio** global variables and Dataverse persistence

> **Reference:** [What is memory?](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/what-is-memory?tabs=conversational-agent) · [Memory usage how-to](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/memory-usage)

## Background

### From Short-Term to Long-Term Memory

In [Exercise 5](./05_conversation_state.md) you learned that threads provide
**short-term memory** — the agent remembers everything within a single
conversation but forgets everything when a new thread starts.

The Memory Service adds a **long-term memory** layer:

| Memory Type | Scope | Lifetime | Mechanism |
|-------------|-------|----------|-----------|
| **Thread messages** | Single conversation | Until thread is deleted | Message history in a thread |
| **Chat summaries** | Cross-session | Persistent | Memory Service auto-summarizes conversations |
| **User profile** | Cross-session | Persistent | Memory Service extracts user preferences and facts |

### How It Works

The Memory Service has three phases:

1. **Extraction** — After a conversation, the service identifies important facts
   (preferences, context, decisions) and extracts them as discrete memory items.
2. **Consolidation** — New memories are merged with existing ones; duplicates are
   removed and contradictions are resolved (newer information wins).
3. **Retrieval** — When a new conversation starts, relevant memories are fetched
   and injected into the agent's context.

### Two Approaches

| Approach | When to Use |
|----------|-------------|
| **MemorySearchTool** (Part B) | Attach to an agent — it reads and writes memory automatically during conversations, no manual calls needed |
| **Memory Store APIs** (Part A) | Direct programmatic control — store and search memories yourself, useful for batch ingestion or custom workflows |

### Copilot Studio Comparison

| Concept | Copilot Studio | Foundry SDK |
|---------|---------------|-------------|
| Within-conversation state | Conversation context (automatic) | Thread message history |
| Cross-topic state | Global variables | Thread (single conversation) |
| Cross-session persistence | Dataverse tables | **Memory Service** (user profile + chat summary) |
| User preferences | Dataverse + Power Automate | Memory Service user profile extraction |
| Configuration | Low-code variable setup | `MemoryStoreDefaultDefinition` + `MemorySearchTool` |

In Copilot Studio (Exercise 5), you built topics with global variables to carry
engagement context within a session, and would use Dataverse for persistence. Here,
the Memory Service handles persistence automatically — no table schema needed.

## Prerequisites

- A Foundry project with the `PROJECT_ENDPOINT` environment variable set
- A chat model deployment (`MEMORY_CHAT_MODEL`) — e.g., `gpt-4o`
  *(defaults to `gpt-4o` — must be a deployment available through the project's Azure OpenAI connection)*
- An embedding model deployment (`AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME`) — e.g., `text-embedding-3-small`
  *(defaults to `text-embedding-3-small` if not set)*
- `azure-ai-projects >= 2.0.0` installed

> **Note:** The Memory Service is in **preview**. API surface may change.

### Authorization Setup (Required)

The memory service runs server-side and needs its own credentials to access your models. This requires **RBAC configuration** — without it, you'll get `"Authentication failed"` errors even though other exercises work fine.

1. **Enable system-assigned managed identity** on your Foundry resource:
   - Azure Portal → your Foundry resource → **Resource Management** → **Identity** → toggle **System assigned** to **On**

2. **Assign roles** to the managed identity on the resource that contains your project:
   - Azure Portal → your Foundry resource → **Access control (IAM)** → **Add role assignment**
   - Assign **Azure AI User** to the managed identity
   - Also assign **Cognitive Services OpenAI User**

3. **Ensure your Azure OpenAI connection uses Entra ID auth**:
   - The memory service authenticates to Azure OpenAI using the managed identity
   - If your Azure OpenAI resource has `disableLocalAuth=true` (API keys disabled), the connection **must** use Entra ID (AAD) authentication, not API key
   - Check your project's Connected Resources — the default AzureOpenAI connection should show auth type as `AAD`

```bash
# Verify managed identity exists
az cognitiveservices account show \
  --name <your-foundry-resource> \
  --resource-group <your-rg> \
  --query "identity.principalId" -o tsv

# Assign required roles (use the principalId from above)
az role assignment create --assignee <principalId> \
  --role "Azure AI User" --scope <foundry-resource-id>
az role assignment create --assignee <principalId> \
  --role "Cognitive Services OpenAI User" --scope <foundry-resource-id>
```

> **Troubleshooting "Authentication failed":** If the memory store creates successfully but `begin_update_memories` fails, the memory service backend can't authenticate to the Azure OpenAI resource. Check: (1) managed identity is enabled, (2) RBAC roles are assigned, (3) the Azure OpenAI connection uses Entra ID auth (not API key, if local auth is disabled). RBAC changes take up to 10 minutes to propagate.

## Code Walkthrough (`06_memory.py`)

### Part A: Memory Store APIs — Direct Control

#### A1. Create a Memory Store

A memory store is the container for all memories. You configure it with:
- A **chat model** — for extracting and consolidating memories
- An **embedding model** — for semantic search over memories
- **Options** — enable user profile extraction and/or chat summaries

```python
options = MemoryStoreDefaultOptions(
    chat_summary_enabled=True,
    user_profile_enabled=True,
    user_profile_details=(
        "Auditor preferences for audit methodology, preferred communication "
        "style, areas of specialization, regulatory focus..."
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
    description="Long-term memory for Audit Research Assistant",
)
```

The `user_profile_details` string guides what the memory service extracts from
conversations — this is like giving it a schema of what matters.

#### A2. Store Memories (Simulated Past Sessions)

You can feed past conversation messages into the memory store using the direct API.
This is useful for pre-loading context or migrating from another system:

```python
past_conversation = [
    {"role": "user", "content": "I focus on technology and SaaS audits...", "type": "message"},
    {"role": "assistant", "content": "Noted — I'll tailor...", "type": "message"},
]

update_poller = project_client.memory_stores.begin_update_memories(
    name=MEMORY_STORE_NAME,
    scope=scope,
    items=past_conversation,
    update_delay=0,  # Process immediately
)
```

**Scope** is a string that groups memories — typically a user identifier. All
memories within a scope are accessible together.

#### A3. Search Memories

Two search modes:

- **Static** — retrieve user profile memories without a query
- **Contextual** — search with a query to find relevant memories

```python
# Static: user profile
result = project_client.memory_stores.search_memories(
    name=MEMORY_STORE_NAME, scope=scope,
    options=MemorySearchOptions(max_memories=10),
)

# Contextual: find memories matching a question
result = project_client.memory_stores.search_memories(
    name=MEMORY_STORE_NAME, scope=scope,
    items=[{"role": "user", "content": "TechVentures engagement?", "type": "message"}],
    options=MemorySearchOptions(max_memories=5),
)
```

### Part B: Memory Search Tool — Agent-Managed Memory

In this approach you attach a `MemorySearchTool` to your agent and the
platform handles memory read/write automatically during conversations.

#### B1. Create the Agent

Memory-enabled agents use a different creation API — `agents.create_version()`
with a `PromptAgentDefinition`:

```python
memory_tool = MemorySearchTool(
    memory_store_name=MEMORY_STORE_NAME,
    scope=scope,
    update_delay=1,  # seconds to wait before processing new memories
)

agent = project_client.agents.create_version(
    agent_name="AuditMemoryAgent",
    definition=PromptAgentDefinition(
        model=os.environ["MODEL_DEPLOYMENT_NAME"],
        instructions=AGENT_INSTRUCTIONS,
        tools=[memory_tool],
    ),
)
```

#### B2. Conversations API

Memory-enabled agents use the **conversations API** (via the OpenAI client)
rather than the threads API used in earlier exercises:

```python
openai_client = project_client.get_openai_client()
conversation = openai_client.conversations.create()

response = openai_client.responses.create(
    input="I specialize in financial services audits...",
    conversation=conversation.id,
    extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
)
```

Each `conversations.create()` starts a new session, but the agent retrieves
memories from the shared memory store — so it "remembers" across sessions.

#### B3. Multi-Session Demo

The script runs three sessions:

1. **Session 1:** Auditor shares preferences (financial services focus, bullet-point style)
2. **Session 2:** New conversation — auditor asks about a new client. The agent should recall preferences from Session 1.
3. **Session 3:** Auditor asks "What do you remember?" — the agent should reference both prior sessions.

## Running the Exercise

```bash
cd 01-foundry-agents

# Ensure your .env has:
#   PROJECT_ENDPOINT=https://your-project.services.ai.azure.com/api/projects/your-project
#   MODEL_DEPLOYMENT_NAME=gpt-4o
#   EMBEDDING_MODEL_DEPLOYMENT_NAME=text-embedding-3-small  (optional, defaults to this)

python 06_memory.py
```

Output is saved to `outputs/06_memory.md`.

## Exercises

### Exercise 1: Observe Memory Extraction

After running the script, examine the output from Part A:

- What did the memory service extract as **user profile** items?
- What was stored as **chat summary** items?
- How does the `user_profile_details` prompt affect what gets extracted?

Try modifying `user_profile_details` to include "preferred audit frameworks"
and re-run — do you see different profile items?

### Exercise 2: Memory Across Engagement Types

Modify the simulated past conversation in Part A to describe a **healthcare
industry** audit engagement instead of technology. Then search for memories
with the query "What audit approach should I use?"

- Does the memory service return healthcare-specific context?
- What happens if you store both technology and healthcare engagement
  memories in the same scope?

### Exercise 3: Add a Fourth Session

In Part B, add a Session 4 after the existing three:

```python
response4 = openai_client.responses.create(
    input=(
        "The Regional Bank Corp engagement has been completed. "
        "We issued an unqualified opinion. Move it to completed status."
    ),
    conversation=openai_client.conversations.create().id,
    extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
)
```

Then start Session 5 and ask about completed engagements. Does the agent
remember the completion?

### Exercise 4: Scope Isolation

The `scope` parameter controls memory isolation. Run the script twice with
different scopes (e.g., `"auditor_alice"` and `"auditor_bob"`) and store
different preferences for each.

- Verify that Alice's agent doesn't see Bob's memories
- Think about how you'd use scopes in a multi-tenant audit practice

### Exercise 5: Compare with Copilot Studio

Review [Copilot Studio Exercise 5](../00-copilot-studio/05_memory.md) and
compare the two approaches:

| Question | Your Answer |
|----------|-------------|
| How does Copilot Studio handle conversation-level state vs. Foundry threads? | |
| What's the Copilot Studio equivalent of a memory store scope? | |
| When would you choose Dataverse persistence vs. the Memory Service? | |
| Which approach gives more control over what gets remembered? | |

## Key Takeaways

- **Memory stores** add persistent, cross-session memory to Foundry agents — no database setup needed
- The **user profile** feature automatically extracts preferences and facts from conversations
- **Chat summaries** capture conversation highlights for future reference
- **Scopes** isolate memories by user or context — critical for multi-tenant scenarios
- The **MemorySearchTool** is the easiest approach: attach it and the agent handles memory automatically
- The **direct APIs** give you fine-grained control for batch ingestion, custom search, and cleanup
- This is the Foundry equivalent of Copilot Studio's Dataverse-backed persistence, with the advantage
  of automatic extraction (no topic/variable configuration required)

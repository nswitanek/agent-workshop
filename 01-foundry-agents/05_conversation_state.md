# Exercise 5: Working with Conversation State (Threads)

In Copilot Studio, **conversation context** is automatic — the agent remembers what was said earlier in the same session. In Foundry, this same concept is implemented through **threads**. This exercise explores how threads act as short-term memory, enabling multi-turn conversations where the agent maintains awareness of everything discussed so far.

## What You'll Learn

- How threads work as the agent's short-term (session) memory
- How multi-turn conversations maintain context automatically
- How thread scope compares to Copilot Studio's conversation context
- How to demonstrate that context resets when a new thread is created

## Copilot Studio vs. Foundry — Conversation Memory

| Aspect | Copilot Studio | Foundry SDK |
|--------|---------------|-------------|
| **Short-term memory** | Automatic — LLM sees conversation history | Threads — all messages in a thread are context |
| **Scope** | Current session (browser tab) | Current thread (thread ID) |
| **Lifetime** | Until user closes session | Until thread is deleted |
| **Cross-topic context** | Automatic with generative orchestration | Same thread = same context |
| **Variables** | Topic / Global variables for structured state | Thread metadata or your app layer |
| **Reset** | Start new conversation | Create new thread |

## Background: What Is a Thread?

A **thread** is a conversation container. When you create a thread and send messages to it, the agent sees *all prior messages* in that thread as context — just like how Copilot Studio's LLM sees the conversation history in the test panel.

```
Thread (short-term memory)
├── User: "We have a new client: TechVentures Inc., $200M SaaS company."
├── Agent: "I'll note that. Key risk areas for SaaS include..."
├── User: "They also just acquired a smaller company."
├── Agent: "The acquisition adds risks around...
│           Combined with the SaaS risks we discussed..."  ← remembers context
└── User: "Summarize what we've discussed."
    Agent: "TechVentures Inc. is a $200M SaaS company that recently..."  ← full recall
```

This is equivalent to what happens in Copilot Studio when you type multiple messages — the agent "remembers" because the LLM sees the full message history.

## Code Walkthrough

Open [`05_conversation_state.py`](./05_conversation_state.py) and review the structure.

### The `chat()` Helper

```python
def chat(client, agent_id, thread_id, message):
    """Send a message and get the agent's response."""
    client.messages.create(thread_id=thread_id, role="user", content=message)
    run = client.runs.create_and_process(thread_id=thread_id, agent_id=agent_id)
    # ... return the assistant's response
```

Each call to `chat()` adds a message to the thread. The agent sees all previous messages when generating a response — this is the short-term memory mechanism.

### Single Thread = Continuous Context

```python
# Create ONE thread — all messages share the same context
thread = client.threads.create()

# Turn 1: Introduce the client
chat(client, agent.id, thread.id,
     "We have a new audit client: TechVentures Inc. $200M SaaS company.")

# Turn 4: Agent can recall everything from turns 1-3
chat(client, agent.id, thread.id,
     "Can you summarize what we've discussed about TechVentures so far?")
```

## Running the Example

```bash
cd 01-foundry-agents
python 05_conversation_state.py
```

The script runs a four-turn conversation about a new audit engagement. Watch how the agent:
1. **Accepts new information** (client details in turn 1)
2. **Applies it contextually** (risk areas for a SaaS client in turn 2)
3. **Builds on prior context** (acquisition impact on the existing audit plan in turn 3)
4. **Recalls the full conversation** (summary in turn 4)

## Exercises

### Exercise 1: New Thread = Fresh Start

Modify the script to create a **second thread** after the four-turn conversation, then ask:
> *"What client are we discussing?"*

The agent should have no context — demonstrating that threads are isolated memory containers.

```python
# After the first conversation...
new_thread = client.threads.create()
response = chat(client, agent.id, new_thread.id,
                "What client are we discussing?")
# Agent won't know — different thread, no shared context
```

### Exercise 2: Parallel Threads for Multiple Engagements

Create two threads to simulate two parallel audit engagements:

```python
thread_a = client.threads.create()  # TechVentures engagement
thread_b = client.threads.create()  # Apex Financial engagement

chat(client, agent.id, thread_a.id, "Client is TechVentures Inc., SaaS, $200M revenue.")
chat(client, agent.id, thread_b.id, "Client is Apex Financial Group, banking, $5B assets.")

# Each thread has its own context — they don't overlap
chat(client, agent.id, thread_a.id, "What industry is our client in?")  # → SaaS
chat(client, agent.id, thread_b.id, "What industry is our client in?")  # → Banking
```

### Exercise 3: Thread History Inspection

After the conversation, inspect the full thread history:

```python
messages = client.messages.list(thread_id=thread.id)
for msg in reversed(list(messages)):
    print(f"[{msg.role}] {msg.content[0].text.value}")
```

This shows every user and assistant message — the full context the agent used.

## Key Takeaways

- **Threads are short-term memory** — all messages in a thread are available as context to the agent, just like Copilot Studio's automatic conversation context
- **Thread isolation** — each thread is independent; context doesn't leak between threads
- **No explicit variable management** — unlike Copilot Studio's global variables, the agent infers context from the full conversation history
- **Threads persist** — unlike Copilot Studio sessions, threads remain until explicitly deleted, meaning you could resume a conversation later
- **Token limits apply** — very long threads may exceed the model's context window; for production, consider summarization strategies

## Comparing Memory Levels

| Level | Copilot Studio | Foundry | Scope |
|-------|---------------|---------|-------|
| **Conversation context** | Automatic | Threads | Current session |
| **Structured state** | Global variables | Your app layer | Current session |
| **Long-term memory** | Dataverse | Memory Service (preview) | Across sessions |

The next exercise explores long-term memory using the Foundry Agent Memory Service — the equivalent of using Dataverse in Copilot Studio to persist information across sessions.

## Next Steps

→ [`06_memory.md`](./06_memory.md) / [`06_memory.py`](./06_memory.py) — Long-term memory with the Foundry Agent Memory Service

# Exercise 0: Creating a Foundry Agent in the Portal

Before diving into the SDK, let's create the **same agent from `01_first_agent.py`** using the **Azure AI Foundry portal** — no code required. This gives you a mental model of what the SDK automates.

## What You'll Build

An **Assurance Assistant** agent with:
- A system prompt scoped to professional services / audit
- A single-turn conversation asking about audit phases
- The same model deployment you'll use in the code examples

This mirrors exactly what `01_first_agent.py` and `02_system_prompts.py` do in code.

## Steps

### 1. Open Azure AI Foundry

1. Navigate to [ai.azure.com](https://ai.azure.com) and sign in.
2. Select your **project** (the one matching your `PROJECT_ENDPOINT` in `.env`).
3. In the left sidebar, select **Agents** under the Build section.

### 2. Create a New Agent

1. Select **+ New agent**.
2. Configure the agent:

   | Field | Value |
   |-------|-------|
   | **Name** | `AssuranceAssistant` |
   | **Model** | Select your deployed model (e.g., `gpt-4o`) — this should match `MODEL_DEPLOYMENT_NAME` in your `.env` |

3. In the **Instructions** field, enter the following system prompt:

   ```
   You are a helpful assistant for an assurance practice at a professional
   services firm.
   ```

   > This is the exact same prompt used in `01_first_agent.py`.

4. Select **Save**.

### 3. Test the Agent

1. In the agent's chat panel on the right, type:

   ```
   What are the key phases of a financial statement audit?
   ```

2. Review the response. It should describe the standard audit phases (planning, risk assessment, fieldwork, reporting, etc.) in a professional tone.

3. This is the same question sent in `01_first_agent.py` — compare the response style.

### 4. Upgrade the Instructions

Now replicate what `02_system_prompts.py` does — a more detailed, guarded system prompt.

1. Select **Edit** on the agent (or create a new agent named `AuditAssistant-Detailed`).
2. Replace the instructions with:

   ```
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
   ```

3. Select **Save**.

### 5. Compare Behavior

Ask the same question with both instruction sets and compare:

```
How should we assess the risk of material misstatement for a new audit client?
```

| | Basic Instructions | Detailed Instructions |
|---|---|---|
| **Tone** | Helpful, general | Professional, precise |
| **Standards cited** | May or may not reference standards | Should cite PCAOB AS / AU-C sections |
| **Guardrails** | No constraints | Caveats about professional judgment |

### 6. Explore the Portal UI

While you're in the portal, note the features that map to SDK concepts:

| Portal UI | SDK Equivalent | Code Example |
|-----------|---------------|--------------|
| Agent name + instructions | `client.agents.create_agent(name=, instructions=)` | `01_first_agent.py` |
| Chat panel (send a message) | `client.agents.create_thread()` + `client.agents.create_message()` | `01_first_agent.py` |
| Run the conversation | `client.agents.create_run()` | `01_first_agent.py` |
| Add a file / knowledge source | `client.agents.upload_file()` + `FileSearchTool` | `03_knowledge.py` |
| Add a function tool | `FunctionTool` definition | `04_function_calling.py` |
| Conversation history | Thread with multiple messages | `05_conversation_state.py` |

## Key Takeaways

- The portal provides a **visual interface** for the same operations the SDK performs in code
- Every portal action has a **direct SDK equivalent** — the code examples that follow automate exactly what you just did manually
- The portal is great for **prototyping and testing** — the SDK is for **production, automation, and version control**
- **Instructions are the most important configuration** — they define the agent's behavior, tone, and constraints

## Next Steps

Now that you've seen how it works in the portal, let's do it in code:

→ [01_first_agent.py](./01_first_agent.py) — The same agent, built with the SDK

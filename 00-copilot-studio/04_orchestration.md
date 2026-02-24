# Exercise 4: Understanding Orchestration

In this exercise, you'll explore how Copilot Studio's **orchestration modes** determine how your agent selects topics, tools, and knowledge sources to respond to user queries.

## What You'll Learn

- The difference between **generative** and **classic** orchestration
- How generative orchestration dynamically selects tools, topics, and knowledge
- How classic orchestration uses trigger phrases to match topics
- When to use each mode and how to switch between them

## Background

Orchestration is *how the agent decides what to do* when it receives a user message. Copilot Studio offers two modes:

| | Generative Orchestration | Classic Orchestration |
|---|---|---|
| **How topics are selected** | AI selects based on topic name + description | Trigger phrases matched against user message |
| **How tools are invoked** | AI automatically calls tools when relevant | Tools must be called explicitly from a topic |
| **Knowledge search** | AI proactively searches when helpful | Knowledge is a fallback when no topic matches |
| **Multi-intent** | Can handle multiple intents in one message | Selects a single best-matching topic |
| **User input collection** | AI generates questions for missing inputs | You author question nodes manually |

> 📖 **Reference:** [Generative orchestration](https://learn.microsoft.com/en-us/microsoft-copilot-studio/advanced-generative-actions)

## Steps

### 1. Verify Your Current Orchestration Mode

New agents default to **generative orchestration**. Verify this:

1. Go to your **Audit Research Assistant** agent.
2. Navigate to **Settings** (gear icon) → **Generative AI**.
3. Confirm that **Generative orchestration** is enabled.

### 2. Observe Generative Orchestration in Action

With generative orchestration enabled, the agent dynamically decides how to respond. Test this:

1. Open the **Test your agent** panel.
2. Try a multi-intent prompt:

   > I need two things: look up Apple's latest 10-K filing, and also tell me what the current federal funds rate is.

3. Observe how the agent:
   - Identifies **two separate intents** in one message
   - Calls the **SEC EDGAR tool** for the Apple filing
   - Calls the **FRED API tool** for the federal funds rate
   - Combines results into a single response

4. Now try a knowledge-plus-tool query:

   > What does ISA 315 say about understanding the economic environment, and what is the current GDP growth rate?

5. The agent should search **knowledge** (IAASB website) for ISA 315 content and call the **FRED tool** for GDP data.

### 3. Create a Topic for Generative Orchestration

In generative mode, topics are selected based on their **name and description** — not trigger phrases.

1. Navigate to the **Topics** page → select **Add a topic** → **From blank**.
2. Name the topic: `Engagement Risk Summary`
3. On the **Trigger** node (which defaults to "The agent chooses"), add a description:

   > Use this topic when the user asks for a risk summary, risk assessment overview, or engagement risk analysis for a specific company or client.

4. Add a **Message** node with:

   ```
   I'll compile a risk summary for this engagement. Let me gather the relevant data...
   ```

5. Add a **Tool** node — select the EDGAR API tool to call `getCompanyFacts`.
6. Add another **Tool** node — select the FRED API tool to call `getSeriesObservations` for FEDFUNDS.
7. Add a final **Message** node:

   ```
   Based on the data gathered, here are the key risk factors to consider for this engagement. Review the financial data and economic indicators above in the context of your client's industry and circumstances.
   ```

8. **Save** the topic.

9. **Test it:** Ask `Give me a risk summary for Apple` — the agent should select this topic based on the description match.

### 4. Switch to Classic Orchestration

Now switch to classic mode to see the difference:

1. Go to **Settings** → **Generative AI**.
2. Turn **off** generative orchestration (switch to classic mode).
3. Navigate back to **Topics** and open `Engagement Risk Summary`.
4. Notice the trigger changes to **User says a phrase** — you now need explicit trigger phrases.
5. Add trigger phrases:
   - `risk summary`
   - `engagement risk`
   - `risk assessment overview`
   - `assess the risk for`
   - `compile risk factors`

6. **Save** the topic.

### 5. Compare Behavior in Classic Mode

Test the same prompts in classic mode:

| Prompt | Generative Mode | Classic Mode |
|--------|----------------|--------------|
| `Give me a risk summary for Apple` | ✅ Selects topic via description | ✅ Matches "risk summary" trigger |
| `I need to assess the engagement risk` | ✅ Selects topic via description | ✅ Matches "engagement risk" trigger |
| `What are the risk factors I should consider?` | ✅ Matches description intent | ❓ May not match any trigger phrase |
| Multi-intent: `risk summary and current rates` | ✅ Handles both intents | ❌ Selects only one topic |
| `Look up the federal funds rate` | ✅ Calls FRED tool directly | ❌ No topic matches → fallback |

### 6. Switch Back to Generative Mode

1. Go to **Settings** → **Generative AI** → re-enable **Generative orchestration**.
2. Generative mode is recommended for most scenarios as it provides more natural, flexible interactions.

## When to Use Each Mode

| Use Case | Recommended Mode |
|----------|-----------------|
| General-purpose assistant with multiple tools | **Generative** |
| Highly structured, compliance-critical workflows | **Classic** |
| Agents with many knowledge sources | **Generative** |
| Simple FAQ / decision-tree bots | **Classic** |
| Agents that need to handle unexpected questions | **Generative** |
| Agents where you need full control over every response | **Classic** |

## Key Takeaways

- **Generative orchestration** is more flexible — the AI dynamically selects the best combination of topics, tools, and knowledge
- **Classic orchestration** gives you more control — topics fire based on explicit trigger phrase matching
- **Topic descriptions** are critical in generative mode — they replace trigger phrases as the primary selection mechanism
- Generative mode can handle **multi-intent queries** and automatically **generate input prompts**
- You can switch between modes at any time — but topics may need updating (descriptions ↔ trigger phrases)

## Next Steps

→ [Exercise 5: Configuring Memory and Variables](./05_memory.md)

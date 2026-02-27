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
2. Navigate to **Settings** (button at the upper right).
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

6. Now try a two-sources-of-knowledge query:

   > What does ISA 315 say about understanding the economic environment, and how does that interact with EY insights?

7. The agent should search **knowledge** (IAASB website) for ISA 315 content and also search the EY Insights **knowledge**.

### 3a. Create a Topic for Generative Orchestration - Tools

In generative mode, topics are selected based on their **name and description** — not trigger phrases.

1. Navigate to the **Topics** page → select **Add a topic** → **From blank**.
2. Change the topic name from `Untitled` (in the upper left) to: `Engagement Risk Summary`
3. On the **Trigger** node (which defaults to "The agent chooses"), add a description:

   > Use this topic when the user asks for a risk summary, risk assessment overview, or engagement risk analysis for a specific company or client.

4. Add a **Send a message** node with:

   ```
   I'll compile a risk summary for this engagement. Let me gather the relevant data...
   ```

5. Add a **Tool** node — search connectors for "edgar" and select the EDGAR API tool to call `getCompanyFacts`.
6. Add another **Tool** node — search connectors for "edgar" and select the FRED API tool to call `getSeriesObservations` for FEDFUNDS.
7. Add a final **Message** node:

   ```
   Based on the data gathered, here are the key risk factors to consider for this engagement. Review the financial data and economic indicators above in the context of your client's industry and circumstances.
   ```

8. **Save** the topic.

9. **Test it:** Ask `Give me a risk summary for Apple` — the agent should select this topic based on the description match.

### 4a. Switch to Classic Orchestration — Tools

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

### 5a. Compare Behavior in Classic Mode — Tools

Test the same prompts in classic mode:

| Prompt | Generative Mode | Classic Mode |
|--------|----------------|--------------|
| `Give me a risk summary for Apple` | ✅ Selects topic via description | ✅ Matches "risk summary" trigger |
| `I need to assess the engagement risk` | ✅ Selects topic via description | ✅ Matches "engagement risk" trigger |
| `What are the risk factors I should consider?` | ✅ Matches description intent | ❓ May not match any trigger phrase |
| Multi-intent: `risk summary and current rates` | ✅ Handles both intents | ❌ Selects only one topic |
| `Look up the federal funds rate` | ✅ Calls FRED tool directly | ❌ No topic matches → fallback |

After comparing, **switch back to generative orchestration** in Settings → Generative AI before continuing.

---

### 3b. Create a Topic for Generative Orchestration — Knowledge Only

> **Use this path if you didn't set up REST API tools in Exercise 3**, or if you want to see how orchestration works with knowledge sources alone.

1. Navigate to the **Topics** page → select **Add a topic** → **From blank**.
2. Name the topic: `Standards Research Summary`
3. On the **Trigger** node (which defaults to "The agent chooses"), add a description:

   > Use this topic when the user asks for a summary of relevant audit standards, a standards research brief, or wants to know which professional standards apply to a particular audit area.

4. Add a **Message** node with:

   ```
   I'll research the relevant professional standards for this topic. Let me check the knowledge sources...
   ```

5. Add a **Generative answers** node and configure it:
   - **Input:** Click the **Input** box and set it to System `Activity.Text` — this passes the user's original message as the search query.
   - **Data sources:** Click **Edit** under Data sources → select the knowledge sources you added in Exercise 2 (IAASB, PCAOB, EY Insights, etc.). You can select specific sources or leave it set to **Search all knowledge** to use everything configured on the agent.
   - **Content moderation:** Leave the default setting (Medium) unless you have a reason to change it.

   > The Generative answers node searches the selected knowledge sources using the input text, retrieves relevant content, and composes a grounded answer with citations.

6. Add a final **Message** node:

   ```
   The above summary is based on publicly available standards content. Always verify against the authoritative full-text standards for your engagement.
   ```

7. **Save** the topic.

8. **Test it:** Ask `Give me a standards research summary for revenue recognition auditing` — the agent should select this topic and ground its response in the IAASB, PCAOB, and other knowledge sources.

### 4b. Switch to Classic Orchestration — Knowledge Only

Now switch to classic mode to see the difference with your knowledge-only topic:

1. Go to **Settings** → **Generative AI**.
2. Turn **off** generative orchestration (switch to classic mode).
3. Navigate back to **Topics** and open `Standards Research Summary`.
4. Notice the trigger changes to **User says a phrase** — you now need explicit trigger phrases.
5. Add trigger phrases:
   - `standards research`
   - `relevant standards`
   - `which standards apply`
   - `audit standards for`
   - `standards summary`

6. **Save** the topic.

### 5b. Compare Behavior in Classic Mode — Knowledge Only

Test the same prompts in classic mode:

| Prompt | Generative Mode | Classic Mode |
|--------|----------------|--------------|
| `Give me a standards research summary` | ✅ Selects topic via description | ✅ Matches "standards research" trigger |
| `Which standards apply to inventory auditing?` | ✅ Selects topic via description | ✅ Matches "which standards apply" trigger |
| `What professional guidance exists for going-concern?` | ✅ Matches description intent | ❓ May not match any trigger phrase |
| `What does ISA 540 say about estimates?` | ✅ Searches knowledge directly | ❌ No topic matches → may fall back to general knowledge |
| Multi-intent: `standards for revenue and for leases` | ✅ Handles both in one response | ❌ Selects only one topic |

> **Notice the key difference:** In generative mode, the agent can decide to search knowledge *without* a topic match. In classic mode, knowledge search only happens as a fallback when no topic triggers — so the agent may give a less grounded answer.

After comparing, **switch back to generative orchestration** in Settings → Generative AI.

---

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

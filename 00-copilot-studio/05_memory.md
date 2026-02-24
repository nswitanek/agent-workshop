# Exercise 5: Configuring Memory and Variables

In this exercise, you'll configure your Audit Research Assistant to **remember context** across conversation turns using variables and topic-scoped state.

## What You'll Learn

- How Copilot Studio manages conversation memory
- How to create and use **topic variables** and **global variables**
- How to persist information across topics using global variables
- How conversation context influences agent behavior

> 📖 **Reference:** [Work with variables](https://learn.microsoft.com/en-us/microsoft-copilot-studio/authoring-variables)

## Background

Copilot Studio provides several levels of memory:

| Level | Scope | Lifetime | Use Case |
|-------|-------|----------|----------|
| **Conversation context** | Automatic | Current conversation | LLM uses prior messages to inform responses |
| **Topic variables** | Single topic | While topic is active | Capture and use information within a topic flow |
| **Global variables** | All topics | Entire conversation | Share data across topics (e.g., client name) |
| **Dataverse** | Persistent | Across conversations | Long-term user preferences and history |

## Steps

### 1. Observe Built-in Conversation Context

Copilot Studio's generative orchestration automatically uses **conversation history** as context. Test this:

1. Open the **Test your agent** panel and start a new session.
2. Ask: `I'm working on an audit for JPMorgan Chase.`
3. Then ask: `What are their recent SEC filings?`
4. The agent should understand that "their" refers to **JPMorgan Chase** from the prior message — it uses conversation history for context.
5. Follow up: `What industry are they in?`
6. Again, the agent maintains context from the conversation.

### 2. Create a Topic with Variables

Build a topic that captures structured engagement information using variables.

1. Navigate to **Topics** → **Add a topic** → **From blank**.
2. Name the topic: `Set Up Engagement`
3. Configure the trigger description (generative orchestration):

   > Use this topic when the user wants to set up a new engagement, start a new audit, or configure engagement details like client name, industry, and fiscal year.

4. Add a **Question** node:
   - Question text: `What is the client name for this engagement?`
   - **Identify as:** User's entire response
   - **Save response as:** Create a new variable named `ClientName`

5. Add another **Question** node:
   - Question text: `What industry is the client in?`
   - **Identify as:** User's entire response
   - **Save response as:** Create a variable named `ClientIndustry`

6. Add another **Question** node:
   - Question text: `What is the fiscal year-end date? (e.g., December 31, 2025)`
   - **Identify as:** Date and time
   - **Save response as:** Create a variable named `FiscalYearEnd`

7. Add a **Message** node:
   ```
   ✅ Engagement set up:
   - **Client:** {ClientName}
   - **Industry:** {ClientIndustry}
   - **Fiscal Year-End:** {FiscalYearEnd}

   I'll use this context to tailor my research and recommendations.
   ```
   (Insert the variables using the `{x}` variable picker in the message editor.)

8. **Save** the topic.

### 3. Make Variables Global

To use engagement information across *all* topics, make the key variables global:

1. Open the `Set Up Engagement` topic.
2. Click on the `ClientName` variable in the variable panel.
3. In the variable properties, toggle **Global (across all topics)** to **On**.
4. Repeat for `ClientIndustry` and `FiscalYearEnd`.
5. **Save** the topic.

> Global variables are prefixed with `Global.` — e.g., `Global.ClientName`.

### 4. Use Global Variables in Another Topic

Create a topic that uses the engagement context set by the previous topic.

1. Create a new topic: `Engagement Context Check`
2. Set the trigger description:

   > Use this topic when the user asks about the current engagement, current client, or what engagement is active.

3. Add a **Condition** node:
   - Check if `Global.ClientName` **is not blank**.

4. In the **True** branch, add a **Message** node:
   ```
   📋 Current Engagement:
   - **Client:** {Global.ClientName}
   - **Industry:** {Global.ClientIndustry}
   - **Fiscal Year-End:** {Global.FiscalYearEnd}
   ```

5. In the **False** branch (All other conditions), add a **Message** node:
   ```
   No engagement is currently set up. Would you like to set one up now?
   ```
   Then add a **Redirect** node pointing to the `Set Up Engagement` topic.

6. **Save** the topic.

### 5. Test the Memory Flow

1. Start a **new test session**.
2. Ask: `Set up a new engagement`
3. Provide the details when prompted:
   - Client: `Apex Financial Group`
   - Industry: `Financial Services`
   - Fiscal year-end: `December 31, 2025`
4. Verify the confirmation message shows the correct details.
5. Now ask: `What engagement am I working on?` — the Engagement Context Check topic should fire and display the stored information.
6. Ask: `Look up SEC filings for my current client` — with generative orchestration, the agent may use the `Global.ClientName` context to search EDGAR.

### 6. Explore Variable Scope

Experiment with variable behavior:

| Test | Expected Result |
|------|----------------|
| Start a new conversation → ask `What engagement am I working on?` | Should say "No engagement set up" (global vars reset per conversation) |
| Set up an engagement → navigate through multiple topics → check context | Global variables persist across topics within the same conversation |
| Set `ClientName` to a new value mid-conversation | Previous value is overwritten |

## Key Takeaways

- **Conversation context** (LLM memory of prior turns) works automatically — no configuration needed
- **Topic variables** are scoped to a single topic execution and are discarded when the topic ends
- **Global variables** persist across topics within a conversation — use them for shared state like client name
- Variables **reset when a new conversation starts** — for persistent state across sessions, use Dataverse
- Good variable naming (e.g., `ClientName`, not `var1`) helps both you and the AI orchestrator

## Next Steps

→ [Exercise 6: Configuring Triggers](./06_triggers.md)

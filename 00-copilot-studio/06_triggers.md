# Exercise 6: Configuring Triggers

In this exercise, you'll configure different **trigger types** to control when your agent's topics activate — including generative triggers, phrase-based triggers, event triggers, and inactivity prompts.

## What You'll Learn

- How to configure different trigger types in Copilot Studio
- The difference between "The agent chooses" and "User says a phrase" triggers
- How to set up event-based triggers (conversation start, inactivity)
- How to use trigger conditions and priorities

> 📖 **Reference:** [Triggers](https://learn.microsoft.com/en-us/microsoft-copilot-studio/authoring-triggers)

## Background

Triggers determine **when a topic activates**. Different trigger types suit different scenarios:

| Trigger Type | When It Fires | Best For |
|-------------|---------------|----------|
| **The agent chooses** | AI matches user intent to topic description | Flexible, natural conversations |
| **User says a phrase** | User message matches trigger phrases | Predictable, controlled flows |
| **A message is received** | Any message activity arrives | Catch-all processing |
| **A custom client event occurs** | An event activity is received | External system integration |
| **The conversation changes** | Conversation update (e.g., user joins) | Welcome messages in Teams |
| **The user is inactive for a while** | No user input for a configured period | Follow-up prompts, session cleanup |
| **A plan completes** | Agent finishes all planned steps | Post-processing, summaries |

## Steps

### 1. Review Your Existing Triggers

1. Navigate to the **Topics** page for your agent.
2. Open each topic you've created and note the trigger type:
   - `Engagement Risk Summary` — should use "The agent chooses"
   - `Set Up Engagement` — should use "The agent chooses"
   - `Engagement Context Check` — should use "The agent chooses"
3. Open the **Conversation Start** system topic — this uses an event trigger.

### 2. Create a Topic with "User says a phrase" Trigger

For compliance-critical workflows, you may want deterministic trigger matching.

1. Create a new topic: `Independence Confirmation`
2. Hover over the **Trigger** node → select the **Change trigger** icon.
3. Select **User says a phrase**.
4. Add these trigger phrases:
   - `independence check`
   - `confirm independence`
   - `independence declaration`
   - `are we independent`
   - `check for conflicts`

5. Add a **Message** node:
   ```
   ⚠️ **Independence Confirmation Required**

   Before proceeding with any engagement, confirm the following:
   ```

6. Add a **Question** node:
   - Question: `Has the engagement team completed the independence assessment in the firm's system?`
   - **Identify as:** Boolean (Yes/No)
   - Save as: `IndependenceConfirmed`

7. Add a **Condition** node on `IndependenceConfirmed`:

   **If Yes:**
   ```
   ✅ Independence confirmed. You may proceed with engagement activities.
   ```

   **If No:**
   ```
   🚫 Independence has NOT been confirmed. Please complete the independence assessment before proceeding. Contact your engagement quality reviewer if you have questions.
   ```

8. **Save** the topic.

### 3. Test Trigger Phrase Matching

1. Open the test panel and start a new session.
2. Try these prompts:

   | Prompt | Should Match? |
   |--------|--------------|
   | `independence check` | ✅ Yes — exact trigger phrase |
   | `confirm independence` | ✅ Yes — exact trigger phrase |
   | `I need to verify our independence` | ⚠️ Maybe — depends on phrase similarity matching |
   | `What are the independence rules?` | ❌ Probably not — different intent |

3. Compare with a generative trigger topic — try `Give me a risk summary` and observe how the "agent chooses" trigger is more flexible.

### 4. Configure an Inactivity Trigger

Create a follow-up prompt when the user goes silent.

1. Create a new topic: `Inactivity Follow-Up`
2. Change the trigger to **The user is inactive for a while**.
3. In the trigger properties panel, set **Inactivity duration** to **2 minutes** (for testing; use longer in production).
4. Add a **Message** node:

   ```
   Still there? Here are some things I can help with:

   📋 `Set up a new engagement` — Configure client details
   🔍 `Look up SEC filings` — Search EDGAR for company data
   📈 `Get economic indicators` — Retrieve rates, GDP, inflation
   ✅ `Independence check` — Confirm engagement independence

   Just ask, or type "help" for more options.
   ```

5. **Save** the topic.
6. **Test:** Open the test panel, start a conversation, and wait 2 minutes. The follow-up message should appear.

### 5. Customize the Conversation Start Trigger

The **Conversation Start** system topic fires when a user first opens a conversation.

1. Navigate to **Topics** → **System** → open **Conversation Start**.
2. This topic uses the **The conversation changes** trigger type.
3. You already customized the introduction message in Exercise 1. Now add context:

   After the greeting message, add a **Condition** node:
   - Check if `Global.ClientName` **is not blank**

   **If True**, add a message:
   ```
   📋 I see you have an active engagement for **{Global.ClientName}**. Would you like to continue working on it?
   ```

   **If False**, keep the standard greeting.

4. **Save** the topic.

> **Note:** Global variables reset between conversations, so this condition will only apply if the conversation start topic redirects from another topic within the same session.

### 6. Create a Topic with the "A plan completes" Trigger

This trigger fires after the agent finishes executing all planned steps in generative orchestration.

1. Create a new topic: `Post-Research Summary`
2. Change the trigger to **A plan completes**.
3. Add a **Message** node:

   ```
   ---
   💡 **Next Steps:** Would you like me to:
   - Research additional topics?
   - Set up a new engagement?
   - Export this information?

   Just let me know how I can help further.
   ```

4. **Save** the topic.
5. **Test:** Ask a complex query (e.g., `Look up Apple's filings and the current GDP`). After the agent completes its plan, the post-research summary should appear.

### 7. Explore Trigger Conditions and Priority

Triggers can have **conditions** (when to fire) and **priorities** (which fires first when multiple match).

1. Open the `Independence Confirmation` topic.
2. Select **Edit** on the trigger node to open the properties panel.
3. Add a **Condition:**
   - Variable: `Global.ClientName`
   - Operator: `is not blank`
   - This means the independence check topic only fires if an engagement has been set up.

4. Explore **Priority**: When multiple topics could match, priority determines which one the agent selects first. Higher priority topics are evaluated before lower priority ones.

## Trigger Selection Summary

```
User sends message
    │
    ├─ Generative orchestration ON?
    │   ├─ YES → AI evaluates all "The agent chooses" topics
    │   │        based on name + description + context
    │   │        → Can select multiple topics + tools + knowledge
    │   │
    │   └─ NO  → Match against "User says a phrase" triggers
    │            → Best matching topic wins
    │
    ├─ Event triggers fire independently:
    │   ├─ "The conversation changes" → welcome messages
    │   ├─ "The user is inactive" → follow-up prompts
    │   └─ "A plan completes" → post-processing
    │
    └─ "It's redirected to" → explicit topic-to-topic calls
```

## Key Takeaways

- **"The agent chooses"** triggers are most flexible — use them with generative orchestration for natural conversations
- **"User says a phrase"** triggers give deterministic control — use them for compliance-critical or structured workflows
- **Inactivity triggers** help re-engage users who may be stuck or distracted
- **"A plan completes"** triggers are useful for adding follow-up actions after the agent finishes its work
- **Trigger conditions** add guardrails — topics only fire when prerequisites are met
- You can **mix trigger types** — some topics can use generative triggers while others use phrase-based triggers

## What You've Built

Congratulations! Over these six exercises, you've built an **Audit Research Assistant** with:

- ✅ **Instructions** — Professional persona and guardrails
- ✅ **Knowledge** — Grounded in IAASB, PCAOB, IFAC, and EY content
- ✅ **Tools** — Connected to SEC EDGAR and FRED APIs
- ✅ **Orchestration** — Generative mode for flexible, multi-intent handling
- ✅ **Memory** — Engagement context persisted across topics
- ✅ **Triggers** — Multiple trigger types for different scenarios

## Next Steps

Continue to the code-first sessions:
- → [Building Agents in Microsoft Foundry](../01-foundry-agents/README.md)
- → [Code-First Agents with Microsoft Agent Framework](../02-maf-agents/README.md)

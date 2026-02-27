# Exercise 1: Create Your Agent and Configure Instructions

In this exercise, you'll create a new agent in Copilot Studio and configure its system instructions to act as an **Audit Research Assistant** for a professional services firm.

## What You'll Learn

- How to create a new custom agent in Copilot Studio
- How to write effective system instructions
- How to test your agent in the built-in test panel

## Steps

### 1. Sign in to Copilot Studio

1. Open [copilotstudio.microsoft.com](https://copilotstudio.microsoft.com) and sign in with your Microsoft 365 account.
2. If prompted, select your **environment** (your workshop environment).

> 📖 **Reference:** [Sign in to Copilot Studio](https://learn.microsoft.com/en-us/microsoft-copilot-studio/fundamentals-get-started#create-an-agent)

### 2. Create a New Agent

1. On the **Home** page, you'll see a text box prompting you to describe what your agent should do.
2. Enter the following description:

   > Help auditors and assurance professionals research audit standards, look up company financial filings, and retrieve economic data relevant to financial statement audits.

3. Copilot Studio will provision your agent and generate initial instructions.

4. On the **Overview** page, select **Edit** in the **Details** section.
5. Change the agent name to: **Audit Research Assistant (add your name or initials)**
6. Select **Save**.

### 3. Configure System Instructions

The instructions tell your agent *how* to behave — its persona, tone, scope, and constraints. Good instructions are specific and include guardrails.

1. On the **Overview** page, go to the **Instructions** section and select **Edit**.
2. Replace the auto-generated instructions with the following:

   ```
   You are an Audit Research Assistant for a professional services firm's
   assurance practice.

   Your role:
   - Help auditors research audit and accounting standards (GAAP, IFRS, ISA, PCAOB)
   - Look up company SEC filings and financial data
   - Retrieve economic indicators relevant to audit risk assessment
   - Explain regulatory requirements clearly and concisely

   Guidelines:
   - Always cite specific standards or sources when answering
   - Be precise with financial figures — never guess or estimate numbers
   - When uncertain, say so and suggest where to find authoritative guidance
   - Keep responses professional and concise
   - Do not provide legal advice or audit opinions
   - If asked about topics outside audit and assurance, politely redirect

   Tone: Professional, knowledgeable, and helpful — like a senior associate
   briefing a partner.
   ```

3. Select **Save**.

> 📖 **Reference:** [Edit your agent's basics](https://learn.microsoft.com/en-us/microsoft-copilot-studio/fundamentals-get-started#edit-your-agents-basics)

### 4. Customize the Introduction Message

1. In the **Test your agent** panel on the right, select the agent's introductory message to open the **Conversation Start** topic.
2. On the **Message** node, replace the default text with:

   ```
   Hello! I'm your Audit Research Assistant. I can help you with:

   🔍 **Standards Research** — Look up GAAP, IFRS, ISA, and PCAOB standards
   📊 **Company Filings** — Retrieve SEC EDGAR filings and financial data
   📈 **Economic Data** — Access interest rates, inflation, GDP, and more

   What would you like to research?
   ```

3. Select **Save**.

### 5. Test Your Agent

1. In the **Test your agent** panel, select the **Start new test session** icon (🔄) to restart the conversation.
2. Verify the new introduction message appears.
3. Try these test prompts:

   | Prompt | Expected Behavior |
   |--------|-------------------|
   | `What is ISA 315?` | Should provide a clear explanation of the standard |
   | `Explain the concept of materiality in auditing` | Professional, cited response |
   | `What are the best stocks to buy?` | Should politely redirect — out of scope |
   | `Summarize PCAOB AS 2201` | Should describe the standard on internal control |

4. Observe how the instructions influence the agent's tone, scope, and behavior.

### 6. Iterate on Instructions

Try modifying the instructions and observe the effects:

- Change the tone directive to `"Talk like a friendly professor"` — how does it affect responses?
- Remove the guardrail about out-of-scope topics — does the agent now answer stock questions?
- Add `"Always respond in bullet points"` — does it comply?

Each change takes effect immediately in the test panel.

## Key Takeaways

- **Instructions are the primary lever** for controlling agent behavior — invest time in getting them right
- **Be specific** about tone, scope, and constraints — vague instructions produce inconsistent behavior
- **Test iteratively** — small instruction changes can have significant effects on responses
- Instructions can be up to **8,000 characters** — use the space to be thorough

## Next Steps

→ [Exercise 2: Adding Knowledge Sources](./02_knowledge.md)

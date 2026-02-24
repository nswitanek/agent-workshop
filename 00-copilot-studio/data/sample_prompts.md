# Sample Test Prompts

Use these prompts to test your Audit Research Assistant at each stage of the exercises.

---

## Exercise 1: Instructions

Test that the agent responds with the correct tone, scope, and constraints.

### In-Scope Prompts (should get helpful responses)
- `What is ISA 315?`
- `Explain the concept of materiality in auditing.`
- `What are the three lines of defense in risk management?`
- `Summarize the key requirements of PCAOB AS 2201 on internal control.`
- `What is the difference between inherent risk and control risk?`
- `How does an auditor assess going-concern risk?`

### Out-of-Scope Prompts (should redirect politely)
- `What are the best stocks to buy right now?`
- `Write me a poem about accounting.`
- `Can you help me with my tax return?`
- `What's the weather like today?`

---

## Exercise 2: Knowledge

Test that the agent grounds responses in the added knowledge sources.

### Standards Research
- `What does ISA 315 Revised say about understanding the entity and its environment?`
- `What are PCAOB requirements for auditing accounting estimates?`
- `What guidance does IFAC provide on professional skepticism?`
- `Summarize ISA 540 Revised on auditing accounting estimates.`
- `What does PCAOB AS 2401 say about fraud risk factors?`

### Industry Insights
- `What are the latest trends in audit quality?`
- `What does EY say about the future of assurance?`
- `What are emerging risks in financial services audits?`

---

## Exercise 3: Tools

Test the SEC EDGAR and FRED API integrations.

### SEC EDGAR Prompts
- `Look up Apple's recent SEC filings.` (CIK: 0000320193)
- `What is Microsoft's total revenue from their latest annual report?` (CIK: 0000789019)
- `Show me Amazon's net income trend over the last 5 years.` (CIK: 0001018724)
- `Get JPMorgan Chase's filing history.` (CIK: 0000019617)
- `What are the total assets reported by Goldman Sachs?` (CIK: 0000886982)

### FRED API Prompts
- `What is the current federal funds rate?` (Series: FEDFUNDS)
- `Show me GDP growth over the last 5 years.` (Series: GDP)
- `What is the current unemployment rate?` (Series: UNRATE)
- `What is the 10-year Treasury rate?` (Series: DGS10)
- `Search for inflation-related economic indicators.`
- `What is the current 30-year mortgage rate?` (Series: MORTGAGE30US)

### Combined Prompts
- `I'm assessing going-concern risk for a retail company. What's the current economic outlook?`
- `Pull Apple's revenue data and compare it against GDP growth.`
- `For an audit of a bank, what interest rate environment should I consider?`

---

## Exercise 4: Orchestration

Test generative vs. classic orchestration behavior.

### Multi-Intent (Generative Mode)
- `Look up Apple's latest 10-K filing, and also tell me what the current federal funds rate is.`
- `Give me a risk summary for Microsoft and search for any PCAOB guidance on technology company audits.`
- `Set up a new engagement and then look up the client's SEC filings.`

### Topic Selection (Generative Mode)
- `Give me a risk summary for Apple.`
- `I need to assess the engagement risk.`
- `What are the risk factors I should consider for a financial services audit?`

### Comparison Prompts (try in both modes)
- `risk summary` (exact trigger phrase — works in both modes)
- `Can you compile an overview of the key risks?` (natural language — better in generative mode)

---

## Exercise 5: Memory

Test variable persistence and conversation context.

### Engagement Setup Flow
1. `Set up a new engagement`
2. When prompted: Client = `Apex Financial Group`, Industry = `Financial Services`, Year-end = `December 31, 2025`
3. `What engagement am I working on?`
4. `Look up SEC filings for my current client.`

### Context Persistence
1. `I'm working on an audit for JPMorgan Chase.`
2. `What are their recent SEC filings?`
3. `What industry are they in?`
4. `What economic indicators are relevant for their sector?`

---

## Exercise 6: Triggers

Test different trigger types.

### Phrase-Based Trigger
- `independence check`
- `confirm independence`
- `are we independent`
- `I need to verify our independence`

### Inactivity Trigger
1. Start a conversation and send any message.
2. Wait 2 minutes without typing.
3. The follow-up prompt should appear.

### Plan Completion Trigger
- `Look up Apple's filings and the current GDP.`
- After the agent completes its response, the post-research summary should appear.

### Trigger with Conditions
1. Try `independence check` without setting up an engagement first (if condition was added).
2. Set up an engagement, then try `independence check` again.

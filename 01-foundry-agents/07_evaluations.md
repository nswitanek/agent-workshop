# Exercise 7: Evaluating Foundry Agents

In this exercise you'll evaluate your Audit Research Agent using Azure AI
Foundry's evaluation framework — measuring quality, safety, and agentic
behaviour across a synthetic dataset of assurance scenarios. More importantly,
you'll see how **adding tools**, **adding memory**, and **optimizing prompts**
measurably improve evaluation scores.

## What You'll Learn

- How to run **batch evaluations** with `azure-ai-evaluation` evaluators
- Which **quality evaluators** (coherence, relevance, groundedness, fluency) map to agent quality
- Which **agentic evaluators** (intent resolution, task adherence) measure agent capability
- How to run **safety evaluators** (content safety) for responsible AI
- How to **log results to the Foundry portal** for visual comparison
- How iterative changes (tools → enhanced prompt → memory) show up in the eval dashboard

> **Reference:** [Azure AI Evaluation overview](https://learn.microsoft.com/en-us/azure/ai-foundry/evaluation/) · [Evaluator library](https://learn.microsoft.com/en-us/azure/ai-foundry/evaluation/concepts/evaluators)

## Background

### Why Evaluate Agents?

Manual "try a few questions" testing doesn't scale and doesn't catch regressions.
Evaluation lets you:

- **Quantify** agent quality with repeatable scores
- **Compare** configurations side-by-side (baseline vs. tools vs. optimised prompt)
- **Catch regressions** when you change instructions or add tools
- **Demonstrate** improvement to stakeholders with concrete metrics

### Evaluator Categories

| Category | Evaluators | What It Measures | Needs Model? |
|----------|-----------|------------------|-------------|
| **Quality** | Coherence, Relevance, Fluency, Groundedness | Response quality (1-5 Likert scale) | Yes (LLM-as-judge) |
| **Agentic** | Intent Resolution, Task Adherence, Tool Call Accuracy | Agent behaviour and instruction-following | Yes |
| **Safety** | Content Safety (violence, sexual, self-harm, hate) | Responsible AI compliance | Backend service |
| **NLP** | F1, BLEU, ROUGE, METEOR | Text overlap with ground truth | No |

### Evaluators Used in This Exercise

| Evaluator | Why It Matters for Audit Agents |
|-----------|-------------------------------|
| **Coherence** | Audit memos must be logically structured |
| **Relevance** | Responses must address the specific audit question asked |
| **Fluency** | Professional writing quality expected in client deliverables |
| **Groundedness** | Claims must be grounded in retrieved data / tool outputs (not hallucinated) |
| **Intent Resolution** | Agent must correctly understand what the auditor needs |
| **Task Adherence** | Agent must follow its instructions (cite standards, structure responses, etc.) |
| **Content Safety** | Agent must not produce harmful content |

### The Evaluation Dataset

The file [data/eval_dataset.jsonl](./data/eval_dataset.jsonl) contains 10
assurance-themed queries with expert ground-truth answers:

| # | Query Theme | Tests |
|---|-------------|-------|
| 1 | Going-concern risk for SaaS company | SEC filing knowledge + economic indicators |
| 2 | Audit risks for financial services + cloud migration | Multi-domain risk assessment |
| 3 | ASC 606 revenue recognition testing | Technical standards knowledge |
| 4 | Federal funds rate impact on bank audits | Real data retrieval (FRED) |
| 5 | CECL allowance evaluation (ASC 326) | Complex methodology understanding |
| 6 | Tesla CIK lookup and 10-K filing | Direct EDGAR tool usage |
| 7 | Economic data for going-concern in rising rates | FRED data retrieval |
| 8 | Apex Financial Group derivative findings | Client-specific analysis |
| 9 | SOX 404 controls for cloud ERP migration | IT audit knowledge |
| 10 | Litigation contingency assessment (ASC 450) | Judgment and materiality |

Queries 4, 6, and 7 particularly benefit from **tool access** (they ask for
real data). Queries 1, 2, 5, 8, and 9 benefit from **better instructions**
(they need structured, standards-aware responses). Query 8 benefits from
**memory** (it references a specific client the agent may have seen before).

## Prerequisites

- A Foundry project with `PROJECT_ENDPOINT` and `MODEL_DEPLOYMENT_NAME` set
- `azure-ai-evaluation` installed: `pip install azure-ai-evaluation`
- For tool-enhanced runs: FRED connection set up (see Exercise 4a)
- Enough model quota for ~60-70 LLM calls per evaluation run
  (10 queries × 6 evaluators + the agent's own calls)
- Set `PARTICIPANT_INITIALS` in your `.env` file (e.g., `PARTICIPANT_INITIALS=NS`)
  so your agents, evaluation runs, and output files are uniquely namespaced
  within the shared Foundry project

## Code Walkthrough (`07_evaluations.py`)

### Architecture

The script has a CLI-driven workflow. Each mode creates/updates the same
persistent agent and runs the evaluation pipeline.

> **Why CLI-driven?** Because each mode is a standalone command, this
> workflow integrates naturally into CI/CD and DevOps pipelines. You can
> run `python 07_evaluations.py baseline` in a GitHub Actions step,
> compare scores against a threshold, and gate deployments on evaluation
> results — turning agent improvements into a repeatable, automated process.

```
eval_dataset.jsonl  →  Agent (run each query)  →  responses.jsonl  →  evaluate()  →  Foundry portal
```

### Modes

Set your initials first so results are namespaced in the shared project:

```bash
export PARTICIPANT_INITIALS=NS   # or add to .env
```

```bash
python 07_evaluations.py baseline   # Instructions only, no tools
python 07_evaluations.py tools      # Add OpenAPI tools
python 07_evaluations.py enhanced   # Enhanced prompt + tools
python 07_evaluations.py compare    # Side-by-side metrics table
python 07_evaluations.py safety     # Safety evaluators on latest run
```

With initials set, the agent is created as `AuditResearchAgent-Eval-NS`,
evaluation runs appear as `audit-agent-baseline-NS`, and output files are
saved as `eval_baseline_responses-NS.jsonl`, etc.

### Step 1: Create the Persistent Agent

The agent is created once and persisted in Foundry (not deleted at the end).
This lets you also experiment in the portal:

```python
agent = client.create_agent(
    model=os.environ["MODEL_DEPLOYMENT_NAME"],
    name="AuditResearchAgent-Eval",
    instructions=BASELINE_INSTRUCTIONS,
    tools=[],  # No tools in baseline
)
```

### Step 2: Generate Responses

Each query from the dataset is sent to the agent in its own thread.
The response and any tool-call outputs (used as `context` for groundedness)
are captured:

```python
thread = client.threads.create()
client.messages.create(thread_id=thread.id, role="user", content=query)
run = client.runs.create_and_process(thread_id=thread.id, agent_id=agent_id)
```

### Step 3: Run Evaluators

Quality evaluators use LLM-as-judge — a separate model call scores each
response on a 1-5 scale:

```python
evaluators = {
    "coherence": CoherenceEvaluator(model_config=model_config),
    "relevance": RelevanceEvaluator(model_config=model_config),
    "fluency": FluencyEvaluator(model_config=model_config),
    "groundedness": GroundednessEvaluator(model_config=model_config),
    "intent_resolution": IntentResolutionEvaluator(model_config=model_config),
    "task_adherence": TaskAdherenceEvaluator(model_config=model_config),
}

result = evaluate(
    data=str(results_path),
    evaluators=evaluators,
    azure_ai_project=project_endpoint,   # Logs to Foundry portal
    evaluation_name="audit-agent-baseline",
)
```

The `azure_ai_project` parameter is the key — it logs results to the
Foundry portal where you can view them visually.

### Step 4: View Results

The script prints aggregate metrics and a portal URL:

```
Evaluation: audit-agent-baseline
  coherence: 4.200
  fluency: 4.500
  groundedness: 3.100
  intent_resolution: 4.000
  relevance: 4.300
  task_adherence: 3.800

  View in Foundry portal: https://ai.azure.com/...
```

## Running the Exercise

### Run 1: Baseline (Instructions Only)

```bash
cd 01-foundry-agents
python 07_evaluations.py baseline
```

This creates the agent with basic instructions and no tools, runs all 10
queries, evaluates the responses, and logs to Foundry.

**Observe:** The agent can answer knowledge-based questions (ASC 606,
SOX 404) reasonably well, but queries asking for real data (Tesla CIK,
federal funds rate) will get hallucinated or generic answers — expect
low groundedness scores on those.

### Run 2: Add Tools

```bash
python 07_evaluations.py tools
```

The same agent is updated to include SEC EDGAR and FRED OpenAPI tools.

**Observe:** Queries 4, 6, and 7 should improve significantly —
the agent now retrieves real data instead of guessing. Groundedness
scores should increase because tool outputs provide grounding context.

### Run 3: Enhanced Prompt

```bash
python 07_evaluations.py enhanced
```

The agent gets an optimized prompt that explicitly tells it when and how
to use tools, reference standards, and structure responses.

**Observe:** Task adherence and coherence should improve — the agent
follows more specific instructions about formatting, standard references,
and specialist involvement recommendations.

### Run 4: Compare

```bash
python 07_evaluations.py compare
```

Prints a side-by-side table of all evaluation runs:

```
Metric                        audit-agent-baseline  audit-agent-with-tools  audit-agent-enhanced
----------------------------------------------------------------------------------------------
coherence                                    4.200                   4.300                 4.600
fluency                                      4.500                   4.500                 4.700
groundedness                                 3.100                   4.200                 4.400
intent_resolution                            4.000                   4.200                 4.500
relevance                                    4.300                   4.500                 4.700
task_adherence                               3.800                   4.000                 4.500
```

### Run 5 (Optional): Safety

```bash
python 07_evaluations.py safety
```

Runs content safety evaluators on the most recent response set.

## Checking Evaluations in the Foundry Portal

### Navigate to the Evaluation Dashboard

1. Go to [Azure AI Foundry](https://ai.azure.com) and open your project
2. In the left navigation, click **Evaluation**
3. You'll see a list of all evaluation runs, each tagged with the
   `evaluation_name` you provided

### What You'll See

| View | What It Shows |
|------|---------------|
| **Run list** | All evaluation runs with aggregate scores and timestamps |
| **Run details** | Per-row scores for every query, with the evaluator reasoning |
| **Metric charts** | Score distributions and histograms for each evaluator |
| **Compare view** | Select 2+ runs to see side-by-side metric comparison |

### How to Compare Runs

1. In the **Evaluation** section, check the boxes next to your runs:
   - `audit-agent-baseline`
   - `audit-agent-with-tools`
   - `audit-agent-enhanced`
2. Click **Compare**
3. The portal shows bar charts and tables comparing scores across runs
4. Drill into specific rows to see where tools made the biggest difference

### What to Look For

- **Groundedness jump** from baseline → tools: This shows the value of
  grounding responses in real retrieved data vs. relying on knowledge alone
- **Task adherence jump** from tools → enhanced: This shows the value of
  prompt optimization — explicit instructions about formatting and standards
- **Consistent fluency/coherence**: These tend to stay high regardless of
  configuration — the model writes well by default
- **Per-row outliers**: Click into individual rows to find queries where
  the agent still struggles — these are candidates for further improvement

## Exercises

### Exercise 1: Analyse the Baseline

After running `baseline`, open the Foundry portal and examine per-row results:

1. Which queries scored lowest on groundedness? Why?
2. Which queries scored highest on coherence? What makes them different?
3. Are there any queries where the agent hallucinated specific data?

### Exercise 2: Measure Tool Impact

After running `tools`, compare with baseline in the portal:

1. Did Tesla CIK lookup (query 6) groundedness improve?
2. Did FRED economic data queries (4, 7) improve?
3. Did any queries get *worse* with tools? (Tools can add noise if the
   agent tries to use them when knowledge alone would suffice.)

### Exercise 3: Prompt Engineering via Eval

Modify `ENHANCED_INSTRUCTIONS` in the script to try different prompt
strategies. Some ideas to test:

- Add "Always respond with bullet points" → Does fluency change?
- Add "Never reference a standard without its number" → Does task adherence improve?
- Remove the tool usage instructions → Does groundedness drop?

Run `enhanced` after each change and compare in the portal.

### Exercise 4: Add Memory and Re-Evaluate

This exercise combines Exercises 6 and 7 — add long-term memory
to the eval agent:

1. Create a memory store (see Exercise 6)
2. Pre-load it with Apex Financial Group engagement context
3. Modify query 8 in the dataset to assume the agent should remember
   Apex details from a prior session
4. Run evaluation and compare — does contextual recall improve on
   query 8 while other queries stay stable?

### Exercise 5: Use the Portal Prompt Optimizer

Azure AI Foundry includes a **prompt optimizer** feature:

1. In the portal, navigate to your agent (`AuditResearchAgent-Eval`)
2. Open the **Prompt optimizer** (if available in your region)
3. Upload the evaluation dataset
4. Let the optimizer suggest prompt improvements
5. Apply the optimized prompt and re-run evaluation
6. Compare the optimizer's prompt vs. your `ENHANCED_INSTRUCTIONS`

### Exercise 6: Custom Evaluator

Create a custom evaluator for audit-specific quality:

```python
from azure.ai.evaluation import AzureOpenAILabelGrader

audit_standards_eval = AzureOpenAILabelGrader(
    model=os.environ["MODEL_DEPLOYMENT_NAME"],
    input=[
        {"role": "system", "content": (
            "You are an audit quality reviewer. Evaluate whether the "
            "response correctly references applicable accounting or "
            "auditing standards (ASC, PCAOB AS, SOX). "
            "Label as 'pass' if standards are cited correctly, "
            "'fail' if standards are missing or incorrect."
        )},
        {"role": "user", "content": "Query: {{item.query}}\nResponse: {{item.response}}"},
    ],
    passing_labels=["pass"],
    labels=["pass", "fail"],
    name="standards_citation",
)
```

Add this to the evaluators dict and run — which queries pass and which fail?

### Exercise 7: Expand the Dataset

Add 5 more queries to `eval_dataset.jsonl` covering:

- International standards (IFRS vs. US GAAP differences)
- Fraud risk assessment (SAS 99 / PCAOB AS 2401)
- Related-party transactions (ASC 850)
- Subsequent events (ASC 855)
- Engagement quality review procedures

Re-run all three configurations. Do the relative rankings hold?

## Key Takeaways

- **Evaluation makes improvement measurable** — "it feels better" becomes
  "groundedness improved from 3.1 to 4.4 when we added real data tools"
- **Different evaluators catch different problems** — groundedness catches
  hallucination, task adherence catches instruction drift, intent resolution
  catches misunderstanding
- **Tools improve data-dependent queries** — grounding in real API data
  dramatically improves scores on queries that ask for specific facts
- **Prompt optimization improves structure and compliance** — explicit
  instructions about formatting, standards citations, and specialist flags
  show up in coherence and task adherence scores
- **The Foundry portal enables visual comparison** — the eval dashboard
  makes it easy to show stakeholders exactly how each change helped
- **The agent is persistent** — you can find `AuditResearchAgent-Eval`
  in the Foundry portal and continue experimenting without re-running the script
- **Evaluation should be continuous** — set up evaluation runs as part of
  your agent development workflow, not just a one-time check

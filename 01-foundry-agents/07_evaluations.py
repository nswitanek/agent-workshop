"""
07 — Evaluating Foundry Agents

Creates a persistent Audit Research Agent, runs it against a synthetic
evaluation dataset, and scores responses with Foundry evaluators.

The agent is intentionally NOT deleted so participants can iteratively:
  1. Run evals with the baseline agent (instructions only)
  2. Add OpenAPI tools   → re-eval → observe improvement on data-retrieval queries
  3. Add memory          → re-eval → observe improvement on context-dependent queries
  4. Optimize the prompt → re-eval → observe improvement across the board

Each run is logged to the Foundry portal for side-by-side comparison.

Concepts: evaluate(), quality evaluators, safety evaluators, agentic evaluators,
          AIAgentConverter, Foundry eval dashboard, iterative agent improvement

Reference: https://learn.microsoft.com/en-us/azure/ai-foundry/evaluation/
"""

import json
import multiprocessing
import os
import sys
import time
from pathlib import Path

from azure.ai.agents import AgentsClient
from azure.ai.agents.models import (
    OpenApiAnonymousAuthDetails,
    OpenApiConnectionAuthDetails,
    OpenApiConnectionSecurityScheme,
    OpenApiTool,
)
from azure.ai.evaluation import (
    AzureOpenAIModelConfiguration,
    CoherenceEvaluator,
    ContentSafetyEvaluator,
    EvaluatorConfig,
    FluencyEvaluator,
    GroundednessEvaluator,
    IntentResolutionEvaluator,
    RelevanceEvaluator,
    TaskAdherenceEvaluator,
    evaluate,
)
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"
OPENAPI_DIR = SCRIPT_DIR / "openapi"
OUTPUTS_DIR = SCRIPT_DIR / "outputs"

PARTICIPANT_INITIALS = os.environ.get("PARTICIPANT_INITIALS", "")
SUFFIX = f"-{PARTICIPANT_INITIALS}" if PARTICIPANT_INITIALS else ""
AGENT_NAME = f"AuditResearchAgent-Eval{SUFFIX}"

BASELINE_INSTRUCTIONS = """\
You are an Audit Research Assistant at a professional services firm.

Help auditors with:
- SEC filing research and analysis
- Economic data gathering for risk assessment
- Audit planning and risk identification
- Going-concern evaluations
- Internal control assessments
- Accounting standards guidance (ASC 606, ASC 326, ASC 820, ASC 450, etc.)

Be professional, precise, and reference applicable standards when relevant.
Provide structured, actionable responses.
"""

ENHANCED_INSTRUCTIONS = """\
You are a Senior Audit Research Assistant at a Big Four professional services firm
with deep expertise in SEC filings, economic analysis, and audit methodology.

Help auditors with:
- SEC filing research — search EDGAR for CIK numbers, retrieve 10-K/10-Q filings,
  pull XBRL financial data (revenue, assets, liabilities, net income)
- Economic data — retrieve interest rates (FEDFUNDS, DGS10), inflation (CPIAUCSL),
  GDP, unemployment (UNRATE), and mortgage rates (MORTGAGE30US) from FRED
- Audit planning and risk identification per PCAOB standards
- Going-concern evaluations under PCAOB AS 2415
- Internal control assessments under SOX 404
- Accounting standards guidance (ASC 606, ASC 326, ASC 820, ASC 450, ASC 815)

When answering:
1. Structure responses with clear headings and numbered steps
2. Reference specific standards (e.g., "per ASC 606-10-25-1")
3. When data retrieval would help, use your SEC EDGAR and FRED tools
4. Explain audit implications of the data you retrieve
5. Consider materiality thresholds in your analysis
6. Flag areas requiring specialist involvement (IT, valuation, tax, legal)

Be concise but thorough. Prioritize actionable audit procedures.
"""


# ---------------------------------------------------------------------------
# Agent creation / retrieval
# ---------------------------------------------------------------------------

def load_spec(filename: str) -> dict:
    spec_path = OPENAPI_DIR / filename
    with open(spec_path, encoding="utf-8") as f:
        return json.load(f)


def get_openapi_tools() -> list:
    """Build OpenAPI tool definitions for SEC EDGAR and FRED."""
    edgar_data_spec = load_spec("sec-edgar.openapi.json")
    edgar_search_spec = load_spec("sec-edgar-search.openapi.json")
    fred_spec = load_spec("fred-api.openapi.json")

    anon_auth = OpenApiAnonymousAuthDetails()

    edgar_tool = OpenApiTool(
        name="sec_edgar_data",
        description="Access SEC EDGAR for company filing history, financial statements, and XBRL data.",
        spec=edgar_data_spec,
        auth=anon_auth,
    )
    edgar_search_tool = OpenApiTool(
        name="sec_edgar_search",
        description="Search SEC EDGAR by company name or ticker to find CIK numbers.",
        spec=edgar_search_spec,
        auth=anon_auth,
    )

    fred_connection_id = os.environ.get("FRED_CONNECTION_ID", "")
    if fred_connection_id:
        fred_auth = OpenApiConnectionAuthDetails(
            security_scheme=OpenApiConnectionSecurityScheme(
                connection_id=fred_connection_id,
            ),
        )
    else:
        fred_auth = OpenApiAnonymousAuthDetails()

    fred_tool = OpenApiTool(
        name="fred_economic_data",
        description="Access FRED economic data — interest rates, inflation, GDP, unemployment.",
        spec=fred_spec,
        auth=fred_auth,
    )

    return (
        edgar_tool.definitions
        + edgar_search_tool.definitions
        + fred_tool.definitions
    )


def create_or_get_agent(
    client: AgentsClient,
    *,
    instructions: str = BASELINE_INSTRUCTIONS,
    with_tools: bool = False,
) -> str:
    """Create the eval agent or retrieve it if it already exists.
    Returns the agent ID."""
    # Check if agent already exists
    for agent in client.list_agents():
        if agent.name == AGENT_NAME:
            print(f"Found existing agent: {agent.id} ({agent.name})")
            return agent.id

    tools = get_openapi_tools() if with_tools else []

    agent = client.create_agent(
        model=os.environ["MODEL_DEPLOYMENT_NAME"],
        name=AGENT_NAME,
        description="Persistent audit research agent for evaluation experiments",
        instructions=instructions,
        tools=tools,
    )
    print(f"Created agent: {agent.id} ({agent.name})")
    return agent.id


def update_agent(
    client: AgentsClient,
    agent_id: str,
    *,
    instructions: str | None = None,
    with_tools: bool | None = None,
) -> None:
    """Update the existing agent's instructions and/or tools."""
    kwargs: dict = {}
    if instructions is not None:
        kwargs["instructions"] = instructions
    if with_tools is not None:
        kwargs["tools"] = get_openapi_tools() if with_tools else []
    if kwargs:
        client.update_agent(agent_id=agent_id, **kwargs)
        print(f"Updated agent {agent_id}")


# ---------------------------------------------------------------------------
# Run agent against dataset
# ---------------------------------------------------------------------------

def run_agent_on_dataset(
    client: AgentsClient,
    agent_id: str,
    dataset_path: Path,
    output_path: Path,
) -> Path:
    """Run the agent on each query in the dataset, producing a results JSONL
    file with columns: query, response, context, ground_truth."""
    with open(dataset_path, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]

    results = []
    for i, row in enumerate(rows):
        query = row["query"]
        print(f"  [{i + 1}/{len(rows)}] {query[:80]}...")
        t0 = time.time()

        # Retry with exponential backoff for rate-limit errors
        response_text = ""
        context_parts = []
        thread = None
        for attempt in range(5):
            try:
                thread = client.threads.create()
                client.messages.create(thread_id=thread.id, role="user", content=query)
                run = client.runs.create_and_process(
                    thread_id=thread.id,
                    agent_id=agent_id,
                )

                # Collect response
                messages = client.messages.list(thread_id=thread.id)
                for msg in messages:
                    if msg.role == "assistant":
                        for block in msg.content:
                            if hasattr(block, "text"):
                                response_text = block.text.value
                                break

                # Collect tool call info as context
                run_steps = client.run_steps.list(thread_id=thread.id, run_id=run.id)
                for step in run_steps:
                    if step.type == "tool_calls":
                        for tc in step.step_details.tool_calls:
                            tc_dict = tc if isinstance(tc, dict) else tc.as_dict()
                            tc_type = tc_dict.get("type", "")
                            if tc_type == "open_api":
                                api_info = tc_dict.get("open_api", {})
                                output_val = api_info.get("output", "")
                                if output_val:
                                    context_parts.append(output_val[:2000])

                client.threads.delete(thread.id)
                thread = None
                elapsed = time.time() - t0
                print(f"    ✓ {elapsed:.1f}s")
                break  # Success

            except Exception as e:
                if "429" in str(e) or "Too Many Requests" in str(e) or "rate" in str(e).lower():
                    wait = 2 ** attempt * 5
                    print(f"    Rate limited, retrying in {wait}s (attempt {attempt + 1}/5)...")
                    time.sleep(wait)
                else:
                    print(f"    Error: {e}")
                    break
            finally:
                if thread:
                    try:
                        client.threads.delete(thread.id)
                    except Exception:
                        pass
                    thread = None

        results.append({
            "query": query,
            "response": response_text,
            "context": "\n---\n".join(context_parts) if context_parts else "",
            "ground_truth": row.get("ground_truth", ""),
        })

    # Write results JSONL
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    print(f"  Agent responses saved to {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def get_model_config() -> AzureOpenAIModelConfiguration:
    """Build the model config used by LLM-as-judge evaluators.

    Uses EVAL_MODEL_DEPLOYMENT_NAME (default: gpt-4.1) to separate evaluator
    load from agent load. This avoids rate-limit contention when 30+
    participants run evals in parallel.
    """
    endpoint = os.environ["PROJECT_ENDPOINT"]
    parts = endpoint.split("/api/")
    azure_endpoint = parts[0] if len(parts) > 1 else endpoint

    eval_model = os.environ.get("EVAL_MODEL_DEPLOYMENT_NAME", "gpt-4.1")

    return AzureOpenAIModelConfiguration(
        azure_endpoint=azure_endpoint,
        azure_deployment=eval_model,
    )


def run_evaluation(
    results_path: Path,
    evaluation_name: str,
    include_safety: bool = False,
) -> dict:
    """Run quality (and optionally safety) evaluators on agent results."""
    project_endpoint = os.environ["PROJECT_ENDPOINT"]
    credential = DefaultAzureCredential()
    model_config = get_model_config()

    # --- Quality evaluators ---
    evaluators = {
        "coherence": CoherenceEvaluator(model_config=model_config),
        "relevance": RelevanceEvaluator(model_config=model_config),
        "fluency": FluencyEvaluator(model_config=model_config),
        "groundedness": GroundednessEvaluator(model_config=model_config),
        "intent_resolution": IntentResolutionEvaluator(model_config=model_config),
        "task_adherence": TaskAdherenceEvaluator(model_config=model_config),
    }

    evaluator_config = {
        "groundedness": EvaluatorConfig(
            column_mapping={
                "query": "${data.query}",
                "response": "${data.response}",
                "context": "${data.context}",
            }
        ),
    }

    # --- Safety evaluators (optional — requires backend service) ---
    if include_safety:
        evaluators["content_safety"] = ContentSafetyEvaluator(
            azure_ai_project=project_endpoint,
            credential=credential,
        )

    output_path = OUTPUTS_DIR / f"{evaluation_name}_results.json"

    print(f"\nRunning evaluation: {evaluation_name}")
    print(f"  Evaluators: {', '.join(evaluators.keys())}")
    print(f"  Data: {results_path}")

    try:
        result = evaluate(
            data=str(results_path),
            evaluators=evaluators,
            evaluator_config=evaluator_config,
            azure_ai_project=project_endpoint,
            evaluation_name=evaluation_name,
            output_path=str(output_path),
        )
    except Exception as e:
        if "AuthorizationFailure" in str(e) or "not authorized" in str(e):
            print(
                "\n  ⚠️  Portal upload failed (storage network access restricted)."
                "\n  Running evaluation locally without portal upload..."
            )
            result = evaluate(
                data=str(results_path),
                evaluators=evaluators,
                evaluator_config=evaluator_config,
                output_path=str(output_path),
            )
        else:
            raise

    # --- Print summary ---
    print(f"\n{'=' * 60}")
    print(f"Evaluation: {evaluation_name}")
    print(f"{'=' * 60}")

    metrics = result.get("metrics", {})
    for metric_name, value in sorted(metrics.items()):
        if isinstance(value, float):
            print(f"  {metric_name}: {value:.3f}")
        else:
            print(f"  {metric_name}: {value}")

    studio_url = result.get("studio_url", "")
    if studio_url:
        print(f"\n  View in Foundry portal: {studio_url}")

    print(f"  Full results saved to: {output_path}")
    return result


# ---------------------------------------------------------------------------
# Main — Evaluation workflow
# ---------------------------------------------------------------------------

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "baseline"

    client = AgentsClient(
        endpoint=os.environ["PROJECT_ENDPOINT"],
        credential=DefaultAzureCredential(),
    )

    dataset_path = DATA_DIR / "eval_dataset.jsonl"

    if mode == "baseline":
        # --- Run 1: Baseline agent (instructions only, no tools) ---
        print("=" * 60)
        print("BASELINE EVALUATION — Instructions only, no tools")
        print("=" * 60)

        agent_id = create_or_get_agent(
            client, instructions=BASELINE_INSTRUCTIONS, with_tools=False
        )

        results_path = OUTPUTS_DIR / f"eval_baseline_responses{SUFFIX}.jsonl"
        print("\nGenerating agent responses...")
        run_agent_on_dataset(client, agent_id, dataset_path, results_path)

        run_evaluation(results_path, f"audit-agent-baseline{SUFFIX}")

    elif mode == "tools":
        # --- Run 2: Agent with OpenAPI tools ---
        print("=" * 60)
        print("TOOLS EVALUATION — Agent with SEC EDGAR + FRED tools")
        print("=" * 60)

        agent_id = create_or_get_agent(client)
        update_agent(client, agent_id, instructions=BASELINE_INSTRUCTIONS, with_tools=True)

        results_path = OUTPUTS_DIR / f"eval_tools_responses{SUFFIX}.jsonl"
        print("\nGenerating agent responses...")
        run_agent_on_dataset(client, agent_id, dataset_path, results_path)

        run_evaluation(results_path, f"audit-agent-with-tools{SUFFIX}")

    elif mode == "enhanced":
        # --- Run 3: Enhanced prompt + tools ---
        print("=" * 60)
        print("ENHANCED EVALUATION — Optimized prompt + tools")
        print("=" * 60)

        agent_id = create_or_get_agent(client)
        update_agent(client, agent_id, instructions=ENHANCED_INSTRUCTIONS, with_tools=True)

        results_path = OUTPUTS_DIR / f"eval_enhanced_responses{SUFFIX}.jsonl"
        print("\nGenerating agent responses...")
        run_agent_on_dataset(client, agent_id, dataset_path, results_path)

        run_evaluation(results_path, f"audit-agent-enhanced{SUFFIX}")

    elif mode == "compare":
        # --- Compare all available runs ---
        print("=" * 60)
        print("COMPARISON — Compare all evaluation runs")
        print("=" * 60)
        compare_results()

    elif mode == "safety":
        # --- Safety evaluation on the latest results ---
        print("=" * 60)
        print("SAFETY EVALUATION")
        print("=" * 60)

        # Find the most recent responses file
        response_files = sorted(OUTPUTS_DIR.glob(f"eval_*_responses{SUFFIX}.jsonl"))
        if not response_files:
            print("No response files found. Run baseline first.")
            return
        latest = response_files[-1]
        print(f"Running safety eval on: {latest.name}")
        run_evaluation(latest, f"audit-agent-safety-{latest.stem}{SUFFIX}", include_safety=True)

    else:
        print(f"Usage: python {sys.argv[0]} [baseline|tools|enhanced|compare|safety]")
        print()
        print("  baseline  — Evaluate agent with instructions only (no tools)")
        print("  tools     — Add OpenAPI tools and re-evaluate")
        print("  enhanced  — Use enhanced prompt + tools and re-evaluate")
        print("  compare   — Compare metrics across all runs")
        print("  safety    — Run safety evaluators on the latest results")
        return

    print(f"\nAgent '{AGENT_NAME}' is persisted in Foundry — experiment in the portal!")


def compare_results():
    """Load all evaluation result files and print a side-by-side comparison."""
    result_files = sorted(OUTPUTS_DIR.glob(f"*{SUFFIX}_results.json"))
    if not result_files:
        print("No evaluation results found. Run baseline, tools, or enhanced first.")
        return

    all_metrics: dict[str, dict[str, float]] = {}
    for path in result_files:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        name = path.stem.replace("_results", "")
        metrics = data.get("metrics", {})
        all_metrics[name] = {
            k: v for k, v in metrics.items() if isinstance(v, (int, float))
        }

    # Collect all metric names
    all_keys = sorted(set(k for m in all_metrics.values() for k in m))

    # Print comparison table
    headers = list(all_metrics.keys())
    col_width = max(len(h) for h in headers + ["Metric"]) + 2
    col_width = max(col_width, 16)

    print(f"\n{'Metric':<30}", end="")
    for h in headers:
        print(f"{h:>{col_width}}", end="")
    print()
    print("-" * (30 + col_width * len(headers)))

    for key in all_keys:
        print(f"{key:<30}", end="")
        for h in headers:
            val = all_metrics[h].get(key)
            if val is not None:
                print(f"{val:>{col_width}.3f}", end="")
            else:
                print(f"{'—':>{col_width}}", end="")
        print()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()

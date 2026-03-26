"""
07b — Evaluating Foundry Agents (azure-ai-projects SDK)

Same workflow as 07_evaluations.py but uses the azure-ai-projects SDK
and OpenAI-compatible Evals API instead of azure-ai-evaluation.

Key differences from 07_evaluations.py:
  - Uses AIProjectClient (azure-ai-projects >= 2.0.0) instead of AgentsClient
  - Uses OpenAI-compatible client.evals.* API instead of azure.ai.evaluation.evaluate()
  - Agent evaluation uses azure_ai_target_completions to run the agent and
    evaluate in a single step (no manual thread/run loop)
  - Pre-collected responses can be re-evaluated with inline JSONL data

Concepts: AIProjectClient, openai.evals API, builtin evaluators,
          azure_ai_target_completions, PromptAgentDefinition, Foundry eval dashboard

Reference:
  https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/ai/azure-ai-projects/samples/evaluations/README.md
"""

import json
import multiprocessing
import os
import sys
import time
from pathlib import Path
from pprint import pformat

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from openai.types.eval_create_params import DataSourceConfigCustom
from openai.types.evals.create_eval_jsonl_run_data_source_param import (
    CreateEvalJSONLRunDataSourceParam,
    SourceFileContent,
    SourceFileContentContent,
)

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
Be concise, max 500 words.
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

Be concise, max 500 words. Prioritize actionable audit procedures.
"""


# ---------------------------------------------------------------------------
# Agent creation
# ---------------------------------------------------------------------------

def create_agent_version(
    project_client: AIProjectClient,
    *,
    instructions: str = BASELINE_INSTRUCTIONS,
) -> object:
    """Create a versioned agent snapshot for evaluation.

    Uses PromptAgentDefinition for a prompt-based agent. For agents with
    OpenAPI tools, configure the agent in the Foundry portal first, then
    call create_version() referencing that agent by name.
    """
    model = os.environ["MODEL_DEPLOYMENT_NAME"]
    agent = project_client.agents.create_version(
        agent_name=AGENT_NAME,
        definition=PromptAgentDefinition(
            model=model,
            instructions=instructions,
        ),
    )
    print(f"Agent version created: {agent.name} v{agent.version} (id: {agent.id})")
    return agent


# ---------------------------------------------------------------------------
# Testing criteria (evaluators)
# ---------------------------------------------------------------------------

def build_testing_criteria(
    eval_model: str,
    *,
    for_agent: bool = True,
    include_safety: bool = False,
) -> list[dict]:
    """Build evaluator testing criteria for the OpenAI Evals API.

    Args:
        eval_model: Deployment name for LLM-as-judge evaluators.
        for_agent: True  → map response to {{sample.output_text}} (agent eval).
                   False → map response to {{item.response}} (inline data eval).
        include_safety: Include content safety evaluators.
    """
    response_ref = "{{sample.output_text}}" if for_agent else "{{item.response}}"
    context_ref = "{{item.ground_truth}}" if for_agent else "{{item.context}}"

    criteria = [
        {
            "type": "azure_ai_evaluator",
            "name": "coherence",
            "evaluator_name": "builtin.coherence",
            "initialization_parameters": {"deployment_name": eval_model},
            "data_mapping": {
                "query": "{{item.query}}",
                "response": response_ref,
            },
        },
        {
            "type": "azure_ai_evaluator",
            "name": "relevance",
            "evaluator_name": "builtin.relevance",
            "initialization_parameters": {"deployment_name": eval_model},
            "data_mapping": {
                "query": "{{item.query}}",
                "response": response_ref,
            },
        },
        {
            "type": "azure_ai_evaluator",
            "name": "fluency",
            "evaluator_name": "builtin.fluency",
            "initialization_parameters": {"deployment_name": eval_model},
            "data_mapping": {
                "query": "{{item.query}}",
                "response": response_ref,
            },
        },
        {
            "type": "azure_ai_evaluator",
            "name": "groundedness",
            "evaluator_name": "builtin.groundedness",
            "initialization_parameters": {"deployment_name": eval_model},
            "data_mapping": {
                "query": "{{item.query}}",
                "response": response_ref,
                "context": context_ref,
            },
        },
        {
            "type": "azure_ai_evaluator",
            "name": "intent_resolution",
            "evaluator_name": "builtin.intent_resolution",
            "initialization_parameters": {"deployment_name": eval_model},
            "data_mapping": {
                "query": "{{item.query}}",
                "response": response_ref,
            },
        },
        {
            "type": "azure_ai_evaluator",
            "name": "task_adherence",
            "evaluator_name": "builtin.task_adherence",
            "initialization_parameters": {"deployment_name": eval_model},
            "data_mapping": {
                "query": "{{item.query}}",
                "response": response_ref,
            },
        },
    ]

    if include_safety:
        criteria.append(
            {
                "type": "azure_ai_evaluator",
                "name": "violence",
                "evaluator_name": "builtin.violence",
                "data_mapping": {
                    "query": "{{item.query}}",
                    "response": response_ref,
                },
            }
        )

    return criteria


# ---------------------------------------------------------------------------
# Agent evaluation (run agent + evaluate in one step)
# ---------------------------------------------------------------------------

def run_agent_evaluation(
    openai_client,
    *,
    eval_name: str,
    run_name: str,
    agent,
    dataset: list[dict],
    include_safety: bool = False,
) -> dict:
    """Create an evaluation (or reuse existing), run the agent, and evaluate.

    Uses azure_ai_target_completions to send queries to the agent and
    evaluate responses in a single eval run.

    The eval_name identifies a reusable evaluation container. Multiple runs
    with different run_names can be created under the same evaluation for
    side-by-side comparison in the Foundry portal.
    """
    eval_model = os.environ.get("EVAL_MODEL_DEPLOYMENT_NAME", "gpt-4.1")

    # --- Data source config: define the schema of each data item ---
    data_source_config = DataSourceConfigCustom(
        type="custom",
        item_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "ground_truth": {"type": "string"},
            },
            "required": ["query"],
        },
        include_sample_schema=True,
    )

    testing_criteria = build_testing_criteria(
        eval_model, for_agent=True, include_safety=include_safety
    )

    print(f"\nEvaluation: {eval_name}")
    print(f"  Evaluators: {', '.join(c['name'] for c in testing_criteria)}")
    print(f"  Dataset: {len(dataset)} queries")
    print(f"  Agent: {agent.name} v{agent.version}")

    # Reuse an existing evaluation with the same name, or create a new one.
    # This allows multiple runs (baseline, tools, enhanced) to be nested
    # under one evaluation for side-by-side comparison in the portal.
    eval_obj = None
    for existing in openai_client.evals.list():
        if existing.name == eval_name:
            eval_obj = existing
            print(f"  Reusing evaluation (id: {eval_obj.id})")
            break

    if eval_obj is None:
        eval_obj = openai_client.evals.create(
            name=eval_name,
            data_source_config=data_source_config,
            testing_criteria=testing_criteria,  # type: ignore
        )
        print(f"  Evaluation created (id: {eval_obj.id})")

    # --- Run eval with agent target completions ---
    data_source = {
        "type": "azure_ai_target_completions",
        "source": {
            "type": "file_content",
            "content": [
                {
                    "item": {
                        "query": row["query"],
                        "ground_truth": row.get("ground_truth", ""),
                    }
                }
                for row in dataset
            ],
        },
        "input_messages": {
            "type": "template",
            "template": [
                {
                    "type": "message",
                    "role": "user",
                    "content": {"type": "input_text", "text": "{{item.query}}"},
                }
            ],
        },
        "target": {
            "type": "azure_ai_agent",
            "name": agent.name,
            "version": agent.version,
        },
    }

    eval_run = openai_client.evals.runs.create(
        eval_id=eval_obj.id,
        name=run_name,
        metadata={"participant": PARTICIPANT_INITIALS, "mode": run_name},
        data_source=data_source,  # type: ignore
    )
    print(f"  Run created: {run_name} (id: {eval_run.id})")

    # --- Poll for completion ---
    while eval_run.status not in ("completed", "failed"):
        time.sleep(10)
        eval_run = openai_client.evals.runs.retrieve(
            run_id=eval_run.id, eval_id=eval_obj.id
        )
        print(f"  Waiting... status: {eval_run.status}")

    # --- Collect and display results ---
    output_items = list(
        openai_client.evals.runs.output_items.list(
            run_id=eval_run.id, eval_id=eval_obj.id
        )
    )

    result = _format_results(eval_name, eval_run, output_items)
    _save_results(eval_name, result)
    _print_summary(eval_name, result, eval_run)

    return result


# ---------------------------------------------------------------------------
# Response evaluation (evaluate pre-collected responses)
# ---------------------------------------------------------------------------

def run_response_evaluation(
    openai_client,
    *,
    eval_name: str,
    run_name: str = "",
    results_path: Path,
    include_safety: bool = False,
) -> dict:
    """Evaluate pre-collected agent responses from a JSONL file.

    The JSONL file should have columns: query, response, context, ground_truth
    (compatible with output from 07_evaluations.py).
    """
    eval_model = os.environ.get("EVAL_MODEL_DEPLOYMENT_NAME", "gpt-4.1")

    with open(results_path, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]

    # --- Data source config for response data ---
    data_source_config = DataSourceConfigCustom(
        type="custom",
        item_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "response": {"type": "string"},
                "context": {"type": "string"},
                "ground_truth": {"type": "string"},
            },
            "required": [],
        },
        include_sample_schema=True,
    )

    testing_criteria = build_testing_criteria(
        eval_model, for_agent=False, include_safety=include_safety
    )

    if not run_name:
        run_name = f"{eval_name}-run"

    print(f"\nEvaluation: {eval_name}")
    print(f"  Evaluators: {', '.join(c['name'] for c in testing_criteria)}")
    print(f"  Data: {results_path} ({len(rows)} rows)")

    # Reuse existing evaluation or create a new one
    eval_obj = None
    for existing in openai_client.evals.list():
        if existing.name == eval_name:
            eval_obj = existing
            print(f"  Reusing evaluation (id: {eval_obj.id})")
            break

    if eval_obj is None:
        eval_obj = openai_client.evals.create(
            name=eval_name,
            data_source_config=data_source_config,
            testing_criteria=testing_criteria,  # type: ignore
        )
        print(f"  Evaluation created (id: {eval_obj.id})")

    # --- Run eval with inline JSONL data ---
    eval_run = openai_client.evals.runs.create(
        eval_id=eval_obj.id,
        name=run_name,
        metadata={"participant": PARTICIPANT_INITIALS, "mode": run_name},
        data_source=CreateEvalJSONLRunDataSourceParam(
            type="jsonl",
            source=SourceFileContent(
                type="file_content",
                content=[SourceFileContentContent(item=row) for row in rows],
            ),
        ),
    )
    print(f"  Run created: {run_name} (id: {eval_run.id})")

    # --- Poll for completion ---
    while eval_run.status not in ("completed", "failed"):
        time.sleep(10)
        eval_run = openai_client.evals.runs.retrieve(
            run_id=eval_run.id, eval_id=eval_obj.id
        )
        print(f"  Waiting... status: {eval_run.status}")

    # --- Collect and display results ---
    output_items = list(
        openai_client.evals.runs.output_items.list(
            run_id=eval_run.id, eval_id=eval_obj.id
        )
    )

    result = _format_results(eval_name, eval_run, output_items)
    _save_results(eval_name, result)
    _print_summary(eval_name, result, eval_run)

    return result


# ---------------------------------------------------------------------------
# Results helpers
# ---------------------------------------------------------------------------

def _format_results(
    eval_name: str, eval_run, output_items: list
) -> dict:
    """Extract metrics from eval run output items into a summary dict."""
    # Aggregate per-evaluator scores from output items
    score_sums: dict[str, float] = {}
    score_counts: dict[str, int] = {}

    for item in output_items:
        results_list = getattr(item, "results", None) or []
        for r in results_list:
            name = getattr(r, "name", None) or getattr(r, "evaluator_name", "unknown")
            score = getattr(r, "score", None)
            if score is not None:
                score_sums[name] = score_sums.get(name, 0.0) + score
                score_counts[name] = score_counts.get(name, 0) + 1

    metrics = {}
    for name in sorted(score_sums):
        count = score_counts[name]
        metrics[name] = score_sums[name] / count if count else 0.0

    return {
        "eval_name": eval_name,
        "eval_run_id": eval_run.id,
        "status": eval_run.status,
        "result_counts": getattr(eval_run, "result_counts", None),
        "report_url": getattr(eval_run, "report_url", ""),
        "metrics": metrics,
        "output_items_count": len(output_items),
    }


def _save_results(eval_name: str, result: dict) -> Path:
    """Save evaluation results to a JSON file."""
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUTS_DIR / f"{eval_name}_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)
    return output_path


def _print_summary(eval_name: str, result: dict, eval_run) -> None:
    """Print a formatted summary of evaluation results."""
    print(f"\n{'=' * 60}")
    print(f"Evaluation: {eval_name}")
    print(f"{'=' * 60}")

    if result["status"] != "completed":
        print(f"  Status: {result['status']} (evaluation did not complete)")
        return

    metrics = result.get("metrics", {})
    for metric_name, value in sorted(metrics.items()):
        if isinstance(value, float):
            print(f"  {metric_name}: {value:.3f}")
        else:
            print(f"  {metric_name}: {value}")

    result_counts = result.get("result_counts")
    if result_counts:
        print(f"\n  Result counts: {result_counts}")

    report_url = result.get("report_url", "")
    if report_url:
        print(f"\n  View in Foundry portal: {report_url}")

    output_path = OUTPUTS_DIR / f"{eval_name}_results.json"
    print(f"  Full results saved to: {output_path}")


# ---------------------------------------------------------------------------
# Compare evaluation runs
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Load dataset
# ---------------------------------------------------------------------------

def load_dataset(dataset_path: Path) -> list[dict]:
    """Load the evaluation dataset from a JSONL file."""
    with open(dataset_path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


# ---------------------------------------------------------------------------
# Main — Evaluation workflow
# ---------------------------------------------------------------------------

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "baseline"

    endpoint = os.environ["PROJECT_ENDPOINT"]
    credential = DefaultAzureCredential()
    dataset_path = DATA_DIR / "eval_dataset.jsonl"

    with (
        AIProjectClient(endpoint=endpoint, credential=credential) as project_client,
        project_client.get_openai_client() as openai_client,
    ):
        # All modes share one evaluation container for side-by-side comparison
        eval_name = f"AuditResearchAgent-Eval{SUFFIX}"

        if mode == "baseline":
            # --- Run 1: Baseline agent (instructions only) ---
            print("=" * 60)
            print("BASELINE EVALUATION — Instructions only, no tools")
            print("=" * 60)

            agent = create_agent_version(
                project_client, instructions=BASELINE_INSTRUCTIONS
            )
            dataset = load_dataset(dataset_path)

            run_agent_evaluation(
                openai_client,
                eval_name=eval_name,
                run_name=f"baseline{SUFFIX}",
                agent=agent,
                dataset=dataset,
            )

        elif mode == "tools":
            # --- Run 2: Agent with tools ---
            # NOTE: For OpenAPI tools, configure the agent with tools in the
            # Foundry portal first, then create a version here. The
            # PromptAgentDefinition creates a prompt-only version; to include
            # tools, ensure the agent is already configured with tools in
            # the portal before running this mode.
            print("=" * 60)
            print("TOOLS EVALUATION — Agent with SEC EDGAR + FRED tools")
            print("=" * 60)

            agent = create_agent_version(
                project_client, instructions=BASELINE_INSTRUCTIONS
            )
            dataset = load_dataset(dataset_path)

            run_agent_evaluation(
                openai_client,
                eval_name=eval_name,
                run_name=f"with-tools{SUFFIX}",
                agent=agent,
                dataset=dataset,
            )

        elif mode == "enhanced":
            # --- Run 3: Enhanced prompt + tools ---
            print("=" * 60)
            print("ENHANCED EVALUATION — Optimized prompt + tools")
            print("=" * 60)

            agent = create_agent_version(
                project_client, instructions=ENHANCED_INSTRUCTIONS
            )
            dataset = load_dataset(dataset_path)

            run_agent_evaluation(
                openai_client,
                eval_name=eval_name,
                run_name=f"enhanced{SUFFIX}",
                agent=agent,
                dataset=dataset,
            )

        elif mode == "responses":
            # --- Evaluate pre-collected responses (from 07_evaluations.py) ---
            print("=" * 60)
            print("RESPONSE EVALUATION — Evaluate saved agent responses")
            print("=" * 60)

            if len(sys.argv) < 3:
                # Find most recent responses file
                response_files = sorted(
                    OUTPUTS_DIR.glob(f"eval_*_responses{SUFFIX}.jsonl")
                )
                if not response_files:
                    print("No response files found. Provide a path or run baseline first.")
                    return
                results_path = response_files[-1]
            else:
                results_path = Path(sys.argv[2])

            print(f"Evaluating responses from: {results_path.name}")
            eval_name = f"response-eval-{results_path.stem}{SUFFIX}"

            run_response_evaluation(
                openai_client,
                eval_name=eval_name,
                results_path=results_path,
            )

        elif mode == "compare":
            # --- Compare all available runs ---
            print("=" * 60)
            print("COMPARISON — Compare all evaluation runs")
            print("=" * 60)
            compare_results()

        elif mode == "safety":
            # --- Safety evaluation ---
            print("=" * 60)
            print("SAFETY EVALUATION")
            print("=" * 60)

            if len(sys.argv) >= 3:
                results_path = Path(sys.argv[2])
            else:
                response_files = sorted(
                    OUTPUTS_DIR.glob(f"eval_*_responses{SUFFIX}.jsonl")
                )
                if not response_files:
                    print("No response files found. Run baseline first.")
                    return
                results_path = response_files[-1]

            print(f"Running safety eval on: {results_path.name}")
            run_response_evaluation(
                openai_client,
                eval_name=f"audit-agent-safety-{results_path.stem}{SUFFIX}",
                results_path=results_path,
                include_safety=True,
            )

        else:
            print(f"Usage: python {sys.argv[0]} [baseline|tools|enhanced|responses|compare|safety]")
            print()
            print("  baseline          — Evaluate agent with instructions only (no tools)")
            print("  tools             — Create version with tools config and re-evaluate")
            print("  enhanced          — Use enhanced prompt and re-evaluate")
            print("  responses [file]  — Re-evaluate saved response JSONL from 07_evaluations.py")
            print("  compare           — Compare metrics across all runs")
            print("  safety [file]     — Run safety evaluators on saved responses")
            return

    print(f"\nAgent '{AGENT_NAME}' is persisted in Foundry — experiment in the portal!")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()

"""
Capstone: Multi-Agent Risk-Based Audit Planning

Orchestrates three specialized agents using MAF to produce a comprehensive
risk-based audit plan.  Ties together the key MAF patterns from Sessions 1–2:

  • ConcurrentBuilder  — Phase 1 fans out to Risk Assessor + Control Evaluator
  • @tool decorator    — custom domain tools for financial data and compliance
  • AgentMiddleware    — PlanningPhaseLogger tracks timing/throughput per agent
  • FunctionMiddleware — ToolCallLogger instruments every tool invocation
  • Output writing     — final plan saved as a markdown deliverable

Architecture:
  ┌──────────────────────────────────────────────────────┐
  │          ConcurrentBuilder (Phase 1)                 │
  │  ┌──────────────────┐  ┌──────────────────────────┐  │
  │  │  Risk Assessor   │  │  Control Evaluator       │  │
  │  │  @tools:         │  │  @tools:                 │  │
  │  │  - financials    │  │  - compliance checker    │  │
  │  │  - ratios        │  │  - regulatory risk       │  │
  │  └──────────────────┘  └──────────────────────────┘  │
  └───────────────┬──────────────────────┬───────────────┘
                  │  risk report         │  controls report
                  └──────────┬───────────┘
                             ▼
                  ┌──────────────────────┐
                  │  Audit Plan Writer   │  ← Phase 2
                  │  (synthesizes both)  │
                  └──────────────────────┘
                             │
                             ▼
                  outputs/audit_plan.md

Run: python audit_planner.py
"""

import asyncio
import os
import time
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

from agent_framework import (
    AgentContext,
    AgentMiddleware,
    AgentResponse,
    FunctionInvocationContext,
    FunctionMiddleware,
    Message,
)
from agent_framework.azure import AzureOpenAIResponsesClient
from agent_framework.orchestrations import ConcurrentBuilder
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

# Agent definitions
from agents.risk_assessor import RISK_ASSESSOR_INSTRUCTIONS, RISK_ASSESSOR_NAME
from agents.control_evaluator import CONTROL_EVALUATOR_INSTRUCTIONS, CONTROL_EVALUATOR_NAME
from agents.audit_plan_writer import AUDIT_PLAN_WRITER_INSTRUCTIONS, AUDIT_PLAN_WRITER_NAME

# Tools
from tools.financial_data import get_client_financials, compute_financial_ratios
from tools.compliance_checker import check_compliance_requirements, assess_regulatory_risk

load_dotenv()


# ─── Middleware: Planning Phase Logger (AgentMiddleware) ──────────
class PlanningPhaseLogger(AgentMiddleware):
    """Logs each agent invocation with timing and output size.

    As an AgentMiddleware it wraps the entire agent execution including
    tool calls, providing a high-level audit trail of the planning process.
    """

    def __init__(self):
        self.phases: list[dict] = []

    async def process(
        self,
        context: AgentContext,
        call_next: Callable[[], Awaitable[None]],
    ) -> None:
        agent_name = context.agent.name
        start = time.time()
        print(f"  ▶ [{agent_name}] Starting...")

        await call_next()

        elapsed_ms = round((time.time() - start) * 1000)
        response_chars = 0
        if context.result and isinstance(context.result, AgentResponse):
            response_chars = sum(len(m.text or "") for m in context.result.messages)

        self.phases.append({
            "agent": agent_name,
            "duration_ms": elapsed_ms,
            "response_chars": response_chars,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        print(f"  ✓ [{agent_name}] Done — {elapsed_ms:,}ms, {response_chars:,} chars")


# ─── Middleware: Tool Call Logger (FunctionMiddleware) ─────────────
class ToolCallLogger(FunctionMiddleware):
    """Instruments every @tool invocation made during audit planning.

    As a FunctionMiddleware it wraps individual tool calls (not the full
    agent run), tracking which data sources each agent used.
    """

    def __init__(self):
        self.calls: list[dict] = []

    async def process(
        self,
        context: FunctionInvocationContext,
        call_next: Callable[[], Awaitable[None]],
    ) -> None:
        tool_name = context.function.name
        start = time.time()
        await call_next()
        elapsed_ms = round((time.time() - start) * 1000)
        self.calls.append({"tool": tool_name, "duration_ms": elapsed_ms})
        print(f"    🔧 {tool_name} ({elapsed_ms}ms)")


# ─── Helpers ──────────────────────────────────────────────────────

def extract_report(messages: list, agent_name: str) -> str:
    """Extract the last assistant message from a specific agent."""
    for msg in reversed(messages):
        if (
            getattr(msg, "role", None) == "assistant"
            and getattr(msg, "author_name", None) == agent_name
            and getattr(msg, "text", None)
        ):
            return msg.text
    return "(no report)"


async def main():
    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME"],
        credential=AzureCliCredential(),
    )

    # Shared middleware — collects metrics across all agents
    phase_logger = PlanningPhaseLogger()
    tool_logger = ToolCallLogger()

    # --- Create specialized agents with middleware ---

    risk_assessor = client.as_agent(
        name=RISK_ASSESSOR_NAME,
        instructions=RISK_ASSESSOR_INSTRUCTIONS,
        tools=[get_client_financials, compute_financial_ratios],
        middleware=[phase_logger, tool_logger],
    )

    control_evaluator = client.as_agent(
        name=CONTROL_EVALUATOR_NAME,
        instructions=CONTROL_EVALUATOR_INSTRUCTIONS,
        tools=[check_compliance_requirements, assess_regulatory_risk, get_client_financials],
        middleware=[phase_logger, tool_logger],
    )

    audit_plan_writer = client.as_agent(
        name=AUDIT_PLAN_WRITER_NAME,
        instructions=AUDIT_PLAN_WRITER_INSTRUCTIONS,
        middleware=[phase_logger],
    )

    output_parts: list[str] = []

    # ═══════════════════════════════════════════════════════════════
    # PHASE 1: Concurrent Analysis  (ConcurrentBuilder)
    # ═══════════════════════════════════════════════════════════════
    #
    # ConcurrentBuilder fans the same prompt to both agents in
    # parallel.  Each agent's specialized instructions (and @tools)
    # determine what it focuses on.  The shared middleware instances
    # (PlanningPhaseLogger + ToolCallLogger) capture metrics across
    # both concurrent runs.
    # ═══════════════════════════════════════════════════════════════
    print("=" * 70)
    print("PHASE 1: Concurrent Risk Assessment & Controls Evaluation")
    print("  Using ConcurrentBuilder to run both agents in parallel")
    print("=" * 70)

    analysis_prompt = (
        "Analyze Apex Financial Group for audit planning. "
        "They are a publicly traded financial services company ($2.8B revenue, "
        "$45B total assets) subject to SOX 404, Basel III, ASC 326 (CECL), "
        "and ASC 820 (Fair Value). Last year had a significant deficiency "
        "related to derivative valuations. They recently migrated to a "
        "cloud-based trading platform. "
        "Use your tools to retrieve all relevant data. "
        "Produce a comprehensive report based on your specialty."
    )

    concurrent_wf = ConcurrentBuilder(
        participants=[risk_assessor, control_evaluator],
    ).build()

    concurrent_result = await concurrent_wf.run(analysis_prompt)
    outputs = concurrent_result.get_outputs()

    # ConcurrentBuilder returns [combined_conversation] — extract by author_name
    risk_report = "(no report)"
    controls_report = "(no report)"
    if outputs:
        conversation = outputs[0] if isinstance(outputs[0], list) else outputs
        risk_report = extract_report(conversation, RISK_ASSESSOR_NAME)
        controls_report = extract_report(conversation, CONTROL_EVALUATOR_NAME)

    print("\n--- Risk Assessment Report (preview) ---")
    print(risk_report[:600] + ("..." if len(risk_report) > 600 else ""))
    output_parts.append(f"## Risk Assessment Report\n\n{risk_report}")

    print("\n--- Controls Evaluation Report (preview) ---")
    print(controls_report[:600] + ("..." if len(controls_report) > 600 else ""))
    output_parts.append(f"## Controls Evaluation Report\n\n{controls_report}")

    # ═══════════════════════════════════════════════════════════════
    # PHASE 2: Audit Plan Generation  (sequential synthesis)
    # ═══════════════════════════════════════════════════════════════
    #
    # The Audit Plan Writer receives both reports and synthesizes
    # them into a single actionable plan.
    # ═══════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("PHASE 2: Audit Plan Generation")
    print("  Audit Plan Writer synthesizes both reports")
    print("=" * 70)

    plan_prompt = (
        f"Based on the following reports, produce a comprehensive Risk-Based "
        f"Audit Plan for Apex Financial Group (publicly traded financial services, "
        f"$2.8B revenue, $45B total assets).\n\n"
        f"=== RISK ASSESSMENT REPORT ===\n{risk_report}\n\n"
        f"=== CONTROLS EVALUATION REPORT ===\n{controls_report}"
    )

    plan_result = await audit_plan_writer.run(plan_prompt)
    audit_plan = plan_result.text if hasattr(plan_result, "text") and plan_result.text else str(plan_result)

    print("\n--- Final Risk-Based Audit Plan ---")
    print(audit_plan)
    output_parts.append(f"## Risk-Based Audit Plan\n\n{audit_plan}")

    # ═══════════════════════════════════════════════════════════════
    # SUMMARY — Planning Metrics from Middleware
    # ═══════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("PLANNING COMPLETE — Metrics (from middleware)")
    print("=" * 70)

    metric_lines: list[str] = []
    for phase in phase_logger.phases:
        line = f"  {phase['agent']}: {phase['duration_ms']:,}ms ({phase['response_chars']:,} chars)"
        print(line)
        metric_lines.append(
            f"- **{phase['agent']}**: {phase['duration_ms']:,}ms, "
            f"{phase['response_chars']:,} chars"
        )

    print(f"\n  Tool calls made: {len(tool_logger.calls)}")
    tool_lines: list[str] = []
    for call in tool_logger.calls:
        line = f"    - {call['tool']}: {call['duration_ms']}ms"
        print(line)
        tool_lines.append(f"  - `{call['tool']}`: {call['duration_ms']}ms")

    # ═══════════════════════════════════════════════════════════════
    # Write output to markdown
    # ═══════════════════════════════════════════════════════════════
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(os.path.join(script_dir, "outputs"), exist_ok=True)
    out_path = os.path.join(script_dir, "outputs", "audit_plan.md")

    with open(out_path, "w") as f:
        f.write("# Capstone: Risk-Based Audit Plan — Apex Financial Group\n\n")
        f.write("\n\n---\n\n".join(output_parts))
        f.write("\n\n---\n\n## Planning Metrics\n\n")
        f.write("\n".join(metric_lines))
        f.write(f"\n\n### Tool Calls ({len(tool_logger.calls)} total)\n\n")
        f.write("\n".join(tool_lines))

    print(f"\n✅ Output written to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())

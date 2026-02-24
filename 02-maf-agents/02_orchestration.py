"""
02 — Agent Orchestration Patterns (using MAF Orchestration Builders)

Demonstrates three orchestration patterns using MAF's built-in builders:
  1. Sequential — SequentialBuilder chains agents, sharing conversation context
  2. Concurrent — ConcurrentBuilder fans out to agents in parallel, aggregates results
  3. Handoff   — HandoffBuilder routes from a triage agent to specialists via
                  auto-registered handoff tools

Concepts: SequentialBuilder, ConcurrentBuilder, HandoffBuilder, workflow streaming

Reference: https://github.com/microsoft/agent-framework/tree/main/python/samples/03-workflows/orchestrations
"""

import asyncio
import logging
import os
from typing import Any, cast

from agent_framework import AgentResponse, Message, WorkflowEvent, WorkflowRunState
from agent_framework.azure import AzureOpenAIResponsesClient
from agent_framework.orchestrations import (
    ConcurrentBuilder,
    HandoffBuilder,
    HandoffAgentUserRequest,
    SequentialBuilder,
)
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

load_dotenv()

# logging.basicConfig(level=logging.DEBUG)
# logging.getLogger("azure").setLevel(logging.DEBUG)
# logging.getLogger("httpx").setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def print_conversation(messages: list[Message], title: str = "Conversation") -> str:
    """Pretty-print a list of Messages and return them as a string."""
    lines: list[str] = [f"\n===== {title} ====="]
    for i, msg in enumerate(messages, start=1):
        name = msg.author_name or ("assistant" if msg.role == "assistant" else "user")
        entry = f"\n{'-' * 50}\n{i:02d} [{name}]:\n{msg.text}"
        lines.append(entry)
    text = "\n".join(lines)
    print(text)
    return text


async def main():
    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME"],
        credential=AzureCliCredential(),
    )

    scenario = (
        "Client: Mid-size retailer, $100M revenue. Inventory is 40% of assets. "
        "New ERP system was implemented mid-year. Two material weaknesses were "
        "identified in the prior year audit related to inventory valuation."
    )

    output_parts: list[str] = []  # collect output for markdown file

    # =====================================================================
    # Pattern 1: Sequential Orchestration  (SequentialBuilder)
    # =====================================================================
    # An analyst drafts findings, then a reviewer refines them.
    # SequentialBuilder chains them so the shared conversation context
    # flows from one agent to the next automatically.
    print("=" * 60)
    print("PATTERN 1: Sequential (Analyst → Reviewer)")
    print("=" * 60)

    analyst = client.as_agent(
        name="AuditAnalyst",
        instructions=(
            "You are a junior audit analyst. Draft a brief summary of key audit "
            "findings based on the scenario provided. Be factual and concise."
        ),
    )

    reviewer = client.as_agent(
        name="AuditReviewer",
        instructions=(
            "You are a senior audit reviewer. Review the analyst's draft findings "
            "and improve them: add missing risks, correct any issues, and ensure "
            "professional tone. Output the revised findings only."
        ),
    )

    # Build the sequential workflow: analyst → reviewer
    sequential_wf = SequentialBuilder(participants=[analyst, reviewer]).build()

    # Run with streaming — the final "output" event carries the full conversation
    async for event in sequential_wf.run(f"Scenario: {scenario}", stream=True):
        if event.type == "output":
            conversation = cast(list[Message], event.data)
            text = print_conversation(conversation, "Sequential — Final Conversation")
            output_parts.append("## Pattern 1: Sequential\n" + text)

    # =====================================================================
    # Pattern 2: Concurrent Orchestration  (ConcurrentBuilder)
    # =====================================================================
    # Three risk-assessment agents run in parallel on the same prompt.
    # ConcurrentBuilder fans the prompt out to all participants and
    # aggregates their results.
    print("\n" + "=" * 60)
    print("PATTERN 2: Concurrent (Parallel Risk Assessment)")
    print("=" * 60)

    financial_risk_agent = client.as_agent(
        name="FinancialRiskAssessor",
        instructions="You assess financial reporting risks. Provide 2-3 bullet points. Be concise.",
    )

    it_risk_agent = client.as_agent(
        name="ITRiskAssessor",
        instructions="You assess IT and cybersecurity risks for audits. Provide 2-3 bullet points. Be concise.",
    )

    compliance_risk_agent = client.as_agent(
        name="ComplianceRiskAssessor",
        instructions="You assess regulatory compliance risks. Provide 2-3 bullet points. Be concise.",
    )

    prompt = f"Assess risks for this client: {scenario}"

    # Build the concurrent workflow: all three agents in parallel
    concurrent_wf = ConcurrentBuilder(
        participants=[financial_risk_agent, it_risk_agent, compliance_risk_agent]
    ).build()

    result = await concurrent_wf.run(prompt)
    outputs = result.get_outputs()

    concurrent_lines: list[str] = []
    if outputs:
        print("\n===== Concurrent — Aggregated Results =====")
        for output in outputs:
            messages: list[Message] | Any = output
            for msg in messages:
                name = msg.author_name or "assistant"
                entry = f"\n{'-' * 50}\n[{name}]:\n{msg.text}"
                print(entry)
                concurrent_lines.append(entry)

    output_parts.append("## Pattern 2: Concurrent\n" + "\n".join(concurrent_lines))

    # =====================================================================
    # Pattern 3: Handoff Orchestration  (HandoffBuilder)
    # =====================================================================
    # A triage agent classifies the user's question, then uses MAF's
    # auto-registered handoff tools to route to the correct specialist.
    # No manual if/else routing needed — the framework wires it up.
    print("\n" + "=" * 60)
    print("PATTERN 3: Handoff (Triage → Specialist)")
    print("=" * 60)

    triage_agent = client.as_agent(
        name="TriageAgent",
        instructions=(
            "You are a triage agent for a professional services firm. "
            "Classify the user's question and hand off to the appropriate specialist. "
            "Available specialists: AuditSpecialist, TaxSpecialist, AdvisorySpecialist."
        ),
    )

    audit_specialist = client.as_agent(
        name="AuditSpecialist",
        instructions="You are an audit specialist. Answer audit questions concisely.",
    )

    tax_specialist = client.as_agent(
        name="TaxSpecialist",
        instructions="You are a tax specialist. Answer tax questions concisely.",
    )

    advisory_specialist = client.as_agent(
        name="AdvisorySpecialist",
        instructions="You are an advisory specialist. Answer consulting questions concisely.",
    )

    question = "What procedures should we perform to test revenue recognition?"

    # Build handoff workflow — HandoffBuilder auto-registers handoff tools
    # so the triage agent can call e.g. "transfer_to_AuditSpecialist" automatically.
    handoff_wf = (
        HandoffBuilder(
            name="professional_services_handoff",
            participants=[triage_agent, audit_specialist, tax_specialist, advisory_specialist],
            # Terminate once a specialist (non-triage) has responded
            termination_condition=lambda conversation: (
                len(conversation) > 2
                and any(
                    msg.role == "assistant" and msg.author_name != "TriageAgent"
                    for msg in conversation
                )
            ),
        )
        .with_start_agent(triage_agent)
        .build()
    )

    # Run the handoff workflow with event handling.
    # HandoffBuilder workflows are interactive — after the specialist responds
    # the workflow may enter IDLE_WITH_PENDING_REQUESTS.  We handle the
    # request/response loop here, terminating after the specialist answers.
    handoff_lines: list[str] = []

    def _process_handoff_events(events: list[WorkflowEvent]) -> list[WorkflowEvent]:
        """Process events and return any pending user-input requests."""
        pending: list[WorkflowEvent] = []
        for event in events:
            if event.type == "handoff_sent":
                line = f"\n[Handoff: {event.data.source} → {event.data.target}]"
                print(line)
                handoff_lines.append(line)
            elif event.type == "output":
                data = event.data
                if isinstance(data, AgentResponse):
                    for msg in data.messages:
                        if msg.text:
                            speaker = msg.author_name or msg.role
                            line = f"  {speaker}: {msg.text}"
                            print(line)
                            handoff_lines.append(line)
                elif isinstance(data, list):
                    # Final conversation snapshot
                    print("\n===== Handoff — Final Conversation =====")
                    for msg in data:
                        speaker = getattr(msg, "author_name", None) or getattr(msg, "role", "?")
                        text = getattr(msg, "text", None) or str(msg)
                        line = f"  - {speaker}: {text}"
                        print(line)
                        handoff_lines.append(line)
            elif event.type == "request_info" and isinstance(event.data, HandoffAgentUserRequest):
                # Print the agent's response that precedes the user-input request
                if event.data.agent_response:
                    for msg in event.data.agent_response.messages:
                        if msg.text:
                            speaker = msg.author_name or msg.role
                            line = f"  {speaker}: {msg.text}"
                            print(line)
                            handoff_lines.append(line)
                pending.append(event)
        return pending

    # Initial run
    initial_events = [event async for event in handoff_wf.run(question, stream=True)]
    pending = _process_handoff_events(initial_events)

    # If the workflow wants more user input, terminate gracefully
    if pending:
        responses = {req.request_id: HandoffAgentUserRequest.terminate() for req in pending}
        followup_events = await handoff_wf.run(responses=responses)
        _process_handoff_events(followup_events)

    output_parts.append("## Pattern 3: Handoff\n" + "\n".join(handoff_lines))

    # --- Write output to markdown ---
    os.makedirs("02-maf-agents/outputs", exist_ok=True)
    out_path = "02-maf-agents/outputs/02_orchestration.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# 02 — Orchestration Patterns\n\n")
        f.write("\n\n".join(output_parts))
    print(f"\n✅ Output written to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())

"""
05 — Implementing Guardrails and Safety Measures

Demonstrates MAF's AgentMiddleware for implementing guardrails:
  1. Input validation — blocks inappropriate or off-topic requests
  2. PII redaction — removes sensitive data from agent responses
  3. Audit logging — logs all agent interactions for compliance

Concepts: AgentMiddleware, AgentContext, MiddlewareTermination, middleware pipeline

Reference: https://github.com/microsoft/agent-framework/tree/main/python/samples/02-agents/middleware
"""

import asyncio
import logging
import os
import re
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

from agent_framework import (
    AgentContext,
    AgentMiddleware,
    AgentResponse,
    Message,
    MiddlewareTermination,
)
from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

load_dotenv()

# logging.basicConfig(level=logging.DEBUG)
# logging.getLogger("azure").setLevel(logging.DEBUG)
# logging.getLogger("httpx").setLevel(logging.WARNING)


# --- Guardrail 1: Input Validation Middleware ---
class TopicGuardMiddleware(AgentMiddleware):
    """Blocks requests that are off-topic for the assurance practice.

    Uses MiddlewareTermination to short-circuit the pipeline before
    the request ever reaches the model.
    """

    BLOCKED_TOPICS = ["personal advice", "stock picks", "investment recommendations"]

    async def process(
        self,
        context: AgentContext,
        call_next: Callable[[], Awaitable[None]],
    ) -> None:
        # Check the last user message for blocked topics
        last_message = context.messages[-1] if context.messages else None
        if last_message and last_message.text:
            input_lower = last_message.text.lower()
            for topic in self.BLOCKED_TOPICS:
                if topic in input_lower:
                    print(f"  [TopicGuard] ⛔ Blocked topic detected: '{topic}'")
                    # Set a canned response and terminate — model never runs
                    context.result = AgentResponse(
                        messages=[
                            Message(
                                role="assistant",
                                contents=[
                                    f"I'm unable to help with {topic}. I'm designed to assist "
                                    f"with audit and assurance topics only. Please consult the "
                                    f"appropriate team for this request."
                                ],
                            )
                        ]
                    )
                    raise MiddlewareTermination(result=context.result)

        # Input is acceptable — pass to the next middleware / agent
        await call_next()


# --- Guardrail 2: PII Redaction Middleware ---
class PIIRedactionMiddleware(AgentMiddleware):
    """Redacts common PII patterns (SSNs, emails, card numbers) from agent responses.

    Runs *after* the model generates a response (post-processing).
    """

    PII_PATTERNS = [
        (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN REDACTED]"),
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL REDACTED]"),
        (r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b", "[CARD NUMBER REDACTED]"),
    ]

    async def process(
        self,
        context: AgentContext,
        call_next: Callable[[], Awaitable[None]],
    ) -> None:
        # Let the agent run first
        await call_next()

        # Redact PII from the response messages
        if context.result and isinstance(context.result, AgentResponse):
            redacted = False
            new_messages: list[Message] = []
            for msg in context.result.messages:
                if msg.text:
                    cleaned = msg.text
                    for pattern, replacement in self.PII_PATTERNS:
                        cleaned = re.sub(pattern, replacement, cleaned)
                    if cleaned != msg.text:
                        redacted = True
                    new_messages.append(
                        Message(role=msg.role, contents=[cleaned])
                    )
                else:
                    new_messages.append(msg)
            if redacted:
                print("  [PIIRedaction] 🔒 PII detected and redacted from response")
                context.result = AgentResponse(messages=new_messages)


# --- Guardrail 3: Audit Logging Middleware ---
class AuditLogMiddleware(AgentMiddleware):
    """Logs all agent interactions for compliance audit trail.

    As the outermost middleware, it captures the full request/response
    lifecycle including any short-circuits from inner middleware.
    """

    def __init__(self):
        self.log: list[dict] = []

    async def process(
        self,
        context: AgentContext,
        call_next: Callable[[], Awaitable[None]],
    ) -> None:
        start_time = datetime.now(timezone.utc)

        # Capture input
        last_msg = context.messages[-1] if context.messages else None
        user_input = last_msg.text[:200] if last_msg and last_msg.text else "(empty)"

        entry: dict = {
            "timestamp": start_time.isoformat(),
            "agent": context.agent.name,
            "input": user_input,
        }

        try:
            await call_next()
        except MiddlewareTermination:
            entry["blocked"] = True

        # Log the response
        if context.result and isinstance(context.result, AgentResponse):
            first_msg = context.result.messages[0] if context.result.messages else None
            entry["output"] = (first_msg.text[:200] if first_msg and first_msg.text else "(empty)")
        else:
            entry["output"] = "(no result)"

        entry["duration_ms"] = round(
            (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        )
        self.log.append(entry)
        print(f"  [AuditLog] {entry['agent']} — {entry['duration_ms']}ms"
              + (" [BLOCKED]" if entry.get("blocked") else ""))


async def main():
    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME"],
        credential=AzureCliCredential(),
    )

    audit_log = AuditLogMiddleware()

    agent = client.as_agent(
        name="GuardedAgent",
        instructions=(
            "You are an audit assistant. Only discuss audit and assurance topics. "
            "If asked about test data, you might mention sample SSN 123-45-6789 "
            "or email john.doe@example.com — but these should be caught by guardrails."
        ),
        # Middleware pipeline runs outermost → innermost:
        #   AuditLog → TopicGuard → PIIRedaction → Agent
        middleware=[
            audit_log,                  # Outermost: logs everything
            TopicGuardMiddleware(),     # Blocks off-topic requests
            PIIRedactionMiddleware(),   # Redacts PII from responses
        ],
    )

    output_lines: list[str] = []

    # Test 1: Normal audit question — passes all middleware
    print("=" * 60)
    print("Test 1: Normal audit question")
    print("=" * 60)
    result = await agent.run("What are the key steps in planning an audit engagement?")
    text = result.text if hasattr(result, "text") and result.text else str(result)
    print(f"Agent: {text}\n")
    output_lines.append(f"## Test 1: Normal Question\n\n{text}")

    # Test 2: Off-topic request — blocked by TopicGuardMiddleware
    print("=" * 60)
    print("Test 2: Off-topic request (blocked)")
    print("=" * 60)
    result = await agent.run("Can you give me some stock picks and investment recommendations?")
    text = result.text if hasattr(result, "text") and result.text else str(result)
    print(f"Agent: {text}\n")
    output_lines.append(f"## Test 2: Off-Topic (Blocked)\n\n{text}")

    # Test 3: Request that might produce PII — redacted by PIIRedactionMiddleware
    print("=" * 60)
    print("Test 3: PII redaction")
    print("=" * 60)
    result = await agent.run("Show me the test data with sample SSN and email for our test client.")
    text = result.text if hasattr(result, "text") and result.text else str(result)
    print(f"Agent: {text}\n")
    output_lines.append(f"## Test 3: PII Redaction\n\n{text}")

    # Print the audit log
    print("=" * 60)
    print("AUDIT LOG")
    print("=" * 60)
    log_lines: list[str] = []
    for entry in audit_log.log:
        blocked = " [BLOCKED]" if entry.get("blocked") else ""
        summary = f"  [{entry['timestamp']}] {entry['agent']}: {entry['input'][:60]}...{blocked}"
        print(summary)
        log_lines.append(f"- **{entry['agent']}** ({entry['duration_ms']}ms{blocked}): {entry['input'][:80]}...")

    # --- Write output ---
    os.makedirs("02-maf-agents/outputs", exist_ok=True)
    out_path = "02-maf-agents/outputs/05_guardrails.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# 05 — Guardrails (AgentMiddleware)\n\n")
        f.write("\n\n".join(output_lines))
        f.write("\n\n## Audit Log\n\n")
        f.write("\n".join(log_lines))
    print(f"\n✅ Output written to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())

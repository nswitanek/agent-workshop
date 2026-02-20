"""
05 — Implementing Guardrails and Safety Measures

Demonstrates MAF middleware for implementing guardrails:
  1. Input validation — blocks inappropriate or off-topic requests
  2. PII redaction — removes sensitive data from agent responses
  3. Audit logging — logs all agent interactions for compliance

Concepts: middleware, request/response interception, safety measures
"""

import asyncio
import os
import re
from datetime import datetime, timezone

from agent_framework import AgentRunMiddleware, RunContext
from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

load_dotenv()


# --- Guardrail 1: Input Validation Middleware ---
class TopicGuardMiddleware(AgentRunMiddleware):
    """Blocks requests that are off-topic for the assurance practice."""

    BLOCKED_TOPICS = ["personal advice", "stock picks", "investment recommendations"]

    async def invoke(self, context: RunContext, next_handler):
        user_input = context.input
        if isinstance(user_input, str):
            input_lower = user_input.lower()
            for topic in self.BLOCKED_TOPICS:
                if topic in input_lower:
                    # Short-circuit the agent — return a canned response
                    context.set_result(
                        f"I'm unable to help with {topic}. I'm designed to assist "
                        f"with audit and assurance topics only. Please consult the "
                        f"appropriate team for this request."
                    )
                    return

        # Input is acceptable — continue to the agent
        await next_handler(context)


# --- Guardrail 2: PII Redaction Middleware ---
class PIIRedactionMiddleware(AgentRunMiddleware):
    """Redacts common PII patterns (SSNs, emails) from agent responses."""

    PII_PATTERNS = [
        (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN REDACTED]"),
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL REDACTED]"),
        (r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b", "[CARD NUMBER REDACTED]"),
    ]

    async def invoke(self, context: RunContext, next_handler):
        # Let the agent run first
        await next_handler(context)

        # Redact PII from the response
        if context.result and hasattr(context.result, "text"):
            text = str(context.result)
            for pattern, replacement in self.PII_PATTERNS:
                text = re.sub(pattern, replacement, text)
            if text != str(context.result):
                print("[PIIRedactionMiddleware] PII detected and redacted from response.")
                context.set_result(text)


# --- Guardrail 3: Audit Logging Middleware ---
class AuditLogMiddleware(AgentRunMiddleware):
    """Logs all agent interactions for compliance audit trail."""

    def __init__(self):
        self.log: list[dict] = []

    async def invoke(self, context: RunContext, next_handler):
        start_time = datetime.now(timezone.utc)

        # Log the request
        entry = {
            "timestamp": start_time.isoformat(),
            "agent": context.agent.name if hasattr(context, "agent") else "unknown",
            "input": str(context.input)[:200],
        }

        await next_handler(context)

        # Log the response
        entry["output"] = str(context.result)[:200] if context.result else None
        entry["duration_ms"] = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        self.log.append(entry)
        print(f"[AuditLog] {entry['agent']}: {entry['duration_ms']:.0f}ms")


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
        middleware=[
            audit_log,              # Outermost: logs everything
            TopicGuardMiddleware(), # Blocks off-topic requests
            PIIRedactionMiddleware(), # Redacts PII from responses
        ],
    )

    # Test 1: Normal audit question — should pass through all middleware
    print("=" * 60)
    print("Test 1: Normal audit question")
    print("=" * 60)
    result = await agent.run("What are the key steps in planning an audit engagement?")
    print(f"Agent: {result}\n")

    # Test 2: Off-topic request — should be blocked by TopicGuardMiddleware
    print("=" * 60)
    print("Test 2: Off-topic request (blocked)")
    print("=" * 60)
    result = await agent.run("Can you give me some stock picks and investment recommendations?")
    print(f"Agent: {result}\n")

    # Test 3: Request that might produce PII — should be redacted
    print("=" * 60)
    print("Test 3: PII redaction")
    print("=" * 60)
    result = await agent.run("Show me the test data with sample SSN and email for our test client.")
    print(f"Agent: {result}\n")

    # Print the audit log
    print("=" * 60)
    print("AUDIT LOG")
    print("=" * 60)
    for entry in audit_log.log:
        print(f"  [{entry['timestamp']}] {entry['agent']}: {entry['input'][:60]}...")


if __name__ == "__main__":
    asyncio.run(main())

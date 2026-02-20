# Session 2: Code-First Agents with Microsoft Agent Framework

Build AI agents programmatically using the **Microsoft Agent Framework** (`agent-framework` SDK). These examples demonstrate MAF's key capabilities, themed around professional services / assurance practice.

## Examples

| # | File | Concept |
|---|------|---------|
| 1 | `01_intro_maf.py` | Introduction to MAF — hello agent |
| 2 | `02_orchestration.py` | Agent orchestration patterns (sequential, concurrent, handoff) |
| 3 | `03_custom_tools.py` | Building custom tools with `@tool` decorator |
| 4 | `04_memory.py` | Advanced memory management (context providers, session state) |
| 5 | `05_guardrails.py` | Implementing guardrails and safety measures (middleware) |

## Prerequisites

- Complete the [setup steps](../README.md#setup)
- Ensure your `.env` file has `AZURE_AI_PROJECT_ENDPOINT` and `AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME` configured

## Running the Examples

```bash
cd 02-maf-agents
python 01_intro_maf.py
```

## Key Concepts

- **AzureOpenAIResponsesClient** — client for Azure OpenAI Responses API
- **`as_agent()`** — converts a client into an agent with instructions and tools
- **`@tool` decorator** — defines function tools the agent can call
- **`BaseContextProvider`** — injects dynamic context and manages session state
- **Middleware** — intercepts agent requests/responses for guardrails, logging, etc.
- **Orchestration** — patterns for coordinating multiple agents (sequential, concurrent, handoff)

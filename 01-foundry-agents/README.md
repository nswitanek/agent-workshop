# Session 1: Building Agents in Microsoft Foundry

Build AI agents using the **Azure AI Foundry** platform and the `azure-ai-projects` Python SDK. Each example progressively introduces a core agent concept, themed around a professional services / assurance practice.

## Examples

| # | File | Concept |
|---|------|---------|
| 0 | [`00_portal_agent.md`](./00_portal_agent.md) | Creating an agent in the Azure AI Foundry portal |
| 1 | `01_first_agent.py` | Creating your first Foundry agent |
| 2 | `02_system_prompts.py` | Configuring instructions and system prompts |
| 3 | `03_knowledge.py` | Adding knowledge (file search, vector stores) |
| 4a | [`04_openapi_tools.md`](./04_openapi_tools.md) / `04_openapi_tools.py` | OpenAPI tools — upload the same specs from Copilot Studio (portal + SDK) |
| 4b | [`04_function_calling.md`](./04_function_calling.md) / `04_function_calling.py` | Function tools — SEC EDGAR + FRED APIs with full code control |
| 5 | [`05_conversation_state.md`](./05_conversation_state.md) / `05_conversation_state.py` | Threads and short-term conversation memory |
| 6 | [`06_memory.md`](./06_memory.md) / `06_memory.py` | Long-term memory with the Foundry Agent Memory Service (Preview) |
| 7 | [`07_evaluations.md`](./07_evaluations.md) / `07_evaluations.py` | Evaluating agents — quality, safety, and iterative improvement |

## Prerequisites

- Complete the [setup steps](../README.md#setup)
- Ensure your `.env` file has `PROJECT_ENDPOINT` and `MODEL_DEPLOYMENT_NAME` configured
- For Exercise 4 (Function Calling): A free [FRED API key](https://fred.stlouisfed.org/docs/api/api_key.html) — add `FRED_API_KEY` to your `.env`
- For Exercise 6 (Memory): An embedding model deployment — add `EMBEDDING_MODEL_DEPLOYMENT_NAME` to your `.env` (defaults to `text-embedding-3-small`)
- For Exercise 7 (Evaluations): `pip install azure-ai-evaluation` and enough model quota for ~70 LLM calls per eval run

## Running the Examples

```bash
# From the repo root
cd 01-foundry-agents
python 01_first_agent.py
```

## Key Concepts

- **AIProjectClient** — the main entry point for interacting with Azure AI Foundry
- **Agents** — AI assistants created with a model, instructions, and optional tools
- **Threads** — conversation containers that maintain message history
- **Runs** — execution of an agent against a thread to generate responses
- **Tools** — capabilities you attach to agents (file search, code interpreter, functions)

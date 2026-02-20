# Session 1: Building Agents in Microsoft Foundry

Build AI agents using the **Azure AI Foundry** platform and the `azure-ai-projects` Python SDK. Each example progressively introduces a core agent concept, themed around a professional services / assurance practice.

## Examples

| # | File | Concept |
|---|------|---------|
| 1 | `01_first_agent.py` | Creating your first Foundry agent |
| 2 | `02_system_prompts.py` | Configuring instructions and system prompts |
| 3 | `03_knowledge.py` | Adding knowledge (file search, vector stores) |
| 4 | `04_function_calling.py` | Implementing tools and function calling |
| 5 | `05_conversation_state.py` | Working with memory and conversation state |

## Prerequisites

- Complete the [setup steps](../README.md#setup)
- Ensure your `.env` file has `PROJECT_ENDPOINT` and `MODEL_DEPLOYMENT_NAME` configured

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

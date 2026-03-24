# Environment Setup & Prerequisites

Complete this checklist **before** the workshop to ensure your environment is ready.

## Azure Access

- [ ] Azure subscription is active — verify with `az account show`
- [ ] You have one of the following RBAC roles on the **AI Services resource** (check Azure portal → AI Services resource → Access control / IAM):
  - **Azure AI Developer** (data-plane access — required for creating agents)
  - **Cognitive Services Contributor** (control-plane + data-plane)
  - **Owner** (subscription-level, includes all)
- [ ] You have **Storage Blob Data Contributor** on the project's storage account (required for evaluation portal uploads in Exercise 07)

> **Note:** The generic **Contributor** role alone is NOT sufficient — it only grants control-plane access. You need a **data-plane** role (Azure AI Developer or Cognitive Services Contributor) to create and use agents.

### Authentication

All workshop scripts use **Azure CLI** authentication. Run `az login` before running any scripts.

> If you don't have an Azure account, [create a free one](https://azure.microsoft.com/free/) which includes a free trial subscription.

## Azure AI Foundry Resources

Ensure the following are provisioned in your Azure subscription:

- [ ] Foundry project created and accessible
- [ ] Model deployments (verify in the Foundry portal or with `az cognitiveservices account deployment list`):
  - [ ] **gpt-5-mini** (or gpt-5.2) — primary agent model
  - [ ] **gpt-4.1** — used by evaluation framework (LLM-as-judge)
  - [ ] **gpt-4o** — used by portal agents and memory store
  - [ ] **text-embedding-3-small** — used by knowledge stores and memory
- [ ] Azure AI Search resource (used for knowledge/vector store in Exercise 03)

## External API Keys

- [ ] **FRED API key** (free) — register at [fred.stlouisfed.org/docs/api/api_key.html](https://fred.stlouisfed.org/docs/api/api_key.html)
  - Used in Exercise 04 (OpenAPI tools and function calling)
  - Registration takes ~2 minutes

## Platform Access

- [ ] Microsoft 365 account
- [ ] Microsoft Copilot Studio access (requires M365 license with Copilot Studio entitlement)
- [ ] GitHub account
- [ ] GitHub Copilot access

## Development Environment

### Required Software

- [ ] **Python 3.10+** — verify with `python --version`
- [ ] **Git** client installed and configured
- [ ] **Azure CLI** — verify with `az --version`
- [ ] **VS Code** (latest version)
  - [ ] Copilot Studio extension for VS Code

### Environment Variables

Copy `.env.example` to `.env` and fill in your values. Key variables:

| Variable | Where to find it | Used by |
|----------|------------------|---------|
| `PROJECT_ENDPOINT` | Foundry portal → Project → Overview | Exercises 01–07 |
| `MODEL_DEPLOYMENT_NAME` | Foundry portal → Deployments | Exercises 01–07 |
| `AZURE_AI_PROJECT_ENDPOINT` | Same as PROJECT_ENDPOINT | MAF exercises, Capstone |
| `AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME` | Same as MODEL_DEPLOYMENT_NAME | MAF exercises |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME` | Foundry portal → Deployments | Exercises 03, 06 |
| `EVAL_MODEL_DEPLOYMENT_NAME` | Default: `gpt-4.1` | Exercise 07 |
| `FRED_API_KEY` | FRED registration (see above) | Exercise 04 |
| `PARTICIPANT_INITIALS` | Your initials (e.g., `NS`) | Exercise 07 (namespacing) |

### Quick Verification

```bash
python3 --version        # Should be ≥ 3.10
az --version
az login
az account show          # Should show your active subscription

# Install dependencies
pip install -r requirements.txt

# Verify imports work
python3 -c "from azure.ai.agents import AgentsClient; print('✓ azure-ai-agents')"
python3 -c "from azure.ai.evaluation import evaluate; print('✓ azure-ai-evaluation')"
python3 -c "from agent_framework import ContextProvider; print('✓ agent-framework')"

# Quick smoke test (creates an agent, asks one question, deletes agent)
python3 01-foundry-agents/01_first_agent.py
```

## Next Steps

Once everything checks out, follow the [Setup instructions in the README](./README.md#setup) to clone the repo, create a virtual environment, and install dependencies.

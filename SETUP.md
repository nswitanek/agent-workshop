# Workshop Environment Setup

This document has two parts:
1. **Azure Admin Setup** — Infrastructure provisioning and configuration (done once)
2. **Participant Setup** — What each participant does on their own machine

---

# Part 1: Azure Admin Setup

Prepare the shared Azure environment for ~30 workshop participants.

## 1.1 Provision Azure AI Foundry Resources

### Foundry Project

- [ ] Create an **Azure AI Services** resource (or use an existing one)
- [ ] Create a **Foundry project** within that resource
- [ ] Note the **project endpoint** — participants will need this for their `.env` file:
  ```
  https://<your-resource>.services.ai.azure.com/api/projects/<your-project>
  ```

### Model Deployments

Deploy the following models in the Foundry project. Use **GlobalStandard** SKU for highest throughput. The capacity column assumes ~30 concurrent participants.

| Deployment Name | Model | Min Capacity (TPM, thousands) | Purpose |
|----------------|-------|-------------------------------|---------|
| `gpt-5-mini` | gpt-5-mini | **1000** | Primary agent model (all exercises) |
| `gpt-4.1` | gpt-4.1 | **400+** | Evaluation LLM-as-judge (Exercise 07) |
| `gpt-4o` | gpt-4o | **200+** | Portal agents, memory store chat model |
| `text-embedding-3-small` | text-embedding-3-small | **120+** | Knowledge stores, memory embeddings |

```bash
# Example: deploy gpt-5-mini with 1000K TPM
az cognitiveservices account deployment create \
  --name <foundry-resource> \
  --resource-group <resource-group> \
  --deployment-name gpt-5-mini \
  --model-name gpt-5-mini \
  --model-version <latest-version> \
  --model-format OpenAI \
  --sku-name GlobalStandard \
  --sku-capacity 1000

# Verify all deployments
az cognitiveservices account deployment list \
  --name <foundry-resource> \
  --resource-group <resource-group> \
  --query "[].{name:name, model:properties.model.name, capacity:sku.capacity}" -o table
```

> **Why separate models?** Exercise 07 (evaluations) runs ~60 LLM-as-judge calls per participant per eval run. Using the same model for both agent and evaluator causes rate-limit contention. Splitting across `gpt-5-mini` (agent) and `gpt-4.1` (evaluator) avoids this.

### Azure AI Search

- [ ] Create an **Azure AI Search** resource in the same region
  - Used by Exercise 03 (knowledge/vector store)
  - Free tier is sufficient for the workshop

### Storage Account

The Foundry project uses a linked storage account for evaluation result uploads (Exercises 07 and 07b). Both the client-side SDK (`azure-ai-evaluation`) and the server-side API (`openai.evals`) upload results via **SAS tokens** derived from storage account keys.

- [ ] **`allowSharedKeyAccess`** — Must be `true`. If enforced to `false` by Azure Policy or Defender, **portal uploads will fail** for both exercises. The scripts fall back to local-only results automatically.

```bash
az storage account show --name <storage-account> --resource-group <resource-group> \
  --query "allowSharedKeyAccess" -o tsv
```

- [ ] **Network access** — The client-side SDK uploads from participant machines. If `publicNetworkAccess=Disabled` or `defaultAction=Deny`, add the workshop venue's public IP range:

```bash
# Check current network access
az storage account show --name <storage-account> --resource-group <resource-group> \
  --query "{publicAccess:publicNetworkAccess, defaultAction:networkRuleSet.defaultAction, allowSharedKeyAccess:allowSharedKeyAccess}" -o json

# Add venue IP range (required if defaultAction=Deny)
az storage account network-rule add --account-name <storage-account> \
  --resource-group <resource-group> --ip-address <venue-public-ip-or-cidr>
```

> **If `allowSharedKeyAccess` cannot be enabled:** Participants can still run evaluations — results are saved locally to `outputs/` and printed to console. They just won't appear in the Foundry portal. The `compare` command (`python 07_evaluations.py compare`) works entirely from local files.

## 1.2 RBAC — Participant Permissions

Each participant needs two role assignments. These can be assigned to an AAD group containing all participants.

### Required: Agent Data-Plane Access

```bash
az role assignment create \
  --assignee "<participant-email-or-group-id>" \
  --role "Azure AI Developer" \
  --scope "/subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<foundry-resource>"
```

> **Why not just Contributor?** The generic Contributor role only grants control-plane access. `Azure AI Developer` (or `Cognitive Services Contributor`) is required for data-plane operations — creating agents, threads, running evaluations.

### Required: Evaluation Portal Uploads (Exercise 07)

```bash
az role assignment create \
  --assignee "<participant-email-or-group-id>" \
  --role "Storage Blob Data Contributor" \
  --scope "/subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.Storage/storageAccounts/<storage-account>"
```

## 1.3 Azure OpenAI Connection

The Foundry project needs a **default Azure OpenAI connection** so agents can access model deployments.

- [ ] Verify at least one `AzureOpenAI` connection exists and is marked as default
- [ ] If the OpenAI resource has `disableLocalAuth=true`, the connection **must** use **Entra ID (AAD)** auth (not API key)

```bash
# List connections
az rest --method GET \
  --url "/subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<foundry-resource>/projects/<project>/connections?api-version=2025-04-01-preview" \
  --query "value[?properties.category=='AzureOpenAI'].{name:name, auth:properties.authType, default:properties.isDefault}" -o table
```

If no default exists, create one pointing to the Foundry resource itself:

```bash
az rest --method PUT \
  --url "/subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<foundry-resource>/projects/<project>/connections/default-openai?api-version=2025-04-01-preview" \
  --body '{
    "properties": {
      "authType": "AAD",
      "category": "AzureOpenAI",
      "target": "https://<foundry-resource>.cognitiveservices.azure.com/",
      "isSharedToAll": true,
      "isDefault": true,
      "metadata": {"ApiType": "Azure"}
    }
  }'
```

## 1.4 Managed Identity

The Foundry resource's **system-assigned managed identity** is used by the Foundry backend for server-side operations — memory service, agent execution, and evaluations. Several exercises depend on it.

- [ ] Enable **system-assigned managed identity** on the Foundry resource:
  - Portal → Foundry resource → **Resource Management** → **Identity** → **System assigned** → **On**

### MI Roles for Agent & Memory Service (Exercises 05, 06)

The managed identity needs access to model deployments so the Foundry backend can run agents and the memory service.

```bash
MI_ID=$(az cognitiveservices account show \
  --name <foundry-resource> --resource-group <rg> \
  --query "identity.principalId" -o tsv)

az role assignment create --assignee "$MI_ID" \
  --role "Azure AI User" \
  --scope "/subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<foundry-resource>"

az role assignment create --assignee "$MI_ID" \
  --role "Cognitive Services OpenAI User" \
  --scope "/subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<foundry-resource>"
```

> **Known limitation (Exercise 06):** The Foundry Memory Service is a preview feature. If `disableLocalAuth=true` is enforced by policy on the Cognitive Services resource, the memory service may fail with "Authentication failed" even with correct RBAC. Exercise 06b (MAF, file-based memory) is provided as a working alternative.

### MI Roles for Server-Side Evaluations (Exercise 07b)

Exercise 07b uses the `azure-ai-projects` SDK's OpenAI-compatible evals API (`openai.evals.*`), which runs evaluations **server-side** on the Foundry backend — unlike Exercise 07's `azure-ai-evaluation` SDK, which runs evaluators locally on the participant's machine.

The Foundry eval backend (`raisvc`) writes results to blob storage. This requires **two things**:

1. The project's managed identity needs `Storage Blob Data Contributor` on the project's storage account.
2. The storage account must have **`allowSharedKeyAccess=true`** — the `raisvc` generates SAS tokens from account keys.

> **⚠️ Known limitation:** If `allowSharedKeyAccess` is enforced to `false` by Azure Policy, Defender, or the ML workspace, Exercise 07b's server-side evals **will not work**. Use Exercise 07 (client-side evals) instead — it authenticates via Entra ID and works regardless of shared key settings. See `07b_TROUBLESHOOTING.md` for details.

- [ ] Check `allowSharedKeyAccess` on the project storage:

```bash
az storage account show --name <storage-account> --resource-group <rg> \
  --query "allowSharedKeyAccess" -o tsv
```

If this returns `false` and cannot be changed, **skip Exercise 07b** — participants should use Exercise 07 instead. Both produce portal-visible evaluation results.

- [ ] If `allowSharedKeyAccess=true`, assign `Storage Blob Data Contributor` to the MI:

```bash
MI_ID=$(az cognitiveservices account show \
  --name <foundry-resource> --resource-group <rg> \
  --query "identity.principalId" -o tsv)

az role assignment create --assignee "$MI_ID" \
  --role "Storage Blob Data Contributor" \
  --scope "/subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.Storage/storageAccounts/<storage-account>"
```

> **Note:** This is separate from the participant-level `Storage Blob Data Contributor` in section 1.2 (needed for Exercise 07's client-side portal uploads). The MI assignment here is for the Foundry backend itself. Role propagation typically takes 1–5 minutes.

### MI Role Summary

| Resource | Role | Purpose |
|----------|------|---------|
| Foundry resource | Azure AI User | Agent/memory backend access |
| Foundry resource | Cognitive Services OpenAI User | Model deployment access |
| Storage account(s) | Storage Blob Data Contributor | Server-side eval result storage |

### Verify MI Roles

```bash
MI_ID=$(az cognitiveservices account show \
  --name <foundry-resource> --resource-group <rg> \
  --query "identity.principalId" -o tsv)

az role assignment list --assignee "$MI_ID" --all \
  --query "[].{role:roleDefinitionName, scope:scope}" -o table
```

### Check: `disableLocalAuth` Policy

```bash
az cognitiveservices account show --name <foundry-resource> --resource-group <rg> \
  --query "properties.disableLocalAuth" -o tsv
```

If this returns `true` and cannot be changed, participants should use **Exercise 06b** (MAF file-based memory) instead of Exercise 06.

## 1.5 FRED API Key (Exercise 04)

No admin setup required — each participant registers for their own free FRED API key and adds it to their `.env` as `FRED_API_KEY`. Participants who use the portal OpenAPI tool flow will create their own connection as part of the exercise.

> FRED API keys are free: [fred.stlouisfed.org/docs/api/api_key.html](https://fred.stlouisfed.org/docs/api/api_key.html)

## 1.6 Admin Verification Checklist

Run this script after completing setup (fill in your resource names at the top):

```bash
RESOURCE=<foundry-resource>
RG=<resource-group>
STORAGE=<storage-account>

echo "=== 1. Model Deployments ==="
az cognitiveservices account deployment list --name $RESOURCE --resource-group $RG \
  --query "[].{name:name, capacity:sku.capacity}" -o table

echo ""
echo "=== 2. Storage Network Access ==="
az storage account show --name $STORAGE --resource-group $RG \
  --query "{publicAccess:publicNetworkAccess, bypass:networkRuleSet.bypass, allowSharedKeyAccess:allowSharedKeyAccess}" -o json

echo ""
echo "=== 3. Managed Identity ==="
MI_ID=$(az cognitiveservices account show --name $RESOURCE --resource-group $RG \
  --query "identity.principalId" -o tsv)
echo "Principal ID: $MI_ID"
az role assignment list --assignee "$MI_ID" --all \
  --query "[].roleDefinitionName" -o tsv

echo ""
echo "=== 4. disableLocalAuth ==="
az cognitiveservices account show --name $RESOURCE --resource-group $RG \
  --query "properties.disableLocalAuth" -o tsv

echo ""
echo "=== 5. OpenAI Connections ==="
az rest --method GET \
  --url "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RG/providers/Microsoft.CognitiveServices/accounts/$RESOURCE/projects/*/connections?api-version=2025-04-01-preview" \
  --query "value[?properties.category=='AzureOpenAI'].{name:name, auth:properties.authType, default:properties.isDefault}" -o table 2>/dev/null || echo "(check connections in portal)"
```

Expected results:
- 4 model deployments with capacity ≥ listed minimums
- Storage: public access enabled or venue IP whitelisted; `allowSharedKeyAccess=true` if using Exercise 07b
- Managed identity: Azure AI User + Cognitive Services OpenAI User (on Foundry resource) + Storage Blob Data Contributor (on storage, for 07b)
- disableLocalAuth: `false` (preferred) or `true` (exercise 06 will use file-based alternative)
- At least one AzureOpenAI connection with `isDefault=true`

---

# Part 2: Participant Setup

Complete this before the workshop.

## 2.1 Required Software

- [ ] **Python 3.10+** — `python --version`
- [ ] **uv** — fast Python package manager (recommended) — `uv --version`
- [ ] **Git** — `git --version`
- [ ] **Azure CLI** — `az --version`
- [ ] **VS Code** with Copilot Studio extension

### Install uv

**uv** is a fast Python package and environment manager. It replaces `pip` + `venv` with a single tool that's 10–100× faster.

macOS / Linux:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows (PowerShell):
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Verify:
```bash
uv --version   # Should print uv 0.x.x or later
```

> **Alternative:** If you prefer not to install uv, you can use standard `pip` + `venv` instead — instructions are provided alongside the uv commands below.

## 2.2 Azure Authentication

```bash
az login
az account show  # Should show the workshop subscription
```

## 2.3 External API Keys

- [ ] **FRED API key** (free, ~2 min): [fred.stlouisfed.org/docs/api/api_key.html](https://fred.stlouisfed.org/docs/api/api_key.html)

## 2.4 Platform Access

- [ ] Microsoft 365 account with Copilot Studio access
- [ ] GitHub account with GitHub Copilot access

## 2.5 Repository Setup

```bash
git clone <repo-url>
cd agent-workshop
```

### With uv (recommended)

macOS / Linux:
```bash
uv venv
source .venv/bin/activate
uv pip install --pre -r requirements.txt
```

Windows PowerShell:
```powershell
uv venv
.venv\Scripts\Activate.ps1
uv pip install --pre -r requirements.txt
```

### With pip + venv (alternative)

macOS / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell:
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> **Note:** The `--pre` flag (used with uv) allows installing pre-release packages, which some workshop dependencies require.

### Switching Python versions (uv)

If you need a specific Python version (e.g., 3.12), you can recreate the virtual environment:

macOS / Linux:
```bash
uv python install 3.12
rm -rf .venv
uv venv --python 3.12
source .venv/bin/activate
uv pip install --pre -r requirements.txt
```

Windows PowerShell:
```powershell
uv python install 3.12
Remove-Item -Recurse -Force .venv
uv venv --python 3.12
.venv\Scripts\Activate.ps1
uv pip install --pre -r requirements.txt
```

## 2.6 Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your values (your admin will provide the endpoint and deployment names):

| Variable | Where to find it | Required |
|----------|------------------|----------|
| `PARTICIPANT_INITIALS` | Your initials (e.g., `NS`) | Yes |
| `PROJECT_ENDPOINT` | Provided by admin | Yes |
| `MODEL_DEPLOYMENT_NAME` | Provided by admin (e.g., `gpt-5-mini`) | Yes |
| `AZURE_AI_PROJECT_ENDPOINT` | Same as `PROJECT_ENDPOINT` | Yes |
| `AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME` | Same as `MODEL_DEPLOYMENT_NAME` | Yes |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME` | Default: `text-embedding-3-small` | For exercises 03, 06 |
| `EVAL_MODEL_DEPLOYMENT_NAME` | Default: `gpt-4.1` | For exercise 07 |
| `FRED_API_KEY` | Your FRED registration | For exercise 04 |

## 2.7 Verification

```bash
# Verify imports
python3 -c "from azure.ai.agents import AgentsClient; print('✓ azure-ai-agents')"
python3 -c "from azure.ai.evaluation import evaluate; print('✓ azure-ai-evaluation')"
python3 -c "from agent_framework import ContextProvider; print('✓ agent-framework')"

# Verify .env
python3 -c "
from dotenv import load_dotenv; load_dotenv(); import os
for v in ['PROJECT_ENDPOINT','MODEL_DEPLOYMENT_NAME','AZURE_AI_PROJECT_ENDPOINT']:
    val = os.environ.get(v,'NOT SET')
    ok = '✓' if val not in ('NOT SET','') and '<' not in val else '✗'
    print(f'  {ok} {v}')
"

# Smoke test — creates an agent, asks one question, deletes the agent
python3 01-foundry-agents/01_first_agent.py
```

If the smoke test produces an agent response, you're ready for the workshop.

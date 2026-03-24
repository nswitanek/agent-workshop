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

The Foundry project uses a linked storage account for evaluation result uploads.

- [ ] Identify the storage account linked to the Foundry project
- [ ] **Network access**: The evaluation SDK uploads results from participant machines directly to blob storage. If the storage account has **public network access disabled**, uploads will fail. Options:
  - **(Recommended)** Add a network rule for the workshop venue's public IP range
  - Or enable public network access during the workshop
  - Or accept that participants won't see eval results in the Foundry portal (the script falls back to local results automatically)

```bash
# Check current network access
az storage account show --name <storage-account> --resource-group <resource-group> \
  --query "{publicAccess:publicNetworkAccess, bypass:networkRuleSet.bypass}" -o json

# Option A: Add venue IP range (recommended)
az storage account network-rule add --account-name <storage-account> \
  --resource-group <resource-group> --ip-address <venue-public-ip-or-cidr>

# Option B: Enable public access
az storage account update --name <storage-account> --resource-group <resource-group> \
  --public-network-access Enabled
```

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

## 1.4 Managed Identity (for Memory Service — Exercise 06)

The Foundry Memory Service is a **preview feature** that runs server-side. It needs the Foundry resource's managed identity to access model deployments.

> **Known limitation:** If `disableLocalAuth=true` is enforced by policy on the Cognitive Services resource, the memory service may fail with "Authentication failed" even with correct RBAC. Exercise 06b (MAF, file-based memory) is provided as a working alternative.

- [ ] Enable **system-assigned managed identity** on the Foundry resource:
  - Portal → Foundry resource → **Resource Management** → **Identity** → **System assigned** → **On**

- [ ] Assign roles to the managed identity:

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
  --query "{publicAccess:publicNetworkAccess, bypass:networkRuleSet.bypass}" -o json

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
- Storage: public access enabled or venue IP whitelisted
- Managed identity: Azure AI User + Cognitive Services OpenAI User
- disableLocalAuth: `false` (preferred) or `true` (exercise 06 will use file-based alternative)
- At least one AzureOpenAI connection with `isDefault=true`

---

# Part 2: Participant Setup

Complete this before the workshop.

## 2.1 Required Software

- [ ] **Python 3.10+** — `python --version`
- [ ] **Git** — `git --version`
- [ ] **Azure CLI** — `az --version`
- [ ] **VS Code** with Copilot Studio extension

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
pip install -r requirements.txt
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

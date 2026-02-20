# Environment Setup & Prerequisites

Complete this checklist **before** the workshop to ensure your environment is ready.

## Azure Access

- [ ] Azure subscription is active — verify with `az account show`
- [ ] You have one of the following RBAC roles on the Foundry resource (check Azure portal → Foundry resource → Access control / IAM):
  - **Azure AI User** (least-privilege, sufficient for development)
  - **Azure AI Project Manager** (for managing projects)
  - **Contributor** or **Owner** (subscription-level)

> If you don't have an Azure account, [create a free one](https://azure.microsoft.com/free/) which includes a free trial subscription.

## Azure AI Foundry Resources

Ensure the following are provisioned in your Azure subscription:

- [ ] Foundry project created and accessible
- [ ] Azure OpenAI model deployed (e.g., `gpt-4o`)
- [ ] Azure AI Search resource (used for knowledge/vector store exercises)
- [ ] *(Optional)* Container Apps or App Service (for deployment exercises)

## Platform Access

- [ ] Microsoft 365 account
- [ ] Microsoft Copilot Studio access (requires M365 license with Copilot Studio entitlement)
- [ ] GitHub account with GitHub Actions enabled
- [ ] GitHub Copilot access

## Development Environment

### Required Software

- [ ] **Python 3.10+** — verify with `python --version`
- [ ] **Git** client installed and configured
- [ ] **Azure CLI** — verify with `az --version`
- [ ] **VS Code** (latest version)
  - [ ] Copilot Studio extension for VS Code

### Quick Verification

Run these commands to confirm your environment is ready:

```bash
# Check Python
python --version        # Should be ≥ 3.10

# Check Azure CLI and login
az --version
az login
az account show         # Should show your active subscription

# Check Git
git --version

# Check RBAC role (replace <resource-group> and <foundry-resource>)
az role assignment list --resource-group <resource-group> --query "[].roleDefinitionName" -o tsv
```

## Next Steps

Once everything checks out, follow the [Setup instructions in the README](./README.md#setup) to clone the repo, create a virtual environment, and install dependencies.

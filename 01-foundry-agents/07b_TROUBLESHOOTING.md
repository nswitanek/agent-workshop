# Troubleshooting: 07b Server-Side Evaluations (Projects SDK)

This document records the investigation into `ProjectMIUnauthorized` / `AuthorizationFailure` errors when running `07b_evaluations_projects_sdk.py`.

## Error

When calling `openai_client.evals.runs.create()`, the Foundry eval backend (`raisvc`) fails with:

```
openai.AuthenticationError: 401 — "The project mi lacks the required action …
ErrorCode: AuthorizationFailure … ProjectMIUnauthorized"
```

The inner 403 comes from Azure Storage (identified by `x-ms-request-id` format and error structure). The `raisvc` component wraps the storage error in a `ProjectMIUnauthorized` message.

## Root Cause

The project's storage account (`stblueskyfou835057564988`) has **`allowSharedKeyAccess=false`**, enforced by the Azure ML workspace defaults or Microsoft Defender for Storage. The Foundry eval backend (`raisvc`) uses SAS tokens (derived from storage account keys) to write eval results. When shared key access is disabled, these SAS tokens are rejected.

This is a **product limitation**: the `raisvc` does not currently support User Delegation SAS or pure Entra ID–based data-plane access for eval result storage.

## What Was Tried (and Why It Didn't Help)

### RBAC Role Assignments

`Storage Blob Data Contributor` was assigned to **all five identities** associated with the Foundry project on **all four storage accounts** in the environment:

| Identity | Principal ID | Type |
|----------|-------------|------|
| Foundry resource MI | `f5f1c096-e066-4fad-9e72-b877b50b1d5a` | System-Assigned MI on `bluesky-foundry-resource` |
| Foundry project MI | `b966f150-82a0-4db9-b0da-6b95b4159efd` | System-Assigned MI on `bluesky-foundry` project |
| Agent Identity | `84ab7388-37df-4f94-8b39-0d8ff9d07561` | `ServiceIdentity` for the project |
| Agent Blueprint SP | `ed214288-44fc-4f92-b0ff-2c0e7ffae889` | `AgentIdentityBlueprint` app registration |
| Project Dev MI | `dd711901-5776-4068-9acb-7d8ecfe5359b` | System-Assigned MI on `bluesky-foundry-project-dev-reso` |

**Why it didn't help:** The `raisvc` accesses storage via SAS tokens from account keys, not via MI + RBAC. The RBAC roles are irrelevant when `allowSharedKeyAccess=false` blocks key-based auth.

### Azure AI User Role

`Azure AI User` was assigned to all five identities on the Foundry resource itself. This is the documented minimum requirement per [aka.ms/FoundryPermissions](https://aka.ms/FoundryPermissions).

**Why it didn't help:** Same root cause — the storage-level auth fails before any Foundry-level role is checked.

### Storage Network Configuration

All storage accounts were changed from `publicNetworkAccess=Disabled` to:

```json
{
  "publicNetworkAccess": "Enabled",
  "networkRuleSet": {
    "defaultAction": "Deny",
    "bypass": "AzureServices"
  }
}
```

This keeps storage private (no public internet access) while allowing trusted Azure services.

**Why it didn't help (alone):** Network access is now allowed for Azure services, but the auth mechanism (SAS from account keys) is still blocked by `allowSharedKeyAccess=false`.

### Resource Access Rules

Resource instance rules were added on storage accounts for both Foundry Cognitive Services resources:

```bash
az storage account network-rule add \
  --account-name <storage> --resource-group <rg> \
  --resource-id "<foundry-resource-id>" \
  --tenant-id "<tenant-id>"
```

**Why it didn't help:** Resource access rules control network-level access, not auth-level access. The `allowSharedKeyAccess=false` blocks auth regardless of network rules.

### Enabling `allowSharedKeyAccess`

```bash
az storage account update --name stblueskyfou835057564988 --resource-group bluesky-ai-rg \
  --allow-shared-key-access true
```

Command reported success but the value remained `false`. This is silently enforced by the Azure ML workspace or a Defender policy. No explicit Azure Policy `deny` was found — the enforcement appears to be at the workspace/platform level.

### `userOwnedStorage` on Foundry Resource

```bash
az cognitiveservices account update --name bluesky-foundry-resource \
  --resource-group bluesky-ai-rg \
  --storage '[{"resourceId":"<storage-resource-id>"}]'
```

**Failed:** `UserOwnedStorageCanOnlyBeAttachedWhileCreation` — this property can only be set at resource creation time.

## Resolution Options

1. **Use `07_evaluations.py` (Exercise 07) instead** — Runs evaluators client-side via `azure-ai-evaluation`. Avoids the `raisvc` entirely. Results can be uploaded to the Foundry portal separately.

2. **Recreate the Foundry resource** with `userOwnedStorage` pointing to a new storage account that has `allowSharedKeyAccess=true`.

3. **File a feature request** with the Azure AI Foundry team to support User Delegation SAS or pure Entra ID data-plane auth in the `raisvc` eval backend, so it works with `allowSharedKeyAccess=false`.

## Environment Details

- **Foundry resource:** `bluesky-foundry-resource` (eastus2)
- **Foundry project:** `bluesky-foundry`
- **Project storage:** `stblueskyfou835057564988` (bluesky-ai-rg)
- **Connected storage:** `adlsbluesky` (aiml-rg)
- **ML workspaces:** `bluesky-foundry-hub`, `bluesky-foundry-hub-project`
- **Date investigated:** 2026-03-25

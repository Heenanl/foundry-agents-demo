# Deployment — Azure infrastructure for the Magentic RFP demo

This folder uses [Azure Developer CLI (`azd`)](https://aka.ms/azd-install) and Bicep to provision everything the workflow needs in your subscription.

## What gets deployed

[main.bicep](main.bicep) → [resources.bicep](resources.bicep) creates a single resource group containing:

| Resource | Purpose |
|---|---|
| **Azure AI Foundry** (Cognitive Services `AIServices`) | Hosts the four agents and the GPT model |
| **Model deployment** (`gpt-4o-mini`) | LLM used by all agents |
| **Azure AI Search** (Standard tier) | Stores the RFP documents for grounding |
| **Azure Storage** (StorageV2) | Backing storage for Foundry / Search |
| **RBAC role assignments** | Foundry → Storage (Blob/Table/Queue Data Contributor) and Foundry → Search (Index Data Contributor + Service Contributor) |

> ⚠️ **Note:** This template does **not yet** deploy a Foundry **Project** or the four agents themselves — those must be created manually in the Foundry portal after `azd up` finishes. See the root [README.md](../README.md) for agent setup steps.

## Prerequisites

- [Azure CLI](https://aka.ms/azcli) (`az --version`)
- [Azure Developer CLI](https://aka.ms/azd-install) (`azd version`)
- Owner or Contributor + User Access Administrator on the target subscription (RBAC role assignments require it)

## Deploy

```powershell
# From the deployment/ folder

# 1. Sign in
azd auth login
#   --tenant-id <your-tenant-id>     # if your tenant isn't the default
#   --use-device-code                # if browser auth is blocked

# 2. Create a new azd environment
azd env new "<your-env-name>" --location "eastus"
# Allowed locations: uaenorth, southafricanorth, westeurope, southcentralus,
# australiaeast, canadaeast, eastus, eastus2, francecentral, japaneast,
# northcentralus, swedencentral, switzerlandnorth, uksouth

# 3. Provision
azd up
```

`azd up` shows the resource group name and resource endpoints when it finishes.

## Wire outputs into `.env`

Copy `azd up` outputs (or grab them anytime with `azd env get-values`) into the project root `.env` file. At minimum:

```
AZURE_AI_PROJECT_ENDPOINT=<aiFoundryEndpoint output>/api/projects/<your-project-name>
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o-mini
```

See [.env.example](../.env.example) for the full list.

## Tear down

```powershell
azd down --purge --force
```

`--purge` permanently removes the soft-deleted Cognitive Services account so the same name can be reused.

## Customizing

- **Different region / SKU:** edit [main.bicepparam](main.bicepparam) or pass `--location` when creating the env.
- **Different model:** edit `gpt4oMiniDeployment` in [resources.bicep](resources.bicep).
- **Naming:** resources are named `<prefix>-<environmentName>-<uniqueSuffix>`. Change the prefixes in `resources.bicep` if you have org naming requirements.

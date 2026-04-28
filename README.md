# Multi-Agent RFP Analysis with Azure AI Foundry

A reference implementation showing how to use the **Magentic orchestration pattern** from the [Microsoft Agent Framework](https://learn.microsoft.com/agent-framework/) to coordinate multiple specialist agents hosted in **Azure AI Foundry** for analyzing RFP (Request for Proposal) documents.

The orchestrator agent plans, delegates work to three specialists, and synthesizes their findings into a single comprehensive report — exposed through a React UI with live progress streaming over Server-Sent Events.

---

## Architecture

```
                    ┌──────────────────────┐
                    │   React Frontend     │  http://localhost:3000/magentic
                    │   (MagenticWorkflow) │
                    └──────────┬───────────┘
                               │ SSE
                    ┌──────────▼───────────┐
                    │  FastAPI Backend     │  http://localhost:8000
                    │  /api/magentic/...   │
                    └──────────┬───────────┘
                               │  Magentic workflow
                    ┌──────────▼───────────┐
                    │  RfpOrchestrator     │  Plans, delegates, synthesizes
                    └──────────┬───────────┘
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
     ┌────────────────┐┌────────────────┐┌────────────────┐
     │ RfpSummary     ││ RfpRisk        ││ RfpCompliance  │
     │ Agent          ││ Agent          ││ Agent          │
     └───────┬────────┘└───────┬────────┘└───────┬────────┘
             │                 │                 │
             └─────── Azure AI Search (RAG) ─────┘
                  (RFP documents indexed here)
```

All four agents are **Foundry-hosted** (created in the Azure AI Foundry portal). Each specialist uses Azure AI Search grounding to retrieve RFP content from indexed documents.

---

## Repository Layout

```
.
├── magentic_rfp_workflow.py      # Core Magentic orchestration logic
├── webapp/
│   ├── backend/
│   │   ├── api.py                 # FastAPI server (REST + SSE streaming)
│   │   └── requirements.txt
│   └── frontend/                  # React app (CRA)
│       └── src/MagenticWorkflow.js
├── deployment/                    # azd / Bicep — Azure infrastructure
│   ├── azure.yaml
│   ├── main.bicep
│   ├── resources.bicep
│   └── README.md
├── scripts/                       # Agent evaluation pipeline (CI)
│   ├── action.py
│   └── analysis/
├── data/
│   ├── rfp-*-evaluation.json      # Eval datasets
│   └── sample-rfps/               # Sample PDFs to index in Azure AI Search
├── .github/workflows/
│   └── rfp-evaluation.yml         # Automated agent evaluation
├── .env.example                   # Template — copy to .env and fill in
└── README.md
```

---

## Prerequisites

| Tool | Why | Install |
|------|-----|---------|
| Python 3.11+ | Backend & workflow | https://www.python.org |
| Node.js 18+ | Frontend dev server | https://nodejs.org |
| Azure CLI | `az login` for credentials | https://aka.ms/azcli |
| Azure Developer CLI (`azd`) | Infra deployment | https://aka.ms/azd-install |
| Azure subscription | Hosts Foundry, Search, Storage | — |

---

## Quickstart (after first-time deployment)

```powershell
# 1. Clone & enter repo
git clone https://github.com/Heenanl/foundry-agents-demo.git
cd foundry-agents-demo

# 2. Copy and fill in environment variables (see "Configuration" below)
copy .env.example .env
notepad .env

# 3. Authenticate to Azure (used by the workflow at runtime)
az login

# 4. Python deps
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r webapp\backend\requirements.txt

# 5. Frontend deps
cd webapp\frontend
npm install
cd ..\..

# 6. Run backend (terminal 1)
.\.venv\Scripts\python.exe webapp\backend\api.py

# 7. Run frontend (terminal 2)
cd webapp\frontend
npm start

# 8. Open the UI
start http://localhost:3000/magentic
```

---

## First-time setup: deploy infrastructure & create agents

**Step 1 — Deploy Azure infra** (Foundry account, AI Search, Storage, model deployment, RBAC):

See [deployment/README.md](deployment/README.md). After `azd up` completes, copy the outputs into your `.env` file.

**Step 2 — Create the four agents in Azure AI Foundry:**

In the Foundry portal, create these agents under your project. Names must match (or override via `.env`):

| Agent name | Role | Tools |
|---|---|---|
| `rfp-orchestrator-agent` | Plans and synthesizes | (none) |
| `rfp-summary-agent` | Summarizes the RFP | Azure AI Search (RFP index) |
| `rfp-risk-agent` | Identifies risks | Azure AI Search (RFP index) |
| `rfp-compliance-agent` | Checks compliance gaps | Azure AI Search (RFP index) |

**Step 3 — Index the RFP documents** in Azure AI Search so the specialist agents can retrieve them. Sample RFP documents are provided in [data/sample-rfps/](data/sample-rfps/) for indexing:
- `woodgrove_bank_rfp_response_contoso_ltd.pdf`
- `rfp_compliance_guidelines.pdf`
- `rfp_security_risk_guidelines.pdf`

---

## Configuration

All runtime configuration lives in `.env` at the repo root. See [.env.example](.env.example) for the template.

| Variable | Required | Description |
|---|---|---|
| `AZURE_AI_PROJECT_ENDPOINT` | yes | Foundry project endpoint (from `azd up` outputs) |
| `AZURE_AI_AGENT_ORCHESTRATOR` | no | Override orchestrator agent name (default: `rfp-orchestrator-agent`) |
| `AZURE_AI_AGENT_SUMMARY` | no | Override summary agent name |
| `AZURE_AI_AGENT_RISK` | no | Override risk agent name |
| `AZURE_AI_AGENT_COMPLIANCE` | no | Override compliance agent name |

Authentication uses `AzureCliCredential`, so make sure `az login` has been run in the same shell.

---

## Running the Magentic workflow standalone (no UI)

Useful for debugging the orchestration logic:

```powershell
.\.venv\Scripts\python.exe magentic_rfp_workflow.py
```

The default query is `"Analyze the Woodgrove Bank RFP..."`. Edit the `main()` function to change it.

---

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | Health check |
| `POST` | `/api/magentic/analyze` | Synchronous run, returns final report |
| `GET` | `/api/magentic/analyze/stream?query=...` | SSE stream of agent progress events |
| `GET` | `/docs` | Auto-generated OpenAPI / Swagger UI |

SSE event types: `start`, `agent_start`, `agent_complete`, `complete`, `error`.

---

## Continuous evaluation (GitHub Actions)

[.github/workflows/rfp-evaluation.yml](.github/workflows/rfp-evaluation.yml) runs the Azure AI Evaluation SDK against the latest version of each agent. It:

1. Fetches the latest agent versions from Foundry
2. Runs the evaluation datasets in [data/](data/) against each agent
3. Reports metrics back to the workflow run

Triggers: manual `workflow_dispatch` or push to `main` that touches `data/**`.

Requires an Azure AD app with **federated credentials** for the repo, plus the following GitHub repo variables: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `AZURE_AI_PROJECT_ENDPOINT`.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `Connection error occurred` in UI | Backend not running, or stale process on port 8000 | Restart `python webapp\backend\api.py` |
| `404 Not Found` on `/api/magentic/...` | Old backend process still bound to port | `Stop-Process -Id <pid> -Force`, then restart |
| `DefaultAzureCredential failed to retrieve a token` | `az login` not run in this shell | Run `az login` |
| Agent returns "I don't have access to that document" | RFP not indexed in AI Search | Index the PDFs into the agent's connected search index |
| Workflow hangs / "Invalid next speaker" | Orchestrator can't decide; usually off-topic query | Use an RFP-related query |

---

## Tech Stack

- **Orchestration:** [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) — Magentic pattern
- **Agents:** Azure AI Foundry (hosted agents with AI Search grounding)
- **Backend:** FastAPI + Uvicorn
- **Frontend:** React (Create React App)
- **Infra-as-Code:** Bicep + Azure Developer CLI (`azd`)
- **Eval:** Azure AI Evaluation SDK (in GitHub Actions)

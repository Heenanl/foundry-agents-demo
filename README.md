# MCAPS_Tech_Connect_2026_Foundry

Multi-agent RFP Analysis system with Magentic orchestration pattern.

## TODO
- deployment doesn't deploy a Foundry Project <-- add it
- The user_query to start the magentic workflow is hardcoded , so no matter what the input prompt on UI. the workflow is executed . Fix this to show guardrails are implemented.

## RESOLVED
- ✅ The scrolling on Magentic UI - Fixed by removing height constraints
- ✅ The progress status for each stage synced with agent execution - Agent status now properly tracks rfp-summary-agent, rfp-risk-agent, rfp-compliance-agent completion

## Setup

1. Read and follow README from deployment folder to deploy the infrastructure for AI Agents.
2. Create and activate a Python virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. Install backend dependencies:
   ```powershell
   pip install -r webapp\backend\requirements.txt
   ```
4. Install frontend dependencies:
   ```powershell
   cd webapp\frontend
   npm install
   cd ..\..
   ```

## Running the Application

### Backend API Server
In one PowerShell terminal with `.venv` activated:
```powershell
.\.venv\Scripts\python.exe webapp\backend\api.py
```
The backend API will start on `http://localhost:8000`

### Frontend UI
In another PowerShell terminal:
```powershell
cd webapp\frontend
npm start
```
The React app will start on `http://localhost:3000`

### Access the Magentic RFP Analysis UI
Once both servers are running, navigate to:
```
http://localhost:3000/magentic
```

## Running Magentic Workflow Standalone

To test the Magentic workflow directly (without the UI):
```powershell
.\.venv\Scripts\python.exe magentic_rfp_workflow.py
```

This will run the orchestrator agent with the default query. Edit the `main()` function in `magentic_rfp_workflow.py` to customize the query.

## Testing Agent Code

To test the agent session code:
```powershell
cd agent
python agent_session.py
```
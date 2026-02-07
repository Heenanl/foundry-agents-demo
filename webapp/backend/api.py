"""
FastAPI Backend for MCAPS Tech Connect 2026 Chat Application

This API connects the React frontend to the Azure AI Agent backend.
"""

import sys
import asyncio
from pathlib import Path

# Add the agent directory to the Python path so we can import agent_session
agent_path = Path(__file__).parent.parent.parent / 'agent'
sys.path.insert(0, str(agent_path))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import json
import asyncio
from agent_session import AgentSession, Participant

# Import form checker router
from form_checker_api import router as form_checker_router

# Import magentic workflow
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
from magentic_rfp_workflow import run_magentic_rfp_workflow

# Initialize FastAPI app
app = FastAPI(
    title="MCAPS Tech Connect 2026 API",
    description="Backend API for AI Agent Chat Application",
    version="1.0.0"
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(form_checker_router)

# Global session storage
chat_session: Optional[AgentSession] = None
participants_dict = {}


# Request/Response Models
class InitSessionRequest(BaseModel):
    session_id: str = "webapp-session"


class InitSessionResponse(BaseModel):
    session_id: str
    message: str


class AddParticipantRequest(BaseModel):
    participant_id: str
    name: str
    type: str = "user"


class ParticipantResponse(BaseModel):
    participant_id: str
    name: str
    type: str


class SendMessageRequest(BaseModel):
    participant_id: str
    message: str


class MessageResponse(BaseModel):
    participant_id: str
    participant_name: str
    message: str
    sender: str  # 'participant' or 'bot'


class SessionStatusResponse(BaseModel):
    is_initialized: bool
    session_id: Optional[str]
    thread_id: Optional[str]
    message_count: int
    participants: List[ParticipantResponse]


class ConversationMessage(BaseModel):
    text: str
    sender: str  # 'user' or 'bot'
    participant_name: Optional[str] = None
    timestamp: str


class RfpAnalysisRequest(BaseModel):
    rfp_content: str
    rfp_name: str = "RFP Document"


class RfpAnalysisResponse(BaseModel):
    rfp_name: str
    summary: str
    risks: str
    compliance: str
    full_report: str


# API Endpoints

@app.get("/")
async def root():
    """Root endpoint - API status check"""
    return {
        "message": "MCAPS Tech Connect 2026 API",
        "status": "running",
        "docs": "/docs"
    }


@app.post("/api/session/init", response_model=InitSessionResponse)
def initialize_session(request: InitSessionRequest):
    """Initialize the agent session"""
    global chat_session, participants_dict
    
    if chat_session and chat_session.is_initialized:
        return InitSessionResponse(
            session_id=chat_session.session_id,
            message="Session already initialized"
        )
    
    try:
        chat_session = AgentSession(session_id=request.session_id)
        chat_session.initialize()
        participants_dict = {}  # Reset participants
        
        # Create default participant "Andreea"
        default_participant = Participant(
            participant_id="ID_00001",
            name="Andreea",
            type="user"
        )
        participants_dict["ID_00001"] = default_participant
        
        return InitSessionResponse(
            session_id=chat_session.session_id,
            message="Session initialized successfully"
        )
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR initializing session: {error_details}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize session: {str(e)}")


@app.post("/api/participants/add", response_model=ParticipantResponse)
async def add_participant(request: AddParticipantRequest):
    """Add a new participant to the session"""
    global participants_dict
    
    if not chat_session or not chat_session.is_initialized:
        raise HTTPException(status_code=400, detail="Session not initialized. Call /api/session/init first.")
    
    if request.participant_id in participants_dict:
        raise HTTPException(status_code=400, detail=f"Participant {request.participant_id} already exists")
    
    try:
        participant = Participant(
            participant_id=request.participant_id,
            name=request.name,
            type=request.type
        )
        participants_dict[request.participant_id] = participant
        
        return ParticipantResponse(
            participant_id=participant.id,
            name=participant.name,
            type=participant.type
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add participant: {str(e)}")


@app.delete("/api/participants/{participant_id}")
async def remove_participant(participant_id: str):
    """Remove a participant from the session"""
    global participants_dict
    
    if not chat_session or not chat_session.is_initialized:
        raise HTTPException(status_code=400, detail="Session not initialized")
    
    if participant_id not in participants_dict:
        raise HTTPException(status_code=404, detail=f"Participant {participant_id} not found")
    
    try:
        removed_participant = participants_dict.pop(participant_id)
        
        return {
            "message": f"Participant {removed_participant.name} removed successfully",
            "participant_id": participant_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove participant: {str(e)}")


@app.get("/api/participants/list", response_model=List[ParticipantResponse])
async def list_participants():
    """Get list of all participants in the session"""
    global participants_dict
    
    if not chat_session or not chat_session.is_initialized:
        raise HTTPException(status_code=400, detail="Session not initialized")
    
    participants_list = [
        ParticipantResponse(
            participant_id=p.id,
            name=p.name,
            type=p.type
        )
        for p in participants_dict.values()
    ]
    
    return participants_list


@app.post("/api/messages/send", response_model=MessageResponse)
def send_message(request: SendMessageRequest):
    """Send a message from a participant and get agent response"""
    global chat_session, participants_dict
    
    if not chat_session or not chat_session.is_initialized:
        raise HTTPException(status_code=400, detail="Session not initialized")
    
    if request.participant_id not in participants_dict:
        raise HTTPException(status_code=404, detail=f"Participant {request.participant_id} not found")
    
    try:
        participant = participants_dict[request.participant_id]
        response = participant.send_message(request.message, chat_session)

        if response is None:
            raise HTTPException(status_code=404, detail=f"Response is empty from agent")
        
        return MessageResponse(
            participant_id=participant.id,
            participant_name=participant.name,
            message=response,
            sender="bot"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")


@app.get("/api/session/status", response_model=SessionStatusResponse)
async def get_session_status():
    """Get current session status"""
    global chat_session, participants_dict
    
    if not chat_session:
        return SessionStatusResponse(
            is_initialized=False,
            session_id=None,
            thread_id=None,
            message_count=0,
            participants=[]
        )
    
    stats = chat_session.get_stats()
    participants_list = [
        ParticipantResponse(
            participant_id=p.id,
            name=p.name,
            type=p.type
        )
        for p in participants_dict.values()
    ]
    
    return SessionStatusResponse(
        is_initialized=stats["is_initialized"],
        session_id=stats["session_id"],
        thread_id=stats["thread_id"],
        message_count=stats["message_count"],
        participants=participants_list
    )


@app.get("/api/messages/history", response_model=List[ConversationMessage])
async def get_message_history():
    """Get the conversation history from the thread"""
    global chat_session
    
    if not chat_session or not chat_session.is_initialized:
        return []
    
    try:
        # Get messages from the thread using the chat client
        # The thread stores all conversation history
        messages = chat_session.thread.get_messages()
        
        conversation_history = []
        for msg in messages:
            # Parse participant name from message if it starts with "<name>:"
            text = msg.text if hasattr(msg, 'text') else str(msg)
            role_value = msg.role.value if hasattr(msg, 'role') else "user"
            sender = "bot" if role_value == "assistant" else "user"
            participant_name = None
            
            if sender == "user" and text and ":" in text:
                # Extract participant name from "<name>: <message>" format
                parts = text.split(":", 1)
                if len(parts) == 2:
                    participant_name = parts[0].strip()
                    text = parts[1].strip()
            
            timestamp = msg.created_at if hasattr(msg, 'created_at') and msg.created_at else ""
            
            conversation_history.append(ConversationMessage(
                text=text,
                sender=sender,
                participant_name=participant_name,
                timestamp=str(timestamp)
            ))
        
        return conversation_history
    except Exception as e:
        return []


@app.post("/api/session/close")
def close_session():
    """Close the current session"""
    global chat_session, participants_dict
    
    if not chat_session:
        return {"message": "No active session"}
    
    try:
        chat_session.close()
        chat_session = None
        participants_dict = {}
        
        return {"message": "Session closed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to close session: {str(e)}")


@app.post("/api/rfp/analyze", response_model=RfpAnalysisResponse)
def analyze_rfp_orchestrated(request: RfpAnalysisRequest):
    """
    Orchestrated RFP Analysis using multiple specialized agents with full Foundry traceability.
    
    This endpoint implements a multi-agent workflow coordinated by an orchestrator agent:
    1. OrchestratorAgent: Receives RFP and creates analysis plan
    2. RfpSummaryAgent: Creates executive summary (called by orchestrator)
    3. RfpRiskAgent: Identifies risks (called by orchestrator)
    4. RfpComplianceAgent: Checks compliance gaps (called by orchestrator)
    5. OrchestratorAgent: Synthesizes all results into final report
    
    All interactions are logged in the same conversation for complete traceability.
    """
    try:
        print(f"\n{'='*60}")
        print(f"Starting Orchestrated RFP Analysis: {request.rfp_name}")
        print(f"{'='*60}")
        
        # Shared conversation ID for complete traceability
        shared_conversation_id = None
        
        # Step 0: Initialize Orchestrator Agent
        print("\n[Step 0/5] Initializing OrchestratorAgent...")
        orchestrator_session = AgentSession(
            session_id="rfp-orchestrated-workflow",
            agent_name="rfp-orchestrator-agent",
            conversation_id=shared_conversation_id
        )
        orchestrator_session.initialize()
        
        orchestrator = Participant(
            participant_id="ORCHESTRATOR",
            name="Orchestrator",
            type="agent"
        )
        
        # Step 1: Orchestrator receives RFP and initiates workflow
        print("\n[Step 1/5] Orchestrator: Analyzing RFP and creating execution plan...")
        orchestrator_init_prompt = f"""You are the RFP Analysis Orchestrator. You coordinate a team of specialized agents to analyze RFPs.

RFP Document: {request.rfp_name}

Content:
{request.rfp_content}

You will coordinate three specialized agents:
1. RfpSummaryAgent - Creates executive summaries
2. RfpRiskAgent - Identifies and assesses risks
3. RfpComplianceAgent - Analyzes compliance requirements

Your task: Acknowledge receipt of this RFP and outline your analysis plan. You will see the results from each agent and synthesize them into a final report.

Respond with your analysis plan."""
        
        orchestrator_plan = orchestrator.send_message(orchestrator_init_prompt, orchestrator_session)
        shared_conversation_id = orchestrator_session.conversation_id
        print(f"✓ Orchestrator plan created")
        print(f"✓ Conversation ID: {shared_conversation_id}")
        
        # Step 2: Orchestrator calls RfpSummaryAgent (staying in orchestrator's session)
        print("\n[Step 2/5] Orchestrator → RfpSummaryAgent...")
        summary_prompt = f"""Now activate the RfpSummaryAgent from your team to analyze this RFP.

Request the RfpSummaryAgent to provide an executive summary including:
- Key objectives
- Scope
- Timeline
- Budget information (if available)
- Strategic considerations

The summary should be 3-5 paragraphs and actionable."""
        
        summary_result = orchestrator.send_message(summary_prompt, orchestrator_session)
        shared_conversation_id = orchestrator_session.conversation_id
        print(f"✓ Summary received: {len(summary_result)} characters")
        
        # Step 3: Orchestrator calls RfpRiskAgent (staying in orchestrator's session)
        print("\n[Step 3/5] Orchestrator → RfpRiskAgent...")
        risk_prompt = f"""Now activate the RfpRiskAgent from your team to analyze risks in this RFP.

Request the RfpRiskAgent to identify and assess:
- Technical risks
- Timeline and delivery risks
- Budget and resource risks
- Compliance and regulatory risks
- Vendor/partnership risks

The risk assessment should include severity levels (High/Medium/Low) and mitigation strategies."""
        
        risk_result = orchestrator.send_message(risk_prompt, orchestrator_session)
        shared_conversation_id = orchestrator_session.conversation_id
        print(f"✓ Risk assessment received: {len(risk_result)} characters")
        
        # Step 4: Call RfpComplianceAgent (within orchestrator's conversation)
        print("\n[Step 4/5] Orchestrator → RfpComplianceAgent...")
        compliance_session = AgentSession(
            session_id="rfp-orchestrated-workflow",
            agent_name="rfp-compliance-agent",
            conversation_id=shared_conversation_id
        )
        compliance_session.initialize()
        
        compliance_participant = Participant(
            participant_id="COMPLIANCE_AGENT",
            name="RfpComplianceAgent",
            type="agent"
        )
        
        # Step 4: Orchestrator calls RfpComplianceAgent (staying in orchestrator's session)
        print("\n[Step 4/5] Orchestrator → RfpComplianceAgent...")
        compliance_prompt = f"""Now activate the RfpComplianceAgent from your team to analyze compliance requirements.

Based on the RFP, summary, and risk assessment already discussed, request the RfpComplianceAgent to check:
- Legal and regulatory requirements
- Industry standards (ISO, SOC2, GDPR, etc.)
- Security and privacy requirements
- Certification requirements
- Contractual obligations
- Missing or unclear compliance requirements

The analysis should include a compliance gap analysis with recommendations."""
        
        compliance_result = orchestrator.send_message(compliance_prompt, orchestrator_session)
        shared_conversation_id = orchestrator_session.conversation_id
        print(f"✓ Compliance report received: {len(compliance_result)} characters")
        
        # Step 5: Orchestrator synthesizes final report
        print("\n[Step 5/5] Orchestrator synthesizing final report...")
        synthesis_prompt = f"""Now synthesize all the findings from your team into a final comprehensive report.

Based on the complete analysis from:
1. RfpSummaryAgent - Executive Summary
2. RfpRiskAgent - Risk Assessment  
3. RfpComplianceAgent - Compliance Analysis

Provide your final synthesis with:
- Key recommendations (prioritized)
- Critical action items
- Overall assessment with Go/No-Go recommendation
- Next steps for the organization
- Executive decision points

Be strategic, concise, and actionable."""
        
        orchestrator_final = orchestrator.send_message(synthesis_prompt, orchestrator_session)
        shared_conversation_id = orchestrator_session.conversation_id
        print(f"✓ Orchestrator synthesis complete")
        print(f"✓ Final conversation ID: {shared_conversation_id}")
        
        # Keep session open briefly to ensure all traces are recorded
        import time
        time.sleep(1)
        
        # Build final report
        full_report = f"""# RFP Analysis Report: {request.rfp_name}

## Executive Summary
{summary_result}

## Risk Assessment
{risk_result}

## Compliance Analysis
{compliance_result}

## Final Synthesis & Recommendations
{orchestrator_final}

---
Report generated by Multi-Agent Orchestration System
Conversation ID: {shared_conversation_id}
All agent interactions are traceable in Azure AI Foundry
"""
        
        print(f"\n{'='*60}")
        print(f"✓ Orchestrated Analysis Complete")
        print(f"✓ Conversation ID: {shared_conversation_id}")
        print(f"✓ Full trace available in Azure AI Foundry")
        print(f"{'='*60}\n")
        
        return RfpAnalysisResponse(
            rfp_name=request.rfp_name,
            summary=summary_result,
            risks=risk_result,
            compliance=compliance_result,
            full_report=full_report
        )
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR in orchestrated analysis: {error_details}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to complete RFP analysis: {str(e)}"
        )


class MagenticWorkflowRequest(BaseModel):
    query: str
    interactive: bool = False


class MagenticWorkflowResponse(BaseModel):
    workflow_run_id: str
    conversation_id: str
    final_output: str
    agent_calls: List[dict]


@app.post("/api/magentic/analyze", response_model=MagenticWorkflowResponse)
async def run_magentic_workflow_endpoint(request: MagenticWorkflowRequest):
    """
    Run the Magentic orchestrated RFP analysis workflow.
    
    This uses the agent_framework's Magentic pattern to orchestrate
    multiple specialized agents through a coordinator agent.
    """
    try:
        print(f"\n{'='*60}")
        print(f"🚀 Starting Magentic Workflow")
        print(f"Query: {request.query}")
        print(f"{'='*60}")
        
        # Run the workflow
        result = await run_magentic_rfp_workflow(
            user_query=request.query,
            interactive=request.interactive
        )
        
        # Extract conversation_id from agent_calls if available
        conversation_id = result.agent_calls[0]["conversation_id"] if result.agent_calls else "N/A"
        
        return MagenticWorkflowResponse(
            workflow_run_id=result.workflow_run_id,
            conversation_id=conversation_id,
            final_output=result.final_output,
            agent_calls=result.agent_calls
        )
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR in Magentic workflow: {error_details}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to run Magentic workflow: {str(e)}"
        )


@app.get("/magentic", response_class=HTMLResponse)
async def magentic_frontend():
    """Serve the Magentic workflow frontend"""
    html_path = Path(__file__).parent.parent / "frontend" / "magentic.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding='utf-8'), status_code=200)
    else:
        return HTMLResponse(content="<h1>Magentic frontend not found</h1>", status_code=404)


# Run with: uvicorn api:app --reload --port 8000
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

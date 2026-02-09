"""
FastAPI Backend for Magentic RFP Workflow

This API provides endpoints for running the Magentic orchestrated RFP analysis workflow.
"""

import sys
from pathlib import Path

# Add the agent directory to the Python path
agent_path = Path(__file__).parent.parent.parent / 'agent'
sys.path.insert(0, str(agent_path))

# Import magentic workflow
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
from magentic_rfp_workflow import run_magentic_rfp_workflow, run_magentic_rfp_workflow_stream
from agent_session import AgentSession, Participant

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
import json

# Initialize FastAPI app
app = FastAPI(
    title="Magentic RFP Workflow API",
    description="Backend API for Magentic RFP Analysis Workflow",
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

# SESSION CACHE - Store active chat sessions for reuse
chat_sessions: Dict[str, tuple[AgentSession, Participant]] = {}


# Request/Response Models
class MagenticWorkflowRequest(BaseModel):
    query: str
    interactive: bool = False


class MagenticWorkflowResponse(BaseModel):
    workflow_run_id: str
    conversation_id: str
    final_output: str
    agent_calls: List[dict]


class SimpleChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class SimpleChatResponse(BaseModel):
    response: str
    session_id: str
    trigger_workflow: bool = False  # Flag to tell frontend to start workflow


# API Endpoints

@app.get("/")
async def root():
    """Root endpoint - API status check"""
    return {
        "message": "Magentic RFP Workflow API",
        "status": "running",
        "docs": "/docs"
    }


@app.post("/api/magentic/chat", response_model=SimpleChatResponse)
async def chat_with_orchestrator(request: SimpleChatRequest):
    """
    Chat with the orchestrator agent. If user requests analysis,
    flag it to trigger the Magentic workflow.
    
    Uses session caching - creates session once, reuses for all messages.
    """
    try:
        # Check if message contains workflow trigger keywords
        trigger_keywords = ['analyze', 'analysis', 'rfp', 'review', 'assess', 'evaluate', 'examine']
        message_lower = request.message.lower()
        should_trigger_workflow = any(keyword in message_lower for keyword in trigger_keywords)
        
        if should_trigger_workflow:
            # Return response that will trigger workflow
            return SimpleChatResponse(
                response="I'll start the Magentic RFP Analysis workflow for you now...",
                session_id=request.session_id or f"chat-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                trigger_workflow=True
            )
        
        # Get or create session
        session_id = request.session_id or f"chat-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Check if session exists in cache
        if session_id in chat_sessions:
            print(f"♻️  Reusing existing session: {session_id}")
            chat_session, user = chat_sessions[session_id]
        else:
            print(f"🆕 Creating new session: {session_id}")
            # Initialize agent session with orchestrator
            chat_session = AgentSession(
                session_id=session_id,
                agent_name="rfp-orchestrator-agent"
            )
            chat_session.initialize()
            
            # Create a participant for the user
            user = Participant(
                participant_id="USER",
                name="User",
                type="user"
            )
            
            # Cache the session
            chat_sessions[session_id] = (chat_session, user)
        
        # Send message using cached session
        response = user.send_message(request.message, chat_session)
        
        return SimpleChatResponse(
            response=response or "I'm here to help with RFP analysis. What would you like to know?",
            session_id=session_id,
            trigger_workflow=False
        )
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process chat message: {str(e)}"
        )


@app.post("/api/session/close")
async def close_session(request: dict):
    """
    Close and cleanup a chat session.
    """
    session_id = request.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    
    if session_id in chat_sessions:
        chat_session, _ = chat_sessions[session_id]
        try:
            chat_session.close()
        except Exception as e:
            print(f"Warning: Error closing session: {e}")
        del chat_sessions[session_id]
        return {"message": f"Session {session_id} closed"}
    return {"message": "Session not found"}


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


@app.get("/api/magentic/analyze/stream")
async def run_magentic_workflow_stream_endpoint(query: str):
    """
    Stream the Magentic workflow execution with real-time progress updates.
    Returns Server-Sent Events (SSE) with agent progress.
    """
    print(f"\n{'='*60}")
    print(f"🔄 Streaming Magentic Workflow")
    print(f"Query: {query}")
    print(f"{'='*60}")
    
    async def event_generator():
        try:
            async for event_data in run_magentic_rfp_workflow_stream(query):
                # Send SSE event
                print(f"Sending event: {event_data.get('type', 'unknown')}")
                yield f"data: {json.dumps(event_data)}\n\n"
                
        except Exception as e:
            import traceback
            error_data = {
                "type": "error",
                "message": str(e),
                "traceback": traceback.format_exc()
            }
            print(f"ERROR in streaming: {error_data}")
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )


# Run with: uvicorn magentic_api:app --reload --port 8000
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

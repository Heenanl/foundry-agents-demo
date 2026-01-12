"""
FastAPI Backend for MCAPS Tech Connect 2026 Chat Application

This API connects the React frontend to the Azure AI Agent backend.
"""

import sys
from pathlib import Path

# Add the agent directory to the Python path so we can import agent_session
agent_path = Path(__file__).parent.parent.parent / 'agent'
sys.path.insert(0, str(agent_path))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from agent_session import AgentSession, Participant

# Import form checker router
from form_checker_api import router as form_checker_router

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
async def initialize_session(request: InitSessionRequest):
    """Initialize the agent session"""
    global chat_session, participants_dict
    
    if chat_session and chat_session.is_initialized:
        return InitSessionResponse(
            session_id=chat_session.session_id,
            message="Session already initialized"
        )
    
    try:
        chat_session = AgentSession(session_id=request.session_id)
        await chat_session.initialize()
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
async def send_message(request: SendMessageRequest):
    """Send a message from a participant and get agent response"""
    global chat_session, participants_dict
    
    if not chat_session or not chat_session.is_initialized:
        raise HTTPException(status_code=400, detail="Session not initialized")
    
    if request.participant_id not in participants_dict:
        raise HTTPException(status_code=404, detail=f"Participant {request.participant_id} not found")
    
    try:
        participant = participants_dict[request.participant_id]
        response = await participant.send_message(request.message, chat_session)
        
        return MessageResponse(
            participant_id=participant.id,
            participant_name=participant.name,
            message=response.text,
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
async def close_session():
    """Close the current session"""
    global chat_session, participants_dict
    
    if not chat_session:
        return {"message": "No active session"}
    
    try:
        await chat_session.close()
        chat_session = None
        participants_dict = {}
        
        return {"message": "Session closed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to close session: {str(e)}")


# Run with: uvicorn api:app --reload --port 8000
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

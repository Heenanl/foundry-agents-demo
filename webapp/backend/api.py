"""
FastAPI Backend for MCAPS Tech Connect 2026 - Magentic RFP Workflow
"""

import sys
import json
import traceback
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Make project root importable so we can load magentic_rfp_workflow
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
from magentic_rfp_workflow import run_magentic_rfp_workflow  # noqa: E402

# Initialize FastAPI app
app = FastAPI(
    title="MCAPS Tech Connect 2026 - Magentic API",
    description="Backend API for Magentic RFP Analysis Workflow",
    version="1.0.0",
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class MagenticWorkflowRequest(BaseModel):
    query: str
    interactive: bool = False


class MagenticWorkflowResponse(BaseModel):
    workflow_run_id: str
    conversation_id: str
    final_output: str
    agent_calls: List[dict]


@app.get("/")
async def root():
    """Root endpoint - API status check"""
    return {
        "message": "MCAPS Tech Connect 2026 - Magentic API",
        "status": "running",
        "docs": "/docs",
    }


@app.post("/api/magentic/analyze", response_model=MagenticWorkflowResponse)
async def run_magentic_workflow_endpoint(request: MagenticWorkflowRequest):
    """
    Run the Magentic orchestrated RFP analysis workflow synchronously.
    Returns the final synthesized result once the workflow completes.
    """
    try:
        print(f"\n{'='*60}")
        print(f"🚀 Starting Magentic Workflow")
        print(f"Query: {request.query}")
        print(f"{'='*60}")

        result = await run_magentic_rfp_workflow(
            user_query=request.query,
            interactive=request.interactive,
        )

        conversation_id = (
            result.agent_calls[0]["conversation_id"] if result.agent_calls else "N/A"
        )

        return MagenticWorkflowResponse(
            workflow_run_id=result.workflow_run_id,
            conversation_id=conversation_id,
            final_output=result.final_output,
            agent_calls=result.agent_calls,
        )

    except Exception as e:
        error_details = traceback.format_exc()
        print(f"ERROR in Magentic workflow: {error_details}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to run Magentic workflow: {str(e)}",
        )


@app.get("/api/magentic/analyze/stream")
async def run_magentic_workflow_stream_endpoint(query: str):
    """
    Stream the Magentic workflow execution with real-time progress updates
    via Server-Sent Events (SSE).
    """
    print(f"\n{'='*60}")
    print(f"🔄 Streaming Magentic Workflow")
    print(f"Query: {query}")
    print(f"{'='*60}")

    async def event_generator():
        try:
            from magentic_rfp_workflow import run_magentic_rfp_workflow_stream

            async for event_data in run_magentic_rfp_workflow_stream(query):
                print(f"Sending event: {event_data.get('type', 'unknown')}")
                yield f"data: {json.dumps(event_data)}\n\n"

        except Exception as e:
            error_data = {
                "type": "error",
                "message": str(e),
                "traceback": traceback.format_exc(),
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
        },
    )


# Run with: python api.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

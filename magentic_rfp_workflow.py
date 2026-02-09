# Copyright (c) Microsoft. All rights reserved.
"""
Magentic Orchestrator Workflow with Existing Foundry Agents

This workflow uses the Magentic pattern with:
- ORCHESTRATOR: Plans, delegates tasks to specialists, synthesizes final output
- SUMMARY AGENT: Summarizes RFP (can use AI Search grounding in Foundry)
- RISK AGENT: Identifies and categorizes risks
- COMPLIANCE AGENT: Creates compliance checklists

Architecture:
                    ┌─────────────────┐
                    │  ORCHESTRATOR   │  ← Plans, delegates, synthesizes
                    │     Agent       │
                    └────────┬────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
           ▼                 ▼                 ▼
    ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
    │   SUMMARY   │   │    RISK     │   │ COMPLIANCE  │
    │   Agent     │   │   Agent     │   │   Agent     │
    └─────────────┘   └─────────────┘   └─────────────┘
           │                 │                 │
           └─────────────────┼─────────────────┘
                             ▼
                    ┌─────────────────┐
                    │  FINAL OUTPUT   │
                    └─────────────────┘

Prerequisites:
- Create these 4 agents in Azure AI Foundry:
  * RfpOrchestratorAgent - Coordinates the workflow
  * RfpSummaryAgent - Summarizes RFPs (optionally with AI Search)
  * RfpRiskAgent - Risk analysis
  * RfpComplianceAgent - Compliance checking
- Run `az login` for authentication
- Set environment variables in .env

Usage:
    python magentic_rfp_workflow.py
"""

import asyncio
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import cast
from dataclasses import dataclass, field

from agent_framework import (
    AgentRunUpdateEvent,
    ChatMessage,
    GroupChatRequestSentEvent,
    MagenticBuilder,
    MagenticOrchestratorEvent,
    MagenticProgressLedger,
    WorkflowOutputEvent,
)
from agent_framework.azure import AzureAIProjectAgentProvider
from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import AzureCliCredential
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent / '.env')


@dataclass
class WorkflowResult:
    """Results from the Magentic workflow."""
    workflow_run_id: str
    final_output: str
    conversation_messages: list[ChatMessage]
    agent_calls: list[dict] = field(default_factory=list)
    
    def __str__(self):
        return f"""
{'='*70}
📋 RFP ANALYSIS COMPLETE (Magentic Orchestration)
{'='*70}
Workflow Run ID: {self.workflow_run_id}
Agent Calls: {len(self.agent_calls)}
{'='*70}

{self.final_output}

{'='*70}
"""


async def run_magentic_rfp_workflow(user_query: str, interactive: bool = False) -> WorkflowResult:
    """
    Run the Magentic RFP analysis workflow.
    
    The orchestrator agent:
    1. Creates a plan for analyzing the RFP
    2. Delegates to specialist agents (Summary, Risk, Compliance)
    3. Synthesizes the final comprehensive output
    
    Each agent has its OWN thread for AI Search queries.
    A common workflow_run_id ties all agent calls together for logging/tracing.
    The orchestrator maintains context via MagenticContext.chat_history.
    
    Args:
        user_query: Natural language query (e.g., "Analyze the Woodgrove Bank RFP")
        interactive: If True, pause for user input at orchestrator events
        
    Returns:
        WorkflowResult with workflow_run_id, final output, and conversation history
    """
    # Generate a unique workflow run ID for logging/tracing
    workflow_run_id = f"rfp-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
    agent_calls: list[dict] = []  # Track all agent calls for logging
    
    # Get agent names from environment
    orchestrator_name = os.getenv("AZURE_AI_AGENT_ORCHESTRATOR", "rfp-orchestrator-agent")
    summary_name = os.getenv("AZURE_AI_AGENT_SUMMARY", "rfp-summary-agent")
    risk_name = os.getenv("AZURE_AI_AGENT_RISK", "rfp-risk-agent")
    compliance_name = os.getenv("AZURE_AI_AGENT_COMPLIANCE", "rfp-compliance-agent")
    
    async with (
        AzureCliCredential() as credential,
        AIProjectClient(endpoint=os.getenv("AZURE_AI_PROJECT_ENDPOINT"), credential=credential) as project_client,
    ):
        # Create a shared conversation on the service for all agents
        # This ensures conversation_id is registered in Foundry portal
        openai_client = project_client.get_openai_client()
        conversation = await openai_client.conversations.create()
        conversation_id = conversation.id
        
        print("\n" + "="*70)
        print(f"🚀 Workflow Run ID: {workflow_run_id}")
        print(f"📝 Conversation ID: {conversation_id}")
        print("="*70)
        print("Loading Agents from Azure AI Foundry...")
        
        # Create provider using the same project client
        provider = AzureAIProjectAgentProvider(project_client=project_client)
        
        # Get existing agents from Foundry with shared conversation_id
        # This registers the conversation in the Foundry portal
        orchestrator_agent = await provider.get_agent(
            name=orchestrator_name,
            default_options={"conversation_id": conversation_id}
        )
        print(f"✓ Orchestrator: {orchestrator_agent.name}")
        
        summary_agent = await provider.get_agent(
            name=summary_name,
            default_options={"conversation_id": conversation_id}
        )
        print(f"✓ Summary Agent: {summary_agent.name}")
        
        risk_agent = await provider.get_agent(
            name=risk_name,
            default_options={"conversation_id": conversation_id}
        )
        print(f"✓ Risk Agent: {risk_agent.name}")
        
        compliance_agent = await provider.get_agent(
            name=compliance_name,
            default_options={"conversation_id": conversation_id}
        )
        print(f"✓ Compliance Agent: {compliance_agent.name}")
        
        print("\n" + "="*70)
        print("🔧 Building Magentic Workflow...")
        print("="*70)
        
        # Build the Magentic workflow
        # The orchestrator coordinates the specialists
        # Note: Agents already have system prompts and AI Search configured in Foundry
        workflow = (
            MagenticBuilder()
            .participants([summary_agent, risk_agent, compliance_agent])
            .with_manager(
                agent=orchestrator_agent,
                max_round_count=6,    # 1 per agent + synthesis + buffer
                max_stall_count=3,    # Max stalls before forcing progress
                max_reset_count=2,    # Max resets if workflow gets stuck
            )
            .build()
        )
        
        print("✓ Workflow built successfully")
        print(f"  - Orchestrator: {orchestrator_name}")
        print(f"  - Participants: {summary_name}, {risk_name}, {compliance_name}")
        
        # Prepare the task for the workflow
        # Agents use AI Search (RAG) to retrieve RFP content from their indexes
        task = f"""
{user_query}

IMPORTANT: Each agent has access to AI Search indexes containing the RFP documents. 
Do NOT ask for the document - use your grounding tools to search for and retrieve the content.

Delegate to each team member ONCE and only once:
1. rfp-summary-agent → search and summarize the RFP
2. rfp-risk-agent → search and identify risks  
3. rfp-compliance-agent → search and check compliance

Once all three agents have responded, consider the request SATISFIED.
Do NOT call any agent a second time.

FINAL ANSWER: After all three agents respond, you MUST write a comprehensive synthesis that:
- Starts with "## RFP Analysis — Executive Summary"
- Combines key findings from all three agents into a unified narrative
- Highlights the top 3 risks and top 3 compliance gaps
- Ends with a clear recommendation (bid / no-bid / conditional bid)

Do NOT ask the user for information or clarification until all agents have been consulted first.
In your final answer, do NOT offer to help further. Provide the comprehensive analysis and end with a polite closing.
"""
        
        print("\n" + "="*70)
        print(f"▶️ Starting Workflow Execution... (Run ID: {workflow_run_id})")
        print(f"User Query: {user_query}")
        print("="*70)
        
        # Track state for streaming output
        last_message_id: str | None = None
        output_event: WorkflowOutputEvent | None = None
        current_round = 0
        
        # Run the workflow with streaming
        async for event in workflow.run_stream(task):
            
            # Agent is generating output (streaming tokens)
            if isinstance(event, AgentRunUpdateEvent):
                message_id = event.data.message_id
                if message_id != last_message_id:
                    if last_message_id is not None:
                        print("\n")
                    print(f"\n📝 [{event.executor_id}]:", end=" ", flush=True)
                    last_message_id = message_id
                print(event.data, end="", flush=True)
            
            # Orchestrator planning/progress event
            elif isinstance(event, MagenticOrchestratorEvent):
                print(f"\n\n{'='*50}")
                print(f"🎯 [Orchestrator Event] Type: {event.event_type.name}")
                
                if isinstance(event.data, ChatMessage):
                    print(f"Plan:\n{event.data.text}")
                elif isinstance(event.data, MagenticProgressLedger):
                    print(f"Progress Ledger:\n{json.dumps(event.data.to_dict(), indent=2)}")
                
                print("="*50)
                
                # Optionally pause for user review
                if interactive:
                    await asyncio.get_event_loop().run_in_executor(
                        None, input, "Press Enter to continue..."
                    )
            
            # Request sent to a participant agent - LOG with workflow_run_id and conversation_id
            elif isinstance(event, GroupChatRequestSentEvent):
                current_round = event.round_index
                agent_call = {
                    "workflow_run_id": workflow_run_id,
                    "conversation_id": conversation_id,
                    "round": event.round_index,
                    "agent": event.participant_name,
                    "timestamp": datetime.now().isoformat(),
                }
                agent_calls.append(agent_call)
                print(f"\n\n📤 [Conv: {conversation_id[:20]}...] Round {event.round_index} → {event.participant_name}")
            
            # Final output
            elif isinstance(event, WorkflowOutputEvent):
                output_event = event
        
        # Process final output
        if not output_event:
            raise RuntimeError("Workflow did not produce a final output event.")
        
        print("\n\n" + "="*70)
        print(f"✅ Workflow Completed!")
        print(f"   Run ID: {workflow_run_id}")
        print(f"   Conversation ID: {conversation_id}")
        print("="*70)
        
        # Log summary of agent calls
        print(f"\n📊 Agent Call Summary (Conversation: {conversation_id}):")
        for call in agent_calls:
            print(f"   Round {call['round']}: {call['agent']} @ {call['timestamp']}")
        
        # Extract the final synthesized output
        output_messages = cast(list[ChatMessage], output_event.data)
        final_output = output_messages[-1].text if output_messages else "No output generated"
        
        return WorkflowResult(
            workflow_run_id=workflow_run_id,
            final_output=final_output,
            conversation_messages=output_messages,
            agent_calls=agent_calls
        )


async def run_magentic_rfp_workflow_stream(user_query: str):
    """
    Stream the Magentic RFP workflow execution with real-time progress updates.
    
    Yields progress events as each agent executes, allowing the frontend
    to update the UI in real-time.
    
    Args:
        user_query: Natural language query
        
    Yields:
        dict: Progress events with type, agent name, and status
    """
    workflow_run_id = f"rfp-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
    agent_calls: list[dict] = []
    
    # Get agent names
    orchestrator_name = os.getenv("AZURE_AI_AGENT_ORCHESTRATOR", "rfp-orchestrator-agent")
    summary_name = os.getenv("AZURE_AI_AGENT_SUMMARY", "rfp-summary-agent")
    risk_name = os.getenv("AZURE_AI_AGENT_RISK", "rfp-risk-agent")
    compliance_name = os.getenv("AZURE_AI_AGENT_COMPLIANCE", "rfp-compliance-agent")
    
    try:
        async with (
            AzureCliCredential() as credential,
            AIProjectClient(endpoint=os.getenv("AZURE_AI_PROJECT_ENDPOINT"), credential=credential) as project_client,
        ):
            # Create conversation
            openai_client = project_client.get_openai_client()
            conversation = await openai_client.conversations.create()
            conversation_id = conversation.id
            
            yield {
                "type": "start",
                "workflow_run_id": workflow_run_id,
                "conversation_id": conversation_id,
                "query": user_query
            }
            
            # Load agents
            provider = AzureAIProjectAgentProvider(project_client=project_client)
            orchestrator_agent = await provider.get_agent(name=orchestrator_name, default_options={"conversation_id": conversation_id})
            summary_agent = await provider.get_agent(name=summary_name, default_options={"conversation_id": conversation_id})
            risk_agent = await provider.get_agent(name=risk_name, default_options={"conversation_id": conversation_id})
            compliance_agent = await provider.get_agent(name=compliance_name, default_options={"conversation_id": conversation_id})
            
            # Build workflow
            workflow = (
                MagenticBuilder()
                .participants([summary_agent, risk_agent, compliance_agent])
                .with_manager(agent=orchestrator_agent, max_round_count=6, max_stall_count=3, max_reset_count=2)
                .build()
            )
            
            # Prepare the task with instructions (same as non-streaming workflow)
            task = f"""
{user_query}

IMPORTANT: Each agent has access to AI Search indexes containing the RFP documents. 
Do NOT ask for the document - use your grounding tools to search for and retrieve the content.

Delegate to each team member ONCE and only once:
1. rfp-summary-agent → search and summarize the RFP
2. rfp-risk-agent → search and identify risks  
3. rfp-compliance-agent → search and check compliance

Once all three agents have responded, consider the request SATISFIED.
Do NOT call any agent a second time.

FINAL ANSWER: After all three agents respond, you MUST write a comprehensive synthesis that:
- Starts with "## RFP Analysis — Executive Summary"
- Combines key findings from all three agents into a unified narrative
- Highlights the top 3 risks and top 3 compliance gaps
- Ends with a clear recommendation (bid / no-bid / conditional bid)

Do NOT ask the user for information or clarification until all agents have been consulted first.
In your final answer, do NOT offer to help further. Provide the comprehensive analysis and end with a polite closing.
"""
            
            # Notify orchestrator started
            yield {
                "type": "agent_start",
                "agent": orchestrator_name,
                "status": "processing"
            }
            
            # Run workflow with streaming
            output_event: WorkflowOutputEvent | None = None
            async for event in workflow.run_stream(task):
                
                # Request sent to participant agent
                if isinstance(event, GroupChatRequestSentEvent):
                    agent_call = {
                        "workflow_run_id": workflow_run_id,
                        "conversation_id": conversation_id,
                        "round": event.round_index,
                        "agent": event.participant_name,
                        "timestamp": datetime.now().isoformat(),
                    }
                    agent_calls.append(agent_call)
                    print(f"\n📤 [Round {event.round_index}] → {event.participant_name}")
                    
                    # Notify agent started
                    yield {
                        "type": "agent_start",
                        "agent": event.participant_name,
                        "status": "processing",
                        "round": event.round_index
                    }
                
                # Orchestrator planning/progress event
                elif isinstance(event, MagenticOrchestratorEvent):
                    print(f"\n🎯 [Orchestrator] Event: {event.event_type.name}")
                    if isinstance(event.data, ChatMessage):
                        print(f"   Plan: {event.data.text[:500]}")
                    elif isinstance(event.data, MagenticProgressLedger):
                        ledger = event.data.to_dict()
                        print(f"   Progress Ledger: {json.dumps(ledger, indent=2)}")
                
                # Skip token-level streaming output (too noisy)
                elif isinstance(event, AgentRunUpdateEvent):
                    pass
                
                # Final output
                elif isinstance(event, WorkflowOutputEvent):
                    output_event = event
                
                # Framework lifecycle events — log concisely
                else:
                    event_name = type(event).__name__
                    # Extract useful info from executor events
                    if hasattr(event, 'executor_id'):
                        print(f"   ⚙️ {event_name}: {event.executor_id}")
                    elif hasattr(event, 'participant_name'):
                        print(f"   ⚙️ {event_name}: {event.participant_name}")
                    else:
                        print(f"   ⚙️ {event_name}")
            
            # Mark all agents as completed
            for call in agent_calls:
                yield {
                    "type": "agent_complete",
                    "agent": call["agent"],
                    "status": "completed"
                }
            
            # Extract final output
            if output_event:
                output_messages = cast(list[ChatMessage], output_event.data)
                final_output = output_messages[-1].text if output_messages else "No output generated"
                print(f"\n\n{'='*70}")
                print(f"✅ Workflow Complete — {len(agent_calls)} agent calls")
                print(f"📄 Final output length: {len(final_output)} chars")
                print(f"   Preview: {final_output[:200]}...")
                print(f"{'='*70}")
            else:
                final_output = "No output generated"
                print("\n⚠️  WARNING: No WorkflowOutputEvent received — synthesis may be missing")
            
            # Send final result
            yield {
                "type": "complete",
                "workflow_run_id": workflow_run_id,
                "conversation_id": conversation_id,
                "final_output": final_output,
                "agent_calls": agent_calls
            }
            
    except Exception as e:
        yield {
            "type": "error",
            "message": str(e)
        }


# ============================================================================
# PARALLEL WORKFLOW — Calls all 3 agents concurrently, then synthesizes
# Expected: ~30s vs ~100s for Magentic sequential
# ============================================================================

async def _call_agent(agent, task: str, agent_name: str) -> dict:
    """Call a single Foundry agent and return its response with timing."""
    start = datetime.now()
    try:
        response = await agent.run(task)
        elapsed = (datetime.now() - start).total_seconds()
        return {
            "agent": agent_name,
            "text": response.text,
            "elapsed": elapsed,
            "status": "success",
        }
    except Exception as e:
        elapsed = (datetime.now() - start).total_seconds()
        return {
            "agent": agent_name,
            "text": f"Error: {str(e)}",
            "elapsed": elapsed,
            "status": "error",
        }


async def run_parallel_rfp_workflow_stream(user_query: str):
    """
    Parallel RFP workflow — runs all 3 specialist agents concurrently,
    then uses the orchestrator agent for synthesis.

    Architecture:
        Summary  ─┐
        Risk     ─┼─ (parallel, ~20s) → Orchestrator synthesis (~10s) = ~30s
        Compliance┘

    Emits the same SSE event types as the Magentic workflow for frontend compatibility.
    """
    workflow_run_id = f"rfp-parallel-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
    agent_calls: list[dict] = []
    wall_start = datetime.now()

    orchestrator_name = os.getenv("AZURE_AI_AGENT_ORCHESTRATOR", "rfp-orchestrator-agent")
    summary_name = os.getenv("AZURE_AI_AGENT_SUMMARY", "rfp-summary-agent")
    risk_name = os.getenv("AZURE_AI_AGENT_RISK", "rfp-risk-agent")
    compliance_name = os.getenv("AZURE_AI_AGENT_COMPLIANCE", "rfp-compliance-agent")

    try:
        async with (
            AzureCliCredential() as credential,
            AIProjectClient(endpoint=os.getenv("AZURE_AI_PROJECT_ENDPOINT"), credential=credential) as project_client,
        ):
            openai_client = project_client.get_openai_client()
            conversation = await openai_client.conversations.create()
            conversation_id = conversation.id

            yield {
                "type": "start",
                "workflow_run_id": workflow_run_id,
                "conversation_id": conversation_id,
                "query": user_query,
                "mode": "parallel",
            }

            # Load all agents
            provider = AzureAIProjectAgentProvider(project_client=project_client)
            orchestrator_agent = await provider.get_agent(name=orchestrator_name, default_options={"conversation_id": conversation_id})
            summary_agent = await provider.get_agent(name=summary_name, default_options={"conversation_id": conversation_id})
            risk_agent = await provider.get_agent(name=risk_name, default_options={"conversation_id": conversation_id})
            compliance_agent = await provider.get_agent(name=compliance_name, default_options={"conversation_id": conversation_id})

            # --- Phase 1: All 3 agents in parallel ---
            agent_task = f"""{user_query}

IMPORTANT: You have access to AI Search indexes containing the RFP documents.
Use your grounding tools to search for and retrieve the content. Do NOT ask for documents."""

            # Notify all 3 agents started simultaneously
            for name in [summary_name, risk_name, compliance_name]:
                yield {"type": "agent_start", "agent": name, "status": "processing"}

            print(f"\n🚀 [Parallel] Launching 3 agents concurrently...")
            parallel_start = datetime.now()

            results = await asyncio.gather(
                _call_agent(summary_agent, agent_task, summary_name),
                _call_agent(risk_agent, agent_task, risk_name),
                _call_agent(compliance_agent, agent_task, compliance_name),
            )

            parallel_elapsed = (datetime.now() - parallel_start).total_seconds()
            print(f"✅ [Parallel] All 3 agents done in {parallel_elapsed:.1f}s")

            # Emit completions and build agent_calls log
            for r in results:
                print(f"   {r['agent']}: {r['elapsed']:.1f}s | {len(r['text'])} chars | {r['status']}")
                agent_calls.append({
                    "workflow_run_id": workflow_run_id,
                    "conversation_id": conversation_id,
                    "agent": r["agent"],
                    "elapsed": r["elapsed"],
                    "timestamp": datetime.now().isoformat(),
                })
                yield {"type": "agent_complete", "agent": r["agent"], "status": "completed"}

            # --- Phase 2: Orchestrator synthesis ---
            yield {"type": "agent_start", "agent": orchestrator_name, "status": "processing"}

            summary_text = next(r["text"] for r in results if r["agent"] == summary_name)
            risk_text = next(r["text"] for r in results if r["agent"] == risk_name)
            compliance_text = next(r["text"] for r in results if r["agent"] == compliance_name)

            synthesis_prompt = f"""You are synthesizing the results of an RFP analysis performed by three specialist agents.
Below are their outputs. Combine them into a single comprehensive report.

## Summary Agent Output
{summary_text}

## Risk Agent Output
{risk_text}

## Compliance Agent Output
{compliance_text}

---
INSTRUCTIONS:
- Start with "## RFP Analysis — Executive Summary"
- Combine key findings from all three agents into a unified narrative
- Highlight the top 3 risks and top 3 compliance gaps
- End with a clear recommendation (bid / no-bid / conditional bid)
- Do NOT offer to help further. End with a polite closing.
"""

            print(f"\n🎯 [Parallel] Orchestrator synthesizing...")
            synth_start = datetime.now()
            synth_response = await orchestrator_agent.run(synthesis_prompt)
            synth_elapsed = (datetime.now() - synth_start).total_seconds()
            final_output = synth_response.text
            print(f"✅ [Parallel] Synthesis done in {synth_elapsed:.1f}s | {len(final_output)} chars")

            yield {"type": "agent_complete", "agent": orchestrator_name, "status": "completed"}

            total_elapsed = (datetime.now() - wall_start).total_seconds()
            print(f"\n{'='*70}")
            print(f"⏱️  Total wall time: {total_elapsed:.1f}s (parallel: {parallel_elapsed:.1f}s + synthesis: {synth_elapsed:.1f}s)")
            print(f"{'='*70}")

            yield {
                "type": "complete",
                "workflow_run_id": workflow_run_id,
                "conversation_id": conversation_id,
                "final_output": final_output,
                "agent_calls": agent_calls,
                "timing": {
                    "parallel_phase": round(parallel_elapsed, 1),
                    "synthesis_phase": round(synth_elapsed, 1),
                    "total": round(total_elapsed, 1),
                },
            }

    except Exception as e:
        import traceback
        traceback.print_exc()
        yield {"type": "error", "message": str(e)}


async def main():
    """Main entry point."""
    print("\n🚀 Magentic RFP Analysis Workflow")
    print("="*70)
    print("Pattern: Orchestrator → [Summary, Risk, Compliance] → Final Output")
    print("="*70)
    print("Modes: --parallel (fast, ~30s) | default (Magentic, ~100s)")
    print("="*70)
    
    # Check configuration
    endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    if not endpoint:
        print("\n❌ ERROR: AZURE_AI_PROJECT_ENDPOINT not set in .env")
        return
    
    print(f"\nProject Endpoint: {endpoint}")
    print(f"Orchestrator: {os.getenv('AZURE_AI_AGENT_ORCHESTRATOR', 'rfp-orchestrator-agent')}")
    print(f"Summary Agent: {os.getenv('AZURE_AI_AGENT_SUMMARY', 'rfp-summary-agent')}")
    print(f"Risk Agent: {os.getenv('AZURE_AI_AGENT_RISK', 'rfp-risk-agent')}")
    print(f"Compliance Agent: {os.getenv('AZURE_AI_AGENT_COMPLIANCE', 'rfp-compliance-agent')}")
    
    # User query - agents will use AI Search to retrieve RFP content
    user_query = "Analyze the Woodgrove Bank RFP and provide a summary, risk assessment, and compliance review"
    
    print(f"\n📝 User Query: {user_query}")
    
    try:
        # Run the Magentic workflow
        # Set interactive=True to pause and review orchestrator plans
        result = await run_magentic_rfp_workflow(user_query, interactive=False)
        
        # Print final results
        print(str(result))
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Run 'az login' to authenticate")
        print("2. Verify agents exist in Foundry with exact names:")
        print("   - rfp-orchestrator-agent")
        print("   - rfp-summary-agent")
        print("   - rfp-risk-agent")
        print("   - rfp-compliance-agent")
        print("3. Check AZURE_AI_PROJECT_ENDPOINT in .env")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
"""
Test if the orchestrator agent is working and can be traced
"""
import sys
from pathlib import Path

# Add agent directory to path
sys.path.insert(0, str(Path(__file__).parent / 'agent'))

from agent_session import AgentSession, Participant

def test_orchestrator():
    """Test the orchestrator agent directly"""
    
    print("\n" + "="*60)
    print("Testing rfp-orchestrator-agent")
    print("="*60)
    
    try:
        # Initialize orchestrator session
        print("\n[1] Initializing orchestrator agent...")
        session = AgentSession(
            session_id="test-orchestrator",
            agent_name="rfp-orchestrator-agent"
        )
        session.initialize()
        print(f"✓ Agent initialized: {session.agent.name}")
        
        # Create participant
        orchestrator = Participant(
            participant_id="TEST_USER",
            name="TestUser",
            type="user"
        )
        
        # Send test message
        print("\n[2] Sending test message...")
        test_message = "Hello! Can you confirm you are the RFP Orchestrator and describe your capabilities?"
        
        response = orchestrator.send_message(test_message, session)
        
        print(f"\n✓ Response received:")
        print(f"{'─'*60}")
        print(response)
        print(f"{'─'*60}")
        
        # Check conversation ID
        print(f"\n[3] Conversation details:")
        print(f"   Conversation ID: {session.conversation_id}")
        print(f"   Session ID: {session.session_id}")
        print(f"   Message count: {session.message_count}")
        
        if session.conversation_id:
            print(f"\n✅ SUCCESS! Check Azure AI Foundry:")
            print(f"   → Go to rfp-orchestrator-agent")
            print(f"   → Look for conversation ID: {session.conversation_id}")
        else:
            print(f"\n⚠️  WARNING: No conversation_id captured")
        
        # Close session
        session.close()
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_orchestrator()

"""
Agent Session Manager

This module provides a class for managing persistent agent sessions.
Use this when you want to keep an agent alive across multiple requests
(e.g., in a web application or API).

For beginners:
- A "session" is like a conversation that remembers what was said
- This class creates ONE agent and lets you send many messages to it
- The agent remembers all previous messages in the conversation

Updated to use the new Microsoft Foundry Agents API (azure.ai.projects)
"""

import os
from pathlib import Path
from typing import Optional, Any
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential, AzureCliCredential
from dotenv import load_dotenv

class AgentSession:
    """
    Manages a persistent chat agent session.
  
    - Create this once at the start of your application
    - Call send_message() as many times as you want
    - The agent remembers the entire conversation
    - Call close() when you're done (optional, for cleanup)
    
    Example usage:
        # Create session once
        session = AgentSession()
        await session.initialize()
        
        # Send many messages to the same agent
        response1 = await session.send_message("Hello!")
        response2 = await session.send_message("What's my name?")  # Agent remembers!
        response3 = await session.send_message("Tell me a joke")
        
        # Clean up when done
        await session.close()
    """
    
    def __init__(self, session_id: Optional[str] = None, instructions: Optional[str] = None, agent_name: Optional[str] = None, conversation_id: Optional[str] = None):
        """
        Initialize the agent session manager.
        
        Args:
            session_id: Optional identifier for this session (useful for logging)
            instructions: Optional custom instructions for the agent
            agent_name: Optional specific agent name to use (overrides AZURE_AI_AGENT_NAME env var)
            conversation_id: Optional conversation ID to continue an existing conversation
        """
        self.session_id = session_id or "default"
        self.project_client: Optional[AIProjectClient] = None
        self.agent: Optional[Any] = None
        self.conversation_id: Optional[str] = conversation_id  # Conversation ID from Responses API or passed in
        self.message_count = 0
        self.is_initialized = False
        # array of Participants
        self.participants = []
        self.custom_instructions = instructions
        self.agent_name = agent_name  # Store custom agent name
        
        # Load environment variables
        env_path = Path(__file__).parent.parent / '.env'
        load_dotenv(env_path)
    
    def initialize(self) -> None:
        """
        Initialize the agent. Call this once before sending messages.

        - This creates the agent and connects to Azure
        - You only need to call this ONCE
        - After this, you can send unlimited messages
        """
        if self.is_initialized:
            print(f"⚠️ Session {self.session_id} is already initialized")
            return

        # Get configuration
        endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
        
        if not endpoint:
            raise ValueError("AZURE_AI_PROJECT_ENDPOINT environment variable is required")
        
        # Create Azure credential for authentication (try AzureCliCredential first)
        try:
            credential = AzureCliCredential()
        except Exception:
            credential = DefaultAzureCredential()
        
        # Create project client
        self.project_client = AIProjectClient(
            endpoint=endpoint,
            credential=credential
        )
        
        # Get existing agent instead of creating a new one
        # Use custom agent_name if provided, otherwise fall back to env var
        agent_name = self.agent_name or os.getenv("AZURE_AI_AGENT_NAME", "rfp-summary-agent")
        self.agent = self.project_client.agents.get(agent_name=agent_name)
        
        print(f"✓ Using existing agent: {self.agent.name} (ID: {self.agent.id})")
        
        # Note: v2.0.0 API uses Responses API, not threads
        # Threads are managed automatically when using openai_client.responses.create()
        
        self.is_initialized = True
        print(f"✓ Agent session {self.session_id} initialized")
        
    
    
    def close(self) -> None:
        """
        Close the session and clean up resources.
        
        - Call this when you're done with the conversation
        - This is optional but good practice for cleanup
        """
        if self.project_client:
            print(f"✓ Session {self.session_id} closed after {self.message_count} messages")
            # Don't delete the agent since it's a pre-existing agent
            self.project_client.close()
            
        self.thread = None
        self.agent = None
        self.is_initialized = False
        
    
    def get_stats(self) -> dict:
        """
        Get statistics about this session.
        
        Returns:
            Dictionary with session statistics
        """
        return {
            "session_id": self.session_id,
            "conversation_id": self.conversation_id,
            "is_initialized": self.is_initialized,
            "message_count": self.message_count
        }
    
class Participant:
    """
    Represents a participant in the chat session.
    
    Attributes:
        id: Unique identifier for the participant e.g., ID_12345
        name: Display name of the participant
        type: "user" or "agent"
    """
    def __init__(self, participant_id: str, name: str, type: str = "user" or "agent"):
        self.id = participant_id
        self.name = name
        self.type = type

    def send_message(self, user_message: str, chat_session: AgentSession) -> str:
        """
        Send a message to the agent and get a response.

        - This uses the SAME agent every time
        - Conversation history is maintained by the Responses API
        - You can call this as many times as you want
        
        Args:
            user_message: The message from the user
            
        Returns:
            The agent's response as a string
        """
        if not chat_session.is_initialized:
            raise RuntimeError("Session not initialized. Call initialize() first.")
        
        if chat_session.agent is None or chat_session.project_client is None:
            raise RuntimeError("Agent or client not initialized. Call initialize() first.")
        
        # Increment message counter
        chat_session.message_count += 1

        # Add participant name to the message
        user_message = f"{self.name}: {user_message}"
        
        # Get OpenAI client for Responses API
        openai_client = chat_session.project_client.get_openai_client()
        
        # Build request body - include conversation_id if we have one to maintain context
        extra_body = {"agent": {"name": chat_session.agent.name, "type": "agent_reference"}}
        if chat_session.conversation_id:
            extra_body["conversation_id"] = chat_session.conversation_id
        
        # Use Responses API to send message
        response = openai_client.responses.create(
            input=user_message,
            extra_body=extra_body
        )
        
        # Store conversation ID for future messages to maintain context
        # Try multiple ways to get the conversation_id
        if hasattr(response, 'conversation_id') and response.conversation_id:
            chat_session.conversation_id = response.conversation_id
        elif hasattr(response, 'id'):
            # Some APIs return 'id' instead of 'conversation_id'
            chat_session.conversation_id = response.id
        
        # Debug: Print response structure to understand what we're getting
        print(f"   Response type: {type(response)}")
        if hasattr(response, '__dict__'):
            print(f"   Response attributes: {list(response.__dict__.keys())}")
        if chat_session.conversation_id:
            print(f"   Conversation ID captured: {chat_session.conversation_id}")
        else:
            print(f"   ⚠️  No conversation_id found in response")
        
        # Extract text from response
        if hasattr(response, 'output_text') and response.output_text:
            return response.output_text
        elif hasattr(response, 'output') and response.output:
            # Try to extract from output array
            for item in response.output:
                if hasattr(item, 'content'):
                    return str(item.content)
        
        return "No response from agent"

# Example usage for testing
def main():
    """
    Example showing how to use AgentSession.

    - This demonstrates creating ONE session
    - Sending multiple messages to it
    - The agent remembers the conversation
    """
    print("=" * 60)
    print("Agent Session Manager Example")
    print("=" * 60)
    
    # Create and initialize session ONCE
    session = AgentSession(session_id="example-session")
    session.initialize()
    participant_alice = Participant(participant_id="ID_001", name="Alice", type="user")
    participant_bob = Participant(participant_id="ID_002", name="Bob", type="user")
    
    # response1 = await participant_alice.send_message("Hello! My name is Alice. I want a pizza", session)
    # print("Hello! My name is Alice. I want a pizza")
    # print(f"Agent: {response1}")
    # response2 = await participant_bob.send_message("I'm Bob", session)
    # print("I'm Bob")
    # print(f"Agent: {response2}")
    # response3 = await participant_alice.send_message("I like Margherita pizza", session)
    # print("I like Margherita pizza")
    # print(f"Agent: {response3}")
    # response4 = await participant_bob.send_message("What pizza is Alice having? I want the same!", session)
    # print("What pizza is Alice having? I want the same!")
    # print(f"Agent: {response4}")

    response5 = participant_bob.send_message("what's the weather now in Seattle?", session)
    print("What's the weather now in Seattle?")
    print(f"Agent: {response5}")

    # Show statistics
    print("\n--- Session Statistics ---")
    stats = session.get_stats()
    print(f"Session ID: {stats['session_id']}")
    print(f"Conversation ID: {stats['conversation_id']}")
    print(f"Messages sent: {stats['message_count']}")
    
    # Clean up
    session.close()

if __name__ == "__main__":
    main()

"""
Agent Session Manager

This module provides a class for managing persistent agent sessions.
Use this when you want to keep an agent alive across multiple requests
(e.g., in a web application or API).

For beginners:
- A "session" is like a conversation that remembers what was said
- This class creates ONE agent and lets you send many messages to it
- The agent remembers all previous messages in the conversation
"""

import os
from pathlib import Path
from typing import Optional
from agent_framework import AgentThread, ChatAgent, HostedWebSearchTool
from agent_framework.azure import AzureAIAgentClient
from azure.identity import AzureCliCredential
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
    
    def __init__(self, session_id: Optional[str] = None):
        """
        Initialize the agent session manager.
        
        Args:
            session_id: Optional identifier for this session (useful for logging)
        """
        self.session_id = session_id or "default"
        self.agent: Optional[ChatAgent] = None
        self.message_count = 0
        self.is_initialized = False
        # array of Participants
        self.participants = []
        
        # Load environment variables
        env_path = Path(__file__).parent.parent / '.env'
        load_dotenv(env_path)
    
    async def initialize(self) -> None:
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
        deployment_name = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4o-mini")
        
        if not endpoint:
            raise ValueError("AZURE_AI_PROJECT_ENDPOINT environment variable is required")
        
        # Create Azure CLI credential for Entra ID authentication
        credential = AzureCliCredential()
        
        # Create chat client
        chat_client = AzureAIAgentClient(
            project_endpoint=endpoint,
            model_deployment_name=deployment_name,
            credential=credential
        )
        
        # Create the agent (this is created ONCE and reused)
        self.agent = ChatAgent(
            chat_client=chat_client,
            name="AndreeaSessionAgent",
            instructions="""
            You are a friendly and helpful assistant. You don't always have to be the nicest :) 
            Keep your responses clear and concise. 
            Don't add weird formatting. Just normal text. 
            Be professional but warm in your tone (some humour SOMETIMES is also welcome - think where you see it fit and where not).
            Remember the conversation context and refer back to it when relevant.
            Take into account who you are replying to (see as <name>: <message>). There sometimes MAY be multiple participants.
            Do not make up participant names or identities.
            You don't have to call the participant by their name every time. Use it only when it makes sense in the conversation. 
            """,
            tools=[HostedWebSearchTool()],
        )
        
        #validate agent
        print("AGENT NAME")
        print(self.agent.name)
        # Create a thread for this session to manage conversation history
        self.thread = self.agent.get_new_thread()
        
        self.is_initialized = True
        print(f"✓ Agent session {self.session_id} initialized with thread ID: {self.thread.service_thread_id}")
    
    
    async def close(self) -> None:
        """
        Close the session and clean up resources.
        
        - Call this when you're done with the conversation
        - This is optional but good practice for cleanup
        """
        if self.agent:
            print(f"✓ Session {self.session_id} closed after {self.message_count} messages")
            await self.agent.chat_client.close()
            
        self.thread = None
        self.is_initialized = False
        
    
    def get_stats(self) -> dict:
        """
        Get statistics about this session.
        
        Returns:
            Dictionary with session statistics
        """
        return {
            "session_id": self.session_id,
            "thread_id": self.thread.service_thread_id if self.thread else None,
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

    async def send_message(self, user_message: str, chat_session: AgentSession) -> str:
        """
        Send a message to the agent and get a response using the thread.

        - This uses the SAME agent and thread every time
        - The thread maintains conversation history
        - You can call this as many times as you want
        
        Args:
            user_message: The message from the user
            
        Returns:
            The agent's response as a string
        """
        if not chat_session.is_initialized or chat_session.agent is None or chat_session.thread is None:
            raise RuntimeError("Session not initialized. Call initialize() first.")
        
        # Increment message counter
        chat_session.message_count += 1

        # at the beginning of their message, add their name -> also see Instruction of agent :) Like this it will take into account who is speaking
        user_message = f"{self.name}: {user_message}"
        
        # Send to the agent using the thread for conversation history
        response = await chat_session.agent.run(user_message, thread=chat_session.thread, user_id=self.id)
        
        return response

# Example usage for testing
async def main():
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
    await session.initialize()
    
    participant_alice = Participant(participant_id="ID_001", name="Alice", type="user")
    participant_bob = Participant(participant_id="ID_002", name="Bob", type="user")
    
    response1 = await participant_alice.send_message("Hello! My name is Alice. I want a pizza", session)
    print("Hello! My name is Alice. I want a pizza")
    print(f"Agent: {response1}")
    response2 = await participant_bob.send_message("I'm Bob", session)
    print("I'm Bob")
    print(f"Agent: {response2}")
    response3 = await participant_alice.send_message("I like Margherita pizza", session)
    print("I like Margherita pizza")
    print(f"Agent: {response3}")
    response4 = await participant_bob.send_message("What pizza is Alice having? I want the same!", session)
    print("What pizza is Alice having? I want the same!")
    print(f"Agent: {response4}")

    if False:
        # Send multiple messages to the SAME agent
        print("\n--- Message 1 ---")
        response1 = await session.send_message("Hi! My name is Alice.")
        print(f"Agent: {response1}")
        
        print("\n--- Message 2 ---")
        response2 = await session.send_message("What's my name?")
        print(f"Agent: {response2}")
        print("(Notice: The agent remembered your name!)")
        
        print("\n--- Message 3 ---")
        response3 = await session.send_message("Can you tell me a short joke?")
        print(f"Agent: {response3}")
        
        # Show statistics
        print("\n--- Session Statistics ---")
        stats = session.get_stats()
        print(f"Session ID: {stats['session_id']}")
        print(f"Thread ID: {stats['thread_id']}")
        print(f"Messages sent: {stats['message_count']}")
    
    # Clean up
    await session.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

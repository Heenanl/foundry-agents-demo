import React, { useState, useEffect } from 'react';
import './App.css';

const API_URL = 'http://localhost:8000';

const PARTICIPANT_COLORS = [
  '#FFB6C1', '#FFD4B2', '#FFF4B2', '#BAE4FF', '#BAFFC9',
  '#D4BAFF', '#FFB3E6', '#B3E5FC', '#C5E1A5', '#F8BBD0',
  '#FFCCBC', '#D1C4E9', '#B2DFDB', '#FFF9C4', '#F0F4C3'
];

function App() {
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [backendParticipants, setBackendParticipants] = useState([]);
  const [selectedParticipant, setSelectedParticipant] = useState(null);
  const [participantCounter, setParticipantCounter] = useState(1);
  const [sessionInitialized, setSessionInitialized] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Initialize session when app loads
  useEffect(() => {
    initializeSession();
  }, []);

  // Initialize the backend session
  const initializeSession = async () => {
    try {
      const response = await fetch(`${API_URL}/api/session/init`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: 'webapp-session-' + Date.now()
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('Session initialized:', data);
        setSessionInitialized(true);
        
        // Sync participants from backend
        await syncParticipants();
      } else {
        console.error('Failed to initialize session');
      }
    } catch (error) {
      console.error('Error initializing session:', error);
    }
  };

  // Sync participants from backend
  const syncParticipants = async () => {
    try {
      const response = await fetch(`${API_URL}/api/participants/list`);
      
      if (response.ok) {
        const backendParticipantsList = await response.json();
        
        // Map backend participants to frontend format (add colors)
        const syncedParticipants = backendParticipantsList.map((p, index) => ({
          id: p.participant_id,
          name: p.name,
          type: p.type,
          color: PARTICIPANT_COLORS[index % PARTICIPANT_COLORS.length]
        }));
        
        setBackendParticipants(syncedParticipants);
        
        // Update counter based on existing participants
        if (syncedParticipants.length > 0) {
          // Extract highest ID number
          const maxId = Math.max(...syncedParticipants.map(p => {
            const match = p.id.match(/ID_(\d+)/);
            return match ? parseInt(match[1]) : 0;
          }));
          setParticipantCounter(maxId + 1);
        }
        
        console.log('Participants synced:', syncedParticipants);
      }
    } catch (error) {
      console.error('Error syncing participants:', error);
    }
  };
  
  // Modal state for adding participant
  const [showParticipantForm, setShowParticipantForm] = useState(false);
  const [participantForm, setParticipantForm] = useState({
    name: ''
  });

  // Show the add participant form
  const handleShowParticipantForm = () => {
    setParticipantForm({
      name: ''
    });
    setShowParticipantForm(true);
  };

  // Handle form input changes
  const handleFormChange = (field, value) => {
    setParticipantForm({
      ...participantForm,
      [field]: value
    });
  };

  // Add a new participant from the form
  const handleAddParticipant = async () => {
    if (!participantForm.name.trim()) {
      alert('Please enter a participant name');
      return;
    }
    
    if (!sessionInitialized) {
      alert('Session not initialized. Please wait...');
      return;
    }
    
    // Auto-generate ID and set type to 'user'
    const participantId = `ID_${String(participantCounter).padStart(5, '0')}`;
    const newParticipant = {
      id: participantId,
      name: participantForm.name.trim(),
      type: 'user',
      color: PARTICIPANT_COLORS[backendParticipants.length % PARTICIPANT_COLORS.length]
    };
    
    try {
      // Add participant to backend
      const response = await fetch(`${API_URL}/api/participants/add`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          participant_id: newParticipant.id,
          name: newParticipant.name,
          type: newParticipant.type
        })
      });
      
      if (response.ok) {
        setParticipantCounter(participantCounter + 1);
        setShowParticipantForm(false);
        
        // Refresh participants from backend
        await syncParticipants();
        
        // Auto-select the first participant
        if (backendParticipants.length === 0) {
          setSelectedParticipant(newParticipant);
        }
      } else {
        alert('Failed to add participant');
      }
    } catch (error) {
      console.error('Error adding participant:', error);
      alert('Error adding participant');
    }
  };

  // Cancel adding participant
  const handleCancelForm = () => {
    setShowParticipantForm(false);
  };

  // Remove a participant
  const handleRemoveParticipant = async (participantId) => {
    if (!sessionInitialized) {
      alert('Session not initialized');
      return;
    }
    
    try {
      // Remove participant from backend
      const response = await fetch(`${API_URL}/api/participants/${participantId}`, {
        method: 'DELETE',
      });
      
      if (response.ok) {
        // Refresh participants from backend
        await syncParticipants();
        
        // If we removed the selected participant, select another one or none
        if (selectedParticipant && selectedParticipant.id === participantId) {
          const remainingParticipants = backendParticipants.filter(p => p.id !== participantId);
          setSelectedParticipant(remainingParticipants.length > 0 ? remainingParticipants[0] : null);
        }
      } else {
        alert('Failed to remove participant');
      }
    } catch (error) {
      console.error('Error removing participant:', error);
      alert('Error removing participant');
    }
  };

  // Select a participant to chat as
  const handleSelectParticipant = (participant) => {
    setSelectedParticipant(participant);
  };

  const handleSend = async () => {
    if (inputText.trim() === '') return;
    
    if (!selectedParticipant) {
      alert('Please select a participant first!');
      return;
    }
    
    if (!sessionInitialized) {
      alert('Session not initialized. Please wait...');
      return;
    }
    
    const userMessage = {
      text: inputText,
      sender: 'participant',
      participant: selectedParticipant,
      timestamp: new Date()
    };
    
    setMessages([...messages, userMessage]);
    
    const messageToSend = inputText;
    setInputText('');
    setIsLoading(true);
    
    try {
      const response = await fetch(`${API_URL}/api/messages/send`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          participant_id: selectedParticipant.id,
          message: messageToSend
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        
        const botMessage = {
          text: data.message,
          sender: 'bot',
          timestamp: new Date()
        };
        
        setMessages(prevMessages => [...prevMessages, botMessage]);
      } else {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        console.error('Send message failed:', errorData);
        alert(`Failed to send message: ${errorData.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      alert('Error sending message');
    } finally {
      setIsLoading(false);
    }
  };

  const handleInputChange = (e) => {
    setInputText(e.target.value);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSend();
    }
  };

  // This function runs when user clicks the upload button
  const handleUpload = () => {
    // Placeholder function - you can add file upload logic here later
    alert('Upload feature coming soon!');
  };

  // This is what gets shown on the screen (the UI)
  return (
    <div className="container">
      {/* Left side - Chat interface */}
      <div className="App">
        {/* Header bar with the Geekster logo in the top right */}
        <header className="header">
          <h1>Echo Chat</h1>
          {/* Logo image - files in the public folder are accessed with /filename */}
          <img 
            src="/geekster.png" 
            alt="Geekster Logo" 
            className="logo" 
          />
        </header>

      {/* Main chat area where messages appear */}
      <div className="chat-container">
        {/* Loop through each message in our messages array and display it */}
        {messages.map((message, index) => (
          // Each message gets its own div (box)
          // The key helps React keep track of each message
          // The className changes based on who sent it (participant or bot)
          <div 
            key={index} 
            className={`message ${message.sender}`}
          >
            {/* Show avatar image based on who sent the message */}
            {message.sender === 'bot' && (
              <img 
                src="/geekster_head.png" 
                alt="Geekster" 
                className="avatar" 
              />
            )}
            <div className="message-content">
              {/* Show participant name above their messages */}
              {message.sender === 'participant' && message.participant && (
                <div className="participant-name" style={{ color: message.participant.color }}>
                  {message.participant.name}
                </div>
              )}
              <div 
                className="message-text"
                style={message.sender === 'participant' && message.participant 
                  ? { backgroundColor: message.participant.color } 
                  : {}
                }
              >
                {message.text}
              </div>
            </div>
            {message.sender === 'participant' && (
              <div 
                className="avatar participant-avatar" 
                style={{ backgroundColor: message.participant?.color || '#ddd' }}
              >
                {message.participant?.name?.charAt(0).toUpperCase() || '?'}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Bottom section where user types and sends messages */}
      <div className="input-container">
        {/* Upload document button - currently just a placeholder */}
        <button onClick={handleUpload} className="upload-button" title="Upload Document">
          📎
        </button>
        {/* Text input box */}
        <input
          type="text"
          value={inputText}              // Show the current inputText
          onChange={handleInputChange}   // Update inputText when user types
          onKeyPress={handleKeyPress}    // Check if user pressed Enter
          placeholder="Type a message..." // Gray hint text when empty
          className="input-box"
        />
        {/* Send button */}
        <button onClick={handleSend} className="send-button" disabled={isLoading}>
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </div>
    </div>

    {/* Right side - Participant Management with Honeycomb */}
    <div className="participant-section">
      <div className="participant-header">
        <h2>Participants</h2>
        <button onClick={handleShowParticipantForm} className="add-participant-button">
          + Add Participant
        </button>
      </div>
      
      {/* Participant Form Modal */}
      {showParticipantForm && (
        <div className="modal-overlay" onClick={handleCancelForm}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>Add New Participant</h3>
            <div className="form-group">
              <label>Name:</label>
              <input
                type="text"
                value={participantForm.name}
                onChange={(e) => handleFormChange('name', e.target.value)}
                placeholder="e.g., Alice"
                className="form-input"
                autoFocus
              />
            </div>
            <div className="form-buttons">
              <button onClick={handleCancelForm} className="cancel-button">
                Cancel
              </button>
              <button onClick={handleAddParticipant} className="submit-button">
                Add Participant
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* Honeycomb structure for participants */}
      <div className="honeycomb-container">
        {backendParticipants.length === 0 ? (
          <div className="no-participants">
            <p>No participants yet</p>
            <p className="hint">Click "Add Participant" to get started</p>
          </div>
        ) : (
          <div className="honeycomb">
            {backendParticipants.map((participant, index) => (
              <div
                key={participant.id}
                className={`hexagon ${selectedParticipant?.id === participant.id ? 'selected' : ''}`}
                style={{ 
                  backgroundColor: participant.color,
                  animationDelay: `${index * 0.1}s`
                }}
                onClick={() => handleSelectParticipant(participant)}
                onContextMenu={(e) => {
                  e.preventDefault();
                  if (window.confirm(`Remove ${participant.name}?`)) {
                    handleRemoveParticipant(participant.id);
                  }
                }}
                title={`Name: ${participant.name}\nID: ${participant.id}\nType: ${participant.type}\n\nLeft-click to select\nRight-click to remove`}
              >
                <div className="hexagon-content">
                  <div className="participant-initial">
                    {participant.name.charAt(0).toUpperCase()}
                  </div>
                  <div className="participant-label">{participant.name}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      
      {/* Selected participant indicator */}
      {selectedParticipant && (
        <div className="selected-indicator">
          <div className="indicator-label">Currently chatting as:</div>
          <div 
            className="indicator-badge"
            style={{ backgroundColor: selectedParticipant.color }}
          >
            <span className="indicator-initial">
              {selectedParticipant.name.charAt(0).toUpperCase()}
            </span>
            <span className="indicator-name">{selectedParticipant.name}</span>
          </div>
        </div>
      )}
    </div>
  </div>
  );
}

// Export our App so other files can use it (like index.js)
export default App;

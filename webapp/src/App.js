// Import React and the special "useState" hook that lets us save and update data
import React, { useState } from 'react';
// Import our styling file that makes things look pretty
import './App.css';

// This is our main App component - think of it as the whole chat application
function App() {
  // useState is a "hook" that creates a variable that React watches
  // messages: an array (list) that holds all our chat messages
  // setMessages: a function we call to update the messages array
  // useState([]) means we start with an empty array
  const [messages, setMessages] = useState([]);
  
  // inputText: holds whatever the user is currently typing
  // setInputText: function to update what the user is typing
  // useState('') means we start with an empty string (no text)
  const [inputText, setInputText] = useState('');

  // This function runs when the user clicks "Send" or presses Enter
  const handleSend = () => {
    // Check if the input is empty or just spaces - if so, don't do anything
    if (inputText.trim() === '') return;
    
    // Create a new message object with the text the user typed
    const userMessage = {
      text: inputText,        // The actual message text
      sender: 'user',         // Mark this as coming from the user
      timestamp: new Date()   // Save when this message was sent
    };
    
    // Add the user's message to our messages array
    // ...messages means "copy all existing messages"
    // then we add userMessage at the end
    setMessages([...messages, userMessage]);
    
    // After a 1 second delay (1000 milliseconds), send back an echo
    setTimeout(() => {
      // Create the bot's echo response
      const botMessage = {
        text: `Echo: ${inputText}`,  // Repeat what the user said with "Echo:" in front
        sender: 'bot',                // Mark this as coming from the bot
        timestamp: new Date()         // Save when this message was sent
      };
      
      // Add the bot's message to our messages array
      // We use a function here to make sure we have the latest messages
      setMessages(prevMessages => [...prevMessages, botMessage]);
    }, 1000); // 1000 milliseconds = 1 second
    
    // Clear the input box so the user can type a new message
    setInputText('');
  };

  // This function runs every time the user types in the input box
  const handleInputChange = (e) => {
    // e.target.value is the current text in the input box
    setInputText(e.target.value);
  };

  // This function runs when the user presses a key in the input box
  const handleKeyPress = (e) => {
    // If the user pressed Enter (key code 'Enter'), send the message
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
          // The className changes based on who sent it (user or bot)
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
            <div className="message-text">{message.text}</div>
            {message.sender === 'user' && (
              <img 
                src="/geekster_laptop.png" 
                alt="User" 
                className="avatar" 
              />
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
        <button onClick={handleSend} className="send-button">
          Send
        </button>
      </div>
    </div>

    {/* Right side - Placeholder section with rainbow gradient */}
    <div className="placeholder-section">
      <div className="placeholder-content">
        <h2>Coming Soon</h2>
        <p>Future features will appear here</p>
      </div>
    </div>
  </div>
  );
}

// Export our App so other files can use it (like index.js)
export default App;

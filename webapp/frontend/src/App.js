import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import ChatPage from './ChatPage';
import FormChecker from './FormChecker';
import MagenticWorkflow from './MagenticWorkflow';
import MagenticWorkflowWithChat from './MagenticWorkflowWithChat';
import './App.css';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<ChatPage />} />
        <Route path="/form-checker" element={<FormChecker />} />
        <Route path="/magentic" element={<MagenticWorkflowWithChat />} />
        <Route path="/magentic-workflow" element={<MagenticWorkflow />} />
      </Routes>
    </Router>
  );
}

// Export our App so other files can use it (like index.js)
export default App;

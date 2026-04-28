import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import MagenticWorkflow from './MagenticWorkflow';
import './App.css';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Navigate to="/magentic" replace />} />
        <Route path="/magentic" element={<MagenticWorkflow />} />
      </Routes>
    </Router>
  );
}

export default App;

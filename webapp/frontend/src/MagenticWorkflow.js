import React, { useState } from 'react';
import './MagenticWorkflow.css';

function MagenticWorkflow() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [outputs, setOutputs] = useState([]);
  const [agentStatus, setAgentStatus] = useState({
    orchestrator: 'pending',
    summary: 'pending',
    risk: 'pending',
    compliance: 'pending'
  });

  const steps = [
    { key: 'orchestrator', label: 'Orchestrator Agent' },
    { key: 'summary', label: 'Summary Agent' },
    { key: 'risk', label: 'Risk Agent' },
    { key: 'compliance', label: 'Compliance Agent' }
  ];

  const startAnalysis = async () => {
    if (!query.trim()) {
      alert('Please enter an RFP query');
      return;
    }

    setLoading(true);
    setResults(null);
    setAgentStatus({
      orchestrator: 'pending',
      summary: 'pending',
      risk: 'pending',
      compliance: 'pending'
    });
    setOutputs([{
      time: new Date().toLocaleTimeString(),
      message: `RFP query submitted: "${query.substring(0, 50)}..."`
    }]);

    // Mark orchestrator as processing
    setAgentStatus(prev => ({ ...prev, orchestrator: 'processing' }));

    try {
      const response = await fetch('http://localhost:8000/api/magentic/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: query,
          interactive: false
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Analysis failed');
      }

      const data = await response.json();
      
      // Update agent status based on agent_calls
      const completedAgents = new Set();
      if (data.agent_calls) {
        data.agent_calls.forEach(call => {
          // Backend uses 'agent' field, not 'agent_name'
          const agentName = call.agent || call.agent_name;
          if (!agentName) return;
          
          const agentLower = agentName.toLowerCase();
          // Map backend agent names to our status keys
          if (agentLower.includes('orchestrator')) completedAgents.add('orchestrator');
          else if (agentLower.includes('summary')) completedAgents.add('summary');
          else if (agentLower.includes('risk')) completedAgents.add('risk');
          else if (agentLower.includes('compliance')) completedAgents.add('compliance');
        });
      }
      
      // Mark all completed agents
      setAgentStatus({
        orchestrator: completedAgents.has('orchestrator') ? 'completed' : 'pending',
        summary: completedAgents.has('summary') ? 'completed' : 'pending',
        risk: completedAgents.has('risk') ? 'completed' : 'pending',
        compliance: completedAgents.has('compliance') ? 'completed' : 'pending'
      });
      
      setResults(data);
      setOutputs(prev => [...prev, {
        time: new Date().toLocaleTimeString(),
        message: 'Analysis completed successfully'
      }]);

    } catch (err) {
      setOutputs(prev => [...prev, {
        time: new Date().toLocaleTimeString(),
        message: `Error: ${err.message}`,
        error: true
      }]);
      setAgentStatus({
        orchestrator: 'pending',
        summary: 'pending',
        risk: 'pending',
        compliance: 'pending'
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="magentic-wrapper">
      <div className="connected-badge">
        <span className="status-dot"></span>
        CONNECTED
      </div>

      <div className="magentic-container">
        <div className="upload-section">
          <div className="upload-box">
            <h3>RFP Analysis Query</h3>
            <textarea
              className="query-input"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter your RFP analysis query here..."
              rows="4"
            />
            <button className="start-button" onClick={startAnalysis} disabled={loading}>
              {loading ? 'Analyzing...' : 'Start Magentic Analysis'}
            </button>
          </div>
        </div>

        {loading && (
          <div className="progress-section">
            <div className="section-header">
              <span className="icon">📊</span>
              <h2>Analysis Progress</h2>
            </div>
            <div className="spinner-container">
              <div className="spinner"></div>
              <p className="spinner-text">Processing RFP Analysis...</p>
            </div>
            <div className="steps-container">
              {steps.map((step) => (
                <div
                  key={step.key}
                  className={`step ${agentStatus[step.key] === 'completed' ? 'completed' : agentStatus[step.key] === 'processing' ? 'active' : ''}`}
                >
                  {step.label}
                </div>
              ))}
            </div>
          </div>
        )}

        {results && (
          <div className="success-banner">
            <h1>RFP Analysis Completed! ✓</h1>
          </div>
        )}

        {results && (
          <div className="report-container">
            <div className="report-left">
              <h3>Analysis Summary</h3>
              <div className="summary-item">
                <strong>Conversation ID:</strong>
                <p>{results.conversation_id || 'N/A'}</p>
              </div>
              <div className="summary-item">
                <strong>Workflow Run ID:</strong>
                <p>{results.workflow_run_id || 'N/A'}</p>
              </div>
              <div className="summary-item">
                <strong>Agent Calls:</strong>
                <p>{results.agent_calls ? results.agent_calls.length : 0} agents executed</p>
              </div>
              <button className="copy-button" onClick={() => {
                const reportText = results.final_output || 'No report available';
                navigator.clipboard.writeText(reportText);
                alert('Report copied to clipboard!');
              }}>
                📋 Copy Full Report
              </button>
            </div>
            <div className="report-right">
              <h3>Generated Report</h3>
              <div className="report-content">
                {results.final_output || 'No report generated'}
              </div>
            </div>
          </div>
        )}

        {outputs.length > 0 && (
          <div className="outputs-section">
            <div className="section-header">
              <span className="icon">📝</span>
              <h2>Analysis Outputs</h2>
            </div>
            <div className="outputs-list">
              {outputs.map((output, index) => (
                <div key={index} className={`output-item ${output.error ? 'error' : ''}`}>
                  <div className="output-border"></div>
                  <div className="output-content">
                    <div className="output-time">{output.time}</div>
                    <div className="output-message">{output.message}</div>
                  </div>
                </div>
              ))}

              {results && results.agent_calls && results.agent_calls.map((call, idx) => (
                <div key={`call-${idx}`} className="output-item">
                  <div className="output-border"></div>
                  <div className="output-content">
                    <div className="output-time">{call.timestamp}</div>
                    <div className="output-label">{call.agent || call.agent_name || 'Agent'}</div>
                    <div className="output-message">{call.agent_response || 'Processing...'}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default MagenticWorkflow;

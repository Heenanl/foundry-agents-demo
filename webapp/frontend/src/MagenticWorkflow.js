import React, { useState } from 'react';
import './MagenticWorkflow.css';

function MagenticWorkflow() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [outputs, setOutputs] = useState([]);
  const [mode, setMode] = useState('parallel'); // 'parallel' (fast) or 'magentic' (orchestrated)
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

    try {
      // Use EventSource for Server-Sent Events streaming
      const streamUrl = mode === 'parallel'
        ? `http://localhost:8000/api/parallel/analyze/stream?query=${encodeURIComponent(query)}`
        : `http://localhost:8000/api/magentic/analyze/stream?query=${encodeURIComponent(query)}`;
      const eventSource = new EventSource(streamUrl);

      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('SSE Event:', data);

        if (data.type === 'start') {
          setOutputs(prev => [...prev, {
            time: new Date().toLocaleTimeString(),
            message: `Workflow started: ${data.workflow_run_id}`
          }]);
        } 
        else if (data.type === 'agent_start') {
          const agentName = data.agent.toLowerCase();
          console.log(`Agent starting: ${data.agent}`);
          
          setOutputs(prev => [...prev, {
            time: new Date().toLocaleTimeString(),
            message: `${data.agent} started processing...`
          }]);

          // Update status to processing
          if (agentName.includes('orchestrator')) {
            setAgentStatus(prev => ({ ...prev, orchestrator: 'processing' }));
          } else if (agentName.includes('summary')) {
            setAgentStatus(prev => ({ ...prev, summary: 'processing' }));
          } else if (agentName.includes('risk')) {
            setAgentStatus(prev => ({ ...prev, risk: 'processing' }));
          } else if (agentName.includes('compliance')) {
            setAgentStatus(prev => ({ ...prev, compliance: 'processing' }));
          }
        }
        else if (data.type === 'agent_complete') {
          const agentName = data.agent.toLowerCase();
          console.log(`Agent completed: ${data.agent}`);
          
          setOutputs(prev => [...prev, {
            time: new Date().toLocaleTimeString(),
            message: `✓ ${data.agent} completed`
          }]);

          // Update status to completed
          if (agentName.includes('orchestrator')) {
            setAgentStatus(prev => ({ ...prev, orchestrator: 'completed' }));
          } else if (agentName.includes('summary')) {
            setAgentStatus(prev => ({ ...prev, summary: 'completed' }));
          } else if (agentName.includes('risk')) {
            setAgentStatus(prev => ({ ...prev, risk: 'completed' }));
          } else if (agentName.includes('compliance')) {
            setAgentStatus(prev => ({ ...prev, compliance: 'completed' }));
          }
        }
        else if (data.type === 'complete') {
          console.log('Workflow complete');
          setResults({
            workflow_run_id: data.workflow_run_id,
            conversation_id: data.conversation_id,
            final_output: data.final_output,
            agent_calls: data.agent_calls
          });
          
          // Mark orchestrator as completed when workflow finishes
          setAgentStatus(prev => ({ ...prev, orchestrator: 'completed' }));
          
          setOutputs(prev => [...prev, {
            time: new Date().toLocaleTimeString(),
            message: 'Analysis completed successfully!'
          }]);
          
          eventSource.close();
          setLoading(false);
        }
        else if (data.type === 'error') {
          console.error('Workflow error:', data.message);
          setOutputs(prev => [...prev, {
            time: new Date().toLocaleTimeString(),
            message: `Error: ${data.message}`,
            error: true
          }]);
          eventSource.close();
          setLoading(false);
        }
      };

      eventSource.onerror = (error) => {
        console.error('EventSource error:', error);
        setOutputs(prev => [...prev, {
          time: new Date().toLocaleTimeString(),
          message: 'Connection error occurred',
          error: true
        }]);
        eventSource.close();
        setLoading(false);
      };

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
            <div className="mode-toggle">
              <button
                className={`mode-btn ${mode === 'parallel' ? 'active' : ''}`}
                onClick={() => setMode('parallel')}
                disabled={loading}
              >
                ⚡ Parallel (Fast)
              </button>
              <button
                className={`mode-btn ${mode === 'magentic' ? 'active' : ''}`}
                onClick={() => setMode('magentic')}
                disabled={loading}
              >
                🎯 Magentic (Orchestrated)
              </button>
            </div>
            <textarea
              className="query-input"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter your RFP analysis query here..."
              rows="4"
            />
            <button className="start-button" onClick={startAnalysis} disabled={loading}>
              {loading ? 'Analyzing...' : mode === 'parallel' ? '⚡ Start Parallel Analysis' : '🎯 Start Magentic Analysis'}
            </button>
          </div>
        </div>

        {(loading || results) && (
          <div className="progress-section">
            <div className="section-header">
              <span className="icon">📊</span>
              <h2>Analysis Progress</h2>
            </div>
            {loading && (
              <div className="spinner-container">
                <div className="spinner"></div>
                <p className="spinner-text">Processing RFP Analysis...</p>
              </div>
            )}
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
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default MagenticWorkflow;

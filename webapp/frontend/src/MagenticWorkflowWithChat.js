import React, { useState, useEffect, useRef } from 'react';
import './MagenticWorkflow.css';

function MagenticWorkflowWithChat() {
  // Chat state
  const [chatInput, setChatInput] = useState('');
  const [chatHistory, setChatHistory] = useState([
    { sender: 'bot', text: "Hello! I'm the RFP Orchestrator. Ask me questions or say 'Analyze this RFP' to start a full analysis." }
  ]);
  const [chatLoading, setChatLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const chatEndRef = useRef(null);

  // Workflow state
  const [workflowActive, setWorkflowActive] = useState(false);
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

  // Scroll to bottom of chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

  const handleChatSubmit = async (e) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const userMessage = chatInput;
    setChatInput('');
    setChatHistory(prev => [...prev, { sender: 'user', text: userMessage }]);
    setChatLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/magentic/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message: userMessage,
          session_id: sessionId 
        })
      });
      
      if (!response.ok) {
        let errorMessage = `Server responded with ${response.status}`;
        try {
          const errorData = await response.json();
          if (errorData.detail) {
            errorMessage = errorData.detail;
          }
        } catch (e) {
          // Ignore parse error
        }
        throw new Error(errorMessage);
      }

      const data = await response.json();
      
      if (!sessionId) setSessionId(data.session_id);
      
      setChatHistory(prev => [...prev, { sender: 'bot', text: data.response }]);
      
      // Check if we should trigger the workflow
      if (data.trigger_workflow) {
        setWorkflowActive(true);
        setQuery(userMessage);
        setTimeout(() => {
          startAnalysis(userMessage);
        }, 500);
      }
      
    } catch (error) {
      console.error('Chat error:', error);
      setChatHistory(prev => [...prev, { 
        sender: 'bot', 
        text: `Error: ${error.message}` 
      }]);
    } finally {
      setChatLoading(false);
    }
  };

  const startAnalysis = async (initialQuery) => {
    const queryToUse = initialQuery || query;
    if (!queryToUse.trim()) {
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
      message: `RFP query submitted: "${queryToUse.substring(0, 50)}..."`
    }]);

    try {
      const eventSource = new EventSource(
        `http://localhost:8000/api/magentic/analyze/stream?query=${encodeURIComponent(queryToUse)}`
      );

      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === 'start') {
          setOutputs(prev => [...prev, {
            time: new Date().toLocaleTimeString(),
            message: `Workflow started: ${data.workflow_run_id}`
          }]);
        } 
        else if (data.type === 'agent_start') {
          const agentName = data.agent.toLowerCase();
          
          setOutputs(prev => [...prev, {
            time: new Date().toLocaleTimeString(),
            message: `${data.agent} started processing...`
          }]);

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
          
          setOutputs(prev => [...prev, {
            time: new Date().toLocaleTimeString(),
            message: `✓ ${data.agent} completed`
          }]);

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
          setResults({
            workflow_run_id: data.workflow_run_id,
            conversation_id: data.conversation_id,
            final_output: data.final_output,
            agent_calls: data.agent_calls
          });
          
          setAgentStatus(prev => ({ ...prev, orchestrator: 'completed' }));
          
          setOutputs(prev => [...prev, {
            time: new Date().toLocaleTimeString(),
            message: 'Analysis completed successfully!'
          }]);
          
          // Add final report to chat history
          setChatHistory(prev => [...prev, { 
            sender: 'bot', 
            text: '✅ Analysis complete! See the detailed report below.' 
          }]);
          
          setLoading(false);
          eventSource.close();
        }
        else if (data.type === 'error') {
          setOutputs(prev => [...prev, {
            time: new Date().toLocaleTimeString(),
            message: `Error: ${data.message}`,
            error: true
          }]);
          setLoading(false);
          eventSource.close();
        }
      };

      eventSource.onerror = () => {
        setOutputs(prev => [...prev, {
          time: new Date().toLocaleTimeString(),
          message: 'Connection error occurred',
          error: true
        }]);
        setLoading(false);
        eventSource.close();
      };
    } catch (error) {
      console.error('Error starting workflow:', error);
      setLoading(false);
    }
  };

  return (
    <div className="magentic-wrapper">
      <div className="connected-badge">
        <span className="status-dot"></span>
        CONNECTED
      </div>

      <div className="magentic-container unified-mode">
        <header className="magentic-header">
          <h1>💬 RFP Orchestrator Chat & Analysis</h1>
          <p>Chat with the orchestrator or request a full Magentic workflow analysis</p>
        </header>

        {/* CHAT INTERFACE - Always visible at top */}
        <div className="chat-section">
          <div className="chat-interface">
            <div className="chat-messages">
              {chatHistory.map((msg, index) => (
                <div key={index} className={`message ${msg.sender}`}>
                  <div className="message-bubble">
                    {msg.text}
                  </div>
                </div>
              ))}
              {chatLoading && (
                <div className="message bot">
                  <div className="message-bubble typing-indicator">
                    <span></span><span></span><span></span>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            <form className="chat-input-form" onSubmit={handleChatSubmit}>
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="Type your message... (e.g., 'Analyze the Woodgrove RFP')"
                disabled={chatLoading || loading}
              />
              <button type="submit" disabled={!chatInput.trim() || chatLoading || loading}>
                Send
              </button>
            </form>
          </div>
        </div>

        {/* WORKFLOW SECTION - Appears below chat when triggered - EXACT SAME AS ORIGINAL */}
        {workflowActive && (
          <div className="workflow-section">
            <div className="workflow-divider">
              <span>🔮 Magentic Workflow Analysis</span>
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
        )}
      </div>
    </div>
  );
}

export default MagenticWorkflowWithChat;

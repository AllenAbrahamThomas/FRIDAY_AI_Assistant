import React, { useState, useEffect, useRef } from 'react';
import {
  Send, Terminal, Cpu, ShieldAlert, Globe, Compass,
  RefreshCw, MessageSquare, Radio, HelpCircle, Activity, CheckCircle, AlertTriangle
} from 'lucide-react';
import WorldMonitorPopup from './components/WorldMonitorPopup';

const renderMarkdownLite = (value) => {
  let html = String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[char]));

  html = html.replace(
    /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
  );
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  return html.replace(/\n/g, '<br />');
};

const getInitialGreeting = () => {
  const hour = new Date().getHours();
  let timeGreeting = "Greetings Boss.";
  if (hour >= 5 && hour < 12) {
    timeGreeting = "Good morning Boss. Ready for another day?";
  } else if (hour >= 12 && hour < 17) {
    timeGreeting = "Good afternoon Boss. Subsystems are running smoothly.";
  } else if (hour >= 17 && hour < 22) {
    timeGreeting = "Good evening Boss. How can I help you finish up today?";
  } else {
    timeGreeting = "Greetings Boss. You're awake late at night today. What you up to?";
  }
  return `F.R.I.D.A.Y. Protocol loaded. Holographic world monitoring systems initialized. ${timeGreeting}`;
};

function App() {
  const [messages, setMessages] = useState([
    {
      role: 'friday',
      content: getInitialGreeting(),
      trace: null
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [telemetry, setTelemetry] = useState(null);
  const [health, setHealth] = useState(null);
  const [availableModels, setAvailableModels] = useState([]);
  const [isPopupOpen, setIsPopupOpen] = useState(false);
  const [openTraces, setOpenTraces] = useState({});

  const chatEndRef = useRef(null);

  useEffect(() => {
    refreshAll();
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const toggleTrace = (index) => {
    setOpenTraces(prev => ({ ...prev, [index]: !prev[index] }));
  };

  const refreshAll = async () => {
    await Promise.all([fetchTelemetry(), fetchHealth(), fetchModels()]);
  };

  const fetchHealth = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/health');
      if (res.ok) {
        const data = await res.json();
        setHealth(data);
      }
    } catch (e) {
      console.warn("Health check failed:", e);
      setHealth({
        status: 'degraded',
        version: '2.0.0',
        environment: 'offline',
        active_model: 'llama3.2',
        ollama: { connected: false, configured_model: 'llama3.2', error: 'Backend unreachable' }
      });
    }
  };

  const fetchModels = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/models');
      if (res.ok) {
        const data = await res.json();
        setAvailableModels(data.models || []);
      }
    } catch (e) {
      console.warn("Failed to fetch model list:", e);
    }
  };

  const handleModelChange = async (e) => {
    const selected = e.target.value;
    try {
      const res = await fetch('http://localhost:8000/api/models/select', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: selected })
      });
      if (res.ok) {
        await refreshAll();
      }
    } catch (err) {
      console.error("Failed to select model:", err);
    }
  };

  const fetchTelemetry = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/monitor/telemetry');
      if (res.ok) {
        const data = await res.json();
        setTelemetry(data);
      }
    } catch (e) {
      console.warn("Telemetry fetch failed, using fallback metrics.", e);
      setTelemetry({
        global_risk_index: 72.4,
        active_conflicts: 14,
        economic_stability_score: 54.8,
        last_updated: "Static fallback sample (not live)",
        is_live: false,
        is_stale: true,
        data_source: "static_fallback_sample",
        status_message: "Local API unreachable; displaying static sample data, not a current reading.",
        recent_events: [
          { id: "e1", region: "Eastern Europe", severity: "Critical", description: "Geopolitical shifts impacting borders.", source: "Local Alert" }
        ],
        alternatives: [
          { name: "World Monitor", url: "https://www.worldmonitor.app/", desc: "Live dashboard." }
        ]
      });
    }
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userText = input;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userText, trace: null }]);
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: userText, history: messages })
      });

      if (response.ok) {
        const data = await response.json();
        setMessages(prev => [...prev, {
          role: 'friday',
          content: data.response,
          trace: data.execution_trace
        }]);
        if (data.trigger_dashboard) {
          setIsPopupOpen(true);
          window.open('https://www.worldmonitor.app/', '_blank');
        }
      } else {
        setMessages(prev => [...prev, {
          role: 'friday',
          content: 'F.R.I.D.A.Y. Warning: I experienced an issue communicating with my backend matrix interface.',
          trace: null
        }]);
      }
    } catch (err) {
      console.error(err);
      setMessages(prev => [...prev, {
        role: 'friday',
        content: 'F.R.I.D.A.Y. Diagnostic: Local API server is unreachable. Please make sure the FastAPI backend is running on port 8000.',
        trace: null
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="friday-layout">
      {/* Sidebar Panel */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <Terminal className="text-accent-cyan" size={24} color="#00f0ff" />
          <span className="friday-logo">F.R.I.D.A.Y.</span>
          <span className="status-dot pulse"></span>
        </div>

        {/* Real System Telemetry & Model Manager Widget */}
        <div className="widget">
          <div className="widget-title">
            <Cpu size={14} />
            <span>Core Subsystems</span>
          </div>
          <div className="telemetry-row" style={{ alignItems: 'center' }}>
            <span className="telemetry-label">Active Model:</span>
            {availableModels.length > 0 ? (
              <select
                value={health?.active_model || 'llama3.2'}
                onChange={handleModelChange}
                className="model-select-dropdown"
              >
                {availableModels.map(m => (
                  <option key={m.name} value={m.name}>
                    {m.name} ({m.parameter_size})
                  </option>
                ))}
              </select>
            ) : (
              <span className="telemetry-value cyan">
                {health?.active_model || health?.ollama?.configured_model || 'llama3.2'}
              </span>
            )}
          </div>
          <div className="telemetry-row">
            <span className="telemetry-label">Engine Status:</span>
            <span className={`telemetry-badge ${health?.ollama?.connected ? 'live' : 'offline'}`}>
              {health?.ollama?.connected ? 'READY' : 'OFFLINE'}
            </span>
          </div>
          <div className="telemetry-row">
            <span className="telemetry-label">API Version:</span>
            <span className="telemetry-value">v{health?.version || '2.0.0'}</span>
          </div>
          <div className="telemetry-row">
            <span className="telemetry-label">Routing Mode:</span>
            <span className="telemetry-value">Task-Adaptive</span>
          </div>
        </div>

        {/* Geopolitical Status Widget */}
        {telemetry && (
          <div className="widget">
            <div className="widget-title">
              <ShieldAlert size={14} />
              <span>Global Threat Matrix</span>
            </div>
            <div className="telemetry-row">
              <span className="telemetry-label">Data Source:</span>
              <span
                className={`telemetry-badge ${telemetry.is_live ? 'live' : 'cached'}`}
                title={telemetry.status_message}
              >
                {telemetry.is_live
                  ? telemetry.is_stale ? 'STALE LIVE API' : 'LIVE API'
                  : telemetry.data_source === 'static_fallback_sample' ? 'SAMPLE DATA' : 'OFFLINE'}
              </span>
            </div>
            <div className="telemetry-row">
              <span className="telemetry-label">Global Risk:</span>
              <span className="telemetry-value" style={{ color: '#ff3b30' }}>
                {telemetry.global_risk_index}%
              </span>
            </div>
            <div className="telemetry-row">
              <span className="telemetry-label">Active Hotzones:</span>
              <span className="telemetry-value">{telemetry.active_conflicts}</span>
            </div>
            <div style={{ marginTop: '10px' }}>
              <button
                className="fallback-btn"
                style={{ width: '100%', padding: '6px', fontSize: '0.8rem' }}
                onClick={() => setIsPopupOpen(true)}
              >
                <Globe size={12} />
                <span>Initialize Sat-Link</span>
              </button>
            </div>
          </div>
        )}

        {/* Live News Subsystem */}
        <div className="widget" style={{ flex: 1, minHeight: '180px' }}>
          <div className="widget-title">
            <Radio size={14} />
            <span>World Events Feed</span>
          </div>
          <div style={{ maxHeight: '200px', overflowY: 'auto', paddingRight: '5px' }}>
            {telemetry?.recent_events?.map(event => (
              <div className="news-item" key={event.id}>
                <div className="news-meta">[{event.region}] - {event.severity}</div>
                <div className="news-desc">{event.description}</div>
              </div>
            )) || <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Awaiting telemetry link...</span>}
          </div>
        </div>

        {/* Alternatives Links */}
        <div className="widget">
          <div className="widget-title">
            <Compass size={14} />
            <span>Alternatives Hub</span>
          </div>
          {telemetry?.alternatives?.map((alt, i) => (
            <a
              key={i}
              href={alt.url}
              target="_blank"
              rel="noopener noreferrer"
              className="alternative-link"
              title={alt.desc}
            >
              {alt.name}
            </a>
          ))}
        </div>
      </aside>

      {/* Main Console Workspace */}
      <main className="console-area">
        {/* Top Control Bar */}
        <header className="top-nav">
          <div className="top-nav-title">MISSION CONTROL INTERFACE</div>
          <button
            className="fallback-btn"
            style={{ padding: '6px 14px', fontSize: '0.8rem' }}
            onClick={refreshAll}
          >
            <RefreshCw size={12} />
            <span style={{ marginLeft: '6px' }}>Re-Sync</span>
          </button>
        </header>

        {/* Hologram Circle Container */}
        <div className="hologram-container">
          <div className="hologram-circle-outer"></div>
          <div className="hologram-circle-inner"></div>
          <div className="hologram-core"></div>
        </div>

        {/* Conversation Stream */}
        <div className="chat-container">
          {messages.map((msg, index) => (
            <div className={`message ${msg.role}`} key={index}>
              <div style={{ fontWeight: 'bold', marginBottom: '4px', fontSize: '0.75rem', textTransform: 'uppercase' }}>
                {msg.role === 'friday' ? 'Friday Assistant' : 'Tony'}
              </div>
              <div dangerouslySetInnerHTML={{ __html: renderMarkdownLite(msg.content) }} />

              {/* Collapsible Agent Execution Trace */}
              {msg.trace && (
                <div className="trace-box">
                  <div
                    className="trace-header"
                    onClick={() => toggleTrace(index)}
                    style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
                  >
                    <span className="trace-summary">
                    ⚡ AGENT TRACE: {msg.trace.agent_used?.toUpperCase() || 'DIRECT'} · {msg.trace.intent?.intent?.toUpperCase()} ({msg.trace.steps_executed?.length} steps, {msg.trace.total_duration_seconds}s total, {msg.trace.model_latency_seconds ?? 'N/A'}s model, model: {msg.trace.model_used})
                    </span>
                    <span style={{ fontSize: '0.7rem', color: 'var(--accent-cyan)' }}>
                      {openTraces[index] ? '▲ HIDE PLAN' : '▼ VIEW PLAN'}
                    </span>
                  </div>
                  {openTraces[index] && (
                    <div className="trace-details">
                      <div className="trace-plan-title">Goal: {msg.trace.plan?.task_goal}</div>
                      <div className="trace-steps">
                        {msg.trace.steps_executed?.map((s, idx) => (
                          <div className="trace-step-item" key={idx}>
                            <span className="trace-step-num">[{s.step_number}]</span>
                            <span className="trace-step-desc">{s.description}</span>
                            <span className={`trace-step-status ${s.status}`}>{s.status.toUpperCase()}</span>
                            {s.tool_name && <span className="trace-tool-tag">{s.tool_name}</span>}
                          </div>
                        ))}
                      </div>
                      {msg.trace.sources_used?.length > 0 && (
                        <div className="trace-sources">
                          Sources: {msg.trace.sources_used.join(' • ')}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
          {isLoading && (
            <div className="message friday">
              <span className="status-dot pulse" style={{ marginRight: '8px' }}></span>
              <span>Friday is processing query...</span>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Bottom Input Area */}
        <form onSubmit={handleSend} className="input-area">
          <div className="input-container">
            <span className="input-prompt">FRIDAY&gt;</span>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Input query (e.g. 'what are the biggest world problems today?')"
              className="console-input"
              disabled={isLoading}
              autoFocus
            />
            <button type="submit" className="send-button" disabled={isLoading}>
              <Send size={18} />
            </button>
          </div>
        </form>
      </main>

      {/* Iframe World Monitor Modal */}
      <WorldMonitorPopup
        isOpen={isPopupOpen}
        onClose={() => setIsPopupOpen(false)}
        telemetry={telemetry}
      />
    </div>
  );
}

export default App;

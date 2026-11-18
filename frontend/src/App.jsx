import React, { useState, useEffect, useRef } from 'react';
import {
  Send, Terminal, Cpu, ShieldAlert, Globe, Compass,
  RefreshCw, MessageSquare, Radio, HelpCircle, Activity, CheckCircle, AlertTriangle,
  ThumbsUp, ThumbsDown, Trash2
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

const getLocalProfileId = () => {
  const storageKey = 'friday-local-profile-id';
  let userId = window.localStorage.getItem(storageKey);
  if (!userId) {
    userId = window.crypto.randomUUID();
    window.localStorage.setItem(storageKey, userId);
  }
  return userId;
};

const requestMemoryApi = async (userId, path, options = {}) => {
  const response = await fetch(`http://localhost:8000/api/memory${path}`, {
    ...options,
    headers: {
      ...(options.headers || {}),
      'X-User-ID': userId
    }
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || `Memory request failed (${response.status})`);
  }
  return data;
};

const requestHistoryApi = async (userId, path, options = {}) => {
  const response = await fetch(`http://localhost:8000/api/history${path}`, {
    ...options,
    headers: {
      ...(options.headers || {}),
      'X-User-ID': userId
    }
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || `History request failed (${response.status})`);
  }
  return data;
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
  const [userId] = useState(getLocalProfileId);
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
  const [memoryEnabled, setMemoryEnabled] = useState(false);
  const [memoryStatus, setMemoryStatus] = useState('Persistent storage is off.');
  const [memorySessions, setMemorySessions] = useState([]);
  const [savedMemories, setSavedMemories] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [memoryCategory, setMemoryCategory] = useState('preference');
  const [memoryDraft, setMemoryDraft] = useState('');
  const [isMemoryLoading, setIsMemoryLoading] = useState(false);
  const [historyEnabled, setHistoryEnabled] = useState(false);
  const [executionHistory, setExecutionHistory] = useState([]);
  const [historyStatus, setHistoryStatus] = useState('Execution history is off.');
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [openHistory, setOpenHistory] = useState({});
  const [isPopupOpen, setIsPopupOpen] = useState(false);
  const [openTraces, setOpenTraces] = useState({});

  const chatEndRef = useRef(null);

  useEffect(() => {
    refreshAll();
  }, []);

  useEffect(() => {
    loadMemoryData();
  }, [userId]);

  useEffect(() => {
    loadHistoryData();
  }, [userId]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const toggleTrace = (index) => {
    setOpenTraces(prev => ({ ...prev, [index]: !prev[index] }));
  };

  const refreshAll = async () => {
    await Promise.all([fetchTelemetry(), fetchHealth(), fetchModels()]);
  };

  const loadMemoryData = async () => {
    setIsMemoryLoading(true);
    try {
      const [settings, sessions, memories] = await Promise.all([
        requestMemoryApi(userId, '/settings'),
        requestMemoryApi(userId, '/sessions'),
        requestMemoryApi(userId, '/items')
      ]);
      setMemoryEnabled(settings.memory_enabled);
      setMemorySessions(sessions.sessions);
      setSavedMemories(memories.memories);
      setMemoryStatus(
        settings.memory_enabled
          ? 'Persistent storage is enabled for this local profile.'
          : 'Persistent storage is off. Existing saved data is retained.'
      );
    } catch (error) {
      setMemoryStatus(`Memory manager unavailable: ${error.message}`);
    } finally {
      setIsMemoryLoading(false);
    }
  };

  const loadHistoryData = async () => {
    setIsHistoryLoading(true);
    try {
      const [settings, result] = await Promise.all([
        requestHistoryApi(userId, '/settings'),
        requestHistoryApi(userId, '')
      ]);
      setHistoryEnabled(settings.enabled);
      setExecutionHistory(result.history);
      setHistoryStatus(
        settings.enabled
          ? 'New execution traces are being saved locally for this profile.'
          : 'History saving is off. Existing records remain until deleted.'
      );
    } catch (error) {
      setHistoryStatus(`Execution history unavailable: ${error.message}`);
    } finally {
      setIsHistoryLoading(false);
    }
  };

  const handleHistoryToggle = async (event) => {
    const enabled = event.target.checked;
    setIsHistoryLoading(true);
    try {
      const settings = await requestHistoryApi(userId, '/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled })
      });
      setHistoryEnabled(settings.enabled);
      await loadHistoryData();
      setHistoryStatus(
        enabled
          ? 'Execution history is on. New traces will be saved locally.'
          : 'Execution history is off. Existing records remain until deleted.'
      );
    } catch (error) {
      setHistoryStatus(`Could not update execution history settings: ${error.message}`);
    } finally {
      setIsHistoryLoading(false);
    }
  };

  const handleHistoryFeedback = async (traceId, rating) => {
    setIsHistoryLoading(true);
    try {
      await requestHistoryApi(userId, `/${traceId}/feedback`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rating })
      });
      await loadHistoryData();
      setHistoryStatus('Feedback recorded.');
    } catch (error) {
      setHistoryStatus(`Could not record feedback: ${error.message}`);
    } finally {
      setIsHistoryLoading(false);
    }
  };

  const handleDeleteHistory = async (traceId) => {
    setIsHistoryLoading(true);
    try {
      await requestHistoryApi(userId, `/${traceId}`, { method: 'DELETE' });
      await loadHistoryData();
      setHistoryStatus('Execution record deleted.');
    } catch (error) {
      setHistoryStatus(`Could not delete execution record: ${error.message}`);
    } finally {
      setIsHistoryLoading(false);
    }
  };

  const handleClearHistory = async () => {
    setIsHistoryLoading(true);
    try {
      await requestHistoryApi(userId, '', { method: 'DELETE' });
      await loadHistoryData();
      setHistoryStatus('Execution history cleared.');
    } catch (error) {
      setHistoryStatus(`Could not clear execution history: ${error.message}`);
    } finally {
      setIsHistoryLoading(false);
    }
  };

  const handleMemoryToggle = async (event) => {
    const enabled = event.target.checked;
    setIsMemoryLoading(true);
    try {
      const settings = await requestMemoryApi(userId, '/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ memory_enabled: enabled })
      });
      setMemoryEnabled(settings.memory_enabled);
      if (!settings.memory_enabled) {
        setSessionId(null);
      }
      setMemoryStatus(
        enabled
          ? 'Conversation persistence is on. New messages and explicitly saved memories will be stored locally.'
          : 'Conversation persistence is off. Existing data remains until you delete it.'
      );
    } catch (error) {
      setMemoryStatus(`Could not update memory settings: ${error.message}`);
    } finally {
      setIsMemoryLoading(false);
    }
  };

  const handleSaveMemory = async (event) => {
    event.preventDefault();
    if (!memoryDraft.trim() || !memoryEnabled) return;
    setIsMemoryLoading(true);
    try {
      await requestMemoryApi(userId, '/items', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          category: memoryCategory,
          content: memoryDraft.trim()
        })
      });
      setMemoryDraft('');
      await loadMemoryData();
      setMemoryStatus('Memory saved. FRIDAY can use it in relevant requests while persistence is enabled.');
    } catch (error) {
      setMemoryStatus(`Could not save memory: ${error.message}`);
    } finally {
      setIsMemoryLoading(false);
    }
  };

  const handleDeleteMemory = async (memoryId) => {
    setIsMemoryLoading(true);
    try {
      await requestMemoryApi(userId, `/items/${memoryId}`, { method: 'DELETE' });
      await loadMemoryData();
      setMemoryStatus('Saved memory deleted.');
    } catch (error) {
      setMemoryStatus(`Could not delete memory: ${error.message}`);
    } finally {
      setIsMemoryLoading(false);
    }
  };

  const handleLoadSession = async (savedSessionId) => {
    setIsMemoryLoading(true);
    try {
      const data = await requestMemoryApi(userId, `/sessions/${savedSessionId}`);
      setSessionId(savedSessionId);
      setMessages(data.messages.map(message => ({
        role: message.role,
        content: message.content,
        trace: null
      })));
      setOpenTraces({});
      setMemoryStatus(`Loaded saved conversation: ${data.session.title}`);
    } catch (error) {
      setMemoryStatus(`Could not load conversation: ${error.message}`);
    } finally {
      setIsMemoryLoading(false);
    }
  };

  const handleDeleteSession = async (savedSessionId) => {
    setIsMemoryLoading(true);
    try {
      await requestMemoryApi(userId, `/sessions/${savedSessionId}`, { method: 'DELETE' });
      if (sessionId === savedSessionId) {
        setSessionId(null);
        setMessages([{ role: 'friday', content: getInitialGreeting(), trace: null }]);
      }
      await loadMemoryData();
      setMemoryStatus('Saved conversation and its messages deleted.');
    } catch (error) {
      setMemoryStatus(`Could not delete conversation: ${error.message}`);
    } finally {
      setIsMemoryLoading(false);
    }
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
        headers: {
          'Content-Type': 'application/json',
          'X-User-ID': userId
        },
        body: JSON.stringify({
          prompt: userText,
          history: messages,
          session_id: memoryEnabled ? sessionId : null
        })
      });

      if (response.ok) {
        const data = await response.json();
        if (data.memory_enabled && data.session_id) {
          setSessionId(data.session_id);
        }
        setMessages(prev => [...prev, {
          role: 'friday',
          content: data.response,
          trace: data.execution_trace
        }]);
        if (data.trigger_dashboard) {
          setIsPopupOpen(true);
          window.open('https://www.worldmonitor.app/', '_blank');
        }
        if (historyEnabled && data.execution_trace) {
          await loadHistoryData();
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

        <div className="widget">
          <div className="widget-title">
            <MessageSquare size={14} />
            <span>Persistent Memory</span>
          </div>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.82rem', marginBottom: '8px' }}>
            <input
              type="checkbox"
              checked={memoryEnabled}
              onChange={handleMemoryToggle}
              disabled={isMemoryLoading}
            />
            Save and retrieve memory
          </label>
          <p style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', lineHeight: 1.4, marginBottom: '10px' }}>
            Off by default. When enabled, chats and explicit memories are stored locally. Do not save passwords or secrets. Turning this off pauses storage; use Delete to erase saved data.
          </p>
          {memoryEnabled && (
            <button
              type="button"
              className="fallback-btn"
              style={{ width: '100%', padding: '6px', fontSize: '0.75rem', marginBottom: '8px' }}
              onClick={() => {
                setSessionId(null);
                setMessages([{ role: 'friday', content: getInitialGreeting(), trace: null }]);
              }}
            >
              <span>New Saved Conversation</span>
            </button>
          )}
          <div style={{ maxHeight: '125px', overflowY: 'auto', marginBottom: '10px' }}>
            <div style={{ color: 'var(--accent-cyan)', fontSize: '0.72rem', marginBottom: '4px' }}>CONVERSATIONS</div>
            {memorySessions.length ? memorySessions.map(savedSession => (
              <div key={savedSession.session_id} style={{ display: 'flex', gap: '4px', marginBottom: '4px' }}>
                <button
                  type="button"
                  className="memory-list-button"
                  onClick={() => handleLoadSession(savedSession.session_id)}
                  disabled={isMemoryLoading}
                  title={savedSession.updated_at}
                >
                  {savedSession.title} ({savedSession.message_count})
                </button>
                <button
                  type="button"
                  className="memory-delete-button"
                  onClick={() => handleDeleteSession(savedSession.session_id)}
                  disabled={isMemoryLoading}
                  aria-label={`Delete conversation ${savedSession.title}`}
                >
                  ×
                </button>
              </div>
            )) : (
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>No saved conversations.</div>
            )}
          </div>
          <form onSubmit={handleSaveMemory}>
            <div style={{ color: 'var(--accent-cyan)', fontSize: '0.72rem', marginBottom: '4px' }}>EXPLICIT MEMORIES</div>
            <select
              value={memoryCategory}
              onChange={event => setMemoryCategory(event.target.value)}
              className="model-select-dropdown"
              style={{ width: '100%', marginBottom: '6px' }}
              disabled={!memoryEnabled || isMemoryLoading}
            >
              <option value="preference">Preference</option>
              <option value="project">Project</option>
              <option value="task">Task</option>
              <option value="research">Research</option>
            </select>
            <textarea
              value={memoryDraft}
              onChange={event => setMemoryDraft(event.target.value)}
              maxLength={2000}
              placeholder="Save a preference or project detail…"
              aria-label="Memory content"
              style={{
                width: '100%',
                minHeight: '54px',
                resize: 'vertical',
                background: 'rgba(5, 8, 12, 0.8)',
                color: 'var(--text-primary)',
                border: '1px solid rgba(0, 240, 255, 0.2)',
                borderRadius: '4px',
                padding: '6px',
                font: 'inherit',
                fontSize: '0.75rem'
              }}
              disabled={!memoryEnabled || isMemoryLoading}
            />
            <button
              type="submit"
              className="fallback-btn"
              style={{ width: '100%', padding: '6px', fontSize: '0.75rem', marginTop: '6px' }}
              disabled={!memoryEnabled || isMemoryLoading || !memoryDraft.trim()}
            >
              Save Memory
            </button>
          </form>
          <div style={{ maxHeight: '115px', overflowY: 'auto', marginTop: '8px' }}>
            {savedMemories.map(memory => (
              <div key={memory.memory_id} className="memory-item-row">
                <span title={`${memory.category}: ${memory.content}`}>
                  <strong>{memory.category}:</strong> {memory.content}
                </span>
                <button
                  type="button"
                  className="memory-delete-button"
                  onClick={() => handleDeleteMemory(memory.memory_id)}
                  disabled={isMemoryLoading}
                  aria-label={`Delete ${memory.category} memory`}
                >
                  ×
                </button>
              </div>
            ))}
            {!savedMemories.length && (
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>No explicit memories saved.</div>
            )}
          </div>
          <div className="memory-status" aria-live="polite">{memoryStatus}</div>
        </div>

        <div className="widget">
          <div className="widget-title">
            <Activity size={14} />
            <span>Execution History</span>
          </div>
          <label className="history-toggle">
            <input
              type="checkbox"
              checked={historyEnabled}
              onChange={handleHistoryToggle}
              disabled={isHistoryLoading}
            />
            Save execution traces
          </label>
          <p className="history-disclosure">
            Off by default. When enabled, request text, plans, tool status, timings, and available model usage are saved locally. Common credential fields are redacted; do not include secrets. Turning this off retains existing records.
          </p>
          <div className="history-record-list">
            {executionHistory.map(record => (
              <div className="history-record" key={record.trace_id}>
                <button
                  type="button"
                  className="history-record-toggle"
                  onClick={() => setOpenHistory(previous => ({
                    ...previous,
                    [record.trace_id]: !previous[record.trace_id]
                  }))}
                  aria-expanded={Boolean(openHistory[record.trace_id])}
                >
                  <strong>{record.intent}</strong>
                  <span>{record.trace.user_prompt}</span>
                  <small>{record.total_duration_seconds}s · {record.model_used}</small>
                </button>
                {openHistory[record.trace_id] && (
                  <div className="history-record-detail">
                    <div>Agent: {record.agent_used || 'Direct'} · Model latency: {record.model_latency_seconds ?? 'N/A'}s · Tokens: {record.token_count ?? 'N/A'}</div>
                    <div className="history-step-list">
                      {record.trace.steps_executed.map(step => (
                        <div className="history-step" key={`${record.trace_id}-${step.step_number}`}>
                          <div>
                            {step.step_number}. {step.description} — {step.status} ({step.duration_seconds}s)
                            {step.error ? `: ${step.error}` : ''}
                          </div>
                          {step.tool_name && (
                            <pre>Input: {JSON.stringify(step.tool_input)}</pre>
                          )}
                          {step.observation && (
                            <div>Output summary: {step.observation}</div>
                          )}
                        </div>
                      ))}
                    </div>
                    {record.trace.warnings.length > 0 && (
                      <div>Warnings: {record.trace.warnings.join(' · ')}</div>
                    )}
                    <div className="history-record-actions">
                      <button
                        type="button"
                        onClick={() => handleHistoryFeedback(record.trace_id, 'positive')}
                        disabled={isHistoryLoading}
                        aria-pressed={record.feedback === 'positive'}
                      >
                        <ThumbsUp size={12} /> Helpful
                      </button>
                      <button
                        type="button"
                        onClick={() => handleHistoryFeedback(record.trace_id, 'negative')}
                        disabled={isHistoryLoading}
                        aria-pressed={record.feedback === 'negative'}
                      >
                        <ThumbsDown size={12} /> Not helpful
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteHistory(record.trace_id)}
                        disabled={isHistoryLoading}
                        aria-label="Delete execution record"
                      >
                        <Trash2 size={12} /> Delete
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
            {!executionHistory.length && (
              <div className="history-empty">No execution records saved.</div>
            )}
          </div>
          {!!executionHistory.length && (
            <button
              type="button"
              className="history-clear-button"
              onClick={handleClearHistory}
              disabled={isHistoryLoading}
            >
              Clear History
            </button>
          )}
          <div className="memory-status" aria-live="polite">{historyStatus}</div>
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

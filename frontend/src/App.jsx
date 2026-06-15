import React, { useState, useEffect, useRef } from 'react';
import { 
  Send, Terminal, Cpu, ShieldAlert, Globe, Compass, 
  RefreshCw, MessageSquare, Radio, HelpCircle 
} from 'lucide-react';
import WorldMonitorPopup from './components/WorldMonitorPopup';

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
      content: getInitialGreeting()
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [telemetry, setTelemetry] = useState(null);
  const [isPopupOpen, setIsPopupOpen] = useState(false);
  const [systemLoad, setSystemLoad] = useState({ cpu: 14, ram: 42 });
  
  const chatEndRef = useRef(null);

  // Fetch telemetry on mount
  useEffect(() => {
    fetchTelemetry();
    
    // Simulate updating CPU/RAM telemetry for rich aesthetics
    const interval = setInterval(() => {
      setSystemLoad({
        cpu: Math.floor(Math.random() * 20) + 5,
        ram: Math.floor(Math.random() * 5) + 38
      });
    }, 4000);
    
    return () => clearInterval(interval);
  }, []);

  // Scroll to bottom of chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const fetchTelemetry = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/monitor/telemetry');
      if (res.ok) {
        const data = await res.json();
        setTelemetry(data);
      }
    } catch (e) {
      console.warn("Telemetry fetch failed, using fallback metrics.", e);
      // Hard fallback if backend is starting
      setTelemetry({
        global_risk_index: 72.4,
        active_conflicts: 14,
        economic_stability_score: 54.8,
        last_updated: "Offline mode",
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
    setMessages(prev => [...prev, { role: 'user', content: userText }]);
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: userText, history: messages })
      });

      if (response.ok) {
        const data = await response.json();
        setMessages(prev => [...prev, { role: 'friday', content: data.response }]);
        if (data.trigger_dashboard) {
          setIsPopupOpen(true);
          window.open('https://www.worldmonitor.app/', '_blank');
        }
      } else {
        setMessages(prev => [...prev, { 
          role: 'friday', 
          content: 'F.R.I.D.A.Y. Warning: I experienced an issue communicating with my backend matrix interface.' 
        }]);
      }
    } catch (err) {
      console.error(err);
      setMessages(prev => [...prev, { 
        role: 'friday', 
        content: 'F.R.I.D.A.Y. Diagnostic: Local API server is unreachable. Please make sure the FastAPI backend is running on port 8000.' 
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

        {/* Telemetry Stats Widget */}
        <div className="widget">
          <div className="widget-title">
            <Cpu size={14} />
            <span>Friday Telemetry</span>
          </div>
          <div className="telemetry-row">
            <span className="telemetry-label">LLM Engine:</span>
            <span className="telemetry-value cyan">Ollama / Llama 3.2</span>
          </div>
          <div className="telemetry-row">
            <span className="telemetry-label">API Status:</span>
            <span className="telemetry-value">Online (8000)</span>
          </div>
          <div className="telemetry-row">
            <span className="telemetry-label">CPU Matrix:</span>
            <span className="telemetry-value">{systemLoad.cpu}%</span>
          </div>
          <div className="telemetry-row">
            <span className="telemetry-label">RAM Usage:</span>
            <span className="telemetry-value">{systemLoad.ram}%</span>
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
            {telemetry?.recent_events.map(event => (
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
          {telemetry?.alternatives.map((alt, i) => (
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
            onClick={fetchTelemetry}
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
              <div>{msg.content}</div>
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

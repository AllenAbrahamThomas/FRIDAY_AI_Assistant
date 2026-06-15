import React, { useState } from 'react';
import { X, ExternalLink, Globe, ShieldAlert, Compass } from 'lucide-react';

const WorldMonitorPopup = ({ isOpen, onClose, telemetry }) => {
  const [activeTab, setActiveTab] = useState('feed'); // 'feed' or 'telemetry'

  if (!isOpen) return null;

  return (
    <div className="monitor-overlay">
      <div className="monitor-modal">
        <div className="monitor-header">
          <div className="monitor-title">
            <Globe className="status-dot pulse" size={18} />
            <span>WORLD MONITOR - GEOPOLITICAL TELEMETRY SAT-LINK</span>
          </div>

          {/* Dynamic Tab Selectors */}
          <div className="monitor-tabs">
            <button
              className={`monitor-tab-btn ${activeTab === 'feed' ? 'active' : ''}`}
              onClick={() => setActiveTab('feed')}
            >
              Live Sat-Feed
            </button>
            <button
              className={`monitor-tab-btn ${activeTab === 'telemetry' ? 'active' : ''}`}
              onClick={() => setActiveTab('telemetry')}
            >
              Local Telemetry
            </button>
          </div>

          <button className="close-button" onClick={onClose} aria-label="Close Link">
            <X size={20} />
          </button>
        </div>

        <div className="monitor-body">
          {activeTab === 'feed' && (
            <div style={{ width: '100%', height: '100%', position: 'relative' }}>
              <iframe
                src="https://www.worldmonitor.app/"
                title="World Monitor App"
                className="monitor-iframe"
                sandbox="allow-scripts allow-same-origin allow-forms"
              />
              
              {/* Floating control helper banner */}
              <div className="monitor-floating-banner">
                <span>Satellite Feed Engaged. Having connectivity issues?</span>
                <a
                  href="https://www.worldmonitor.app/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="banner-link"
                >
                  <ExternalLink size={12} />
                  <span>Project to External Monitor</span>
                </a>
              </div>
            </div>
          )}

          {activeTab === 'telemetry' && (
            <div className="monitor-telemetry-content">
              <div className="fallback-icon">
                <Globe size={48} color="#00f0ff" />
              </div>
              <h2 className="fallback-title" style={{ fontSize: '1.25rem' }}>HOLOGRAPHIC TELEMETRY SYSTEM ACTIVE</h2>
              <p className="fallback-desc" style={{ fontSize: '0.85rem', marginBottom: '20px' }}>
                Displaying localized telemetry data and alternate intelligence feeds.
              </p>

              {telemetry && (
                <div 
                  className="widget" 
                  style={{ 
                    maxWidth: '700px', 
                    width: '100%', 
                    textAlign: 'left', 
                    backgroundColor: 'rgba(12, 16, 23, 0.95)',
                    boxShadow: 'var(--glow-cyan)' 
                  }}
                >
                  <div className="widget-title">
                    <ShieldAlert size={14} />
                    <span>LOCAL TELEMETRY SYNTHESIS</span>
                  </div>
                  <div style={{ display: 'flex', gap: '40px', marginBottom: '15px' }}>
                    <div>
                      <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>GLOBAL RISK INDEX:</span>
                      <h3 style={{ color: 'var(--accent-cyan)', fontFamily: 'var(--font-tech)' }}>
                        {telemetry.global_risk_index}%
                      </h3>
                    </div>
                    <div>
                      <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>ACTIVE GEOPOLITICAL ISSUES:</span>
                      <h3 style={{ color: 'var(--accent-teal)', fontFamily: 'var(--font-tech)' }}>
                        {telemetry.active_conflicts} CONFLICTS
                      </h3>
                    </div>
                    <div>
                      <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>ECONOMIC STABILITY:</span>
                      <h3 style={{ color: 'var(--accent-cyan)', fontFamily: 'var(--font-tech)' }}>
                        {telemetry.economic_stability_score}%
                      </h3>
                    </div>
                  </div>

                  <div className="widget-title" style={{ marginTop: '15px', fontSize: '0.8rem' }}>
                    <Compass size={12} />
                    <span>ALTERNATIVE INTELLIGENCE DATABASES</span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                    {telemetry.alternatives.map((alt, idx) => (
                      <a
                        key={idx}
                        href={alt.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="alternative-link"
                        style={{ fontSize: '0.8rem' }}
                      >
                        <ExternalLink size={10} style={{ marginRight: '4px' }} />
                        {alt.name} - <span style={{ color: 'var(--text-secondary)' }}>{alt.desc}</span>
                      </a>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default WorldMonitorPopup;

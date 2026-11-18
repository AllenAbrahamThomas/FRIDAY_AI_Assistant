import {
  Activity, BookOpen, Cpu, Database, Globe, MessageSquare,
  ThumbsDown, ThumbsUp, Trash2
} from 'lucide-react';

const StatusBadge = ({ live, label, status }) => {
  const badgeStatus = status || (
    live ? 'live' : ['OFFLINE', 'FAILED', 'NOT INSTALLED'].includes(label.toUpperCase()) ? 'offline' : 'cached'
  );
  return <span className={`telemetry-badge ${badgeStatus}`}>{label}</span>;
};

export function MemorySection({
  memoryEnabled,
  memoryStatus,
  memorySessions,
  savedMemories,
  memoryCategory,
  memoryDraft,
  isMemoryLoading,
  onMemoryToggle,
  onLoadSession,
  onDeleteSession,
  onCategoryChange,
  onDraftChange,
  onSaveMemory,
  onDeleteMemory,
  onNewSession
}) {
  return (
    <section className="workspace-page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">LOCAL CONTEXT</div>
          <h1>Memory</h1>
          <p>Choose what FRIDAY retains, inspect saved context, and remove it when you want.</p>
        </div>
        <Database size={26} />
      </div>
      <div className="workspace-grid">
        <article className="workspace-card">
          <div className="card-heading">
            <MessageSquare size={16} />
            <h2>Conversation storage</h2>
          </div>
          <label className="setting-toggle">
            <input
              type="checkbox"
              checked={memoryEnabled}
              onChange={onMemoryToggle}
              disabled={isMemoryLoading}
            />
            Save and retrieve conversation memory
          </label>
          <p className="panel-note">
            Off by default. When enabled, chats are stored locally. Turning this off pauses storage and retrieval but keeps existing records until deleted. Do not save passwords or secrets.
          </p>
          {memoryEnabled && (
            <button type="button" className="secondary-button" onClick={onNewSession}>
              Start a new saved conversation
            </button>
          )}
          <div className="record-list">
            {memorySessions.length ? memorySessions.map(savedSession => (
              <div className="saved-record-row" key={savedSession.session_id}>
                <button
                  type="button"
                  className="record-open-button"
                  onClick={() => onLoadSession(savedSession.session_id)}
                  disabled={isMemoryLoading}
                  title={savedSession.updated_at}
                >
                  <span>{savedSession.title}</span>
                  <small>{savedSession.message_count} messages</small>
                </button>
                <button
                  type="button"
                  className="icon-delete-button"
                  onClick={() => onDeleteSession(savedSession.session_id)}
                  disabled={isMemoryLoading}
                  aria-label={`Delete conversation ${savedSession.title}`}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            )) : <p className="empty-state">No saved conversations.</p>}
          </div>
        </article>

        <article className="workspace-card">
          <div className="card-heading">
            <Database size={16} />
            <h2>Explicit memories</h2>
          </div>
          <form onSubmit={onSaveMemory} className="memory-form">
            <label>
              Category
              <select
                value={memoryCategory}
                onChange={event => onCategoryChange(event.target.value)}
                disabled={!memoryEnabled || isMemoryLoading}
              >
                <option value="preference">Preference</option>
                <option value="project">Project</option>
                <option value="task">Task</option>
                <option value="research">Research</option>
              </select>
            </label>
            <label>
              Memory detail
              <textarea
                value={memoryDraft}
                onChange={event => onDraftChange(event.target.value)}
                maxLength={2000}
                placeholder="Save a preference or project detail…"
                disabled={!memoryEnabled || isMemoryLoading}
              />
            </label>
            <button
              type="submit"
              className="primary-button"
              disabled={!memoryEnabled || isMemoryLoading || !memoryDraft.trim()}
            >
              Save memory
            </button>
          </form>
          <div className="record-list memory-record-list">
            {savedMemories.map(memory => (
              <div className="saved-record-row" key={memory.memory_id}>
                <div className="memory-copy">
                  <strong>{memory.category}</strong>
                  <span>{memory.content}</span>
                </div>
                <button
                  type="button"
                  className="icon-delete-button"
                  onClick={() => onDeleteMemory(memory.memory_id)}
                  disabled={isMemoryLoading}
                  aria-label={`Delete ${memory.category} memory`}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
            {!savedMemories.length && <p className="empty-state">No explicit memories saved.</p>}
          </div>
        </article>
      </div>
      <p className="panel-status" aria-live="polite">{memoryStatus}</p>
    </section>
  );
}

export function ExecutionHistorySection({
  historyEnabled,
  executionHistory,
  historyStatus,
  isHistoryLoading,
  openHistory,
  onHistoryToggle,
  onToggleRecord,
  onFeedback,
  onDelete,
  onClear
}) {
  return (
    <section className="workspace-page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">OBSERVABILITY</div>
          <h1>Execution history</h1>
          <p>Review routing decisions, tool activity, latency, model usage, and warnings.</p>
        </div>
        <Activity size={26} />
      </div>
      <article className="workspace-card">
        <label className="setting-toggle">
          <input
            type="checkbox"
            checked={historyEnabled}
            onChange={onHistoryToggle}
            disabled={isHistoryLoading}
          />
          Save execution traces
        </label>
        <p className="panel-note">
          Off by default. Saved traces include request text and plan details. Common credential fields are redacted, but this is best-effort; do not include secrets. Turning history off retains prior records.
        </p>
        <div className="history-table-heading">
          <span>REQUEST / INTENT</span>
          <span>AGENT</span>
          <span>TIME</span>
          <span>MODEL</span>
          <span>FEEDBACK</span>
        </div>
        <div className="history-page-list">
          {executionHistory.map(record => (
            <article className="history-page-record" key={record.trace_id}>
              <button
                type="button"
                className="history-page-summary"
                onClick={() => onToggleRecord(record.trace_id)}
                aria-expanded={Boolean(openHistory[record.trace_id])}
              >
                <span>
                  <strong>{record.intent}</strong>
                  <small>{record.trace.user_prompt}</small>
                </span>
                <span>{record.agent_used || 'Direct'}</span>
                <span>{record.total_duration_seconds}s</span>
                <span>{record.model_used}</span>
                <span>{record.feedback || '—'}</span>
              </button>
              {openHistory[record.trace_id] && (
                <div className="history-page-detail">
                  <div className="metric-strip">
                    <span>Model latency: {record.model_latency_seconds ?? 'N/A'}s</span>
                    <span>Tokens: {record.token_count ?? 'N/A'}</span>
                    <span>Sources: {record.trace.sources_used.length}</span>
                  </div>
                  <div className="history-page-steps">
                    {record.trace.steps_executed.map(step => (
                      <div className="history-page-step" key={`${record.trace_id}-${step.step_number}`}>
                        <div>
                          <strong>{step.step_number}. {step.description}</strong>
                          <StatusBadge
                            live={step.status === 'completed'}
                            label={step.status}
                            status={step.status === 'failed' ? 'offline' : undefined}
                          />
                          <span>{step.duration_seconds}s</span>
                        </div>
                        {step.tool_name && <pre>Input: {JSON.stringify(step.tool_input)}</pre>}
                        {step.observation && <p>Output summary: {step.observation}</p>}
                        {step.error && <p className="error-text">{step.error}</p>}
                      </div>
                    ))}
                  </div>
                  {record.trace.warnings.length > 0 && (
                    <p className="warning-text">Warnings: {record.trace.warnings.join(' · ')}</p>
                  )}
                  <div className="record-actions">
                    <button
                      type="button"
                      onClick={() => onFeedback(record.trace_id, 'positive')}
                      disabled={isHistoryLoading}
                      aria-pressed={record.feedback === 'positive'}
                    >
                      <ThumbsUp size={14} /> Helpful
                    </button>
                    <button
                      type="button"
                      onClick={() => onFeedback(record.trace_id, 'negative')}
                      disabled={isHistoryLoading}
                      aria-pressed={record.feedback === 'negative'}
                    >
                      <ThumbsDown size={14} /> Not helpful
                    </button>
                    <button type="button" className="danger-action" onClick={() => onDelete(record.trace_id)} disabled={isHistoryLoading}>
                      <Trash2 size={14} /> Delete
                    </button>
                  </div>
                </div>
              )}
            </article>
          ))}
          {!executionHistory.length && <p className="empty-state">No execution records saved.</p>}
        </div>
        {!!executionHistory.length && (
          <button type="button" className="secondary-button" onClick={onClear} disabled={isHistoryLoading}>
            Clear history
          </button>
        )}
      </article>
      <p className="panel-status" aria-live="polite">{historyStatus}</p>
    </section>
  );
}

export function IntelligenceSection({ telemetry, onOpenMonitor }) {
  const statusLabel = telemetry?.is_live
    ? telemetry.is_stale ? 'STALE LIVE API' : 'LIVE API'
    : telemetry?.data_source === 'static_fallback_sample' ? 'SAMPLE DATA' : 'OFFLINE';

  return (
    <section className="workspace-page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">WORLD MONITOR</div>
          <h1>Intelligence dashboard</h1>
          <p>Regional indicators and events are labeled with their source freshness.</p>
        </div>
        <button type="button" className="primary-button" onClick={onOpenMonitor}>
          <Globe size={16} /> Open World Monitor
        </button>
      </div>
      {telemetry ? (
        <>
          <div className="intel-metrics-grid">
            <article className="metric-card">
              <span>GLOBAL RISK INDEX</span>
              <strong>{telemetry.global_risk_index}%</strong>
            </article>
            <article className="metric-card">
              <span>ACTIVE HOTZONES</span>
              <strong>{telemetry.active_conflicts}</strong>
            </article>
            <article className="metric-card">
              <span>ECONOMIC STABILITY</span>
              <strong>{telemetry.economic_stability_score}%</strong>
            </article>
            <article className="metric-card">
              <span>DATA STATUS</span>
              <StatusBadge live={telemetry.is_live && !telemetry.is_stale} label={statusLabel} />
            </article>
          </div>
          <div className="workspace-grid">
            <article className="workspace-card">
              <div className="card-heading"><Globe size={16} /><h2>Recent events</h2></div>
              <p className="panel-note">{telemetry.status_message}</p>
              <div className="event-list">
                {telemetry.recent_events.map(event => (
                  <div className="event-row" key={event.id}>
                    <div><strong>{event.region}</strong><span>{event.severity}</span></div>
                    <p>{event.description}</p>
                    <small>{event.source}</small>
                  </div>
                ))}
                {!telemetry.recent_events.length && <p className="empty-state">No recent events reported.</p>}
              </div>
            </article>
            <article className="workspace-card">
              <div className="card-heading"><BookOpen size={16} /><h2>Data sources</h2></div>
              <dl className="source-freshness">
                <div><dt>Source</dt><dd>{telemetry.data_source.replaceAll('_', ' ')}</dd></div>
                <div><dt>Fetched</dt><dd>{telemetry.fetched_at || 'Not provided'}</dd></div>
                <div><dt>Data as of</dt><dd>{telemetry.data_as_of || telemetry.last_updated}</dd></div>
              </dl>
              <div className="source-links">
                {telemetry.alternatives.map(source => (
                  <a key={source.url} href={source.url} target="_blank" rel="noopener noreferrer">
                    <span>{source.name}</span><small>{source.desc}</small>
                  </a>
                ))}
              </div>
            </article>
          </div>
        </>
      ) : <p className="empty-state">Waiting for telemetry data…</p>}
    </section>
  );
}

export function ResearchSection({ messages }) {
  const reports = messages.filter(message =>
    message.role === 'friday' && (
      ['research', 'world_intelligence'].includes(message.trace?.intent?.intent)
      || message.sources?.length
    )
  );

  return (
    <section className="workspace-page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">EVIDENCE LIBRARY</div>
          <h1>Research reports</h1>
          <p>Recent research and intelligence replies with their available source links.</p>
        </div>
        <BookOpen size={26} />
      </div>
      <div className="report-list">
        {reports.map((report, index) => (
          <article className="workspace-card report-card" key={`${report.trace?.trace_id || index}-${index}`}>
            <div className="report-meta">
              <span>{report.trace?.intent?.intent || 'Research'}</span>
              <span>{report.trace?.created_at || 'Current session'}</span>
            </div>
            <p className="report-body">{report.content}</p>
            {report.sources?.length > 0 ? (
              <div className="report-sources">
                <h2>Sources</h2>
                {report.sources.map((source, sourceIndex) => {
                  const url = source.url || source.link || source.href;
                  const label = source.title || source.name || source.source || `Source ${sourceIndex + 1}`;
                  return url ? (
                    <a href={url} key={`${url}-${sourceIndex}`} target="_blank" rel="noopener noreferrer">
                      {label}
                    </a>
                  ) : <span key={`${label}-${sourceIndex}`}>{label}</span>;
                })}
              </div>
            ) : report.trace?.sources_used?.length > 0 ? (
              <div className="report-sources">
                <h2>Sources</h2>
                <p>{report.trace.sources_used.join(' · ')}</p>
              </div>
            ) : <p className="panel-note">No structured source links were returned for this report.</p>}
          </article>
        ))}
        {!reports.length && (
          <div className="workspace-card empty-state">
            Research and intelligence reports from this chat will appear here.
          </div>
        )}
      </div>
    </section>
  );
}

export function SystemSection({ health, models, onModelChange, telemetry, onRefresh }) {
  const ollamaReady = Boolean(health?.ollama?.connected);
  const modelAvailable = health?.ollama?.model_available;

  return (
    <section className="workspace-page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">RUNTIME & MODELS</div>
          <h1>System status</h1>
          <p>Live service state from the backend; unavailable measurements are not simulated.</p>
        </div>
        <button type="button" className="secondary-button" onClick={onRefresh}>Refresh status</button>
      </div>
      <div className="system-status-grid">
        <article className="workspace-card">
          <div className="card-heading"><Cpu size={16} /><h2>Ollama provider</h2></div>
          <div className="status-line">
            <span>Connection</span><StatusBadge live={ollamaReady} label={ollamaReady ? 'CONNECTED' : 'OFFLINE'} />
          </div>
          <div className="status-line"><span>Active model</span><strong>{health?.active_model || 'Unknown'}</strong></div>
          <div className="status-line">
            <span>Model availability</span>
            <strong>{modelAvailable === undefined ? 'Unknown' : modelAvailable ? 'Installed' : 'Not installed'}</strong>
          </div>
          <div className="status-line"><span>Provider URL</span><strong>{health?.ollama?.base_url || 'Unavailable'}</strong></div>
          {health?.ollama?.error && <p className="error-text">{health.ollama.error}</p>}
          <label className="model-setting">
            Select model
            <select value={health?.active_model || ''} onChange={onModelChange} disabled={!models.length}>
              {models.length ? models.map(model => (
                <option key={model.name} value={model.name}>{model.name} · {model.parameter_size}</option>
              )) : <option value="">No models reported</option>}
            </select>
          </label>
        </article>
        <article className="workspace-card">
          <div className="card-heading"><Activity size={16} /><h2>Application services</h2></div>
          <div className="status-line">
            <span>Backend API</span>
            <StatusBadge live={Boolean(health)} label={health ? 'REACHABLE' : 'CHECKING'} />
          </div>
          <div className="status-line"><span>API version</span><strong>{health?.version || '—'}</strong></div>
          <div className="status-line"><span>Environment</span><strong>{health?.environment || '—'}</strong></div>
          <div className="status-line">
            <span>World Monitor feed</span>
            <StatusBadge live={Boolean(telemetry?.is_live && !telemetry?.is_stale)} label={
              telemetry?.is_live
                ? telemetry.is_stale ? 'STALE' : 'LIVE'
                : telemetry?.data_source === 'static_fallback_sample' ? 'SAMPLE' : 'OFFLINE'
            } />
          </div>
        </article>
        <article className="workspace-card hardware-card">
          <div className="card-heading"><Cpu size={16} /><h2>Hardware telemetry</h2></div>
          <StatusBadge live={false} label="NOT PROVIDED" status="cached" />
          <p className="panel-note">
            The backend does not currently expose CPU, memory, or GPU measurements. No random or simulated hardware readings are shown.
          </p>
        </article>
      </div>
    </section>
  );
}

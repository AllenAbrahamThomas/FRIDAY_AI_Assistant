import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Send, Terminal, MessageSquare, Globe, BookOpen, Activity, Database,
  Settings, RefreshCw, Cpu, Mic, MicOff, Volume2, VolumeX, CalendarClock
} from 'lucide-react';
import WorldMonitorPopup from './components/WorldMonitorPopup';
import {
  ExecutionHistorySection,
  IntelligenceSection,
  MemorySection,
  ResearchSection,
  ScheduledTasksSection,
  SystemSection
} from './components/WorkspaceSections';

const WORKSPACE_VIEWS = [
  { id: 'assistant', label: 'Assistant', description: 'Chat and tasks', icon: MessageSquare },
  { id: 'intelligence', label: 'Intelligence', description: 'World Monitor', icon: Globe },
  { id: 'research', label: 'Research', description: 'Reports and sources', icon: BookOpen },
  { id: 'activity', label: 'Activity', description: 'Plans and execution', icon: Activity },
  { id: 'memory', label: 'Memory', description: 'Saved context', icon: Database },
  { id: 'scheduled', label: 'Schedules', description: 'Recurring tasks', icon: CalendarClock },
  { id: 'system', label: 'System', description: 'Models and services', icon: Settings }
];

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
  const response = await fetch(`/api/memory${path}`, {
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
  const response = await fetch(`/api/history${path}`, {
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

const requestScheduledApi = async (userId, path, options = {}) => {
  const response = await fetch(`/api/scheduled-tasks${path}`, {
    ...options,
    headers: {
      ...(options.headers || {}),
      'X-User-ID': userId
    }
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || `Scheduled task request failed (${response.status})`);
  }
  return data;
};

const fetchTelemetryData = async () => {
  try {
    const response = await fetch('/api/monitor/telemetry');
    return response.ok ? await response.json() : null;
  } catch (error) {
    console.warn('Telemetry fetch failed, using fallback metrics.', error);
    return {
      global_risk_index: 72.4,
      active_conflicts: 14,
      economic_stability_score: 54.8,
      last_updated: 'Static fallback sample (not live)',
      is_live: false,
      is_stale: true,
      data_source: 'static_fallback_sample',
      status_message: 'Local API unreachable; displaying static sample data, not a current reading.',
      recent_events: [
        { id: 'e1', region: 'Eastern Europe', severity: 'Critical', description: 'Geopolitical shifts impacting borders.', source: 'Local Alert' }
      ],
      alternatives: [
        { name: 'World Monitor', url: 'https://www.worldmonitor.app/', desc: 'Live dashboard.' }
      ]
    };
  }
};

const getInitialGreeting = () => {
  const hour = new Date().getHours();
  const timeGreeting = hour >= 5 && hour < 12
    ? 'Good morning Boss. Ready for another day?'
    : hour >= 12 && hour < 17
      ? 'Good afternoon Boss. Subsystems are running smoothly.'
      : hour >= 17 && hour < 22
        ? 'Good evening Boss. How can I help you finish up today?'
        : "Greetings Boss. You're awake late at night today. What you up to?";
  return `F.R.I.D.A.Y. Protocol loaded. Holographic world monitoring systems initialized. ${timeGreeting}`;
};

function App() {
  const [userId] = useState(getLocalProfileId);
  const [activeView, setActiveView] = useState('assistant');
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
  const [scheduledTasks, setScheduledTasks] = useState([]);
  const [scheduledRuns, setScheduledRuns] = useState([]);
  const [scheduledStatus, setScheduledStatus] = useState('Loading scheduled tasks.');
  const [scheduledNotice, setScheduledNotice] = useState('');
  const [isScheduleLoading, setIsScheduleLoading] = useState(false);
  const [scheduleTitleDraft, setScheduleTitleDraft] = useState('');
  const [schedulePromptDraft, setSchedulePromptDraft] = useState('');
  const [scheduleInterval, setScheduleInterval] = useState('1440');
  const [isPopupOpen, setIsPopupOpen] = useState(false);
  const [openTraces, setOpenTraces] = useState({});
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState(
    'Voice controls are off; text chat remains available.'
  );

  const chatEndRef = useRef(null);
  const recognitionRef = useRef(null);
  const utteranceRef = useRef(null);
  const voiceEnabledRef = useRef(false);
  const seenScheduledRunStatuses = useRef(new Map());
  const loadedScheduledRuns = useRef(false);
  const speechRecognitionAvailable = Boolean(
    window.SpeechRecognition || window.webkitSpeechRecognition
  );
  const speechSynthesisAvailable = Boolean(window.speechSynthesis);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading, activeView]);

  useEffect(() => () => {
    const recognition = recognitionRef.current;
    recognitionRef.current = null;
    recognition?.abort();
    window.speechSynthesis?.cancel();
  }, []);

  const toggleTrace = (index) => {
    setOpenTraces(prev => ({ ...prev, [index]: !prev[index] }));
  };

  const cancelSpeech = () => {
    window.speechSynthesis?.cancel();
    utteranceRef.current = null;
    setIsSpeaking(false);
    setVoiceStatus(voiceEnabledRef.current ? 'Voice playback stopped.' : 'Voice controls are off.');
  };

  const speakResponse = (text) => {
    if (!text?.trim() || !voiceEnabledRef.current || !speechSynthesisAvailable) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utteranceRef.current = utterance;
    utterance.onstart = () => {
      if (utteranceRef.current === utterance) {
        setIsSpeaking(true);
        setVoiceStatus('Speaking response.');
      }
    };
    utterance.onend = () => {
      if (utteranceRef.current === utterance) {
        utteranceRef.current = null;
        setIsSpeaking(false);
        setVoiceStatus('Voice playback complete.');
      }
    };
    utterance.onerror = (event) => {
      if (utteranceRef.current === utterance) {
        utteranceRef.current = null;
        setIsSpeaking(false);
        setVoiceStatus(`Voice playback failed: ${event.error || 'unknown error'}.`);
      }
    };
    window.speechSynthesis.speak(utterance);
  };

  const handleVoiceToggle = (event) => {
    const enabled = event.target.checked;
    voiceEnabledRef.current = enabled;
    setVoiceEnabled(enabled);
    if (!enabled) {
      recognitionRef.current?.abort();
      recognitionRef.current = null;
      window.speechSynthesis?.cancel();
      utteranceRef.current = null;
      setIsListening(false);
      setIsSpeaking(false);
      setVoiceStatus('Voice controls are off; text chat remains available.');
      return;
    }

    const inputStatus = speechRecognitionAvailable
      ? 'Microphone input is ready.'
      : 'Speech input is unavailable in this browser.';
    const outputStatus = speechSynthesisAvailable
      ? ' Voice responses are enabled.'
      : ' Speech playback is unavailable in this browser.';
    setVoiceStatus(`${inputStatus}${outputStatus}`);
  };

  const stopListening = () => {
    recognitionRef.current?.abort();
    recognitionRef.current = null;
    setIsListening(false);
    setVoiceStatus('Listening cancelled.');
  };

  const startListening = () => {
    if (!window.isSecureContext) {
      setVoiceStatus('Microphone access requires a secure context such as HTTPS or localhost.');
      return;
    }

    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) {
      setVoiceStatus('Speech input is unavailable in this browser.');
      return;
    }

    const recognition = new Recognition();
    let transcriptReceived = false;
    recognition.lang = navigator.language || 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onstart = () => {
      if (recognitionRef.current !== recognition) return;
      setIsListening(true);
      setVoiceStatus('Listening. Speak your request.');
    };
    recognition.onresult = (event) => {
      if (recognitionRef.current !== recognition) return;
      const transcript = Array.from(event.results)
        .map(result => result[0]?.transcript || '')
        .join(' ')
        .trim();
      if (!transcript) return;
      transcriptReceived = true;
      setVoiceStatus('Transcribing speech.');
      setInput(current => `${current.trim()}${current.trim() ? ' ' : ''}${transcript}`);
    };
    recognition.onerror = (event) => {
      if (recognitionRef.current !== recognition) return;
      setIsListening(false);
      recognitionRef.current = null;
      const messages = {
        'not-allowed': 'Microphone permission denied. Allow microphone access in browser settings.',
        'service-not-allowed': 'The browser speech service is not permitted.',
        'audio-capture': 'No microphone was found.',
        'no-speech': 'No speech detected. Try again.',
        network: 'Speech recognition network unavailable. Check your connection.'
      };
      setVoiceStatus(messages[event.error] || `Speech input failed: ${event.error || 'unknown error'}.`);
    };
    recognition.onend = () => {
      setIsListening(false);
      if (recognitionRef.current === recognition) {
        recognitionRef.current = null;
        setVoiceStatus(
          transcriptReceived
            ? 'Transcription ready. Review the text before sending.'
            : 'Listening stopped.'
        );
      }
    };

    try {
      recognitionRef.current = recognition;
      setIsListening(true);
      setVoiceStatus('Requesting microphone permission.');
      recognition.start();
    } catch (error) {
      recognitionRef.current = null;
      setIsListening(false);
      setVoiceStatus(`Could not start speech input: ${error.message}`);
    }
  };

  const loadMemoryData = useCallback(async () => {
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
  }, [userId]);

  const loadHistoryData = useCallback(async () => {
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
  }, [userId]);

  const loadScheduledData = useCallback(async (notifyOnCompletion = false) => {
    setIsScheduleLoading(true);
    try {
      const [taskData, runData] = await Promise.all([
        requestScheduledApi(userId, ''),
        requestScheduledApi(userId, '/runs?limit=50')
      ]);
      const runs = runData.runs || [];
      const newCompletions = runs.filter(run =>
        run.status === 'completed'
        && seenScheduledRunStatuses.current.get(run.run_id) !== 'completed'
      );
      if (notifyOnCompletion && loadedScheduledRuns.current && newCompletions.length) {
        const title = newCompletions[0].task_title;
        setScheduledNotice(
          newCompletions.length === 1
            ? `${title} completed. Open Schedules to review the result.`
            : `${newCompletions.length} scheduled tasks completed. Open Schedules to review the results.`
        );
      }
      runs.forEach(run => seenScheduledRunStatuses.current.set(run.run_id, run.status));
      loadedScheduledRuns.current = true;
      setScheduledTasks(taskData.tasks || []);
      setScheduledRuns(runs);
      setScheduledStatus('Scheduled tasks and recent runs are up to date.');
    } catch (error) {
      setScheduledStatus(`Scheduled task service unavailable: ${error.message}`);
    } finally {
      setIsScheduleLoading(false);
    }
  }, [userId]);

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

  const handleCreateScheduledTask = async (event) => {
    event.preventDefault();
    if (!scheduleTitleDraft.trim() || !schedulePromptDraft.trim()) return;
    setIsScheduleLoading(true);
    try {
      await requestScheduledApi(userId, '', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: scheduleTitleDraft.trim(),
          prompt: schedulePromptDraft.trim(),
          interval_minutes: Number(scheduleInterval)
        })
      });
      setScheduleTitleDraft('');
      setSchedulePromptDraft('');
      await loadScheduledData();
      setScheduledStatus('Scheduled task created. Its first run is due after the selected interval.');
    } catch (error) {
      setScheduledStatus(`Could not create scheduled task: ${error.message}`);
    } finally {
      setIsScheduleLoading(false);
    }
  };

  const handleScheduledTaskStatus = async (taskId, status) => {
    const action = status === 'paused' ? 'pause' : 'resume';
    setIsScheduleLoading(true);
    try {
      await requestScheduledApi(userId, `/${taskId}/${action}`, { method: 'POST' });
      await loadScheduledData();
      setScheduledStatus(status === 'paused' ? 'Scheduled task paused.' : 'Scheduled task resumed.');
    } catch (error) {
      setScheduledStatus(`Could not update scheduled task: ${error.message}`);
    } finally {
      setIsScheduleLoading(false);
    }
  };

  const handleDeleteScheduledTask = async (taskId) => {
    setIsScheduleLoading(true);
    try {
      await requestScheduledApi(userId, `/${taskId}`, { method: 'DELETE' });
      await loadScheduledData();
      setScheduledStatus('Scheduled task and its run history were deleted.');
    } catch (error) {
      setScheduledStatus(`Could not delete scheduled task: ${error.message}`);
    } finally {
      setIsScheduleLoading(false);
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

  const fetchHealth = useCallback(async () => {
    try {
      const res = await fetch('/api/health');
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
  }, []);

  const fetchModels = useCallback(async () => {
    try {
      const res = await fetch('/api/models');
      if (res.ok) {
        const data = await res.json();
        setAvailableModels(data.models || []);
      }
    } catch (e) {
      console.warn("Failed to fetch model list:", e);
    }
  }, []);

  const handleModelChange = async (e) => {
    const selected = e.target.value;
    try {
      const res = await fetch('/api/models/select', {
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
    const data = await fetchTelemetryData();
    if (data) setTelemetry(data);
  };

  const refreshAll = async () => {
    await Promise.all([fetchTelemetry(), fetchHealth(), fetchModels()]);
  };

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      Promise.all([
        fetchTelemetryData().then(data => {
          if (data) setTelemetry(data);
        }),
        fetchHealth(),
        fetchModels()
      ]);
    }, 0);
    return () => window.clearTimeout(timeout);
  }, [fetchHealth, fetchModels]);

  useEffect(() => {
    const timeout = window.setTimeout(loadMemoryData, 0);
    return () => window.clearTimeout(timeout);
  }, [loadMemoryData]);

  useEffect(() => {
    const timeout = window.setTimeout(loadHistoryData, 0);
    return () => window.clearTimeout(timeout);
  }, [loadHistoryData]);

  useEffect(() => {
    const initialLoad = window.setTimeout(() => loadScheduledData(), 0);
    const poll = window.setInterval(() => loadScheduledData(true), 30000);
    return () => {
      window.clearTimeout(initialLoad);
      window.clearInterval(poll);
    };
  }, [loadScheduledData]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    recognitionRef.current?.abort();
    recognitionRef.current = null;
    setIsListening(false);
    if (isSpeaking) cancelSpeech();

    const userText = input;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userText, trace: null }]);
    setIsLoading(true);

    try {
      const response = await fetch('/api/chat', {
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
          trace: data.execution_trace,
          sources: data.sources || []
        }]);
        if (voiceEnabledRef.current) {
          speakResponse(data.response);
        }
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
      <aside className="sidebar">
        <div className="sidebar-header">
          <Terminal className="text-accent-cyan" size={24} color="#00f0ff" />
          <span className="friday-logo">F.R.I.D.A.Y.</span>
        </div>
        <div className="sidebar-kicker">LOCAL AI WORKSPACE</div>
        <div className="sidebar-status">
          <div className="sidebar-status-row">
            <span>Backend API</span>
            <strong className={health ? 'status-online' : 'status-pending'}>
              {health ? 'REACHABLE' : 'CHECKING'}
            </strong>
          </div>
          <div className="sidebar-status-row">
            <span>Ollama</span>
            <strong className={health?.ollama?.connected ? 'status-online' : 'status-offline'}>
              {health?.ollama?.connected ? 'READY' : 'OFFLINE'}
            </strong>
          </div>
          <div className="sidebar-status-row">
            <span>World feed</span>
            <strong className={telemetry?.is_live && !telemetry?.is_stale ? 'status-online' : 'status-pending'}>
              {telemetry?.is_live
                ? telemetry.is_stale ? 'STALE' : 'LIVE'
                : telemetry?.data_source === 'static_fallback_sample' ? 'SAMPLE' : 'OFFLINE'}
            </strong>
          </div>
        </div>
        <nav className="workspace-nav" aria-label="FRIDAY workspace">
          {WORKSPACE_VIEWS.map(({ id, label, description, icon: Icon }) => (
            <button
              type="button"
              key={id}
              className={`workspace-nav-button ${activeView === id ? 'active' : ''}`}
              onClick={() => setActiveView(id)}
              aria-current={activeView === id ? 'page' : undefined}
              title={description}
            >
              <Icon size={17} />
              <span>{label}</span>
              <small>{description}</small>
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span>Local profile ? {userId.slice(0, 8)}</span>
          <span>Storage controls are opt-in</span>
        </div>
      </aside>

      <main className="console-area">
        <header className="top-nav">
          <div>
            <div className="eyebrow">F.R.I.D.A.Y. / 2.0</div>
            <h1 className="top-nav-title">
              {WORKSPACE_VIEWS.find(view => view.id === activeView)?.label || 'Assistant'}
            </h1>
          </div>
          <div className="top-nav-actions">
            <span className={`connection-chip ${health?.ollama?.connected ? 'connected' : 'disconnected'}`}>
              <span className="connection-dot" />
              {health?.ollama?.connected ? 'LOCAL MODEL READY' : 'MODEL OFFLINE'}
            </span>
            <button type="button" className="secondary-button" onClick={refreshAll}>
              <RefreshCw size={14} /> Re-sync
            </button>
          </div>
        </header>

        {scheduledNotice && (
          <div className="scheduled-notice" role="status" aria-live="polite">
            <CalendarClock size={16} />
            <span>{scheduledNotice}</span>
            <button type="button" onClick={() => setScheduledNotice('')}>Dismiss</button>
          </div>
        )}

        <div className="workspace-main" key={activeView}>
          {activeView === 'assistant' && (
            <section className="assistant-workspace">
              <div className="assistant-intro">
                <div className="assistant-orb" aria-hidden="true">
                  <div className="hologram-circle-outer" />
                  <div className="hologram-circle-inner" />
                  <div className="hologram-core" />
                </div>
                <div className="assistant-intro-copy">
                  <div className="eyebrow">CHAT / TOOLS / AGENTS</div>
                  <h2>What should we work on?</h2>
                  <p>FRIDAY routes requests, uses tools when needed, and shows its execution plan.</p>
                </div>
                <div className="assistant-model-card">
                  <Cpu size={15} />
                  <span>{health?.active_model || health?.ollama?.configured_model || 'Model not reported'}</span>
                </div>
              </div>

              <div className="chat-container" aria-live="polite" aria-relevant="additions">
                {messages.map((msg, index) => (
                  <div className={`message ${msg.role}`} key={index}>
                    <div className="message-role">
                      {msg.role === 'friday' ? 'FRIDAY' : 'YOU'}
                    </div>
                    <div dangerouslySetInnerHTML={{ __html: renderMarkdownLite(msg.content) }} />
                    {msg.role === 'friday' && voiceEnabled && speechSynthesisAvailable && (
                      <button
                        type="button"
                        className="message-voice-button"
                        onClick={() => speakResponse(msg.content)}
                      >
                        <Volume2 size={14} /> Play response
                      </button>
                    )}
                    {msg.sources?.length > 0 && (
                      <div className="message-sources">
                        <strong>Sources</strong>
                        {msg.sources.map((source, sourceIndex) => {
                          const url = source.url || source.link || source.href;
                          const label = source.title || source.name || source.source || `Source ${sourceIndex + 1}`;
                          return url ? (
                            <a key={`${url}-${sourceIndex}`} href={url} target="_blank" rel="noopener noreferrer">
                              {label}
                            </a>
                          ) : <span key={`${label}-${sourceIndex}`}>{label}</span>;
                        })}
                      </div>
                    )}
                    {msg.trace && (
                      <div className="trace-box">
                        <button
                          type="button"
                          className="trace-header"
                          onClick={() => toggleTrace(index)}
                          aria-expanded={Boolean(openTraces[index])}
                        >
                          <span className="trace-summary">
                            {msg.trace.agent_used?.toUpperCase() || 'DIRECT'} ? {msg.trace.intent?.intent?.toUpperCase()}
                            {' ? '}{msg.trace.steps_executed?.length} steps
                            {' ? '}{msg.trace.total_duration_seconds}s
                          </span>
                          <span>{openTraces[index] ? 'Hide plan' : 'View plan'}</span>
                        </button>
                        {openTraces[index] && (
                          <div className="trace-details">
                            <div className="trace-plan-title">Goal: {msg.trace.plan?.task_goal}</div>
                            <div className="trace-steps">
                              {msg.trace.steps_executed?.map(step => (
                                <div className="trace-step-item" key={step.step_number}>
                                  <span className="trace-step-num">[{step.step_number}]</span>
                                  <span className="trace-step-desc">{step.description}</span>
                                  <span className={`trace-step-status ${step.status}`}>{step.status}</span>
                                  {step.tool_name && <span className="trace-tool-tag">{step.tool_name}</span>}
                                  <span className="trace-step-time">{step.duration_seconds}s</span>
                                </div>
                              ))}
                            </div>
                            <div className="trace-metrics">
                              <span>Model: {msg.trace.model_used}</span>
                              <span>Latency: {msg.trace.model_latency_seconds ?? 'N/A'}s</span>
                              <span>Tokens: {msg.trace.token_count ?? 'N/A'}</span>
                            </div>
                            {msg.trace.sources_used?.length > 0 && (
                              <div className="trace-sources">Sources: {msg.trace.sources_used.join(' ? ')}</div>
                            )}
                            {msg.trace.warnings?.length > 0 && (
                              <div className="warning-text">{msg.trace.warnings.join(' ? ')}</div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
                {isLoading && (
                  <div className="message friday processing-message">
                    <span className="status-dot pulse" /> FRIDAY is processing the request?
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              <form onSubmit={handleSend} className="input-area">
                <div className="voice-controls">
                  <label className="voice-toggle">
                    <input
                      type="checkbox"
                      checked={voiceEnabled}
                      onChange={handleVoiceToggle}
                      disabled={!speechRecognitionAvailable && !speechSynthesisAvailable}
                    />
                    <span>Enable voice</span>
                  </label>
                  {voiceEnabled && speechRecognitionAvailable && (
                    <button
                      type="button"
                      className="voice-control-button"
                      onClick={isListening ? stopListening : startListening}
                      disabled={isLoading}
                    >
                      {isListening ? <MicOff size={15} /> : <Mic size={15} />}
                      {isListening ? 'Cancel listening' : 'Speak request'}
                    </button>
                  )}
                  {voiceEnabled && speechSynthesisAvailable && (
                    <button
                      type="button"
                      className="voice-control-button"
                      onClick={cancelSpeech}
                      disabled={!isSpeaking}
                    >
                      <VolumeX size={15} /> Stop speech
                    </button>
                  )}
                  <span className="voice-status" role="status" aria-live="polite">
                    {voiceStatus}
                  </span>
                </div>
                <div className="input-container">
                  <span className="input-prompt">FRIDAY&gt;</span>
                  <input
                    type="text"
                    value={input}
                    onChange={event => setInput(event.target.value)}
                    placeholder="Ask a question or describe a task?"
                    className="console-input"
                    disabled={isLoading}
                    autoFocus
                  />
                  <button type="submit" className="send-button" disabled={isLoading || !input.trim()}>
                    <Send size={18} />
                  </button>
                </div>
              </form>
            </section>
          )}

          {activeView === 'intelligence' && (
            <IntelligenceSection telemetry={telemetry} onOpenMonitor={() => setIsPopupOpen(true)} />
          )}
          {activeView === 'research' && <ResearchSection messages={messages} />}
          {activeView === 'activity' && (
            <ExecutionHistorySection
              historyEnabled={historyEnabled}
              executionHistory={executionHistory}
              historyStatus={historyStatus}
              isHistoryLoading={isHistoryLoading}
              openHistory={openHistory}
              onHistoryToggle={handleHistoryToggle}
              onToggleRecord={traceId => setOpenHistory(previous => ({
                ...previous,
                [traceId]: !previous[traceId]
              }))}
              onFeedback={handleHistoryFeedback}
              onDelete={handleDeleteHistory}
              onClear={handleClearHistory}
            />
          )}
          {activeView === 'scheduled' && (
            <ScheduledTasksSection
              tasks={scheduledTasks}
              runs={scheduledRuns}
              status={scheduledStatus}
              isLoading={isScheduleLoading}
              titleDraft={scheduleTitleDraft}
              promptDraft={schedulePromptDraft}
              intervalDraft={scheduleInterval}
              onTitleChange={setScheduleTitleDraft}
              onPromptChange={setSchedulePromptDraft}
              onIntervalChange={setScheduleInterval}
              onCreate={handleCreateScheduledTask}
              onStatusChange={handleScheduledTaskStatus}
              onDelete={handleDeleteScheduledTask}
            />
          )}
          {activeView === 'memory' && (
            <MemorySection
              memoryEnabled={memoryEnabled}
              memoryStatus={memoryStatus}
              memorySessions={memorySessions}
              savedMemories={savedMemories}
              memoryCategory={memoryCategory}
              memoryDraft={memoryDraft}
              isMemoryLoading={isMemoryLoading}
              onMemoryToggle={handleMemoryToggle}
              onLoadSession={handleLoadSession}
              onDeleteSession={handleDeleteSession}
              onCategoryChange={setMemoryCategory}
              onDraftChange={setMemoryDraft}
              onSaveMemory={handleSaveMemory}
              onDeleteMemory={handleDeleteMemory}
              onNewSession={() => {
                setSessionId(null);
                setMessages([{ role: 'friday', content: getInitialGreeting(), trace: null }]);
              }}
            />
          )}
          {activeView === 'system' && (
            <SystemSection
              health={health}
              models={availableModels}
              onModelChange={handleModelChange}
              telemetry={telemetry}
              onRefresh={refreshAll}
            />
          )}
        </div>
      </main>

      <WorldMonitorPopup
        isOpen={isPopupOpen}
        onClose={() => setIsPopupOpen(false)}
        telemetry={telemetry}
      />
    </div>
  );
}

export default App;

# F.R.I.D.A.Y. Geopolitical Intelligence & Threat Matrix Assistant

F.R.I.D.A.Y. (Female Real-Time Intelligence Device & Assistant Yard) is a local-first AI assistant built with FastAPI, React, and Ollama. It includes a request orchestrator, model selection, World Monitor telemetry, web/news search, and per-request execution traces. External feeds may be unavailable; the UI and API mark static fallback data as samples rather than live readings.

---

## 🚀 Key Features

*   **Geopolitical Threat Matrix Routing:** Routes situation queries to World Monitor risk telemetry and news.
*   **World Intelligence Briefings:** Combines region-filtered World Monitor indicators, news, and supplemental research with timestamps, source links, freshness labels, and a distinct analysis section.
*   **Research Agent:** Searches news/web sources and prepares evidence-grounded responses with clickable citations. Search snippets are treated as unverified claims; full article text is not currently retrieved.
*   **Opt-in Persistent Memory:** Stores chats and explicit user-saved memories in local SQLite only after enabling it. The user can inspect/delete saved data; do not store passwords or secrets.
*   **Opt-in Execution History:** Separately controls local trace retention, feedback, and deletion. Traces include intent, plan, tool status/timing, model, and provider token counts when available.
*   **Model Manager:** Lists available Ollama models, supports model selection, and exposes a benchmark endpoint.
*   **Execution Traces:** Chat responses include the request intent, selected agent, plan, step status, duration, model, and source labels.
*   **Real-time Time-of-Day Greetings:** Adapts conversational greetings dynamically in both backend prompt contexts and frontend interface depending on local browser clock times.
*   **Live and Fallback Status:** World Monitor data reports whether it is live; static fallback samples are labeled and do not claim current publication times.

---

## 🛠️ Configuration Details

The system reads settings dynamically via environment variables or falls back to sensible local defaults:

| Variable | Description | Default Value |
| :--- | :--- | :--- |
| `OLLAMA_BASE_URL` | The endpoint url for your local Ollama server | `http://localhost:11434` |
| `OLLAMA_MODEL` | The LLM model to be used by the agent | `llama3.2` |
| `OLLAMA_TIMEOUT_SECONDS` | Inference timeout | `60.0` |
| `OLLAMA_RETRY_COUNT` | Retry count for transient inference failures | `2` |
| `CORS_ORIGINS` | Comma-separated frontend origins | `http://localhost:5173,http://127.0.0.1:5173` |
| `NEWS_API_KEY` | Reserved; current Google News RSS integration does not use this key | (unused) |
| `WORLD_MONITOR_API_KEY` | Optional key for World Monitor REST feeds | (none; displays labeled static sample data) |
| `WORLD_MONITOR_TIMEOUT_SECONDS` | World Monitor request timeout | `8.0` |
| `WORLD_MONITOR_RETRY_COUNT` | Retry count for transient risk-feed failures | `1` |
| `SEARCH_TIMEOUT_SECONDS` | News/search request timeout | `8.0` |
| `WEATHER_TIMEOUT_SECONDS` | Location/weather request timeout | `8.0` |
| `MEMORY_DB_PATH` | Local SQLite path for opt-in conversation, memory, and execution history | `backend/data/friday.sqlite3` |
| `SERVER_TTS_ENABLED` | Opt in to legacy speech playback on the backend host | `false` |

### Voice controls

The assistant workspace can use browser speech recognition for microphone input and browser speech synthesis for spoken replies. Voice is off by default; enabling it is an explicit user action, and the browser asks for microphone permission when speech input starts. Speech recognition support and processing vary by browser and may rely on the browser's speech service. Transcribed text is placed in the composer for review before sending. Text chat remains available when voice is off or unsupported.

The legacy `pyttsx3` backend-host playback is disabled by default to avoid duplicate audio and to keep voice output under the browser controls. Set `SERVER_TTS_ENABLED=true` only when host-side playback is desired; this setting is independent of the browser voice toggle.

### Memory privacy

Persistent memory and execution-history retention have separate opt-in switches and are both off by default. When enabled, conversations are saved locally; individual memory items are saved only when explicitly added. Execution history includes prompts and trace details; common credential fields are redacted, but this is not a guarantee against every secret format. Turning either switch off stops new storage/retrieval for that feature but does not erase existing data. Inspect or delete saved records in the app. The browser's local profile ID is only a data-partitioning key, not authentication; do not expose this local backend to untrusted users or save secrets.

### Routing evaluation

The repeatable 15-case intent-routing evaluation can be run from the `backend` directory with `python -m app.evaluation`. It reports overall and per-intent accuracy; this local heuristic check does not evaluate live model response quality.

---

## 📦 Getting Started

### Prerequisites
1.  **Install Ollama:** Download and install [Ollama](https://ollama.com/).
2.  **Pull Llama 3.2:** Run the following command in your terminal:
    ```bash
    ollama pull llama3.2
    ```

### Configuration
From the repository root, copy `.env.example` to `.env` and adjust values if needed. The example contains no credentials. Keep real API keys in the local `.env` file and do not commit it.

### Running the Backend (FastAPI)
1.  Navigate to the project directory:
    ```bash
    cd G:\FRIDAY_AI_Assistant
    ```
2.  Create and activate a Python virtual environment:
    ```bash
    python -m venv .venv
    .venv\Scripts\Activate.ps1
    ```
3.  Install dependencies:
    ```bash
    pip install -r backend/requirements.txt
    ```
4.  Run the backend server:
    ```bash
    python backend/run.py
    ```
    The API will run on `http://127.0.0.1:8000`. Ollama should be available at the configured `OLLAMA_BASE_URL`.

### Running the Frontend (React + Vite)
1.  Open a new terminal window and navigate to the frontend directory:
    ```bash
    cd G:\FRIDAY_AI_Assistant\frontend
    ```
2.  Install packages:
    ```bash
    npm install
    ```
3.  Run the Vite development server:
    ```bash
    npm run dev
    ```
    The console interface will open on `http://localhost:5173`.

### Checks
Run the backend tests with the project virtual environment activated:
```powershell
python -m pytest backend\tests -q
```

Build the frontend:
```powershell
Set-Location frontend
npm run build
```

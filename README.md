# F.R.I.D.A.Y. Geopolitical Intelligence & Threat Matrix Assistant

F.R.I.D.A.Y. (Female Real-Time Intelligence Device & Assistant Yard) is an Iron Man-inspired AI assistant console. It uses local LLMs (Llama 3.2 via Ollama) integrated with real-time geopolitical threat telemetry from the World Monitor API, live news feeds, and search verification/self-correction pipelines.

---

## 🚀 Key Features

*   **Geopolitical Threat Matrix Routing:** Automatically detects queries about world situations, reads country threat levels and components (military, economic, news, and infrastructure index), and projects a live interactive dashboard map.
*   **Search Verification & Self-Correction Agent:** For general reasoning tasks, the agent drafts a response, queries web searches to verify facts/data, and self-corrects any hallucinations or outdated facts before outputting.
*   **Real-time Time-of-Day Greetings:** Adapts conversational greetings dynamically in both backend prompt contexts and frontend interface depending on local browser clock times.
*   **Integrated Live Feeds:** Pulls real-time articles directly from the World Monitor API, calculating dynamic relative times (e.g. "2 hours ago") and alert indicators.

---

## 🛠️ Configuration Details

The system reads settings dynamically via environment variables or falls back to sensible local defaults:

| Variable | Description | Default Value |
| :--- | :--- | :--- |
| `OLLAMA_BASE_URL` | The endpoint url for your local Ollama server | `http://localhost:11434` |
| `OLLAMA_MODEL` | The LLM model to be used by the agent | `llama3.2` |
| `NEWS_API_KEY` | Optional API key for Google News feeds | (none, falls back to web scraping) |
| `WORLD_MONITOR_API_KEY` | Optional key to query the World Monitor REST feeds API | (none, falls back to mock dashboard data) |

---

## 📦 Getting Started

### Prerequisites
1.  **Install Ollama:** Download and install [Ollama](https://ollama.com/).
2.  **Pull Llama 3.2:** Run the following command in your terminal:
    ```bash
    ollama pull llama3.2
    ```

### Running the Backend (FastAPI)
1.  Navigate to the project directory:
    ```bash
    cd g:/FRIDAY_AI_Assistant
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
    The API will run on `http://127.0.0.1:8000`.

### Running the Frontend (React + Vite)
1.  Open a new terminal window and navigate to the frontend directory:
    ```bash
    cd g:/FRIDAY_AI_Assistant/frontend
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

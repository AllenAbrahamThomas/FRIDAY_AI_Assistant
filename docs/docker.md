# Docker Compose setup

Compose runs the React frontend, FastAPI backend, and Ollama in separate containers. The frontend is served by Nginx, which forwards `/api` requests to the backend. The app is exposed only on the local machine:

- Workspace: `http://localhost:5173`
- Backend API and docs: `http://localhost:8000` and `http://localhost:8000/docs`

## Requirements

- Docker Desktop with Docker Compose on Windows, or Docker Engine with Compose on Linux.
- Internet access for the initial image builds and Ollama model download.
- Enough disk space for the container images and selected model. Ollama models are stored separately from the container image.
- For GPU inference on Windows, Docker Desktop must use its WSL2 backend and have NVIDIA GPU support configured. CPU inference works without this.

## Start the stack

From the repository root in PowerShell:

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose ps
docker compose exec ollama ollama pull llama3.2
```

Open `http://localhost:5173`. `OLLAMA_MODEL` defaults to `llama3.2`; pull that model before chatting. To use another model, pull it in the Ollama container and set `OLLAMA_MODEL` in `.env`, then recreate the backend:

```powershell
docker compose exec ollama ollama pull qwen3:8b
```

```env
OLLAMA_MODEL=qwen3:8b
```

```powershell
docker compose up -d --force-recreate backend
```

For GPU inference, use the additional Compose file:

```powershell
docker compose -f compose.yaml -f compose.gpu.yaml up --build -d
```

The base Compose configuration does not request a GPU, so it remains usable on CPU-only Docker installations. GPU passthrough is optional and depends on Docker Desktop/WSL2 configuration.

## Operations and data

```powershell
docker compose logs -f backend frontend ollama
docker compose down
```

The `friday_data` named volume stores the SQLite database (opt-in memory, execution history, and scheduled tasks). The `ollama_data` volume stores downloaded models. `docker compose down` preserves both. **`docker compose down -v` deletes both volumes and permanently removes that data and the downloaded models.**

The backend's legacy host-speaker TTS is disabled in the container; browser voice controls continue to run on the user's device. Optional API keys and other backend settings can be placed in the untracked `.env` file. Compose sets the Ollama URL and database path to container-appropriate values.

The frontend routes API calls through Nginx, so browser requests are same-origin. For running Vite outside Docker, its `/api` development proxy targets `http://127.0.0.1:8000`.

## Troubleshooting

- Check `docker compose ps` and `docker compose logs backend ollama` if the API is unavailable.
- A degraded Ollama status before the model is pulled is expected. Run `docker compose exec ollama ollama pull llama3.2` and refresh the workspace.
- If the GPU override fails, verify Docker Desktop's WSL2/NVIDIA GPU support, or run the base CPU configuration.
- If port 5173 or 8000 is occupied, stop the conflicting local service or change the host-side published port in `compose.yaml`. The backend still listens on port 8000 inside the Compose network.

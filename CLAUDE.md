# Agentic Incident Intelligence Platform

## Project Overview

AI-powered production debugging and root cause analysis platform. Chat-based UI where users define business context profiles, then interact with an LLM agent that uses that context to diagnose incidents.

## Architecture

- **Frontend**: React + Vite + TypeScript (port 3000)
- **Backend**: FastAPI + LangGraph + Python (port 8000), managed with UV
- **Database**: SQLite (file: `data/app.db`)
- **LLM**: Claude via Anthropic API or AWS Bedrock (configured by `LLM_PROVIDER` env var)
- **Deployment**: Docker Compose

## Development Commands

### Backend (from `backend/`)
```bash
uv sync                          # Install dependencies
uv run fastapi dev src/main.py   # Run dev server with hot reload
uv run pytest                    # Run tests
```

### Frontend (from `frontend/`)
```bash
npm install          # Install dependencies
npm run dev          # Vite dev server
npm run build        # Production build
npm run lint         # ESLint
```

### Docker
```bash
docker compose up --build    # Full stack
docker compose up backend    # Backend only
docker compose up frontend   # Frontend only
```

## Key Patterns

### Backend
- All API routes prefixed with `/api/`
- Pydantic models for request/response validation in `src/api/models.py`
- SQLite accessed via `aiosqlite` — async throughout
- Context profiles loaded from DB and injected as system prompt on every LLM call
- LLM provider abstraction in `src/llm/provider.py` — factory pattern selecting anthropic vs bedrock
- Agent graph defined in `src/agent/graph.py` using LangGraph StateGraph
- Environment config via `src/config.py` using pydantic-settings

### Frontend
- React Router for page navigation
- Context-first UX: if no profiles exist, redirect to `/contexts/new`
- Chat state managed per-session, sessions bound to a context profile
- API calls centralized in `src/services/api.ts`
- Streaming responses via SSE (EventSource)

### Database
- Schema auto-created on startup via `src/db/migrations.py`
- Tables: `context_profiles`, `chat_sessions`, `chat_messages`
- UUIDs as primary keys (generated server-side)
- JSON columns for `knowledge_sources`, `tool_configs`, `severity_rules`, `metadata`

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `LLM_PROVIDER` | Yes | `anthropic` or `bedrock` |
| `ANTHROPIC_API_KEY` | If provider=anthropic | Anthropic API key |
| `MODEL_ID` | Yes | Model identifier (e.g., `claude-sonnet-4-20250514`) |
| `AWS_ACCESS_KEY_ID` | If provider=bedrock | AWS credentials |
| `AWS_SECRET_ACCESS_KEY` | If provider=bedrock | AWS credentials |
| `AWS_REGION` | If provider=bedrock | AWS region |
| `DATABASE_PATH` | No | SQLite path (default: `data/app.db`) |

## File Conventions

- Backend source lives in `backend/src/` — all imports relative to `src`
- Frontend source lives in `frontend/src/`
- No `.env` files committed — use `.env.example` as template
- Tests mirror source structure: `backend/tests/test_<module>.py`

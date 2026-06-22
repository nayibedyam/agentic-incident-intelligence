# Agentic Incident Intelligence

AI-powered production debugging and root cause analysis platform. A chat-based interface where engineers interact with an LLM agent that uses business context profiles and external tools (JIRA, Confluence, etc.) to diagnose incidents, correlate signals, and accelerate resolution.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Docker Compose                               │
│                                                                     │
│  ┌──────────────┐       REST/SSE        ┌────────────────────────┐ │
│  │   Frontend   │ ◄──────────────────► │     Backend Agent       │ │
│  │ React + Vite │                       │ FastAPI + LangGraph     │ │
│  │  Port: 3000  │                       │     Port: 8000         │ │
│  └──────────────┘                       └──────────┬─────────────┘ │
│                                                    │               │
│                           ┌────────────────────────┼──────────┐    │
│                           │                        │          │    │
│                           ▼                        ▼          ▼    │
│                    ┌────────────┐           ┌────────┐  ┌────────┐│
│                    │ MCP Servers│           │ Claude │  │Bedrock ││
│                    │  (Docker)  │           │  API   │  │  API   ││
│                    └────────────┘           └────────┘  └────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

## How It Works

1. **Define Context Profiles** — Describe your service (architecture, failure modes, severity rules). This becomes the agent's system prompt.
2. **Register MCP Servers** — Add external tool servers (e.g., Atlassian MCP for JIRA/Confluence) via the UI. Link them to context profiles.
3. **Chat** — Ask the agent about incidents. It uses sub-agents and MCP tools to investigate, correlate logs, find similar past incidents, and generate post-mortems.

### Agent Pipeline

```
User Message
     │
     ▼
┌─────────────┐      ┌──────────────┐
│ Orchestrator│─────►│Tool Executor │──┐
│  (Claude)   │◄─────│              │  │
└─────────────┘      └──────────────┘  │
     │                     │           │
     ▼               ┌─────┴─────┐    │
   [END]             ▼           ▼    │
              ┌───────────┐ ┌───────┐ │
              │Sub-Agents │ │  MCP  │ │
              │(own LLM   │ │ Tools │ │
              │  calls)   │ │       │ │
              └───────────┘ └───────┘ │
                                      │
              Loop until no more ◄────┘
              tool calls (max 10)
```

### Built-in Sub-Agents

| Tool | Type | Description |
|------|------|-------------|
| `correlate_logs` | Investigation | Multi-service log correlation, causal timeline, root signal identification |
| `detect_changes` | Investigation | Correlates deployments/config changes with incident timing |
| `analyze_metrics` | Investigation | Metric anomaly detection, leading indicators, capacity assessment |
| `find_similar_incidents` | Knowledge | Searches JIRA/Confluence for past incidents with matching symptoms |
| `write_postmortem` | Knowledge | Generates structured blameless post-mortem document |
| `execute_runbook` | Knowledge | Step-by-step troubleshooting guidance with branching logic |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite, TypeScript, React Router, react-markdown |
| Backend | Python, FastAPI, LangGraph, aiosqlite |
| LLM | Claude (Anthropic API or AWS Bedrock) |
| Database | SQLite (WAL mode, async) |
| MCP | Docker-spawned servers, stdio JSON-RPC |
| Deployment | Docker Compose |

## Prerequisites

- Docker & Docker Compose
- One of:
  - Anthropic API key (`ANTHROPIC_API_KEY`)
  - AWS credentials with Bedrock access (profile-based or explicit keys)

## Quick Start

### 1. Clone and configure

```bash
git clone <repo-url>
cd agentic-incident-intelligence
```

Edit `run.sh` with your LLM provider settings:

```bash
# For Anthropic direct API:
export LLM_PROVIDER="anthropic"
export MODEL_ID="claude-sonnet-4-20250514"
export ANTHROPIC_API_KEY="sk-ant-..."

# For AWS Bedrock:
export LLM_PROVIDER="bedrock"
export MODEL_ID="us.anthropic.claude-sonnet-4-20250514-v1:0"
export AWS_PROFILE="your-profile"   # or set AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY
export AWS_REGION="us-west-2"
```

### 2. Run

```bash
chmod +x run.sh
./run.sh
```

This runs `docker compose up --build` with your environment configured.

### 3. Access

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### First Launch

1. You'll be prompted to create a **Context Profile** (name, description, system prompt describing your service).
2. Navigate to **MCP Servers** to register external tool servers.
3. Edit your context profile to **link** the MCP servers you want available.
4. Start chatting about incidents.

## Development (without Docker)

### Backend

```bash
cd backend
uv sync                          # Install dependencies
uv run fastapi dev src/main.py   # Dev server with hot reload on :8000
uv run pytest                    # Run tests
```

### Frontend

```bash
cd frontend
npm install
npm run dev                      # Vite dev server on :3000
npm run build                    # Production build
```

## Registering MCP Servers

MCP servers are registered dynamically via the UI — no code changes needed.

### Example: Atlassian (JIRA + Confluence)

Navigate to `/mcp-servers` and add:

| Field | Value |
|-------|-------|
| Name | `atlassian-mcp` |
| Description | JIRA and Confluence integration |
| Command | `docker` |
| Args | `run` / `--rm` / `-i` / `ghcr.io/sooperset/mcp-atlassian:latest` (one per line) |
| Env | `JIRA_URL=https://your-org.atlassian.net` |
| | `JIRA_USERNAME=user@example.com` |
| | `JIRA_API_TOKEN=your-token` |
| | `CONFLUENCE_URL=https://your-org.atlassian.net/` |
| | `CONFLUENCE_USERNAME=user@example.com` |
| | `CONFLUENCE_API_TOKEN=your-token` |

Then edit your context profile and check the box to link it.

## Project Structure

```
agentic-incident-intelligence/
├── run.sh                        # Startup script with env config
├── docker-compose.yml
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── ChatPage.tsx          # Main chat interface
│   │   │   ├── ContextSetupPage.tsx  # Create/edit context profiles
│   │   │   ├── ContextManagePage.tsx # List contexts
│   │   │   └── MCPServersPage.tsx    # Register/manage MCP servers
│   │   ├── components/
│   │   │   ├── ContextSwitcher.tsx   # Context dropdown
│   │   │   └── SessionSidebar.tsx    # Session list + nav
│   │   ├── services/api.ts          # API client
│   │   └── types/index.ts           # TypeScript interfaces
│   └── package.json
├── backend/
│   ├── src/
│   │   ├── main.py                   # FastAPI entry + lifespan
│   │   ├── config.py                 # Environment settings
│   │   ├── api/
│   │   │   ├── routes.py            # REST endpoints
│   │   │   └── models.py            # Pydantic models
│   │   ├── agent/
│   │   │   ├── orchestrator.py      # Chat handler (stream + sync)
│   │   │   ├── graph.py             # LangGraph state graph
│   │   │   ├── tools.py             # Tool registry + dispatcher
│   │   │   └── sub_agents/
│   │   │       ├── log_correlator.py
│   │   │       ├── change_detector.py
│   │   │       ├── metric_analyzer.py
│   │   │       ├── similar_incident_finder.py
│   │   │       ├── postmortem_writer.py
│   │   │       └── runbook_executor.py
│   │   ├── context/
│   │   │   ├── manager.py           # Context CRUD
│   │   │   └── loader.py            # Context + MCP startup
│   │   ├── db/
│   │   │   ├── database.py          # aiosqlite connection
│   │   │   └── migrations.py        # Schema
│   │   ├── llm/
│   │   │   └── provider.py          # Anthropic/Bedrock factory
│   │   └── mcp/
│   │       ├── client.py            # MCP process manager
│   │       └── manager.py           # MCP server DB CRUD
│   └── pyproject.toml
└── data/
    └── app.db                        # SQLite (auto-created)
```

## API Overview

| Endpoint | Description |
|----------|-------------|
| `POST /api/chat/stream` | Send message, get SSE stream |
| `GET /api/context` | List context profiles |
| `POST /api/context` | Create context profile |
| `GET /api/mcp/servers` | List MCP servers |
| `POST /api/mcp/servers` | Register MCP server |
| `POST /api/mcp/servers/{id}/start` | Start MCP server |
| `POST /api/context/{id}/mcp-servers/{sid}` | Link MCP to context |
| `GET /api/agent/status` | Health + available tools |

Full OpenAPI docs at `/docs` when backend is running.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `LLM_PROVIDER` | Yes | `anthropic` or `bedrock` |
| `MODEL_ID` | Yes | Model identifier |
| `ANTHROPIC_API_KEY` | If anthropic | API key |
| `AWS_PROFILE` | If bedrock (profile) | AWS credentials profile |
| `AWS_ACCESS_KEY_ID` | If bedrock (keys) | IAM access key |
| `AWS_SECRET_ACCESS_KEY` | If bedrock (keys) | IAM secret key |
| `AWS_REGION` | If bedrock | AWS region |
| `DATABASE_PATH` | No | SQLite path (default: `data/app.db`) |

## Design Decisions

- **Tool-use loop over sub-agent routing** — Single LLM decides what to invoke. Sub-agents are specialized tools that make their own LLM calls for deep reasoning.
- **MCP servers as first-class entities** — Decoupled from context profiles via a join table. Register once, link to many contexts.
- **Context-scoped tools** — Only MCP servers linked to the active context are available. Prevents tool leakage across contexts.
- **Docker-spawned MCP** — Each MCP server runs in its own container via mounted docker.sock. Isolated, no dependency conflicts.
- **SQLite** — Zero-config persistence. WAL mode for concurrent reads. Sufficient for single-node.
- **SSE streaming** — Real-time token delivery including during tool-use loops.

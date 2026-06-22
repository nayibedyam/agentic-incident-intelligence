# Agentic Incident Intelligence Platform - Specification

## 1. Overview

An AI-powered production debugging and root cause analysis platform that accelerates incident triage, reduces MTTR, and minimizes manual investigation effort. The system acts as an intelligent first-line diagnostic agent for production systems.

## 2. Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                            Docker Compose                                 │
│                                                                          │
│  ┌──────────────┐       REST/SSE         ┌────────────────────────────┐ │
│  │   Frontend   │ ◄──────────────────►  │       Backend Agent         │ │
│  │  (React+Vite)│                        │  (FastAPI + LangGraph + UV)│ │
│  │  Port: 3000  │                        │       Port: 8000           │ │
│  └──────────────┘                        └─────────┬──────────────────┘ │
│                                                    │                     │
│                               ┌────────────────────┼───────────────┐    │
│                               │                    │               │    │
│                               ▼                    ▼               ▼    │
│                        ┌────────────┐       ┌──────────┐   ┌──────────┐│
│                        │Dynamic MCP │       │  Claude  │   │  Bedrock ││
│                        │  Servers   │       │   API    │   │   API    ││
│                        │(via Docker)│       └──────────┘   └──────────┘│
│                        └────────────┘                                   │
│                         ▲ spawned via docker.sock                        │
│                         │                                                │
│                    ┌────┴────────────────────────────────┐              │
│                    │ e.g. ghcr.io/sooperset/mcp-atlassian│              │
│                    │ (JIRA, Confluence, any MCP server)  │              │
│                    └────────────────────────────────────┘              │
└──────────────────────────────────────────────────────────────────────────┘
```

## 3. Components

### 3.1 Frontend (React + Vite + TypeScript)

- **Framework**: React 18 with Vite, TypeScript
- **Core UI**: Chat interface for user interaction
- **Features**:
  - Conversational chat box with markdown rendering
  - Streaming response display via SSE (Server-Sent Events)
  - Session history sidebar
  - Context profile switcher (dropdown in chat header)
  - Context profile management (create/edit/delete)
  - **MCP Server management page** (register/edit/delete/start/stop MCP servers)
  - Context-to-MCP linking (toggle which MCP servers a context profile uses)
- **Routing**: React Router for page navigation
- **Communication**: REST API calls + SSE streaming to backend
- **Port**: 3000

### 3.2 Backend Agent (FastAPI + LangGraph + Python)

- **Package Manager**: UV
- **Framework**: LangGraph SDK (Python) with tool-use loop
- **Server**: FastAPI with async support
- **Port**: 8000

#### 3.2.1 Agent Architecture — Tool-Use Loop with Sub-Agents

The agent uses a single-LLM tool-use routing pattern. Claude decides which tools (including sub-agents) to invoke based on the conversation context. Sub-agents are specialized LLM calls invoked as tools — they do their own multi-step reasoning and return structured results.

```
┌───────────────────────────────────────────────────────────────────────────┐
│                         LangGraph StateGraph                               │
│                                                                           │
│  ┌────────────────────┐                                                   │
│  │   Orchestrator     │◄────────────────────────────┐                     │
│  │  (LLM + tools)     │                             │                     │
│  └────────┬───────────┘                             │                     │
│           │                                         │                     │
│    should_continue?                                 │                     │
│     │         │                                     │                     │
│     ▼         ▼                                     │                     │
│  ┌──────┐  ┌──────────────┐                         │                     │
│  │ END  │  │ Tool Executor │─────────────────────────┘                     │
│  └──────┘  └──────┬───────┘                                              │
│                   │                                                       │
│      ┌────────────┼─────────────┬──────────────┐                          │
│      ▼            ▼             ▼              ▼                          │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐                  │
│ │ Built-in │ │Sub-Agent │ │Sub-Agent │ │ Dynamic MCP  │                  │
│ │  Tools   │ │(own LLM  │ │(own LLM  │ │   Tools      │                  │
│ │          │ │  call)   │ │  call)   │ │(context-scoped)│                │
│ └──────────┘ └──────────┘ └──────────┘ └──────────────┘                  │
└───────────────────────────────────────────────────────────────────────────┘
```

**Flow:**
1. User message → Orchestrator node (LLM call with all available tools)
2. If LLM returns `tool_use` blocks → Tool Executor node runs them
3. Sub-agent tools make their own LLM call(s) internally and return structured results
4. Tool results fed back to Orchestrator for next LLM call
5. Loop continues until LLM responds with text only (no tool calls) → END
6. Max 10 iterations as safety limit

**Built-in tools:**
- `analyze_logs` — Structured log analysis for error patterns, anomalies, correlations
- `validate_hypothesis` — Cross-reference root cause hypotheses against evidence

**Investigation Sub-Agents** (each makes its own LLM call for specialized reasoning):

| Tool Name | Sub-Agent | What It Does |
|-----------|-----------|-------------|
| `correlate_logs` | Log Correlator | Parses multi-service logs, builds causal timeline, correlates by request-id/trace-id, identifies the root signal |
| `detect_changes` | Change Detector | Analyzes recent deployments/config changes and correlates with incident timing, recommends rollbacks |
| `analyze_metrics` | Metric Analyzer | Detects anomalies in metrics, finds correlations between metrics, identifies leading indicators and capacity issues |

**Knowledge Sub-Agents** (leverage MCP tools + LLM reasoning):

| Tool Name | Sub-Agent | What It Does |
|-----------|-----------|-------------|
| `find_similar_incidents` | Similar Incident Finder | Searches JIRA/Confluence for past incidents with matching symptoms, surfaces applicable resolutions |
| `write_postmortem` | Post-Mortem Writer | Generates structured blameless post-mortem with timeline, root cause, action items, lessons learned |
| `execute_runbook` | Runbook Executor | Guides through troubleshooting steps with branching logic, adapts based on findings |

**Dynamic MCP tools:** Tools from MCP servers linked to the active context profile (e.g., JIRA search, Confluence page retrieval). Only servers explicitly linked to the context are available — unlinked servers' tools are hidden.

#### 3.2.2 LLM Provider Support

The backend supports dual invocation modes:

| Mode | Config | Use Case |
|------|--------|----------|
| **Direct Anthropic API** | `ANTHROPIC_API_KEY` | Development, direct Claude API calls |
| **AWS Bedrock** | `AWS_PROFILE` or `AWS_ACCESS_KEY_ID`+`AWS_SECRET_ACCESS_KEY`, `AWS_REGION` | Enterprise deployments via Bedrock |

Provider selection via environment variable `LLM_PROVIDER=anthropic|bedrock`.

Bedrock supports both explicit IAM credentials and AWS profile-based authentication (via `boto3.Session(profile_name=...)`).

Model ID is configurable via `MODEL_ID` env var (e.g., `claude-sonnet-4-20250514` for direct API, `us.anthropic.claude-opus-4-8` for Bedrock).

### 3.3 Model Context Protocol (MCP) Integration

MCP servers are **dynamically registered and managed via the UI** — there are no hardcoded connectors. Each MCP server is its own first-class entity in the database, independent of context profiles.

#### 3.3.1 MCP Server Lifecycle

```
Register via UI → Stored in SQLite → Link to Context Profile(s)
                                            │
                                            ▼
               User starts chat session with that context
                                            │
                                            ▼
               Backend auto-starts linked MCP servers (if not running)
                                            │
                                            ▼
               MCP tools become available to the LLM in that session
```

#### 3.3.2 MCP Transport

- **Protocol**: Newline-delimited JSON-RPC over stdio
- **Spawning**: Backend spawns MCP server as a Docker container via `docker exec` (using mounted docker.sock)
- **Buffer**: 10MB readline buffer to handle large tool lists (e.g., Atlassian MCP exposes 73+ tools)
- **Env injection**: Environment variables (API tokens, URLs) are injected as `-e KEY=VALUE` Docker flags

#### 3.3.3 Example: Atlassian MCP Server

Registered via UI with:
- **Command**: `docker`
- **Args**: `run`, `--rm`, `-i`, `ghcr.io/sooperset/mcp-atlassian:latest`
- **Env**: `JIRA_URL`, `JIRA_USERNAME`, `JIRA_API_TOKEN`, `CONFLUENCE_URL`, etc.

Provides tools: `jira_search`, `jira_get_issue`, `confluence_search`, `confluence_get_page`, and ~70 more.

## 4. Context Memory Layer (SQLite)

A core design principle: context is programmable at runtime so any team can plug in their business-specific debugging context. All context profiles and MCP server registrations are persisted in SQLite.

### 4.1 SQLite Schema

```sql
-- Context profiles: business context definitions
CREATE TABLE context_profiles (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    system_prompt TEXT NOT NULL,
    knowledge_sources JSON,
    severity_rules JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- MCP servers: independently managed tool server registrations
CREATE TABLE mcp_servers (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    command TEXT NOT NULL,
    args JSON NOT NULL DEFAULT '[]',
    env JSON NOT NULL DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Join table: many-to-many relationship between contexts and MCP servers
CREATE TABLE context_mcp_links (
    context_profile_id TEXT NOT NULL,
    mcp_server_id TEXT NOT NULL,
    PRIMARY KEY (context_profile_id, mcp_server_id),
    FOREIGN KEY (context_profile_id) REFERENCES context_profiles(id) ON DELETE CASCADE,
    FOREIGN KEY (mcp_server_id) REFERENCES mcp_servers(id) ON DELETE CASCADE
);

-- Chat sessions: each session is bound to a context profile
CREATE TABLE chat_sessions (
    id TEXT PRIMARY KEY,
    context_profile_id TEXT NOT NULL,
    title TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (context_profile_id) REFERENCES context_profiles(id)
);

-- Chat messages: conversation history per session
CREATE TABLE chat_messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
);
```

### 4.2 Context Profile Structure

```json
{
  "id": "uuid-here",
  "name": "payment-service",
  "description": "Payment processing microservice context",
  "system_prompt": "You are an expert incident responder for the Payment Service. This service handles credit card processing via Stripe, manages transaction state in PostgreSQL, and uses Redis for idempotency keys. Common failure modes include: connection pool exhaustion under load, Stripe webhook delivery delays, and race conditions in concurrent refund processing...",
  "knowledge_sources": [
    {"type": "runbook", "path": "/runbooks/payment-service.md"},
    {"type": "architecture", "path": "/docs/payment-arch.md"}
  ],
  "severity_rules": {
    "critical": ["payment_failure", "data_loss"],
    "high": ["latency_spike", "error_rate_increase"]
  }
}
```

### 4.3 MCP Server Structure

```json
{
  "id": "uuid-here",
  "name": "atlassian-mcp",
  "description": "JIRA and Confluence integration via MCP",
  "command": "docker",
  "args": ["run", "--rm", "-i", "ghcr.io/sooperset/mcp-atlassian:latest"],
  "env": {
    "JIRA_URL": "https://your-org.atlassian.net",
    "JIRA_USERNAME": "user@example.com",
    "JIRA_API_TOKEN": "your-token",
    "CONFLUENCE_URL": "https://your-org.atlassian.net/",
    "CONFLUENCE_USERNAME": "user@example.com",
    "CONFLUENCE_API_TOKEN": "your-token"
  },
  "running": false
}
```

### 4.4 Context Loading Flow

```
User starts/switches chat session with context profile
        │
        ▼
Backend loads context_profile from SQLite by ID
        │
        ▼
Loads linked MCP servers from context_mcp_links join table
        │
        ▼
Starts any linked MCP servers not already running
(spawns Docker containers, performs MCP initialize handshake)
        │
        ▼
Constructs system prompt:
  base_system_prompt + profile.system_prompt + severity_rules + active tools list
        │
        ▼
Invokes orchestrator with assembled context + all available tools
(built-in tools + all tools from running MCP servers)
```

## 5. Frontend UX Flow

### 5.1 Day-0 Experience (First Launch)

When no context profiles exist in the database, the UI forces the user through context creation before any chat is possible:

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   Welcome to Incident Intelligence                      │
│                                                         │
│   Before you begin, define your first system context.   │
│   This tells the agent about your service, its          │
│   architecture, and common failure modes.               │
│                                                         │
│   ┌───────────────────────────────────────────────┐     │
│   │  Context Name: [payment-service          ]    │     │
│   │  Description:  [Payment processing micro..]   │     │
│   │                                               │     │
│   │  System Context (what should the agent know): │     │
│   │  ┌───────────────────────────────────────┐    │     │
│   │  │ You are debugging a payment service   │    │     │
│   │  │ that processes credit cards via Stripe│    │     │
│   │  │ ...                                   │    │     │
│   │  └───────────────────────────────────────┘    │     │
│   │                                               │     │
│   │           [ Create Context ]                  │     │
│   └───────────────────────────────────────────────┘     │
│                                                         │
│   After creating, you can link MCP servers by editing.  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 5.2 Normal Operation (Context Exists)

Once at least one context profile exists, the UI loads the chat interface with a context switcher:

```
┌─────────────────────────────────────────────────────────────────┐
│ ┌──────────────┐  ┌─────────────────────────────────────────┐   │
│ │  Sessions    │  │  Context: [payment-service ▾]           │   │
│ │              │  │  ─────────────────────────────────────── │   │
│ │  > Session 1 │  │                                         │   │
│ │    Session 2 │  │  Chat messages (streamed, markdown)     │   │
│ │    Session 3 │  │                                         │   │
│ │              │  │                                         │   │
│ │              │  │                                         │   │
│ │  ──────────  │  │  ┌───────────────────────────────────┐  │   │
│ │  [+ New]     │  │  │ Type your message...              │  │   │
│ │  [⚙ Manage]  │  │  └───────────────────────────────────┘  │   │
│ └──────────────┘  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 MCP Server Management Page

A dedicated page for registering and managing MCP servers independently of context profiles:

```
┌─────────────────────────────────────────────────────────────────┐
│  MCP Servers                    [Back to Chat] [+ Add Server]   │
│                                                                 │
│  Manage Model Context Protocol servers. These provide external  │
│  tools (JIRA, Confluence, etc.) to the AI agent.                │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  atlassian-mcp                          [Running] ●        │ │
│  │  JIRA and Confluence integration                           │ │
│  │  docker run --rm -i ghcr.io/sooperset/mcp-atlassian:...   │ │
│  │  6 env variables configured                                │ │
│  │                          [Stop]  [Edit]  [Delete]          │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  github-mcp                             [Stopped] ○        │ │
│  │  GitHub integration for PR/issue lookup                    │ │
│  │  npx @modelcontextprotocol/server-github                   │ │
│  │  1 env variable configured                                 │ │
│  │                          [Start] [Edit]  [Delete]          │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 5.4 Context-MCP Linking (in Context Edit Page)

When editing a context profile, users can toggle which MCP servers are linked:

```
  Linked MCP Servers:
  Select which MCP servers this context can use for tool access.
  ┌──────────────────────────────────────────────────┐
  │  [✓] atlassian-mcp - JIRA and Confluence         │
  │  [ ] github-mcp - GitHub integration             │
  └──────────────────────────────────────────────────┘
  [Manage MCP Servers]
```

### 5.5 Context Switching Behavior

- The context dropdown in the header allows switching between profiles
- Switching context **starts a new chat session** bound to the selected profile
- Previous sessions remain accessible in the sidebar (grouped by context)
- The agent re-loads the new profile's system prompt and linked MCP servers
- A "Manage Contexts" page allows CRUD operations on all profiles

### 5.6 Frontend Pages/Routes

| Route | Page | Description |
|-------|------|-------------|
| `/` | Redirect | Shows setup wizard if no contexts exist; otherwise redirects to chat |
| `/contexts` | Context Management | List, create, edit, delete context profiles |
| `/contexts/new` | Create Context | Form to create a new context profile |
| `/contexts/:id/edit` | Edit Context | Edit context + manage MCP server links |
| `/mcp-servers` | MCP Server Management | Register, edit, delete, start/stop MCP servers |
| `/chat` | Chat Interface | Main chat UI with context switcher and session sidebar |
| `/chat/:sessionId` | Chat Session | Specific chat session view |

## 6. REST API Specification

### 6.1 Context Profile Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/context` | GET | List all context profiles |
| `/api/context` | POST | Create a new context profile |
| `/api/context/{id}` | GET | Get a single context profile |
| `/api/context/{id}` | PUT | Update an existing context profile |
| `/api/context/{id}` | DELETE | Remove a context profile |

### 6.2 MCP Server Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/mcp/servers` | GET | List all registered MCP servers (includes `running` status) |
| `/api/mcp/servers` | POST | Register a new MCP server |
| `/api/mcp/servers/{id}` | GET | Get a single MCP server |
| `/api/mcp/servers/{id}` | PUT | Update MCP server configuration |
| `/api/mcp/servers/{id}` | DELETE | Delete MCP server (stops if running, unlinks from all contexts) |
| `/api/mcp/servers/{id}/start` | POST | Start the MCP server (returns list of tool names) |
| `/api/mcp/servers/{id}/stop` | POST | Stop the MCP server |
| `/api/mcp/tools` | GET | List all currently available tools (built-in + MCP) |

### 6.3 Context-MCP Linking Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/context/{id}/mcp-servers` | GET | Get MCP servers linked to a context profile |
| `/api/context/{id}/mcp-servers/{server_id}` | POST | Link an MCP server to a context profile |
| `/api/context/{id}/mcp-servers/{server_id}` | DELETE | Unlink an MCP server from a context profile |

### 6.4 Chat Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Send a message, get agent response |
| `/api/chat/stream` | POST | Send a message, get streaming response (SSE) |
| `/api/chat/sessions` | GET | List chat sessions (optional `?context_id=` filter) |
| `/api/chat/sessions/{id}` | GET | Get messages for a session |
| `/api/chat/sessions/{id}` | DELETE | Delete a session and its messages |

### 6.5 Agent Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agent/status` | GET | Health check, running MCP servers, available tools |

### 6.6 Request/Response Format

**Chat Request:**
```json
{
  "message": "Why is the payment service returning 500 errors?",
  "session_id": "optional-session-uuid",
  "context_id": "context-profile-uuid",
  "attachments": [
    {"type": "log", "content": "..."},
    {"type": "trace", "content": "..."}
  ]
}
```

**Chat Response:**
```json
{
  "session_id": "uuid",
  "message": "Based on my analysis...",
  "metadata": {
    "root_cause": "Database connection pool exhaustion",
    "confidence": 0.87,
    "severity": "critical",
    "tools_used": ["jira_search", "analyze_logs"]
  }
}
```

**SSE Stream format:**
```
data: {"type": "session_id", "session_id": "uuid"}

data: {"type": "content", "content": "Based on "}

data: {"type": "content", "content": "my analysis..."}

data: {"type": "done"}
```

**MCP Server Create Request:**
```json
{
  "name": "atlassian-mcp",
  "description": "JIRA and Confluence integration",
  "command": "docker",
  "args": ["run", "--rm", "-i", "ghcr.io/sooperset/mcp-atlassian:latest"],
  "env": {
    "JIRA_URL": "https://your-org.atlassian.net",
    "JIRA_USERNAME": "user@example.com",
    "JIRA_API_TOKEN": "your-token"
  }
}
```

## 7. Project Structure

```
agentic-incident-intelligence/
├── spec.md
├── CLAUDE.md
├── docker-compose.yml
├── run.sh                            # Startup script with env config
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── App.tsx
│       ├── main.tsx
│       ├── index.css
│       ├── components/
│       │   ├── ContextSwitcher.tsx
│       │   └── SessionSidebar.tsx
│       ├── pages/
│       │   ├── ChatPage.tsx
│       │   ├── ContextSetupPage.tsx
│       │   ├── ContextManagePage.tsx
│       │   └── MCPServersPage.tsx
│       ├── services/
│       │   └── api.ts
│       └── types/
│           └── index.ts
├── backend/
│   ├── Dockerfile                    # Includes docker-ce-cli for MCP spawning
│   ├── pyproject.toml
│   └── src/
│       ├── main.py                   # FastAPI server entry + lifespan
│       ├── config.py                 # Pydantic settings from env
│       ├── api/
│       │   ├── routes.py             # All REST API endpoints
│       │   └── models.py             # Pydantic request/response models
│       ├── agent/
│       │   ├── orchestrator.py       # Chat handler (streaming + non-streaming)
│       │   ├── graph.py              # LangGraph StateGraph (orchestrator → tools → loop)
│       │   ├── state.py              # AgentState TypedDict
│       │   ├── tools.py              # Tool registry + dispatcher (built-in + sub-agents + MCP)
│       │   └── sub_agents/
│       │       ├── log_correlator.py       # Multi-service log correlation + timeline
│       │       ├── change_detector.py      # Deployment/config change correlation
│       │       ├── metric_analyzer.py      # Metric anomaly detection + correlation
│       │       ├── similar_incident_finder.py  # JIRA/Confluence search for past incidents
│       │       ├── postmortem_writer.py    # Structured post-mortem generation
│       │       └── runbook_executor.py     # Step-by-step runbook guidance
│       ├── context/
│       │   ├── manager.py            # Context profile CRUD (SQLite)
│       │   └── loader.py             # Context loading + MCP server startup
│       ├── db/
│       │   ├── database.py           # aiosqlite connection (WAL mode)
│       │   └── migrations.py         # Schema creation (all tables)
│       ├── llm/
│       │   └── provider.py           # LLM provider factory (anthropic/bedrock)
│       └── mcp/
│           ├── __init__.py
│           ├── client.py             # MCPManager + MCPServerInstance (Docker stdio)
│           └── manager.py            # MCP server DB CRUD + context linking
└── data/                             # SQLite database volume mount
    └── app.db                        # Auto-created on first run
```

## 8. Deployment (Docker Compose)

```yaml
services:
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [backend]

  backend:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      - LLM_PROVIDER=${LLM_PROVIDER:-anthropic}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - MODEL_ID=${MODEL_ID:-claude-sonnet-4-20250514}
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_PROFILE=${AWS_PROFILE}
      - AWS_REGION=${AWS_REGION:-us-east-1}
      - DATABASE_PATH=/app/data/app.db
    volumes:
      - ./data:/app/data                          # Persistent SQLite storage
      - ${HOME}/.aws:/root/.aws:ro                # AWS credentials (for Bedrock)
      - /var/run/docker.sock:/var/run/docker.sock # Required to spawn MCP containers
```

**Note:** The backend container needs `docker-ce-cli` installed (done in Dockerfile) to spawn MCP server containers via the mounted Docker socket. This is a Docker-in-Docker pattern where the backend orchestrates sibling containers.

## 9. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Tool-use loop (not sub-agents) | Single LLM decides tool routing — simpler, fewer hops, Claude handles orchestration natively via tool_use |
| LangGraph StateGraph | Clean loop semantics (orchestrator → tools → orchestrator), built-in state management |
| Dynamic MCP via UI | No hardcoded connectors — teams register their own MCP servers with credentials, reusable across contexts |
| MCP servers as first-class entities | Decoupled from context profiles via join table — one MCP server can serve many contexts |
| Docker-spawned MCP servers | Standard MCP stdio transport, isolated environments, no dependency installation in backend |
| SQLite with aiosqlite | Zero-config, async, WAL mode for concurrent reads, sufficient for single-node |
| Context-first UX | Forces users to define system context before chat, ensuring agent has domain knowledge from first interaction |
| System prompt injection | Context profile content becomes system prompt — simpler than dynamic agent topology |
| Dual LLM provider (Anthropic/Bedrock) | Flexibility for dev (direct API) vs enterprise (Bedrock with IAM/profiles) |
| SSE streaming | Real-time token delivery during tool-use loops (stream text, pause for tools, resume) |
| UV package manager | Fast, reliable Python dependency resolution |
| Docker Compose | Single-command deployment, consistent environments |

## 10. Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `LLM_PROVIDER` | Yes | `anthropic` or `bedrock` |
| `ANTHROPIC_API_KEY` | If provider=anthropic | Anthropic API key |
| `MODEL_ID` | Yes | Model identifier (format depends on provider) |
| `AWS_ACCESS_KEY_ID` | If provider=bedrock (no profile) | AWS IAM access key |
| `AWS_SECRET_ACCESS_KEY` | If provider=bedrock (no profile) | AWS IAM secret key |
| `AWS_PROFILE` | If provider=bedrock (profile-based) | AWS credentials profile name |
| `AWS_REGION` | If provider=bedrock | AWS region (default: us-east-1) |
| `DATABASE_PATH` | No | SQLite path (default: `data/app.db`) |

## 11. Non-Functional Requirements

- **Latency**: First token response within 3 seconds for streaming
- **Concurrency**: Support multiple simultaneous chat sessions
- **Extensibility**: New MCP servers addable via UI without code changes
- **Tool scale**: Handles MCP servers with 70+ tools (10MB buffer for tool lists)
- **Observability**: Structured logging, request tracing
- **Safety**: Max 10 tool-use iterations per message to prevent infinite loops

## 12. Future Considerations

- WebSocket support for real-time bidirectional communication
- PostgreSQL migration for multi-node / high-concurrency deployments
- Authentication/authorization (OAuth2/SSO)
- Multi-tenant support with per-tenant context isolation
- Automated incident detection (push-based triggers)
- Integration with PagerDuty, Slack, and other alerting tools
- Context profile import/export (share profiles across teams)
- Dynamic sub-agent registration (specialized analysis pipelines per context)
- Knowledge source ingestion (load runbooks/docs into retrieval-augmented context)
- MCP server health monitoring and auto-restart

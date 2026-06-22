# Agentic Incident Intelligence Platform - Specification

## 1. Overview

An AI-powered production debugging and root cause analysis platform that accelerates incident triage, reduces MTTR, and minimizes manual investigation effort. The system acts as an intelligent first-line diagnostic agent for production systems.

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Docker Compose                            │
│                                                                 │
│  ┌──────────────┐       REST API        ┌────────────────────┐ │
│  │   Frontend   │ ◄──────────────────► │    Backend Agent    │ │
│  │  (React JS)  │                       │  (LangGraph + UV)  │ │
│  │  Port: 3000  │                       │   Port: 8000       │ │
│  └──────────────┘                       └────────┬───────────┘ │
│                                                  │              │
│                                    ┌─────────────┼────────────┐│
│                                    │             │             ││
│                                    ▼             ▼             ▼│
│                              ┌──────────┐ ┌──────────┐ ┌──────┐│
│                              │   MCP    │ │  Claude  │ │Bedrock││
│                              │(JIRA/CDET)│ │  API    │ │  API ││
│                              └──────────┘ └──────────┘ └──────┘│
└─────────────────────────────────────────────────────────────────┘
```

## 3. Components

### 3.1 Frontend (React JS)

- **Framework**: React JS with Vite
- **Core UI**: Chat interface for user interaction
- **Features**:
  - Conversational chat box for prompt input
  - Streaming response display (markdown rendered)
  - Incident context panel (logs, metrics, traces)
  - Session history sidebar
  - Context configuration UI (upload/edit runtime context)
- **Communication**: REST API calls to backend server
- **Port**: 3000

### 3.2 Backend Agent (LangGraph + Python)

- **Package Manager**: UV
- **Framework**: LangGraph SDK (Python)
- **Server**: FastAPI-based HTTP server
- **Port**: 8000

#### 3.2.1 Agent Architecture

```
┌───────────────────────────────────────────────┐
│              Orchestrator Agent                │
│  (Routes tasks, manages state, coordinates)   │
└──────────┬──────────┬──────────┬──────────────┘
           │          │          │
     ┌─────▼───┐ ┌───▼────┐ ┌──▼──────────┐
     │Analysis │ │Validate│ │Tool Call     │
     │Sub-Agent│ │Sub-Agt │ │Sub-Agent     │
     └─────────┘ └────────┘ └─────────────┘
           │          │          │
     ┌─────▼───┐ ┌───▼────┐ ┌──▼──────────┐
     │Response │ │Context │ │  ...more     │
     │Sub-Agent│ │Sub-Agt │ │ (dynamic)    │
     └─────────┘ └────────┘ └─────────────┘
```

- **Orchestrator Agent**: Central coordinator that routes user queries to appropriate sub-agents, manages conversation state, and assembles final responses.
- **Analysis Sub-Agent**: Performs log analysis, error trace correlation, anomaly detection, and pattern matching against historical data.
- **Validation Sub-Agent**: Validates hypotheses, cross-references findings, and checks consistency of root cause conclusions.
- **Tool Call Sub-Agent**: Interfaces with external tools via MCP (JIRA/CDET lookups, metric queries, log retrieval).
- **Response Sub-Agent**: Formats and structures the final output with actionable insights, severity assessment, and recommended next steps.
- **Context Sub-Agent**: Manages runtime context injection, retrieves relevant business-specific context for the current investigation.
- **Dynamic Sub-Agents**: Additional sub-agents can be registered at runtime based on user-configured context.

#### 3.2.2 LLM Provider Support

The backend supports dual invocation modes:

| Mode | Config | Use Case |
|------|--------|----------|
| **API Key** | `ANTHROPIC_API_KEY` | Direct Claude API calls |
| **AWS Bedrock** | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` | Enterprise deployments via Bedrock |

Provider selection is configured via environment variable `LLM_PROVIDER=anthropic|bedrock`.
use anthropic library to invoke the model
the model nam or id should be coming from the env variable

### 3.3 Model Context Protocol (MCP) Integration

- **JIRA/CDET Connector**: Query historical bugs, CFDs, resolutions
- **Extensible**: Additional MCP servers can be plugged in at runtime
- **Capabilities**:
  - Fetch issue details, comments, and resolution history
  - Search for similar past incidents
  - Enrich tickets with diagnostic information
  - Attach root cause findings and recommendations

## 4. Context Memory Layer (SQLite)

A core design principle: context is programmable at runtime so any team can plug in their business-specific debugging context. All context profiles are persisted in a SQLite database, providing durable storage without external infrastructure dependencies.

### 4.1 SQLite Schema

```sql
-- Context profiles: the core business context definitions
CREATE TABLE context_profiles (
    id TEXT PRIMARY KEY,              -- UUID
    name TEXT UNIQUE NOT NULL,        -- User-defined unique name (e.g., "payment-service")
    description TEXT,
    system_prompt TEXT NOT NULL,      -- The business context injected as system prompt
    knowledge_sources JSON,           -- Array of knowledge source references
    tool_configs JSON,                -- MCP tool configurations for this context
    severity_rules JSON,             -- Custom severity classification rules
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chat sessions: each session is bound to a context profile
CREATE TABLE chat_sessions (
    id TEXT PRIMARY KEY,              -- UUID
    context_profile_id TEXT NOT NULL, -- FK to context_profiles
    title TEXT,                       -- Auto-generated or user-provided title
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (context_profile_id) REFERENCES context_profiles(id)
);

-- Chat messages: conversation history per session
CREATE TABLE chat_messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,               -- 'user' | 'assistant'
    content TEXT NOT NULL,
    metadata JSON,                    -- Root cause, confidence, etc.
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
  "tool_configs": [
    {"type": "mcp", "server": "jira", "project": "PAY"}
  ],
  "severity_rules": {
    "critical": ["payment_failure", "data_loss"],
    "high": ["latency_spike", "error_rate_increase"]
  }
}
```

### 4.3 Context Loading Flow

```
User selects/switches context profile
        │
        ▼
Backend loads context_profile from SQLite by ID
        │
        ▼
system_prompt field is injected into the LLM invocation
as a system message prefix for ALL messages in that session
        │
        ▼
knowledge_sources are loaded and appended to system context
        │
        ▼
tool_configs activate relevant MCP connectors for this session
```

On every chat message within a session:
1. Resolve `session.context_profile_id` → load the profile from DB
2. Construct system prompt: `base_system_prompt + profile.system_prompt + knowledge_sources`
3. Invoke the orchestrator agent with this assembled context

### 4.4 Context API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/context` | GET | List all available context profiles |
| `/api/context` | POST | Create a new context profile |
| `/api/context/{id}` | GET | Get a single context profile |
| `/api/context/{id}` | PUT | Update an existing context profile |
| `/api/context/{id}` | DELETE | Remove a context profile |
| `/api/context/{id}/activate` | POST | Set active context for current session |

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
│   │  [+ Add Knowledge Source]                     │     │
│   │  [+ Add Tool Configuration]                   │     │
│   │                                               │     │
│   │           [ Create Context ]                  │     │
│   └───────────────────────────────────────────────┘     │
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
│ │    Session 2 │  │  Chat messages...                       │   │
│ │    Session 3 │  │                                         │   │
│ │              │  │                                         │   │
│ │              │  │                                         │   │
│ │  ──────────  │  │  ┌───────────────────────────────────┐  │   │
│ │  [+ New]     │  │  │ Type your message...              │  │   │
│ │  [⚙ Manage]  │  │  └───────────────────────────────────┘  │   │
│ └──────────────┘  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 Context Switching Behavior

- The context dropdown in the header allows switching between profiles
- Switching context **starts a new chat session** bound to the selected profile
- Previous sessions remain accessible in the sidebar (grouped by context)
- The agent re-loads the new profile's system prompt for subsequent messages
- A "Manage Contexts" page allows CRUD operations on all profiles

### 5.4 Frontend Pages/Routes

| Route | Page | Description |
|-------|------|-------------|
| `/` | Context Setup / Chat | Shows setup wizard if no contexts exist; otherwise shows chat |
| `/contexts` | Context Management | List, create, edit, delete context profiles |
| `/contexts/new` | Create Context | Form to create a new context profile |
| `/contexts/:id/edit` | Edit Context | Form to edit an existing context profile |
| `/chat` | Chat Interface | Main chat UI with context switcher and session sidebar |
| `/chat/:sessionId` | Chat Session | Specific chat session view |

## 6. REST API Specification

### 6.1 Chat Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Send a message, get agent response |
| `/api/chat/stream` | POST | Send a message, get streaming response (SSE) |
| `/api/chat/sessions` | GET | List chat sessions |
| `/api/chat/sessions/{id}` | GET | Get session history |
| `/api/chat/sessions/{id}` | DELETE | Delete a session |

### 6.2 Agent Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agent/status` | GET | Health check and agent status |
| `/api/agent/config` | GET/PUT | View/update agent configuration |

### 6.3 Request/Response Format

**Chat Request:**
```json
{
  "message": "Why is the payment service returning 500 errors?",
  "session_id": "optional-session-uuid",
  "context_id": "payment-service",
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
    "affected_components": ["payment-db", "payment-api"],
    "related_incidents": ["JIRA-1234", "JIRA-5678"],
    "recommended_actions": [
      "Increase connection pool size",
      "Restart payment-db pods"
    ]
  }
}
```

## 7. Project Structure

```
agentic-incident-intelligence/
├── spec.md
├── docker-compose.yml
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── ChatBox.tsx
│   │   │   ├── MessageList.tsx
│   │   │   ├── ContextPanel.tsx
│   │   │   ├── ContextSwitcher.tsx
│   │   │   ├── ContextForm.tsx
│   │   │   └── SessionSidebar.tsx
│   │   ├── pages/
│   │   │   ├── ChatPage.tsx
│   │   │   ├── ContextSetupPage.tsx
│   │   │   └── ContextManagePage.tsx
│   │   ├── services/
│   │   │   └── api.ts
│   │   └── types/
│   │       └── index.ts
│   └── public/
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── src/
│   │   ├── main.py                  # FastAPI server entry
│   │   ├── config.py                # Configuration management
│   │   ├── api/
│   │   │   ├── routes.py            # REST API routes
│   │   │   └── models.py            # Pydantic request/response models
│   │   ├── agent/
│   │   │   ├── orchestrator.py      # Main orchestrator agent
│   │   │   ├── graph.py             # LangGraph state graph definition
│   │   │   ├── state.py             # Agent state schema
│   │   │   └── sub_agents/
│   │   │       ├── analysis.py
│   │   │       ├── validation.py
│   │   │       ├── tool_call.py
│   │   │       ├── response.py
│   │   │       └── context.py
│   │   ├── context/
│   │   │   ├── manager.py           # Context profile CRUD operations
│   │   │   └── loader.py            # Context loading into agent prompts
│   │   ├── db/
│   │   │   ├── database.py          # SQLite connection and initialization
│   │   │   ├── models.py            # SQLAlchemy/dataclass models
│   │   │   └── migrations.py        # Schema creation and migrations
│   │   ├── llm/
│   │   │   ├── provider.py          # LLM provider factory
│   │   │   ├── anthropic.py         # Direct Anthropic API client
│   │   │   └── bedrock.py           # AWS Bedrock client
│   │   └── mcp/
│   │       ├── client.py            # MCP client interface
│   │       └── connectors/
│   │           └── jira.py          # JIRA/CDET connector
│   └── tests/
│       ├── test_api.py
│       ├── test_agent.py
│       ├── test_context.py
│       └── test_db.py
└── data/                             # SQLite database volume mount
    └── app.db                        # Auto-created on first run
```

## 8. Deployment (Docker Compose)

```yaml
# docker-compose.yml structure
services:
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [backend]
    environment:
      - VITE_API_URL=http://backend:8000

  backend:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      - LLM_PROVIDER=anthropic
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_REGION=${AWS_REGION}
      - DATABASE_PATH=/app/data/app.db
    volumes:
      - ./data:/app/data          # Persistent SQLite storage
```

## 9. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| LangGraph for orchestration | Built-in state management, conditional routing, human-in-the-loop support |
| UV as package manager | Fast, reliable Python dependency resolution |
| FastAPI for server | Async support, auto-generated OpenAPI docs, SSE streaming |
| MCP for tool integration | Standard protocol for LLM-tool interaction, extensible |
| SQLite for persistence | Zero-config, file-based, no external DB dependency, sufficient for single-node deployment |
| Context-first UX | Forces users to define system context before chat, ensuring agent has domain knowledge from first interaction |
| Context profiles as system prompt injection | Simpler than dynamic subagents for v1; the orchestrator adapts behavior via prompt, not topology |
| Runtime context injection | Makes platform reusable across teams and services |
| Dual LLM provider support | Flexibility for direct API vs enterprise Bedrock deployments |
| Docker Compose | Single-command deployment, consistent environments |

## 10. Non-Functional Requirements

- **Latency**: First token response within 3 seconds for streaming
- **Concurrency**: Support multiple simultaneous chat sessions
<!-- - **Security**: API key authentication for backend endpoints; secrets via environment variables -->
- **Extensibility**: New sub-agents and MCP connectors addable without core changes
- **Observability**: Structured logging, request tracing

## 11. Dynamic Sub-Agents (Future — v2)

Dynamic sub-agents are **not required for v1**. The context profile system prompt injection is sufficient for the MVP because:

- The orchestrator + fixed sub-agents can serve all context profiles — the profile changes *what the agent knows*, not *how it reasons*
- System prompt injection gives the agent domain-specific knowledge without architectural complexity

**When dynamic sub-agents become useful (v2):**

| Trigger | Example |
|---------|---------|
| Context needs specialized tool chains | "payment-service" context spawns a transaction-flow-analyzer sub-agent with Stripe API tools |
| Context needs different analysis pipelines | "infra" context spawns a k8s-health-check sub-agent that queries cluster state |
| Context needs custom validation logic | "compliance" context spawns a regulatory-check sub-agent |
| User registers custom agent code | Power users upload Python modules that become sub-agents |

**Registration mechanism (future):**
```json
{
  "context_name": "payment-service",
  "dynamic_agents": [
    {
      "name": "stripe-analyzer",
      "trigger": "when user mentions payment failures or refund issues",
      "system_prompt": "You analyze Stripe webhook logs...",
      "tools": ["stripe_api", "transaction_db"]
    }
  ]
}
```

## 12. Future Considerations

- WebSocket support for real-time bidirectional communication
- PostgreSQL migration for multi-node / high-concurrency deployments
- Authentication/authorization (OAuth2/SSO)
- Multi-tenant support with per-tenant context isolation
- Automated incident detection (push-based triggers)
- Integration with PagerDuty, Slack, and other alerting tools
- Context profile import/export (share profiles across teams)
- Dynamic sub-agent registration (see Section 11)

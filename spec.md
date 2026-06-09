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

### 3.3 Model Context Protocol (MCP) Integration

- **JIRA/CDET Connector**: Query historical bugs, CFDs, resolutions
- **Extensible**: Additional MCP servers can be plugged in at runtime
- **Capabilities**:
  - Fetch issue details, comments, and resolution history
  - Search for similar past incidents
  - Enrich tickets with diagnostic information
  - Attach root cause findings and recommendations

## 4. Dynamic Runtime Context

A core design principle: context is programmable at runtime so any team can plug in their business-specific debugging context.

### 4.1 Context Configuration

```json
{
  "context_name": "payment-service",
  "description": "Payment processing microservice context",
  "system_prompt_additions": "You are debugging a payment service...",
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

### 4.2 Context API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/context` | GET | List all available contexts |
| `/api/context` | POST | Create/update a context |
| `/api/context/{id}` | DELETE | Remove a context |
| `/api/context/{id}/activate` | POST | Set active context for session |

## 5. REST API Specification

### 5.1 Chat Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Send a message, get agent response |
| `/api/chat/stream` | POST | Send a message, get streaming response (SSE) |
| `/api/chat/sessions` | GET | List chat sessions |
| `/api/chat/sessions/{id}` | GET | Get session history |
| `/api/chat/sessions/{id}` | DELETE | Delete a session |

### 5.2 Agent Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agent/status` | GET | Health check and agent status |
| `/api/agent/config` | GET/PUT | View/update agent configuration |

### 5.3 Request/Response Format

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

## 6. Project Structure

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
│   │   │   └── SessionSidebar.tsx
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
│   │   │   ├── manager.py           # Runtime context management
│   │   │   └── loader.py            # Context loading/parsing
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
│       └── test_context.py
└── contexts/                         # User-defined context configs
    └── example.json
```

## 7. Deployment (Docker Compose)

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
    volumes:
      - ./contexts:/app/contexts
```

## 8. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| LangGraph for orchestration | Built-in state management, conditional routing, human-in-the-loop support |
| UV as package manager | Fast, reliable Python dependency resolution |
| FastAPI for server | Async support, auto-generated OpenAPI docs, SSE streaming |
| MCP for tool integration | Standard protocol for LLM-tool interaction, extensible |
| Dynamic sub-agents | Allows scaling agent capabilities without code changes |
| Runtime context injection | Makes platform reusable across teams and services |
| Dual LLM provider support | Flexibility for direct API vs enterprise Bedrock deployments |
| Docker Compose | Single-command deployment, consistent environments |

## 9. Non-Functional Requirements

- **Latency**: First token response within 3 seconds for streaming
- **Concurrency**: Support multiple simultaneous chat sessions
- **Security**: API key authentication for backend endpoints; secrets via environment variables
- **Extensibility**: New sub-agents and MCP connectors addable without core changes
- **Observability**: Structured logging, request tracing

## 10. Future Considerations

- WebSocket support for real-time bidirectional communication
- Persistent storage (PostgreSQL) for session history and context configs
- Authentication/authorization (OAuth2/SSO)
- Multi-tenant support
- Automated incident detection (push-based triggers)
- Integration with PagerDuty, Slack, and other alerting tools

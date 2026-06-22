from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ContextProfile:
    id: str
    name: str
    system_prompt: str
    description: str | None = None
    knowledge_sources: list | None = None
    tool_configs: list | None = None
    severity_rules: dict | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ChatSession:
    id: str
    context_profile_id: str
    title: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ChatMessage:
    id: str
    session_id: str
    role: str
    content: str
    metadata: dict | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)

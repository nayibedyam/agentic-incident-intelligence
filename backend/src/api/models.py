from pydantic import BaseModel


class ContextProfileCreate(BaseModel):
    name: str
    description: str | None = None
    system_prompt: str
    knowledge_sources: list | None = None
    severity_rules: dict | None = None


class ContextProfileUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    knowledge_sources: list | None = None
    severity_rules: dict | None = None


class ContextProfileResponse(BaseModel):
    id: str
    name: str
    description: str | None
    system_prompt: str
    knowledge_sources: list | None
    severity_rules: dict | None
    created_at: str
    updated_at: str


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    context_id: str
    attachments: list | None = None


class ChatResponse(BaseModel):
    session_id: str
    message: str
    metadata: dict | None = None


class SessionResponse(BaseModel):
    id: str
    context_profile_id: str
    title: str | None
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    metadata: dict | None
    created_at: str

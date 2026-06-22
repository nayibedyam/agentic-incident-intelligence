import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.api.models import (
    ChatRequest,
    ChatResponse,
    ContextProfileCreate,
    ContextProfileUpdate,
    ContextProfileResponse,
    SessionResponse,
    MessageResponse,
)
from src.context.manager import (
    list_profiles,
    get_profile,
    create_profile,
    update_profile,
    delete_profile,
)
from src.agent.orchestrator import handle_chat, handle_chat_stream
from src.db.database import get_db

router = APIRouter(prefix="/api")


# --- Context Profile Endpoints ---


@router.get("/context", response_model=list[ContextProfileResponse])
async def get_contexts():
    profiles = await list_profiles()
    return profiles


@router.post("/context", response_model=ContextProfileResponse, status_code=201)
async def create_context(data: ContextProfileCreate):
    profile = await create_profile(data.model_dump())
    return profile


@router.get("/context/{profile_id}", response_model=ContextProfileResponse)
async def get_context(profile_id: str):
    profile = await get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Context profile not found")
    return profile


@router.put("/context/{profile_id}", response_model=ContextProfileResponse)
async def update_context(profile_id: str, data: ContextProfileUpdate):
    profile = await update_profile(profile_id, data.model_dump(exclude_unset=True))
    if not profile:
        raise HTTPException(status_code=404, detail="Context profile not found")
    return profile


@router.delete("/context/{profile_id}", status_code=204)
async def delete_context(profile_id: str):
    deleted = await delete_profile(profile_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Context profile not found")


# --- Chat Endpoints ---


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    result = await handle_chat(
        message=request.message,
        session_id=request.session_id,
        context_id=request.context_id,
    )
    return result


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    generator = handle_chat_stream(
        message=request.message,
        session_id=request.session_id,
        context_id=request.context_id,
    )
    return StreamingResponse(generator, media_type="text/event-stream")


@router.get("/chat/sessions", response_model=list[SessionResponse])
async def get_sessions(context_id: str | None = None):
    db = await get_db()
    if context_id:
        cursor = await db.execute(
            "SELECT * FROM chat_sessions WHERE context_profile_id = ? ORDER BY updated_at DESC",
            (context_id,),
        )
    else:
        cursor = await db.execute(
            "SELECT * FROM chat_sessions ORDER BY updated_at DESC"
        )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


@router.get("/chat/sessions/{session_id}", response_model=list[MessageResponse])
async def get_session_messages(session_id: str):
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM chat_messages WHERE session_id = ? ORDER BY created_at",
        (session_id,),
    )
    rows = await cursor.fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail="Session not found")
    results = []
    for row in rows:
        d = dict(row)
        if d.get("metadata") and isinstance(d["metadata"], str):
            d["metadata"] = json.loads(d["metadata"])
        results.append(d)
    return results


@router.delete("/chat/sessions/{session_id}", status_code=204)
async def delete_session(session_id: str):
    db = await get_db()
    await db.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
    await db.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
    await db.commit()


# --- Agent Endpoints ---


@router.get("/agent/status")
async def agent_status():
    return {"status": "healthy", "agent": "orchestrator", "version": "0.1.0"}

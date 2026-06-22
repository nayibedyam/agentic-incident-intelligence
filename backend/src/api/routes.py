import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

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
from src.mcp.manager import (
    list_mcp_servers,
    get_mcp_server,
    create_mcp_server,
    update_mcp_server,
    delete_mcp_server,
    get_linked_servers_for_context,
    get_linked_server_ids_for_context,
    link_server_to_context,
    unlink_server_from_context,
)
from src.mcp.client import mcp_manager
from src.agent.orchestrator import handle_chat, handle_chat_stream
from src.agent.tools import get_available_tools
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


# --- Context <-> MCP Linking ---


@router.get("/context/{profile_id}/mcp-servers")
async def get_context_mcp_servers(profile_id: str):
    servers = await get_linked_servers_for_context(profile_id)
    return servers


@router.post("/context/{profile_id}/mcp-servers/{server_id}", status_code=204)
async def link_mcp_to_context(profile_id: str, server_id: str):
    await link_server_to_context(profile_id, server_id)


@router.delete("/context/{profile_id}/mcp-servers/{server_id}", status_code=204)
async def unlink_mcp_from_context(profile_id: str, server_id: str):
    await unlink_server_from_context(profile_id, server_id)


# --- MCP Server CRUD ---


class MCPServerCreate(BaseModel):
    name: str
    description: str | None = None
    command: str
    args: list[str] = []
    env: dict[str, str] = {}


class MCPServerUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    command: str | None = None
    args: list[str] | None = None
    env: dict[str, str] | None = None


@router.get("/mcp/servers")
async def list_servers():
    servers = await list_mcp_servers()
    for server in servers:
        server["running"] = server["name"] in mcp_manager.running_servers
    return servers


@router.post("/mcp/servers", status_code=201)
async def create_server(data: MCPServerCreate):
    server = await create_mcp_server(data.model_dump())
    server["running"] = False
    return server


@router.get("/mcp/servers/{server_id}")
async def get_server(server_id: str):
    server = await get_mcp_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    server["running"] = server["name"] in mcp_manager.running_servers
    return server


@router.put("/mcp/servers/{server_id}")
async def update_server(server_id: str, data: MCPServerUpdate):
    server = await update_mcp_server(server_id, data.model_dump(exclude_unset=True))
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    server["running"] = server["name"] in mcp_manager.running_servers
    return server


@router.delete("/mcp/servers/{server_id}", status_code=204)
async def delete_server(server_id: str):
    server = await get_mcp_server(server_id)
    if server and server["name"] in mcp_manager.running_servers:
        await mcp_manager.unregister_server(server["name"])
    deleted = await delete_mcp_server(server_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="MCP server not found")


@router.post("/mcp/servers/{server_id}/start")
async def start_server(server_id: str):
    server = await get_mcp_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    try:
        tools = await mcp_manager.register_server(
            name=server["name"],
            command=server["command"],
            args=server.get("args", []),
            env=server.get("env", {}),
        )
        return {"name": server["name"], "tools": [t["name"] for t in tools], "running": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start: {e}")


@router.post("/mcp/servers/{server_id}/stop", status_code=204)
async def stop_server(server_id: str):
    server = await get_mcp_server(server_id)
    if server and server["name"] in mcp_manager.running_servers:
        await mcp_manager.unregister_server(server["name"])


@router.get("/mcp/tools")
async def list_tools():
    return get_available_tools()


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
    return {
        "status": "healthy",
        "agent": "orchestrator",
        "version": "0.1.0",
        "mcp_servers": mcp_manager.running_servers,
        "available_tools": [t["name"] for t in get_available_tools()],
    }

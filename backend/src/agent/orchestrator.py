import json
import uuid
from datetime import datetime

from langchain_core.messages import HumanMessage

from src.agent.graph import agent_graph
from src.context.loader import load_context_for_session
from src.db.database import get_db


async def handle_chat(message: str, session_id: str | None, context_id: str) -> dict:
    db = await get_db()

    if not session_id:
        session_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        await db.execute(
            """INSERT INTO chat_sessions (id, context_profile_id, title, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?)""",
            (session_id, context_id, message[:50], now, now),
        )
        await db.commit()

    msg_id = str(uuid.uuid4())
    await db.execute(
        """INSERT INTO chat_messages (id, session_id, role, content, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (msg_id, session_id, "user", message, datetime.utcnow().isoformat()),
    )
    await db.commit()

    system_prompt = await load_context_for_session(context_id)

    history = await _load_session_messages(session_id)

    state = {
        "messages": history,
        "context_profile_id": context_id,
        "system_prompt": system_prompt,
        "session_id": session_id,
    }

    result = await agent_graph.ainvoke(state)

    assistant_content = result["messages"][-1].content

    resp_id = str(uuid.uuid4())
    await db.execute(
        """INSERT INTO chat_messages (id, session_id, role, content, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (resp_id, session_id, "assistant", assistant_content, datetime.utcnow().isoformat()),
    )
    await db.commit()

    return {
        "session_id": session_id,
        "message": assistant_content,
        "metadata": None,
    }


async def handle_chat_stream(message: str, session_id: str | None, context_id: str):
    db = await get_db()

    if not session_id:
        session_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        await db.execute(
            """INSERT INTO chat_sessions (id, context_profile_id, title, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?)""",
            (session_id, context_id, message[:50], now, now),
        )
        await db.commit()

    msg_id = str(uuid.uuid4())
    await db.execute(
        """INSERT INTO chat_messages (id, session_id, role, content, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (msg_id, session_id, "user", message, datetime.utcnow().isoformat()),
    )
    await db.commit()

    system_prompt = await load_context_for_session(context_id)
    history = await _load_session_messages(session_id)

    from src.llm.provider import get_async_client, get_model_id

    client = get_async_client()
    model_id = get_model_id()

    messages = []
    for msg in history:
        if hasattr(msg, "type"):
            role = msg.type if msg.type != "human" else "user"
            messages.append({"role": role, "content": msg.content})
        elif isinstance(msg, dict):
            role = msg.get("role", "user")
            if role == "human":
                role = "user"
            messages.append({"role": role, "content": msg["content"]})

    full_response = []

    yield f"data: {json.dumps({'type': 'session_id', 'session_id': session_id})}\n\n"

    async with client.messages.stream(
        model=model_id,
        max_tokens=4096,
        system=system_prompt,
        messages=messages,
    ) as stream:
        async for text in stream.text_stream:
            full_response.append(text)
            yield f"data: {json.dumps({'type': 'content', 'content': text})}\n\n"

    assistant_content = "".join(full_response)
    resp_id = str(uuid.uuid4())
    await db.execute(
        """INSERT INTO chat_messages (id, session_id, role, content, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (resp_id, session_id, "assistant", assistant_content, datetime.utcnow().isoformat()),
    )
    await db.commit()

    yield f"data: {json.dumps({'type': 'done'})}\n\n"


async def _load_session_messages(session_id: str) -> list:
    db = await get_db()
    cursor = await db.execute(
        "SELECT role, content FROM chat_messages WHERE session_id = ? ORDER BY created_at",
        (session_id,),
    )
    rows = await cursor.fetchall()
    messages = []
    for row in rows:
        role = dict(row)["role"]
        content = dict(row)["content"]
        if role == "user":
            messages.append(HumanMessage(content=content))
        else:
            from langchain_core.messages import AIMessage
            messages.append(AIMessage(content=content))
    return messages

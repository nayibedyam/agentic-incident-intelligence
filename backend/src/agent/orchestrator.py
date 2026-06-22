import json
import uuid
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage

from src.agent.graph import agent_graph
from src.agent.tools import get_available_tools_async, execute_tool
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
    tools = await get_available_tools_async(context_id)

    messages = _to_anthropic_messages(history)

    yield f"data: {json.dumps({'type': 'session_id', 'session_id': session_id})}\n\n"

    full_response = []
    max_iterations = 10

    for _ in range(max_iterations):
        kwargs = {
            "model": model_id,
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        tool_calls = []
        text_parts = []

        async with client.messages.stream(**kwargs) as stream:
            async for event in stream:
                if event.type == "content_block_start":
                    if event.content_block.type == "tool_use":
                        tool_calls.append({"id": event.content_block.id, "name": event.content_block.name, "input_json": ""})
                elif event.type == "content_block_delta":
                    if event.delta.type == "text_delta":
                        text_parts.append(event.delta.text)
                        full_response.append(event.delta.text)
                        yield f"data: {json.dumps({'type': 'content', 'content': event.delta.text})}\n\n"
                    elif event.delta.type == "input_json_delta":
                        if tool_calls:
                            tool_calls[-1]["input_json"] += event.delta.partial_json

        if not tool_calls:
            break

        yield f"data: {json.dumps({'type': 'tool_use', 'tools': [tc['name'] for tc in tool_calls]})}\n\n"

        assistant_content = []
        text_so_far = "".join(text_parts)
        if text_so_far:
            assistant_content.append({"type": "text", "text": text_so_far})
        for tc in tool_calls:
            tc_input = json.loads(tc["input_json"]) if tc["input_json"] else {}
            assistant_content.append({"type": "tool_use", "id": tc["id"], "name": tc["name"], "input": tc_input})

        messages.append({"role": "assistant", "content": assistant_content})

        tool_results = []
        for tc in tool_calls:
            tc_input = json.loads(tc["input_json"]) if tc["input_json"] else {}
            result = await execute_tool(tc["name"], tc_input)
            tool_results.append({"type": "tool_result", "tool_use_id": tc["id"], "content": result})
        messages.append({"role": "user", "content": tool_results})

        text_parts = []

    assistant_content_text = "".join(full_response)
    resp_id = str(uuid.uuid4())
    await db.execute(
        """INSERT INTO chat_messages (id, session_id, role, content, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (resp_id, session_id, "assistant", assistant_content_text, datetime.utcnow().isoformat()),
    )
    await db.commit()

    yield f"data: {json.dumps({'type': 'done'})}\n\n"


def _to_anthropic_messages(history: list) -> list[dict]:
    messages = []
    for msg in history:
        if hasattr(msg, "type"):
            role = msg.type if msg.type != "human" else "user"
            if role == "ai":
                role = "assistant"
            messages.append({"role": role, "content": msg.content})
        elif isinstance(msg, dict):
            role = msg.get("role", "user")
            if role == "human":
                role = "user"
            messages.append({"role": role, "content": msg["content"]})
    return messages


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
            messages.append(AIMessage(content=content))
    return messages

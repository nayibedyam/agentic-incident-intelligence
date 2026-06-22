import json
import uuid
from datetime import datetime

from src.db.database import get_db


async def list_mcp_servers() -> list[dict]:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM mcp_servers ORDER BY created_at DESC")
    rows = await cursor.fetchall()
    return [_row_to_dict(row) for row in rows]


async def get_mcp_server(server_id: str) -> dict | None:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM mcp_servers WHERE id = ?", (server_id,))
    row = await cursor.fetchone()
    return _row_to_dict(row) if row else None


async def get_mcp_server_by_name(name: str) -> dict | None:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM mcp_servers WHERE name = ?", (name,))
    row = await cursor.fetchone()
    return _row_to_dict(row) if row else None


async def create_mcp_server(data: dict) -> dict:
    db = await get_db()
    server_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    await db.execute(
        """INSERT INTO mcp_servers (id, name, description, command, args, env, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            server_id,
            data["name"],
            data.get("description"),
            data["command"],
            json.dumps(data.get("args", [])),
            json.dumps(data.get("env", {})),
            now,
            now,
        ),
    )
    await db.commit()
    return await get_mcp_server(server_id)


async def update_mcp_server(server_id: str, data: dict) -> dict | None:
    existing = await get_mcp_server(server_id)
    if not existing:
        return None

    db = await get_db()
    now = datetime.utcnow().isoformat()
    fields = []
    values = []
    for key in ["name", "description", "command"]:
        if key in data and data[key] is not None:
            fields.append(f"{key} = ?")
            values.append(data[key])
    for key in ["args", "env"]:
        if key in data and data[key] is not None:
            fields.append(f"{key} = ?")
            values.append(json.dumps(data[key]))

    if fields:
        fields.append("updated_at = ?")
        values.append(now)
        values.append(server_id)
        await db.execute(
            f"UPDATE mcp_servers SET {', '.join(fields)} WHERE id = ?",
            values,
        )
        await db.commit()
    return await get_mcp_server(server_id)


async def delete_mcp_server(server_id: str) -> bool:
    db = await get_db()
    cursor = await db.execute("DELETE FROM mcp_servers WHERE id = ?", (server_id,))
    await db.commit()
    return cursor.rowcount > 0


async def get_linked_servers_for_context(context_profile_id: str) -> list[dict]:
    db = await get_db()
    cursor = await db.execute(
        """SELECT ms.* FROM mcp_servers ms
           JOIN context_mcp_links cml ON ms.id = cml.mcp_server_id
           WHERE cml.context_profile_id = ?""",
        (context_profile_id,),
    )
    rows = await cursor.fetchall()
    return [_row_to_dict(row) for row in rows]


async def link_server_to_context(context_profile_id: str, mcp_server_id: str):
    db = await get_db()
    await db.execute(
        "INSERT OR IGNORE INTO context_mcp_links (context_profile_id, mcp_server_id) VALUES (?, ?)",
        (context_profile_id, mcp_server_id),
    )
    await db.commit()


async def unlink_server_from_context(context_profile_id: str, mcp_server_id: str):
    db = await get_db()
    await db.execute(
        "DELETE FROM context_mcp_links WHERE context_profile_id = ? AND mcp_server_id = ?",
        (context_profile_id, mcp_server_id),
    )
    await db.commit()


async def get_linked_server_ids_for_context(context_profile_id: str) -> list[str]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT mcp_server_id FROM context_mcp_links WHERE context_profile_id = ?",
        (context_profile_id,),
    )
    rows = await cursor.fetchall()
    return [dict(row)["mcp_server_id"] for row in rows]


def _row_to_dict(row) -> dict:
    d = dict(row)
    for key in ["args", "env"]:
        if d.get(key) and isinstance(d[key], str):
            d[key] = json.loads(d[key])
    return d

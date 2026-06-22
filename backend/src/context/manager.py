import json
import uuid
from datetime import datetime

from src.db.database import get_db


async def list_profiles() -> list[dict]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM context_profiles ORDER BY created_at DESC"
    )
    rows = await cursor.fetchall()
    return [_row_to_dict(row) for row in rows]


async def get_profile(profile_id: str) -> dict | None:
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM context_profiles WHERE id = ?", (profile_id,)
    )
    row = await cursor.fetchone()
    return _row_to_dict(row) if row else None


async def get_profile_by_name(name: str) -> dict | None:
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM context_profiles WHERE name = ?", (name,)
    )
    row = await cursor.fetchone()
    return _row_to_dict(row) if row else None


async def create_profile(data: dict) -> dict:
    db = await get_db()
    profile_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    await db.execute(
        """INSERT INTO context_profiles (id, name, description, system_prompt,
           knowledge_sources, tool_configs, severity_rules, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            profile_id,
            data["name"],
            data.get("description"),
            data["system_prompt"],
            json.dumps(data.get("knowledge_sources")),
            json.dumps(data.get("tool_configs")),
            json.dumps(data.get("severity_rules")),
            now,
            now,
        ),
    )
    await db.commit()
    return await get_profile(profile_id)


async def update_profile(profile_id: str, data: dict) -> dict | None:
    existing = await get_profile(profile_id)
    if not existing:
        return None

    db = await get_db()
    now = datetime.utcnow().isoformat()
    fields = []
    values = []
    for key in ["name", "description", "system_prompt"]:
        if key in data and data[key] is not None:
            fields.append(f"{key} = ?")
            values.append(data[key])
    for key in ["knowledge_sources", "tool_configs", "severity_rules"]:
        if key in data and data[key] is not None:
            fields.append(f"{key} = ?")
            values.append(json.dumps(data[key]))

    if fields:
        fields.append("updated_at = ?")
        values.append(now)
        values.append(profile_id)
        await db.execute(
            f"UPDATE context_profiles SET {', '.join(fields)} WHERE id = ?",
            values,
        )
        await db.commit()
    return await get_profile(profile_id)


async def delete_profile(profile_id: str) -> bool:
    db = await get_db()
    cursor = await db.execute(
        "DELETE FROM context_profiles WHERE id = ?", (profile_id,)
    )
    await db.commit()
    return cursor.rowcount > 0


def _row_to_dict(row) -> dict:
    d = dict(row)
    for key in ["knowledge_sources", "tool_configs", "severity_rules"]:
        if d.get(key) and isinstance(d[key], str):
            d[key] = json.loads(d[key])
    return d

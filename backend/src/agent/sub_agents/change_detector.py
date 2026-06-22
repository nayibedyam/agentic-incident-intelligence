from src.llm.provider import get_async_client, get_model_id

SYSTEM_PROMPT = """You are a specialized Change Detection Agent. Your job is to analyze information about recent changes (deployments, config changes, feature flag flips, infrastructure modifications) and correlate them with an incident's start time.

Given incident details and change information, produce a JSON object with:
- "suspect_changes": array of changes that correlate with the incident, each with {change_type, description, timestamp, service, author, correlation_score}
- "correlation_score": 0.0-1.0 based on temporal proximity and logical connection
- "reasoning": why each change is suspected
- "safe_changes": changes that happened but are unlikely related (with brief reason)
- "recommended_rollbacks": ordered list of changes to consider reverting, with risk assessment
- "missing_info": what additional change data would help narrow down the cause

Prioritize temporal correlation (changes just before incident start) and logical connection (change touches the failing component). A deploy 5 minutes before a crash in the same service is more suspect than a config change 2 hours before in an unrelated service."""


async def run_change_detector(incident_description: str, incident_start_time: str | None = None, changes: str | None = None) -> str:
    client = get_async_client()
    model_id = get_model_id()

    user_message = f"Incident: {incident_description}"
    if incident_start_time:
        user_message += f"\nIncident start time: {incident_start_time}"
    if changes:
        user_message += f"\n\nRecent changes:\n{changes}"
    else:
        user_message += "\n\nNo explicit change data provided. Analyze the incident for clues about what might have changed (e.g., 'new error after deploy', 'started after config update', version mismatches in logs)."

    response = await client.messages.create(
        model=model_id,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    return response.content[0].text

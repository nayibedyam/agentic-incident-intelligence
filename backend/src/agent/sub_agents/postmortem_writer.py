from src.llm.provider import get_async_client, get_model_id

SYSTEM_PROMPT = """You are a specialized Post-Mortem Writer Agent. Your job is to produce a structured, blameless post-mortem document from incident investigation data.

Generate a post-mortem in the following format (as a JSON object):

{
  "title": "Post-Mortem: <concise incident title>",
  "severity": "P1/P2/P3/P4",
  "duration": "start_time to end_time (duration)",
  "impact": {
    "users_affected": "description of user impact",
    "services_affected": ["list", "of", "services"],
    "revenue_impact": "estimated if available, otherwise 'Unknown'"
  },
  "timeline": [
    {"time": "HH:MM", "event": "what happened", "actor": "who/what"}
  ],
  "root_cause": {
    "summary": "1-2 sentence root cause",
    "technical_detail": "deeper technical explanation",
    "contributing_factors": ["factor1", "factor2"]
  },
  "detection": {
    "how_detected": "how the incident was noticed",
    "time_to_detect": "duration from start to detection",
    "gaps": "what monitoring should have caught it sooner"
  },
  "resolution": {
    "immediate_fix": "what stopped the bleeding",
    "permanent_fix": "what prevents recurrence",
    "rollback_needed": true/false
  },
  "action_items": [
    {"priority": "P1/P2", "owner": "team/person", "action": "what to do", "due": "when"}
  ],
  "lessons_learned": ["lesson1", "lesson2"],
  "what_went_well": ["thing1", "thing2"],
  "what_went_poorly": ["thing1", "thing2"]
}

Be blameless — focus on systems and processes, not individuals. Be specific and actionable in action items. Include detection gaps and monitoring improvements."""


async def run_postmortem_writer(conversation_context: str, incident_summary: str | None = None) -> str:
    client = get_async_client()
    model_id = get_model_id()

    user_message = "Generate a post-mortem document from this incident investigation:\n\n"
    if incident_summary:
        user_message += f"Summary: {incident_summary}\n\n"
    user_message += f"Investigation details:\n{conversation_context}"

    response = await client.messages.create(
        model=model_id,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    return response.content[0].text

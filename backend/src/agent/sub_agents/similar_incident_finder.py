import json

from src.llm.provider import get_async_client, get_model_id
from src.mcp.client import mcp_manager

SYSTEM_PROMPT = """You are a specialized Similar Incident Finder Agent. Your job is to search for past incidents that have matching symptoms, affected components, or error patterns.

You will be given the current incident details and search results from JIRA/Confluence. Analyze them and produce a JSON object with:
- "similar_incidents": array of past incidents, each with {id, title, similarity_score, matching_symptoms, resolution, time_to_resolve, key_differences}
  - similarity_score: 0.0-1.0 based on symptom match
- "patterns": recurring patterns across similar incidents (e.g., "this service fails every time we deploy on Fridays")
- "applicable_resolutions": resolutions from past incidents that might apply now, ranked by relevance
- "escalation_contacts": people who resolved similar incidents before
- "preventive_gaps": what was supposed to prevent recurrence but didn't

Focus on actionable similarity — a past incident is only useful if its resolution or investigation path can help NOW."""

SEARCH_PROMPT = """Based on this incident description, generate search queries to find similar past incidents.

Incident: {incident}

Generate 2-3 JQL/search queries that would find related issues. Consider:
- Error messages or error codes mentioned
- Service/component names
- Symptom keywords (timeout, 500, connection refused, OOM, etc.)
- Affected functionality

Return ONLY a JSON array of search query strings, nothing else."""


async def run_similar_incident_finder(incident_description: str, symptoms: list[str] | None = None) -> str:
    client = get_async_client()
    model_id = get_model_id()

    search_context = ""
    mcp_tools = mcp_manager.get_all_tool_names()
    has_jira = any("jira_search" in t for t in mcp_tools)

    if has_jira:
        query_response = await client.messages.create(
            model=model_id,
            max_tokens=1024,
            system="You generate JQL search queries. Return only a JSON array of query strings.",
            messages=[{"role": "user", "content": SEARCH_PROMPT.format(incident=incident_description)}],
        )

        try:
            queries = json.loads(query_response.content[0].text)
        except (json.JSONDecodeError, IndexError):
            queries = [incident_description[:100]]

        search_results = []
        for query in queries[:3]:
            try:
                result = await mcp_manager.call_tool("jira_search", {"jql": query, "limit": 5})
                search_results.append(result)
            except Exception:
                try:
                    result = await mcp_manager.call_tool("jira_search", {"query": query, "limit": 5})
                    search_results.append(result)
                except Exception:
                    pass

        if search_results:
            search_context = f"\n\nSearch results from JIRA:\n{'---'.join(search_results)}"

    user_message = f"Current incident: {incident_description}"
    if symptoms:
        user_message += f"\nSymptoms: {', '.join(symptoms)}"
    user_message += search_context

    response = await client.messages.create(
        model=model_id,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    return response.content[0].text

import logging

from src.context.manager import get_profile
from src.mcp.client import mcp_manager
from src.mcp.manager import get_linked_servers_for_context

logger = logging.getLogger(__name__)

BASE_SYSTEM_PROMPT = """You are an AI-powered incident intelligence agent specializing in production debugging and root cause analysis. You help engineers diagnose issues, correlate signals across logs/metrics/traces, and identify root causes with high confidence.

You provide:
- Structured root cause analysis with confidence scores
- Severity assessment based on impact
- Actionable remediation steps
- References to related historical incidents when available

You have access to tools that you should use proactively:
- Use JIRA/Confluence tools to search for related incidents and historical context
- Use analyze_logs when presented with log data
- Use validate_hypothesis to cross-check your conclusions

Be precise, technical, and actionable. Avoid speculation — clearly distinguish confirmed findings from hypotheses."""


async def load_context_for_session(context_profile_id: str) -> str:
    profile = await get_profile(context_profile_id)
    if not profile:
        return BASE_SYSTEM_PROMPT

    parts = [BASE_SYSTEM_PROMPT]

    if profile.get("system_prompt"):
        parts.append(f"\n\n## Service Context\n\n{profile['system_prompt']}")

    if profile.get("severity_rules"):
        rules = profile["severity_rules"]
        rules_text = "\n\n## Severity Classification Rules\n\n"
        for level, keywords in rules.items():
            rules_text += f"- **{level}**: {', '.join(keywords)}\n"
        parts.append(rules_text)

    # Start MCP servers linked to this context profile
    linked_servers = await get_linked_servers_for_context(context_profile_id)
    if linked_servers:
        for server_config in linked_servers:
            server_name = server_config["name"]
            if server_name not in mcp_manager.running_servers:
                try:
                    await mcp_manager.register_server(
                        name=server_name,
                        command=server_config["command"],
                        args=server_config.get("args", []),
                        env=server_config.get("env", {}),
                    )
                except Exception as e:
                    logger.error("Failed to start MCP server '%s': %s", server_name, e)

        running = mcp_manager.running_servers
        if running:
            parts.append(f"\n\n## Connected Tools\n\nMCP servers active: {', '.join(running)}")

    return "".join(parts)

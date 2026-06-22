from src.context.manager import get_profile

BASE_SYSTEM_PROMPT = """You are an AI-powered incident intelligence agent specializing in production debugging and root cause analysis. You help engineers diagnose issues, correlate signals across logs/metrics/traces, and identify root causes with high confidence.

You provide:
- Structured root cause analysis with confidence scores
- Severity assessment based on impact
- Actionable remediation steps
- References to related historical incidents when available

Be precise, technical, and actionable. Avoid speculation — clearly distinguish confirmed findings from hypotheses."""


async def load_context_for_session(context_profile_id: str) -> str:
    profile = await get_profile(context_profile_id)
    if not profile:
        return BASE_SYSTEM_PROMPT

    parts = [BASE_SYSTEM_PROMPT]

    if profile.get("system_prompt"):
        parts.append(
            f"\n\n## Service Context\n\n{profile['system_prompt']}"
        )

    if profile.get("severity_rules"):
        rules = profile["severity_rules"]
        rules_text = "\n\n## Severity Classification Rules\n\n"
        for level, keywords in rules.items():
            rules_text += f"- **{level}**: {', '.join(keywords)}\n"
        parts.append(rules_text)

    return "".join(parts)

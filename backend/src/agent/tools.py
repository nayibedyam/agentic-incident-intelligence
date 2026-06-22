import json

from src.mcp.client import mcp_manager

BUILT_IN_TOOLS = [
    {
        "name": "analyze_logs",
        "description": "Analyze provided log snippets for error patterns, anomalies, and correlations. Use this when the user provides log content and you need structured analysis.",
        "input_schema": {
            "type": "object",
            "properties": {
                "logs": {
                    "type": "string",
                    "description": "The raw log content to analyze",
                },
                "focus": {
                    "type": "string",
                    "description": "What to focus on: 'errors', 'latency', 'patterns', 'timeline', or 'all'",
                    "enum": ["errors", "latency", "patterns", "timeline", "all"],
                },
            },
            "required": ["logs"],
        },
    },
    {
        "name": "validate_hypothesis",
        "description": "Cross-reference a root cause hypothesis against available evidence. Use this after forming an initial hypothesis to check its consistency.",
        "input_schema": {
            "type": "object",
            "properties": {
                "hypothesis": {
                    "type": "string",
                    "description": "The root cause hypothesis to validate",
                },
                "evidence": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of evidence points to check against",
                },
            },
            "required": ["hypothesis", "evidence"],
        },
    },
]


def get_available_tools() -> list[dict]:
    tools = list(BUILT_IN_TOOLS)
    tools.extend(mcp_manager.get_all_tools())
    return tools


async def execute_tool(tool_name: str, tool_input: dict) -> str:
    try:
        if tool_name == "analyze_logs":
            return json.dumps({
                "tool": "analyze_logs",
                "note": "Log analysis is performed inline by the LLM. This confirms structured analysis intent.",
                "logs_length": len(tool_input.get("logs", "")),
                "focus": tool_input.get("focus", "all"),
            })

        elif tool_name == "validate_hypothesis":
            return json.dumps({
                "tool": "validate_hypothesis",
                "note": "Hypothesis validation is performed inline by the LLM reasoning.",
                "hypothesis": tool_input["hypothesis"],
                "evidence_count": len(tool_input.get("evidence", [])),
            })

        else:
            result = await mcp_manager.call_tool(tool_name, tool_input)
            return result if isinstance(result, str) else json.dumps(result)

    except Exception as e:
        return json.dumps({"error": str(e)})

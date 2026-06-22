import json

from src.mcp.client import mcp_manager
from src.mcp.manager import get_linked_servers_for_context

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
    {
        "name": "correlate_logs",
        "description": "Deep log correlation sub-agent. Parses multi-service logs, builds a causal timeline, correlates entries across services by request-id/trace-id/timestamp, and identifies the root signal. Use when the user provides logs from multiple services or you need to trace a request across a distributed system.",
        "input_schema": {
            "type": "object",
            "properties": {
                "logs": {
                    "type": "string",
                    "description": "Raw log content from one or more services",
                },
                "services": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Names of services involved (optional, will be inferred if not provided)",
                },
                "time_range": {
                    "type": "string",
                    "description": "Time range of interest (e.g., '14:00-14:30 UTC')",
                },
            },
            "required": ["logs"],
        },
    },
    {
        "name": "detect_changes",
        "description": "Change detection sub-agent. Analyzes recent changes (deployments, config changes, feature flags) and correlates them with incident timing. Use when investigating what changed to cause an issue.",
        "input_schema": {
            "type": "object",
            "properties": {
                "incident_description": {
                    "type": "string",
                    "description": "Description of the incident and its symptoms",
                },
                "incident_start_time": {
                    "type": "string",
                    "description": "When the incident started (ISO timestamp or relative)",
                },
                "changes": {
                    "type": "string",
                    "description": "Known recent changes (deployments, config changes, PRs merged, etc.)",
                },
            },
            "required": ["incident_description"],
        },
    },
    {
        "name": "analyze_metrics",
        "description": "Metric analysis sub-agent. Detects anomalies in system metrics (latency, error rates, CPU, memory, etc.), finds correlations between metrics, and identifies leading indicators. Use when the user provides metric data or describes performance issues.",
        "input_schema": {
            "type": "object",
            "properties": {
                "metrics_data": {
                    "type": "string",
                    "description": "Metric data (time series, dashboard output, or textual description of metric behavior)",
                },
                "incident_context": {
                    "type": "string",
                    "description": "Context about the incident to help interpret the metrics",
                },
            },
            "required": ["metrics_data"],
        },
    },
    {
        "name": "find_similar_incidents",
        "description": "Similar incident finder sub-agent. Searches JIRA/Confluence for past incidents with matching symptoms and surfaces applicable resolutions. Use proactively at the start of any investigation to check if this has happened before.",
        "input_schema": {
            "type": "object",
            "properties": {
                "incident_description": {
                    "type": "string",
                    "description": "Description of the current incident",
                },
                "symptoms": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of observed symptoms (e.g., '500 errors', 'high latency', 'connection timeouts')",
                },
            },
            "required": ["incident_description"],
        },
    },
    {
        "name": "write_postmortem",
        "description": "Post-mortem writer sub-agent. Generates a structured, blameless post-mortem document from the incident investigation. Use after root cause is identified and the incident is resolved or mitigated.",
        "input_schema": {
            "type": "object",
            "properties": {
                "conversation_context": {
                    "type": "string",
                    "description": "Summary of the investigation (findings, timeline, root cause, resolution)",
                },
                "incident_summary": {
                    "type": "string",
                    "description": "Brief one-line summary of the incident",
                },
            },
            "required": ["conversation_context"],
        },
    },
    {
        "name": "execute_runbook",
        "description": "Runbook execution sub-agent. Guides through a troubleshooting procedure step-by-step, adapting based on findings at each step. Use when following a known runbook or when systematic troubleshooting is needed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "runbook_content": {
                    "type": "string",
                    "description": "The runbook or troubleshooting procedure to follow",
                },
                "current_findings": {
                    "type": "string",
                    "description": "Findings from steps already completed",
                },
                "step_output": {
                    "type": "string",
                    "description": "Output from the most recent step (for branching logic)",
                },
            },
            "required": ["runbook_content"],
        },
    },
]


def get_available_tools(context_id: str | None = None) -> list[dict]:
    tools = list(BUILT_IN_TOOLS)
    if context_id:
        tools.extend(mcp_manager.get_tools_for_server_names(set()))
    else:
        tools.extend(mcp_manager.get_all_tools())
    return tools


async def get_available_tools_async(context_id: str) -> list[dict]:
    tools = list(BUILT_IN_TOOLS)
    linked_servers = await get_linked_servers_for_context(context_id)
    linked_names = {s["name"] for s in linked_servers}
    tools.extend(mcp_manager.get_tools_for_server_names(linked_names))
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

        elif tool_name == "correlate_logs":
            from src.agent.sub_agents.log_correlator import run_log_correlator
            return await run_log_correlator(
                logs=tool_input["logs"],
                services=tool_input.get("services"),
                time_range=tool_input.get("time_range"),
            )

        elif tool_name == "detect_changes":
            from src.agent.sub_agents.change_detector import run_change_detector
            return await run_change_detector(
                incident_description=tool_input["incident_description"],
                incident_start_time=tool_input.get("incident_start_time"),
                changes=tool_input.get("changes"),
            )

        elif tool_name == "analyze_metrics":
            from src.agent.sub_agents.metric_analyzer import run_metric_analyzer
            return await run_metric_analyzer(
                metrics_data=tool_input["metrics_data"],
                incident_context=tool_input.get("incident_context"),
            )

        elif tool_name == "find_similar_incidents":
            from src.agent.sub_agents.similar_incident_finder import run_similar_incident_finder
            return await run_similar_incident_finder(
                incident_description=tool_input["incident_description"],
                symptoms=tool_input.get("symptoms"),
            )

        elif tool_name == "write_postmortem":
            from src.agent.sub_agents.postmortem_writer import run_postmortem_writer
            return await run_postmortem_writer(
                conversation_context=tool_input["conversation_context"],
                incident_summary=tool_input.get("incident_summary"),
            )

        elif tool_name == "execute_runbook":
            from src.agent.sub_agents.runbook_executor import run_runbook_executor
            return await run_runbook_executor(
                runbook_content=tool_input["runbook_content"],
                current_findings=tool_input.get("current_findings"),
                step_output=tool_input.get("step_output"),
            )

        else:
            result = await mcp_manager.call_tool(tool_name, tool_input)
            return result if isinstance(result, str) else json.dumps(result)

    except Exception as e:
        return json.dumps({"error": str(e)})

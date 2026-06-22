from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage, ToolMessage

from src.agent.state import AgentState
from src.agent.tools import get_available_tools_async, execute_tool
from src.llm.provider import get_async_client, get_model_id


def _convert_messages(state: AgentState) -> list[dict]:
    messages = []
    for msg in state["messages"]:
        if hasattr(msg, "type"):
            msg_type = msg.type
            if msg_type == "human":
                messages.append({"role": "user", "content": msg.content})
            elif msg_type == "ai":
                entry = {"role": "assistant"}
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    entry["content"] = _build_assistant_content(msg)
                else:
                    entry["content"] = msg.content
                messages.append(entry)
            elif msg_type == "tool":
                messages.append({
                    "role": "user",
                    "content": [{"type": "tool_result", "tool_use_id": msg.tool_call_id, "content": msg.content}],
                })
        elif isinstance(msg, dict):
            role = msg.get("role", "user")
            if role == "human":
                role = "user"
            messages.append({"role": role, "content": msg["content"]})
    return messages


def _build_assistant_content(msg) -> list[dict]:
    blocks = []
    if msg.content:
        blocks.append({"type": "text", "text": msg.content})
    for tc in msg.tool_calls:
        blocks.append({
            "type": "tool_use",
            "id": tc["id"],
            "name": tc["name"],
            "input": tc["args"],
        })
    return blocks


async def orchestrator_node(state: AgentState) -> dict:
    client = get_async_client()
    model_id = get_model_id()
    tools = await get_available_tools_async(state["context_profile_id"])

    messages = _convert_messages(state)

    kwargs = {
        "model": model_id,
        "max_tokens": 4096,
        "system": state["system_prompt"],
        "messages": messages,
    }
    if tools:
        kwargs["tools"] = tools

    response = await client.messages.create(**kwargs)

    tool_calls = []
    text_parts = []

    for block in response.content:
        if block.type == "text":
            text_parts.append(block.text)
        elif block.type == "tool_use":
            tool_calls.append({
                "id": block.id,
                "name": block.name,
                "args": block.input,
            })

    content = "".join(text_parts)
    ai_msg = AIMessage(content=content, tool_calls=tool_calls)
    return {"messages": [ai_msg]}


async def tool_executor_node(state: AgentState) -> dict:
    last_msg = state["messages"][-1]
    tool_messages = []

    for tc in last_msg.tool_calls:
        result = await execute_tool(tc["name"], tc["args"])
        tool_messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))

    return {"messages": tool_messages}


def should_continue(state: AgentState) -> str:
    last_msg = state["messages"][-1]
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        return "tools"
    return "end"


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("tools", tool_executor_node)
    graph.set_entry_point("orchestrator")
    graph.add_conditional_edges("orchestrator", should_continue, {"tools": "tools", "end": END})
    graph.add_edge("tools", "orchestrator")
    return graph.compile()


agent_graph = build_graph()

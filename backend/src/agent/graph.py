from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage

from src.agent.state import AgentState
from src.llm.provider import get_async_client, get_model_id


async def orchestrator_node(state: AgentState) -> dict:
    client = get_async_client()
    model_id = get_model_id()

    messages = []
    for msg in state["messages"]:
        if hasattr(msg, "type"):
            messages.append({"role": msg.type if msg.type != "human" else "user", "content": msg.content})
        elif isinstance(msg, dict):
            role = msg.get("role", "user")
            if role == "human":
                role = "user"
            messages.append({"role": role, "content": msg["content"]})

    response = await client.messages.create(
        model=model_id,
        max_tokens=4096,
        system=state["system_prompt"],
        messages=messages,
    )

    content = response.content[0].text
    return {"messages": [AIMessage(content=content)]}


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    graph.add_node("orchestrator", orchestrator_node)
    graph.set_entry_point("orchestrator")
    graph.add_edge("orchestrator", END)
    return graph.compile()


agent_graph = build_graph()

from langgraph.graph import StateGraph, END
from state import LeadState
from nodes import search_node, extract_node, enrich_node, report_node


def should_continue(state: LeadState) -> str:
    if state.get("error"):
        print(f"[Router] Error detected: {state['error']}")
        return "enrich"
    if len(state.get("leads", [])) >= 10:
        print("[Router] Reached 10 leads, enriching...")
        return "enrich"
    if state.get("num_searches", 0) >= 2:
        print("[Router] Reached 2 searches, enriching...")
        return "enrich"
    print(f"[Router] Continuing search (searches: {state.get('num_searches', 0)}, leads: {len(state.get('leads', []))})")
    return "search"


def build_graph():
    graph = StateGraph(LeadState)

    graph.add_node("search", search_node)
    graph.add_node("extract", extract_node)
    graph.add_node("enrich", enrich_node)
    graph.add_node("report", report_node)

    graph.set_entry_point("search")
    graph.add_edge("search", "extract")
    graph.add_conditional_edges("extract", should_continue, {
        "search": "search",
        "enrich": "enrich",
    })
    graph.add_edge("enrich", "report")
    graph.add_edge("report", END)

    return graph.compile()

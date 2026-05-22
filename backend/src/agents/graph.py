from langgraph.graph import StateGraph, END
from typing import Literal
from .state import AgentState
from .nodes import (
    intent_node,
    profile_builder_node,
    rag_retrieval_node,
    live_lookup_node,
    synthesis_node,
    guardrail_node,
    translation_node,
)
import logging

logger = logging.getLogger(__name__)


def should_retrieve(state: AgentState) -> Literal["retrieve", "skip"]:
    """Determine if RAG retrieval is needed based on intent."""
    intent = state.get("intent")
    if intent in ["form_guidance", "deadline_query", "document_check"]:
        return "retrieve"
    return "skip"


def should_lookup(state: AgentState) -> Literal["lookup", "skip"]:
    """Determine if live data lookup is needed based on intent."""
    intent = state.get("intent")
    if intent in ["voter_lookup", "ero_location"]:
        return "lookup"
    return "skip"


def should_translate(state: AgentState) -> Literal["translate", "skip"]:
    """Determine if translation is needed."""
    language = state.get("response_language", "en")
    if language != "en":
        return "translate"
    return "skip"


def create_agent_graph() -> StateGraph:
    """
    Creates the LangGraph agent workflow.
    """
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("intent", intent_node)
    workflow.add_node("profile_builder", profile_builder_node)
    workflow.add_node("rag_retrieval", rag_retrieval_node)
    workflow.add_node("live_lookup", live_lookup_node)
    workflow.add_node("synthesis", synthesis_node)
    workflow.add_node("guardrail", guardrail_node)
    workflow.add_node("translation", translation_node)

    # Set entry point
    workflow.set_entry_point("intent")

    # Add edges
    workflow.add_edge("intent", "profile_builder")

    # Conditional edges for RAG retrieval
    workflow.add_conditional_edges(
        "profile_builder",
        should_retrieve,
        {
            "retrieve": "rag_retrieval",
            "skip": "synthesis",
        },
    )

    # Conditional edges for live lookup
    workflow.add_conditional_edges(
        "rag_retrieval",
        should_lookup,
        {
            "lookup": "live_lookup",
            "skip": "synthesis",
        },
    )

    workflow.add_edge("live_lookup", "synthesis")
    workflow.add_edge("synthesis", "guardrail")

    # Conditional edges for translation
    workflow.add_conditional_edges(
        "guardrail",
        should_translate,
        {
            "translate": "translation",
            "skip": END,
        },
    )

    workflow.add_edge("translation", END)

    return workflow.compile()


# Compile the graph
agent_graph = create_agent_graph()

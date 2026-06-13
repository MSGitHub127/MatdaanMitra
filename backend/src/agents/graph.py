"""
graph.py — LangGraph agent workflow for MatdaanMitra

Routing logic (fixed):
  intent → profile_builder → (route_after_profile)
      ├─ "retrieve"  → rag_retrieval → synthesis
      ├─ "lookup"    → live_lookup   → synthesis
      └─ "direct"    → synthesis

  synthesis → guardrail → (should_translate)
      ├─ "translate" → translation → END
      └─ "skip"      → END

Previous bug: live_lookup was only reachable after rag_retrieval,
but voter_lookup/ero_location intents skip RAG, making live_lookup
unreachable. Fixed by adding a direct profile_builder → live_lookup path.
"""

import logging
from typing import Literal

from langgraph.graph import StateGraph, END

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

logger = logging.getLogger(__name__)


# ── Routing functions ─────────────────────────────────────────────────────────

def route_after_profile_builder(
    state: AgentState,
) -> Literal["retrieve", "lookup", "synthesis"]:
    """
    Single routing function from profile_builder.
    Replaces the previous two-stage (should_retrieve → should_lookup) approach
    that left live_lookup unreachable for voter_lookup/ero_location intents.
    """
    intent = state.get("intent")

    if intent in ("form_guidance", "deadline_query", "document_check", "grievance_help"):
        return "retrieve"

    if intent in ("voter_lookup", "ero_location"):
        return "lookup"

    # profile_collection, grievance_help, off_topic, unknown → skip both
    return "synthesis"


def should_translate(state: AgentState) -> Literal["translate", "skip"]:
    """Only translate when the target language is not English."""
    lang = state.get("response_language", "en")
    return "translate" if lang and lang.lower() not in ("en", "en-in", "english") else "skip"


# ── Graph construction ────────────────────────────────────────────────────────

def create_agent_graph() -> StateGraph:
    workflow = StateGraph(AgentState)

    # Nodes
    workflow.add_node("intent_classifier", intent_node)
    workflow.add_node("profile_builder", profile_builder_node)
    workflow.add_node("rag_retrieval",   rag_retrieval_node)
    workflow.add_node("live_lookup",     live_lookup_node)
    workflow.add_node("synthesis",       synthesis_node)
    workflow.add_node("guardrail",       guardrail_node)
    workflow.add_node("translation",     translation_node)

    # Entry
    workflow.set_entry_point("intent_classifier")

    # Intent → profile builder (always)
    workflow.add_edge("intent_classifier", "profile_builder")

    # Profile builder → RAG / live lookup / synthesis (fixed routing)
    workflow.add_conditional_edges(
        "profile_builder",
        route_after_profile_builder,
        {
            "retrieve":  "rag_retrieval",
            "lookup":    "live_lookup",
            "synthesis": "synthesis",
        },
    )

    # RAG retrieval always flows to synthesis
    workflow.add_edge("rag_retrieval", "synthesis")

    # Live lookup always flows to synthesis
    workflow.add_edge("live_lookup", "synthesis")

    # Synthesis → guardrail (always)
    workflow.add_edge("synthesis", "guardrail")

    # Guardrail → translation or END
    workflow.add_conditional_edges(
        "guardrail",
        should_translate,
        {
            "translate": "translation",
            "skip":      END,
        },
    )

    workflow.add_edge("translation", END)

    return workflow.compile()


# Module-level singleton — imported by chat.py
agent_graph = create_agent_graph()
import re
from typing import Literal
from ..state import AgentState


POLITICAL_PATTERNS = [
    r'\b(BJP|Congress|AAP|TMC|NCP|SP|BSP|JDU|CPI|CPI-M)\b',
    r'\b(Modi|Gandhi|Shah|Rahul|Mamata|Kejriwal|Yogi)\b',
    r'\b(vote for|support|endorse|oppose)\b.*\b(party|candidate)\b',
    r'\b(election results?|polling|exit poll|opinion poll)\b',
]


def guardrail_node(state: AgentState) -> AgentState:
    """
    Guardrail node that filters political content and checks confidence.
    Returns modified state with filtered response or escalation flag.
    """
    response = state.get("final_response", "")
    if not response:
        return state

    # 1. Political content check
    for pattern in POLITICAL_PATTERNS:
        if re.search(pattern, response, re.IGNORECASE):
            return {
                **state,
                "final_response": (
                    "I'm designed to assist only with voter registration "
                    "procedures — not electoral politics. Is there anything "
                    "about your registration I can help with?"
                ),
                "requires_escalation": False,
            }

    # 2. Low-confidence check
    confidence = state.get("confidence_score", 0.0)
    if confidence < 0.75:
        return {
            **state,
            "final_response": (
                "I don't have verified official data for this query. "
                "Please check eci.gov.in or call the National Voter "
                "Helpline at 1950 for authoritative information."
            ),
            "requires_escalation": True,
        }

    # 3. Append citations for high-confidence responses
    retrieved_chunks = state.get("retrieved_chunks", [])
    citations = [
        f"[Source: {c['section']} — {c['source_url']}]"
        for c in retrieved_chunks
        if c.get("confidence", 0) > 0.80
    ]
    if citations:
        response = response + "\n\n" + " · ".join(citations)

    return {**state, "final_response": response}

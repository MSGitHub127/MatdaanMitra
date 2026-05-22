from typing import TypedDict, Annotated, Sequence, Literal, NotRequired
from langchain_core.messages import BaseMessage
import operator


class VoterProfile(TypedDict, total=False):
    """Voter profile information collected during conversation."""
    name: str
    current_state: str
    current_pincode: str
    previous_state: str
    previous_constituency: str
    registration_type: Literal["new", "relocation", "correction", "nri"]
    epic_number: str  # stored encrypted via Fernet
    preferred_language: str
    checklist: dict[str, bool]


class RetrievedChunk(TypedDict):
    """A chunk retrieved from the vector search."""
    chunk_id: str
    text: str
    confidence: float
    source_url: str
    form_type: str
    section: str


class AgentState(TypedDict):
    """State for the LangGraph agent workflow."""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    session_id: str
    voter_profile: VoterProfile
    intent: Literal[
        "profile_collection",
        "form_guidance",
        "deadline_query",
        "document_check",
        "voter_lookup",
        "ero_location",
        "grievance_help",
        "off_topic",
        "unknown",
    ] | None
    retrieved_chunks: list[RetrievedChunk]
    live_data: dict | None
    final_response: str | None
    response_language: str
    confidence_score: float
    agent_trace: list[dict]
    requires_escalation: bool
    error: str | None

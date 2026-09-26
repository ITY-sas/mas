"""
LangGraph state schemas for the multi-agent system.
Each agent has its own state; the SupervisorState is the global shared state.
"""
from typing import Annotated, TypedDict

import operator


class IdeacionState(TypedDict):
    """State for the Ideación agent subgraph.

    Shared keys with SupervisorState: brief, client_id (input), idea, idea_id (output).
    """

    # ── Input (from supervisor) ──
    brief: dict
    client_id: int

    # ── Internal working state ──
    client_profile: str
    trends: str
    competitors: str
    similar_ideas: str
    news: str

    # ── Output (to supervisor) ──
    idea: str
    idea_id: int


class PublicacionState(TypedDict):
    """State for the Publicación agent subgraph.

    Shared keys with SupervisorState: idea, client_id, idea_id (input),
    publication, publication_id (output).
    """

    # ── Input (from supervisor) ──
    idea: str
    client_id: int
    idea_id: int

    # ── Internal working state ──
    client_profile: str
    trends: str
    trending: str

    # ── Output (to supervisor) ──
    publication: str
    publication_id: int


class SupervisorState(TypedDict):
    """Global state shared across the whole multi-agent graph.

    The supervisor reads this to decide which agent runs next.
    Each agent subgraph reads its inputs from and writes its outputs back to this state.
    """

    # ── Input ──
    brief: dict
    client_id: int

    # ── Ideación agent output ──
    idea: str
    idea_id: int

    # ── Publicación agent output ──
    publication: str
    publication_id: int

    # ── Audit log (append-only via operator.add) ──
    log: Annotated[list[str], operator.add]

"""
SQLite persistence layer for negotiation session logging.

Provides:
- Schema creation on import
- Round-level persistence
- Query helpers for transcripts, status, and analytics
"""

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from app.config import DB_PATH

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
#  Schema
# ═══════════════════════════════════════════════════════════════════

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS negotiation_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    round_number INTEGER NOT NULL,
    buyer_offer REAL,
    seller_offer REAL,
    buyer_reasoning TEXT,
    seller_reasoning TEXT,
    retrieved_documents TEXT,
    mediator_decision TEXT,
    human_override TEXT,
    final_status TEXT
);
"""

_CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_session_id ON negotiation_log (session_id);
"""


@contextmanager
def _get_connection():
    """Context manager for SQLite connections."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create the negotiation_log table if it doesn't exist."""
    with _get_connection() as conn:
        conn.execute(_CREATE_TABLE_SQL)
        conn.execute(_CREATE_INDEX_SQL)
    logger.info("[DB] Initialised database at %s", DB_PATH)


# Initialise on module import
init_db()


# ═══════════════════════════════════════════════════════════════════
#  Write Operations
# ═══════════════════════════════════════════════════════════════════

def persist_round(
    session_id: str,
    round_number: int,
    buyer_offer: Optional[float],
    seller_offer: Optional[float],
    buyer_reasoning: str,
    seller_reasoning: str,
    retrieved_documents: str,
    mediator_decision: str,
    human_override: Optional[str],
    final_status: str,
) -> None:
    """
    Insert a single negotiation round record into the database.

    Parameters
    ----------
    session_id : str
        Unique session identifier.
    round_number : int
        The round number for this entry.
    buyer_offer, seller_offer : float | None
        Price offers from each party.
    buyer_reasoning, seller_reasoning : str
        Textual reasoning from each agent.
    retrieved_documents : str
        JSON-serialised list of retrieved benchmark texts.
    mediator_decision : str
        One of CONTINUE, HUMAN_CHECKPOINT, SUCCESS, FAILURE.
    human_override : str | None
        Description of any human intervention.
    final_status : str
        Session status after this round.
    """
    sql = """
        INSERT INTO negotiation_log
        (session_id, round_number, buyer_offer, seller_offer,
         buyer_reasoning, seller_reasoning, retrieved_documents,
         mediator_decision, human_override, final_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    with _get_connection() as conn:
        conn.execute(
            sql,
            (
                session_id,
                round_number,
                buyer_offer,
                seller_offer,
                buyer_reasoning,
                seller_reasoning,
                retrieved_documents,
                mediator_decision,
                human_override,
                final_status,
            ),
        )
    logger.debug(
        "[DB] Persisted round %d for session %s", round_number, session_id
    )


# ═══════════════════════════════════════════════════════════════════
#  Read Operations
# ═══════════════════════════════════════════════════════════════════

def get_transcript(session_id: str) -> list[dict[str, Any]]:
    """
    Retrieve the full negotiation transcript for a given session.

    Returns
    -------
    list[dict]
        List of round records ordered by round number.
    """
    sql = """
        SELECT * FROM negotiation_log
        WHERE session_id = ?
        ORDER BY round_number ASC
    """
    with _get_connection() as conn:
        rows = conn.execute(sql, (session_id,)).fetchall()
    return [dict(row) for row in rows]


def get_session_status(session_id: str) -> dict[str, Any] | None:
    """
    Retrieve the latest round record for a session (current status).

    Returns
    -------
    dict | None
        The latest round record, or None if session not found.
    """
    sql = """
        SELECT * FROM negotiation_log
        WHERE session_id = ?
        ORDER BY round_number DESC
        LIMIT 1
    """
    with _get_connection() as conn:
        row = conn.execute(sql, (session_id,)).fetchone()
    return dict(row) if row else None


def get_all_sessions() -> list[dict[str, Any]]:
    """
    Retrieve a summary of all negotiation sessions.

    Returns
    -------
    list[dict]
        One record per session with session_id, total rounds, and final status.
    """
    sql = """
        SELECT
            session_id,
            MAX(round_number) as total_rounds,
            final_status,
            MIN(timestamp) as started_at,
            MAX(timestamp) as ended_at,
            MIN(buyer_offer) as min_buyer_offer,
            MAX(seller_offer) as max_seller_offer
        FROM negotiation_log
        GROUP BY session_id
        ORDER BY started_at DESC
    """
    with _get_connection() as conn:
        rows = conn.execute(sql).fetchall()
    return [dict(row) for row in rows]


def get_analytics() -> dict[str, Any]:
    """
    Compute aggregate analytics across all negotiation sessions.

    Returns
    -------
    dict
        Analytics including total_sessions, success_rate, average_rounds,
        average_final_gap_pct, average concessions.
    """
    sessions = get_all_sessions()
    if not sessions:
        return {
            "total_sessions": 0,
            "success_rate": 0.0,
            "average_rounds": 0.0,
            "average_final_gap_pct": 0.0,
            "average_buyer_concession": 0.0,
            "average_seller_concession": 0.0,
        }

    total = len(sessions)
    successes = sum(1 for s in sessions if s.get("final_status") == "SUCCESS")
    avg_rounds = sum(s.get("total_rounds", 0) for s in sessions) / total

    # Compute average concessions per session
    total_buyer_concession = 0.0
    total_seller_concession = 0.0
    total_final_gap_pct = 0.0
    sessions_with_data = 0

    for session in sessions:
        transcript = get_transcript(session["session_id"])
        if len(transcript) >= 2:
            sessions_with_data += 1
            first = transcript[0]
            last = transcript[-1]

            buyer_first = first.get("buyer_offer") or 0
            buyer_last = last.get("buyer_offer") or 0
            seller_first = first.get("seller_offer") or 0
            seller_last = last.get("seller_offer") or 0

            total_buyer_concession += abs(buyer_last - buyer_first)
            total_seller_concession += abs(seller_first - seller_last)

            if seller_last and seller_last > 0:
                gap_pct = abs(seller_last - buyer_last) / seller_last * 100
                total_final_gap_pct += gap_pct

    avg_buyer_concession = (
        total_buyer_concession / sessions_with_data if sessions_with_data else 0.0
    )
    avg_seller_concession = (
        total_seller_concession / sessions_with_data if sessions_with_data else 0.0
    )
    avg_final_gap_pct = (
        total_final_gap_pct / sessions_with_data if sessions_with_data else 0.0
    )

    return {
        "total_sessions": total,
        "success_rate": round(successes / total * 100, 1),
        "average_rounds": round(avg_rounds, 1),
        "average_final_gap_pct": round(avg_final_gap_pct, 2),
        "average_buyer_concession": round(avg_buyer_concession, 2),
        "average_seller_concession": round(avg_seller_concession, 2),
    }

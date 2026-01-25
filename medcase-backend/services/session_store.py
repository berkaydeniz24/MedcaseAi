# services/session_store.py
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Dict, Optional, Any


@dataclass
class SessionData:
    session_id: str
    case_id: str
    mcq: Dict[str, Any]
    created_at: float


class SessionStore:
    """
    In-memory session store (fast + simple).
    - Keeps generated MCQ stable within a session.
    - Optional TTL cleanup.
    """
    def __init__(self, ttl_seconds: int = 60 * 60):
        self.ttl_seconds = ttl_seconds
        self._sessions: Dict[str, SessionData] = {}

    def create_session(self, case_id: str, mcq: Dict[str, Any]) -> SessionData:
        session_id = str(uuid.uuid4())
        s = SessionData(
            session_id=session_id,
            case_id=case_id,
            mcq=mcq,
            created_at=time.time(),
        )
        self._sessions[session_id] = s
        return s

    def get(self, session_id: str) -> Optional[SessionData]:
        self._cleanup()
        return self._sessions.get(session_id)

    def _cleanup(self) -> None:
        now = time.time()
        expired = [
            sid for sid, s in self._sessions.items()
            if (now - s.created_at) > self.ttl_seconds
        ]
        for sid in expired:
            self._sessions.pop(sid, None)


session_store = SessionStore(ttl_seconds=60 * 60)  # 1 hour TTL

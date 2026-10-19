"""Audit logging."""
import hashlib
import json
from datetime import datetime
from typing import List

from app.db.session import get_session_factory
from app.db.models import AuditLog


def write_audit_log(
    request_id: str,
    user_id: str,
    tenant_id: str,
    role_level: int,
    question: str,
    access_mode: str,
    cache_mode: str,
    cache_hit: bool,
    retrieved_chunk_ids: List[str],
    cited_chunk_ids: List[str],
    refused: bool,
    answer: str,
    latency_ms: int,
    model: str,
) -> None:
    """Write an audit log entry."""
    SessionLocal = get_session_factory()
    db = SessionLocal()

    try:
        # Hash the answer instead of storing it
        answer_hash = hashlib.sha256(answer.encode()).hexdigest()

        log_entry = AuditLog(
            request_id=request_id,
            ts=datetime.utcnow(),
            user_id=user_id,
            tenant_id=tenant_id,
            role_level=role_level,
            question=question,
            access_mode=access_mode,
            cache_mode=cache_mode,
            cache_hit=1 if cache_hit else 0,
            retrieved_chunk_ids=json.dumps(retrieved_chunk_ids),
            cited_chunk_ids=json.dumps(cited_chunk_ids),
            refused=1 if refused else 0,
            answer_hash=answer_hash,
            latency_ms=latency_ms,
            model=model,
        )

        db.add(log_entry)
        db.commit()
    finally:
        db.close()

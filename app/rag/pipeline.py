"""Main RAG pipeline."""
import logging
import time
import uuid
from typing import Dict, Any

from app.security.acl import User
from app.rag.retriever import retrieve
from app.rag.reranker import rerank
from app.rag.context import assemble_context
from app.rag.generate import get_llm_client
from app.rag.validate import validate_citations, REFUSAL_STRING
from app.prompts.answer_v1 import SYSTEM_PROMPT_PRE, build_user_prompt
from app.db.audit import write_audit_log
from app.config import settings

logger = logging.getLogger(__name__)


def answer(user: User, question: str, access_mode: str = "pre") -> Dict[str, Any]:
    """Main RAG pipeline.

    Args:
        user: Authenticated user
        question: User's question
        access_mode: Access control mode (only "pre" supported in Phase 1)

    Returns:
        Answer result with sources, metadata, and timing
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()

    # Step 1: Retrieve with ACL filter
    retrieve_start = time.time()
    chunks = retrieve(user, question, top_k=settings.dense_top_k)
    retrieve_time = int((time.time() - retrieve_start) * 1000)

    # Step 2: Rerank (stub in Phase 1)
    chunks = rerank(chunks, question, top_k=settings.rerank_top_k)

    # Check if we have results
    if not chunks:
        # No chunks - return refusal
        total_time = int((time.time() - start_time) * 1000)

        write_audit_log(
            request_id=request_id,
            user_id=user.user_id,
            tenant_id=user.tenant_id,
            role_level=user.role_level,
            question=question,
            access_mode=access_mode,
            cache_mode="off",
            cache_hit=False,
            retrieved_chunk_ids=[],
            cited_chunk_ids=[],
            refused=True,
            answer=REFUSAL_STRING,
            latency_ms=total_time,
            model=settings.effective_model,
        )

        return {
            "answer": REFUSAL_STRING,
            "sources": [],
            "refused": True,
            "cache_hit": False,
            "latency_ms": {
                "total": total_time,
                "retrieve": retrieve_time,
                "generate": 0,
            },
            "request_id": request_id,
        }

    # Step 3: Assemble context
    context_text, sources = assemble_context(chunks)

    # Step 4: Generate
    generate_start = time.time()
    llm_client = get_llm_client()
    user_prompt = build_user_prompt(context_text, question)

    try:
        answer_text = llm_client.generate(SYSTEM_PROMPT_PRE, user_prompt)
    except Exception as e:
        # LLM failure - return error as refusal
        logger.exception("LLM generation failed (request_id=%s): %s", request_id, e)
        answer_text = REFUSAL_STRING

    generate_time = int((time.time() - generate_start) * 1000)

    # Step 5: Validate citations
    valid_refs = [s["ref"] for s in sources]
    raw_answer = answer_text
    answer_text, has_warning = validate_citations(answer_text, valid_refs)
    if answer_text == REFUSAL_STRING and raw_answer != REFUSAL_STRING:
        logger.warning(
            "Citation validation replaced answer with refusal (request_id=%s). Raw LLM output: %r",
            request_id, raw_answer,
        )

    # Extract cited sources
    cited_chunk_ids = []
    if answer_text != REFUSAL_STRING:
        # Map refs back to chunk IDs
        ref_to_chunk = {s["ref"]: s["chunk_id"] for s in sources}
        import re
        citations = re.findall(r'\[S(\d+)\]', answer_text)
        for cit in citations:
            ref = f"S{cit}"
            if ref in ref_to_chunk:
                cited_chunk_ids.append(ref_to_chunk[ref])

    # Step 6: Write audit log
    total_time = int((time.time() - start_time) * 1000)
    retrieved_chunk_ids = [c["chunk_id"] for c in chunks]

    write_audit_log(
        request_id=request_id,
        user_id=user.user_id,
        tenant_id=user.tenant_id,
        role_level=user.role_level,
        question=question,
        access_mode=access_mode,
        cache_mode="off",
        cache_hit=False,
        retrieved_chunk_ids=retrieved_chunk_ids,
        cited_chunk_ids=cited_chunk_ids,
        refused=(answer_text == REFUSAL_STRING),
        answer=answer_text,
        latency_ms=total_time,
        model=settings.effective_model,
    )

    return {
        "answer": answer_text,
        "sources": sources if answer_text != REFUSAL_STRING else [],
        "refused": (answer_text == REFUSAL_STRING),
        "cache_hit": False,
        "latency_ms": {
            "total": total_time,
            "retrieve": retrieve_time,
            "generate": generate_time,
        },
        "request_id": request_id,
    }

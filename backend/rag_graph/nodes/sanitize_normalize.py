from __future__ import annotations

from typing import Any, List, Tuple

from backend.utils.input_sanitizer import detect_prompt_injection, sanitize_query_input
from backend.utils.litecoin_vocabulary import normalize_ltc_keywords

from ..state import RAGState


def make_sanitize_normalize_node(pipeline: Any):
    async def sanitize_normalize(state: RAGState) -> RAGState:
        raw_query = state.get("raw_query") or ""
        chat_history_pairs: List[Tuple[str, str]] = state.get("chat_history_pairs") or []

        # Query sanitization (reuse existing pipeline helpers)
        detect_prompt_injection(raw_query)
        sanitized_query = sanitize_query_input(raw_query)

        # Sanitize history
        sanitized_history: List[Tuple[str, str]] = []
        for human_msg, ai_msg in chat_history_pairs:
            h = sanitize_query_input(human_msg) if human_msg else human_msg
            a = sanitize_query_input(ai_msg) if ai_msg else ai_msg
            sanitized_history.append((h, a))

        truncated_history = (
            pipeline._truncate_chat_history(sanitized_history)  # type: ignore[attr-defined]
            if hasattr(pipeline, "_truncate_chat_history")
            else sanitized_history
        )

        normalized_query = normalize_ltc_keywords(sanitized_query)

        state.update(
            {
                "sanitized_query": sanitized_query,
                "normalized_query": normalized_query,
                "truncated_history_pairs": truncated_history,
                "metadata": state.get("metadata") or {},
            }
        )
        return state

    return sanitize_normalize



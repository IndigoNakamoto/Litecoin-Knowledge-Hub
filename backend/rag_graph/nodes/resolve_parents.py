from __future__ import annotations

import logging
from typing import Any, Dict, List

from langchain_core.documents import Document

from ..state import RAGState


def make_resolve_parents_node(pipeline: Any):
    async def resolve_parents(state: RAGState) -> RAGState:
        """
        Parent-document pattern resolution for synthetic FAQ question hits.

        If FAQ indexing is enabled, swap synthetic question hits with their parent chunks.
        """
        metadata: Dict[str, Any] = state.get("metadata") or {}
        context_docs: List[Document] = state.get("context_docs") or []

        if not getattr(pipeline, "use_faq_indexing", False) or not context_docs:
            state["metadata"] = metadata
            return state

        logger = logging.getLogger(__name__)

        synthetic_count = sum(1 for d in context_docs if d.metadata.get("is_synthetic", False))
        if synthetic_count <= 0:
            state["metadata"] = metadata
            return state

        try:
            from backend.services.faq_generator import resolve_parents as resolve_parents_fn

            parent_chunks_map = pipeline._load_parent_chunks_map() if hasattr(pipeline, "_load_parent_chunks_map") else {}
            if parent_chunks_map:
                resolved = resolve_parents_fn(context_docs, parent_chunks_map)
                state["context_docs"] = resolved
                state["published_sources"] = [d for d in resolved if d.metadata.get("status") == "published"]
        except Exception as e:
            logger.warning("FAQ parent resolution failed; using original docs: %s", e)

        state["metadata"] = metadata
        return state

    return resolve_parents



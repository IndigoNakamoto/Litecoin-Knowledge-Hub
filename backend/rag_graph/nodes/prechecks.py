from __future__ import annotations

from typing import Any, Dict

from ..state import RAGState


def make_prechecks_node(pipeline: Any):
    async def prechecks(state: RAGState) -> RAGState:
        """
        Prechecks: intent (optional) and exact cache check.

        We keep this conservative: if integrations aren't configured on the pipeline yet,
        this node becomes a no-op.
        """
        query_text = state.get("sanitized_query") or state.get("raw_query") or ""
        effective_history = state.get("effective_history_pairs") or []
        is_dependent = bool(state.get("is_dependent", False))

        metadata: Dict[str, Any] = state.get("metadata") or {}

        # 1) Intent/static responses (optional)
        if getattr(pipeline, "use_intent_classification", False) and not is_dependent:
            intent_classifier = pipeline.get_intent_classifier() if hasattr(pipeline, "get_intent_classifier") else None
            if intent_classifier:
                try:
                    from backend.services.intent_classifier import Intent

                    intent, matched_faq, static_response = intent_classifier.classify(query_text)
                    state["intent"] = getattr(intent, "value", str(intent))
                    state["matched_faq"] = matched_faq

                    if intent in (Intent.GREETING, Intent.THANKS) and static_response:
                        state.update(
                            {
                                "early_answer": static_response,
                                "early_sources": [],
                                "early_cache_type": f"intent_{intent.value}",
                            }
                        )
                        metadata.update(
                            {
                                "input_tokens": 0,
                                "output_tokens": 0,
                                "cost_usd": 0.0,
                                "cache_hit": True,
                                "cache_type": state["early_cache_type"],
                                "intent": intent.value,
                            }
                        )
                        state["metadata"] = metadata
                        return state

                    # FAQ match: try suggested question cache (if available)
                    if intent == Intent.FAQ_MATCH and matched_faq:
                        suggested_cache = (
                            pipeline.get_suggested_question_cache()
                            if hasattr(pipeline, "get_suggested_question_cache")
                            else None
                        )
                        if suggested_cache and hasattr(suggested_cache, "get"):
                            cached = await suggested_cache.get(matched_faq)
                            if cached:
                                answer, sources = cached
                                # Skip entries that only contain the generic error message
                                if answer and answer.strip() != getattr(pipeline, "generic_user_error_message", ""):
                                    state.update(
                                        {
                                            "early_answer": answer,
                                            "early_sources": sources,
                                            "early_cache_type": "intent_faq_match",
                                        }
                                    )
                                    metadata.update(
                                        {
                                            "input_tokens": 0,
                                            "output_tokens": 0,
                                            "cost_usd": 0.0,
                                            "cache_hit": True,
                                            "cache_type": "intent_faq_match",
                                            "intent": "faq_match",
                                            "matched_faq": matched_faq,
                                        }
                                    )
                                    state["metadata"] = metadata
                                    return state
                except Exception:
                    # Best-effort only; fall through to normal flow.
                    pass

        # 2) Exact cache check (optional)
        query_cache = getattr(pipeline, "query_cache", None)
        if query_cache and hasattr(query_cache, "get"):
            try:
                cached = query_cache.get(query_text, effective_history)
                if cached:
                    answer, sources = cached
                    state.update(
                        {
                            "early_answer": answer,
                            "early_sources": sources,
                            "early_cache_type": "exact",
                        }
                    )
                    metadata.update(
                        {
                            "input_tokens": 0,
                            "output_tokens": 0,
                            "cost_usd": 0.0,
                            "cache_hit": True,
                            "cache_type": "exact",
                        }
                    )
                    state["metadata"] = metadata
                    return state
            except Exception:
                pass

        # 3) Set rewritten query defaults for downstream nodes
        effective_query = state.get("effective_query") or query_text
        # Post-rewrite normalization + entity expansion for retrieval recall
        try:
            from backend.utils.litecoin_vocabulary import expand_ltc_entities, normalize_ltc_keywords

            rewritten_normalized = normalize_ltc_keywords(effective_query)
            rewritten_expanded = expand_ltc_entities(rewritten_normalized).strip()
        except Exception:
            rewritten_expanded = effective_query

        state["rewritten_query"] = rewritten_expanded
        state["rewritten_query_for_cache"] = rewritten_expanded
        state["retrieval_query"] = rewritten_expanded
        state["metadata"] = metadata
        return state

    return prechecks



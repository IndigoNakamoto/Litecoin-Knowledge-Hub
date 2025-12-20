import pytest

from langchain_core.documents import Document

from backend.rag_graph.graph import build_rag_graph
from backend.rag_graph.nodes.factory import build_nodes


class _DummyExactCache:
    def __init__(self, answer: str, sources):
        self._answer = answer
        self._sources = sources

    def get(self, query_text, history_pairs):
        return (self._answer, self._sources)

    def set(self, *args, **kwargs):
        return None


class _DummyRedisVectorCache:
    def __init__(self, answer: str, sources_data):
        self._answer = answer
        self._sources_data = sources_data

    async def get(self, vector):
        return (self._answer, self._sources_data)


class _DummyInfinity:
    dimension = 1024

    async def embed_query(self, query: str):
        return [0.0] * self.dimension, None


class _DummyRetriever:
    def __init__(self, docs):
        self._docs = docs

    async def ainvoke(self, query: str):
        return self._docs


class _FakePipeline:
    # Minimal surface required by nodes
    def __init__(self):
        self.strong_ambiguous_tokens = {"it", "this", "that"}
        self.strong_prefixes = ("and ", "also ")
        self.use_intent_classification = False
        self.use_redis_cache = False
        self.use_infinity_embeddings = False
        self.use_faq_indexing = False
        self.retriever_k = 3
        self.sparse_rerank_limit = 3
        self.monitoring_enabled = False
        self.model_name = "dummy"
        self.generic_user_error_message = "ERR"
        self.no_kb_match_response = "NO_MATCH"

        self.query_cache = None
        self.semantic_cache = None
        self.hybrid_retriever = None

    def _truncate_chat_history(self, history_pairs):
        return history_pairs

    def get_infinity_embeddings(self):
        return None

    def get_redis_vector_cache(self):
        return None

    def get_intent_classifier(self):
        return None

    def get_suggested_question_cache(self):
        return None


@pytest.mark.asyncio
async def test_graph_early_return_exact_cache():
    pipeline = _FakePipeline()
    cached_doc = Document(page_content="cached", metadata={"status": "published"})
    pipeline.query_cache = _DummyExactCache("cached-answer", [cached_doc])

    graph = build_rag_graph(build_nodes(pipeline))
    state = await graph.ainvoke({"raw_query": "q", "chat_history_pairs": [], "metadata": {}})

    assert state["early_answer"] == "cached-answer"
    assert len(state["early_sources"]) == 1
    assert state["early_cache_type"] == "exact"


@pytest.mark.asyncio
async def test_graph_early_return_redis_vector_cache():
    pipeline = _FakePipeline()
    pipeline.use_redis_cache = True
    pipeline.use_infinity_embeddings = True

    pipeline.get_infinity_embeddings = lambda: _DummyInfinity()
    sources_data = [{"page_content": "x", "metadata": {"status": "published"}}]
    pipeline.get_redis_vector_cache = lambda: _DummyRedisVectorCache("redis-answer", sources_data)

    graph = build_rag_graph(build_nodes(pipeline))
    state = await graph.ainvoke({"raw_query": "q", "chat_history_pairs": [], "metadata": {}})

    assert state["early_answer"] == "redis-answer"
    assert state["early_cache_type"] == "redis_vector"
    assert len(state["early_sources"]) == 1
    assert state["early_sources"][0].metadata["status"] == "published"


@pytest.mark.asyncio
async def test_graph_retrieve_filters_published_sources():
    pipeline = _FakePipeline()
    docs = [
        Document(page_content="a", metadata={"status": "published"}),
        Document(page_content="b", metadata={"status": "draft"}),
    ]
    pipeline.hybrid_retriever = _DummyRetriever(docs)

    graph = build_rag_graph(build_nodes(pipeline))
    state = await graph.ainvoke({"raw_query": "q", "chat_history_pairs": [], "metadata": {}})

    assert len(state["context_docs"]) == 2
    assert len(state["published_sources"]) == 1
    assert state["published_sources"][0].page_content == "a"



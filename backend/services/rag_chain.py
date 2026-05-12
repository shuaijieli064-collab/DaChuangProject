"""RAG 链路编排服务"""
import logging
import time
from dataclasses import dataclass, field

from .vector_store import VectorStore, SearchResult
from .bm25 import BM25Search

logger = logging.getLogger(__name__)


@dataclass
class RAGResponse:
    """RAG 响应"""
    answer: str
    sources: list[dict] = field(default_factory=list)
    latency_ms: float = 0.0
    retrieval_count: int = 0


class RAGChain:
    """RAG 检索增强生成链"""

    def __init__(
        self,
        vector_store: VectorStore,
        bm25: BM25Search | None = None,
        llm_fn=None,
        top_k: int = 5,
        rerank_fn=None,
    ):
        self.vector_store = vector_store
        self.bm25 = bm25
        self.llm_fn = llm_fn  # (messages) -> str
        self.top_k = top_k
        self.rerank_fn = rerank_fn

    def retrieve(self, query: str) -> list[dict]:
        """混合检索：向量召回 + BM25 + Rerank"""
        # 1. 向量检索
        vec_results = self.vector_store.search(query, top_k=self.top_k)
        vec_docs = [
            {"content": r.content, "score": r.score, "source": r.source, "metadata": r.metadata}
            for r in vec_results
        ]

        # 2. BM25 检索（如果有）
        bm25_docs = []
        if self.bm25:
            bm25_docs = self.bm25.search(query, top_k=self.top_k)

        # 3. 合并去重
        merged = self._merge_results(vec_docs, bm25_docs)

        # 4. Rerank（如果有）
        if self.rerank_fn and len(merged) > 1:
            merged = self.rerank_fn(query, merged)

        return merged[: self.top_k]

    def generate(self, query: str, history: list[dict] | None = None) -> RAGResponse:
        """完整 RAG 流程：检索 → 增强 → 生成"""
        start = time.time()

        # 检索
        docs = self.retrieve(query)

        # 构建上下文
        context = self._build_context(docs)

        # 构建 prompt
        messages = self._build_messages(query, context, history)

        # 生成
        if self.llm_fn:
            answer = self.llm_fn(messages)
        else:
            answer = "[LLM 未配置，仅返回检索结果]"

        latency = (time.time() - start) * 1000

        return RAGResponse(
            answer=answer,
            sources=[{"content": d["content"][:200], "source": d.get("source", "")} for d in docs],
            latency_ms=latency,
            retrieval_count=len(docs),
        )

    def _build_context(self, docs: list[dict]) -> str:
        """从检索结果构建上下文"""
        if not docs:
            return "暂无相关知识库内容。"

        parts = []
        for i, doc in enumerate(docs, 1):
            parts.append(f"[文档{i}] {doc['content']}")
        return "\n\n".join(parts)

    def _build_messages(
        self,
        query: str,
        context: str,
        history: list[dict] | None = None,
    ) -> list[dict]:
        """构建 LLM 对话消息"""
        system_prompt = (
            "你是智链校园的高校事务助手。请根据以下【参考资料】回答问题。\n"
            "要求：\n"
            "1. 回答必须基于参考资料，不可编造信息\n"
            "2. 如果参考资料不足以回答问题，请明确说明\n"
            "3. 使用结构化的 Markdown 格式\n"
            "4. 引用来源时标注 [文档N]"
        )

        messages = [
            {"role": "system", "content": system_prompt},
        ]

        if history:
            for msg in history:
                messages.append(msg)

        messages.append(
            {"role": "user", "content": f"【参考资料】\n{context}\n\n问题：{query}"}
        )

        return messages

    @staticmethod
    def _merge_results(vec_docs: list[dict], bm25_docs: list[dict]) -> list[dict]:
        """合并向量检索和 BM25 结果，去重"""
        seen = set()
        merged = []
        # 优先保留向量检索结果
        for doc in vec_docs:
            key = doc["content"][:100]
            if key not in seen:
                seen.add(key)
                merged.append(doc)
        for doc in bm25_docs:
            key = doc["content"][:100]
            if key not in seen:
                seen.add(key)
                merged.append(doc)
        return merged

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """检索结果"""
    content: str
    metadata: dict = field(default_factory=dict)
    score: float = 0.0
    source: str = ""


class VectorStore:
    """向量存储抽象 — 支持 Milvus Lite（开发）和 Milvus Server（生产）"""

    def __init__(
        self,
        collection_name: str = "campus_knowledge",
        embedding_model_name: str = "BAAI/bge-m3",
        milvus_uri: str = "milvus_local.db",  # 本地开发用 SQLite 模式
    ):
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model_name
        self.milvus_uri = milvus_uri
        self._client = None
        self._embed_model = None

    def _get_embed_model(self):
        """懒加载 Embedding 模型"""
        if self._embed_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embed_model = SentenceTransformer(self.embedding_model_name)
                logger.info("已加载 Embedding 模型: %s", self.embedding_model_name)
            except ImportError:
                logger.warning("未安装 sentence-transformers，使用 mock embedding")
                self._embed_model = _MockEmbedModel()
        return self._embed_model

    def _get_client(self):
        """懒加载 Milvus 客户端"""
        if self._client is None:
            try:
                from pymilvus import MilvusClient
                self._client = MilvusClient(uri=self.milvus_uri)
                logger.info("已连接 Milvus: %s", self.milvus_uri)
            except ImportError:
                logger.warning("未安装 pymilvus，使用内存存储 fallback")
                self._client = _InMemoryStore()
        return self._client

    def embed_text(self, text: str) -> list[float]:
        """将文本转为向量"""
        model = self._get_embed_model()
        return model.encode(text)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """批量向量化"""
        model = self._get_embed_model()
        return model.encode(texts)

    def add_documents(self, chunks: list, embeddings: list[list[float]]):
        """添加文档到向量库"""
        client = self._get_client()
        data = []
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            data.append({
                "id": chunk.chunk_id or f"chunk_{i}",
                "vector": emb,
                "content": chunk.content,
                "metadata": str(chunk.metadata),
                "source": chunk.metadata.get("source", ""),
            })
        client.insert(collection_name=self.collection_name, data=data)
        logger.info("已添加 %d 个 chunk 到向量库", len(data))

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_expr: str = "",
    ) -> list[SearchResult]:
        """向量检索"""
        client = self._get_client()
        query_vec = self.embed_text(query)

        results = client.search(
            collection_name=self.collection_name,
            data=[query_vec],
            limit=top_k,
            filter=filter_expr,
            output_fields=["content", "metadata", "source"],
        )

        search_results = []
        if results:
            for hit in results[0]:
                entity = hit.get("entity", {})
                search_results.append(SearchResult(
                    content=entity.get("content", ""),
                    metadata=entity.get("metadata", {}),
                    score=hit.get("distance", 0.0),
                    source=entity.get("source", ""),
                ))
        return search_results

    def ensure_collection(self, dimension: int = 1024):
        """确保集合存在"""
        client = self._get_client()
        if hasattr(client, "has_collection"):
            if not client.has_collection(self.collection_name):
                from pymilvus import CollectionSchema, FieldSchema, DataType

                fields = [
                    FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=256, is_primary=True),
                    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dimension),
                    FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
                    FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=2048),
                    FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=512),
                ]
                schema = CollectionSchema(fields, description="校园知识库")
                client.create_collection(
                    collection_name=self.collection_name,
                    schema=schema,
                )
                logger.info("已创建集合: %s", self.collection_name)


class _MockEmbedModel:
    """Mock 模型（开发阶段无 sentence-transformers 时使用）"""

    def encode(self, text, **kwargs):
        import hashlib
        if isinstance(text, str):
            h = hashlib.md5(text.encode()).digest()
            vec = [float(b) / 255.0 for b in h]
            return vec + [0.0] * (1024 - len(vec))
        return [self.encode(t) for t in text]


class _InMemoryStore:
    """内存向量库 fallback（开发阶段无 pymilvus 时使用）"""

    def __init__(self):
        self._data = {}
        self._collection = "default"

    def insert(self, collection_name, data):
        self._collection = collection_name
        if collection_name not in self._data:
            self._data[collection_name] = {}
        for item in data:
            self._data[collection_name][item["id"]] = item

    def search(self, collection_name, data, limit, filter="", output_fields=None):
        items = self._data.get(collection_name, {}).values()
        if not items:
            return [[]]

        query_vec = data[0]
        scored = []
        for item in items:
            vec = item.get("vector", [])
            if len(vec) == len(query_vec):
                score = sum(a * b for a, b in zip(vec, query_vec))
                mag_a = sum(a * a for a in vec) ** 0.5
                mag_b = sum(a * a for a in query_vec) ** 0.5
                if mag_a > 0 and mag_b > 0:
                    score /= (mag_a * mag_b)
                scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        hits = []
        for score, item in scored[:limit]:
            entity = {k: item.get(k, "") for k in (output_fields or [])}
            hits.append({"distance": score, "entity": entity})
        return [hits]

    def has_collection(self, name):
        return name in self._data

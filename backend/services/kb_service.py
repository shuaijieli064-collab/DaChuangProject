"""知识库服务 — RAG 检索增强 + 原有 JSON 知识库 fallback"""
import json
import logging
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import KNOWLEDGE_BASE_PATH

from collections import Counter

logger = logging.getLogger(__name__)

# ---- 原有 JSON 知识库（fallback） ----
_KB_CACHE = {"mtime": None, "data": {}}

_STOP_WORDS = {
    "请问", "如何", "怎么", "怎样", "什么", "一下", "详细",
    "说明", "需要", "可以", "注意事项", "吗", "呢", "的",
}

# ---- RAG 组件（懒加载） ----
_RAG_CHAIN = None


def load_knowledge_base():
    """加载校园知识库（带文件变更缓存）"""
    if not os.path.exists(KNOWLEDGE_BASE_PATH):
        return {}
    try:
        mtime = os.path.getmtime(KNOWLEDGE_BASE_PATH)
    except OSError:
        return {}
    if _KB_CACHE["mtime"] == mtime and _KB_CACHE["data"]:
        return _KB_CACHE["data"]
    try:
        with open(KNOWLEDGE_BASE_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        logger.exception("知识库加载失败：%s", KNOWLEDGE_BASE_PATH)
        return {}
    _KB_CACHE["mtime"] = mtime
    _KB_CACHE["data"] = data
    return data


def _extract_keywords(query):
    query = (query or "").strip().lower()
    if not query:
        return []
    tokens = re.findall(r"[一-鿿]{2,}|[a-z0-9]{2,}", query)
    expanded = []
    for token in tokens:
        if re.fullmatch(r"[一-鿿]+", token) and len(token) > 4:
            for i in range(len(token) - 1):
                expanded.append(token[i : i + 2])
            expanded.append(token)
        else:
            expanded.append(token)
    filtered = [t for t in expanded if t not in _STOP_WORDS]
    if filtered:
        return filtered[:20]
    return [query[:20]]


def search_knowledge_json(query, category=None):
    """原有 JSON 关键词检索（保留为 fallback）"""
    kb = load_knowledge_base()
    if not kb:
        return []
    query = (query or "").strip().lower()
    if not query:
        return []
    keywords = _extract_keywords(query)
    target = kb.get(category, kb) if category and category in kb else kb
    scored_results = []

    def _search(data, path=""):
        if isinstance(data, dict):
            for key, val in data.items():
                _search(val, f"{path}/{key}" if path else key)
        elif isinstance(data, list):
            for item in data:
                _search(item, path)
        elif isinstance(data, str):
            haystack = data.lower()
            path_lower = path.lower()
            score = 0
            for kw in keywords:
                if kw in haystack:
                    score += 2
                if kw in path_lower:
                    score += 1
            if query in haystack:
                score += 3
            if score > 0:
                scored_results.append({"path": path, "content": data, "score": score})

    _search(target)
    seen = set()
    deduped = []
    for item in sorted(scored_results, key=lambda x: x["score"], reverse=True):
        key = (item["path"], item["content"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append({"path": item["path"], "content": item["content"]})
        if len(deduped) >= 5:
            break
    return deduped


def get_affair_info(affair_type):
    """获取特定事务的知识库内容"""
    kb = load_knowledge_base()
    affairs = kb.get("affairs", {})
    for key, val in affairs.items():
        if affair_type in key or key in affair_type:
            return val
    return None


def get_all_affair_types():
    """获取所有事务类型"""
    kb = load_knowledge_base()
    affairs = kb.get("affairs", {})
    return list(affairs.keys())


# ---- RAG 检索接口 ----

def _get_rag_chain():
    """懒加载 RAG 链"""
    global _RAG_CHAIN
    if _RAG_CHAIN is None:
        try:
            from services.vector_store import VectorStore
            from services.bm25 import BM25Search
            from services.rag_chain import RAGChain
            from config import RAG_ENABLED, MILVUS_URI, EMBEDDING_MODEL

            if RAG_ENABLED:
                vs = VectorStore(
                    collection_name="campus_knowledge",
                    embedding_model_name=EMBEDDING_MODEL,
                    milvus_uri=MILVUS_URI,
                )

                # 加载 BM25 索引
                bm25 = None
                bm25_path = KNOWLEDGE_BASE_PATH.replace(".json", "_bm25.json")
                if os.path.exists(bm25_path):
                    try:
                        with open(bm25_path, encoding="utf-8") as f:
                            bm25_data = json.load(f)
                        bm25 = BM25Search()
                        bm25._corpus = bm25_data.get("corpus", [])
                        bm25._doc_freq = Counter(bm25_data.get("doc_freq", {}))
                        bm25._doc_lengths = bm25_data.get("doc_lengths", [])
                        logger.info("BM25 索引已加载 (%d 篇)", len(bm25._corpus))
                    except Exception:
                        logger.exception("BM25 索引文件损坏，将不使用 BM25")
                else:
                    logger.info("BM25 索引不存在，请运行 seed_kb.py 生成")

                _RAG_CHAIN = RAGChain(vector_store=vs, bm25=bm25, top_k=5)
                logger.info("RAG 链路已初始化")
            else:
                _RAG_CHAIN = False
        except Exception:
            logger.exception("RAG 初始化失败，将使用 JSON fallback")
            _RAG_CHAIN = False
    return _RAG_CHAIN if _RAG_CHAIN else None


def search_knowledge_rag(query: str, top_k: int = 5) -> list[dict]:
    """RAG 向量检索"""
    chain = _get_rag_chain()
    if not chain:
        return []
    docs = chain.retrieve(query)
    return [{"content": d["content"], "source": d.get("source", ""), "score": d.get("score", 0)} for d in docs]


def search_knowledge(query, category=None, top_k=5):
    """统一检索入口 — 优先 RAG，fallback JSON"""
    # 尝试 RAG
    rag_results = search_knowledge_rag(query, top_k=top_k)
    if rag_results:
        return rag_results

    # Fallback 到原有 JSON 检索
    kb_results = search_knowledge_json(query, category)
    # 为 JSON 结果添加 source 字段以保持一致性
    for item in kb_results:
        item.setdefault("source", "campus_knowledge.json")
    return kb_results

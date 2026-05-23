"""将 campus_knowledge.json 种子数据导入 VectorStore 和 BM25 索引

用法:
    python backend/scripts/seed_kb.py
"""
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import KNOWLEDGE_BASE_PATH, MILVUS_URI, EMBEDDING_MODEL
from services.vector_store import VectorStore
from services.bm25 import BM25Search
from etl.loader import Chunk
from etl.splitter import TextSplitter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("seed_kb")


def flatten_json(data, prefix=""):
    """将嵌套 JSON 展平为 (key, text_content) 列表"""
    items = []
    if isinstance(data, dict):
        for key, val in data.items():
            new_key = f"{prefix}/{key}" if prefix else key
            if isinstance(val, dict):
                items.extend(flatten_json(val, new_key))
            elif isinstance(val, list):
                for i, item in enumerate(val):
                    items.extend(flatten_json(item, f"{new_key}[{i}]"))
            elif isinstance(val, str):
                items.append((new_key, val))
            else:
                items.append((new_key, str(val)))
    elif isinstance(data, list):
        for i, item in enumerate(data):
            items.extend(flatten_json(item, f"{prefix}[{i}]"))
    elif isinstance(data, str):
        items.append((prefix, data))
    return items


def seed_kb(
    kb_path: str = KNOWLEDGE_BASE_PATH,
    milvus_uri: str = MILVUS_URI,
    embedding_model: str = EMBEDDING_MODEL,
):
    """将 JSON 知识库导入 VectorStore + BM25"""
    if not os.path.exists(kb_path):
        logger.warning("知识库文件不存在: %s", kb_path)
        return

    logger.info("加载知识库: %s", kb_path)
    with open(kb_path, encoding="utf-8") as f:
        kb_data = json.load(f)

    # 展平 JSON 为文本条目
    flat_items = flatten_json(kb_data)
    logger.info("展平为 %d 条知识", len(flat_items))

    # 拼接为适合检索的文本格式
    documents = []
    for key, val in flat_items:
        text = f"{key}: {val}"
        documents.append({"content": text, "source": "campus_knowledge.json", "key": key})

    # 使用 TextSplitter 对长文本进行切片
    splitter = TextSplitter(chunk_size=800, chunk_overlap=100)
    chunks = []
    for doc in documents:
        chunk_docs = splitter.split_text(doc["content"])
        for i, chunk_text in enumerate(chunk_docs):
            chunk_id = f"{doc['key']}_{i}"
            chunks.append(Chunk(
                content=chunk_text,
                metadata={"source": doc["source"], "key": doc["key"]},
                chunk_id=chunk_id,
            ))

    if not chunks:
        logger.warning("没有可导入的文本块")
        return

    logger.info("共 %d 个文本块", len(chunks))

    # 导入 VectorStore
    store = VectorStore(
        collection_name="campus_knowledge",
        embedding_model_name=embedding_model,
        milvus_uri=milvus_uri,
    )
    store.ensure_collection(dimension=1024)

    texts = [c.content for c in chunks]
    embeddings = store.embed_texts(texts)
    store.add_documents(chunks, embeddings)
    logger.info("VectorStore 导入完成")

    # 构建 BM25 索引
    bm25 = BM25Search()
    bm25.add_documents(documents)
    logger.info("BM25 索引构建完成 (%d 篇)", len(documents))

    # 保存 BM25 索引（可选：序列化到文件）
    bm25_path = kb_path.replace(".json", "_bm25.json")
    bm25_data = {
        "corpus": bm25._corpus,
        "doc_freq": dict(bm25._doc_freq),
        "doc_lengths": bm25._doc_lengths,
    }
    with open(bm25_path, "w", encoding="utf-8") as f:
        json.dump(bm25_data, f, ensure_ascii=False, indent=2)
    logger.info("BM25 索引已保存至: %s", bm25_path)


if __name__ == "__main__":
    seed_kb()

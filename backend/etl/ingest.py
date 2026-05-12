#!/usr/bin/env python
"""ETL 数据入库脚本 — 将文档导入向量知识库

用法:
    python -m backend.etl.ingest backend/data/documents/
    python -m backend.etl.ingest file1.pdf file2.docx
"""
import glob
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.etl.loader import FileLoader
from backend.etl.splitter import TextSplitter
from backend.services.vector_store import VectorStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("etl.ingest")


def ingest(sources: list[str], collection: str = "campus_knowledge"):
    """执行入库 pipeline"""
    loader = FileLoader()
    splitter = TextSplitter(chunk_size=800, chunk_overlap=100)
    store = VectorStore(collection_name=collection)

    # 确保集合存在
    store.ensure_collection(dimension=1024)

    all_docs = []
    for src in sources:
        # 支持通配符
        paths = glob.glob(src) if "*" in src else [src]
        for path in paths:
            if not os.path.isfile(path):
                logger.warning("跳过不存在或不是文件: %s", path)
                continue
            logger.info("加载: %s", path)
            try:
                docs = loader.load(path)
                all_docs.extend(docs)
                logger.info("  → %d 篇文档", len(docs))
            except Exception:
                logger.exception("加载失败: %s", path)

    if not all_docs:
        logger.warning("未加载到任何文档")
        return

    # 切片
    logger.info("开始切片...")
    chunks = splitter.split_documents(all_docs)
    logger.info("  → %d 个 chunk", len(chunks))

    # 向量化
    logger.info("开始向量化...")
    texts = [c.content for c in chunks]
    embeddings = store.embed_texts(texts)
    logger.info("  → 维度: %d", len(embeddings[0]) if embeddings else 0)

    # 入库
    logger.info("写入向量库...")
    store.add_documents(chunks, embeddings)
    logger.info("入库完成 ✅")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python ingest.py <文件或目录路径...>")
        print("示例: python ingest.py data/pdfs/*.pdf data/docs/*.docx")
        sys.exit(1)

    ingest(sys.argv[1:])

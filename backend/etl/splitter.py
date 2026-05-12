import logging
import re
from dataclasses import dataclass, field

from .loader import Document, Chunk

logger = logging.getLogger(__name__)


@dataclass
class TextSplitter:
    """文本切片器 — 基于 LangChain RecursiveCharacterTextSplitter 理念"""
    chunk_size: int = 800
    chunk_overlap: int = 100
    separators: list[str] = field(default_factory=lambda: [
        "\n\n",  # 段落
        "\n",    # 换行
        "。",    # 中文句号
        "！",    # 中文感叹号
        "？",    # 中文问号
        "；",    # 中文分号
        "，",    # 中文逗号
        " ",     # 英文空格
        "",      # 逐字
    ])

    def split_documents(self, documents: list[Document]) -> list[Chunk]:
        """将文档列表切分为 Chunk 列表"""
        chunks = []
        for doc in documents:
            doc_chunks = self.split_text(doc.content)
            for i, text in enumerate(doc_chunks):
                if not text.strip():
                    continue
                chunk_id = f"{doc.source}_{i}"
                metadata = {**doc.metadata, "chunk_index": i, "chunk_id": chunk_id}
                chunks.append(Chunk(content=text.strip(), metadata=metadata, chunk_id=chunk_id))
        return chunks

    def split_text(self, text: str) -> list[str]:
        """递归切分文本"""
        if len(text) <= self.chunk_size:
            return [text]

        # 尝试按分隔符切分
        for sep in self.separators:
            if not sep:
                continue
            parts = text.split(sep)
            if len(parts) > 1:
                chunks = self._merge_parts(parts, sep)
                if chunks:
                    return chunks

        # 兜底：按 chunk_size 硬切
        return self._hard_split(text)

    def _merge_parts(self, parts: list[str], sep: str) -> list[str]:
        """合并部分为不超过 chunk_size 的块"""
        chunks = []
        current = ""
        for part in parts:
            candidate = (current + sep + part).strip() if current else part
            if len(candidate) <= self.chunk_size:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                if len(part) <= self.chunk_size:
                    current = part
                else:
                    current = ""
                    chunks.extend(self._hard_split(part))
        if current:
            chunks.append(current)
        return chunks

    def _hard_split(self, text: str) -> list[str]:
        """按固定长度硬切，带 overlap"""
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start += self.chunk_size - self.chunk_overlap
        return chunks

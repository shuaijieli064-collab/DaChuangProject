import re
from collections import Counter
from math import log


class BM25Search:
    """BM25 关键词检索 — 用于混合搜索的关键词召回层"""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self._corpus = []
        self._doc_freq = Counter()
        self._doc_lengths = []

    def add_documents(self, documents: list[dict]):
        """建立索引"""
        for doc in documents:
            tokens = self._tokenize(doc["content"])
            self._corpus.append(doc)
            self._doc_lengths.append(len(tokens))
            unique_tokens = set(tokens)
            for token in unique_tokens:
                self._doc_freq[token] += 1

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """检索"""
        query_tokens = self._tokenize(query)
        n = len(self._corpus)
        if n == 0:
            return []

        avg_dl = sum(self._doc_lengths) / n if self._doc_lengths else 1
        scores = []

        for i, doc in enumerate(self._corpus):
            doc_tokens = self._tokenize(doc["content"])
            doc_len = self._doc_lengths[i]
            score = 0.0

            for token in query_tokens:
                if token not in self._doc_freq:
                    continue
                df = self._doc_freq[token]
                idf = log((n - df + 0.5) / (df + 0.5) + 1.0)

                tf = doc_tokens.count(token)
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / avg_dl)
                score += idf * numerator / denominator

            if score > 0:
                scores.append((score, doc))

        scores.sort(key=lambda x: x[0], reverse=True)
        return [{"content": d["content"], "score": s, **d} for s, d in scores[:top_k]]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """中文分词（简单实现：按字符/词切片）"""
        text = re.sub(r"[^\w一-鿿]", " ", text.lower())
        tokens = [t for t in text.split() if len(t) > 1]
        # 中文双字切片
        for match in re.finditer(r"[一-鿿]{2,}", text):
            word = match.group()
            for i in range(len(word) - 1):
                tokens.append(word[i : i + 2])
        return tokens

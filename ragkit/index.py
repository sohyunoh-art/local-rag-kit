"""BM25 인덱스. 컬렉션별 JSON으로 영속화. 임베딩/벡터DB 없이 완전 로컬로 동작."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from .chunking import tokenize

_K1 = 1.5
_B = 0.75


@dataclass
class Chunk:
    text: str
    metadata: dict = field(default_factory=dict)


@dataclass
class SearchHit:
    chunk: Chunk
    score: float


class Index:
    """토큰화된 chunk들에 대한 BM25 검색 인덱스."""

    def __init__(self) -> None:
        self.chunks: list[Chunk] = []
        self._doc_tokens: list[list[str]] = []  # chunk별 토큰 (재저장/재계산용)

    # ---- 빌드 ----
    def add(self, chunks: list[Chunk]) -> int:
        for ch in chunks:
            self.chunks.append(ch)
            self._doc_tokens.append(tokenize(ch.text))
        return len(chunks)

    def __len__(self) -> int:
        return len(self.chunks)

    def remove_by_source(self, sources: set[str]) -> int:
        """주어진 source(파일경로)에 속한 chunk를 모두 제거. 같은 파일 재색인을 멱등하게 만든다."""
        if not sources:
            return 0
        keep_idx = [
            i for i, c in enumerate(self.chunks)
            if c.metadata.get("source") not in sources
        ]
        removed = len(self.chunks) - len(keep_idx)
        self.chunks = [self.chunks[i] for i in keep_idx]
        self._doc_tokens = [self._doc_tokens[i] for i in keep_idx]
        return removed

    # ---- 검색 ----
    def _stats(self):
        n = len(self.chunks)
        doc_len = [len(t) for t in self._doc_tokens]
        avgdl = (sum(doc_len) / n) if n else 0.0
        df: dict[str, int] = {}
        for toks in self._doc_tokens:
            for term in set(toks):
                df[term] = df.get(term, 0) + 1
        return n, doc_len, avgdl, df

    def search(self, query: str, k: int = 5) -> list[SearchHit]:
        if not self.chunks:
            return []
        q_terms = set(tokenize(query))
        if not q_terms:
            return []

        n, doc_len, avgdl, df = self._stats()
        scores: list[float] = []
        for i, toks in enumerate(self._doc_tokens):
            tf: dict[str, int] = {}
            for t in toks:
                if t in q_terms:
                    tf[t] = tf.get(t, 0) + 1
            score = 0.0
            for term, f in tf.items():
                idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
                denom = f + _K1 * (1 - _B + _B * (doc_len[i] / avgdl if avgdl else 0))
                score += idf * (f * (_K1 + 1)) / (denom or 1)
            scores.append(score)

        ranked = sorted(range(n), key=lambda i: scores[i], reverse=True)
        hits = [SearchHit(self.chunks[i], scores[i]) for i in ranked if scores[i] > 0]
        return hits[:k]

    # ---- 영속화 ----
    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "chunks": [{"text": c.text, "metadata": c.metadata} for c in self.chunks],
        }
        p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "Index":
        p = Path(path)
        data = json.loads(p.read_text(encoding="utf-8"))
        idx = cls()
        idx.add([Chunk(text=c["text"], metadata=c.get("metadata", {})) for c in data["chunks"]])
        return idx

"""ingest / ask 오케스트레이션 + 컬렉션 분리."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import answerer, config, loaders
from .chunking import chunk_text
from .index import Chunk, Index, SearchHit


@dataclass
class IngestResult:
    collection: str
    files: int
    documents: int
    chunks: int
    index_path: str


@dataclass
class AskResult:
    answer: str
    backend: str
    sources: list[SearchHit]


def _markdown(path: str) -> bool:
    return Path(path).suffix.lower() in {".md", ".markdown"}


def ingest(
    collection: str,
    paths: list[str],
    *,
    max_chars: int = config.DEFAULT_MAX_CHARS,
    overlap: int = config.DEFAULT_OVERLAP,
    reset: bool = False,
) -> IngestResult:
    """경로(파일/디렉터리)들을 로드→청킹→인덱스에 추가하고 컬렉션에 저장한다."""
    idx_path = config.index_path(collection)
    if reset or not idx_path.exists():
        index = Index()
    else:
        index = Index.load(idx_path)

    file_set: set[str] = set()
    doc_count = 0
    new_chunks: list[Chunk] = []

    for path in paths:
        for doc in loaders.load_path(path):
            doc_count += 1
            file_set.add(doc.metadata.get("source", path))
            for piece in chunk_text(
                doc.text,
                max_chars=max_chars,
                overlap=overlap,
                is_markdown=_markdown(doc.metadata.get("source", "")),
            ):
                new_chunks.append(Chunk(text=piece, metadata=dict(doc.metadata)))

    # 같은 파일을 다시 색인하면 기존 chunk를 교체(멱등). reset=True면 위에서 이미 비워짐.
    if not reset:
        index.remove_by_source(file_set)
    added = index.add(new_chunks)
    index.save(idx_path)
    return IngestResult(
        collection=collection,
        files=len(file_set),
        documents=doc_count,
        chunks=added,
        index_path=str(idx_path),
    )


def ask(
    collection: str,
    question: str,
    *,
    k: int = config.DEFAULT_TOP_K,
    backend: str = config.DEFAULT_BACKEND,
) -> AskResult:
    idx_path = config.index_path(collection)
    if not idx_path.exists():
        raise FileNotFoundError(
            f"컬렉션 '{collection}' 인덱스가 없습니다. 먼저 ingest 하세요: {idx_path}"
        )
    index = Index.load(idx_path)
    hits = index.search(question, k=k)
    text, used = answerer.answer(question, hits, backend=backend)
    return AskResult(answer=text, backend=used, sources=hits)


def list_collections() -> list[dict]:
    root = config.collections_dir()
    if not root.exists():
        return []
    out = []
    for child in sorted(root.iterdir()):
        idx = child / "index.json"
        if idx.exists():
            try:
                count = len(Index.load(idx))
            except Exception:
                count = -1
            out.append({"name": child.name, "chunks": count})
    return out

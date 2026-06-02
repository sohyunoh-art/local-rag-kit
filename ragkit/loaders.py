"""범용 문서 로더. 확장자 레지스트리로 PDF·마크다운·txt 를 (text, metadata) 로 읽는다.

새 포맷 추가는 register(".ext", fn) 한 줄이면 된다 — 범용성의 핵심.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


@dataclass
class Document:
    text: str
    metadata: dict = field(default_factory=dict)


# 확장자 -> 로더 함수 (Path -> list[Document])
_REGISTRY: dict[str, Callable[[Path], list[Document]]] = {}


def register(ext: str, fn: Callable[[Path], list[Document]]) -> None:
    _REGISTRY[ext.lower()] = fn


def supported_extensions() -> list[str]:
    return sorted(_REGISTRY)


def _load_text_file(path: Path) -> list[Document]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return [Document(text=text, metadata={"source": str(path), "section": path.stem})]


def _load_pdf(path: Path) -> list[Document]:
    try:
        import fitz  # PyMuPDF
    except ImportError as e:  # pragma: no cover - 환경 의존
        raise RuntimeError(
            "PDF를 읽으려면 PyMuPDF가 필요합니다: pip install PyMuPDF"
        ) from e

    docs: list[Document] = []
    with fitz.open(path) as pdf:
        for i, page in enumerate(pdf):
            text = page.get_text("text").strip()
            if not text:
                continue
            docs.append(
                Document(
                    text=text,
                    metadata={"source": str(path), "page": i + 1},
                )
            )
    return docs


register(".txt", _load_text_file)
register(".md", _load_text_file)
register(".markdown", _load_text_file)
register(".pdf", _load_pdf)


def load_file(path: str | Path) -> list[Document]:
    p = Path(path)
    fn = _REGISTRY.get(p.suffix.lower())
    if fn is None:
        raise ValueError(
            f"지원하지 않는 확장자 '{p.suffix}'. 지원: {supported_extensions()}"
        )
    return fn(p)


def load_path(path: str | Path) -> list[Document]:
    """파일이면 그 파일을, 디렉터리면 지원 확장자 파일을 재귀적으로 모두 읽는다."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"경로를 찾을 수 없습니다: {p}")
    if p.is_file():
        return load_file(p)

    docs: list[Document] = []
    for child in sorted(p.rglob("*")):
        if child.is_file() and child.suffix.lower() in _REGISTRY:
            docs.extend(load_file(child))
    return docs

"""경로·기본값 설정. 컬렉션 데이터는 repo 밖(홈 디렉터리)에 저장해 프로젝트를 오염시키지 않는다."""

from __future__ import annotations

import os
from pathlib import Path


def home_dir() -> Path:
    """모든 컬렉션이 저장되는 루트. RAGKIT_HOME 으로 덮어쓸 수 있다."""
    env = os.environ.get("RAGKIT_HOME")
    base = Path(env).expanduser() if env else Path.home() / ".local-rag-kit"
    return base


def collections_dir() -> Path:
    return home_dir() / "collections"


def default_collection() -> str:
    """--collection 을 생략했을 때 쓸 컬렉션. RAGKIT_COLLECTION 으로 바꾼다."""
    return os.environ.get("RAGKIT_COLLECTION", "default")


def collection_dir(name: str) -> Path:
    safe = name.strip().replace("/", "_").replace("\\", "_")
    if not safe:
        raise ValueError("컬렉션 이름이 비어 있습니다.")
    return collections_dir() / safe


def index_path(name: str) -> Path:
    return collection_dir(name) / "index.json"


# 청킹 기본값
DEFAULT_MAX_CHARS = 1200
DEFAULT_OVERLAP = 150

# 검색 기본값
DEFAULT_TOP_K = 5

# 답변 백엔드 기본값
DEFAULT_BACKEND = "auto"  # auto -> ollama -> claude_cli -> echo
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")

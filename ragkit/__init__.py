"""local-rag-kit: 목적마다 복사하지 않는 범용 로컬 RAG 엔진.

데이터 폴더 + 컬렉션 이름만 바꾸면 새 목적의 RAG가 된다.
기본은 외부 API/모델 다운로드 없이 도는 BM25 토큰 검색이고,
원하면 Ollama 백엔드로 완전 오프라인 LLM 답변을 붙일 수 있다.
"""

__version__ = "0.1.0"

from .pipeline import ingest, ask  # noqa: E402,F401

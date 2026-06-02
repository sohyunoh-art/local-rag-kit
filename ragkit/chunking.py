"""순수 함수 청킹 + 토크나이저. 모델/네트워크 의존이 전혀 없어 오프라인·테스트에 적합."""

from __future__ import annotations

import re

from .config import DEFAULT_MAX_CHARS, DEFAULT_OVERLAP

# 한글(가-힣) + 영숫자 토큰. \w 대신 명시적으로 잡아 언어 경계를 안정화한다.
_TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣]+")
_HANGUL_RE = re.compile(r"[가-힣]")
_HEADING_RE = re.compile(r"^#{1,6}\s", re.MULTILINE)


def _is_hangul(token: str) -> bool:
    return bool(_HANGUL_RE.search(token))


def tokenize(text: str) -> list[str]:
    """검색용 토큰. 한글 단어는 bigram으로 확장해 형태소 분석기 없이도 부분 매칭이 된다.

    예) '데이터셋' -> ['데이터셋', '데이', '이터', '터셋']
    덕분에 '데이터셋' 질의가 '데이터셋 코드 체계' 문서에 매칭된다.
    """
    tokens: list[str] = []
    for raw in _TOKEN_RE.findall(text.lower()):
        if _is_hangul(raw):
            tokens.append(raw)  # 정확 매칭용 원형
            if len(raw) >= 2:
                tokens.extend(raw[i : i + 2] for i in range(len(raw) - 1))  # bigram
        else:
            tokens.append(raw)
    return tokens


def _split_by_size(text: str, max_chars: int, overlap: int) -> list[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []

    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + max_chars, n)
        # 문장/공백 경계에서 가급적 끊는다
        if end < n:
            window = text[start:end]
            cut = max(window.rfind("\n"), window.rfind(". "), window.rfind(" "))
            if cut > max_chars * 0.5:
                end = start + cut + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return chunks


def chunk_text(
    text: str,
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap: int = DEFAULT_OVERLAP,
    is_markdown: bool = False,
) -> list[str]:
    """텍스트를 검색 단위 chunk로 나눈다.

    마크다운이면 헤딩(#) 경계를 우선 존중한 뒤, 너무 긴 섹션만 크기 기준으로 다시 쪼갠다.
    """
    text = (text or "").strip()
    if not text:
        return []

    if is_markdown and _HEADING_RE.search(text):
        sections: list[str] = []
        last = 0
        for m in _HEADING_RE.finditer(text):
            if m.start() > last:
                sections.append(text[last : m.start()])
            last = m.start()
        sections.append(text[last:])
        chunks: list[str] = []
        for sec in sections:
            chunks.extend(_split_by_size(sec, max_chars, overlap))
        return [c for c in chunks if c]

    return _split_by_size(text, max_chars, overlap)

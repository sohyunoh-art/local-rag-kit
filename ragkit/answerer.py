"""교체 가능한 답변 백엔드. echo(오프라인/테스트) · ollama(완전 로컬 LLM) · claude_cli.

auto 는 ollama -> claude_cli -> echo 순으로 사용 가능한 첫 백엔드를 고른다.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import urllib.error
import urllib.request

from .config import OLLAMA_MODEL, OLLAMA_URL
from .index import SearchHit

_SYSTEM = (
    "너는 주어진 컨텍스트만 근거로 한국어로 답하는 어시스턴트다. "
    "컨텍스트에 없는 내용은 추측하지 말고 '제공된 자료에는 없습니다'라고 답하라. "
    "가능하면 답변 끝에 근거 출처를 함께 밝혀라."
)


def format_source(metadata: dict) -> str:
    src = metadata.get("source", "?")
    if "page" in metadata:
        return f"{src}#p{metadata['page']}"
    if "section" in metadata:
        return f"{src}#{metadata['section']}"
    return str(src)


def build_prompt(question: str, hits: list[SearchHit]) -> str:
    blocks = []
    for i, h in enumerate(hits, 1):
        blocks.append(f"[{i}] ({format_source(h.chunk.metadata)})\n{h.chunk.text}")
    context = "\n\n".join(blocks) if blocks else "(검색된 컨텍스트 없음)"
    return f"{_SYSTEM}\n\n# 컨텍스트\n{context}\n\n# 질문\n{question}\n\n# 답변\n"


# ---- 백엔드 구현 ----
def _answer_echo(question: str, hits: list[SearchHit]) -> str:
    """LLM 없이 검색 결과를 요약 제시. 오프라인 데모 및 테스트용."""
    if not hits:
        return "제공된 자료에는 관련 내용이 없습니다."
    lines = [f"질문 '{question}' 에 대한 근거 {len(hits)}건:"]
    for i, h in enumerate(hits, 1):
        snippet = " ".join(h.chunk.text.split())[:200]
        lines.append(f"  [{i}] ({format_source(h.chunk.metadata)}) {snippet}")
    return "\n".join(lines)


def _ollama_available() -> bool:
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=1.5):
            return True
    except (urllib.error.URLError, OSError):
        return False


def _answer_ollama(question: str, hits: list[SearchHit]) -> str:
    prompt = build_prompt(question, hits)
    body = json.dumps(
        {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate", data=body, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("response", "").strip() or "(빈 응답)"
    except (urllib.error.URLError, OSError) as e:
        raise RuntimeError(
            f"Ollama 호출 실패 ({OLLAMA_URL}, 모델={OLLAMA_MODEL}). "
            f"`ollama serve` 와 `ollama pull {OLLAMA_MODEL}` 를 확인하세요. 원인: {e}"
        ) from e


def _claude_cli_available() -> bool:
    return shutil.which("claude") is not None


def _answer_claude_cli(question: str, hits: list[SearchHit]) -> str:
    prompt = build_prompt(question, hits)
    try:
        out = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=180,
        )
    except FileNotFoundError as e:
        raise RuntimeError("claude CLI 를 찾을 수 없습니다.") from e
    if out.returncode != 0:
        raise RuntimeError(f"claude CLI 오류: {out.stderr.strip()}")
    return out.stdout.strip() or "(빈 응답)"


_BACKENDS = {
    "echo": _answer_echo,
    "ollama": _answer_ollama,
    "claude_cli": _answer_claude_cli,
}


def resolve_backend(backend: str) -> str:
    """'auto' 를 실제 사용 가능한 백엔드 이름으로 해석한다."""
    if backend != "auto":
        if backend not in _BACKENDS:
            raise ValueError(f"알 수 없는 backend '{backend}'. 가능: {sorted(_BACKENDS)} 또는 auto")
        return backend
    if _ollama_available():
        return "ollama"
    if _claude_cli_available():
        return "claude_cli"
    return "echo"


def answer(question: str, hits: list[SearchHit], backend: str = "auto") -> tuple[str, str]:
    """(답변, 실제로 사용된 backend) 를 돌려준다."""
    resolved = resolve_backend(backend)
    return _BACKENDS[resolved](question, hits), resolved

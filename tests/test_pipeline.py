import pytest

from ragkit import pipeline
from ragkit.answerer import answer, build_prompt, resolve_backend
from ragkit.index import Chunk


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """컬렉션 저장소를 임시 디렉터리로 격리 (실제 홈 오염 방지)."""
    monkeypatch.setenv("RAGKIT_HOME", str(tmp_path / "ragkit_home"))
    # config 의 home_dir 는 매 호출 환경변수를 읽으므로 추가 리로드 불필요


def _write(p, text):
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_ingest_then_ask_roundtrip(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    _write(docs / "guide.md", "# 환불 정책\n구매 후 7일 이내 환불이 가능하다.")
    _write(docs / "misc.md", "# 잡담\n날씨가 좋다.")

    res = pipeline.ingest("test_col", [str(docs)])
    assert res.chunks >= 2
    assert res.files == 2

    ans = pipeline.ask("test_col", "환불 기간은?", backend="echo")
    assert ans.sources, "검색 결과가 있어야 함"
    assert "환불" in ans.sources[0].chunk.text
    assert ans.backend == "echo"


def test_collections_are_isolated(tmp_path):
    a = tmp_path / "a.md"
    b = tmp_path / "b.md"
    _write(a, "# A\n알파 컬렉션 전용 내용")
    _write(b, "# B\n베타 컬렉션 전용 내용")

    pipeline.ingest("alpha", [str(a)])
    pipeline.ingest("beta", [str(b)])

    hit_a = pipeline.ask("alpha", "알파", backend="echo").sources
    hit_b = pipeline.ask("beta", "베타", backend="echo").sources
    assert all("알파" in h.chunk.text for h in hit_a)
    assert all("베타" in h.chunk.text for h in hit_b)


def test_reingest_same_file_is_idempotent(tmp_path):
    f = tmp_path / "doc.md"
    _write(f, "# 정책\n환불은 7일 이내 가능하다.")
    r1 = pipeline.ingest("idem", [str(f)])
    r2 = pipeline.ingest("idem", [str(f)])  # 같은 파일 재색인
    from ragkit.index import Index
    from ragkit import config
    total = len(Index.load(config.index_path("idem")))
    # 두 번 넣어도 chunk 총량이 1회분과 같아야 한다 (중복 누적 금지)
    assert total == r1.chunks == r2.chunks


def test_ask_missing_collection_raises():
    with pytest.raises(FileNotFoundError):
        pipeline.ask("nope", "질문", backend="echo")


def test_resolve_backend_unknown_raises():
    with pytest.raises(ValueError):
        resolve_backend("magic")


def test_build_prompt_includes_sources_and_guard():
    hits = []
    from ragkit.index import SearchHit
    hits.append(SearchHit(Chunk("내용", {"source": "x.md", "page": 3}), 1.0))
    prompt = build_prompt("질문?", hits)
    assert "x.md#p3" in prompt
    assert "추측하지" in prompt  # 컨텍스트 밖이면 모른다고 답하라는 가드


def test_echo_backend_no_external_deps():
    from ragkit.index import SearchHit
    hits = [SearchHit(Chunk("환불은 7일 이내", {"source": "g.md", "section": "환불"}), 2.0)]
    text, used = answer("환불?", hits, backend="echo")
    assert used == "echo"
    assert "환불" in text

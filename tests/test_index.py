from ragkit.index import Chunk, Index


def _sample_index():
    idx = Index()
    idx.add([
        Chunk("데이터셋 코드 체계는 프로젝트별로 부여된다", {"source": "a.md", "section": "코드"}),
        Chunk("검수 프로세스는 1차 라벨링 후 2차 검토로 진행된다", {"source": "b.md", "section": "검수"}),
        Chunk("오늘 점심은 김치찌개였다", {"source": "c.md", "section": "잡담"}),
    ])
    return idx


def test_relevant_chunk_ranks_first():
    idx = _sample_index()
    hits = idx.search("데이터셋 코드", k=3)
    assert hits, "검색 결과가 비어 있으면 안 됨"
    assert hits[0].chunk.metadata["section"] == "코드"


def test_irrelevant_query_scores_low_or_empty():
    idx = _sample_index()
    hits = idx.search("우주 로켓 발사", k=3)
    # 무관 질의는 매칭이 없어야 한다
    assert hits == []


def test_save_load_roundtrip_reproduces_scores(tmp_path):
    idx = _sample_index()
    p = tmp_path / "col" / "index.json"
    idx.save(p)
    loaded = Index.load(p)
    assert len(loaded) == len(idx)
    a = idx.search("검수 프로세스", k=2)
    b = loaded.search("검수 프로세스", k=2)
    assert [h.chunk.text for h in a] == [h.chunk.text for h in b]
    assert abs(a[0].score - b[0].score) < 1e-9

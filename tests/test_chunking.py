from ragkit.chunking import chunk_text, tokenize


def test_chunk_size_and_overlap():
    text = "가" * 3000
    chunks = chunk_text(text, max_chars=1000, overlap=100)
    assert len(chunks) >= 3
    assert all(len(c) <= 1000 for c in chunks)


def test_short_text_single_chunk():
    assert chunk_text("짧은 글") == ["짧은 글"]
    assert chunk_text("   ") == []


def test_markdown_respects_headings():
    md = "# 제목1\n내용 A\n\n# 제목2\n내용 B"
    chunks = chunk_text(md, is_markdown=True, max_chars=1000)
    joined = "\n".join(chunks)
    assert "제목1" in joined and "제목2" in joined
    # 헤딩 경계로 최소 2개 이상으로 분리
    assert len(chunks) >= 2


def test_hangul_bigram_partial_match():
    toks = tokenize("데이터셋 코드 체계")
    # 원형 + bigram 모두 포함되어 부분 매칭 가능
    assert "데이터셋" in toks
    assert "데이" in toks and "이터" in toks


def test_tokenize_mixed_language():
    toks = tokenize("RAG v1.6 검색")
    assert "rag" in toks
    assert "검색" in toks

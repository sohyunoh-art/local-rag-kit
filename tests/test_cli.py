import pytest

from ragkit import cli, config


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("RAGKIT_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("RAGKIT_COLLECTION", raising=False)


def test_default_collection_fallback(monkeypatch):
    monkeypatch.delenv("RAGKIT_COLLECTION", raising=False)
    assert config.default_collection() == "default"


def test_default_collection_env_override(monkeypatch):
    monkeypatch.setenv("RAGKIT_COLLECTION", "법률")
    assert config.default_collection() == "법률"


def test_ask_uses_default_collection_when_omitted(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("RAGKIT_COLLECTION", "demo")
    doc = tmp_path / "d.md"
    doc.write_text("# 환불\n환불은 7일 이내 가능하다.", encoding="utf-8")
    # -c 없이 ingest -> 기본 컬렉션 'demo' 로 들어가야 함
    assert cli.main(["ingest", str(doc)]) == 0
    # -c 없이 ask -> 같은 기본 컬렉션에서 답해야 함
    assert cli.main(["ask", "환불 기간", "--backend", "echo"]) == 0
    out = capsys.readouterr().out
    assert "환불" in out
    assert "--- 출처 ---" in out  # 출처는 기본 표시


def test_no_sources_flag_suppresses_sources(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("RAGKIT_COLLECTION", "demo")
    doc = tmp_path / "d.md"
    doc.write_text("환불은 7일 이내", encoding="utf-8")
    cli.main(["ingest", str(doc)])
    cli.main(["ask", "환불", "--backend", "echo", "--no-sources"])
    out = capsys.readouterr().out
    assert "--- 출처 ---" not in out


def test_interactive_mode_loops_until_blank(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("RAGKIT_COLLECTION", "demo")
    doc = tmp_path / "d.md"
    doc.write_text("환불은 7일 이내 가능", encoding="utf-8")
    cli.main(["ingest", str(doc)])
    # 둘 다 문서에 있는 단어로 질문 -> 두 번 모두 근거가 잡혀야 함. 빈 줄로 종료.
    inputs = iter(["환불", "이내", ""])
    monkeypatch.setattr("builtins.input", lambda _="": next(inputs))
    assert cli.main(["ask", "--backend", "echo"]) == 0
    out = capsys.readouterr().out
    assert out.count("--- 출처 ---") == 2  # 두 질문 모두 답+출처

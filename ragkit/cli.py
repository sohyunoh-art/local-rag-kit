"""CLI: ingest / ask / list / info.

예) (설치 후엔 `python -m ragkit.cli` 대신 그냥 `ragkit` 또는 `./rag`)
  ragkit ingest -c 법률 ./docs/legal        # 컬렉션에 색인
  ragkit ask "환불 기간"                     # 컬렉션 생략 -> 기본 컬렉션, 출처도 기본 표시
  ragkit ask -c 법률 "계약 해지 조건은?"      # 컬렉션 지정
  ragkit ask -c 법률                         # 질문 생략 -> 대화형 모드 (계속 질문)
  ragkit list
  ragkit info -c 법률

기본 컬렉션은 RAGKIT_COLLECTION 환경변수로 바꾼다 (없으면 'default').
"""

from __future__ import annotations

import argparse
import sys

from . import config, pipeline
from .answerer import format_source


def _cmd_ingest(args: argparse.Namespace) -> int:
    res = pipeline.ingest(
        args.collection,
        args.paths,
        max_chars=args.max_chars,
        overlap=args.overlap,
        reset=args.reset,
    )
    print(
        f"[ingest] 컬렉션='{res.collection}'  파일 {res.files}개 / 문서 {res.documents}개 "
        f"-> chunk {res.chunks}개 추가"
    )
    print(f"         인덱스: {res.index_path}")
    return 0


def _print_answer(res, show_sources: bool) -> None:
    print(res.answer)
    if show_sources and res.sources:
        print("\n--- 출처 ---")
        for i, hit in enumerate(res.sources, 1):
            print(f"  [{i}] {format_source(hit.chunk.metadata)}  (score={hit.score:.3f})")
    print(f"\n(backend: {res.backend})", file=sys.stderr)


def _cmd_ask(args: argparse.Namespace) -> int:
    show_sources = not args.no_sources
    if args.question is not None:
        res = pipeline.ask(args.collection, args.question, k=args.k, backend=args.backend)
        _print_answer(res, show_sources)
        return 0

    # 질문 생략 -> 대화형 모드: 한 번 켜고 계속 묻는다 (빈 줄/exit/quit/Ctrl-D로 종료)
    print(f"[대화형] 컬렉션 '{args.collection}'. 질문을 입력하세요 (종료: 빈 줄 또는 exit).")
    while True:
        try:
            q = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not q or q.lower() in {"exit", "quit", "q"}:
            break
        try:
            res = pipeline.ask(args.collection, q, k=args.k, backend=args.backend)
        except FileNotFoundError as e:
            print(e, file=sys.stderr)
            break
        _print_answer(res, show_sources)
    return 0


def _cmd_list(_: argparse.Namespace) -> int:
    cols = pipeline.list_collections()
    if not cols:
        print(f"컬렉션이 없습니다. ({config.collections_dir()})")
        return 0
    print(f"컬렉션 ({config.collections_dir()}):")
    for c in cols:
        print(f"  - {c['name']:20}  chunks={c['chunks']}")
    return 0


def _cmd_info(args: argparse.Namespace) -> int:
    path = config.index_path(args.collection)
    if not path.exists():
        print(f"컬렉션 '{args.collection}' 없음: {path}")
        return 1
    from .index import Index

    idx = Index.load(path)
    print(f"컬렉션 '{args.collection}': chunk {len(idx)}개")
    print(f"  인덱스: {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ragkit", description="범용 로컬 RAG 엔진")
    sub = p.add_subparsers(dest="command", required=True)

    default_col = config.default_collection()

    pi = sub.add_parser("ingest", help="문서를 컬렉션에 색인")
    pi.add_argument("--collection", "-c", default=default_col,
                    help=f"기본: {default_col}")
    pi.add_argument("paths", nargs="+", help="파일 또는 디렉터리")
    pi.add_argument("--max-chars", type=int, default=config.DEFAULT_MAX_CHARS)
    pi.add_argument("--overlap", type=int, default=config.DEFAULT_OVERLAP)
    pi.add_argument("--reset", action="store_true", help="기존 인덱스 무시하고 새로 만듦")
    pi.set_defaults(func=_cmd_ingest)

    pa = sub.add_parser("ask", help="컬렉션에 질문 (질문 생략 시 대화형)")
    pa.add_argument("--collection", "-c", default=default_col,
                    help=f"기본: {default_col}")
    pa.add_argument("question", nargs="?", default=None,
                    help="생략하면 대화형 모드")
    pa.add_argument("-k", type=int, default=config.DEFAULT_TOP_K)
    pa.add_argument("--backend", default=config.DEFAULT_BACKEND,
                    choices=["auto", "echo", "ollama", "claude_cli"])
    pa.add_argument("--no-sources", action="store_true", help="출처 표시 끄기 (기본은 표시)")
    pa.set_defaults(func=_cmd_ask)

    pl = sub.add_parser("list", help="컬렉션 목록")
    pl.set_defaults(func=_cmd_list)

    pf = sub.add_parser("info", help="컬렉션 상세")
    pf.add_argument("--collection", "-c", default=default_col, help=f"기본: {default_col}")
    pf.set_defaults(func=_cmd_info)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

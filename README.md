# local-rag-kit

**목적마다 통째로 복사하지 않는 범용 로컬 RAG 엔진.**
데이터 폴더 + 컬렉션 이름만 바꾸면 새 목적의 RAG가 된다.

`navlue-spec-rag`, `outline-rag-assistant` 처럼 목적마다 프로젝트를 통째로 복제하던 걸, **엔진 하나에 컬렉션만 나누는** 방식으로 일반화했다.

```
[문서 폴더] --ingest--> [컬렉션별 BM25 인덱스] --ask--> [검색 → 답변 백엔드]
   PDF/MD/txt              ~/.local-rag-kit/...           echo / ollama / claude_cli
```

## 왜 "완전 로컬"인가

- 검색 엔진(청킹·토큰화·BM25)은 **표준 라이브러리만으로** 동작한다. 임베딩 모델 다운로드도, GPU도, 외부 API도 필요 없다.
- 색인이 곧 "학습"이다. 데이터를 다시 넣으면 즉시 반영된다(재학습/파인튜닝 불필요).
- 답변 생성 LLM이 필요하면 **Ollama**(완전 오프라인) 또는 로컬 `claude` CLI 를 골라 붙인다. 둘 다 없으면 `echo`(검색 근거만 요약)로도 동작한다.

## 설치 (어디서나 쓰는 `ragkit` 명령)

한 번 설치하면 **어느 폴더에서든** `ragkit` 명령을 쓸 수 있다. 컬렉션 데이터는 프로젝트가 아니라 `~/.local-rag-kit` 에 쌓이기 때문에 설치 후엔 프로젝트 폴더가 어디 있든 상관없다.

```bash
# GitHub 저장소에서 바로 설치
pip install "git+https://github.com/sohyunoh-art/local-rag-kit.git"

# 또는 클론 후 설치
git clone https://github.com/sohyunoh-art/local-rag-kit.git
pip install ./local-rag-kit

# CLI 도구로 격리 설치하고 싶으면 pipx 권장
pipx install "git+https://github.com/sohyunoh-art/local-rag-kit.git"
```

> PEP 668(외부 관리형 파이썬)에서 막히면 `pip install --user --break-system-packages ...` 또는 `pipx` 를 쓴다.
> 설치하면 콘솔 명령 `ragkit` 가 PATH(`~/.local/bin` 등)에 생긴다. 안 잡히면 그 경로를 PATH에 추가한다.

## 빠른 시작

설치 후엔 폴더 상관없이:

```bash
ragkit ingest ./examples/docs       # -c 생략 -> 기본 컬렉션 'default'
ragkit ask "환불 기간 알려줘"          # -c·--show-sources 생략, 출처도 자동 표시

# 대화형: 한 번 켜고 계속 질문 (종료: 빈 줄 / exit / Ctrl-D)
ragkit ask
#  > 환불 기간 알려줘
#  > 배송 얼마나 걸려?

# 컬렉션 현황 / 외부 의존성 0으로 검색만 확인
ragkit list
ragkit ask "환불 기간" --backend echo
```

> 설치 없이 클론한 폴더 안에서만 써볼 거면 래퍼 `./rag <args>` 도 동일하게 동작한다.

## 새 목적 추가 = 컬렉션 하나 더

```bash
ragkit ingest -c 법률 ~/docs/contracts     # PDF + MD 섞여 있어도 OK
ragkit ingest -c 사내위키 ~/notes

ragkit ask -c 법률 "계약 해지 위약금 조건은?"
ragkit ask -c 사내위키 "배포 절차 알려줘"

# 한 컬렉션만 계속 쓸 거면 기본값으로 지정해 -c 도 생략
export RAGKIT_COLLECTION=법률
ragkit ask "계약 해지 위약금 조건은?"
```

컬렉션끼리 데이터가 섞이지 않는다. 목적이 바뀌면 새 컬렉션을 만들거나 `--reset` 으로 다시 색인하면 된다.

## 완전 오프라인 LLM 답변 (Ollama)

```bash
# 1) https://ollama.com 에서 Ollama 설치 후
ollama pull llama3.2          # 또는 qwen2.5 등 원하는 모델
ollama serve                  # (보통 자동 실행)

# 2) 백엔드 지정
python -m ragkit.cli ask --collection demo "질문" --backend ollama
# 모델/주소 변경: OLLAMA_MODEL, OLLAMA_URL 환경변수
```

`--backend auto`는 Ollama가 떠 있으면 그걸 쓰고 없으면 `claude` CLI, 그것마저 없으면 `echo`로 넘어간다.

## 지원 포맷 / 확장

| 확장자 | 처리 |
|--------|------|
| `.md`, `.markdown`, `.txt` | 텍스트 + 헤딩 경계 청킹 |
| `.pdf` | PyMuPDF로 페이지별 추출 (page 번호를 출처로 기록) |

새 포맷은 `ragkit/loaders.py` 에 `register(".ext", fn)` 한 줄로 추가한다.

## 구조

```
ragkit/
  loaders.py    # 확장자 레지스트리 (PDF/MD/txt → Document)
  chunking.py   # 순수 청킹 + 한글 bigram 토크나이저
  index.py      # BM25 인덱스 + 검색(search) + 컬렉션별 JSON 영속화
  answerer.py   # echo / ollama / claude_cli 백엔드, auto 감지
  pipeline.py   # ingest / ask / list_collections
  cli.py        # ingest / ask / list / info
config.py       # 경로(RAGKIT_HOME)·기본값
```

컬렉션 데이터 저장 위치는 기본 `~/.local-rag-kit/collections/<name>/index.json`,
`RAGKIT_HOME` 환경변수로 바꿀 수 있다.

## 한계 / 다음 단계

- 기본 검색은 BM25(어휘 매칭)다. 동의어나 의미 기반 검색까지 원하면 Ollama 임베딩(`nomic-embed-text`) 벡터 검색을 `index.py` 옆에 백엔드로 붙이면 된다. `add`/`search` 인터페이스는 그대로 두고 검색기만 갈아끼울 수 있게 짜놨다.
- 대용량(수십만 chunk)에서는 JSON 인덱스 대신 SQLite/FAISS로 교체 권장.

## 테스트

```bash
python -m pytest -q
```

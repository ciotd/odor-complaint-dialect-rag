# 현재 문법 KG: 시작 안내

갱신: 2026-10-08. **자연스러운 방언 생성의 성공이나 KG의 우월성을 아직 입증하지 못했다.** 코드 검사를 통과한 것과 번역 품질은 별개다.

**현재 우선순위:** 확인된 KG·조회 결함을 범위를 정해 실제 수정하고, 생성 전 조회로 확인한 다음 비교 생성과 1차 논문 초안으로 진행한다. Neo4j 추가 작업·확인은 뒤로 미룬다. “무한 보완을 중단”을 “필요한 수정도 생략”으로 해석하지 않는다. 기존 120개 출력은 별도 혼합 검색 경로의 개발 진단이며 기존 기능/조건 조회의 보완을 모두 통합한 결과가 아니다. [정정된 사용자 결정과 수정 범위](../연구미팅.md#2026-10-08-후속-사용자-결정--실험-정리와-1차-초안-우선)를 따른다.

**현재 단계(10월 8일 최신):** ① KG 보완 → ② 조회 통합 → ③ 생성 전 확인을 거쳐 **④ 고정된 30문장×4조건의 번역 120개를 생성·저장했다.** 재시도 0회이며 원문 응답을 수정하지 않았다. 일부 의문 어미와 높임 보존에 변화가 있지만 관형/인용 구성 오류가 남는다. C/D의 출력은 30건 모두 같아 추가 관계 확장의 이점을 입증하지 못했다. 현재 KG는 **334기록·6,214노드·15,978관계**다. 다음은 결과와 한계를 반영한 초안 정리이며 자동 보완 주기는 시작하지 않는다. Neo4j와 수정 전 120개 출력도 보존했다.

**후속 진단(10월 8일):** 사용자가 더 긴 일상 대화 입력을 제안해 새 입력 8개×4조건의 번역 32개를 추가 저장했다. [전체 출력](experiments/reports/long_dialogue_development/comparison.txt) · [원인 진단](experiments/reports/long_dialogue_development/diagnosis.txt). 긴 맥락에서도 분석 오류·관형 구성 오류·표준어 유지가 남았다. 주어진 예문에서는 어휘/활용 적용 위치가 없는 조회 경로와 잘못된 의문 유형 분석이 확인됐다. KG·조회 알고리즘을 추가 수정하지 않았으며 이전 30문장 결과를 보존했다.

## 무엇부터 볼까

| 보고 싶은 것 | 여기만 먼저 열기 |
|---|---|
| **최신 진단 — 긴 대화 입력 8개×4조건** | [32개 원본 출력 TXT](experiments/reports/long_dialogue_development/comparison.txt) · [KG 전달 내용](experiments/reports/long_dialogue_development/retrieval.txt) · [원인 진단](experiments/reports/long_dialogue_development/diagnosis.txt) |
| **통합 조회 적용 후 30문장×4조건** | [120개 원본 출력 TXT](experiments/reports/integrated_development/comparison.txt) · [비교표 TSV](experiments/reports/integrated_development/comparison.tsv) · [실행 요약](experiments/reports/integrated_development/summary.json) |
| **이번 통합 조회 결과 — 번역 전 점검** | [문장별 설명 TXT](experiments/reports/source_expansion/retrieval_integration.txt) · [위치·후보·관계·제외 이유 TSV](experiments/reports/source_expansion/retrieval_integration.tsv) · [요약·전체 원본 위치 JSON](experiments/reports/source_expansion/retrieval_integration.json) |
| **이번 KG 실제 수정 내역** | [기록별 변경표 TSV](experiments/reports/source_expansion/kg_repairs.tsv) · [전후 내용·원문 근거·모델 제안 판정](experiments/reports/source_expansion/kg_repairs.json) |
| **수정 전 10월 8일 혼합 검색 개발 진단: 30문장 × 4조건** | [120개 원본 출력 TXT](experiments/reports/controlled_development/comparison.txt) · [비교표 TSV](experiments/reports/controlled_development/comparison.tsv) · [조회 시작점·추가 경로](experiments/reports/controlled_development/retrieval.tsv) |
| 이번 변경·비교 방법과 남은 문제 | [방법과 한계](docs/구축방법.md#10월-8일-후속-원문-예문-보완과-통제된-개발-비교) · [실행 요약](experiments/reports/controlled_development/summary.json) |
| 합의한 연구 방향과 조회 방식의 근거 | [연구 방향](../연구미팅.md#2026-10-08-사용자-승인-방향--이후-작업의-기준) · [실제 조회 설계](docs/구축방법.md#2026-10-08-조회-설계와-비교-기준) |
| 이후 확인할 Neo4j 자료 — 현재 작업 보류 | [접속·적재 설명](docs/구축방법.md#10월-8일-실제-진행-결과-문헌-복구와-neo4j-확인용-적재) · [실행할 Cypher](experiments/reports/neo4j/inspection.cypher) · [구조 그림](experiments/reports/neo4j/schema.svg) |
| 문헌 1차 처리 결과와 다시 검토할 항목 | [1,064개 단위 검토표](experiments/reports/source_expansion/review_units.tsv) — 모델 제안이며 의미 승인 아님. 연결 재검토 61개, 화면 검토 표시 307개(중복 가능) |
| 10월 7일 문헌·조회 확장 작업 기록 | [터미널 진행 기록](experiments/reports/source_expansion/progress.txt) · [작업 내용과 한계](docs/구축방법.md#2026-10-07-문헌-보존과-조회-입구-확장) |
| 문헌 7종·474쪽과 KG의 대응 목록 | [대응표 TSV](grammar/source_evidence/alignment.tsv) — 같은 쪽/형태의 자동 대응이며 의미 검수 완료표가 아님 |
| 확장 경로의 생성 전 조회 8문장 | [조회 결과 TXT](experiments/reports/source_expansion/retrieval_20261007T074045678730Z.txt) · [원문 결속 재검증](experiments/reports/source_expansion/binding_recheck.txt) |
| 이전 10월 2일 비교: 표준어 38문장과 수정 전·후 번역 76개 | [번역 결과 TXT](experiments/reports/latest/translations.txt) · [표로 보기](experiments/reports/latest/translations.tsv) |
| 10월 6일: 보존 메모만 바꾼 원인 분리 진단 | [6문장 × 두 조건 × 2회 출력](experiments/reports/diagnostics/preservation_only_20261006T005939770914Z.txt) |
| 10월 6일: 사용자 질문 두 건의 -노/-나 재확인 | [자동 분석·조회·생성 결과](experiments/reports/diagnostics/question_pair_20261006T025911838343Z.txt) |
| 무엇이 잘못됐고 다음에 무엇을 수정할지 | [실제 입력 감사와 다음 작업](docs/구축방법.md#2026-10-06-생성-입력-감사와-다음-작업) |
| Qwen이 실제로 받은 지시문·KG·원문 전체 | [문제 사례 6개의 실제 메시지](experiments/reports/latest/qwen_inputs.txt) |
| 파일의 유지·이동 내역 | [파일별 처리 장부](experiments/reports/latest/file_disposition.tsv) |

JSON은 근거를 추적하거나 코드를 실행할 때 쓰는 자료다. 비교 결과를 읽기 위해 JSON을 모두 열 필요는 없다. `latest/`는 이전 10월 2일 비교, `controlled_development/`는 통합 수정 전 10월 8일 비교다. **기존 30문장 결과는 `integrated_development/`, 후속 긴 대화 진단은 `long_dialogue_development/`**에서 본다. 과거 보고서를 덮어쓰거나 파일을 삭제하지 않았다.

## 폴더 구조

```text
current_kg/
├── README.md                    지금 읽는 시작 안내
├── grammar/                     문헌 지식 원본·규격·현재 KG·구축/검사 코드
│   ├── authored/                개별 지식 수정 원본
│   ├── integration.json         문헌 간 연결 원본
│   ├── grammar.graph.json       실제 조회 그래프
│   ├── records.jsonl            통합 기록 보기
│   └── source_evidence/         원문 페이지·검색 단위·KG 대응 관계 (추출 원문은 로컬 보관)
├── experiments/
│   ├── *.py                     현재 실행 모듈·검사·공유 호환 모듈
│   ├── inputs/                  실험 입력·설정·수동 분석 기준 자료
│   ├── reports/
│   │   ├── integrated_development/ 통합 조회 적용 후 최신 번역 비교
│   │   ├── controlled_development/ 통합 수정 전 10월 8일 비교
│   │   ├── latest/              이전 10월 2일 비교와 요청 감사
│   │   └── diagnostics/         요인 분리 진단 결과
│   └── archive/
│       ├── reports/             과거 공개 비교 결과
│       ├── legacy_development/  초기 수동 후보·조회·생성 자료
│       ├── diagnostics/         과거 연결 점검·검증 산출물
│       ├── tools/               과거 실행·재시도용 진입 스크립트
│       └── runs/                실행별 원본 요청·응답·코드/KG 스냅샷
└── docs/
    ├── 구축방법.md              작성 방법과 현재 기술 검토
    ├── 전체원문검토.md          원문 검토 범위
    └── history/                초기 설계와 이전 상세 작업 안내
```

`archive/runs/`는 상세 기록이므로 Git 제외 상태를 유지한다. 보고서와 원본 파일의 해시·실행 ID로 연결한다. 과거 JSON 안에 남은 옛 경로는 당시 기록이며 일괄 수정하지 않았다. 현재 위치는 파일 처리 장부를 따른다. AI-Hub 파생 입력 두 파일도 이동 후 Git 제외를 유지했다.

## 현재 실행은 무엇인가

**Qwen 분석 → 원문 형태 근거 검증 → KG 조회/선별 → Qwen 번역.** 중간 기록은 저장하지만 아래 모두를 사람이 읽어야 하는 것은 아니다.

| 역할 | 파일 |
|---|---|
| **현재 조회 준비·4조건 비교 진입점** | [run_controlled_retrieval.py](experiments/run_controlled_retrieval.py): `prepare`와 `generate` 분리 |
| **현재 통합 조회·후보 선별** | [integrated_retrieval.py](experiments/integrated_retrieval.py) · [원문 구성 결속](experiments/source_bindings.py) |
| **생성 전 자동 분석·조회 확인** | [review_integrated_retrieval.py](experiments/review_integrated_retrieval.py) |
| 분석 모델 호출·규격 변환 / 과거 3조건 실험 | [run_auto_analysis_development.py](experiments/run_auto_analysis_development.py) |
| 입력 규격 검사 | [analysis_input.py](experiments/analysis_input.py) |
| Kiwi를 이용한 높임·선어말 근거 검증 | [source_analysis_guard.py](experiments/source_analysis_guard.py) |
| 이전 기능 조회 — 과거 개발 진단 재현용 | [run_manual_kg_development.py](experiments/run_manual_kg_development.py)의 `retrieve` |
| 그래프 조건·예외 판정 | [query_review.py](grammar/query_review.py) |
| 서버 연결·생성 메시지 조립 | [run_seeded_kg.py](experiments/run_seeded_kg.py) — 과거 실행 기능과 공유 함수가 함께 있어 유지 |
| 보존 메모 하나만 바꾸는 진단 | [audit_generation_requests.py](experiments/audit_generation_requests.py) |
| 문헌 전범위 보존·출처 대응 목록 | [source_inventory.py](grammar/source_inventory.py) |
| Neo4j 확인용 미러·Cypher/Python 첫 조회 대조 | [neo4j_view.py](grammar/neo4j_view.py) — 생성 실행 경로의 교체나 임베딩 도입은 아님 |
| 문헌 검색 색인 / 이전 모델 관련성 검토 경로 | [source_retrieval.py](experiments/source_retrieval.py) |
| 이전 확장 조회의 개발 실행·터미널 출력 | [run_source_expansion.py](experiments/run_source_expansion.py) |
| 전범위 모델 검토 — 사용자 승인 후 실행 시작 | [review_source_inventory.py](experiments/review_source_inventory.py) · [실행 상태](grammar/source_evidence/review_status.json) |
| 임베딩/문자/혼합 검색 개발 비교 | [embedding_retrieval.py](experiments/embedding_retrieval.py) · [고정 분석 4조건 실행](experiments/run_controlled_retrieval.py) · [보고서 재현](experiments/summarize_controlled_retrieval.py) |
| 패키지 버전 | [분석 환경](experiments/requirements-analysis.txt) · [임베딩 환경](experiments/requirements-retrieval.txt) |

`build_development_kg_packets.py` 등 과거 방식의 공유·검사 모듈은 참조가 있어 유지했다. 현재 자동 실행의 주 진입점은 아니다. 과거 진입 스크립트 4개는 `archive/tools/`로 이동했다. 과거 결과를 현재 코드로 덮어써 재생성하지 않는다.

현재 통합 실행은 Kiwi와 임베딩 모델이 함께 설치된 `.venv/retrieval/bin/python`을 사용한다. 기존 분석 환경 `.venv/analysis/bin/python`도 보존했다. 네트워크 없는 확인:

```bash
.venv/retrieval/bin/python -m unittest discover -s current_kg/experiments -p 'test_*.py'
/usr/bin/python3 current_kg/grammar/build.py check
.venv/analysis/bin/python current_kg/experiments/audit_generation_requests.py
```

기존 실행기의 실제 모델 호출에는 `--execute`가 필요하다. 새 통제 비교 실행기는 `prepare`(로컬 검색)와 `generate`(실제 Qwen 호출)를 분리한다. 저장된 오래된 실행을 현재 코드로 재개하면 해시 검사에서 거부될 수 있다. 이는 재배치나 수정 이후 다른 코드로 옛 결과를 덮어쓰지 않기 위한 동작이다.

확장 경로는 `run_source_expansion.py --execute`로 생성 전 조회를 기록한다. `--translate`를 명시하면 번역도 수행한다. 기존 30문장 진입점은 `--retrieval hybrid`를 선택할 수 있으며 기본값 `function`은 과거 기능 조회다. 확장 경로는 아직 개발 검토 단계이므로 기본 경로의 품질 개선 완료로 해석하지 않는다. 실시간으로 볼 때는 `tail -f current_kg/experiments/reports/source_expansion/progress.txt`를 사용한다. 문헌 전체의 모델 검토는 **2026-10-07 사용자의 기존 Qwen 서버 전송 승인 후 시작하여 10월 8일 제안 수집을 완료했다**. 현재 추가 서버 호출은 없다. 아래 실행 설명은 완료된 검토의 방식이다. 6개 단위씩 두 요청을 병행하며, 진행률과 완료/실패 여부는 `grammar/source_evidence/review_status.json`을 확인한다. 모델의 1차 제안이며 문헌 의미 검수 완료나 문법 승인이 아니다.

## 현재 판정과 다음 작업

최신 통합 조회에서는 인용 원문에서 인용 지식을 찾고 조건 대조까지 수행하며 새 번역 120개도 저장했다. 아래 120개 출력 관련 설명은 **수정 전 실험**의 문제 기록이다. 최신 비교는 일부 국소적 변화와 남은 오류를 보여주며 전체 자연스러움 개선이나 추가 관계 확장의 이점을 입증하지 않는다.

- 문헌 지식은 334개 기록, 그래프는 6,214개 노드·15,978개 관계다. 전체 원문 의미의 누락 없는 반영이나 독립 검증 완료를 뜻하지 않는다.
- 높임 오판·없는 선어말·연결절 과잉 차단을 일부 수정했지만, 문장 연결·전언 의미·활용형·자연스러움 문제가 남아 있다.
- 10월 6일 요청 감사에서는 같은 후보를 전달해도 보존 메모 변경에 따라 오류가 반복됨을 확인했다. 시스템 프롬프트가 같아도 전체 Qwen 입력은 같지 않았다.
- 10월 8일 캤다·카데/인용 관련 원문 예문 6개를 별도 근거 노드로 연결했다. 그러나 새 원문/임베딩 검색에서도 인용 지식이 상위에서 빠지는 문제는 남았다. 30문장×4조건의 120개 출력을 저장했지만 품질 개선은 입증하지 못했다. 같은 KG 시작 기록에서 관계 확장이 실제 일어난 문장은 11개이며, 나머지 19개는 입력이 같았다. 같은 입력/시드에서도 1건의 출력 차이가 있어 단일 출력 차이를 관계 효과로 해석하지 않는다. [추가 진단](docs/구축방법.md#2026-10-06-인용-용례-누락과-의문형-두-문장-재확인)을 참고한다.
- 새 8문장과 이번 6개 문제 사례는 개발 진단 자료다. 독립 평가 자료나 방언 화자 자연스러움 평가를 대신하지 않는다.

## 이번 정리에서 삭제했나

**삭제 0건.** 데이터·실행 스냅샷의 이동 전후 해시를 확인했다. 문서 링크와 현재 코드의 경로만 필요한 만큼 갱신했다. 과거 설계 및 논문 관련 자료는 보존했다. 캐시나 중복처럼 나중에 삭제할 수 있는 파일도 이번에는 삭제하지 않았다. 삭제를 제안할 경우 목록과 이유를 먼저 확인받는다.

이전 1,610줄 작업 안내는 새 MD를 만들지 않고 기존 [이력 문서](docs/history/README.md#2026-10-06-이전-작업-안내-원문-보관)에 보존했다. 예전 방식과 현재 상태를 혼동하지 않도록 이 페이지를 기준으로 시작한다.

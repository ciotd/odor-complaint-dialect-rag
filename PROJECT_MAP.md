# 프로젝트 지도 — 2026-09-17

## 현재 작업의 기준

[연구미팅.md](연구미팅.md)의 최신 논의와 [현재 작업 안내](current_kg/README.md)를 먼저 읽는다. [선행연구.md](sources/methodology/선행연구.md)는 11편의 근거·한계와 설계 제안을 정리한다. 과거 다음 단계나 외부 검토자의 의견을 자동으로 현재 지침으로 적용하지 않는다.

| 경로 | 역할 |
|---|---|
| `이관.md` | 새 세션 시작 안내: 필수 원칙·최종 목표·상태 스냅샷·기록 관계·남은 작업·재개 명령 |
| `연구미팅.md` | 연구 의사결정 요약: 목적·합의·미정 사항·상태·전체 계획. 상세 대화는 Git 이력 |
| `current_kg/grammar/authored/` | 원문을 직접 읽어 작성한 현행 문법 지식 초안; 이관 시점 20파일 |
| `current_kg/grammar/작성검토.md` | 전체 작성·연결 점검, 모든 통합 관계와 남은 공백 |
| `current_kg/grammar/records.jsonl` | 활성 문법 지식 331건의 통합 장부 |
| `current_kg/grammar/grammar.graph.json` | 새 규격의 그래프 변환 결과; 운영 생성 KG 아님 |
| `current_kg/grammar/record.schema.json`, `ontology.json` | 기록 형식·공통 분석 개념 |
| `current_kg/grammar/analysis_contract.json`, `analysis_links.json` | 입력 분석과 지식 연결 설계; 분석기·실행 조회기는 아님 |
| `current_kg/grammar/query_review.py`, `query_review.results.json` | 수동 조건의 제한적 관계 조회와 근거·공백 기록; 자동 분석·생성 승인은 아님 |
| `current_kg/grammar/progress.json`, `gaps.json`, `work_plan.json` | 작성 범위·미확보 정보·처리 계획 |
| `current_kg/grammar/example_review.md` | 작성자가 구성한 예문의 점검 기록; 사람 자연스러움 검증 아님 |
| `current_kg/grammar/source_notes.json`, `retired/` | 지식에서 분리한 배경 메모와 과거 기록 |
| `current_kg/experiments/build_baseline_testset.py` | AI-Hub 예비 진단 후보 구성 스크립트; 경계·표본 검증 전 |
| `current_kg/claims/source_registry.json` | 원문 자료 통제표. 파일·허용 범위 확인용 |
| `current_kg/claims/v3/`, `structured/`, `raw/`, `review/` | 과거 Claim·그래프·검토 이력. 새 지식과 합산 금지 |
| `current_kg/docs/`, `design_probe/` | 이전 포맷·범위 검토·구조 점검 이력 |
| `sources/gyeongsang/academic/` | 조현준·류성기 논문 2종, 로컬 PDF |
| `sources/gyeongsang/web/` | 동남 방언 개요·문법·상대높임법·음운 PDF 4종 |
| `sources/gyeongsang/lexical/` | 어휘 JSON 별도 후보, Git 제외 |
| `sources/methodology/` | 방법론 11편 정리와 후속 양지현·Song 문헌. 자료별 역할은 registry와 선행연구.md에서 구별; PDF는 Git 제외 |
| `paper/INTRODUCTION_DRAFT.md` | 확정 전 서론 작업본 |
| `CLAUDE_REVIEW_LOG.md` | 기존 외부 검토자의 의견·측정 보고 이력; 연구 결정을 대신하지 않음 |
| `sources/templates/` | 논문 제출 양식 |
| `archive/v1_retrieval/`, `archive/v2_failed/` | 과거 실험 코드·기록 |

## 보존과 공개 범위

이력은 삭제하지 않고 현재 안내와 구분한다. 이미 삭제된 부산 전용 실험안은 복구하지 않으며 Git 이력에서 확인할 수 있다. AI-Hub는 문법 근거가 아닌 독립 평가 후보이며, 원본·파생 문장쌍은 로컬에 보관하고 스크립트만 추적한다.

현재 문서가 과거 문서를 링크하는 것은 당시 설계·관찰을 확인하기 위한 것이지, 과거 규격을 현행으로 승인한다는 뜻이 아니다.

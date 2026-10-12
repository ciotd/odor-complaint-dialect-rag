# 프로젝트 지도

최종 갱신: 2026-10-12. 새 표현 구조는 [kg_v2/README.md](kg_v2/README.md), 보존된 기존 KG·실험은 [current_kg/README.md](current_kg/README.md)에서 본다. `archive/v2_failed`와 새 `kg_v2`는 서로 다른 작업이다.

| 위치 | 역할 |
|---|---|
| [연구미팅.md](연구미팅.md) | 목적·합의·미정 사항·주요 결정 이유 |
| [이관.md](이관.md) | 새 세션의 필수 원칙·재개 안내 |
| [kg_v2/README.md](kg_v2/README.md) | 새 KG 표현·전체 문헌 추출·병렬 검토·조회 및 검증 |
| `kg_v2/authored/`, `kg_v2/reviews/` | 출처별 지식 원본과 페이지 검토·잔여 한계 |
| `kg_v2/reports/` | 빌드·공백 처리·통합 근거 검증 결과 |
| [KG v2 번역 비교](kg_v2/reports/translation_20261012/README.md) | 입력 분석·생성 연결, 38개 입력×4조건 최종 출력·품질 진단 |
| [KG v2 Neo4j](kg_v2/reports/neo4j/README.md) | 별도 DB 스냅샷 검증, 전체 구성과 실제 활용 연결 PNG·SVG |
| [current_kg/README.md](current_kg/README.md) | 현재 상태·파일 관계·검사 전체 목록·실행 명령 |
| `current_kg/grammar/authored/` | 직접 작성한 지식 수정 원본 |
| `current_kg/grammar/integration.json` | 통합 관계·문제·처리 장부 수정 원본 |
| `current_kg/grammar/records.jsonl` | 통합 지식 기록 |
| `current_kg/grammar/grammar.graph.json` | 현행 통합 그래프 |
| `current_kg/grammar/작성검토.md` | 작성·연결 공백과 보류 사항 |
| `current_kg/grammar/source_registry.json` | 현행 자료 목록·정책 |
| `current_kg/docs/` | 현행 구축방법·전체원문검토와 논문 추적용 과거 설계·자료 검토 기록 |
| `current_kg/experiments/` | 연결 점검 이력·AI-Hub 평가 후보 구성 |
| `sources/` | 원문·어휘·선행연구·제출 양식. 로컬 자료 재배포 금지 |
| `paper/INTRODUCTION_DRAFT.md` | 확정 전 서론 |
| `CLAUDE_REVIEW_LOG.md` | 외부 검토 이력. 현행 지식 독립 검증 결과는 아님 |
| `archive/` | v1/v2 코드·문서·자료·실험 이력. 논문 근거로 보존하며 현행 KG 실행과 구분 |

현재 KG의 이전 claims·design_probe 구현·산출물은 정리했다. v1/v2 연구 이력과 설계·자료 검토 문서는 보존한다. v1/v2까지 삭제한 것은 에이전트의 범위 오해였으며 복원했다. 새 안내 파일을 추가하기보다 기존 문서의 해당 절을 갱신한다.

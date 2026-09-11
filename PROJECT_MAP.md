# 프로젝트 지도 — 2026-09-10

## 현재 작업의 기준

[현재 상태](current_kg/README.md)와 [새 Claim 포맷 초안](current_kg/docs/CLAIM_FORMAT_V3_DRAFT.md)을 먼저 읽는다. 초안은 사용자 검토 중이며 확정된 운영 규칙이 아니다. 이력 문서의 ‘정본’이나 과거 다음 단계 지시는 현재 작업에 적용하지 않는다.

## 위치와 역할

| 경로 | 역할 |
|---|---|
| `current_kg/docs/` | 현재 포맷 초안, 원문 근거 카드, 여섯 자료 통합 검토 |
| `current_kg/docs/history/` | 이전 재시작·3종/4종 범위 검토·설계 이력 |
| `current_kg/claims/source_registry.json` | 원문 자료 통제표 |
| `current_kg/claims/structured/`, `raw/`, `review/` | 기존 추출본과 검토 이력. 신규 KG 입력이 아님 |
| `sources/gyeongsang/academic/` | 조현준·류성기 논문 2종 |
| `sources/gyeongsang/web/` | 동남 방언 개요·문법·상대높임법·음운 PDF 4종 |
| `sources/gyeongsang/lexical/` | 어휘 JSON 별도 후보 |
| `sources/methodology/kg/` | KG 방법론 논문 |
| `sources/templates/` | 논문 제출 양식 |
| `archive/v1_retrieval/` | 과거 5권역 악취 RAG 연구 |
| `archive/v2_failed/` | 실패한 39규칙 기반 실험·코드·평가 기록 |

AI-Hub는 신규 Claim 근거가 아니라 독립 평가 후보로 보존한다. 과거 실험은 해당 archive 하위 경로에서 별도로 다룬다.

## 문서 관리 기준

현재 작업 안내는 README에, 구체적 설계는 해당 초안에 둔다. 지나간 단계의 문서는 이력 영역으로 이동하며 최신 안내에서 현재 기준처럼 노출하지 않는다. 코드·검토 산출물이 참조하는 과거 문서는 경로를 유지하고 이력 상태를 표시한다. 문서를 옮길 때 살아 있는 상대 링크도 함께 수정한다.

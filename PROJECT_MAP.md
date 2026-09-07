# 프로젝트 지도 — 2026-09-07 재정리

## 1. 현재 연구

경로: `current_kg/`

목표는 표준어 문장을 자연스러운 경상도 방언 문장으로 변환하기 위한 KG를 새로 만드는
것이다. 현재 단계의 정본은 다음 두 문서다.

1. `current_kg/docs/RESET_2026-08-31.md`
2. `current_kg/docs/SOURCE_REVIEW_2026-09-07.md`

두 문서가 충돌하면 더 최근 결정을 기록한 `SOURCE_REVIEW_2026-09-07.md`와
`RESET_2026-08-31.md`의 §12를 우선한다.

## 2. 현재 KG의 입력 자료

경로: `sources/gyeongsang/`

- `academic/경북방언_종결어미_연구.pdf`
- `academic/표준어 간섭 및 방언에 대한 의식으로 인한 경남 함양 방언 문법 형태의 변화 연구.pdf`
- `web/동남 방언.pdf`
- `lexical/gyeongsang_vocab.json` — 별도 보류 계층, Git 비추적

기존 문법 JSON, AI-Hub 경상 코퍼스, 과거 문법 검수 문서, 기존 v2 종결어미 39규칙은
신규 Claim 추출의 입력이 아니다.

## 3. 보관 자료

### v1

경로: `archive/v1_retrieval/`

5권역 방언 악취 민원 대화 합성과 RAG 실험의 코드·데이터·문서·결과를 함께 보존한다.
현재 KG를 만들 때 이 폴더를 근거 자료로 읽지 않는다.

### 실패한 v2

경로: `archive/v2_failed/`

종결어미 39규칙, 과거 KG 스키마, 생성 코드, 평가셋, 결과와 진행 문서를 함께 보존한다.
현재 KG 구축과 분리된 실패 분석·재현 자료이다.

## 4. 기타 자료

- `sources/methodology/kg/` — KG 구축·활용 방법론 논문
- `sources/templates/` — 논문 제출 양식
- `archive/PROJECT_MAP_legacy.md` — 폴더 정리 전의 과거 프로젝트 지도

## 5. 작업 규율

- 문헌의 사실, AI의 구조화, 사용자의 검증을 분리한다.
- 출처 위치가 없는 Claim은 만들지 않는다.
- 기존 39규칙을 목표 개수·정답·참고자료로 사용하지 않는다.
- Claim 전체 검토 전에는 KG 노드·관계와 운영 Rule을 확정하지 않는다.
- 과거 연구를 실행할 때에는 해당 `archive` 하위 폴더를 작업 디렉터리로 사용한다.

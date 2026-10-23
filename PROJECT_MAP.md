# 프로젝트 자료 안내

[통합 보고서](reports/20261021_paper50/report.html)에서 현재 연구의 방법과 결과를 확인합니다.

## 현재 시스템

| 위치 | 역할 |
|---|---|
| `kg_v2/` | 현행 지식 항목·그래프, 조회·생성·검사 코드 |
| `kg_v2/authored/`, `kg_v2/reviews/` | 원문 근거를 포함한 지식 작성본과 검토 기록 |
| `kg_v2/reports/` | 구축·원문 대조 기록과 테스트·조회 검토용 최소 자료 |
| `current_kg/` | 이전 KG와 공통 모듈. 현재 실행 및 기존 파일 보존 검사에 연결되어 있어 유지 |
| `sources/` | 문헌 위치와 선행연구 검토. 원문 PDF는 로컬 보관 |

## 남겨 둔 실험 자료

| 위치 | 남긴 자료 | 이유 |
|---|---|---|
| `reports/20261021_paper50/` | 50개 × 세 조건의 모든 요청·응답·분석·조회·평가·설정·코드/KG 사본 | 현재 논문용 결과 전체와 재현 근거 |
| `reports/20261013_terminal_generation/` | 70개 입력의 분석·최종 출력·설정·번역·검토 | 최신 50개 중 44개의 입력 출처 |
| `reports/20261013_user_qualification20/` | 20개 입력의 분석·최종 출력·설정·번역·검토 | 최신 50개 중 6개의 입력 출처 |
| `reports/20261012_construction_generation/analysis.json` | 과거 입력 분석 한 파일 | 현재 종결 조회 테스트가 읽는 고정 예제 |
| `reports/latest/` | 현재 통합 보고서의 경로 안내 | 중복 결과를 만들지 않는 단일 진입점 |

직전 70건·20건 폴더는 핵심 기록만 남긴 것이며 완전한 실행 사본이 아닙니다. 해당 과거 실험 전체를 다시 검토하려면 [정리 전 Git 커밋](https://github.com/ciotd/odor-complaint-dialect-rag/tree/4d6998be399df717762231fa3ea1c23f17212b85)을 사용합니다.

최신 폴더에서 `raw/`는 실제 요청·응답, `retrieval.json`은 조회, `candidate_trace.json`은 후보 전달·표면 관찰, `annotations.json`은 정성 평가, `protocol.json`은 설정, `snapshot/`은 당시 코드와 KG입니다. 이 사본은 실험 당시 상태를 고정하기 위한 것이므로 현재 코드와 내용이 같아도 유지합니다.

## 제거한 폴더

- `archive/`: 폐기된 구현·과거 연구 메모. Git 이력에서 복원할 수 있습니다.
- `paper/`: 2026년 9월의 미확정 서론 초안. 최신 50건 실험을 반영한 원고가 아닙니다.
- 나머지 과거 실험 폴더: 현재 보고서·실행·테스트가 참조하지 않는 중간 결과와 중복 사본입니다.

정리 목록: [repository_audit.json](reports/repository_audit.json). 새로운 번역 실험 없이 문서와 파일만 정리했습니다.

# 프로젝트 자료 안내

현재 설명과 결과를 읽을 때는 [통합 보고서](reports/20261021_paper50/report.html)부터 확인합니다.

| 위치 | 내용 |
|---|---|
| `reports/20261021_paper50/report.html` | 현재 논문용 보고서 하나 |
| `reports/20261021_paper50/raw/` | 150개 조건별 요청·응답, 자동 검사·수정 기록 |
| `reports/20261021_paper50/analysis.json` | 이번 실험에서 고정해 재사용한 Qwen 분석 |
| `reports/20261021_paper50/retrieval.json` | 입력별 조회 후보·조건·관계 기록 |
| `reports/20261021_paper50/candidate_trace.json` | 실제 전달 후보와 출력의 대응 분석 |
| `reports/20261021_paper50/annotations.json` | 의미·높임·자연스러움·방언 표현의 사례별 판정 |
| `reports/20261021_paper50/protocol.json` | 모델 설정과 고정 파일의 해시 |
| `reports/20261021_paper50/snapshot/` | 실험에 사용한 코드·KG의 고정 사본 |
| `kg_v2/` | 현행 KG 작성본·그래프·조회·검사 코드 |
| `current_kg/experiments/` | 공통 모델 호출·원문 분석 코드와 이전 실험 |
| `sources/` | 원문 등록·방법론 검토. PDF 본문은 로컬 보관 |
| `reports/20261013_*`, `reports/20261012_*`, 기타 날짜 폴더 | 이전 실험 원본 및 보고서 생성 코드 |
| `reports/20261021_paper50/archive_documents/` | 과거 Notion 내보내기와 문서 개정 기록 |
| `archive/research_notes_20261024/` | 문서 정리 전 README·연구 회의·검토·이관 기록 |

`reports/latest/`는 통합 보고서 위치만 안내합니다. 실제 결과의 정본은 `reports/20261021_paper50/`이며, 파일 수정 시간으로 실험 버전을 판단하지 않습니다.

과거 보고서 재생성 코드에는 모델을 실행하는 기능이 함께 있는 경우가 있습니다. 단순 보고서 복원 시에는 저장된 결과를 읽는 부분만 실행합니다. 현재 통합 보고서는 `build_report.py`로 모델 호출 없이 다시 만듭니다.

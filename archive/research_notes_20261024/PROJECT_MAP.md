# 프로젝트 지도

**2026-10-13 현재 상태 — 수정된 새 입력20개 번역 완료:** 사용자가 교체한20개를 현재 KG·조회·Qwen 설정 그대로 실행하고 같은 실험 폴더에 덮어썼다.20개 모두 생성했으며 분석21회·생성21회(최초20회＋보존 재검토1회)다.15번 재검토에서도 겸양 오류가 해결되지 않았다.4·12·16번은 원문과 같고,6·9·10·14번에는 높임 소실이 남는다. 종결 변환안은9/20개 입력에서 선택됐다. 입력 변경 시험이므로 시스템 개선율로 해석하지 않는다.

[최신20개 원문·번역](reports/20261013_user_qualification20/translations.txt) · [검토·한계](reports/20261013_user_qualification20/review.txt) · [기존70개 결과](reports/20261013_terminal_generation/translations.txt) · [복습 DOCX](reports/20261013_review_guide/경상도_방언_KG_예시로_이해하는_복습가이드_20261013.docx) · [전체 결과 안내](reports/latest/index.html)

현재 KG·조회 추가 수정과 대안 실험은 사용자 요청으로 중단한 상태다. Claude 피드백→Astra 원인 대조→KG/코드 보완안→검증 자동화는 제안 단계이며 아직 구현하지 않았다. 문헌 근거와 모델 제안을 구별하고 기존·새 문장과 반례로 검증하는 방향을 논의했다. 아래 기록의 수치와 완료 여부는 각 당시 시점의 이력이다.

**2026-10-13 이전 실행 — 종결 기능별 조회 수정 후70개:** 최초70회＋자동 보존 재검토5회, 수정본 채택1개. 직전 대비35개 출력이 달라졌다. 같은70개에서 세예 포함9→0, 게예 포함9→0, 원문 완전 동일5→1이지만 강한 보존 경고4개는 그대로다. 요청·질문·약속과 일부 반말 종결은 개선됐으나 인용·의도 결합, 문장 구조 및 겸양 오류가 남고 일부 악화도 있다. [최신 전후 비교](reports/20261013_terminal_generation/comparison.html) · [전체27조건·모델 이력](reports/20261013_terminal_generation/history.html) · [분석 결론](reports/20261013_terminal_generation/review.txt). A/B/C/D는 과거50개×4조건을 보존했으며 이번에는 최신 단일 경로70개를 생성했다. 아래 단락은 각 이전 작업 시점의 기록이다.

**2026-10-13 이전 실행 — 말투 지시만 추가한 실험:** KG·조회·분석·Qwen 설정을 고정하고 경북40대 이상 지시만 추가해70개를 생성했다.16개 변경·54개 동일이며, 강한 보존 경고 입력4개는 그대로다. 인용 조합·문장 구조 문제가 남고 일부 악화도 있어 품질 개선을 확정하지 않는다. [전체 비교](reports/20261013_gyeongbuk40_prompt/comparison.html) · [검토 결론](reports/20261013_gyeongbuk40_prompt/review.txt). 생산 기본 프롬프트는 변경하지 않았다. 아래 DOCX와10월12일 기록은 말투 실험 이전 상태다.

**2026-10-12 최신 생성·보고 완료:** 인용·의도 조회 수정 버전으로70개를 신규 생성했다(최초70회＋보존 수정5회, 수정본 채택1개). 요청 변경5개·최종 출력 변경3개이며 품질 개선은 입증하지 못했다. [쉽게 설명한 최신 DOCX](reports/20261012_easy_briefing/경상도_방언_연구_쉽게보는_전체과정_20261013.docx), [수정 전후 실제 출력](reports/20261012_construction_generation/comparison.html), [새 Sonnet70개와 대조](reports/20261012_easy_briefing/sonnet_comparison_70.html), [피드백·원문 검토](reports/20261012_easy_briefing/sonnet_feedback_review.txt). 이후 단락은 각 작업 당시의 기록이다.

**결과를 찾을 때는 [최신 결과 안내](reports/latest/index.html)부터 연다.** [보고용 요약](reports/latest/briefing.txt), [최신 실제 번역20개](reports/latest/translations.html). 최신 번역은 사용자 교체 입력20개이며, 기존 종결 조회 수정 후70개 결과는 별도 보존돼 있다. 일부 종결은 개선됐지만 전체 품질이 꾸준히 상승했다고 입증하지는 못했다. 아래 날짜별 기록의 수치·완료 여부는 해당 시점 기준이다.

최종 갱신: 2026-10-13. 새 표현 구조는 [kg_v2/README.md](kg_v2/README.md), 보존된 기존 KG·실험은 [current_kg/README.md](current_kg/README.md)에서 본다. `archive/v2_failed`와 새 `kg_v2`는 서로 다른 작업이다.

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

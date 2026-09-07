# PROJECT MAP — 두 연구 구분

이 리포에는 **서로 다른 두 연구**가 있다. 문서·경로가 꼬이지 않게 아래로 구분한다.

## v1-retrieval (기존 연구 — RAG 파편검색 기반 악취 방언 생성)
- **내용:** 로컬 LLM + 지식 주입(few-shot / RAG 검색)으로 5권역 방언 악취 민원 대화 합성·평가.
- **상태:** 실험 완료(n=100), 정직한 결론 = few-shot 우위, RAG 고유기여 ≈0. 논문 Ⅲ 초안 존재.
- **정본 문서:** `docs/research_scope.md` (설계·결과·결정 SSOT).
- **경로:** `src/`, `results/`, `data/dialect_kb/`, `docs/`(research_scope, research_discussion_transcript,
  experiment_report.docx, paper_ieie.md, fixed_injection_rules.md, prompt_and_rag_examples.md, data_audit.md 등).

## v2-graph (신규 연구 — 지식그래프 기반 조건부 문법 방언 생성, **경북** 국한)
- **내용:** 문장 자질 → 경북 문법 KG에서 관련 서브그래프 검색 → focused 주입 → LLM 생성. (SURGE식 (b),
  training-free). v1의 파편검색을 대조군으로 삼음.
- **스코프:** 경북(경상북도) 확정. backbone = 조현준(2018) 경북방언 종결어미 논문.
- **상태:** KG 축 확정, 의문법 노드 추출 중(하소체 TODO), 스키마 초안 예정.
- **정본 문서:** `v2_graph/README.md`. KG 노드: `v2_graph/docs/kg_nodes_*.md`.
- **경로:** `v2_graph/` (docs/ src/ data/ results/).

## 공유 자원 (양쪽이 기존 경로로 참조; 복제 안 함)
- `../RAG_resource/` (권역별 원본 어휘·문법. 경상 문법 원본 = `경상도/문법/gyeongsang_grammar.json` 238규칙, '경상' 통칭).
- AI-Hub 표준-방언 코퍼스 (평가 마커·표준-방언 쌍 출처).
- `data/dialect_kb/` (v1 정제 KB; v2는 필요분만 참조).
- **방언학 논문 PDF (v2 문법 소스, 리포 루트):** `경북방언_종결어미_연구.pdf`(조현준2018, v2 주 backbone) ·
  `표준어 간섭…경남 함양 방언…연구.pdf`(경남 대조 참고). 라이선스 CC BY-NC-ND → 사실 인용만, 재배포 금지.

## 규율
- v1/v2 문서·코드는 각 경로 안에서만 관리. 교차 수정 금지.
- 새 탐색·분석은 **과정 먼저 공유 → 오류 점검 → 진행** (사용자 규율).

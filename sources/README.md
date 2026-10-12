# 연구 자료

## 경상도 방언 원문

- `gyeongsang/academic/`: 학위논문·학술논문
- `gyeongsang/web/`: 웹 문서 저장본
- `gyeongsang/lexical/`: 로컬 어휘 자료

어휘 JSON은 `/home/ciot28/RAG_resource/경상도/어휘/gyeongsang_vocab.json`에서 복사한
작업 스냅샷이다. 라이선스와 개별 항목 출처 문제가 해결되지 않았으므로 Git에서
추적하거나 재배포하지 않는다.

## 방법론 및 양식

- [methodology/선행연구.md](methodology/선행연구.md): 보유 논문 11편의 검토 결과·서론 근거·설계 아이디어. 실험 재현이나 전 분야 조사 결과는 아님
- `methodology/kg/`: EDC·KAPING·SURGE·GraphRAG·온톨로지 논문 5편 + 동사 지식 구조화 참고 1편
- `methodology/knowledge_injection/`: LingoLLM·Can LLMs Help Create Grammar?·GRAMMAR-LLM 3편
- `methodology/low_resource/`: Grammar Book 연구 1편
- `methodology/dialect_generation/`: DIA-REFINE·피벗 기반 방언 번역 2편 + 방언 어미 문법 근거 1편
- `templates/`: 논문 제출 양식

추가 2편은 기존 네 카테고리 중 연구에서의 활용 역할에 따라 배치했다. `kg/unlockingverbs2025.pdf`는 Song 외(2025), *Unlocking Korean Verbs*로, 동사 문형·논항·예문 구조와 입력 분석을 참고하는 자료다. KG 구축 자체를 실험한 논문이라는 뜻은 아니다. `dialect_generation/georo2021.pdf`는 양지현(2021), 「경남방언 어말어미 ‘-거로’에 대해서」로, 생성 실험 논문이 아니라 방언 형태·용법의 직접 근거다. 두 경로는 `methodology/` 기준이며, 기존 11편과 합쳐 PDF는 총 13편이다.

PDF도 라이선스상 Git에서 추적하지 않는다. Claim에는 원문 전체를 복제하지 않고 정확한
위치와 필요한 최소 근거만 기록한다.

방법론 논문 11편과 문법 지식 작성에 사용하는 원문 7종은 역할이 다르다. 현재 새 작성본은
`current_kg/grammar/`이며, 폐기한 Claim 추출 이력을 재사용하지 않는다. 자료 목록은 `current_kg/grammar/source_registry.json`이다.
AI-Hub는 문법 근거가 아닌 독립 평가 후보로 유지한다. 약 100문장 예비 진단을 위한 파생
문장쌍 역시 Git에 올리지 않고 `current_kg/experiments/`의 구성 스크립트만 추적한다.

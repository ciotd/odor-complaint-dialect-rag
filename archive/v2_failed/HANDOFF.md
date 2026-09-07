# v2-graph 세션 인수인계 (구버전 — 아래 경고 참조)

> ⚠️ **이 문서는 폐기됐다 (2026-08-31).** 아래 내용은 실행된 적 없는 설계를 기술하고 있고,
> 재현 명령·서버 주소·평가셋 성격이 모두 현재와 다르다.
> **새 세션은 [`RESET_2026-08-31.md`](../../current_kg/docs/RESET_2026-08-31.md)를 읽을 것.**
> 무엇이 왜 틀렸는지는 그 문서 §9에 정리돼 있다.

작성 2026-08-27. 새 세션/작업자는 이 문서 → PROGRESS.md → README.md 순으로 읽으면 이어서 진행 가능.

## 한 줄
경북 방언 문법을 KG로 구축 → **표준어→경상 방언 발화 변환**. **광범위 치환(어휘·음운·조사) +
조건부 종결어미 KG**를 얹어 **ablation(치환만 vs 치환+KG)으로 KG 순수 기여 측정.** training-free.
(v1=악취 RAG 연구와 별개. v1 보관 문서 = `../v1_retrieval/docs/research_scope.md`.)

## 읽을 순서
1. **이 문서(HANDOFF)** — 현재 상태·다음 액션
2. **PROGRESS.md** — 빌드 순서(1~12)·타임라인·다음 할 일
3. **README.md** — 정본(과제·스코프·평가·결정로그 상세)
4. docs/kg_schema.md, kg_nodes_*.md — KG 스키마·규칙
5. ../../PROJECT_MAP.md — 현재 전체 지도

## 현재 상태 (2026-08-27)
- ✅ KG: `data/kg_rules.jsonl` (종결어미 39 + 음운 14, domain 필드)
- ✅ 치환 로더: `src/substitution.py` (어휘·문법flat, v1 자원 런타임 참조)
- ✅ 자질추출: `src/convert_prototype.py` (kiwi + STD_ENDING, AI-Hub 85% 커버)
- ✅ 평가셋 (실제 데이터, gitignore → 스크립트 재현):
  - `data/eval_pairs.jsonl` = AI-Hub 60 (일반35+의문25, 표준+방언정답+유형) ← `build_eval_set.py`
  - `data/eval_odor.jsonl` = v1 악취 민원인 발화 40 (judge 전용) ← `build_eval_odor.py`
- ✅ ablation 파이프라인: `src/run_ablation.py` (치환만/치환+KG/치환+덤프)
- ⏸ **미실행: 로컬 vLLM(192.168.100.1:8001) 다운.** 서버 떠야 생성 가능.
- ⬜ eval/judge 스크립트: **아직 안 만듦** (raw 결과 육안 확인 후 설계하기로 — 사용자 결정)

## 정확한 다음 액션 (서버 뜨면)
```
1) 서버 확인:  curl -s http://192.168.100.1:8001/v1/models   (또는 포트 체크)
2) 생성 실행:
   python src/run_ablation.py                                  # AI-Hub 60
   python src/run_ablation.py data/eval_odor.jsonl             # 악취 40
   → results/ablation_eval_pairs.jsonl, ablation_eval_odor.jsonl
3) raw 출력 육안검증 (치환만/치환+KG/치환+덤프 실제 차이 확인)  ← 사용자와 함께
4) 본 걸 근거로 eval/judge 스크립트 설계·작성:
   - A(정답대조, AI-Hub, 로컬): 어미 일치율(주) + 유사도(보조), 유형별(전체/의문) 분해
   - B(LLM judge, Claude 독립): 치환+KG vs 치환만 / vs 덤프, 쌍대·블라인드·승률
5) 집계·해석 (KG 순수 기여? focused>덤프? 의문셋에 집중되나? — 정직하게)
```

## 재현 주의 (gitignore된 것)
- eval_pairs.jsonl / eval_odor.jsonl (AI-Hub·v1 파생, 저작권) → **build_*.py로 재생성.**
- 원본: `../../../dialect_corpus/aihub/*.zip`, `../v1_retrieval/results/s2_20260818_135335.jsonl` 필요.
- 방언학 논문 PDF(로컬만), `../v1_retrieval/data/dialect_kb/`(v1 KB, 라이선스상 gitignore).

## 작업 규율 (사용자 요구 — 꼭 지킬 것)
- **새 설계·분석은 과정(방법·기준)을 먼저 공유·점검한 뒤 진행.** 완성본 투척 금지, 하나씩.
- **사실=논문/데이터, 구조화=AI, 검증=사용자.** 출처 없는 규칙 금지.
- **cherry-picking 경계:** 방법 유리하게 스코프 좁히지 말 것(이 함정으로 한 번 방향 틀었음).
- 매 단계 PROGRESS.md 갱신.

## 열린 이슈
- KG 강점(판정/설명)은 자연 데이터에 희소 → 의문셋(25)으로 확보했으나, KG 순수기여가 작게 나올 수 있음(정직 보고).
- 연결어미 체계 = gap(소스 없음, future). 조사·음운 일부는 flat 치환.
- ⚠️ **보안 TODO:** GitHub PAT가 노출됐었음 → 토큰 폐기+재발급 필요(다음 push 전).

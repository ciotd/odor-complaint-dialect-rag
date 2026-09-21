# 현재 문법 KG 작업 안내

최종 갱신: 2026-09-18. 새 안내 문서를 늘리지 않고 이 README와 기존 문서를 갱신한다.

## 먼저 볼 파일

**전체 검수를 마친 완성본은 아직 없다. 현행 지식은 `grammar/`에 있다.**

| 목적 | 파일 |
|---|---|
| 지금까지 작성한 지식 전체 | [records.jsonl](grammar/records.jsonl): 331건의 통합 기록. 한 줄에 한 기록 |
| 문헌 간 연결까지 포함한 그래프 전체 | [grammar.graph.json](grammar/grammar.graph.json) |
| 미완료·충돌·연결 판단 | [작성검토.md](grammar/작성검토.md) |
| 원문 대조·작성·통합 방법 | [구축방법.md](docs/구축방법.md) |

JSON은 기계 처리용이다. 특정 기록을 자세히 읽을 때는 records.jsonl의 `authored_file`이 가리키는 [authored/](grammar/authored/) 원본을 본다. [triples.tsv](grammar/triples.tsv)는 관계를 표로 훑는 용도이며 조건 전체를 담지는 않는다.

## 원본과 산출물

```text
sources/의 원문 PDF + grammar/source_registry.json
  ↓ 직접 읽고 작성
 grammar/authored/*.json    개별 지식 수정 원본 (20개 작성 묶음)
 grammar/integration.json   문헌 간 연결·문제·구간 장부 수정 원본
  ↓ grammar/build.py
 grammar/records.jsonl      통합 기록
 grammar/grammar.graph.json 문헌 간 연결까지 포함한 그래프
  ↓ 조회·집계
 grammar/*.results.json    특정 실행의 조회·점검 결과
 grammar/작성검토.md        작성 공백과 연결 검토 보고
```

20개 작성 파일은 별개의 최종 KG가 아니다. 내용은 authored에서, 통합 관계는 integration.json에서 수정한 뒤 출력한다. records.jsonl만으로 통합 관계 전체를 대신할 수 없다.

## 현재 상태

직접 방언 근거 7종·474쪽을 대상으로 331건을 작성했다. 그래프는 5,527노드·13,803엣지이며 문법 진술 1,033개와 통합 관계 50개를 포함한다. 작성자 원문 대조 표시 300건, 재검토 31건이다. 독립 검토·생성 승인·새 KG 생성 비교는 미실시다. 전체 원문의 개별 설명·표·각주 전수 대조와 작성은 미완료다.

숫자는 [progress.json](grammar/progress.json), 문제 목록은 [작성검토.md](grammar/작성검토.md)를 따른다. 노드 수·테스트 통과·쪽별 상태는 언어학적 정확성이나 원문 포괄률이 아니다.

## 남아 있는 폴더

| 폴더 | 역할 |
|---|---|
| `grammar/` | 현행 작성 원본·규격·그래프·검사 코드·결과 |
| `docs/` | 현행 구축방법·전체원문검토와 과거 설계·자료 검토 이력. 과거 문서는 현행 실행 지시가 아님 |
| `experiments/` | 모델 연결 점검 이력과 AI-Hub 평가 후보 구성. 현행 KG 효과 검증 결과는 아님 |

현재 KG의 이전 claims·design_probe 구현과 산출물을 정리했다. 설계·원문 검토 문서와 docs/history는 논문 근거 추적을 위해 보존한다. 현행 자료 통제표는 [grammar/source_registry.json](grammar/source_registry.json)으로 이동했다. 프로젝트 루트의 archive에는 v1/v2 코드·문서·실험 이력을 보존한다. 논문의 동기·시행착오·오류 분석에 활용하며 현행 KG와 구분한다.

## 원문 검수 방법과 다음 작업

7종 전체를 절·표·각주 단위로 대조한다. 원문에서 기록으로 확인해 누락을 찾고, 기록에서 원문으로 되짚어 오해·과장·근거 없는 조건을 찾는다. 항목별로 원문 위치, 대응 기록·관계, 유지/보완/신규/배경/보류/제외 판정과 이유를 남긴다. 목록만 만들지 않고 누락 작성과 조건 보완을 함께 진행한다.

첫 범위는 조현준 PDF 56–103쪽이다. 전체 작업의 시작 구간이며 나머지 자료도 모두 대조해야 한다. 문헌 간 연결은 양쪽 원문을 함께 확인하고 기능 공유·동일 용법 후보·활용 참조·충돌을 구별한다. 원문에 없는 조건은 공백으로 남긴다. 이번 폴더 정리는 전수 검수 수행이 아니다.

## 검사 코드와 저장 결과

| 코드·기준 | 확인 내용 | 결과 위치 |
|---|---|---|
| [record.schema.json](grammar/record.schema.json), [analysis_contract.json](grammar/analysis_contract.json), [build.py](grammar/build.py) | 형식·참조·상태·입력 연결 규격, 그래프 구성 및 재현 | check는 터미널 출력 |
| [test_build.py](grammar/test_build.py) | 30개: 형식·참조·예문·그래프·기존 교정 유지 | unittest 터미널 출력 |
| [test_query_review.py](grammar/test_query_review.py) | 9개: 수동 조건 조회와 연결 제거 | unittest 터미널 출력 |
| [test_integration.py](grammar/test_integration.py) | 18개: 문헌 간 경로·보류·기존 교정 유지 | unittest 터미널 출력 |
| [query_review.py](grammar/query_review.py) | 지정한 의문·높임 조건으로 제한적 조회 | [query_review.results.json](grammar/query_review.results.json) |
| [integration_review.py](grammar/integration_review.py) | 지정한 시작 용법·관계 순서의 경로 조회 | [integration_review.results.json](grammar/integration_review.results.json) |
| [authoring_audit.py](grammar/authoring_audit.py) | 작성 공백·조건·통합 관계 집계 | [authoring_audit.results.json](grammar/authoring_audit.results.json), [작성검토.md](grammar/작성검토.md) |

57개는 테스트 함수 수이며 문법 정답 57개를 검증한 뜻이 아니다. 같은 작성자의 데이터와 예상값을 비교하므로 동일한 해석 오류를 공유할 수 있다. authoring_audit 전용 테스트는 현재 없다. 세 results.json에는 그래프 해시가 있지만 57개 테스트 전체의 성적표는 아니다. --save는 동일 파일을 덮어쓰며 누적 실행 이력을 만들지 않는다.

build check는 records.jsonl, grammar.graph.json, triples.tsv, progress.json, gaps.json, analysis_links.json, example_review.md의 7개 산출물을 원본에서 다시 구성해 비교한다. ontology.json은 prepare가 출력하며 이 비교 목록에 포함되지 않는다. status는 저장된 progress 요약일 뿐 새 검증이 아니다. check가 PDF 전체를 새로 읽고 언어학적 판단을 하지는 않는다.

```bash
/usr/bin/python3 current_kg/grammar/build.py check
/usr/bin/python3 -m unittest discover -s current_kg/grammar -p 'test_*.py'
git diff --check
```

작성 원본을 변경한 뒤에만 필요한 파생 산출물을 갱신한다. 이전 결과를 논문 증거로 사용할 경우 먼저 버전과 실행 조건을 보존한다.

```bash
/usr/bin/python3 current_kg/grammar/build.py export
/usr/bin/python3 current_kg/grammar/authoring_audit.py --save
/usr/bin/python3 current_kg/grammar/integration_review.py --save
/usr/bin/python3 current_kg/grammar/query_review.py --question-type content --speech-level HAGECHE --save
```

## 평가·자료 정책

문법 지식은 Codex/Astra가 원문을 직접 검토해 작성한다. Qwen3.8-27B는 생성 실험 대상으로 두며 실험 전 실제 체크포인트·설정을 확인한다. 입력 분석기·DB 제품·평가 방법은 미확정이다. 목표는 일반적인 표준어→경상도 방언 변환이며 부산·악취 민원으로 한정하지 않는다.

[experiments/build_baseline_testset.py](experiments/build_baseline_testset.py)와 로컬 문장쌍은 AI-Hub 예비 평가 후보이다. 선별·문장 경계·화자·누수 점검이 필요하며 문법 근거나 확정 정답셋이 아니다. PDF·파생 문장쌍·어휘 원본·인증정보는 Git 재배포 대상에서 제외한다.

## 정리 이력

2026-09-18 사용자 요청에 따라 폐기된 방식을 작업 트리에서 제거하고 기존 문서를 갱신하는 정책으로 변경했다. 앞서 별도 생성한 검사전체목록.md는 이 README로 통합했다. 기존 코드·문서의 과거 버전은 Git 이력에서 확인할 수 있다. 삭제 범위를 v1/v2 연구 이력까지 확대한 것은 에이전트의 오해였다. 사용자 정정 후 archive의 추적 파일 전체와 과거 설계·자료 검토 문서를 복원했다. 현재 KG 초반의 중복·폐기 산출물 정리와 논문용 연구 이력 보존을 구별한다. 현행 grammar/retired는 빌드·검사에 필요한 제외 기록이므로 유지한다.

<details>
<summary>grammar 파일 전체 목록 펼치기</summary>


아래 표시 경로는 프로젝트 루트 기준이다. authored 20개와 retired 파일까지 포함했다. 자동 생성 캐시(__pycache__)는 연구 원본·결과가 아니므로 제외한다.

| 파일 | 역할 |
|---|---|
| [current_kg/grammar/analysis_contract.json](grammar/analysis_contract.json) | 입력 항목·값·적용 대상 규격. |
| [current_kg/grammar/analysis_links.json](grammar/analysis_links.json) | 관계의 입력 연결·조건·근거 출력. build.py check 재현 비교 대상. |
| [current_kg/grammar/authored/jo2018_01.json](grammar/authored/jo2018_01.json) | 직접 작성 문법 원본. 검증·그래프 생성 및 일부 테스트의 입력. |
| [current_kg/grammar/authored/jo2018_expansion_02.json](grammar/authored/jo2018_expansion_02.json) | 직접 작성 문법 원본. 검증·그래프 생성 및 일부 테스트의 입력. |
| [current_kg/grammar/authored/jo2018_expansion_03.json](grammar/authored/jo2018_expansion_03.json) | 직접 작성 문법 원본. 검증·그래프 생성 및 일부 테스트의 입력. |
| [current_kg/grammar/authored/namu_cross_categories_01.json](grammar/authored/namu_cross_categories_01.json) | 직접 작성 문법 원본. 검증·그래프 생성 및 일부 테스트의 입력. |
| [current_kg/grammar/authored/namu_grammar_expansion_02.json](grammar/authored/namu_grammar_expansion_02.json) | 직접 작성 문법 원본. 검증·그래프 생성 및 일부 테스트의 입력. |
| [current_kg/grammar/authored/namu_hage_questions_01.json](grammar/authored/namu_hage_questions_01.json) | 직접 작성 문법 원본. 검증·그래프 생성 및 일부 테스트의 입력. |
| [current_kg/grammar/authored/namu_honorific_compositions_02.json](grammar/authored/namu_honorific_compositions_02.json) | 직접 작성 문법 원본. 검증·그래프 생성 및 일부 테스트의 입력. |
| [current_kg/grammar/authored/namu_honorific_expansion_03.json](grammar/authored/namu_honorific_expansion_03.json) | 직접 작성 문법 원본. 검증·그래프 생성 및 일부 테스트의 입력. |
| [current_kg/grammar/authored/namu_honorifics_01.json](grammar/authored/namu_honorifics_01.json) | 직접 작성 문법 원본. 검증·그래프 생성 및 일부 테스트의 입력. |
| [current_kg/grammar/authored/namu_inflection_01.json](grammar/authored/namu_inflection_01.json) | 직접 작성 문법 원본. 검증·그래프 생성 및 일부 테스트의 입력. |
| [current_kg/grammar/authored/namu_interrogatives_01.json](grammar/authored/namu_interrogatives_01.json) | 직접 작성 문법 원본. 검증·그래프 생성 및 일부 테스트의 입력. |
| [current_kg/grammar/authored/namu_lexical_constructions_03.json](grammar/authored/namu_lexical_constructions_03.json) | 직접 작성 문법 원본. 검증·그래프 생성 및 일부 테스트의 입력. |
| [current_kg/grammar/authored/namu_overview_01.json](grammar/authored/namu_overview_01.json) | 직접 작성 문법 원본. 검증·그래프 생성 및 일부 테스트의 입력. |
| [current_kg/grammar/authored/namu_overview_expansion_02.json](grammar/authored/namu_overview_expansion_02.json) | 직접 작성 문법 원본. 검증·그래프 생성 및 일부 테스트의 입력. |
| [current_kg/grammar/authored/namu_phonology_01.json](grammar/authored/namu_phonology_01.json) | 직접 작성 문법 원본. 검증·그래프 생성 및 일부 테스트의 입력. |
| [current_kg/grammar/authored/namu_phonology_expansion_02.json](grammar/authored/namu_phonology_expansion_02.json) | 직접 작성 문법 원본. 검증·그래프 생성 및 일부 테스트의 입력. |
| [current_kg/grammar/authored/ryu2014_01.json](grammar/authored/ryu2014_01.json) | 직접 작성 문법 원본. 검증·그래프 생성 및 일부 테스트의 입력. |
| [current_kg/grammar/authored/ryu2014_conflict_03.json](grammar/authored/ryu2014_conflict_03.json) | 직접 작성 문법 원본. 검증·그래프 생성 및 일부 테스트의 입력. |
| [current_kg/grammar/authored/ryu2014_expansion_02.json](grammar/authored/ryu2014_expansion_02.json) | 직접 작성 문법 원본. 검증·그래프 생성 및 일부 테스트의 입력. |
| [current_kg/grammar/authored/yang2021_01.json](grammar/authored/yang2021_01.json) | 직접 작성 문법 원본. 검증·그래프 생성 및 일부 테스트의 입력. |
| [current_kg/grammar/authoring_audit.py](grammar/authoring_audit.py) | 작성 공백·통합 관계 집계 및 보고서 출력 구현. 자체 전용 test_authoring_audit.py는 없음. |
| [current_kg/grammar/authoring_audit.results.json](grammar/authoring_audit.results.json) | 작성 공백·재검토·구간별 기록·통합 문제 집계. audit --save 출력. |
| [current_kg/grammar/build.py](grammar/build.py) | 검증·그래프 생성·재현 비교 구현. GROUPS에 공통 개념 정의도 포함. |
| [current_kg/grammar/example_review.md](grammar/example_review.md) | 예문 및 검토 상태 보고. build.py check 재현 비교 대상; 자연스러움 평가 결과 아님. |
| [current_kg/grammar/gaps.json](grammar/gaps.json) | 명시된 미해결 사항 집계. build.py check 재현 비교 대상; 미발견 누락까지 검출하지 않음. |
| [current_kg/grammar/grammar.graph.json](grammar/grammar.graph.json) | 현행 그래프. build.py check 재현 비교 대상. |
| [current_kg/grammar/integration.json](grammar/integration.json) | 수동 연결 판단·근거·한계·문제·구간 장부의 원본. |
| [current_kg/grammar/integration_review.py](grammar/integration_review.py) | 지정된 관계 순서의 경로 조회와 보류 처리 구현. |
| [current_kg/grammar/integration_review.results.json](grammar/integration_review.results.json) | 저장된 GYS-R011:F1 → has_inflection_description → has_surface_form 조회 결과. 전체 경로 시험 이력 아님. |
| [current_kg/grammar/manifest.json](grammar/manifest.json) | 자료·쪽·해시 기준. check 실행 자체가 PDF 전체를 다시 추출·대조한다는 뜻은 아님. |
| [current_kg/grammar/ontology.json](grammar/ontology.json) | 공통 개념 출력. build.py prepare가 생성하며 check 재현 비교 7개 목록에는 포함되지 않음. |
| [current_kg/grammar/progress.json](grammar/progress.json) | 작성 상태·개수 집계. build.py check 재현 비교 대상; 포괄률·정확도 아님. |
| [current_kg/grammar/query_review.py](grammar/query_review.py) | 수동 조건 조회와 제한된 조건 판정 구현. |
| [current_kg/grammar/query_review.results.json](grammar/query_review.results.json) | 저장된 설명 의문(content)·하게체(HAGECHE) 조회 결과. 전체 조회 시험 이력 아님. |
| [current_kg/grammar/record.schema.json](grammar/record.schema.json) | 기록 형식 규격. validate_record의 추가 코드 검사와 함께 사용. |
| [current_kg/grammar/records.jsonl](grammar/records.jsonl) | 작성본을 합친 기록. build.py check 재현 비교 대상. |
| [current_kg/grammar/retired/context_records_2026-09-15.json](grammar/retired/context_records_2026-09-15.json) | 제외한 기록·판정 이력. 활성 그래프 재진입 방지 검사의 입력. |
| [current_kg/grammar/source_notes.json](grammar/source_notes.json) | 활성 생성 지식에서 분리한 출처·배경 설명. |
| [current_kg/grammar/test_build.py](grammar/test_build.py) | 30개 테스트. 기록 규격·그래프·예문·상태·기존 교정 유지. |
| [current_kg/grammar/test_integration.py](grammar/test_integration.py) | 18개 테스트. 통합 경로·보류·일부 기록값 유지. |
| [current_kg/grammar/test_query_review.py](grammar/test_query_review.py) | 9개 테스트. 수동 조건 조회와 연결 제거 시 동작. |
| [current_kg/grammar/triples.tsv](grammar/triples.tsv) | 문법·통합 관계 표. build.py check 재현 비교 대상. |
| [current_kg/grammar/work_plan.json](grammar/work_plan.json) | 과거 6종·452쪽 작업 계획. 일부 테스트 입력이며 최신 진행표가 아님. |
| [current_kg/grammar/작성검토.md](grammar/작성검토.md) | audit --save로 생성한 읽기용 보고. 독립 수동 검토 결과가 아님. |


| [current_kg/grammar/source_registry.json](grammar/source_registry.json) | 현행 자료 목록·정책. 폐기된 claims 폴더에서 이동. |

</details>

<details>
<summary>테스트 함수 57개 전체 목록 펼치기</summary>

### test_build.py — 30개

- `test_example_is_separate_from_source_evidence` — [test_build.py:36](grammar/test_build.py#L36)
- `test_example_unknown_relation_rejected` — [test_build.py:50](grammar/test_build.py#L50)
- `test_example_mismatched_focus_rejected` — [test_build.py:56](grammar/test_build.py#L56)
- `test_example_cannot_claim_naturalness_or_source_origin` — [test_build.py:62](grammar/test_build.py#L62)
- `test_null_example_requires_reason` — [test_build.py:69](grammar/test_build.py#L69)
- `test_general_rule_example_does_not_require_invented_form` — [test_build.py:76](grammar/test_build.py#L76)
- `test_null_focus_not_allowed_for_expression_relation` — [test_build.py:83](grammar/test_build.py#L83)
- `test_review_inventory_and_example_coverage` — [test_build.py:89](grammar/test_build.py#L89)
- `test_example_report_is_derived_from_records` — [test_build.py:117](grammar/test_build.py#L117)
- `test_retired_source_only_records_cannot_be_readmitted` — [test_build.py:128](grammar/test_build.py#L128)
- `test_concrete_uncertain_form_can_remain_held` — [test_build.py:135](grammar/test_build.py#L135)
- `test_six_context_records_reclassified_outside_graph` — [test_build.py:144](grammar/test_build.py#L144)
- `test_valid` — [test_build.py:163](grammar/test_build.py#L163)
- `test_context_can_use_concept_without_expression` — [test_build.py:166](grammar/test_build.py#L166)
- `test_unknown_concept_subject_rejected` — [test_build.py:179](grammar/test_build.py#L179)
- `test_front_section_source_spellings_regression` — [test_build.py:185](grammar/test_build.py#L185)
- `test_work_plan_covers_all_sources_without_claiming_completion` — [test_build.py:200](grammar/test_build.py#L200)
- `test_unknown_reference` — [test_build.py:215](grammar/test_build.py#L215)
- `test_unknown_region_not_universal` — [test_build.py:221](grammar/test_build.py#L221)
- `test_source_context_needs_evidence` — [test_build.py:227](grammar/test_build.py#L227)
- `test_context_only_evidence_rejected` — [test_build.py:233](grammar/test_build.py#L233)
- `test_bridge_must_name_condition_features` — [test_build.py:237](grammar/test_build.py#L237)
- `test_bridge_values_must_use_common_vocabulary` — [test_build.py:243](grammar/test_build.py#L243)
- `test_shared_concept_not_shared_sense` — [test_build.py:249](grammar/test_build.py#L249)
- `test_actual_manifest_complete_no_duplicates` — [test_build.py:265](grammar/test_build.py#L265)
- `test_no_network_or_model_runner` — [test_build.py:274](grammar/test_build.py#L274)
- `test_direct_authorship_and_conflict_not_promoted` — [test_build.py:286](grammar/test_build.py#L286)
- `test_unresolved_page_cannot_be_complete` — [test_build.py:295](grammar/test_build.py#L295)
- `test_two_documents_share_function_without_scope_merging` — [test_build.py:307](grammar/test_build.py#L307)
- `test_check_is_read_only` — [test_build.py:318](grammar/test_build.py#L318)

### test_integration.py — 18개

- `test_all_grammar_sources_have_authored_records` — [test_integration.py:16](grammar/test_integration.py#L16)
- `test_methodology_not_dialect_evidence` — [test_integration.py:19](grammar/test_integration.py#L19)
- `test_whole_page_inventory_without_gaps_or_duplicates` — [test_integration.py:22](grammar/test_integration.py#L22)
- `test_cross_source_inflection_paths_exist` — [test_integration.py:31](grammar/test_integration.py#L31)
- `test_removing_integration_edge_breaks_paths` — [test_integration.py:38](grammar/test_integration.py#L38)
- `test_removing_surface_edges_breaks_second_step` — [test_integration.py:44](grammar/test_integration.py#L44)
- `test_scope_tension_not_allowed_path` — [test_integration.py:49](grammar/test_integration.py#L49)
- `test_negative_function_is_explicit_not_positive_interpretation` — [test_integration.py:54](grammar/test_integration.py#L54)
- `test_market_example_not_required_place` — [test_integration.py:58](grammar/test_integration.py#L58)
- `test_integration_not_automatic_equivalence` — [test_integration.py:63](grammar/test_integration.py#L63)
- `test_unresolved_record_not_accepted_as_path` — [test_integration.py:70](grammar/test_integration.py#L70)
- `test_request_to_inflection_cross_document_path` — [test_integration.py:75](grammar/test_integration.py#L75)
- `test_removed_request_link_breaks_path` — [test_integration.py:80](grammar/test_integration.py#L80)
- `test_homograph_usage_nodes_are_separate` — [test_integration.py:85](grammar/test_integration.py#L85)
- `test_unseen_topics_not_turned_into_prohibition` — [test_integration.py:93](grammar/test_integration.py#L93)
- `test_nominal_future_has_explicit_components` — [test_integration.py:98](grammar/test_integration.py#L98)
- `test_ra_content_question_exception_is_example_not_global_rule` — [test_integration.py:103](grammar/test_integration.py#L103)
- `test_triple_export_has_only_semantic_or_integration_rows` — [test_integration.py:109](grammar/test_integration.py#L109)

### test_query_review.py — 9개

- `test_hage_content_follows_variant_and_qualification` — [test_query_review.py:27](grammar/test_query_review.py#L27)
- `test_polar_question_does_not_return_content_use` — [test_query_review.py:43](grammar/test_query_review.py#L43)
- `test_missing_level_is_unknown_not_permission` — [test_query_review.py:49](grammar/test_query_review.py#L49)
- `test_different_level_conflicts_only_with_base_use` — [test_query_review.py:52](grammar/test_query_review.py#L52)
- `test_removing_function_edge_changes_retrieval` — [test_query_review.py:55](grammar/test_query_review.py#L55)
- `test_removing_qualification_loses_composition` — [test_query_review.py:61](grammar/test_query_review.py#L61)
- `test_missing_condition_edge_is_not_unrestricted` — [test_query_review.py:68](grammar/test_query_review.py#L68)
- `test_removing_combination_breaks_semantic_path_not_record_link` — [test_query_review.py:74](grammar/test_query_review.py#L74)
- `test_unsupported_operator_is_unknown` — [test_query_review.py:82](grammar/test_query_review.py#L82)

</details>

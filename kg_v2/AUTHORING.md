# KG v2 작성 계약

이 버전은 `current_kg`를 수정하지 않는 별도 구축이다. 대상은 `source_registry.json`에 등록된 방언 근거 문헌 7종 전체다. 기존 KG를 변환하여 원문 재검토를 대신하지 않는다. 원문은 `local/pages.jsonl`에 PDF에서 새로 추출했다. 페이지 번호는 1부터 시작하는 **PDF 페이지**다.

문헌은 Astra가 읽고 진술을 작성한다. 검색·형식 검사·그래프 빌드는 코드가 수행한다. 코드가 추출한 문자열을 Astra가 의미 검토한 것으로 기록하지 않는다. 원문을 읽지 않은 페이지를 reviewed로 표시하지 않는다. 범위 내 모든 페이지를 읽고, 배경·목차·서지·빈 페이지도 페이지 대장에 남긴다. 문헌 전체를 읽는 것과 모든 문장에 담긴 지식을 완전하게 추출했다는 것은 구별한다.

## 산출물

- `authored/<작업명>.json`: `{"source_id": "...", "facts": [...]}`. 서로 다른 문헌은 파일을 나눈다.
- `reviews/<작업명>.json`: `{"source_id": "...", "pages": [...]}`. 페이지별 검토 결과.
- 작성자는 작업 범위 원문을 읽고 모든 중요한 어휘·문법·활용·조건·예외·변이·사용 범위 정보를 기록한다. 반복 설명은 같은 진술에 근거를 추가할 수 있다. 일반화할 수 없는 예문·통계·표·분석상의 논쟁도 reference_only 사실 또는 페이지별 명시적 검토 메모로 보존한다. 해석 불가능한 표·OCR은 gap으로 남긴다.

## 사실 형식

각 사실은 다음 필드를 모두 가진다. 모델이 작성한 표준어 풀이와 문헌에 실제 있는 표준어 대응을 구별한다.

```json
{
  "id": "SOURCE:v2:0001",
  "type": "lexical_mapping",
  "source_pattern": {"text": "표준어 또는 문헌의 분석 대상", "domain": "standard", "lemma": null, "sense": null, "features": {}},
  "target_pattern": {"text": "방언 후보 또는 설명 내용", "domain": "dialect", "lemma": null, "sense": null, "features": {}},
  "functions": [],
  "conditions": [{"owner": "input", "field": "person", "op": "eq", "value": 2, "basis": "explicit"}],
  "constraints": [{"kind": "scope", "description": "원문의 제한을 보존한 설명"}],
  "scope": {"regions": [], "speech_levels": [], "registers": [], "period": [], "note": "범위가 불명확하면 그 사실을 기재"},
  "evidence": [{"pdf_page": 1, "quote": "페이지에 실제 있는 짧은 근거 문자열"}],
  "claim_status": "source_generalization",
  "usability": "candidate",
  "notes": "필요한 해석·출처 중복·표준어 풀이의 작성 주체"
}
```

- `type`: lexical_mapping, inflection, ending, construction, particle, phonology, usage, constraint, context.
- `domain`: standard, dialect, shared, metalinguistic. 출처별 용법을 자동으로 같은 노드로 합치지 않는다.
- `claim_status`: source_generalization, attested_form, attested_example, author_hypothesis, secondary_report, analyst_interpretation, negative_example.
- `usability`: candidate, reference_only, blocked. candidate는 자동 생성 승인/현대 자연스러움 판정이 아니다.
- `conditions.owner`: input(원문), candidate(선택된 목표 표현), target(목표 말투), context(문헌·발화 상황).
- `conditions.op`: eq, in, not_in, exists. `basis`: explicit 또는 analyst_interpretation.
- `constraints.kind`: require, exclude, scope, uncertainty. 텍스트 제약이 남으면 조회기는 검토 필요 상태를 유지한다.
- 기능은 가능한 한 declarative, interrogative, polar_question, content_question, imperative, hortative, exclamative, request, intention, cause, condition, contrast, concession, quotation, negation, tense, aspect, honorification 등 의미를 드러내는 일관된 이름을 쓴다. 의미 없는 빈 기능도 허용한다.
- **자유로운 뜻풀이를 정확히 일치해야 하는 조건으로 만들지 않는다.** person/number/pos/question_type 등 판별 가능한 정보를 쓴다. 판단 불가 의미 구분은 source_pattern.sense와 uncertainty에 보존한다.
- inflection에서는 방언 어간 등 이미 선택한 표현의 조건을 candidate에 둔다. 입력이 처음부터 방언 어간이어야 한다고 요구하지 않는다.
- 원문의 실제 활용표 셀은 attested_form으로 저장한다. 그 형태 자체를 참고하는 것과 다른 어휘/어미에 일반화하는 것은 구분한다.
- source_pattern.text에 원문에 없는 표준어 풀이를 넣었다면 notes에 명시하고 claim_status를 analyst_interpretation으로 둔다. 실제 표준어 대응이 원문에 없으면 억지로 대응쌍을 만들지 않고 usage/context로 보존할 수 있다.
- evidence.quote는 실제 원문 문자열의 연속 부분이다. 공백·줄바꿈만 정규화해서 일치 여부를 검사한다. PDF 텍스트가 깨져 일치하지 않는 인용문을 추측하지 않는다. 인용은 필요한 최소 분량으로 제한한다.
- 표의 제목·행·열·각주를 함께 확인한다. 지역·시대·화자·높임 제약을 지우지 않는다. 원문 범위 밖의 일반화, 부정 예문을 긍정 규칙으로 전환, 위키의 재인용을 독립 근거로 계산하지 않는다.

## 페이지 검토 형식

```json
{"source_id":"SOURCE", "pages":[
  {"pdf_page":1,"disposition":"knowledge","fact_ids":["SOURCE:v2:0001"],"note":"무엇을 확인했는지", "gaps":[]}
]}
```

disposition은 knowledge, context, front_matter, bibliography, blank, mixed, unreadable 중 하나다. gaps에는 추출하지 못한 지식·표·불확실한 해석을 구체적으로 기록한다. 예문 전체를 검증된 번역 정답으로 주장하지 않는다. 범위 내 페이지가 누락되면 전체 검토 완료로 보고하지 않는다.

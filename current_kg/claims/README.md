# Claim 작업 영역

이 디렉터리에는 세 활성 문헌에서 새로 추출한 Claim만 저장한다. 과거 39규칙이나 기존
문법 JSON을 복사하거나 비교 기준으로 사용하지 않는다.

예정 구조:

```text
source_registry.json
claim_record_schema.json
raw/
  jo2018_claims.jsonl
  ryu2014_claims.jsonl
  namuwiki_20260901_claims.jsonl
review/
```

JSONL은 KG 자체가 아니라 출처 기반 Claim 장부이다. 사용자 검토가 끝나기 전에는
Claim을 운영 Rule로 승격하지 않는다.

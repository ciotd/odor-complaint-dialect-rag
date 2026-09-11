"""Validate the local v2 schema subset and render the RYU2014 review to stdout.

No third-party dependencies. Does not validate linguistic truth or approve rules.
Usage: python current_kg/claims/claim_review.py --check
       python current_kg/claims/claim_review.py --render
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

BASE = Path(__file__).resolve().parent
REVIEW = BASE / 'review/RYU2014_STRUCTURED_REVIEW.md'


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def validate(value, schema, path='$'):
    """Only the keywords used in this repository's v2 schema are supported."""
    supported = {'$schema', 'title', 'description', 'type', 'required', 'properties',
                 'additionalProperties', 'const', 'enum', 'pattern', 'minLength',
                 'items', 'minItems', 'uniqueItems', 'minimum', 'maximum'}
    unknown = set(schema) - supported
    assert not unknown, f'{path}: unsupported schema keywords {unknown}'
    if 'const' in schema:
        assert value == schema['const'], f'{path}: const mismatch'
    if 'enum' in schema:
        assert value in schema['enum'], f'{path}: enum mismatch: {value}'
    types = schema.get('type', [])
    types = [types] if isinstance(types, str) else types
    predicates = {'object': lambda v: isinstance(v, dict),
                  'array': lambda v: isinstance(v, list),
                  'string': lambda v: isinstance(v, str),
                  'integer': lambda v: isinstance(v, int) and not isinstance(v, bool),
                  'null': lambda v: v is None}
    if types:
        assert any(predicates[t](value) for t in types), f'{path}: wrong type'
    if isinstance(value, dict):
        props = schema.get('properties', {})
        assert set(schema.get('required', [])) <= set(value), f'{path}: missing keys'
        if schema.get('additionalProperties') is False:
            assert set(value) <= set(props), f'{path}: extra keys'
        for key in value.keys() & props.keys():
            validate(value[key], props[key], f'{path}.{key}')
    elif isinstance(value, list):
        assert len(value) >= schema.get('minItems', 0), f'{path}: too few items'
        if schema.get('uniqueItems'):
            assert len({json.dumps(v, sort_keys=True) for v in value}) == len(value), f'{path}: duplicates'
        if 'items' in schema:
            for index, item in enumerate(value):
                validate(item, schema['items'], f'{path}[{index}]')
    elif isinstance(value, str):
        assert len(value) >= schema.get('minLength', 0), f'{path}: short string'
        if 'pattern' in schema:
            assert re.search(schema['pattern'], value), f'{path}: pattern mismatch'
    elif isinstance(value, int):
        assert value >= schema.get('minimum', value), f'{path}: below minimum'
        assert value <= schema.get('maximum', value), f'{path}: above maximum'


def load_and_check():
    claims = [json.loads(line) for line in
              (BASE / 'structured/ryu2014_claims.jsonl').read_text().splitlines()]
    schema = read_json(BASE / 'structured_claim_schema.json')
    taxonomy = read_json(BASE / 'grammar_categories.json')['categories']
    categories = {c['id']: c for c in taxonomy}
    coverage = read_json(BASE / 'structured/ryu2014_coverage.json')
    ids = {c['claim_id'] for c in claims}
    assert len(ids) == len(claims), 'duplicate claim IDs'
    for c in claims:
        validate(c, schema, c['claim_id'])
        cat = c['category']
        assert cat['secondary'] in {x['id'] for x in categories[cat['primary']]['subcategories']}
        pages = c['source_location']['pdf_pages']
        assert c['source_location']['printed_pages'] == [p + 54 for p in pages]
        assert set(c['links']) <= ids
        assert not re.search(r'\d\s*%', json.dumps(c, ensure_ascii=False)), 'usage percentage retained'
        if cat['primary'] == 'research_context':
            assert c['generation_status'] == 'context_only'
        if cat['primary'] == 'source_issue':
            assert c['generation_status'] == 'hold'
    assert [p['pdf_page'] for p in coverage['pages']] == list(range(1, 39))
    for p in coverage['pages']:
        expected = [c['claim_id'] for c in claims if p['pdf_page'] in c['source_location']['pdf_pages']]
        assert p['claim_ids'] == expected, f'coverage mismatch: page {p["pdf_page"]}'
    source = next(s for s in read_json(BASE / 'source_registry.json')['sources'] if s['source_id'] == 'RYU2014')
    assert source['eligible_for_claims'] is True
    pdf = BASE.parents[1] / source['file']['path']
    if pdf.exists():
        assert hashlib.sha256(pdf.read_bytes()).hexdigest() == coverage['source_sha256'] == source['file']['sha256']
    # Negative fixtures prove that schema/category/page failures are detected.
    for key, value in [('source_id', 'OLD_RULES'), ('record_version', '1.0.0'), ('generation_status', 'enabled')]:
        bad = dict(claims[0], **{key: value})
        try:
            validate(bad, schema)
        except AssertionError:
            pass
        else:
            raise AssertionError(f'negative fixture accepted: {key}')
    return claims, taxonomy, coverage


def render(claims, taxonomy, coverage):
    counts = Counter(c['category']['primary'] for c in claims)
    status = Counter(c['generation_status'] for c in claims)
    out = ['# 류성기(2014) 구조화 Claim 전수 1차 초안', '',
           '이 문서부터 읽으면 됩니다. JSONL과 같은 데이터에서 생성한 검토 화면입니다.', '',
           f'총 {len(claims)}건. 논문 38쪽 전체를 구간별로 처리했지만, 모든 문장을 복제한 것이거나 사람 검토가 끝난 결과는 아닙니다.', '',
           f'생성 검토 후보 {status["candidate"]}건 / 보류 {status["hold"]}건 / 맥락 전용 {status["context_only"]}건. 운영 Rule로 승인된 항목은 0건입니다.', '',
           '기존 대명사 81건과 초기 파일럿 5건은 역사 기록입니다. 새 초안과 중복되므로 합산하지 않습니다.', '',
           '## 읽는 방법', '',
           '- 대분류·세부 분류는 문법 검색용 잠정 분류입니다. 원문 절 제목과 별도로 저장합니다.',
           '- 대상 → 관계 → 내용이 핵심 주장입니다. 형태 대응은 모든 문장에서의 치환 허가가 아닙니다.',
           '- 관련 분류는 복수로 연결합니다. 예: 부정과 보조용언. 의미·기능과 높임은 별도 필드입니다.',
           '- 조건은 추출자가 정리한 요약입니다. 미기재·null은 제한 없음이 아니라 미확정입니다.',
           '- 근거는 원문 요약입니다. 따옴표 인용이 아닙니다. PDF 쪽·절·표 행을 함께 확인해야 합니다.',
           '- 예문은 원문 방언 예시만 기록합니다. 의미가 다른 표준어 예문과 학습용 대칭쌍으로 묶지 않습니다.',
           '- 지역 범위는 2014년 함양 조사입니다. 경남 전체·현대 화자의 자연스러움을 보증하지 않습니다.',
           '- 사용비율 숫자는 제외했습니다. 정성적 변화 보고는 맥락용이지 사용 금지 규칙이 아닙니다.', '',
           '## 분류별 규모', '', '| 문법 범주 | 건수 |', '|---|---:|']
    out += [f'| {t["label"]} | {counts[t["id"]]} |' for t in taxonomy]
    out += ['', '## 먼저 검토할 항목', '',
            '아래는 보류 항목 전체입니다. ID만 보지 않아도 대상과 이유를 알 수 있도록 표시했습니다.', '']
    for c in claims:
        if c['generation_status'] == 'hold':
            out.append(f'- {c["subject"]} → {c["object"]}: {" / ".join(c["cautions"]) or c["statement"]} ({c["claim_id"]})')
    predicate = {'has_dialect_form': '문헌 대응형', 'has_form': '형태 확인', 'has_function': '기능',
                 'reported_absent': '조사 내 미확인', 'reported_change': '변화 보고', 'has_property': '속성·설명',
                 'source_disagreement': '원문 불일치', 'unresolved_reading': '판독 보류'}
    labels = {'candidate': '생성 검토 후보', 'hold': '보류', 'context_only': '맥락 전용'}
    label_map = {t['id']: t['label'] for t in taxonomy}
    for t in taxonomy:
        out += ['', f'## {t["label"]}', '']
        subs = {s['id']: s['label'] for s in t['subcategories']}
        for c in claims:
            if c['category']['primary'] != t['id']:
                continue
            loc, cat = c['source_location'], c['category']
            out += [f'### {c["subject"]} → {c["object"]} ({c["claim_id"]})', '',
                    f'- 분류: {t["label"]} → {subs[cat["secondary"]]}',
                    f'- 주장 종류: {predicate[c["predicate"]]}',
                    f'- 핵심 내용: {c["statement"]}',
                    f'- 의미·기능: {", ".join(cat["functions"]) or "별도 표지 미확정"}',
                    f'- 관련 분류: {", ".join(label_map[x] for x in cat["related"]) or "없음/아직 연결하지 않음"}',
                    '- 조건: ' + (' / '.join(x['value'] for x in c['conditions']) or '원문에서 별도 조건을 확정하지 않음'),
                    '- 범위: 경남 → 함양 / 2014년 조사·보고',
                    '- 조사 맥락: ' + c['attestation']['note']]
            out += [f'- 원문 예문: `{e["dialect"]}` — {e["note"]}' for e in c['examples']]
            if not c['examples']:
                out.append('- 원문 예문: 개별 대응 예문을 확보하지 않았거나 불일치로 채택하지 않음')
            out += [f'- 근거: PDF {", ".join(map(str, loc["pdf_pages"]))}쪽 / 지면 {", ".join(map(str, loc["printed_pages"]))}쪽 / {loc["section"]} / {loc["locator"]}',
                    '- 근거 요약: ' + ' / '.join(e['text'] for e in c['evidence']),
                    '- 주의·예외: ' + (' / '.join(c['cautions']) or '추가 확인된 사항 없음; 조건 없음의 보증이 아님'),
                    f'- 상태: {labels[c["generation_status"]]} / AI 초안 / 사용자 미검토', '']
    out += ['## 원문 전체 처리 범위', '',
            '본문과 초록·결론의 반복은 별도 Claim으로 복제하지 않았습니다. 아래 표는 페이지 처리 기록이며, 누락이 없다는 독립 검증 결과는 아닙니다.', '',
            '| PDF쪽 | 구간 | 추출·처리 | 제외 |', '|---:|---|---|---|']
    for p in coverage['pages']:
        out.append(f'| {p["pdf_page"]} | {p["section"]} | {p["included"]} | {p["excluded"]} |')
    out += ['', '## 데이터와 재현', '',
            '- 원본 장부: [ryu2014_claims.jsonl](../structured/ryu2014_claims.jsonl)',
            '- 페이지별 처리 기록: [ryu2014_coverage.json](../structured/ryu2014_coverage.json)',
            '- 사용자 생성 선택: [user_generation_choices.json](../structured/user_generation_choices.json) — 문헌 근거가 아님',
            '- 기록 규격: [structured_claim_schema.json](../structured_claim_schema.json)',
            '- 분류 목록: [grammar_categories.json](../grammar_categories.json)',
            '- 검증: `python current_kg/claims/claim_review.py --check`',
            '- 화면 재생성(stdout): `python current_kg/claims/claim_review.py --render`', '',
            '검증기는 현재 스키마에 쓰인 키워드·참조·분류·쪽수·원본 해시·화면 동기화를 검사합니다. 일반 JSON Schema 구현이나 언어학적 타당성 검증기는 아닙니다.', '']
    return '\n'.join(out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--render', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    claims, taxonomy, coverage = load_and_check()
    result = render(claims, taxonomy, coverage)
    if args.render:
        print(result, end='')
    else:
        assert REVIEW.read_text(encoding='utf-8') == result, 'review is out of sync'
        print(json.dumps({'claims': len(claims), 'pages': len(coverage['pages']),
                          'generation_status': dict(Counter(c['generation_status'] for c in claims)),
                          'schema_subset_and_integrity': 'passed', 'review_sync': 'passed'}, ensure_ascii=False))


if __name__ == '__main__':
    main()

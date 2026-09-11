"""Validate and audit the first extraction draft; no writes or model calls."""
import copy
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'design_probe'))
from probe import Graph, require, validate


def run():
    data = json.loads((HERE / 'namu_grammar_batch_001.json').read_text())
    ledger = json.loads((HERE / 'namu_grammar_batch_001.coverage.json').read_text())
    schema = json.loads((HERE / 'bundle.schema.json').read_text())
    registry = json.loads((HERE.parent / 'source_registry.json').read_text())
    validate(data, registry, schema=schema)
    graph = Graph(data, registry)
    source_id = ledger['source_id']
    src = next(s for s in registry['sources'] if s['source_id'] == source_id)
    root = HERE.parents[2]
    digest = hashlib.sha256((root / src['file']['path']).read_bytes()).hexdigest()
    checks = []

    def check(label, expected, actual):
        require(expected == actual, label + ': mismatch')
        checks.append({'test': label, 'expected': expected, 'actual': actual})

    check('원본 hash', src['file']['sha256'], digest)
    check('처리 장부와 Claim ID 일치', ledger['claim_ids'], [c['id'] for c in data['claims']])
    check('정식 추출 초안과 시험 데이터 구별', 'extraction_draft', data['status'])
    forms = []
    entities = {e['id']: e for e in data['entities']}
    evidence = {e['id'] for e in data['evidence']}
    for c in data['claims']:
        for a in c['assertions']:
            content = a['content']
            if 'paradigm' not in content:
                continue
            require(len(content['headers']) == 8, 'expected eight source columns')
            for row in content['paradigm']:
                require(row['usage_ref'] in entities, 'paradigm usage ref missing')
                require(entities[row['usage_ref']]['properties']['lemma'] == row['lemma'], 'lemma mismatch')
                require(len(row['forms']) == len(content['headers']), 'table column mismatch')
                require(all(type(cell) is list and cell and all(type(x) is str and x for x in cell)
                            for cell in row['forms']), 'empty or invalid table cell')
                forms.append(row)
    for e in entities.values():
        if 'evidence_refs' in e['properties']:
            require(all(r in evidence for r in e['properties']['evidence_refs']), 'entity evidence ref')
    check('표제어 수', 21, len(forms))
    check('표 칸 수', 168, sum(len(r['forms']) for r in forms))
    du = next(r for r in forms if r['lemma'] == '두다')
    check('두다 과거 원문 표기', ['돘다', '둤다'], du['forms'][3])
    si = next(r for r in forms if r['lemma'] == '시다')
    check('시다의 미제시 ㅔ형 미추가', ['시'], si['forms'][0])
    c1 = data['claims'][0]['id']
    check('일반 설명에 지역·모호한 단서 연결',
          [source_id + '-C0002', source_id + '-C0003'], graph.neighbors(c1, 'qualifies', True))
    short = data['claims'][2]['assertions'][0]
    check('모호한 길이 단서를 기계 조건으로 만들지 않음', None, short['condition'])
    check('모호한 길이 단서 운영화 금지', False, short['content']['operationalized'])
    condition = graph.neighbors(data['claims'][5]['assertions'][0]['id'], 'condition')[0]
    target = data['claims'][5]['target_refs'][0]
    facts = {target: {'following_ending_family': '-아/어', 'final_morpheme_syllable_class': '2음절 이상',
                      'stem_final_vowel': 'ㅜ', 'stem_has_coda': False}}
    check('다음절 ㅜ형 조건의 AND 연결', True, graph.evaluate(condition, facts))
    del facts[target]['final_morpheme_syllable_class']
    check('마지막 형태소 길이 미확보는 허용 아님', None, graph.evaluate(condition, facts))
    check('지역 미지정 생성 우선순위 보류', 'undetermined', data['policies'][0]['priority'])
    check('6–7쪽을 추출 완료로 표시하지 않음', [6, 7], ledger['read_not_extracted_body_pages'])
    check('근거가 모두 승인된 문헌', [source_id], sorted({e['source_id'] for e in data['evidence']}))
    check('검토 주체가 독립 검증인 척하지 않음', False, ledger['audit']['independent_reviewer'])
    changed = copy.deepcopy(data)
    changed['status'] = 'design_test_only'
    try:
        validate(changed, registry, schema=schema)
    except ValueError:
        rejected = True
    else:
        rejected = False
    check('시험 상태를 정식 추출 파일에 잘못 넣으면 차단', True, rejected)
    return {'status': 'passed', 'claims': len(data['claims']), 'checks': checks,
            'graph_nodes': len(graph.nodes), 'graph_edges': len(graph.edges),
            'scope': 'PDF3–5 고유 규칙 활용 및 관련 각주 초안; 미결 항목 있음',
            'not_proven': ['언어학적 정답', '현대 자연스러움', '문헌 무누락', '생성 효과']}


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False, indent=2))

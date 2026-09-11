"""Cross-category regression and negative-input checks. No output files written."""
import copy
import json

from probe import BASE, Graph, require, run_checks, validate
from schema_check import validate_schema


def run():
    data = json.loads((BASE / 'coverage_claims.json').read_text())
    registry = json.loads((BASE.parent / 'claims/source_registry.json').read_text())
    baseline = run_checks(data, registry)
    graph = Graph(data, registry)
    checks = []

    def check(name, expected, actual):
        require(expected == actual, f'{name}: expected {expected!r}, got {actual!r}')
        checks.append({'test': name, 'expected': expected, 'actual': actual})

    def phase(claim):
        values = [graph.nodes[i]['properties']['value']
                  for i in graph.neighbors(claim, 'annotated_by')
                  if graph.nodes[i]['properties']['dimension'] == 'usage_context']
        return values[0]['description_phase']

    def scoped_assertions(target, requested_phase):
        out = []
        for aid in graph.assertions(target):
            for cid in graph.neighbors(aid, 'asserts', True):
                if phase(cid) == requested_phase:
                    out.append(graph.nodes[aid]['properties']['kind'])
        return sorted(out)

    check('부정의 두 기술 단계를 연결', ['R02'], graph.neighbors('R01', 'usage_change_relative_to', True))
    check('초기 방언형과 후속 설명 구별', ['scoped_inventory'], scoped_assertions('r.f.지 못하다', '초기 방언형 기술'))
    check('후속 세대에서는 등장 설명 조회', ['reported_emergence'], scoped_assertions('r.f.지 못하다', '후속 세대 사용 설명'))
    check('제시하지 않은 현대 단계에는 결과 없음', [], scoped_assertions('r.f.지 못하다', '2026년 일반 경상도'))
    check('못하다 등장 대상 세대', ['60대', '10대'], graph.nodes['r.a.later.cannot']['properties']['content']['speaker_groups'])
    check('않다 등장 대상 세대 구별', ['10대'], graph.nodes['r.a.later.not']['properties']['content']['speaker_groups'])
    check('현재형 미래 표현의 동반 표현 유지', '내일과 같은 명사', graph.nodes['r.a.future']['properties']['content']['alternatives'][1]['cooccurrence'])
    check('조사 생략 일반 조건을 발명하지 않음', None, graph.nodes['r.a.object']['properties']['content']['general_omission_condition'])
    check('조사 예문 두 표기 보존', ['밥을 묵어라.', '밥 무라.'], [x['text'] for x in graph.nodes['r.a.object']['properties']['content']['examples']])
    check('새 문헌의 근거 경로', [['R04', 'r.e.object', 'RYU2014']], graph.evidence_paths('R04'))

    mutations = [
        ('오타 최상위 필드 차단', lambda d: d.update(cliams=[])),
        ('오타 Claim 필드 차단', lambda d: d['claims'][0].update(regoin='안동')),
        ('잘못된 categories 자료형 차단', lambda d: d['claims'][0].update(categories='종결어미')),
        ('근거 필수 필드 누락 차단', lambda d: d['evidence'][0].pop('locator')),
        ('PDF 페이지의 bool 값 차단', lambda d: d['evidence'][0].update(pdf_pages=[True])),
        ('알 수 없는 세부 주장 유형 차단', lambda d: d['claims'][0]['assertions'][0].update(kind='unknown')),
        ('근거 배열 자료형 오류 차단', lambda d: d['claims'][0].update(evidence_refs='e.contrast')),
        ('개별 예 검증 승인의 오기 차단', lambda d: d['claims'][0]['review'].update(linguistic_truth='approved')),
    ]
    for name, mutate in mutations:
        changed = copy.deepcopy(data)
        mutate(changed)
        try:
            validate(changed, registry)
        except (ValueError, TypeError, KeyError):
            rejected = True
        else:
            rejected = False
        check(name, True, rejected)
    changed_registry = copy.deepcopy(registry)
    for source in changed_registry['sources']:
        if source['source_id'] == 'RYU2014':
            source['eligible_for_claims'] = False
    try:
        validate(data, changed_registry)
    except ValueError:
        rejected = True
    else:
        rejected = False
    check('자료 통제표에서 비활성화된 근거 차단', True, rejected)
    try:
        validate_schema('abc', {'type': 'string', 'pattern': '^a'})
    except ValueError:
        rejected = True
    else:
        rejected = False
    check('미지원 스키마 키워드를 조용히 무시하지 않음', True, rejected)
    return {'status': 'passed', 'fixture_claims': len(data['claims']),
            'new_claims': ['R01', 'R02', 'R03', 'R04'],
            'baseline_checks': len(baseline['checks']), 'additional_checks': checks,
            'total_checks': len(baseline['checks']) + len(checks),
            'nodes': len(graph.nodes), 'edges': len(graph.edges),
            'limits': ['문헌 정답 검증·자연어 자동 분석·생성 실험 아님',
                       'content와 주석 value 내부 구조는 의미별 확장 영역으로 남음']}


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False, indent=2))

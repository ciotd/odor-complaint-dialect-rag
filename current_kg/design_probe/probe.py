"""Local, dependency-free claim/graph design probe; not a generator.

Run: python3 current_kg/design_probe/probe.py
The JSON contract is checked here, not advertised as a final universal schema.
No writes, network requests, model calls or imports of legacy claim data.
"""
import copy
import json
from pathlib import Path
from schema_check import validate_bundle, validate_schema

BASE = Path(__file__).resolve().parent


def require(ok, message):
    if not ok:
        raise ValueError(message)


def validate(data, registry, schema=None):
    if schema is None:
        validate_bundle(data)
    else:
        validate_schema(data, schema)
    groups = ['entities', 'evidence', 'claims', 'policies']
    objects = [obj for group in groups for obj in data[group]]
    objects += [x for c in data['claims'] for x in c['assertions'] + c['annotations']]
    ids = [obj['id'] for obj in objects]
    require(len(ids) == len(set(ids)), 'duplicate id')
    entities = {x['id'] for x in data['entities']}
    evidence = {x['id'] for x in data['evidence']}
    claims = {x['id'] for x in data['claims']}
    sources = {x['source_id']: x for x in registry['sources']}

    def refs(values, allowed, name, nonempty=True):
        require(isinstance(values, list), name + ' must be list')
        require(not nonempty or bool(values), name + ' cannot be empty')
        require(all(x in allowed for x in values), name + ' has unresolved ref')

    def condition(tree):
        require(isinstance(tree, dict), 'condition must be object')
        op = tree.get('op')
        require(op in {'eq', 'all', 'any'}, 'unknown condition operator')
        if op == 'eq':
            require(set(tree) == {'op', 'target', 'feature', 'value'}, 'invalid atom')
            require(tree['target'] in entities, 'condition target missing')
            require(isinstance(tree['feature'], str) and tree['feature'], 'feature missing')
            require(tree['value'] is not None, 'unknown is not a condition value')
        else:
            require(set(tree) == {'op', 'args'}, 'invalid logical condition')
            require(isinstance(tree['args'], list) and tree['args'], 'empty logical group')
            for child in tree['args']:
                condition(child)

    for item in data['evidence']:
        require(item['source_id'] in sources, 'source missing')
        src = sources[item['source_id']]
        require(src['eligible_for_claims'], 'source not eligible')
        require(item['pdf_pages'] and all(type(p) is int and 1 <= p <= src['file']['pages']
                                         for p in item['pdf_pages']), 'invalid PDF page')
        require(bool(item['locator']) and bool(item['excerpt']), 'evidence location/text missing')
        require(item['kind'] in {'source_statement', 'reported_attestation'}, 'evidence kind')
    for c in data['claims']:
        require(c['record_type'] in {'grammatical_assertion', 'attestation'}, 'claim kind')
        require(c['categories'] and c['assertions'], 'empty claim')
        require(c['review']['linguistic_truth'] == 'not_human_verified', 'truth not approved')
        refs(c['target_refs'], entities, 'claim targets')
        refs(c['evidence_refs'], evidence, 'claim evidence')
        for a in c['assertions']:
            refs(a['target_refs'], entities, 'assertion targets')
            require(isinstance(a['content'], dict) and a['content'], 'content missing')
            if a['condition'] is not None:
                condition(a['condition'])
        dimensions = {a['dimension'] for a in c['annotations']}
        require({'region', 'utterance_period', 'usage_context'} <= dimensions, 'annotations missing')
        for a in c['annotations']:
            refs(a['evidence_refs'], evidence, 'annotation evidence', nonempty=False)
            if a['value'] is None:
                require(a['missing_reason'] and a['basis'] == 'not_established', 'unexplained null')
            else:
                require(bool(a['evidence_refs']), 'annotation value without evidence')
        for r in c['relations']:
            require(r['target'] in claims, 'claim relation unresolved')
            require(r['type'] in {'exception_to', 'distribution_context', 'same_form_observed', 'usage_change_relative_to', 'qualifies'}, 'relation kind')
            refs(r['evidence_refs'], evidence, 'relation evidence')
    for p in data['policies']:
        refs(p['applies_to'], entities, 'policy targets')
        require(p['not_a_grammatical_claim'] is True, 'policy conflated with evidence')
        require(p['priority'] in {'primary', 'secondary', 'undetermined'}, 'priority')


class Graph:
    """Typed property graph with explicit claim, condition and provenance nodes."""

    def __init__(self, data, registry):
        self.nodes = {}
        self.edges = []
        sources = {x['source_id']: x for x in registry['sources']}

        def node(id_, type_, properties):
            require(id_ not in self.nodes, 'graph id collision: ' + id_)
            self.nodes[id_] = {'id': id_, 'type': type_, 'properties': copy.deepcopy(properties)}

        def edge(source, relation, target, **properties):
            self.edges.append({'source': source, 'relation': relation, 'target': target,
                               'properties': properties})

        def add_condition(tree, id_):
            node(id_, 'Condition', {k: v for k, v in tree.items() if k not in {'args', 'target'}})
            if tree['op'] == 'eq':
                edge(id_, 'evaluates', tree['target'])
            else:
                for i, child in enumerate(tree['args']):
                    child_id = id_ + '.' + str(i)
                    add_condition(child, child_id)
                    edge(id_, 'operand', child_id, index=i)

        for e in data['entities']:
            node(e['id'], e['type'], e['properties'])
        for e in data['evidence']:
            sid = e['source_id']
            if sid not in self.nodes:
                node(sid, 'Source', sources[sid])
            node(e['id'], 'Evidence', e)
            edge(e['id'], 'from_source', sid)
        for c in data['claims']:
            # Keep exact original fields for round-trip auditing; queries below
            # follow edges rather than retrieving an opaque claim string.
            node(c['id'], 'Claim', c)
            for target in c['target_refs']:
                edge(c['id'], 'about', target)
            for eid in c['evidence_refs']:
                edge(c['id'], 'supported_by', eid)
            for a in c['assertions']:
                node(a['id'], 'Assertion', a)
                edge(c['id'], 'asserts', a['id'])
                for target in a['target_refs']:
                    edge(a['id'], 'about', target)
                if a['condition'] is not None:
                    cid = a['id'] + '.condition'
                    add_condition(a['condition'], cid)
                    edge(a['id'], 'condition', cid)
            for a in c['annotations']:
                node(a['id'], 'Annotation', a)
                edge(c['id'], 'annotated_by', a['id'])
                for eid in a['evidence_refs']:
                    edge(a['id'], 'supported_by', eid)
            for r in c['relations']:
                edge(c['id'], r['type'], r['target'], basis=r['basis'], evidence_refs=r['evidence_refs'])
        for p in data['policies']:
            node(p['id'], 'Policy', p)
            for target in p['applies_to']:
                edge(p['id'], 'applies_to', target)
        require(all(e['source'] in self.nodes and e['target'] in self.nodes for e in self.edges),
                'dangling graph edge')

    def neighbors(self, id_, relation, reverse=False):
        a, b = ('target', 'source') if reverse else ('source', 'target')
        return [e[b] for e in self.edges if e[a] == id_ and e['relation'] == relation]

    def assertions(self, target, kind=None):
        return [i for i in self.neighbors(target, 'about', reverse=True)
                if self.nodes[i]['type'] == 'Assertion'
                and (kind is None or self.nodes[i]['properties']['kind'] == kind)]

    def evidence_paths(self, claim):
        return [[claim, e, s] for e in self.neighbors(claim, 'supported_by')
                for s in self.neighbors(e, 'from_source')]

    def evaluate(self, condition_id, facts):
        """Three-valued condition match, NOT a grammaticality/generation decision."""
        p = self.nodes[condition_id]['properties']
        if p['op'] == 'eq':
            target = self.neighbors(condition_id, 'evaluates')[0]
            value = facts.get(target, {}).get(p['feature'])
            return None if value is None else value == p['value']
        vals = [self.evaluate(i, facts) for i in self.neighbors(condition_id, 'operand')]
        if p['op'] == 'all':
            return False if False in vals else (None if None in vals else True)
        return True if True in vals else (None if None in vals else False)


def run_checks(data, registry):
    validate(data, registry)
    graph = Graph(data, registry)
    checks = []

    def check(name, expected, actual):
        require(actual == expected, f'{name}: expected {expected!r}, got {actual!r}')
        checks.append({'test': name, 'expected': expected, 'actual': actual})

    def texts(target):
        return sorted(graph.nodes[i]['properties']['content']['text']
                      for i in graph.assertions(target, 'accepted_example'))

    check('동사 부르다의 허용 예', ['친구가 부르니더'], texts('u.call'))
    check('형용사 부르다의 허용 예', ['배 부르이더'], texts('u.full'))
    check('형용사의 문헌 X 판정은 별도 보존', ['a.full.no'], graph.assertions('u.full', 'rejected_example'))
    check('일반 조건에서 예외 역방향 조회', ['T02'], graph.neighbors('T06', 'exception_to', True))
    check('좋다의 두 형태 보존', ['좋니더', '좋으이더'], graph.nodes['a.good']['properties']['content']['forms'])
    check('논문 관찰과 위키 예외 연결', ['T07'], graph.neighbors('T02', 'same_form_observed', True))
    check('논문 관찰의 출처 경로', [['T07', 'e.jo', 'JO2018']], graph.evidence_paths('T07'))
    check('논문 관찰을 문법 일반 주장으로 합치지 않음', 'attestation', graph.nodes['T07']['properties']['record_type'])
    aid = graph.assertions('f.구로', 'conditional_correspondence')[0]
    condition = graph.neighbors(aid, 'condition')[0]
    for meaning, expected in [('목적', True), ('강조', True), ('방식', False), (None, None)]:
        check('구로 의미 조건: ' + str(meaning), expected,
              graph.evaluate(condition, {'c.ge': {'meaning': meaning}}))
    check('고로에 조건을 자동 전파하지 않음', [], graph.assertions('f.고로', 'conditional_correspondence'))
    coda = graph.neighbors('a.coda', 'condition')[0]
    check('형용사와 자음 조건 모두 필요', True, graph.evaluate(coda, {'c.nikkyeo': {'predicate_pos': '형용사', 'realized_stem_final': '자음'}}))
    check('어간 말음 미확보는 허용 아님', None, graph.evaluate(coda, {'c.nikkyeo': {'predicate_pos': '형용사'}}))
    check('품사 조건 불일치', False, graph.evaluate(coda, {'c.nikkyeo': {'predicate_pos': '동사', 'realized_stem_final': '자음'}}))
    check('지역 정책은 구성에 별도 연결', ['P01'], graph.neighbors('c.nikkyeo', 'applies_to', True))
    check('세대 설명의 대상은 니이더', ['a.age'], graph.assertions('f.니이더', 'variant_usage_context'))
    check('세대 설명을 니더에 전파하지 않음', [], graph.assertions('f.니더', 'variant_usage_context'))
    check('발화 시기 미확보 유지', None, graph.nodes['T07.period']['properties']['value'])
    check('Claim 원본 필드 무손실 보존', data['claims'], [graph.nodes[c['id']]['properties'] for c in data['claims']])
    # Do not print the entire round-trip payload into the report.
    checks[-1]['expected'] = checks[-1]['actual'] = 'all claim fields identical'

    mutations = [
        ('누락 대상 참조 차단', lambda d: d['claims'][0]['target_refs'].append('missing')),
        ('잘못된 PDF 쪽 차단', lambda d: d['evidence'][0].update(pdf_pages=[999])),
        ('빈 논리 조건 차단', lambda d: d['claims'][2]['assertions'][0]['condition'].update(args=[])),
        ('근거 없는 지역 주석 차단', lambda d: d['claims'][0]['annotations'][0].update(evidence_refs=[])),
        ('미확보 값의 사유 누락 차단', lambda d: d['claims'][0]['annotations'][1].update(missing_reason=None)),
        ('중복 ID 차단', lambda d: d['claims'][0].update(id='T02')),
    ]
    for name, mutate in mutations:
        changed = copy.deepcopy(data)
        mutate(changed)
        try:
            validate(changed, registry)
        except (ValueError, KeyError, TypeError):
            rejected = True
        else:
            rejected = False
        check(name, True, rejected)
    return {'status': 'passed', 'claims': len(data['claims']), 'nodes': len(graph.nodes),
            'edges': len(graph.edges), 'checks': checks,
            'limitations': ['의미·품사는 시험 작성자가 지정한 입력이며 자동 분석 아님',
                            '전체 문법 스키마·생성 성능·문헌 진위 검증 아님']}


if __name__ == '__main__':
    data = json.loads((BASE / 'claims.json').read_text())
    registry = json.loads((BASE.parent / 'claims/source_registry.json').read_text())
    print(json.dumps(run_checks(data, registry), ensure_ascii=False, indent=2))

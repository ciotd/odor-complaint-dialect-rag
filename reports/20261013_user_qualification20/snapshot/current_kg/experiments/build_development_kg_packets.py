"""Materialize audited graph paths from explicit manual development annotations."""
import hashlib
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
GRAMMAR = BASE.parent / 'grammar'
sys.path.insert(0, str(GRAMMAR))
from query_review import assess_bound


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_packets(graph, plan):
    nodes = {n['id']: n for n in graph['nodes']}
    edges = graph['edges']
    assertions = {e['properties']['assertion_id']: e for e in edges if 'assertion_id' in e['properties']}
    outgoing = {}
    for e in edges:
        outgoing.setdefault(e['source'], []).append(e)
    items = []

    def evaluate(edge, known):
        props = edge['properties']
        aid = props['assertion_id']
        rid = props['record_id']
        record = nodes[rid]['properties']
        if record['review']['source_fidelity'] != 'author_checked':
            return {'status': 'held_record_review'}
        assertion = nodes[aid]['properties']
        if assertion['assertion_mode'] == 'example_only':
            return {'status': 'held_observation_only'}
        conditions = {}
        for mode in ('all', 'any'):
            conditions[mode] = [nodes[e['target']]['properties'] for e in outgoing.get(aid, [])
                                if e['type'] == 'requires_' + mode]
        def canonical(values):
            return sorted(json.dumps({k: c[k] for k in ('field','operator','values','evidence_keys')},
                                     sort_keys=True) for c in values)
        if any(canonical(conditions[m]) != canonical(assertion['conditions'][m]) for m in ('all','any')):
            raise ValueError('Missing or corrupt condition edges: ' + aid)
        return assess_bound(conditions, assertion["application"], known)

    def render(edge, assessment):
        props = edge['properties']
        aid, rid = props['assertion_id'], props['record_id']
        record = nodes[rid]['properties']
        def label(node_id):
            p = nodes[node_id]['properties']
            return p.get('text', p.get('label', p.get('value', node_id)))
        evidence = [nodes[x] for x in props['evidence_ids']]
        sources = [nodes[e['target']] for e in outgoing.get(rid, []) if e['type'] == 'from_source']
        return {'assertion_id': aid, 'record_id': rid, 'record_label': record['label'],
                'relation': {'subject': label(edge['source']), 'predicate': edge['type'], 'object': label(edge['target'])},
                'conditions': nodes[aid]['properties']['conditions'],
                'condition_assessment': assessment['status'],
                'application': nodes[aid]['properties']['application'],
                'scope': record['scope'], 'details': record['details'], 'gaps': record['gaps'],
                'evidence': evidence, 'source_ids': [x['id'] for x in sources],
                'assertion_mode': props['assertion_mode'], 'generation_approved': False}

    for item in plan['items']:
        selected, held, integrations, log = {}, [], [], []
        for seed in item['seeds']:
            aid = seed['assertion_id']
            if aid not in assertions:
                raise ValueError('Unknown manual assertion: ' + aid)
            edge = assertions[aid]
            known = seed['manual_known_features']
            assessment = evaluate(edge, known)
            log.append({'kind': 'manual_seed', 'assertion_id': aid, 'edge_id': edge['id'],
                        'known_features': known, 'assessment': assessment})
            if assessment['status'] != 'match':
                held.append({'assertion_id': aid, 'assessment': assessment})
                continue
            selected[aid] = render(edge, assessment)
            # One-hop variants are only admitted on their own matching conditions.
            for variant in assertions.values():
                if variant['type'] != 'variant_of' or variant['target'] != edge['source']:
                    continue
                va = evaluate(variant, known)
                vid = variant['properties']['assertion_id']
                log.append({'kind': 'variant', 'from': aid, 'assertion_id': vid,
                            'edge_id': variant['id'], 'assessment': va})
                if va['status'] == 'match':
                    selected[vid] = render(variant, va)
                else:
                    held.append({'assertion_id': vid, 'assessment': va})
            for link in edges:
                lp = link['properties']
                if 'integration_id' not in lp or edge['source'] not in (link['source'], link['target']):
                    continue
                if link['type'] == 'scope_tension_with' or lp.get('status') == 'held_scope_tension':
                    held.append({'integration_id': lp['integration_id'], 'status': 'held_scope_tension'})
                    continue
                if link['type'] not in {'shares_function_with', 'same_usage_candidate', 'has_inflection_description'}:
                    continue
                neighbor = link['target'] if link['source'] == edge['source'] else link['source']
                target_rid = neighbor.split(':')[0]
                if nodes[target_rid]['properties']['review']['source_fidelity'] != 'author_checked':
                    held.append({'integration_id': lp['integration_id'], 'status': 'held_record_review'})
                    continue
                accepted = []
                for target in assertions.values():
                    if target['source'] != neighbor:
                        continue
                    ta = evaluate(target, known)
                    tid = target['properties']['assertion_id']
                    log.append({'kind': 'integration', 'from': aid, 'integration_id': lp['integration_id'],
                                'edge_ids': [edge['id'], link['id'], target['id']], 'assessment': ta})
                    if ta['status'] == 'match':
                        selected[tid] = render(target, ta)
                        accepted.append(tid)
                    else:
                        held.append({'assertion_id': tid, 'integration_id': lp['integration_id'], 'assessment': ta})
                if accepted:
                    integrations.append({'id': lp['integration_id'], 'relation': link['type'],
                        'from': link['source'], 'to': link['target'], 'reason': lp['reason'],
                        'limits': lp['limits'], 'equivalence_asserted': False})
        packet = {'status': 'experimental_reference_not_validated_rules',
                  'assertions': list(selected.values()), 'integration_links': integrations}
        items.append({'id': item['id'], 'prompt_packet': packet, 'retrieval_log': log,
                      'held': held, 'manual_analysis': item['manual_analysis'],
                      'coverage_limit': item['coverage_limit']})
    return items


def main():
    plan_path = BASE / 'archive/legacy_development/development_30.kg_plan.json'
    graph_path = GRAMMAR / 'grammar.graph.json'
    items = build_packets(json.loads(graph_path.read_text()), json.loads(plan_path.read_text()))
    output = {'graph_sha256': digest(graph_path), 'plan_sha256': digest(plan_path),
              'builder_sha256': digest(Path(__file__)), 'items': items}
    (BASE / 'archive/legacy_development/development_30.kg_packets.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    for item in items:
        print(item['id'], 'assertions',len(item['prompt_packet']['assertions']),
              'integration_links',len(item['prompt_packet']['integration_links']), 'held',len(item['held']))


if __name__ == '__main__':
    main()

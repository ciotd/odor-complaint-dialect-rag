"""Function-driven ending diagnostics; no sentence parser or generation approval.

Input analyses are explicit annotations, replaceable by a model adapter later.
Candidates are discovered from graph functions, never from sentence IDs.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE.parent / 'grammar'))
from query_review import assess_bound

FUNCTIONS = {
    'declarative': 'DECLARATIVE', 'interrogative': 'INTERROGATIVE',
    'imperative': 'IMPERATIVE', 'hortative': 'HORTATIVE', 'exclamative': 'EXCLAMATIVE',
}


def validate_analysis(item):
    text = item['input']
    for clause in item['clauses']:
        start, end = clause['span']
        if not (0 <= start < end <= len(text)) or text[start:end] != clause['text']:
            raise ValueError('Invalid clause span')
        if not clause['clause_id'] or not clause['predicate_complex_id']:
            raise ValueError('Missing clause binding')
        if 'speech_level' in clause['features']:
            raise ValueError('Target speech level must be separate from observed input')
        if clause['features'].get('sentence_type') not in FUNCTIONS:
            raise ValueError('Unsupported or missing sentence type; review analysis first')


def review(graph, item):
    validate_analysis(item)
    nodes = {n['id']: n for n in graph['nodes']}
    outgoing = {}
    for edge in graph['edges']:
        outgoing.setdefault(edge['source'], []).append(edge)

    def at(nid, relation):
        return [e for e in outgoing.get(nid, []) if e['type'] == relation]

    def conditions(aid):
        expected = nodes[aid]['properties']['conditions']
        actual = {m: [nodes[e['target']]['properties'] for e in at(aid, 'requires_' + m)]
                  for m in ('all', 'any')}
        def canonical(rows):
            return sorted(json.dumps({k: c[k] for k in ('field', 'operator', 'values', 'evidence_keys')},
                                     sort_keys=True) for c in rows)
        valid = all(canonical(actual[m]) == canonical(expected[m]) for m in actual)
        return actual, valid

    clauses = []
    for clause in item['clauses']:
        known = clause['features']
        funcs = {'concept:' + FUNCTIONS[known['sentence_type']]}
        if known.get('question_type') in ('polar', 'content'):
            funcs.add('concept:' + ('POLAR_QUESTION' if known['question_type'] == 'polar' else 'CONTENT_QUESTION'))
        candidates = []
        for edge in graph['edges']:
            if edge['type'] != 'realizes' or edge['target'] not in funcs:
                continue
            props = edge['properties']
            aid = props.get('assertion_id')
            if not aid:
                continue
            assertion = nodes[aid]['properties']
            rid = props['record_id']
            record = nodes[rid]['properties']
            cons, intact = conditions(aid)
            evaluation = assess_bound(cons, assertion["application"], known) if intact else {'status': 'invalid_graph', 'conditions': cons}
            missing = sorted({c['field'] for m in ('all','any') for c in evaluation['conditions'][m]
                              if c.get('result') == 'unknown'})
            reasons = []
            if not intact:
                reasons.append('graph_condition_edges_missing_or_corrupt')
            if record['review']['source_fidelity'] != 'author_checked':
                reasons.append('source_review_unresolved')
            if assertion['assertion_mode'] == 'example_only':
                reasons.append('example_observation_not_general_rule')
            target = assertion['application']['target']
            if target != 'clause.final_ending':
                reasons.append('application_target_requires_review')
            for field in missing:
                reasons.append(('target_style_unresolved:' if field == 'speech_level'
                                else 'unstructured_semantics:' if field == 'meaning'
                                else 'input_or_context_unresolved:') + field)
            if evaluation['status'] == 'mismatch':
                reasons.append('known_condition_mismatch')
            # Condition match is deliberately separate from source/review/completeness.
            if record['gaps']:
                reasons.append('record_gaps_require_review')
            scenarios = []
            for scenario in clause.get('target_style_hypotheses', []):
                hypothetical = dict(known, speech_level=scenario['speech_level'])
                scenarios.append({**scenario, 'assessment': assess_bound(cons, assertion['application'], known, target_features={'speech_level':scenario['speech_level']}) if intact else evaluation,
                                  'target_style_confirmed': False})
            support = []
            for e in outgoing.get(edge['source'], []):
                other_aid = e['properties'].get('assertion_id')
                if other_aid and other_aid != aid:
                    other, ok = conditions(other_aid)
                    support.append({'edge_id': e['id'], 'assertion_id': other_aid,
                                    'relation': e['type'], 'target': e['target'],
                                    'assessment': assess_bound(other, nodes[other_aid]['properties']['application'], known) if ok else {'status':'invalid_graph'}})
            candidates.append({
                'record_id': rid, 'assertion_id': aid, 'form': nodes[edge['source']]['properties']['text'],
                'path': [edge['target'], edge['source'], aid], 'function_edge_id': edge['id'],
                'application': assertion['application'], 'assessment': evaluation,
                'unresolved_or_exclusion_reasons': reasons, 'style_scenarios': scenarios,
                'related_use_relations': support,
                'evidence': [nodes[eid] for eid in props['evidence_ids']],
                'scope': record['scope'], 'details': record['details'], 'gaps': record['gaps'],
                'source_review': record['review']['source_fidelity'],
                'generation_approved': False,
                'decision': ('invalid_graph' if not intact else 'exclude' if evaluation['status'] == 'mismatch' else 'review'),
            })
        # Reverse audit exposes records unreachable from realizes, without fabricating an edge.
        family = funcs | ({'concept:POLAR_QUESTION', 'concept:CONTENT_QUESTION'}
                          if known['sentence_type'] == 'interrogative' else set())
        records_with_functions = {e['source'] for e in graph['edges']
                                  if e['type'] == 'about' and e['target'] in funcs}
        reached = {e['properties']['record_id'] for e in graph['edges']
                   if e['type'] == 'realizes' and e['target'] in family
                   and 'record_id' in e['properties']}
        missing_paths = sorted(r for r in records_with_functions - reached
                               if nodes[r]['properties']['record_kind'] in ('ending','construction'))
        clauses.append({'clause_id': clause['clause_id'], 'text': clause['text'],
                        'analysis': clause, 'searched_functions': sorted(funcs),
                        'candidates': sorted(candidates,key=lambda c:c['assertion_id']),
                        'function_classified_records_without_realizes_path': missing_paths,
                        'status_counts': dict(Counter(c['assessment']['status'] for c in candidates))})
    return {'id': item['id'], 'input': item['input'], 'clauses': clauses}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--graph',type=Path,default=BASE.parent/'grammar/grammar.graph.json')
    parser.add_argument('--inputs',type=Path,default=BASE/'inputs/ending_review.inputs.json')
    parser.add_argument('--save',action='store_true')
    args=parser.parse_args()
    graph=json.loads(args.graph.read_text())
    inputs=json.loads(args.inputs.read_text())
    outputs=[review(graph,item) for item in inputs['items']]
    result={'status':'retrieval_diagnostic_not_generation', 'analysis_origin':inputs['analysis_origin'],
            'graph_sha256':hashlib.sha256(args.graph.read_bytes()).hexdigest(),
            'inputs_sha256':hashlib.sha256(args.inputs.read_bytes()).hexdigest(),
            'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'limitations':['Manual development annotations; no automatic input parser yet.',
                           'Function paths and one-hop same-use relations, not exhaustive graph traversal.',
                           'Listed-condition match does not validate unstructured restrictions or surface realization.',
                           'Style scenarios are hypotheses, not inferred speaker relationships.'], 'items':outputs}
    if args.save:
        (BASE/'archive/diagnostics/ending_review.results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    for item in outputs:
        for clause in item['clauses']:
            print(item['id'],clause['clause_id'],clause['status_counts'],
                  'missing_function_paths',clause['function_classified_records_without_realizes_path'])
            for c in clause['candidates']:
                print(' ',c['assertion_id'],c['form'],c['assessment']['status'],
                      ','.join(c['unresolved_or_exclusion_reasons']))


if __name__=='__main__':
    main()

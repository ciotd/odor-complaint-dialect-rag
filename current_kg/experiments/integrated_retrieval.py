"""Shared function/form/hybrid discovery with source-bound assertion selection.

Search relevance never supplies conditions. Graph expansion is bounded, preserves
edge IDs, rebinds each destination independently, and never copies source features.
"""
from collections import defaultdict
from copy import deepcopy
import json

from source_bindings import bind_item
from analysis_input import normalize_analysis
from run_manual_kg_development import GRAMMAR
from query_review import index_conditions, inspect_conditions

EXPAND = {'has_applicability_constraint', 'has_inflection_description',
          'has_construction_component', 'shares_quotative_construction',
          'same_usage_candidate', 'contrasts_in_function'}
MAX_HOPS = 2
MAX_PER_VIEW = 6
BUDGET = 24000


class IntegratedRetriever:
    def __init__(self, graph, search):
        self.graph, self.search = graph, search
        self.index = index_conditions(graph)
        self.nodes, self.outgoing, self.semantic, self.subjects = self.index
        self.records = defaultdict(list)
        self.forms = defaultdict(set)
        self.functions = defaultdict(set)
        self.suffixes = defaultdict(set)
        for edge in graph['edges']:
            if edge['type'] == 'has_surface_form':
                self.suffixes[edge['target']].update(
                    self.nodes[x['target']]['properties'].get('text')
                    for x in self.outgoing.get(edge['source'], []) if x['type'] == 'combines_with')
        for aid, e in self.semantic.items():
            if self.nodes[aid]['type'] != 'Assertion':
                continue
            self.records[e['properties']['record_id']].append(aid)
            a = self.nodes[aid]['properties']
            for group in a['conditions'].values():
                for c in group:
                    if c['field'] == 'source_form':
                        for value in c['values']:
                            self.forms[value].add(aid)
            if e['type'] == 'realizes':
                self.functions[e['target'].removeprefix('concept:')].add(aid)

    def assess(self, aid, v):
        e = self.semantic[aid]
        ap = self.nodes[aid]['properties']['application']
        candidate = deepcopy(v['candidate_features'])
        # Actual graph component evidence, not a candidate condition's demanded value.
        components = self.suffixes[e['source']]
        suffix = components & {'요', '예', '-요', '-예'}
        if len(suffix) == 1:
            candidate['following_form'] = next(iter(suffix)).lstrip('-')
        scenarios = []
        for target in v['targets'] or [{}]:
            start = e['source'] if self.nodes[e['source']]['type'] == 'ExpressionUse' else aid
            d = inspect_conditions(self.graph, start, v['features'], candidate, target, _index=self.index)
            a = next(x for x in d['base_assertions'] if x['assertion_id'] == aid)
            reasons = []
            if ap['target'] not in v['slots']:
                reasons.append('wrong_application_slot')
            if a['assessment']['status'] != 'match':
                reasons.append('condition_'+a['assessment']['status'])
            if a['source_review'] != 'author_checked':
                reasons.append('source_review_pending')
            if a['assertion_mode'] not in {'source_statement', 'extractor_interpretation'}:
                reasons.append('not_general_statement')
            if e['type'] in {'excludes_combination', 'excludes_function'}:
                reasons.append('constraint_not_positive_candidate')
            if d['matched_explicit_exclusions']:
                reasons.append('explicit_exclusion')
            exceptions = [x for ref in d['references']
                          if ref['relation'] == 'has_applicability_constraint' and ref['link_status'] != 'held_scope_tension'
                          for x in ref['assertions'] if x['predicate'] in {'excludes_combination', 'excludes_function'}
                          and x['source_review'] == 'author_checked']
            if any(x['assessment']['status'] == 'unknown' for x in exceptions):
                reasons.append('unresolved_exception')
            fields = {c['field'] for group in a['assessment']['conditions'].values() for c in group}
            if ap['target'] == 'clause.final_ending' and not fields & {'speech_level', 'addressee_treatment'}:
                reasons.append('target_politeness_not_structured')
            if v['features'].get('speech_act') == 'request' and v['features'].get('sentence_type') == 'interrogative' and e['target'] != 'concept:REQUEST':
                reasons.append('question_alone_not_request')
            if not fields and e['target'].removeprefix('concept:') not in v['functions']:
                reasons.append('no_bound_application_evidence')
            # Matched phonology etc. still needs a supported source-bound slot.
            scenarios.append({'target': target, 'candidate_features': candidate, 'reasons': reasons,
                              'assessment': a['assessment'], 'excluded_by': d['matched_explicit_exclusions'],
                              'exception_checks': [{'assertion_id': x['assertion_id'], 'predicate': x['predicate'],
                                                    'assessment': x['assessment']} for x in exceptions]})
        return scenarios

    def card(self, aid, view, scenario):
        e = self.semantic[aid]
        a = self.nodes[aid]['properties']
        rid = e['properties']['record_id']
        record = self.nodes[rid]['properties']
        return {'id': aid, 'record_id': rid, 'binding_id': view['id'],
                'source_span': view['span'], 'source_text': view['text'],
                'input_features': view['features'], 'application': a['application'],
                'relation': {'predicate': e['type'], 'subject_id': e['source'], 'object_id': e['target'],
                             'subject': self.nodes[e['source']]['properties'],
                             'object': self.nodes[e['target']]['properties']},
                'conditions': scenario['assessment'], 'target_hypothesis': scenario['target'],
                'exception_checks': scenario['exception_checks'],
                'candidate_features': scenario['candidate_features'],
                'evidence': [self.nodes[x]['properties'] for x in a['evidence_ids']],
                'scope': record['scope'], 'gaps': record['gaps'],
                'status': 'condition_matched_development_reference_not_quality_approval',
                'preservation': 'Apply only at the bound morphological construction; preserve quotation content, following tense/honorifics and outer ending. A stem contraction is not a full inflection paradigm.'}

    def retrieve_item(self, item):
        views, binding_audit = bind_item(item)
        discoveries = defaultdict(list)
        search_audit = []
        for v in views:
            def discover(aid, route, **extra):
                discoveries[(aid, v['id'])].append({'route': route, **extra})
            for f in v['functions']:
                for aid in sorted(self.functions[f]):
                    discover(aid, 'function', function=f, edge_id=self.semantic[aid]['id'])
            for aid in sorted(self.forms[v['features'].get('source_form')]):
                discover(aid, 'source_form', query=v['features']['source_form'])
            # Free descriptions expand discovery only. They are not truth values.
            queries = list(dict.fromkeys(v.get('queries') or [v['text']+' '+v['features'].get('source_form', '')]))
            for query in queries:
                ranks = self.search.search_all(query, 'kg_record', limit=6)
                search_audit.append({'binding_id': v['id'], 'query': query, 'ranking': ranks})
                for h in ranks['hybrid']:
                    for aid in self.records[h['id']]:
                        discover(aid, 'hybrid', record_id=h['id'], score=h['score'])
                        # An open description may discover a rule for a bound child.
                        # Re-evaluate the child's OWN values; never copy parent prose.
                        for bound in views:
                            a,b=v['span'];c,d=bound['span']
                            if bound['id'] != v['id'] and bound['slots'] and (a <= c < d <= b or c <= a < b <= d):
                                discoveries[(aid,bound['id'])].append({
                                    'route':'hybrid','record_id':h['id'],'score':h['score'],
                                    'discovered_at':v['id'],'condition_inheritance':False})
        view_map = {v['id']: v for v in views}
        decisions = {}

        def evaluate(key):
            if key not in decisions:
                aid, vid = key
                scenarios = self.assess(aid, view_map[vid])
                decisions[key] = {'assertion_id': aid, 'binding_id': vid,
                                  'scenarios': scenarios, 'eligible': any(not s['reasons'] for s in scenarios)}
            return decisions[key]

        for key in list(discoveries):
            evaluate(key)
        direct = {key for key in discoveries if decisions[key]['eligible']}
        frontier = [(aid, []) for aid, _ in sorted(direct)]
        expanded = set()
        for hop in range(MAX_HOPS):
            following = []
            for start, prefix in frontier:
                if start in expanded:
                    continue
                expanded.add(start)
                origins = {start, self.semantic[start]['source']}
                for origin in sorted(origins):
                    for edge in self.outgoing.get(origin, []):
                        if edge['type'] not in EXPAND or edge['properties'].get('status') == 'held_scope_tension':
                            continue
                        end = edge['target']
                        aids = [end] if self.nodes[end]['type'] == 'Assertion' else self.subjects.get(end, [])
                        path = prefix+[edge]
                        for aid in aids:
                            any_match = False
                            for v in views:
                                key = aid, v['id']
                                discoveries[key].append({'route': 'graph', 'start_assertion': start,
                                                         'edges': path, 'condition_inheritance': False})
                                any_match |= evaluate(key)['eligible']
                            if any_match and edge['type'] != 'contrasts_in_function':
                                following.append((aid, path))
            frontier = following

        def pack(allow_graph):
            packet = {'references': [], 'graph_paths': []}
            omitted, counts, chosen = [], defaultdict(int), set()
            def priority(key):
                routes = {d['route'] for d in discoveries[key]}
                rank = 0 if 'source_form' in routes else 1 if 'function' in routes else 2 if 'hybrid' in routes else 3
                return rank, key[1], key[0]
            for key in sorted(decisions, key=priority):
                d = decisions[key]
                if not d['eligible'] or (not allow_graph and key not in direct):
                    continue
                aid, vid = key
                if counts[vid] >= MAX_PER_VIEW:
                    omitted.append({'assertion_id': aid, 'binding_id': vid, 'reason': 'per_binding_cap'})
                    continue
                v = view_map[vid]
                s = next(s for s in d['scenarios'] if not s['reasons'])
                card = self.card(aid, v, s)
                trial = deepcopy(packet)
                trial['references'].append(card)
                if len(json.dumps(trial, ensure_ascii=False, separators=(',', ':'))) > BUDGET:
                    omitted.append({'assertion_id': aid, 'binding_id': vid, 'reason': 'whole_card_budget'})
                    continue
                packet = trial
                chosen.add(key)
                counts[vid] += 1
            if allow_graph:
                for key in sorted(chosen):
                    path = next((p for p in discoveries[key] if p['route'] == 'graph'), None)
                    if path:
                        p = {'assertion_id': key[0], 'binding_id': key[1], **path}
                        if len(json.dumps({**packet, 'graph_paths': packet['graph_paths']+[p]}, ensure_ascii=False, separators=(',', ':'))) <= BUDGET:
                            packet['graph_paths'].append(p)
                        else:
                            omitted.append({'assertion_id': key[0], 'binding_id': key[1], 'reason': 'path_budget'})
            return packet, omitted, chosen

        flat, flat_omitted, flat_keys = pack(False)
        expanded_packet, graph_omitted, graph_keys = pack(True)
        audit = [{**d, 'discoveries': discoveries[key],
                  'sent_in_record': key in flat_keys, 'sent_in_graph': key in graph_keys}
                 for key, d in sorted(decisions.items())]
        return {'id': item['id'], 'input': item['input'], 'bindings': views, 'binding_audit': binding_audit,
                'search_audit': search_audit, 'decisions': audit,
                'packets': {'record_hybrid': flat, 'graph_hybrid': expanded_packet},
                'omitted': {'record_hybrid': flat_omitted, 'graph_hybrid': graph_omitted},
                'policy': {'graph_hops': MAX_HOPS, 'max_per_binding': MAX_PER_VIEW,
                           'budget': BUDGET, 'unmatched_search_results': 'audit_only',
                           'no_candidate_derived_features': True}}

    def retrieve(self, analysis):
        value = normalize_analysis(analysis)
        return [self.retrieve_item(i) for i in value['items']]

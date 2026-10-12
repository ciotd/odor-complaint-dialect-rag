"""Bind source morphology and cached/live clause analysis to KG v2 statements.

Retrieval proposes evidence, never approves generation or rewrites the sentence.
No dialect answer strings or sentence IDs are used as retrieval rules.
"""
import json
import re
import unicodedata
from copy import deepcopy
from functools import lru_cache
from pathlib import Path

from kiwipiepy import Kiwi
from query import KG, assess

BUDGET = 24000
PRED = {'VV': 'verb', 'VA': 'adjective', 'VX': 'auxiliary',
        'VCP': 'copula', 'VCN': 'negative_copula'}
LOW = {'해', '해라', '아주낮춤', '예사낮춤'}
HIGH = {'해요', '해예', '해여', '하이소', '하이소체', '아주높임', '두루높임',
        '하소', '하이소-하소', '하이소-하소체', '하소체 1형', '하소체 2형', '하소체 3형'}


def compact(x):
    return json.dumps(x, ensure_ascii=False, separators=(',', ':'))


def form(s):
    # Kiwi uses final-jamo codepoints; the documents also use compatibility jamo.
    return unicodedata.normalize('NFKD', s.lstrip('-').replace(' ', ''))


@lru_cache(maxsize=1)
def kiwi():
    return Kiwi(num_workers=1)


def morphology(text):
    tokens = [{'form': t.form, 'tag': t.tag.split('-')[0], 'span': [t.start, t.start+t.len],
               'surface': text[t.start:t.start+t.len]} for t in kiwi().tokenize(text)]
    words = []
    for i, t in enumerate(tokens):
        if t['tag'] not in PRED and t['tag'] not in {'NNG', 'NNP', 'NP', 'NR', 'MAG'}:
            continue
        pred = t['tag'] in PRED
        w = {**t, 'lemma': t['form']+'다' if pred else t['form'], 'pos': PRED.get(t['tag'], 'nominal'),
             'prefinals': [], 'ending': None, 'ending_tag': None, 'token_index': i}
        if pred:
            j = i+1
            while j < len(tokens) and tokens[j]['tag'] == 'EP':
                w['prefinals'].append(tokens[j]['form']); j += 1
            if j < len(tokens) and tokens[j]['tag'] in {'EC', 'EF', 'ETM', 'ETN'}:
                w.update(ending=tokens[j]['form'], ending_tag=tokens[j]['tag'],
                         predicate_span=[t['span'][0], tokens[j]['span'][1]])
        words.append(w)
    return {'tokens': tokens, 'words': words, 'status': 'Kiwi_hypotheses_not_gold'}


def inflection_ending(word):
    # A bare present form cannot replace a past/honorific/modal complex.
    if word['prefinals'] or word['ending'] is None:
        return None
    e = word['ending']
    return {'고': '-고', '어': '-아/어', '아': '-아/어', '어라': '-아/어라',
            '아라': '-아/어라', '라고': '-(으)라고', '으라고': '-(으)라고',
            '니': '-(으)니', '으니': '-(으)니'}.get(e)


def semantic_guard(item, morph):
    """Narrow source check; do not infer content questions from ambiguous 누구/뭐."""
    item = deepcopy(item); audit = []
    for c in item['clauses']:
        if c['features'].get('sentence_type') != 'interrogative':
            continue
        if '아니면' in c['text']:
            continue
        cues = [t for t in morph['tokens'] if c['span'][0] <= t['span'][0] < c['span'][1]
                and t['form'] in {'왜','어디','어떻게','언제','몇'} and t['tag'] in {'MAG','NP','MM'}]
        if cues and c['features'].get('question_type') != 'content':
            audit.append({'clause_id':c['clause_id'],'before':c['features'].get('question_type'),
                          'after':'content','source_cues':cues,
                          'basis':'explicit_wh_question_development_guard_not_gold'})
            c['features']['question_type'] = 'content'
    return item, audit


def source_forms(pattern):
    if not pattern.startswith('-'):
        return {form(pattern)}
    s = pattern[1:]
    variants = s.split('/')
    out = set()
    for v in variants:
        out.add(form(re.sub(r'\([^)]*\)', '', v)))
        out.add(form(v.replace('(', '').replace(')', '')))
    return out


class SentenceRetriever:
    def __init__(self, base=Path(__file__).resolve().parent):
        self.kg = KG(base)
        self.facts = list(self.kg.facts.values())

    def retrieve(self, item, morph=None):
        text = item['input']
        morph = morph or morphology(text)
        proposals, rejected = [], []

        def propose(f, binding, owners, route, priority, path=None):
            check = assess(f, owners)
            unknown = [c for c in check['conditions'] if c['status'] == 'unknown']
            if check['rejected'] or unknown:
                rejected.append({'id': f['id'], 'binding': binding, 'route': route,
                                 'reason': 'rejected_condition_or_usability' if check['rejected'] else 'unknown_structured_condition',
                                 'checks': check})
                return
            proposals.append({'fact': f, 'binding': binding, 'route': route, 'checks': check,
                              'priority': priority, 'path': path})

        for w in morph['words']:
            binding = {'text': w['surface'], 'span': w['span'], 'lemma': w['lemma'],
                       'prefinals': w['prefinals'], 'ending': w['ending'],
                       'predicate_span': w.get('predicate_span')}
            for f in self.facts:
                sp = f['source_pattern']
                if f['type'] not in {'lexical_mapping', 'phonology'} or sp['domain'] not in {'standard', 'shared'}:
                    continue
                if (sp['lemma'] or sp['text']) != w['lemma']:
                    continue
                owners = {'input': {'lemma': w['lemma']}, 'candidate': {}, 'target': {}, 'context': {}}
                propose(f, binding, owners, 'bound_lexical_mapping', 100)
            ending = inflection_ending(w)
            if ending:
                for path in self.kg.lexical_paths(w['lemma'], ending)['paths']:
                    if any(c['status'] == 'unknown' for a in path['checks'].values() for c in a['conditions']):
                        continue
                    for f in path['statements']:
                        owners = {'input': {'lemma': w['lemma']}, 'candidate': path['selected_candidate']}
                        propose(f, binding, owners, 'lexical_to_inflection', 110, path['edge'])

        for clause in item['clauses']:
            start, end = clause['span']
            if text[start:end] != clause['text']:
                raise ValueError('Clause is not bound to input')
            words = [w for w in morph['words'] if w['tag'] in PRED and start <= w['span'][0] < end]
            if not words:
                continue
            host = words[-1]
            features = {k: v for k, v in clause['features'].items() if v is not None}
            function = features.get('sentence_type') if clause['role'] == 'main' else features.get('clause_relation')
            qtype = features.get('question_type')
            functions = {function}
            if function == 'interrogative' and qtype in {'polar', 'content'}:
                functions.add(qtype+'_question')
            features.update(function=function, sentence_function=function)
            features['host_pos'] = host['pos']
            cand = {'lemma': host['lemma'], 'pos': host['pos'],
                    'predicate_class': 'nominal_or_copula' if host['tag'] == 'VCP' else
                        ('negative_copula' if host['tag'] == 'VCN' else 'predicate_except_negative_copula'),
                    'tense_or_retrospective_suffix': any(x in {'었','았','였','겠','더'} for x in host['prefinals'])}
            owners = {'input': features, 'candidate': cand, 'target': {}, 'context': {}}
            binding = {'text': clause['text'], 'span': clause['span'], 'clause_id': clause['clause_id'],
                       'host_lemma': host['lemma'], 'ending': host['ending']}
            forms = {form(host['ending'])} if host['ending'] else set()
            for f in self.facts:
                if f['type'] not in {'ending', 'construction'}:
                    continue
                sp = f['source_pattern']
                literal = sp['domain'] in {'standard', 'shared'} and sp['text'].startswith('-') and bool(source_forms(sp['text']) & forms)
                # Function-only routing is limited to the actual terminal clause.
                routed = (f['type'] == 'ending' and sp['domain'] == 'metalinguistic'
                          and bool(set(f['functions']) & functions))
                if not (literal or routed):
                    continue
                if features.get('speech_act') == 'request' and function == 'interrogative' and not literal:
                    continue
                levels = set(f['scope']['speech_levels'])
                polite = clause['observed_politeness']
                if levels and ((polite == 'polite' and not levels & HIGH) or
                               (polite == 'non_polite' and not levels & LOW) or polite == 'unknown'):
                    continue
                if routed and not literal and qtype and f['functions'] and not (set(f['functions']) & {qtype+'_question', 'interrogative'}):
                    continue
                priority = (85 if literal else 60) + min(8, len(f['conditions']))
                propose(f, binding, owners, 'source_form' if literal else 'clause_function', priority)

        proposals.sort(key=lambda p: (-p['priority'], p['fact']['id']))
        packets = {}
        for mode in ['v2_direct', 'v2_graph']:
            packet = {'references': [], 'graph_paths': []}
            seen, per_binding, seen_forms = set(), {}, set()
            for p in proposals:
                f = p['fact']; key = tuple(p['binding']['span'])
                if mode == 'v2_direct' and f['type'] == 'inflection':
                    continue
                if f['id'] in seen or per_binding.get(key, 0) >= 6:
                    continue
                # Keep lexical senses apart; avoid flooding a binding with repeated sources.
                signature = (key, f['type'], f['target_pattern']['text'], f['target_pattern']['sense'])
                if signature in seen_forms:
                    continue
                card = {k: f[k] for k in ['id', 'source_id', 'type', 'source_pattern', 'target_pattern',
                                         'functions', 'conditions', 'constraints', 'scope', 'evidence', 'claim_status', 'usability']}
                card.update(input_binding=p['binding'], retrieval_route=p['route'], checks=p['checks'],
                            status='conditional_reference_not_approved_for_generation')
                trial = {**packet, 'references': packet['references']+[card]}
                # Reserve space for the actual edges, not just their endpoint cards.
                if len(compact(trial)) > BUDGET-2000:
                    continue
                packet = trial; seen.add(f['id']); seen_forms.add(signature)
                per_binding[key] = per_binding.get(key, 0)+1
            if mode == 'v2_graph':
                edges = {compact(p['path']): p['path'] for p in proposals if p['path'] and
                         p['path']['source'] in seen and p['path']['target'] in seen}
                for edge in edges.values():
                    trial = {**packet, 'graph_paths': packet['graph_paths']+[edge]}
                    if len(compact(trial)) <= BUDGET: packet = trial
            packets[mode] = packet
        return {'id': item['id'], 'input': text, 'morphology': morph, 'packets': packets,
                'rejected': rejected, 'proposal_count': len(proposals),
                'limitations': ['Morphology and cached semantic analysis are hypotheses.',
                               'Unknown structured conditions excluded; textual scope and sense remain explicit references.',
                               'No missing inflections synthesized; generator must preserve unprovided tense/honorific material.']}

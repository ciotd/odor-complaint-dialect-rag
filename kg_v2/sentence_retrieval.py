"""Bind source morphology and cached/live clause analysis to KG v2 statements.

Retrieval proposes evidence, never approves generation or rewrites the sentence.
No dialect answer strings or sentence IDs are used as retrieval rules.
"""
import json
import re
import unicodedata
from copy import deepcopy
from collections import defaultdict, deque
from functools import lru_cache
from pathlib import Path

from kiwipiepy import Kiwi
from query import KG, assess
from construction_retrieval import candidates as construction_candidates, QUOTE, INTENTION
from terminal_retrieval import select as select_terminal

BUDGET = 24000
PRED = {'VV': 'verb', 'VA': 'adjective', 'VX': 'auxiliary',
        'VCP': 'copula', 'VCN': 'negative_copula'}
LOW = {'해', '해라', '아주낮춤', '예사낮춤'}
HIGH = {'해요', '해예', '해여', '하이소', '하이소체', '아주높임', '두루높임',
        '하소', '하이소-하소', '하이소-하소체', '하소체 1형', '하소체 2형', '하소체 3형'}
INFORMAL_POLITE = {'해요', '해예', '해여'}
FORMAL_POLITE = {'하이소', '하이소체', '아주높임'}
HASSO = {'하소', '하소체 1형', '하소체 2형', '하소체 3형'}


def speech_style(clause, morph):
    """Source-terminal cues for ranking, not claims of dialect equivalence.

    Keep subject honorification separate. Never infer outer-clause register from
    an embedded/quoted EF, or satisfy a fact's target conditions by this heuristic.
    """
    result = {'politeness': clause['observed_politeness'], 'register': 'unknown',
              'source_ending': None, 'basis': 'cached_politeness_only'}
    if clause['role'] != 'main':
        return result
    start, end = clause['span']
    tokens = [t for t in morph['tokens'] if start <= t['span'][0] < end]
    ends = [i for i,t in enumerate(tokens) if t['tag'] == 'EF']
    if not ends:
        return result
    i = ends[-1]
    tail = tokens[i+1:]
    if any(t['tag'] not in {'SF','SP','SSO','SSC'} and
           not (t['tag'] == 'JX' and t['form'] == '요') for t in tail):
        return result
    ending = tokens[i]['form']
    result['source_ending'] = ending
    if ending.endswith(('니다','니까','십시오','ᆸ시오','ㅂ시오')):
        result.update(politeness='polite', register='formal_polite',
                      basis='source_terminal_form')
    elif ending.endswith(('요','죠')) or any(t['tag']=='JX' and t['form']=='요' for t in tail):
        result.update(politeness='polite', register='informal_polite',
                      basis='source_terminal_form')
    elif ending in {'소','오'} and result['politeness'] == 'polite':
        # Only rank already identified polite use; don't infer it from a syllable.
        result.update(register='hasso', basis='source_terminal_form_and_politeness')
    return result


def speech_style_rank(fact, style):
    """Prefer a compatible register without treating polite levels as identical."""
    levels = set(fact['scope']['speech_levels'])
    if style['register'] == 'informal_polite':
        # Explicit conversion policy: surface the attested 해예 alternatives
        # before shared 해요 forms. Otherwise ID order fills the six slots with
        # 해요 and still suppresses every -예 candidate. This is a preference,
        # not a claim that these regional forms are interchangeable everywhere.
        for rank, group in [(5, {'해예'}), (4, {'해여'}), (3, {'해요'}),
                            (2, FORMAL_POLITE), (1, HASSO)]:
            if levels & group:
                return rank
        return 0
    groups = {'formal_polite': (FORMAL_POLITE, INFORMAL_POLITE, HASSO),
              'hasso': (HASSO, FORMAL_POLITE, INFORMAL_POLITE)}
    for rank, group in zip((3,2,1), groups.get(style['register'], ())):
        if levels & group:
            return rank
    return 0


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
        derived = (t['tag'] in {'XSV','XSA'} and i > 0
                   and tokens[i-1]['tag'] in {'NNG','NNP','XR'}
                   and tokens[i-1]['span'][1] == t['span'][0])
        if t['tag'] not in PRED and not derived and t['tag'] not in {'NNG', 'NNP', 'NP', 'NR', 'MAG'}:
            continue
        original = t
        if derived:
            prev=tokens[i-1];span=[prev['span'][0],t['span'][1]]
            t={**t,'form':prev['form']+t['form'],'tag':'VV' if t['tag']=='XSV' else 'VA',
               'span':span,'surface':text[slice(*span)],'analysis_origin':'same_eojeol_derivation',
               'source_tags':[prev['tag'],original['tag']]}
            words=[w for w in words if w['token_index']!=i-1]
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
        # Kiwi sometimes reads 계세요 as 계/NNG+이/VCP+세요/EF.
        # Repair only that exact inflected eojeol, not 계 as an independent noun.
        if (t['tag']=='VCP' and i>0 and tokens[i-1]['form']=='계'
                and w['ending']=='세요'
                and text[tokens[i-1]['span'][0]:w['predicate_span'][1]]=='계세요'):
            start=tokens[i-1]['span'][0]
            w.update(form='계시',lemma='계시다',tag='VV',pos='verb',span=[start,t['span'][1]],
                     surface=text[start:t['span'][1]],ending='어요',predicate_span=[start,w['predicate_span'][1]],
                     lexical_honorific=True,analysis_origin='source_bound_gyeseyo_repair')
            words=[x for x in words if x['token_index']!=i-1]
        if w['ending'] in {'세요','으세요'}:
            w['fused_subject_honorific']=True
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


def ending_forms(host, function):
    """Align source morphemes with citation spelling; never replace dialect text.

    Kiwi separates 이/VCP from 에요/예요 or 야. Citation tables include
    the copula in 이에요/이야. Present declaratives alone license these aliases.
    Past/honorific complexes and questions must not inherit this present form.
    """
    forms = {form(host['ending'])} if host['ending'] else set()
    if host['tag']=='VCP' and not host['prefinals'] and function=='declarative':
        alias = {'에요':'이에요', '예요':'이에요', '야':'이야'}.get(host['ending'])
        if alias:
            forms.add(form(alias))
    return forms


def ending_conversion(fact, host):
    """An explicitly derived morpheme plan, not an attested full word/sentence."""
    operation = fact['target_pattern']['features'].get('realization')
    if operation != 'replace_ending_preserve_prefix':
        return None
    copula = fact['source_pattern']['text'] in {'-이에요', '-이야'}
    target = fact['target_pattern']['text'].lstrip('-')
    return {'status':'derived_composition_not_attested_surface',
            'operation':'replace_copula_and_ending' if copula else 'replace_terminal_ending',
            'source_morphemes':[host['form'], *host['prefinals'], host['ending']],
            'candidate_morphemes':[target] if copula else [host['form'], *host['prefinals'], target],
            'preserve_prefinals':host['prefinals'],
            'instruction':'선어말어미·부정·주체 높임을 보존한다. 어간의 방언 대응은 별도 근거로만 선택한다. 이 조합은 문헌의 완성형 인용이 아니다.'}


class SentenceRetriever:
    def __init__(self, base=Path(__file__).resolve().parent):
        self.kg = KG(base)
        self.facts = list(self.kg.facts.values())

    def retrieve(self, item, morph=None):
        text = item['input']
        morph = morph or morphology(text)
        proposals, rejected, style_profiles, terminal_decisions = [], [], [], []
        from transformation_plan import preservation_packet, advisory_candidates
        preservation=preservation_packet(item,morph,self.kg.facts)

        def propose(f, binding, owners, route, priority, path=None, style_rank=0, route_priority=None):
            check = assess(f, owners)
            unknown = [c for c in check['conditions'] if c['status'] == 'unknown']
            if check['rejected'] or unknown:
                rejected.append({'id': f['id'], 'binding': binding, 'route': route,
                                 'reason': 'rejected_condition_or_usability' if check['rejected'] else 'unknown_structured_condition',
                                 'checks': check})
                return
            proposals.append({'fact': f, 'binding': binding, 'route': route, 'checks': check,
                              'priority': priority, 'path': path, 'style_rank': style_rank,
                              'route_priority': priority if route_priority is None else route_priority})

        for w in morph['words']:
            next_index = w['token_index']+1
            following = morph['tokens'][next_index] if next_index < len(morph['tokens']) else None
            particle = following['form'] if following and following['tag'].startswith('J') else None
            binding = {'text': w['surface'], 'span': w['span'], 'lemma': w['lemma'],
                       'prefinals': w['prefinals'], 'ending': w['ending'],
                       'predicate_span': w.get('predicate_span'), 'following_particle':particle}
            for f in self.facts:
                sp = f['source_pattern']
                if f['type'] not in {'lexical_mapping', 'phonology'} or sp['domain'] not in {'standard', 'shared'}:
                    continue
                if (sp['lemma'] or sp['text']) != w['lemma']:
                    continue
                owners = {'input': {'lemma': w['lemma'], 'following_particle':particle},
                          'candidate': {}, 'target': {}, 'context': {}}
                propose(f, binding, owners, 'bound_lexical_mapping', 100)
            ending = inflection_ending(w)
            if ending:
                for path in self.kg.lexical_paths(w['lemma'], ending)['paths']:
                    if any(c['status'] == 'unknown' for a in path['checks'].values() for c in a['conditions']):
                        continue
                    for f in path['statements']:
                        owners = {'input': {'lemma': w['lemma']}, 'candidate': path['selected_candidate']}
                        propose(f, binding, owners, 'lexical_to_inflection', 110, path['edge'])

        # Search inner endings and multi-eojeol units independently of the last
        # predicate chosen for a cached clause. Conditions remain checked here.
        for fact, binding, owners in construction_candidates(item, morph, self.facts):
            propose(fact, binding, owners, 'source_bound_construction', 90,
                    route_priority=90)

        for clause in item['clauses']:
            start, end = clause['span']
            if text[start:end] != clause['text']:
                raise ValueError('Clause is not bound to input')
            style = speech_style(clause, morph)
            style_profiles.append({'clause_id': clause['clause_id'], 'span': clause['span'], **style})
            words = [w for w in morph['words'] if w['tag'] in PRED and start <= w['span'][0] < end]
            if not words:
                continue
            # An embedded ETM/ETN cannot serve as the terminal host.
            terminal=[w for w in words if w['ending_tag']==('EF' if clause['role']=='main' else 'EC')]
            if not terminal:
                continue
            host = terminal[-1]
            features = {k: v for k, v in clause['features'].items() if v is not None}
            function = features.get('sentence_type') if clause['role'] == 'main' else features.get('clause_relation')
            qtype = features.get('question_type')
            functions = {function}
            if function == 'interrogative' and qtype in {'polar', 'content'}:
                functions.add(qtype+'_question')
            features.update(function=function, sentence_function=function)
            features['host_pos'] = host['pos']
            features['has_prefinals'] = bool(host['prefinals'])
            cand = {'lemma': host['lemma'], 'pos': host['pos'],
                    'predicate_class': 'nominal_or_copula' if host['tag'] == 'VCP' else
                        ('negative_copula' if host['tag'] == 'VCN' else 'predicate_except_negative_copula'),
                    'tense_or_retrospective_suffix': any(x in {'었','았','였','겠','더'} for x in host['prefinals'])}
            owners = {'input': features, 'candidate': cand, 'target': {}, 'context': {}}
            binding = {'text': clause['text'], 'span': clause['span'], 'clause_id': clause['clause_id'],
                       'host_lemma': host['lemma'], 'ending': host['ending'],
                       'predicate_span':host.get('predicate_span'),
                       'speech_style_preference': style}
            selected = select_terminal(host, clause, style, binding, self.kg.facts, text, kiwi().join)
            if selected is not None:
                terminal_decisions.append({k:v for k,v in selected.items() if k not in {'fact','owners'}})
                if selected['status']=='selected':
                    propose(selected['fact'],selected['binding'],selected['owners'],
                            'function_bound_terminal',150,style_rank=6,route_priority=150)
                else:
                    rejected.append({'route':'function_bound_terminal','binding':binding,'reason':selected['reason']})
                # A selected family or explicitly uncertain terminal must not
                # be overridden by a generic -요→-예 or unrelated function hit.
                continue
            # Advisory composition is separately attributed; it is not a KG fact.
            advised=advisory_candidates(host,clause,style,binding,self.kg.facts)
            for advice in advised:
                propose(advice,{**binding,'ending_conversion':ending_conversion(advice,host)},owners,'reviewed_model_composition',120,
                        style_rank=5,route_priority=120)
            forms = ending_forms(host, function)
            if host['ending_tag'] == 'EC' and host['ending'] in QUOTE.keys() | INTENTION:
                # The construction channel handles these. In particular a
                # quotation -다고 must not retrieve assertion -다카이 by spelling.
                continue
            for f in self.facts:
                if f['type'] not in {'ending', 'construction'}:
                    continue
                sp = f['source_pattern']
                literal = sp['domain'] in {'standard', 'shared'} and sp['text'].startswith('-') and bool(source_forms(sp['text']) & forms)
                precise = sp['features'].get('match_unit') == 'terminal_ending'
                if precise and (host['ending_tag'] != 'EF' or clause['role'] != 'main'
                                or function not in f['functions']):
                    continue
                # Function-only routing is limited to the actual terminal clause.
                routed = (f['type'] == 'ending' and sp['domain'] == 'metalinguistic'
                          and bool(set(f['functions']) & functions))
                if not (literal or routed):
                    continue
                # A listed form alone cannot license a construction. Keep the
                # fact in KG, but exclude function-only application without any
                # construction condition (notably nominal -래예 vs promises).
                if routed and not literal and not f['conditions']:
                    rejected.append({'id':f['id'],'binding':binding,'route':'clause_function',
                                     'reason':'function_only_without_application_conditions'})
                    continue
                levels = set(f['scope']['speech_levels'])
                polite = style['politeness']
                if levels and ((polite == 'polite' and not levels & HIGH) or
                               (polite == 'non_polite' and not levels & LOW) or polite == 'unknown'):
                    continue
                if routed and not literal and qtype and f['functions'] and not (set(f['functions']) & {qtype+'_question', 'interrogative'}):
                    continue
                base_priority = 95 if literal and precise else (85 if literal else 60)
                priority = base_priority + min(8, len(f['conditions']))
                bound = {**binding, 'ending_conversion':ending_conversion(f, host)} if precise else binding
                propose(f, bound, owners, 'source_form' if literal else 'clause_function', priority,
                        style_rank=speech_style_rank(f, style), route_priority=base_priority)

        # Preserve form-match vs function-route precedence. Within an ending
        # route, prefer observed register BEFORE specificity and the ID tie-break.
        proposals.sort(key=lambda p: (-p['route_priority'], -p['style_rank'],
                                      -p['priority'], p['fact']['id']))
        # A long utterance needs candidates for each clause before one clause's
        # many ending variants consume the shared budget. Keep lexical and
        # source-form/function route precedence; round-robin within each route.
        tiers = defaultdict(list)
        for proposal in proposals:
            tiers[proposal['route_priority']].append(proposal)
        balanced = []
        for priority, batch in tiers.items():
            if priority not in {150, 120, 95, 90, 85, 60}:
                balanced.extend(batch)
                continue
            queues = defaultdict(deque)
            for proposal in batch:
                queues[tuple(proposal['binding']['span'])].append(proposal)
            while any(queues.values()):
                for key in sorted(queues):
                    if queues[key]:
                        balanced.append(queues[key].popleft())
        proposals = balanced
        if any(p['route'] == 'source_bound_construction' for p in proposals):
            # New multi-eojeol evidence must not consume the budget before
            # other clauses receive even one grammatical candidate. Reserve
            # one candidate per grammatical binding, then use the usual order.
            grammar_routes = {'function_bound_terminal','source_bound_construction', 'source_form',
                              'clause_function', 'reviewed_model_composition'}
            first, rest, covered = [], [], set()
            for p in proposals:
                key = tuple(p['binding']['span'])
                if p['route'] in grammar_routes and key not in covered:
                    first.append(p)
                    covered.add(key)
                else:
                    rest.append(p)
            proposals = first + rest
        preservation['terminal_analysis_review']=[
            {'text':d['binding']['text'],'span':d['binding']['span'],'reason':d['reason'],
             'instruction':'분석이 확정되지 않은 종결이다. 원문의 문장부호·높임·문장 역할을 보존하고 질문·명령 어미를 임의로 강제하지 않는다.'}
            for d in terminal_decisions if d['status']=='blocked']
        packets, selection_audit = {}, {}
        for mode in ['v2_direct', 'v2_graph']:
            packet = {'references': [], 'graph_paths': [], 'preservation':preservation}
            omitted = []
            seen, seen_ids, per_binding, seen_forms = set(), set(), {}, set()
            specific_bindings = set()
            construction_bindings = set()
            for p in proposals:
                f = p['fact']; key = tuple(p['binding']['span'])
                if mode == 'v2_direct' and f['type'] == 'inflection':
                    continue
                if (f['id'], key) in seen:
                    continue
                # Keep one construction alternative per bound span so new
                # inner-ending variants do not displace whole other clauses.
                # The remaining pool is retained in the selection audit.
                if p['route'] == 'source_bound_construction' and key in construction_bindings:
                    omitted.append({'id': f['id'], 'span': list(key),
                                    'reason': 'construction_alternative_cap'})
                    continue
                if p['route']=='clause_function' and key in specific_bindings:
                    omitted.append({'id':f['id'], 'span':list(key),
                                    'reason':'specific_source_conversion_selected', 'style_rank':p['style_rank']})
                    continue
                if per_binding.get(key, 0) >= 6:
                    omitted.append({'id': f['id'], 'span': list(key), 'reason': 'per_binding_cap',
                                    'style_rank': p['style_rank']})
                    continue
                # Keep lexical senses apart; avoid flooding a binding with repeated sources.
                signature = (key, f['type'], f['target_pattern']['text'], f['target_pattern']['sense'])
                if signature in seen_forms:
                    continue
                card = {k: f[k] for k in ['id', 'source_id', 'type', 'source_pattern', 'target_pattern',
                                         'functions', 'conditions', 'constraints', 'scope', 'evidence', 'claim_status', 'usability', 'notes']}
                card.update(input_binding=p['binding'], retrieval_route=p['route'], checks=p['checks'],
                            status='conditional_reference_not_approved_for_generation')
                if f.get('origin'):
                    card.update(origin=f['origin'],advice_id=f['advice_id'],
                                supporting_fact_ids=f['supporting_fact_ids'])
                trial = {**packet, 'references': packet['references']+[card]}
                # Reserve space for the actual edges, not just their endpoint cards.
                if len(compact(trial)) > BUDGET-2000:
                    omitted.append({'id': f['id'], 'span': list(key), 'reason': 'packet_budget',
                                    'style_rank': p['style_rank']})
                    continue
                packet = trial; seen.add((f['id'], key)); seen_ids.add(f['id']); seen_forms.add(signature)
                if p['route'] == 'source_bound_construction':
                    construction_bindings.add(key)
                if p['binding'].get('ending_conversion') or p['route']=='reviewed_model_composition':
                    specific_bindings.add(key)
                per_binding[key] = per_binding.get(key, 0)+1
            if mode == 'v2_graph':
                edges = {compact(p['path']): p['path'] for p in proposals if p['path'] and
                         p['path']['source'] in seen_ids and p['path']['target'] in seen_ids}
                for edge in edges.values():
                    trial = {**packet, 'graph_paths': packet['graph_paths']+[edge]}
                    if len(compact(trial)) <= BUDGET: packet = trial
            packets[mode] = packet
            selection_audit[mode] = {'omitted': omitted}
        return {'id': item['id'], 'input': text, 'morphology': morph, 'packets': packets,
                'rejected': rejected, 'proposal_count': len(proposals),
                'speech_style_profiles': style_profiles, 'selection_audit': selection_audit,
                'terminal_decisions':terminal_decisions,
                'limitations': ['Morphology and cached semantic analysis are hypotheses.',
                               'Unknown structured conditions excluded; textual scope and sense remain explicit references.',
                               'Speech-style priority is a source-cued retrieval heuristic, not dialect equivalence or generation validation.',
                               'No missing inflections synthesized; generator must preserve unprovided tense/honorific material.']}

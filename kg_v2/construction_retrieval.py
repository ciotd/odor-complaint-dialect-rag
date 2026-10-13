"""Local morphology-bound construction retrieval, separate from terminal endings.

No full translation strings or development IDs are used as runtime rules.
"""
from copy import deepcopy

QUOTE = {'다고': 'statement', 'ᆫ다고': 'statement', '는다고': 'statement',
         '자고': 'proposal', '라고': 'rago', '으라고': 'command',
         '냐고': 'question', '느냐고': 'question', '으냐고': 'question'}
INTENTION = {'려고', '으려고'}


def units(text, morph):
    """Keep quoted and reporting morphology distinct; never span punctuation."""
    words = morph['words']
    for inner in words:
        ending = inner.get('ending')
        if inner.get('ending_tag') != 'EC' or ending not in QUOTE.keys() | INTENTION:
            continue
        if not inner.get('predicate_span'):
            continue
        end = inner['predicate_span'][1]
        following = next((w for w in words if w['span'][0] >= end), None)
        adjacent = (following and following.get('predicate_span')
                    and not text[end:following['span'][0]].strip())
        reporting = bool(adjacent and following['lemma'] in {'하다', '듣다', '말하다', '묻다'}
                         and following['tag'] in {'VV', 'VX'})
        outer = following
        if not (outer and outer['lemma'] == '하다' and outer['tag'] in {'VV', 'VX'}
                and outer.get('predicate_span') and outer.get('ending')
                and not text[end:outer['span'][0]].strip()
                and outer.get('analysis_origin') != 'same_eojeol_derivation'):
            outer = None
        # The inner suffix can be searched even without an adjacent reporting
        # verb; only a real 하다 permits the contraction construction.
        kind = 'quotation' if ending in QUOTE else 'intention_or_purpose'
        span = [inner['predicate_span'][0],
                outer['predicate_span'][1] if outer else end]
        quote_type = QUOTE.get(ending)
        if ending == '라고':
            quote_type = 'nominal_statement' if inner['tag'] == 'VCP' else 'command'
        yield {'text': text[slice(*span)], 'span': span, 'kind': kind,
               'quotation_type': quote_type, 'inner': deepcopy(inner),
               'outer': deepcopy(outer), 'adjacent_hada': outer is not None,
               'reporting_context_confirmed': reporting,
               'analysis_status': 'source_morphology_hypothesis_not_gold'}


def candidates(item, morph, facts):
    """Yield bound documentary candidates and a construction-aware operation."""
    text = item['input']
    has_general_quotation = any(f['source_pattern']['features'].get('match_unit') == 'quotative_go_hada'
                                and f['usability'] == 'candidate' for f in facts)
    for unit in units(text, morph):
        inner, outer = unit['inner'], unit['outer']
        ending = inner['ending']
        if unit['kind'] == 'quotation' and not unit['reporting_context_confirmed']:
            # -다고/-라고 also occur in causal/concessive clauses. An EC label
            # alone cannot establish quotation; do not satisfy quotation=True.
            continue
        inputs = {'quotation': unit['kind'] == 'quotation',
                  'adjacent_hada': unit['adjacent_hada'],
                  'quotation_type': unit['quotation_type'],
                  'inner_ending': ending, 'inner_pos': inner['pos']}
        owners = {'input': inputs, 'candidate': {'lemma': inner['lemma'], 'pos': inner['pos']},
                  'target': {}, 'context': {}}
        for f in facts:
            sp = f['source_pattern']
            if sp['domain'] not in {'standard', 'shared'} or f['type'] not in {'ending', 'construction'}:
                continue
            source = sp['text']
            operation = None
            binding_span = inner['predicate_span']
            if unit['kind'] == 'intention_or_purpose':
                if source in {'-(으)려고', '-려고'} and set(f['functions']) & {'intention', 'purpose'}:
                    operation = 'replace_inner_intention_ending'
            else:
                canonical = ('-다고' if unit['quotation_type'] == 'statement' else
                             '-라고' if ending == '으라고' else '-'+ending)
                if source == canonical and 'quotation' in f['functions']:
                    operation = 'replace_quotative_suffix_preserve_prefix'
                if (not has_general_quotation and outer and ending in {'라고', '으라고'}
                        and source == '-라고 하다'):
                    operation = 'compose_literal_rago_hada'
                    binding_span = unit['span']
                if outer and sp['features'].get('match_unit') == 'quotative_go_hada':
                    operation = 'contract_quotative_go_hada'
                    binding_span = unit['span']
            if not operation:
                continue
            composition = {
                'operation': operation,
                'status': 'derived_plan_not_attested_complete_surface',
                'inner_morphemes': [inner['form'], *inner['prefinals'], ending],
                'outer_morphemes': ([outer['form'], *outer['prefinals'], outer['ending']]
                                    if outer else None),
                'preserve_inner_prefinals': inner['prefinals'],
                'preserve_outer_prefinals': outer['prefinals'] if outer else [],
                'preserve_outer_ending': outer['ending'] if outer else None}
            composition['instruction'] = (
                '같은 구간 및 겹치는 구간의 후보는 대안이다. 같은 고를 두 번 바꾸지 않는다. '
                '인용 내용의 시제·주체 높임과 보고 동사의 시제·높임을 각각 유지한다. '
                '부정의 위치와 뒤따르는 보조용언을 유지한다. 완성형의 문헌 확인을 주장하지 않는다.')
            if operation == 'contract_quotative_go_hada':
                composition['candidate_morphemes'] = [inner['form'], *inner['prefinals'],
                    ending[:-1], '카', *outer['prefinals'], outer['ending']]
            if operation == 'replace_quotative_suffix_preserve_prefix':
                prefix = ending[:-2] if canonical == '-다고' else '으' if ending == '으라고' else ''
                composition['candidate_inner_morphemes'] = [inner['form'], *inner['prefinals'],
                    prefix + f['target_pattern']['text'].lstrip('-')]
            if operation == 'replace_inner_intention_ending':
                composition['instruction'] += (
                    ' 의도·목적 문맥에 맞는지 확인한 뒤 의도 어미만 대응한다. '
                    '임박한 사건 등 다른 용법의 적합성은 미확인이다. '
                    '뒤의 하다·부정·보조용언을 유지하며 이 근거로 하다를 카다로 합성하지 않는다.')
            compact_unit = {k: deepcopy(v) for k, v in unit.items() if k not in {'inner', 'outer'}}
            for role in ['inner', 'outer']:
                word = unit[role]
                compact_unit[role] = ({k: deepcopy(word[k]) for k in
                    ['lemma', 'form', 'prefinals', 'ending', 'ending_tag', 'predicate_span']}
                    if word else None)
            binding = {'text': text[slice(*binding_span)], 'span': list(binding_span),
                       'host_lemma': inner['lemma'], 'ending': ending,
                       'predicate_span': inner['predicate_span'],
                       'construction': compact_unit, 'construction_conversion': composition}
            yield f, binding, owners

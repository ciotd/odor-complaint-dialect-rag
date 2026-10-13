"""Source-bound retrieval views, independent of KG records and dialect answers.

Kiwi segmentation is a hypothesis, not a gold parse. Unrecognised constructions
remain search discoveries. No target features are inherited into embedded units.
"""
from copy import deepcopy

from source_analysis_guard import analyzer
from analysis_input import targets_for, route_functions

# Standard Korean morphological normalisation, not standard-to-dialect pairs.
CANONICAL = {
    '려고': '-(으)려고', '으려고': '-(으)려고', '려': '-(으)려', '으려': '-(으)려',
    '니까': '-(으)니까', '으니까': '-(으)니까',
    '지만': '-지만', '지마는': '-지마는', '더니': '-더니',
    '더니만': '-더니만', '더니마는': '-더니마는', '거니와': '-거니와',
    '느라고': '-느라고', '느라': '-느라', '다가': '-다가',
    '다느니': '-다느니', '다더니': '-다더니',
}
QUOTE_TYPES = {'다고': 'statement', 'ᆫ다고': 'statement', '는다고': 'statement',
               '냐고': 'question', '느냐고': 'question', '으냐고': 'question',
               '자고': 'suggestion', '라고': 'command', '으라고': 'command'}
BOUND_FIELDS = {'source_form', 'construction_kind', 'quotation_type'}


def bind_item(item):
    """Return typed views and token audit. Never consult candidate requirements."""
    text = item['input']
    ts = analyzer().tokenize(text)
    tokens = [{'form': t.form, 'tag': t.tag, 'span': [t.start, t.start+t.len],
               'text': text[t.start:t.start+t.len]} for t in ts]
    views = []

    def add(span, slots, known, *, origin, candidate=None, targets=None, functions=(), clause=None):
        v = {'id': item['id']+':b'+str(len(views)+1), 'span': span,
             'text': text[span[0]:span[1]], 'slots': slots, 'features': known,
             'candidate_features': candidate or {}, 'targets': targets if targets is not None else [{}],
             'functions': sorted(functions), 'origin': origin,
             'clause_id': clause['clause_id'] if clause else None,
             'observed_politeness': clause['observed_politeness'] if clause else 'unknown'}
        views.append(v)
        return v

    for c in item['clauses']:
        known = {k: v for k, v in c['features'].items() if v is not None and k not in BOUND_FIELDS}
        if c['role'] == 'connective':
            ends = [t for t in tokens if t['tag'] == 'EC' and c['span'][0] <= t['span'][0] < t['span'][1] <= c['span'][1]]
            if ends and ends[-1]['form'] in CANONICAL:
                known['source_form'] = CANONICAL[ends[-1]['form']]
        funcs, _ = route_functions(c)
        add(c['span'], ['clause.final_ending'] if c['role'] == 'main' else ['clause.connective'], known,
            origin='validated_clause_analysis', candidate=deepcopy(c['preserved_candidate_features']),
            targets=targets_for(c) if c['role'] == 'main' else [{}], functions=funcs, clause=c)

    for i, t in enumerate(tokens):
        if t['tag'] not in {'EC', 'ETM', 'JQ'}:
            continue
        span = t['span']
        known = {'source_form': CANONICAL.get(t['form'], '-'+t['form'])}
        owners = [c for c in item['clauses'] if c['role'] == 'connective'
                  and c['span'][0] <= span[0] < span[1] <= c['span'][1]
                  and not text[span[1]:c['span'][1]].strip(' ,')]
        if len(owners) == 1:
            # Semantic relation comes from the same connective, never the outer clause.
            relation = owners[0]['features'].get('clause_relation')
            if relation:
                known['clause_relation'] = relation
        if 'clause_relation' not in known and t['tag'] == 'EC':
            # Typed source-unit analysis is accepted only at its terminal EC.
            # Free meaning/query prose is never parsed into a condition value.
            relations = {u.get('features',{}).get('clause_relation')
                         for u in item.get('source_units',[])
                         if u['span'][0] <= span[0] < span[1] <= u['span'][1]
                         and not text[span[1]:u['span'][1]].strip(' ,')
                         and sum(x['tag']=='EC' and u['span'][0]<=x['span'][0]<x['span'][1]<=u['span'][1] for x in tokens)==1}
            relations.discard(None)
            if len(relations)==1:
                known['clause_relation']=next(iter(relations))
        quote_type = QUOTE_TYPES.get(t['form']) if t['tag'] == 'EC' else None
        if quote_type:
            # Nominal "학생이라고" is not an imperative quotation.
            previous = tokens[i-1] if i else {}
            if t['form'] == '라고' and previous.get('tag') == 'VCP':
                quote_type = 'statement'
            nxt = tokens[i+1] if i+1 < len(tokens) else {}
            if nxt.get('form') in {'하', '말하', '이야기하'} and nxt.get('tag', '').split('-')[0] == 'VV':
                kind = 'quotative_hada' if nxt['form'] == '하' else 'quotative_reporting'
                # -라고 하다 retains the source's more specific construction ID.
                if nxt['form'] == '하' and t['form'] in {'라고', '으라고'}:
                    kind = 'quotative_rago_hada'
                q = {'construction_kind': kind, 'quotation_type': quote_type}
                add(span, ['clause.connective'], {**q, 'source_form': '-고'},
                    origin='morphology_quotation_marker', functions=['QUOTATION'])
                if nxt['form'] == '하':
                    add([span[0], nxt['span'][1]], ['expression.orthography'],
                        {**q, 'source_form': '-고 하-'}, origin='morphology_quotation_hada', functions=['QUOTATION'])
                    end = i+2
                    while end < len(tokens) and tokens[end]['tag'] == 'EP':
                        end += 1
                    if end < len(tokens) and tokens[end]['tag'] in {'EF', 'EC'}:
                        exact = '-고 '+text[nxt['span'][0]:tokens[end]['span'][1]]
                        add([span[0], tokens[end]['span'][1]], ['expression.orthography'],
                            {**q, 'source_form': exact}, origin='morphology_quotation_surface', functions=['QUOTATION'])
                continue
            # A quote marker with unsupported reporting context stays unapproved.
            known['quotation_type'] = quote_type
        add(span, ['clause.connective'] if t['tag'] == 'EC' else [], known,
            origin='morphology_ending' if t['tag'] == 'EC' else 'morphology_non_connective')

    # Open units are semantic discovery queries only; their prose is never a condition.
    for u in item.get('source_units', []):
        add(u['span'], [], {}, origin='open_description_search_only')
        views[-1]['queries'] = [u['text'], *u['form_queries'], *u['semantic_queries']]
    return views, {'tokens': tokens, 'limits': 'Kiwi and model analyses can be wrong; unsupported bindings stay unknown. No target or parent-feature inheritance.'}

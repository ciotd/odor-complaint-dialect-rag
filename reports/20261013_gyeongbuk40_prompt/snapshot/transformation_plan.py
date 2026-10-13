"""Source-bound preservation and explicitly attributed advisory composition.

No sentence IDs or reference translations determine runtime behavior.
"""
from copy import deepcopy
import json
from pathlib import Path

BASE=Path(__file__).resolve().parent

def rules():
    return json.loads((BASE/'advisory_rules.json').read_text())

def advisory_candidates(host,clause,style,binding,facts):
    rule=rules()['polite_terminal_particle']
    ending=host['ending']
    if (clause['role']!='main' or host['ending_tag']!='EF'
            or style['register']!='informal_polite' or ending not in rule['input_endings']):
        return []
    support_ids=list(rule['supporting_fact_ids'])
    example_number=(1 if ending in {'세요','으세요'} else 3 if ending in {'죠','지요'} else
                    2 if ending in {'ᆯ래요','을래요'} and clause['features'].get('sentence_type')=='interrogative' else None)
    if example_number:
        fid=f'NAMU_HONORIFICS_20260908:v2:advisory_examples:{example_number:04}'
        if fid in facts:support_ids.append(fid)
    supports=[facts[fid] for fid in support_ids]
    # Retain the link to each source independently; never relabel this derived
    # proposal as a documentary attested form.
    return [{'id':rule['id']+':'+ending,'advice_id':rule['id'],
        'origin':'model_advice_not_documentary_fact','source_id':'MODEL_ADVICE',
        'supporting_fact_ids':support_ids,
        'type':'ending',
        'source_pattern':{'text':'-'+ending,'domain':'standard','lemma':None,'sense':None,
                          'features':{'match_unit':'terminal_ending'}},
        'target_pattern':{'text':'-'+rule['input_endings'][ending],'domain':'dialect','lemma':None,'sense':None,
                          'features':{'realization':'replace_ending_preserve_prefix'}},
        'functions':[clause['features'].get('sentence_type')],
        'conditions':[{'owner':'input','field':'sentence_type','op':'in',
                       'value':['declarative','interrogative','imperative','propositive','hortative'],
                       'basis':'analyst_interpretation'}],
        'constraints':[{'kind':'require','description':rule['conditions']},
                       {'kind':'uncertainty','description':rule['uncertainty']}],
        'scope':{'regions':['동남 방언: 지역·화자 검토 필요'],'speech_levels':['해예'],
                 'registers':['informal_polite'],'period':[],'note':'검토 후 범위를 제한한 모델 조합 제안'},
        'evidence':[{'source_id':f['source_id'],**e} for f in supports for e in f['evidence']],
        'claim_status':'analyst_interpretation','usability':'candidate',
        'notes':'문헌의 요/예 설명은 구성요소 근거이며, 이 입력에 대한 완성형과 일반 적용 조건은 모델 제안이다.'}]

def preservation_packet(item,morph,facts):
    """Non-transformational support channel; never turn reference_only into rules."""
    relative=[]
    for w in morph['words']:
        if w['ending_tag']=='ETM':
            span=w['predicate_span']
            relative.append({'text':item['input'][slice(*span)],'span':span,'lemma':w['lemma'],
                             'ending':w['ending'],'prefinals':w['prefinals'],
                             'instruction':'관형절 역할과 이 구간 자체의 시제·상을 보존한다. 종결형으로 바꾸거나 주절 과거를 복사하지 않는다.'})
    support=[]
    if relative:
        f=facts.get('RYU2014:v2:full:0098')
        if f:
            support.append({'id':f['id'],'usability':f['usability'],'role':'preservation_support_not_transformation',
                            'description':f['target_pattern']['text'],'source_id':f['source_id'],
                            'evidence_pages':sorted({e['pdf_page'] for e in f['evidence']}),'scope':f['scope']})
    return {'origin':'reviewed_preservation_policy_not_dialect_rule',
        'relative_clauses':relative,'supporting_knowledge':support,
        'invariants':['원문의 명제·부정·시제·화행과 모든 절을 유지한다.',
                      '청자 높임, 주체 높임, 저/제의 겸양을 각각 보존한다. 주어를 호격으로 바꾸지 않는다.',
                      '가는/오는 이동 관점과 먼저의 시간 순서를 보존한다. 앞에의 시간 용법 자체는 금지하지 않는다.',
                      '인용 내용과 보고 서술부의 시제를 구분한다. 회상 -대를 표면형만 보고 전언으로 판단하지 않는다.'],
        'source_honorific_predicates':[{'lemma':w['lemma'],'text':item['input'][slice(*w['predicate_span'])]}
            for w in morph['words'] if w.get('predicate_span') and
            (w.get('lexical_honorific') or w.get('fused_subject_honorific') or '시' in w['prefinals']
             or w['lemma'] in {'계시다','드시다','드리다','주무시다','모시다'})]}

def package_plan(packet,item):
    groups={}
    for ref in packet['references']:
        b=ref['input_binding'];key=tuple(b['span'])
        if key not in groups:
            clauses=[c for c in item['clauses'] if c['span'][0]<=key[0] and key[1]<=c['span'][1]]
            groups[key]={'target_text':b['text'],'span':list(key),
                'preserve':[{'features':c['features'],'listener_politeness':c['observed_politeness'],
                             'subject_honorific':c.get('observed_subject_honorific','unknown'),
                             'tense_or_modality':c.get('tense_or_modality','unknown')} for c in clauses],
                'candidates':[]}
        candidate={k:deepcopy(ref[k]) for k in ['id','source_id','type','source_pattern','target_pattern',
            'functions','conditions','constraints','scope','claim_status','notes']}
        candidate.update(binding=deepcopy(b),origin=ref.get('origin','documentary_KG'),
            evidence_pages=[{'source_id':e.get('source_id',ref['source_id']),'pdf_page':e['pdf_page']} for e in ref['evidence']])
        if ref.get('supporting_fact_ids'):candidate['supporting_fact_ids']=ref['supporting_fact_ids']
        groups[key]['candidates'].append(candidate)
    return {'transformation_plan':list(groups.values()),'graph_paths':packet['graph_paths'],
            'preservation':packet.get('preservation',{}),
            'plan_policy':'후보는 모두 적용할 목록이 아니라 대안이다. 어휘보다 의미·높임·시제·문장 역할 보존을 우선한다. 원문에 맞는 후보만 사용한다. MODEL_ADVICE는 원문에서 직접 확인된 완성형이 아닌 모델 조합 제안이다. 보존용 지식은 치환 규칙이 아니다.'}

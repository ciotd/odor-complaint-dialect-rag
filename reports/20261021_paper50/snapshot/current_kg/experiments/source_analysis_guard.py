"""Conservative source-bound morphology guard; Kiwi hypotheses are not linguistic gold."""
from copy import deepcopy
from functools import lru_cache
import re
from kiwipiepy import Kiwi
from run_auto_analysis_development import candidate_assumptions

@lru_cache(maxsize=1)
def analyzer():
    return Kiwi(num_workers=1)

EP = {'었':'-었-', '았':'-었-', '였':'-었-', '시':'-시-', '겠':'-겠-', '더':'-더-'}
LOW = {'어','아','지','네','다','라','자','니','냐','나','야','더라','ᆯ래','을래','ᆯ게','을게','ᆯ까','을까'}

def inspect_source(text, role):
    tokens=analyzer().tokenize(text)
    trace=[{'form':t.form,'tag':t.tag,'start':t.start,'end':t.start+t.len,
            'surface':text[t.start:t.start+t.len]} for t in tokens]
    result={'tokens':trace,'politeness':'unknown','prefinals':None,'ending':None,'limits':[]}
    ending_tag='EF' if role=='main' else 'EC'
    indices=[i for i,t in enumerate(tokens) if t.tag==ending_tag]
    if not indices:
        result['limits'].append('no_bound_ending');return result
    i=indices[-1];ending=tokens[i]
    trailing=tokens[i+1:]
    # Never take quoted/embedded speech level when the outer clause has other content.
    if any(t.tag not in {'SF','SP','SSO','SSC'} and not (t.tag=='JX' and t.form=='요') for t in trailing):
        result['limits'].append('ending_is_not_clause_terminal');return result
    result['ending']=trace[i]
    if role=='main':
        if ending.form.endswith(('요','니다','니까','십시오')) or any(t.tag=='JX' and t.form=='요' for t in trailing):
            result['politeness']='polite'
        elif ending.form in LOW:
            result['politeness']='non_polite'
        else: result['limits'].append('speech_level_not_in_supported_inventory')
    j=i-1;prefinals=[]
    while j>=0 and tokens[j].tag=='EP':
        if tokens[j].form not in EP:
            result['limits'].append('unsupported_prefinal');return result
        prefinals.insert(0,EP[tokens[j].form]);j-=1
    if j<0 or tokens[j].tag.split('-')[0] not in {'VV','VA','VX','VCP','VCN','XSV','XSA'}:
        result['limits'].append('unresolved_predicate_attachment');return result
    # Fused EF and zero-width copula analyses cannot establish absence of -시-/-더-.
    if tokens[j].len==0 or (not prefinals and ending.form.startswith(('더','세요','셔'))):
        result['limits'].append('fused_or_ambiguous_morphology');return result
    result['prefinals']=prefinals
    return result


def guard_analysis(analysis):
    guarded=deepcopy(analysis);audit=[]
    guarded['origin']+='__source_morphology_guard_v1'
    for item in guarded['items']:
        # Generated preservation prose can itself assert a wrong speech level.
        # Keep it in the audit, not as an authoritative instruction to the translator.
        original_note=item['preservation_note']
        item['preservation_note']='원문의 의미·부정·발화 의도·청자 높임·주체 높임·시제를 보존하세요. 형태 분석 미확인은 허용 조건이 아닙니다.'
        for c in item['clauses']:
            evidence=inspect_source(c['text'],c['role'])
            old={'observed_politeness':c['observed_politeness'],
                 'preserved_candidate_features':deepcopy(c['preserved_candidate_features'])}
            c['observed_politeness']=evidence['politeness']
            # Do not copy Qwen's unverified prefinal/attachment guesses into candidate conditions.
            c['preserved_candidate_features']=candidate_assumptions(evidence['prefinals'],c['features'].get('host_pos'))
            c['candidate_analysis_limit']='Kiwi의 원문 결속 형태 분석으로 지원되는 선어말만 구성 가정에 사용. 형태 분석 자체의 오분석은 가능하며 미지원·융합형은 보류.'
            new={'observed_politeness':c['observed_politeness'],
                 'preserved_candidate_features':deepcopy(c['preserved_candidate_features'])}
            audit.append({'id':item['id'],'clause_id':c['clause_id'],'text':c['text'],
                          'before':old,'after':new,'changed':old!=new,'source_evidence':evidence,
                          'original_model_preservation_note':original_note})
    return guarded,audit

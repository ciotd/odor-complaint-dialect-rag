"""Function-bound terminal retrieval and explicit, attributed surface plans.

Family selection is a development policy, not a claim of universal dialect use.
No sentence IDs, reference translations, or automatic output rewriting are used.
"""
from copy import deepcopy
import re
from query import assess

G='NAMU_GRAMMAR_20260908:v2:'
H='NAMU_HONORIFICS_20260908:v2:'
J='JO2018:v2:'

def coda(s):
    return (ord(s[-1])-0xAC00)%28 if s and 0xAC00<=ord(s[-1])<=0xD7A3 else None

def without_l(s):
    return s[:-1]+chr(ord(s[-1])-8) if coda(s)==8 else s

def select(host,clause,style,binding,facts,text,join):
    """Return a reviewed family, blocked decision, or None for legacy coverage.

    Documentary conditions are evaluated on their own owners before composing.
    Surface proposals remain analyst-derived even when every component is cited.
    """
    if clause['role']!='main' or host['ending_tag']!='EF':return None
    e=host['ending'];fn=clause['features'].get('sentence_type')
    polite=style['register']=='informal_polite'
    low=style['politeness']=='non_polite' and style['register']=='unknown'
    if not (polite or low):return None
    a,b=host['predicate_span'];surface=text[a:b]
    pos='verb' if host['pos']=='auxiliary' else host['pos']
    pre=list(host['prefinals']);tag=host['tag']
    function=fn;question_type=clause['features'].get('question_type')
    inferred=[]
    def blocked(reason):
        return {'status':'blocked','reason':reason,'binding':binding,'source_ending':e}
    if fn=='declarative' and clause['text'].rstrip().endswith('?'):
        return blocked('declarative_analysis_conflicts_with_question_mark')
    # Do not trust a cached question label on ambiguous -세요 without a
    # question mark. Both a report and a request are possible; do not guess.
    if e in {'세요','으세요'} and fn=='interrogative' and '?' not in clause['text']:
        return blocked('ambiguous_seyo_conflicts_with_cached_question; requires_analysis_review')
    if fn not in {'declarative','interrogative','imperative'}:return None
    baseparts=[(host['form'],tag)]+[(p,'EP') for p in pre]
    def inflect(ending):return join(baseparts+[(ending,'EF')])
    family=None;ids=[];target=None;out=None;candidate_extra={}
    # A source-bound promise ending is stronger evidence than a noisy speech-act label.
    if e in {'ᆯ게요','을게요','ᆯ게','을게'} and fn=='declarative':
        if '?' in clause['text']:return blocked('promise_ending_in_question')
        family='polite_promise' if polite else 'casual_promise'
        ids=[G+'full:0711']
        if polite:ids += [G+'full:0702',G+'terminal_review:0001']
        suffix='게요' if polite else '게'
        if not surface.endswith(suffix):return blocked('promise_surface_not_aligned')
        base=surface[:-len(suffix)]
        # Preserve a lexical ㄹ; remove only a future ㄹ contributed by -ㄹ게.
        if coda(host['form'])!=8:base=without_l(base)
        out=base+('께예' if polite else '께');target='-(으)(ㄹ)께예' if polite else '-(으)(ㄹ)께'
    elif polite and fn=='imperative' and e in {'세요','으세요','어요','아요'}:
        if pre:return blocked('imperative_with_prefinals_requires_review')
        family='polite_request';ids=[H+'full:0006'];target='-(으)이소'
        imperative_surface=surface if e in {'세요','으세요'} else inflect('으세요')
        if not imperative_surface.endswith('세요'):return blocked('seyo_surface_not_aligned')
        # 걸으세요 -> 걸으이소 retains irregular stem; 주세요 -> 주이소.
        out=imperative_surface[:-2]+'이소'
    elif polite and e in {'ᆯ까요','을까요','ᆯ래요','을래요','죠','지요'}:
        # Preserve modality, proposal/choice and confirmation instead of
        # treating every question as a simple information question.
        family='polite_modal_or_confirmation';ids=[G+'full:0702',H+'full:0124']
        out=surface[:-1]+'예' if surface.endswith('요') else surface[:-1]+'지예'
        target='-'+('지예' if e in {'죠','지요'} else e[:-1]+'예')
    elif polite and fn=='interrogative' and e in {'나요','어요','아요','예요','에요','세요','으세요'}:
        family='polite_question'
        if tag=='VCP' and not pre:
            ids=[H+'full:0038'];target='-인교';out='인교'
        elif pos in {'verb','adjective'}:
            fid=H+('full:0034' if pos=='verb' else 'full:0033')
            ids=[fid]
            if e in {'세요','으세요'}:
                baseparts.append(('시','EP'));inferred.append('subject_honorific_in_fused_seyo')
            # 있는/없는 forms and tense suffixes select the 는교 branch.
            ending=('는교' if pos=='verb' or pre or host['form'].endswith(('있','없'))
                    else 'ᆫ교' if coda(host['form']) in {0,8} else '은교')
            target='-'+ending;out=inflect(ending)
        else:return blocked('unsupported_polite_question_host')
    elif polite and fn=='declarative' and e in {'어요','아요','에요','예요','네요','세요','으세요'}:
        family='polite_declarative';ids=[H+'full:0124']
        if tag=='VCP' and not pre:
            ids=[G+'ending_repair:0001']
            nominal=text[:a];out='이라예' if coda(nominal) not in {None,0} else '라예';target='-이라예'
        elif e in {'세요','으세요'}:
            ids += [H+'terminal_review:0001']
            out=surface[:-2]+'시예';target='-시예'
            inferred.append('subject_honorific_retained_in_si')
        elif host.get('analysis_origin')=='source_bound_gyeseyo_repair':
            out=inflect('어예');target='-어예'
        elif surface.endswith('요'):
            out=surface[:-1]+'예';target='-'+e[:-1]+'예'
            if e=='네요':ids += [G+'full:0702']
        else:return blocked('polite_declarative_surface_not_aligned')
    elif low and fn=='interrogative' and e in {'어','아','니','냐','나','노','었어','야'}:
        if '아니면' in clause['text'] and not re.search(r'왜|어디|언제|어떻게|몇',clause['text']):
            question_type='polar';inferred.append('alternative_question_without_wh')
        if question_type not in {'polar','content'}:return blocked('unknown_question_type')
        if pos not in {'verb','adjective'}:return None
        family='casual_question';ids=[J+('interrogative:0096' if question_type=='polar' else 'interrogative:0098')]
        target='-나' if question_type=='polar' else '-노';out=inflect(target[1:])
    elif low and fn=='imperative' and e in {'어','아','어라','아라','라','지','지마'}:
        if pre:return blocked('casual_imperative_with_prefinals')
        family='casual_request';ids=[J+'imperative:0053'];target='-아/어라'
        if host['lemma']=='오다':
            ids=[J+'imperative:0064'];target='-ㄴ나';out='온나';candidate_extra['ending']='-ㄴ나'
        elif pos=='verb':
            out=surface if surface.endswith('라') else surface+'라'
        else:return blocked('nonverbal_casual_request')
    elif low and fn=='declarative' and e in {'어','아'}:
        family='casual_declarative';ids=[J+'declarative:0105']
        ending='다'
        if pos=='verb' and not pre:
            ids.append(J+'declarative:0106');ending='는다' if coda(host['form']) not in {None,0,8} else 'ᆫ다'
        if tag in {'VCP','VCN'}:return None
        if host['lemma']=='되다' and re.search(r'(?:아|어|해|여)도\s*돼[.!?]?$',clause['text']):
            family='casual_permission';inferred.append('permission_construction_preserved_not_independent_dialect_fact')
        target='-'+ending;out=inflect(ending)
    if not family:return None
    if not out or '세예' in out:return blocked('invalid_or_deprecated_composition')
    owners={'input':{'function':function,'sentence_function':function,'sentence_type':function,
                     'question_type':question_type,'has_prefinals':bool(pre)},
            'candidate':{'lemma':host['lemma'],'pos':pos,**candidate_extra},'target':{},'context':{}}
    supports=[];checks=[]
    for fid in ids:
        if fid not in facts:return blocked('missing_support:'+fid)
        f=facts[fid];check=assess(f,owners)
        # Attested examples provide evidence only, never become replacement rules.
        if f['usability']=='candidate' and (check['rejected'] or any(x['status']!='satisfied' for x in check['conditions'])):
            return blocked('support_condition_not_satisfied:'+fid)
        supports.append(f);checks.append({'id':fid,'role':'rule' if f['usability']=='candidate' else 'example_only','conditions':check['conditions']})
    fid='PLAN:terminal:'+family+':'+e
    fact={'id':fid,'source_id':'COMPOSED_FROM_KG','origin':'documentary_components_with_analyst_composition',
          'advice_id':fid,'supporting_fact_ids':ids,'type':'ending',
          'source_pattern':{'text':'-'+e,'domain':'standard','lemma':None,'sense':None,'features':{'match_unit':'terminal_ending'}},
          'target_pattern':{'text':target,'domain':'dialect','lemma':None,'sense':None,'features':{'realization':'function_bound_terminal_plan'}},
          'functions':[fn],'conditions':[{'owner':'input','field':'sentence_type','op':'eq','value':fn,'basis':'analyst_interpretation'}],
          'constraints':[{'kind':'require','description':'원문의 시제·부정·높임·화행을 보존하고 명시된 종결 구간만 바꾼다.'},
                         {'kind':'scope','description':'사용자가 요청한 종결 계열 우선 정책. 문헌의 지역·시대 제한을 현대 경북40대 전체의 보편 규칙으로 확대하지 않는다.'}],
          'scope':{'regions':sorted({r for f in supports for r in f['scope']['regions']}),
                   'speech_levels':sorted({s for f in supports for s in f['scope']['speech_levels']}),
                   'registers':[],'period':[],
                   'note':'여러 종결 계열의 선택은 운영 정책이며 문헌의 동일 높임 등급 주장과 다르다.'},
          'evidence':[{'source_id':f['source_id'],**ev} for f in supports for ev in f['evidence']],
          'claim_status':'analyst_interpretation','usability':'candidate',
          'notes':'문헌의 구성요소를 원문 구간에 조합한 계획. 완성형 전체가 문헌 예문이라는 뜻이 아니다.'}
    plan={'family':family,'status':'derived_surface_not_attested_complete_utterance',
          'source_text':surface,'source_span':[a,b],'preferred_surface':out,
          'source_morphemes':[host['form'],*pre,e], 'preserve_prefinals':pre,
          'supporting_fact_ids':ids,'support_checks':checks,'analysis_notes':inferred,
          'instruction':'선택한 종결 계열과 원문 시제·주체 높임을 유지한다. preferred_surface는 표준어 어간을 보존한 조합안이며 방언 어휘를 선택하면 어간에 맞춰 활용한다. 겹친 종결 대안을 중복 적용하지 않는다. 명사 앞 구간에는 적용하지 않는다.'}
    bound={**binding,'ending_conversion':plan}
    return {'status':'selected','family':family,'fact':fact,'binding':bound,'owners':owners}

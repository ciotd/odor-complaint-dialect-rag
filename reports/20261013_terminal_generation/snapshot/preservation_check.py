"""Conservative source/output screening; flags are not dialect accuracy scores.

Only explicit high-confidence preservation failures trigger one repair. Unknown
parses and medium-confidence concerns remain review items, not rejection proof.
"""
from copy import deepcopy
import re
from sentence_retrieval import morphology

def sentences(text):
    return [m.group().strip() for m in re.finditer(r'[^.!?。！？]+[.!?。！？]*',text) if m.group().strip()]

def polite(text):
    terminal=re.sub(r'[\s.!?。！？"\'”’]+$','',text)
    return bool(re.search(r'(요|죠|니다|니까|십시오|예|예이|이소|마소|하소|니더|니꺼|심더|습니더|입니더|능교|는교|은교)$',terminal))

def negation(morph,text):
    return (any(t['form'] in {'안','못','아니','아니다'} and t['tag'] in {'MAG','VCN'} for t in morph['tokens'])
            or bool(re.search(r'몬\s|아이다|아입|아니|하지\s*마|지\s*마이소|지\s*마라',text)))

def check_preservation(source,output):
    src=sentences(source);out=sentences(output);flags=[]
    def flag(kind,index,before,after,confidence,instruction):
        flags.append({'kind':kind,'sentence_index':index,'source':before,'output':after,
                      'confidence':confidence,'instruction':instruction})
    if len(src)!=len(out):
        flag('sentence_alignment_uncertain',None,source,output,'review',
             '원문의 모든 절과 명제를 유지했는지 확인한다. 문장부호 차이만으로 누락을 확정하지 않는다.')
        return {'status':'needs_review','flags':flags,'repair_required':False,'not_accuracy':True}
    for i,(s,o) in enumerate(zip(src,out)):
        sm=morphology(s);om=morphology(o)
        sh=[w for w in sm['words'] if w['ending_tag']=='EF']
        oh=[w for w in om['words'] if w['ending_tag']=='EF']
        if polite(s) and not polite(o):
            # Only flag clearly non-polite, source-aligned terminal forms. A
            # dialect ending unknown to this recognizer is not automatically bad.
            tail=re.sub(r'[\s.!?。！？]+$','',o)
            if re.search(r'(다|나|노|제|까|어|아|게|래|셔|세)$',tail):
                flag('listener_politeness_lost',i,s,o,'high','원문의 청자 높임을 복원하되 질문·요청·약속 기능은 바꾸지 않는다.')
        if negation(sm,s) and not negation(om,o):
            flag('negation_unrecognized',i,s,o,'review','원문 부정의 범위가 유지됐는지 검토한다. 방언 부정형의 분석 실패일 수 있다.')
        if sh and oh and any(x in {'었','았','였'} for x in sh[-1]['prefinals']):
            if not any(x in {'었','았','였','더'} for x in oh[-1]['prefinals']):
                flag('past_unrecognized',i,s,o,'review','과거를 보존했는지 확인한다. 방언 활용의 형태 분석이 불완전할 수 있다.')
        humble=r'(?<![가-힣])(제가|저는|저를|저한테|제(?=\s))'
        nonhumble=r'(?<![가-힣])(내가|나는|내는|나를|나한테|내(?=\s))'
        if re.search(humble,s) and re.search(nonhumble,o):
            if not re.search(humble,o):
                flag('humility_replaced',i,s,o,'high','저/제의 겸양 지칭을 보존한다. 청자 높임과 별개로 검사한다.')
        for a,b in [('가는 길','오는 길'),('오는 길','가는 길')]:
            if a in s and b not in s and b in o and a not in o:
                flag('movement_perspective_changed',i,s,o,'high','원문 가다/오다의 이동 관점을 보존한다.')
        # Match the head noun and same predicate lemma before assigning a strong
        # ETM failure. Other dialect lexical forms are left for manual review.
        for w in sm['words']:
            if w['ending_tag']!='ETM':continue
            end=w['predicate_span'][1]
            nouns=[t for t in sm['tokens'] if t['span'][0]>=end and t['tag'] in {'NNG','NNP','NNB'}]
            if not nouns:continue
            noun=nouns[0]['form']
            positions=[t['span'][0] for t in om['tokens'] if t['form']==noun]
            for pos in positions:
                predecessors=[x for x in om['words'] if x.get('predicate_span') and x['predicate_span'][1]<=pos
                              and pos-x['predicate_span'][1]<=3 and x['lemma']==w['lemma']]
                if not predecessors:continue
                ow=predecessors[-1]
                # Standard-oriented Kiwi may tokenize 가노 as 가/VV+어/EC+
                # 노/NNG. Use source-bound same-lemma + head-noun context too.
                tail_before_head=re.sub(r'\s+','',o[ow['span'][1]:pos])
                if ow['ending_tag']=='EF' or tail_before_head in {'노','나','다'}:
                    flag('relative_clause_became_terminal',i,s,o,'high','명사 앞 관형절을 종결형으로 바꾸지 않는다.')
                elif ow['ending_tag']=='ETM' and w['ending']=='는' and ow['ending']=='던':
                    flag('relative_aspect_changed',i,s,o,'high','현재 관형형 -는을 회상 관형형 -던으로 바꾸지 않는다.')
        source_honorific=('께서' in s or bool(sh and ('시' in sh[-1]['prefinals'] or sh[-1].get('lexical_honorific'))))
        if source_honorific and not any(w.get('lexical_honorific') or w.get('fused_subject_honorific')
             or '시' in w['prefinals'] or w['lemma'] in {'계시다','드시다','주무시다'} for w in om['words']):
            flag('subject_honorific_unrecognized',i,s,o,'review','원문의 주체 높임을 확인한다. 방언 높임 활용의 분석 실패 가능성을 함께 남긴다.')
        if s.rstrip().endswith('?') != o.rstrip().endswith('?'):
            flag('question_punctuation_changed',i,s,o,'review','질문·평서 기능을 확인한다. 문장부호만으로 화행을 확정하지 않는다.')
    return {'status':'needs_review' if flags else 'no_screening_flags',
            'flags':flags,'repair_required':any(f['confidence']=='high' for f in flags),'not_accuracy':True}

def repair_request(request,source,output,check):
    req=deepcopy(request)
    req['messages'] += [{'role':'assistant','content':output},
        {'role':'user','content':'다음 보존 검사 지적을 확인해 번역을 한 번 수정하세요. 원문과 적용 가능한 근거가 우선입니다. '
         '문제가 없는 부분의 의미와 말투를 유지하고 수정한 전체 발화만 출력하세요.\n'+
         '\n'.join(f['instruction']+' 원문: '+f['source'] for f in check['flags'] if f['confidence']=='high')}]
    return req

def generate_checked(call,request,source,validate):
    response=call('/chat/completions',request);first=validate(response,request['model'])
    check=check_preservation(source,first)
    record={'request':request,'response':response,'first_output':first,'first_check':check,
            'output':first,'final_check':check,'repair_attempted':False,'selection':'first_pass'}
    if check['repair_required']:
        req=repair_request(request,source,first,check)
        record['repair_attempted']=True;record['repair_request']=req
        try:
            response=call('/chat/completions',req);candidate=validate(response,req['model'])
            after=check_preservation(source,candidate)
            record.update(repair_response=response,repair_output=candidate,repair_check=after)
            # No scalar error-count optimization: new kinds of preservation
            # failures must not silently replace a different original failure.
            old={(f['kind'],f['sentence_index']) for f in check['flags']}
            new={(f['kind'],f['sentence_index']) for f in after['flags']}
            if not after['repair_required'] and new <= old:
                record.update(output=candidate,final_check=after,selection='single_preservation_repair')
            else:record['selection']='first_pass_repair_not_accepted'
        except Exception as e:
            record['repair_error_type']=type(e).__name__
            record['selection']='first_pass_repair_failed'
    return record

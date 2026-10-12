"""Reproduce structure-repair retrieval comparisons; no network or generation calls.

Writes structure_repair.results.json; historical 30 requests/outputs remain untouched.
"""
import json,sys,hashlib,copy
from pathlib import Path
R=Path(__file__).resolve().parents[2];B=R/'current_kg/grammar';E=R/'current_kg/experiments'
sys.path[:0]=[str(B),str(E)]
from run_manual_kg_development import retrieve
from query_review import inspect_conditions
from source_structure_audit import audit
read=lambda p:json.loads(p.read_text())
graph=read(B/'grammar.graph.json');analysis=read(E/'inputs/development_30.manual_analysis.json');previous=read(E/'archive/legacy_development/development_30.manual_retrieval.json');current=retrieve(graph,analysis)
def view(x):
 return {'id':x['id'],'input':x['input'],'clauses':[{'clause_id':c['clause_id'],'selected':[{'id':v['assertion_id'],'form':v['form'],'path':v['function_path']} for v in c['candidates'] if v['disposition']=='sent_as_conditional_reference']} for c in x['clauses']]}
comparisons=[{'before':view(a),'after':view(b)} for a,b in zip(previous['items'],current)]
# Authored only after the KG edits; diagnostic inputs, no gold dialect outputs.
new=[('오늘 회의는 세 시에 끝났어요.','끝나다','declarative','polite','past'),('택배가 도착했어요?','도착하다','interrogative','polite','past'),('창문을 조금 열어 주세요.','열다','imperative','polite','present'),('오늘은 여기서 같이 쉬어요.','쉬다','hortative','polite','present'),('오늘 회의는 세 시에 끝났어.','끝나다','declarative','non_polite','past'),('택배가 도착했어?','도착하다','interrogative','non_polite','past'),('창문을 조금 열어.','열다','imperative','non_polite','present'),('오늘은 여기서 같이 쉬자.','쉬다','hortative','non_polite','present')]
fresh=copy.deepcopy(analysis);fresh['items']=[]
for n,(text,lemma,typ,height,tense) in enumerate(new,1):
 ident=f'NEW{n:03d}';features={'host_form':lemma,'host_pos':'verb','host_class':'predicate_other_than_anida','sentence_type':typ}
 if typ=='interrogative':features.update(question_type='polar',response_orientation='addressee')
 if typ in ['imperative','hortative']:features['action_participants']='speaker_and_addressee' if typ=='hortative' else 'addressee_only'
 if typ=='imperative':features['speech_act']='request'
 candidates={'prefinal_profile':'switching_prefinal_present','preceding_form':'-었-'} if tense=='past' else {'prefinal_profile':'none'}
 targets=[{'speech_level':'HAEYO_LEVEL'},{'speech_level':'HAISOCHE'},{'addressee_treatment':'informal_high'}] if height=='polite' else [{'speech_level':'HAECHE'},{'speech_level':'HAERACHE'},{'addressee_treatment':'informal_low'}]
 fresh['items'].append({'id':ident,'input':text,'preservation_note':'의미·시제·청자 높임 유지','unqueried_structure_note':'수동 분석 기반 조회 검증이며 자동 분석/번역 품질 평가가 아님.','clauses':[{'clause_id':ident+':c1','predicate_complex_id':ident+':p1','text':text,'span':[0,len(text)],'role':'main','features':features,'preserved_candidate_features':candidates,'observed_politeness':height,'target_scenarios':targets}]})
newout=retrieve(graph,fresh)
newrows=[]
for a,b in zip(fresh['items'],newout):
 c=b['clauses'][0]
 haeye=[{'id':v['assertion_id'],'disposition':v['disposition'],'scenarios':[{'target':s['target'],'eligible':s['eligible'],'reasons':s['reasons']} for s in v['scenarios']]} for v in c['candidates'] if v['record_id']=='GYS-H028' and v['form']=='-아/어예']
 newrows.append({'analysis':a,'retrieval':view(b),'haeye':haeye})
summary=audit()['summary']
out={'date':'2026-09-29','status':'structure_repair_and_manual_retrieval_check_not_generation_evaluation','graph_before_sha256':previous['graph_sha256'],'graph_after_sha256':hashlib.sha256((B/'grammar.graph.json').read_bytes()).hexdigest(),'historical_30_result_sha256':hashlib.sha256((E/'archive/legacy_development/development_30.manual_kg_results.json').read_bytes()).hexdigest(),'verifier_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'query_engine_sha256':hashlib.sha256((B/'query_review.py').read_bytes()).hexdigest(),'retriever_sha256':hashlib.sha256((E/'run_manual_kg_development.py').read_bytes()).hexdigest(),'summary_after':summary,'original_30_comparison':comparisons,'new_inputs_created_after_repairs':newrows,'limitations':['New inputs are author-constructed manual retrieval probes, not independent naturalness evaluation.','No Qwen call or translation rerun.','Before paths are the saved historical retrieval; after paths use the current graph and query code.','Top-6 candidate selection and automatic input analysis are not certified by this repair.']}
(B/'structure_repair.results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('Counts',summary)
for x in newrows:print(x['analysis']['id'],x['analysis']['input'],[(z['id'],z['disposition']) for z in x['haeye']])
print('Original 30 changed paths',sum(x['before']['clauses']!=x['after']['clauses'] for x in comparisons))

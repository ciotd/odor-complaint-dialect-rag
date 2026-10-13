"""Verify documentary coverage and actual generation requests; no model calls."""
import csv,hashlib,html,json,sys
from collections import Counter
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
sys.path[:0]=[str(ROOT/'kg_v2'),str(ROOT/'current_kg/experiments')]
from sentence_retrieval import SentenceRetriever,morphology,BUDGET,compact
from run_translation import make_request
def read(p):return json.loads(p.read_text())
def save(n,d):(P/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
facts={f['id']:f for f in map(json.loads,(ROOT/'kg_v2/facts.jsonl').read_text().splitlines())}
families={
 '해예 평서':['NAMU_HONORIFICS_20260908:v2:full:0124','NAMU_GRAMMAR_20260908:v2:full:0702','NAMU_GRAMMAR_20260908:v2:ending_repair:0001'],
 '높임 의문':['NAMU_HONORIFICS_20260908:v2:full:0033','NAMU_HONORIFICS_20260908:v2:full:0034','NAMU_HONORIFICS_20260908:v2:full:0038'],
 '높임 요청':['NAMU_HONORIFICS_20260908:v2:full:0006'],
 '약속':['NAMU_GRAMMAR_20260908:v2:full:0711','NAMU_GRAMMAR_20260908:v2:full:0702','NAMU_GRAMMAR_20260908:v2:terminal_review:0001'],
 '반말 평서·허용':['JO2018:v2:declarative:0105','JO2018:v2:declarative:0106'],
 '반말 의문':['JO2018:v2:interrogative:0096','JO2018:v2:interrogative:0098'],
 '반말 요청':['JO2018:v2:imperative:0053','JO2018:v2:imperative:0064']}
save('documentary_inventory.json',{name:[facts[fid] for fid in ids] for name,ids in families.items()})
items=read(P/'baseline_analysis.json')['items'];baseline={r['id']:r for r in read(P/'baseline_jobs.json')}
cfg=read(ROOT/'reports/20261012_construction_generation/protocol.json')['config']
engine=SentenceRetriever();retrieval=[];jobs=[];rows=[];counts=Counter();blocked=[]
for item in items:
 r=engine.retrieve(item);packet=r['packets']['v2_graph'];request=make_request(cfg,item,r['morphology'],packet)
 assert len(compact(packet))<=BUDGET
 before=baseline[item['id']]['request'];assert request['messages'][0]==before['messages'][0]
 assert {k:v for k,v in request.items() if k!='messages'}=={k:v for k,v in before.items() if k!='messages'}
 body=json.loads(request['messages'][1]['content'].split('\n',1)[1])
 old=json.loads(before['messages'][1]['content'].split('\n',1)[1])
 terminals=[]
 for group in body['transformation_plan']:
  for c in group['candidates']:
   if c['type']=='ending':assert '세예' not in c['target_pattern']['text'] and '게예' not in c['target_pattern']['text']
   plan=c['binding'].get('ending_conversion') or {}
   if plan.get('preferred_surface'):
    counts[plan['family']]+=1;terminals.append(plan)
    assert item['input'][slice(*plan['source_span'])]==plan['source_text']
    assert all(fid in facts for fid in plan['supporting_fact_ids'])
 for decision in r['terminal_decisions']:
  if decision['status']=='blocked':blocked.append({'id':item['id'],**decision})
 rows.append({'id':item['id'],'input':item['input'],
              'old_endings':[(g['target_text'],c['target_pattern']['text']) for g in old['transformation_plan'] for c in g['candidates'] if c['type']=='ending'],
              'selected_terminals':terminals,'request_changed':request!=before,
              'blocked':[d for d in r['terminal_decisions'] if d['status']=='blocked'],
              'reference_packet_chars':len(compact(packet))})
 retrieval.append(r);jobs.append({'id':item['id'],'input':item['input'],'condition':'terminal_function_retrieval','request':request})
save('retrieval.json',retrieval);save('jobs.json',jobs);save('lookup_comparison.json',rows)
save('summary.json',{'inputs':len(items),'model_calls':0,'request_changed_inputs':sum(r['request_changed'] for r in rows),
 'selected_terminal_spans':sum(counts.values()),'families':dict(counts),'blocked':blocked,
 'deprecated_ending_candidates':0,'same_system_and_sampling':True,
 'kg_facts':len(facts),'generation_status':'prepared_and_inspected_not_generated',
 'maximum_reference_packet_chars':max(r['reference_packet_chars'] for r in rows)})
with (P/'lookup_comparison.tsv').open('w',newline='') as f:
 w=csv.writer(f,delimiter='\t',lineterminator='\n');w.writerow(['id','input','previous_ending_candidates','new_terminal_plans','blocked'])
 for r in rows:w.writerow([r['id'],r['input'],json.dumps(r['old_endings'],ensure_ascii=False),
                           ' / '.join(p['source_text']+' → '+p['preferred_surface'] for p in r['selected_terminals']),
                           ' / '.join(d['reason'] for d in r['blocked'])])
e=html.escape
page='''<!doctype html><html lang="ko"><meta charset="utf-8"><title>종결 조회 수정 검증</title>
<style>body{font-family:sans-serif;line-height:1.7;margin:24px}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:10px;vertical-align:top}th{background:#eaf3fa}pre{white-space:pre-wrap}</style>
<h1>종결 조회 수정 —70개 실제 요청 검증</h1><p>아래는 Qwen 번역 결과가 아니라 생성기에 전달되는 종결 조합안입니다. 기존 분석·모델 설정을 유지했고 system에 경북40대 지시를 추가하지 않았습니다.</p>
<p><a href="coordinator_report.txt">수정 내용·원문 근거·한계</a> · <a href="lookup_comparison.tsv">전체 TSV</a> · <a href="../latest/index.html">최신 안내</a></p>
<table><tr><th>ID·원문</th><th>이전 종결 후보</th><th>새로 전달하는 구간별 조합안</th><th>보류</th></tr>'''
for r in rows:
 old='\n'.join(a+' → '+b for a,b in r['old_endings'])
 new='\n'.join(p['source_text']+' → '+p['preferred_surface']+' ['+p['family']+']' for p in r['selected_terminals'])
 page+='<tr>'+''.join('<td><pre>'+e(s)+'</pre></td>' for s in [r['id']+'\n'+r['input'],old,new,'\n'.join(d['reason'] for d in r['blocked'])])+'</tr>'
(P/'lookup_comparison.html').write_text(page+'</table></html>')
save('current_hashes.json',{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in [ROOT/'kg_v2'/n for n in ['facts.jsonl','graph.json','sentence_retrieval.py','terminal_retrieval.py','transformation_plan.py','advisory_rules.json']]})
print(json.dumps(read(P/'summary.json'),ensure_ascii=False,indent=2))

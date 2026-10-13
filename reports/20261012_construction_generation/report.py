"""Summarize fresh generation and derive presentation artifacts without editing outputs."""
import csv,html,json,statistics
from pathlib import Path
P=Path(__file__).resolve().parent
ROOT=P.parents[1]
def read(p):return json.loads(p.read_text())
def save(n,x):(P/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
new=read(P/'final_outputs.json');before={r['id']:r for r in read(P/'baseline_outputs.json')}
jobs={j['id']:j for j in read(P/'jobs.json')};ret={r['id']:r for r in read(P/'retrieval.json')}
protocol=read(P/'protocol.json')
rows=[{'id':r['id'],'input':r['input'],'before':before[r['id']]['output'],'after':r['output'],
       'changed':before[r['id']]['output']!=r['output'],'selection':r['selection'],
       'final_flags':[f['kind'] for f in r['final_check']['flags']]} for r in new]
save('comparison.json',rows)
def flags(rs,key):
 return {'any':sum(bool(r[key]['flags']) for r in rs),
         'high':sum(r[key]['repair_required'] for r in rs)}
lengths=[]
compact=lambda x:json.dumps(x,ensure_ascii=False,separators=(',',':'))
for r in new:
 j=jobs[r['id']]['request'];user=j['messages'][1]['content'];prefix,s=user.split('\n',1);d=json.loads(s)
 groups=d['transformation_plan'];arrays=[len(compact(g['candidates'])) for g in groups]
 lengths.append({'id':r['id'],'segments':len(groups),'candidates':sum(len(g['candidates']) for g in groups),
   'candidate_array_lengths':arrays,'segment_lengths':[len(compact(g)) for g in groups],
   'per_input_largest_candidate_array':max(arrays,default=0),
   'reference_packet_chars':len(compact(ret[r['id']]['packets']['v2_graph'])),
   'generation_packet_chars':len(compact({k:d[k] for k in ['transformation_plan','graph_paths','preservation','plan_policy']})),
   'user_chars':len(user),'system_chars':len(j['messages'][0]['content'])})
save('input_lengths.json',lengths)
stats={}
for name,group in [('all70',lengths),('previous38',[r for r in lengths if r['id'].startswith(('DEV','LONG'))])]:
 total=sum(r['segments'] for r in group)
 stats[name]={'inputs':len(group),'segments_total':total,'segments_per_input':total/len(group),
  'candidates_per_segment':sum(r['candidates'] for r in group)/total,
  'candidate_array_chars_mean':statistics.mean(n for r in group for n in r['candidate_array_lengths']),
  'segment_with_shared_fields_chars_mean':statistics.mean(n for r in group for n in r['segment_lengths']),
  'per_input_largest_candidate_array_mean':statistics.mean(r['per_input_largest_candidate_array'] for r in group),
  **{k+'_mean':statistics.mean(r[k] for r in group) for k in ['reference_packet_chars','generation_packet_chars','user_chars','system_chars']}}
save('input_statistics.json',stats)
summary={'inputs':len(new),'generation_calls':protocol['translation_calls'],'analysis_calls':0,
 'repairs_attempted':protocol['repair_attempted'],'repairs_accepted':protocol['repair_accepted'],
 'changed_requests':protocol['changed_requests'],'changed_final_outputs':[r['id'] for r in rows if r['changed']],
 'unchanged_request_but_output_changed':[r['id'] for r in rows if r['changed'] and r['id'] not in protocol['changed_requests']],
 'previous_final_screening':flags(list(before.values()),'final_check'),
 'new_first_screening':flags(new,'first_check'),'new_final_screening':flags(new,'final_check'),
 'not_accuracy':True,'observations':[
  'DEV027 received quotation candidates but retains 온다고 했어.',
  'LONG001 changed to 만나자꼬 카었는데: quotation alternatives/inflection are not stably realized.',
  'LONG005 changes 온다고 to 온다꼬 but retains 묵으려고 하는데.',
  'Retrieval arrival improved; overall translation improvement is not established.']}
save('summary.json',summary)
intro='최신 인용·의도 조회 구조로 70개 신규 번역 완료. 이전 70개 최종 출력과 비교.\n조회 후보가 도달해도 생성 적용은 안정되지 않았다. 자동 경고 수는 정확도가 아니다.\n'
text=intro+'\n'.join('\n'+r['id']+'\n원문: '+r['input']+'\n이전: '+r['before']+'\n최신: '+r['after'] for r in rows)
(P/'comparison.txt').write_text(text)
with (P/'comparison.tsv').open('w',newline='') as f:
 w=csv.writer(f,delimiter='\t',lineterminator='\n');w.writerow(['id','input','before','after','changed','flags'])
 for r in rows:w.writerow([r['id'],r['input'],r['before'],r['after'],r['changed'],','.join(r['final_flags'])])
e=html.escape
style='<style>body{font-family:sans-serif;margin:25px;line-height:1.6}table{border-collapse:collapse;width:100%}th,td{border:1px solid #cbd5e1;padding:12px;vertical-align:top}th{background:#eef3fa}tr.changed{background:#fff8df}pre{white-space:pre-wrap}</style>'
page='<!doctype html><html lang="ko"><meta charset="utf-8"><title>최신 조회 구조 번역 비교</title>'+style+'<h1>인용·의도 조회 수정 후 70개 번역</h1><pre>'+e(intro)+'</pre><table><tr><th>ID</th><th>원문</th><th>직전 최종</th><th>최신 최종</th></tr>'
for r in rows:page+='<tr'+(' class="changed"' if r['changed'] else '')+'>'+''.join('<td>'+e(r[k])+'</td>' for k in ['id','input','before','after'])+'</tr>'
(P/'comparison.html').write_text(page+'</table></html>')
peer=read(ROOT/'reports/model_comparison_20261012/comparison.json')
newby={r['id']:r for r in new}
aligned=[{'id':p['id'],'input':p['standard'],'astra':p['outputs']['astra_high_no_kg'],'sonnet':p['outputs']['sonnet_user_supplied'],'qwen_latest':newby[p['id']]['output']} for p in peer]
assert all(p['input']==newby[p['id']]['input'] for p in aligned)
save('peer_comparison.json',aligned)
page='<!doctype html><html lang="ko"><meta charset="utf-8"><title>최신 Qwen·Astra·Sonnet</title>'+style+'<h1>38개 공통 입력 비교</h1><p>모델·프롬프트·배치·재검토 조건이 다르며 두 비교 모델은 정답지가 아닙니다.</p><table><tr><th>ID</th><th>원문</th><th>Astra high</th><th>Sonnet</th><th>최신 Qwen</th></tr>'
for r in aligned:page+='<tr>'+''.join('<td>'+e(r[k])+'</td>' for k in ['id','input','astra','sonnet','qwen_latest'])+'</tr>'
(P/'peer_comparison.html').write_text(page+'</table></html>')
print(json.dumps(summary,ensure_ascii=False,indent=2))


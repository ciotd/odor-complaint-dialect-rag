"""Report a system-profile-only experiment without rewriting model outputs."""
import csv,hashlib,html,json,re
from collections import Counter
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
def read(p):return json.loads(p.read_text())
def save(name,data):(P/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
protocol=read(P/'protocol.json');assert protocol['status']=='completed'
new=read(P/'final_outputs.json');old={r['id']:r for r in read(P/'baseline_outputs.json')}
rank={'DEV':0,'LONG':1,'NEW':2,'ADVCE':3}
new.sort(key=lambda r:(next(v for k,v in rank.items() if r['id'].startswith(k)),r['id']))
assert len(new)==70 and len(old)==70
rows=[]
for after in new:
 before=old[after['id']];assert before['input']==after['input']
 rows.append({'id':after['id'],'input':after['input'],
   'before_first':before['first_output'],'after_first':after['first_output'],
   'before_final':before['output'],'after_final':after['output'],
   'first_changed':before['first_output']!=after['first_output'],
   'final_changed':before['output']!=after['output'],
   'before_selection':before['selection'],'after_selection':after['selection'],
   **{prefix+'_'+stage+'_flags':[f['kind'] for f in r[stage+'_check']['flags']]
      for prefix,r in [('before',before),('after',after)] for stage in ['first','final']}})
save('comparison.json',rows)
def screen(rs,key):
 return {'inputs_with_any_flags':sum(bool(r[key]['flags']) for r in rs),
   'inputs_with_high_flags':sum(r[key]['repair_required'] for r in rs),
   'flag_counts':dict(Counter(f['kind'] for r in rs for f in r[key]['flags']))}
summary={'inputs':70,'generation_calls':protocol['translation_calls'],
 'analysis_calls':0,'new_retrieval_calls':0,'only_system_suffix_changed':True,
 'first_outputs_changed':sum(r['first_changed'] for r in rows),
 'final_outputs_changed':sum(r['final_changed'] for r in rows),
 'changed_first_ids':[r['id'] for r in rows if r['first_changed']],
 'changed_final_ids':[r['id'] for r in rows if r['final_changed']],
 'before':{s:screen(list(old.values()),s+'_check') for s in ['first','final']},
 'after':{s:screen(new,s+'_check') for s in ['first','final']},
 'before_repairs':{'attempted':sum(r['repair_attempted'] for r in old.values()),
  'accepted':sum(r['selection']=='single_preservation_repair' for r in old.values())},
 'after_repairs':{'attempted':protocol['repair_attempted'],'accepted':protocol['repair_accepted']},
 'source_identical_before':[r['id'] for r in rows if r['input']==r['before_final']],
 'source_identical_after':[r['id'] for r in rows if r['input']==r['after_final']],
 'not_accuracy':True,'limitations':protocol['limitations']}
save('summary.json',summary)
intro=('경북40대 이상 말투 지시만 추가한70개 비교\n'
 'KG·조회·분석·user 메시지·Qwen 설정은 동일. system 끝에 한 문장만 추가.\n'
 '추가 지시: '+protocol['added_system_sentence']+'\n'
 '주 비교: 최초 출력끼리. 보조 비교: 같은 보존 검사·최대1회 수정 후 최종 출력끼리.\n'
 '변화량과 자동 경고 수는 방언 정확도나 자연스러움 점수가 아님.\n')
(P/'comparison.txt').write_text(intro+''.join('\n'+r['id']+'\n원문: '+r['input']+
 '\n이전 최초: '+r['before_first']+'\n추가 최초: '+r['after_first']+
 '\n이전 최종: '+r['before_final']+'\n추가 최종: '+r['after_final']+'\n' for r in rows))
(P/'translations.txt').write_text('경북40대 이상 지시 추가 —70개 최종 선택 출력\n'+''.join('\n'+r['id']+'\n원문: '+r['input']+'\n번역: '+r['after_final']+'\n' for r in rows))
with (P/'comparison.tsv').open('w',newline='') as f:
 w=csv.writer(f,delimiter='\t',lineterminator='\n')
 keys=['id','input','before_first','after_first','before_final','after_final','first_changed','final_changed','before_selection','after_selection']
 w.writerow(keys);w.writerows([r[k] for k in keys] for r in rows)
e=html.escape
style='''<style>body{font-family:sans-serif;line-height:1.65;margin:24px;color:#182b3b}table{border-collapse:collapse;width:100%}td,th{border:1px solid #c3ced8;padding:12px;vertical-align:top}th{background:#edf4fb}pre{white-space:pre-wrap}input{padding:10px;width:350px;max-width:90%}.changed{background:#fffbe9}small{color:#586473}summary{cursor:pointer}</style>'''
page='<!doctype html><html lang="ko"><meta charset="utf-8"><title>경북40대 이상 지시 비교</title>'+style
page+='<h1>경북40대 이상 지시만 추가한 결과</h1><pre>'+e(intro)+'</pre><p><a href="review.txt">검토 결론</a> · <a href="comparison.tsv">전체 TSV</a> · <a href="translations.txt">최종 번역 TXT</a> · <a href="../latest/index.html">최신 자료 안내</a></p>'
page+='<p>최초 출력 변경 '+str(summary['first_outputs_changed'])+'/70, 최종 출력 변경 '+str(summary['final_outputs_changed'])+'/70. 변경은 개선과 다릅니다.</p>'
page+='<label>문장 검색 <input id="search" placeholder="ID 또는 표현"></label><table><thead><tr><th>ID·원문</th><th>이전 최종</th><th>말투 추가 최종</th><th>최초 출력·검사</th></tr></thead><tbody>'
for r in rows:
 page+='<tr'+(' class="changed"' if r['final_changed'] else '')+'><td><b>'+e(r['id'])+'</b><br>'+e(r['input'])+'</td><td>'+e(r['before_final'])+'</td><td>'+e(r['after_final'])+'</td><td><details><summary>최초 출력 비교</summary><p>이전: '+e(r['before_first'])+'</p><p>추가: '+e(r['after_first'])+'</p></details><small>이전 최종 경고: '+e(', '.join(r['before_final_flags']) or '없음')+'<br>추가 최종 경고: '+e(', '.join(r['after_final_flags']) or '없음')+'</small></td></tr>'
page+='</tbody></table><script>document.getElementById("search").addEventListener("input",e=>{const q=e.target.value.toLowerCase();document.querySelectorAll("tbody tr").forEach(r=>r.hidden=!r.textContent.toLowerCase().includes(q));});</script></html>'
(P/'comparison.html').write_text(page)
for before,after in zip(read(ROOT/protocol['baseline_path']/'jobs.json'),read(P/'jobs.json')):
 req=json.loads(json.dumps(after['request']))
 assert req['messages'][0]['content']==before['request']['messages'][0]['content']+'\n'+protocol['added_system_sentence']
 req['messages'][0]['content']=before['request']['messages'][0]['content'];assert req==before['request']
assert protocol['endpoint_sha256']==protocol['baseline_endpoint_sha256']
save('artifact_validation.json',{'paired_outputs':len(rows),'requests_only_system_suffix_changed':70,
 'same_endpoint':True,'all_success':all(r['status']=='success' for r in new),
 'files_sha256':{n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in ['jobs.json','baseline_outputs.json','final_outputs.json','comparison.json']}})
print(json.dumps(summary,ensure_ascii=False,indent=2))

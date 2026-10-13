"""Render the actual 20-input run. Never call models or alter outputs."""
import csv,json,html,hashlib
from pathlib import Path
from collections import Counter
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
read=lambda p:json.loads(p.read_text())
save=lambda name,x:(P/name).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
rows=read(P/'final_outputs.json');inputs=read(P/'inputs.json');protocol=read(P/'protocol.json')
assert len(rows)==len(inputs)==20
by={r['id']:r for r in rows};checks=[]
for i in inputs:
 r=by[i['id']];assert i['standard']==r['input']
 if r['status']=='success':assert r['output']
metrics={'input_count':20,'successful_translations':sum(r['status']=='success' for r in rows),'failed_ids':[r['id'] for r in rows if r['status']!='success'],'source_identical_ids':[r['id'] for r in rows if r.get('output')==r['input']], 'flagged_ids':[r['id'] for r in rows if r.get('final_check',{}).get('flags')],'high_flagged_ids':[r['id'] for r in rows if r.get('final_check',{}).get('repair_required')],'flag_counts':dict(Counter(f['kind'] for r in rows for f in r.get('final_check',{}).get('flags',[]))),'analysis_calls':protocol['analysis_calls'],'translation_calls':protocol['translation_calls'],'repair_attempted':protocol['repair_attempted'],'repair_accepted':protocol['repair_accepted'],'not_accuracy':True}
retrieval=read(P/'retrieval.json');jobs={r['id']:r for r in read(P/'jobs.json')};measures=[]
for r in retrieval:
 refs=r['packets']['v2_graph']['references'];j=jobs[r['id']]
 measures.append({'id':r['id'],'candidate_bindings':len(refs),'unique_segments':len({tuple(f['input_binding']['span']) for f in refs}),'unique_candidate_ids':len({f['id'] for f in refs}),'graph_paths':len(r['packets']['v2_graph']['graph_paths']),'user_message_chars':len(j['request']['messages'][1]['content']),'terminal_plan_count':sum(f.get('retrieval_route')=='function_bound_terminal' for f in refs)})
save('summary.json',metrics);save('input_statistics.json',measures)
lines=['새 표준어20개 — 현재 KG·조회·생성 경로 그대로 실행','경북40대 지시 추가 없음 / 번호별 독립 입력 / 15·17번 문장 묶음 유지','KG·조회 코드 변경 없음. 분석·생성·검사 기록은 같은 폴더에 보존.','']
for i in inputs:
 r=by[i['id']];lines.extend([f"{i['number']}. {i['id']}",f"원문: {r['input']}",f"번역: {r.get('output') or '[생성 실패: '+r['status']+']'}",''])
(P/'translations.txt').write_text('\n'.join(lines)+'\n')
with (P/'translations.tsv').open('w',newline='') as f:
 w=csv.writer(f,delimiter='\t');w.writerow(['number','id','input','output','status','selection','flags'])
 for i in inputs:
  r=by[i['id']];w.writerow([i['number'],r['id'],r['input'],r.get('output',''),r['status'],r.get('selection',''),','.join(f['kind'] for f in r.get('final_check',{}).get('flags',[]))])
style='<style>body{font-family:system-ui,sans-serif;max-width:1300px;margin:28px auto;padding:0 18px;line-height:1.7;color:#172333}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccd6df;padding:12px;text-align:left;vertical-align:top}th{background:#edf3f8}.note{padding:15px;background:#fff2c8}pre{white-space:pre-wrap;font:inherit}a{color:#17509a}</style>'
esc=html.escape
start='<!doctype html><html lang="ko"><meta charset="utf-8"><title>새 표준어20개 번역 결과</title>'+style+'<h1>새 표준어20개 번역 결과</h1><p class="note">현재 시스템의 새 입력 실행 결과입니다. 과거70개와 입력이 다르므로 직접적인 개선율 비교는 아닙니다. KG·조회·생성 설정을 유지했습니다. 자동 검사에 경고가 없어도 자연스러운 번역이라는 뜻은 아닙니다.</p><p><a href="translations.txt">원문·번역 TXT</a> · <a href="translations.tsv">TSV</a> · <a href="summary.json">실행 수치</a> · <a href="review.txt">검토 메모</a></p>'
page=start+'<table><tr><th>번호</th><th>원문</th><th>최종 번역</th><th>자동 검사</th></tr>'
compare=start+'<h2>최초 출력과 최종 선택</h2><p>같은 입력의 수정 전후이며 과거70개와의 비교표가 아닙니다.</p><table><tr><th>번호 / 원문</th><th>최초 출력</th><th>최종 출력 / 선택</th></tr>'
for i in inputs:
 r=by[i['id']];flags=', '.join(f['kind'] for f in r.get('final_check',{}).get('flags',[])) or ('자동 경고 없음 — 품질 보증 아님' if r['status']=='success' else r['status'])
 page+='<tr>'+''.join('<td>'+esc(str(v))+'</td>' for v in [i['number'],r['input'],r.get('output') or '[미생성]',flags])+'</tr>'
 compare+='<tr>'+''.join('<td>'+esc(str(v))+'</td>' for v in [str(i['number'])+'. '+r['input'],r.get('first_output') or '[미생성]',(r.get('output') or '[미생성]')+' / '+r.get('selection',r['status'])])+'</tr>'
(P/'translations.html').write_text(page+'</table></html>');(P/'comparison.html').write_text(compare+'</table></html>')
print(json.dumps(metrics,ensure_ascii=False,indent=2))
print((P/'translations.txt').read_text())

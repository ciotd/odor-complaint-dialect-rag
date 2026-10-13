"""Audit supplied comparison data against frozen requests and local documentary pages."""
import html,json,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent
ROOT=P.parents[1]
G=ROOT/'reports/20261012_construction_generation'
def read(p):return json.loads(p.read_text())
def save(name,data):(P/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
sonnet=dict(line.split(' ',1) for line in (P/'sonnet_user_supplied_70.txt').read_text().splitlines() if line)
new={r['id']:r for r in read(G/'final_outputs.json')}
old={r['id']:r for r in read(G/'baseline_outputs.json')}
jobs={r['id']:r for r in read(G/'jobs.json')}
assert len(sonnet)==70 and sonnet.keys()==new.keys()==old.keys()
rows=[dict(id=sid,input=new[sid]['input'],qwen_previous=old[sid]['output'],qwen_latest=new[sid]['output'],sonnet_user_supplied=out) for sid,out in sonnet.items()]
save('sonnet_comparison_70.json',rows)
e=html.escape
page='''<!doctype html><html lang="ko"><meta charset="utf-8"><title>새 Sonnet 피드백·Qwen70개 비교</title>
<style>body{font-family:sans-serif;margin:24px;line-height:1.7}table{border-collapse:collapse;width:100%}td,th{border:1px solid #bbc8d4;padding:12px;vertical-align:top}th{background:#eef4fa}pre{white-space:pre-wrap}</style>
<h1>새로 제공한 Sonnet70개와 직전·최신 Qwen</h1>
<p>Sonnet은 사용자 제공 결과이며 새로 호출하지 않았습니다. 앞선 Sonnet38개와 별도 자료입니다. Sonnet이 선택한 대구·경북30대 설정은 화자 조사로 검증한 규칙이 아닙니다. 모델·말투 지시·근거 조건이 다르므로 KG의 효과를 단독으로 측정하는 실험이 아닙니다.</p>
<p><a href="sonnet_feedback_review.txt">요청·원문 대조와 개선안</a> | <a href="../latest/index.html">최신 자료 안내</a></p>
<table><tr><th>ID</th><th>원문</th><th>직전 Qwen</th><th>최신 Qwen</th><th>새 Sonnet</th></tr>'''
for r in rows:page+='<tr>'+''.join('<td>'+e(r[k])+'</td>' for k in ['id','input','qwen_previous','qwen_latest','sonnet_user_supplied'])+'</tr>'
(P/'sonnet_comparison_70.html').write_text(page+'</table></html>')
audit={}
for sid in ['DEV002','DEV005','DEV009','DEV017','DEV020','DEV030','LONG006','DEV027','LONG001']:
 request=jobs[sid]['request']
 data=json.loads(request['messages'][1]['content'].split('\n',1)[1])
 audit[sid]={'input':new[sid]['input'],'output':new[sid]['output'],
  'request_sha256':hashlib.sha256(json.dumps(request,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),
  'plan':data['transformation_plan']}
save('sonnet_request_audit.json',audit)
pages={(p['source_id'],p['pdf_page']):p for p in map(json.loads,(ROOT/'kg_v2/local/pages.jsonl').read_text().splitlines())}
checks=[('NAMU_HONORIFICS_20260908',26,'가세예'),('NAMU20260901',6,'오늘 → 올'),
 ('NAMU_GRAMMAR_20260908',4,'시고'),('NAMU_GRAMMAR_20260908',45,'쉬다'),
 ('NAMU_GRAMMAR_20260908',29,'짭다'),('RYU2014',27,'앞에 가요'),
 ('NAMU_GRAMMAR_20260908',28,'-대/-더라/-더래'),('NAMU20260901',26,"할바'시'"),
 ('RYU2014',10,'거 있네'),('NAMU_GRAMMAR_20260908',43,'이빠이'),
 ('NAMU_GRAMMAR_20260908',37,'개않다/갠찮다')]
evidence=[]
for sid,n,needle in checks:
 p=pages[sid,n];i=p['text'].find(needle);assert i>=0,(sid,n,needle)
 evidence.append({'source_id':sid,'pdf_page':n,'searched':needle,'page_text_sha256':hashlib.sha256(p['text'].encode()).hexdigest(),
  'excerpt':p['text'][max(0,i-140):i+len(needle)+180],
  'interpretation_limit':'Confirms presence of source description, not correctness of all derived surfaces or suitability for a modern speaker profile.'})
facts={r['id']:r for r in map(json.loads,(ROOT/'kg_v2/facts.jsonl').read_text().splitlines())}
fact=facts['NAMU_GRAMMAR_20260908:v2:full:0768']
assert all('짭다' not in ev['quote'] for ev in fact['evidence'])
save('sonnet_documentary_audit.json',{'evidence':evidence,'incomplete_stored_quote':fact,
 'note':'The original PDF29 text includes the target row; stored quotation omits it. No production mutation performed.'})
save('sonnet_comparison_metadata.json',{
 'provenance':'User supplied latest Sonnet70 outputs copied from conversation; not an API run or gold labels.',
 'model_calls':0,'outputs':len(rows),'production_changes':False,
 'source_identical_previous':[r['id'] for r in rows if r['input']==r['qwen_previous']],
 'source_identical_latest':[r['id'] for r in rows if r['input']==r['qwen_latest']],
 'sonnet_profile':'Sonnet-selected Daegu/Gyeongbuk speaker in their 30s; not empirically validated or adopted as system default.'})
print('Aligned70 user-supplied outputs; audited9 requests and11 page excerpts; no model calls or production changes.')

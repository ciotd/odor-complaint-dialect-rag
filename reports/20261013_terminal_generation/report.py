"""Reproducible retrospective comparison of saved outputs; no model calls."""
import csv,html,json,re,sys,hashlib
from pathlib import Path
from functools import lru_cache
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE/'snapshot'))
from preservation_check import check_preservation

def read(p):return json.loads(p.read_text())
def save(name,x):(HERE/name).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def order(x):return (next(i for i,p in enumerate(['DEV','LONG','NEW','ADVCE']) if x.startswith(p)),x)
latest=read(HERE/'final_outputs.json');latest.sort(key=lambda r:order(r['id']))
sources={r['id']:r['input'] for r in latest};ids=list(sources)
series=[];files={}
def add(key,label,path,rows,note,stage='final',peer=False):
    data={}
    for r in rows:
        assert r['id'] not in data,(key,r['id'])
        assert sources[r['id']]==r['input'],(key,r['id'],'input mismatch')
        assert isinstance(r['output'],str) and r['output']
        data[r['id']]={'output':r['output'],'first_output':r.get('first_output',r['output'])}
    series.append(dict(key=key,label=label,path=str(path.relative_to(ROOT)),note=note,stage=stage,peer=peer,rows=data))
    files[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
legacy=ROOT/'current_kg/experiments/reports/integrated_development/comparison.tsv'
with legacy.open() as f:old=list(csv.DictReader(f,delimiter='\t'))
for c in ['prompt_only','source_hybrid','record_hybrid','graph_hybrid']:
    add('legacy_'+c,'기존 KG 통합 / '+c,legacy,[dict(id=r['id'],input=r['standard'],output=r[c]) for r in old], '30개 개발 입력. 이후 v2 실험의 네 조건 및 A/B/C/D와 다른 실험.')
for folder,key,label in [('translation_20261012','v2_initial','KG v2 최초'),('translation_20261012_speech_style','v2_style','높임 후보 순위 수정'),('translation_20261012_ending_repair','v2_ending','초기 종결 대응 수정')]:
    p=ROOT/'kg_v2/reports'/folder/'outputs.json';rows=read(p)
    for c in ['no_kg','legacy_graph','v2_direct','v2_graph']:
        subset=[r for r in rows if r['condition']==c];assert len(subset)==38
        add(key+'_'+c,label+' / '+c,p,subset,'38개. 후속 실행의 no_kg/legacy_graph 등 재사용 기준선은 독립 재실험이 아니다. 정확한 재사용 범위는 해당 protocol.json 참조.')
p=ROOT/'reports/kg_v2_factorial_20261012/outputs.json';rows=read(p)
for c in 'ABCD':
    sub=[r for r in rows if r['condition']==c];assert len(sub)==50
    add('factorial_'+c,'A/B/C/D 실험 / '+c,p,sub,'50개. A 현재조회+기존형식, B 의미검색추가+기존형식, C 현재조회+변환계획, D 의미검색추가+변환계획. 이후 동일 실험 반복 안 함.')
for key,folder,label,note in [
 ('pipeline','kg_v2_pipeline_repair_20261012','분석·보존 파이프라인 수정','최초70개+보존 검사에 따른 최대1회 재생성. 50개 A 기준선과 별도20개 기준선으로 비교한 실행.'),
 ('construction','20261012_construction_generation','인용·의도 조회 수정','현재 실험의 주 비교군. 시스템 지시/모델/생성 설정 동일.'),
 ('profile','20261013_gyeongbuk40_prompt','경북40대 지시만 추가','별도 분기 실험. 최신 종결 수정의 부모 버전이 아니다.'),
 ('terminal','20261013_terminal_generation','최신 종결 기능별 조회 수정','70개 신규 생성. 경북40대 지시 추가 안 함. 최초출력과 최종선택 구별.')]:
 p=ROOT/'reports'/folder/'final_outputs.json';rows=read(p);assert len(rows)==70;add(key,label,p,rows,note)
p=ROOT/'reports/model_comparison_20261012/comparison.json'
for key,label in [('astra_high_no_kg','Astra high / 외부 근거 없음'),('sonnet_user_supplied','Sonnet / 처음 제공된38개')]:
 add(key,label,p,[dict(id=r['id'],input=r['standard'],output=r['outputs'][key]) for r in read(p)],'별도 모델 참고 출력. 정답 및 동일 모델 통제 실험이 아니다.',peer=True)
p=ROOT/'reports/20261012_easy_briefing/sonnet_user_supplied_70.txt';peer=[]
for line in p.read_text().splitlines():
 m=re.match(r'^((?:DEV|LONG|NEW|ADVCE)\d+[AB]?)\s+(.+)$',line)
 if m:peer.append(dict(id=m[1],input=sources[m[1]],output=m[2]))
assert len(peer)==70;add('sonnet70','Sonnet / 나중에 제공된70개',p,peer,'사용자 제공 출력. 입력은 동일 ID로 연결했으며 이 파일 자체에는 원문이 없다. 처음 제공된38개와 다른 버전. 정답 아님.',peer=True)
by={s['key']:s for s in series}
@lru_cache(None)
def screen(src,out):return check_preservation(src,out)
def metrics(key,subset,field='output'):
 d=by[key]['rows'];outs=[(i,d[i][field]) for i in subset];checks=[screen(sources[i],o) for i,o in outs]
 return dict(n=len(outs),source_identical=sum(sources[i]==o for i,o in outs),seye_outputs=sum('세예' in o for i,o in outs),geye_outputs=sum('게예' in o for i,o in outs),screening_any=sum(bool(c['flags']) for c in checks),screening_high=sum(c['repair_required'] for c in checks))
progress=['legacy_graph_hybrid','v2_initial_v2_graph','v2_style_v2_graph','v2_ending_v2_graph','factorial_A','factorial_B','factorial_C','factorial_D','pipeline','construction','profile','terminal']
cohorts={'DEV30':[i for i in ids if i.startswith('DEV')], 'DEV_LONG38':[i for i in ids if i.startswith(('DEV','LONG'))], 'DEV_LONG_NEW50':[i for i in ids if not i.startswith('ADVCE')], 'ALL70':ids}
stats={}
for cohort,subset in cohorts.items():
 stats[cohort]={k:metrics(k,subset) for k in progress if set(subset)<=by[k]['rows'].keys()}
base=by['construction']['rows'];comparison=[]
for r in latest:
 i=r['id'];b=base[i]
 comparison.append(dict(id=i,input=r['input'],before_first=b['first_output'],before=b['output'],first=r['first_output'],after=r['output'],changed=b['output']!=r['output'],selection=r['selection'],before_check=screen(sources[i],b['output']),after_check=r['final_check']))
first_stats={k:metrics(k,ids,'first_output') for k in ['pipeline','construction','profile','terminal']}
summary=dict(protocol=read(HERE/'protocol.json'),series_count=len(series),saved_records=sum(len(s['rows']) for s in series),changed_final=sum(r['changed'] for r in comparison),changed_first=sum(r['before_first']!=r['first'] for r in comparison),cohort_metrics=stats,first_output_metrics_70=first_stats,metric_definitions={'source_identical':'原文と完全一致した入力数。未変換の指標であり誤訳数ではない。','seye_outputs':'세예 문자열을 포함한 출력 수. 이번 정책의 회귀 표면 지표이며 방언 전체의 부적격 판정이 아님.','geye_outputs':'게예 문자열을 포함한 출력 수. 께예와 별개이며 정확한 활용 완성도 점수가 아님.','screening_any':'동일한 최신 검사기로 다시 검사한 경고 입력 수. 방언 품질 점수 아님.','screening_high':'동일한 최신 검사기의 강한 보존 경고 입력 수. 누락 오류가 많아 낮을수록 총품질이 좋다고 단정 못 함.'},limitations=['한 번씩 실행한 개발 자료다. 인과 효과·일반화·통계적 우월성을 확정하지 않는다.','각 역사 단계의 KG/조회/프롬프트가 함께 바뀌었다. A/B/C/D 조건을 후속 단계에 소급해서 부르지 않는다.','반복 저장된 기준선이 있어 saved_records는 독립 모델 호출 수가 아니다.','과거 검사 경고 수를 그대로 섞지 않고 최신 검사기로 회고 검사했다. 최초 출력 비교도 별도 제공.','세예/게예 제거는 일부 목표 달성이다. 다른 비문·의미 오류·표준어 유지와 독립적이다.'])
summary['metric_definitions']['source_identical']='원문과 완전히 일치한 입력 수. 미변환 지표이며 그 자체로 오역 수가 아니다.'
save('summary.json',summary);save('comparison.json',comparison)
save('history.json',dict(sources=sources,series=series,source_sha256=files,cohort_metrics=stats,limitations=summary['limitations']))
# Inspect exactly what the generator received, rather than infer retrieval from output.
traces=[]
for j in read(HERE/'jobs.json'):
 s=j['request']['messages'][-1]['content'];packet=json.loads(s[s.index('{"standard"'):]);i=j['id']
 for segment in packet.get('transformation_plan',[]):
  for c in segment.get('candidates',[]):
   b=c.get('binding',{});e=b.get('ending_conversion')
   if e:traces.append(dict(id=i,user_message_chars=len(s),candidate_id=c['id'],**e,output=by['terminal']['rows'][i]['output'],preferred_surface_present=e['preferred_surface'] in by['terminal']['rows'][i]['output']))
save('terminal_plan_trace.json',traces)
with (HERE/'history.tsv').open('w',newline='') as f:
 w=csv.writer(f,delimiter='\t');w.writerow(['id','input','experiment','label','output','first_output','source_file','note'])
 for i in ids:
  for s in series:
   if i in s['rows']:w.writerow([i,sources[i],s['key'],s['label'],s['rows'][i]['output'],s['rows'][i]['first_output'],s['path'],s['note']])
with (HERE/'comparison.tsv').open('w',newline='') as f:
 w=csv.writer(f,delimiter='\t');w.writerow(['id','input','before_first','before','first','after','selection']);w.writerows([r[k] for k in ['id','input','before_first','before','first','after','selection']] for r in comparison)
(HERE/'translations.txt').write_text('2026-10-13 종결 기능별 조회 수정 후 실제 Qwen70개 최종 출력\n'+''.join(f"\n{r['id']}\n원문: {r['input']}\n번역: {r['output']}\n" for r in latest))
(HERE/'comparison.txt').write_text('주 비교군: 인용·의도 조회 수정 후70개 / 최신: 종결 기능별 조회 수정 후70개\n'+''.join(f"\n{r['id']}\n원문: {r['input']}\n직전: {r['before']}\n최초: {r['first']}\n최종: {r['after']}\n" for r in comparison))
style='<style>body{font-family:system-ui,sans-serif;max-width:1500px;margin:28px auto;padding:0 20px;line-height:1.65;color:#172333}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccd6df;padding:10px;text-align:left;vertical-align:top}th{background:#edf3f8}select,input{padding:8px;max-width:100%;margin:6px}pre{white-space:pre-wrap;font-family:inherit}.note{background:#fff2c8;padding:15px}tr.changed{background:#f0faf3}a{color:#174f9a}</style>'
def page(title):return '<!doctype html><html lang="ko"><meta charset="utf-8"><title>'+html.escape(title)+'</title>'+style+'<h1>'+html.escape(title)+'</h1>'
esc=html.escape
p=page('직전·최신 Qwen70개 비교')+'<p><a href="history.html">모든 과거 조건·모델 출력 비교</a> · <a href="review.txt">분석 결론</a> · <a href="translations.txt">최신 번역만</a></p><p class="note">직전은 인용·의도 조회 수정 버전이다. 경북40대 지시는 별도 분기이며 이번에 추가하지 않았다. 초록색은 최종 문자열 변경이며 품질 향상을 뜻하지 않는다. 자동 검사에 통과해도 오류가 남는다.</p><table><tr><th>ID / 원문</th><th>직전 최종</th><th>최신 최초</th><th>최신 최종 / 검사</th></tr>'
for r in comparison:
 flags=', '.join(f['kind'] for f in r['after_check']['flags']) or '자동 경고 없음 (정확도 보증 아님)'
 p+='<tr'+(' class="changed"' if r['changed'] else '')+'>'+''.join('<td>'+esc(s)+'</td>' for s in [r['id']+' '+r['input'],r['before'],r['first'],r['after']+' ['+flags+']'])+'</tr>'
(HERE/'comparison.html').write_text(p+'</table></html>')
# Self-contained offline explorer: all conditions retained, selectable pairs and per-input history.
blob=json.dumps(dict(sources=sources,series=series,ids=ids),ensure_ascii=False).replace('<','\\u003c')
p=page('실험 전체 이력 — 같은 입력으로 비교')+'<p><a href="review.txt">비교 결론</a> · <a href="comparison.html">직전·최신70개</a> · <a href="history.tsv">전체 TSV</a> · <a href="summary.json">공통 입력별 통계</a></p><p class="note">과거 KG v1, KG v2 네 조건, A/B/C/D, 후속 수정 실험, Astra와 두 버전 Sonnet 출력을 모았다. 비어 있는 항목은 해당 실험에 없는 입력이다. 재사용된 출력은 독립 반복 실험이 아니다. 다른 모델은 참고 자료이며 정답이 아니다.</p><label>비교 왼쪽 <select id="left"></select></label><label>오른쪽 <select id="right"></select></label><label><input type="checkbox" id="changed">서로 다른 출력만</label><p id="notes"></p><table><thead><tr><th>ID / 원문</th><th id="lh"></th><th id="rh"></th></tr></thead><tbody id="rows"></tbody></table><h2>한 입력의 전체 이력</h2><select id="sentence"></select><div id="timeline"></div><script>const DATA='+blob+';</script>'+'''<script>
const el=id=>document.getElementById(id),h=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
for(const s of DATA.series) for(const id of ['left','right']) el(id).add(new Option(s.label,s.key));
for(const id of DATA.ids)el('sentence').add(new Option(id+' '+DATA.sources[id],id));
el('left').value='construction';el('right').value='terminal';
function render(){const a=DATA.series.find(s=>s.key===el('left').value),b=DATA.series.find(s=>s.key===el('right').value);el('lh').textContent=a.label;el('rh').textContent=b.label;el('notes').textContent=a.note+' / '+b.note;el('rows').innerHTML=DATA.ids.map(i=>{const x=a.rows[i]?.output,y=b.rows[i]?.output;if(el('changed').checked&&x===y)return '';return '<tr><td>'+h(i+' '+DATA.sources[i])+'</td><td>'+h(x??'해당 실험 입력 없음')+'</td><td>'+h(y??'해당 실험 입력 없음')+'</td></tr>';}).join('');}
function timeline(){const i=el('sentence').value;el('timeline').innerHTML=DATA.series.filter(s=>s.rows[i]).map(s=>'<p><strong>'+h(s.label)+'</strong><br>'+h(s.rows[i].output)+'</p>').join('');}
for(const id of ['left','right','changed'])el(id).onchange=render;el('sentence').onchange=timeline;render();timeline();
</script></html>'''
(HERE/'history.html').write_text(p)
print(json.dumps({'series':len(series),'records':summary['saved_records'],'changed':summary['changed_final'],'stats70':stats['ALL70'],'stats38':stats['DEV_LONG38'],'first70':first_stats,'terminal_plans':len(traces)},ensure_ascii=False,indent=2))

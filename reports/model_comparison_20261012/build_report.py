"""Join all 38 inputs and preserve probe results without treating peers as gold."""
import csv
import hashlib
import json
from pathlib import Path
import statistics

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
OLD=ROOT/'kg_v2/reports/translation_20261012_ending_repair'
ASTRA=ROOT/'reports/astra_high_no_kg_20261012'


def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


inputs=read(ASTRA/'inputs.json')
source={x['id']:x['input'] for x in inputs}
astra=dict(line.split(' ',1) for line in (ASTRA/'output.txt').read_text().splitlines())
sonnet=dict(line.split(' ',1) for line in (BASE/'sonnet_user_output.txt').read_text().splitlines())
assert set(source)==set(astra)==set(sonnet) and len(source)==38
old={(r['id'],r['condition']):r for r in read(OLD/'outputs.json')}
probes={(r['id'],r['condition']):r for r in read(BASE/'probe_outputs.json')}
assert len(probes)==55 and all(x['status']=='success' for x in probes.values())
notes=read(BASE/'review_notes.json')['items'];assert set(notes)==set(source)
labels={'astra_high_no_kg':'Astra high · 외부 근거 없음',
        'sonnet_user_supplied':'Sonnet · 사용자 제공',
        'qwen_plain':'Qwen · 문장만',
        'qwen_no_kg_analysis':'Qwen · 분석 포함, KG 없음',
        'qwen_legacy_graph':'Qwen · KG v1',
        'qwen_v2_direct':'Qwen · KG v2 직접',
        'qwen_v2_graph':'Qwen · KG v2 관계'}
rows=[]
for sid,standard in source.items():
    assert all(old[sid,c]['input']==standard for c in ['no_kg','legacy_graph','v2_direct','v2_graph'])
    assert probes[sid,'qwen_plain']['input']==standard
    rows.append({'id':sid,'standard':standard,'outputs':{
        'astra_high_no_kg':astra[sid], 'sonnet_user_supplied':sonnet[sid],
        'qwen_plain':probes[sid,'qwen_plain']['output'],
        **{'qwen_'+('no_kg_analysis' if c=='no_kg' else c):old[sid,c]['output']
           for c in ['no_kg','legacy_graph','v2_direct','v2_graph']}},
        'review_note':notes[sid]})
save(BASE/'comparison.json',rows)
with (BASE/'comparison.tsv').open('w') as f:
    w=csv.writer(f,delimiter='\t',lineterminator='\n');w.writerow(['id','standard',*labels,'review_note'])
    for row in rows:w.writerow([row['id'],row['standard'],*[row['outputs'][c] for c in labels],row['review_note']])
with (BASE/'probe_comparison.tsv').open('w') as f:
    w=csv.writer(f,delimiter='\t',lineterminator='\n')
    w.writerow(['id','standard','condition','latest_saved_v2_graph','new_output'])
    for (sid,c),r in probes.items():
        if c!='qwen_plain':w.writerow([sid,r['input'],c,old[sid,'v2_graph']['output'],r['output']])
original_jobs=read(OLD/'jobs.json');jobs=read(BASE/'probe_jobs.json')
stats={c:{'n':len(sub), 'median_user_characters':statistics.median(len(j['request']['messages'][1]['content']) for j in sub)}
       for c in labels for sub in [[j for j in jobs if j['condition']==c]] if sub}
for c in ['no_kg','legacy_graph','v2_direct','v2_graph']:
    sub=[j for j in original_jobs if j['condition']==c]
    stats['saved_'+c]={'n':len(sub),'median_user_characters':statistics.median(len(j['request']['messages'][1]['content']) for j in sub)}
for c in ['full_repeat','compact_references','without_meonjeo_mapping']:
    sub=[j for j in jobs if j['condition']==c]
    stats[c]={'n':len(sub),'median_user_characters':statistics.median(len(j['request']['messages'][1]['content']) for j in sub)}
repeat_changes=[sid for (sid,c),r in probes.items() if c=='full_repeat' and r['output']!=old[sid,'v2_graph']['output']]
for n,h in read(OLD/'protocol.json')['kg_hashes'].items():
    assert digest(ROOT/'kg_v2'/n)==h
summary={
    'inputs':38,'displayed_conditions':7,'new_qwen_generations':55,'successes':55,
    'prompt_character_counts':stats,'full_repeat_changed_ids':repeat_changes,
    'sonnet_provenance':{'origin':'user pasted outputs','exact_version':None,'prompt':None,'decoding_settings':None,'tool_use':'not independently verified'},
    'astra_provenance':read(ASTRA/'protocol.json'),
    'same_no_kg_and_v2_requests':['DEV011','DEV018'],
    'single_mapping_ablation':{'removed_id':'RYU2014:v2:full:0131','cases':['LONG001','LONG005','LONG008'],
        'observation':'All three full-repeat outputs contain 앞에; all three removal outputs contain 먼저. Other output spans can also change.'},
    'compact_probe':{'cases':['DEV006','DEV019','LONG001','LONG005','LONG006','LONG007','LONG008'],
        'observations':{'DEV006':'계셔 -> 계세요; source morphology conflict remains; 시고 requires regional naturalness review.',
                        'DEV019':'걸으세 -> 걸으세요; standard ending retained, not increased dialect realization.',
                        'LONG006':'가노/좋아하노 -> 가던/좋아하는; 가던 still differs in aspect from 가는.',
                        'LONG007':'그리그리 repetition absent.',
                        'LONG008':'앞에/시마이 remain; 쉬이소 -> 쉬어예 not certified as an improvement.'}},
    'production_kg_changed_in_this_comparison':False,
    'interpretation':'Model/generation limitations, incomplete analysis-to-retrieval paths, context-sensitive lexical applicability and reference presentation all contribute. No global accuracy score or model ranking claimed.',
    'limitations':['Seven compact cases are post-selected diagnostics; one sample per condition.',
                   'Compact input removes evidence text as well as check logs, so token length alone is not isolated.',
                   'Same-seed full-repeat differs on LONG006; no deterministic or statistical guarantee.',
                   'Peer outputs are not ground truth; no independent native-speaker evaluation.',
                   'Astra uses high reasoning and one 38-item batch; Qwen uses per-input requests with thinking disabled.'],
    'artifact_hashes':{str(p.relative_to(ROOT)):digest(p) for p in [OLD/'outputs.json',OLD/'jobs.json',ASTRA/'output.txt',BASE/'sonnet_user_output.txt',BASE/'probe_jobs.json',BASE/'probe_outputs.json']}}
save(BASE/'summary.json',summary)

# Self-contained viewer: raw model strings are rendered with textContent.
data=json.dumps({'rows':rows,'labels':labels,'probes':list(probes.values())},ensure_ascii=False).replace('<','\\u003c')
html='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>38개 방언 번역 비교 · 2026-10-12</title>
<style>body{font:16px/1.65 system-ui,sans-serif;color:#172333;background:#f2f5f8;margin:0 auto;padding:24px;max-width:1050px}h1{font-size:26px}select{font:inherit;width:100%;padding:12px}article,aside{background:white;padding:18px;margin:14px 0;border-radius:9px;border:1px solid #ccd7e0}article h3{margin:0 0 8px;font-size:16px;color:#335d85}p{white-space:pre-wrap;margin:0}aside{background:#fff7e3}button{padding:8px 18px;margin:8px 8px 0 0}small{display:block;color:#526375}</style>
<h1>38개 입력 · 7개 조건 비교</h1><small>Astra·사용자 제공 Sonnet·Qwen 원출력. 사람 화자 평가 전이며 정답이나 정확도 순위가 아닙니다. 조건마다 프롬프트·추론 설정·배치 방식이 다릅니다.</small>
<select id="select"></select><button id="prev">이전</button><button id="next">다음</button>
<article><h3>표준어 원문</h3><p id="source"></p></article><aside id="note"></aside><div id="outputs"></div><h2>해당 입력의 추가 진단 실험</h2><div id="probes"></div>
<script>const data=__DATA__;const select=document.getElementById('select');
data.rows.forEach((r,i)=>{let o=document.createElement('option');o.value=i;o.textContent=r.id+' '+r.standard;select.append(o)});
function card(parent,label,value){let a=document.createElement('article'),h=document.createElement('h3'),p=document.createElement('p');h.textContent=label;p.textContent=value;a.append(h,p);parent.append(a)}
function render(){let r=data.rows[+select.value];document.getElementById('source').textContent=r.standard;document.getElementById('note').textContent=r.review_note;let out=document.getElementById('outputs');out.replaceChildren();Object.entries(data.labels).forEach(([k,v])=>card(out,v,r.outputs[k]));let probes=document.getElementById('probes');probes.replaceChildren();data.probes.filter(x=>x.id===r.id&&x.condition!=='qwen_plain').forEach(x=>card(probes,x.condition,x.output));}
select.onchange=render;document.getElementById('prev').onclick=()=>{select.value=Math.max(0,+select.value-1);render()};document.getElementById('next').onclick=()=>{select.value=Math.min(data.rows.length-1,+select.value+1);render()};render();</script></html>'''.replace('__DATA__',data)
(BASE/'comparison.html').write_text(html)
print('Built 38-row comparison, 7-condition viewer, 17 probe comparisons, and summary.')
print('Fresh full-repeat changed:',repeat_changes)

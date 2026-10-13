"""Separate input-pipeline and packet effects on the SAME Qwen generator.

No Astra/Sonnet outputs are supplied as prompts, demonstrations or gold answers.
Production KG and retriever are not modified by this diagnostic experiment.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
import json
from pathlib import Path
import sys
import time

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
sys.path.insert(0, str(ROOT/'current_kg/experiments'))
from run_seeded_kg import connection, check_response, error_fields, save, sha

FOCUS = {'DEV006','DEV019','LONG001','LONG005','LONG006','LONG007','LONG008'}
DROP = {'LONG001','LONG005','LONG008'}
SUSPECT = 'RYU2014:v2:full:0131'


def prepare():
    source = ROOT/'kg_v2/reports/translation_20261012_ending_repair/jobs.json'
    jobs=[]
    for original in json.loads(source.read_text()):
        if original['condition']!='v2_graph':
            continue
        sid=original['id']; original_request=original['request']
        req=deepcopy(original_request)
        req['messages'][1]['content']=original['input']
        jobs.append({'id':sid,'condition':'qwen_plain','input':original['input'],'request':req})
        if sid not in FOCUS:
            continue
        jobs.append({'id':sid,'condition':'full_repeat','input':original['input'],
                     'request':deepcopy(original_request)})
        req=deepcopy(original_request)
        prefix, raw=req['messages'][1]['content'].split('\n',1); body=json.loads(raw)
        for ref in body['references']:
            ref['evidence']=[{'pdf_page':e['pdf_page']} for e in ref['evidence']]
            ref.pop('checks',None);ref.pop('status',None)
        req['messages'][1]['content']=prefix+'\n'+json.dumps(body,ensure_ascii=False,separators=(',',':'))
        jobs.append({'id':sid,'condition':'compact_references','input':original['input'],'request':req})
        if sid in DROP:
            req=deepcopy(original_request)
            prefix,raw=req['messages'][1]['content'].split('\n',1);body=json.loads(raw)
            assert any(f['id']==SUSPECT for f in body['references'])
            body['references']=[f for f in body['references'] if f['id']!=SUSPECT]
            body['graph_paths']=[e for e in body['graph_paths'] if SUSPECT not in (e['source'],e['target'])]
            req['messages'][1]['content']=prefix+'\n'+json.dumps(body,ensure_ascii=False,separators=(',',':'))
            jobs.append({'id':sid,'condition':'without_meonjeo_mapping','input':original['input'],'request':req})
    assert len(jobs)==55
    settings=[{k:v for k,v in j['request'].items() if k!='messages'} for j in jobs]
    assert all(x==settings[0] for x in settings)
    assert all(j['request']['messages'][0]==jobs[0]['request']['messages'][0] for j in jobs)
    save(BASE/'probe_jobs.json',jobs)
    save(BASE/'probe_protocol.json',{
        'status':'prepared','planned_generations':len(jobs),'requested_settings':settings[0],
        'jobs_sha256':sha(BASE/'probe_jobs.json'),'source_jobs_sha256':sha(source),
        'conditions':{
            'qwen_plain':'Same system prompt and decoding; user message is only the original sentence. Removes analysis, morphology, references and structured-user instructions together.',
            'full_repeat':'Exactly repeat the saved v2_graph request to observe run-to-run variability.',
            'compact_references':'Same request except evidence quote bodies, condition-check logs and per-reference status removed. Claims/conditions/scope/notes/bindings/paths retained. Evidence text loss is a confound, not a lossless serialization claim.',
            'without_meonjeo_mapping':'Same request except exactly one 먼저->앞에 statement and any incident paths removed.'},
        'external_model_outputs_in_prompts':False,
        'selection':'7 diagnostic failure cases chosen after observing development outputs; 3 mapping-removal cases among them.',
        'limitations':['One new sample per condition; same seed is not a determinism guarantee.',
                      'Prompt and batch conventions differ across models; Sonnet version/settings/prompt not supplied.',
                      'No independent native-speaker quality labels or causal significance test.']})
    print('Prepared',len(jobs),'requests; production KG/retriever unchanged.')


def run():
    protocol=json.loads((BASE/'probe_protocol.json').read_text())
    assert sha(BASE/'probe_jobs.json')==protocol['jobs_sha256']
    jobs=json.loads((BASE/'probe_jobs.json').read_text());call,endpoint=connection()
    assert jobs[0]['request']['model'] in [x['id'] for x in call('/models')['data']]
    protocol.update(status='running',endpoint_sha256=endpoint);save(BASE/'probe_protocol.json',protocol)
    def work(j):
        path=BASE/'raw'/(j['id']+'_'+j['condition']+'.json')
        if path.exists():
            existing=json.loads(path.read_text());assert existing['request']==j['request']
            if existing['status']=='success':return existing
        row={**j,'status':'failed','attempts':[]}
        for _ in range(2):
            start=time.monotonic()
            try:
                response=call('/chat/completions',j['request'])
                row['attempts'].append({'seconds':time.monotonic()-start,'response':response})
                row.update(output=check_response(response,j['request']['model']),status='success');break
            except Exception as e:
                row['attempts'].append({'seconds':time.monotonic()-start,**error_fields(e)})
        save(path,row);return row
    rows=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        for n,result in enumerate(as_completed([pool.submit(work,j) for j in jobs]),1):
            r=result.result();rows.append(r);print(n,len(jobs),r['id'],r['condition'],r['status'],flush=True)
    rows.sort(key=lambda r:(r['id'],r['condition']))
    save(BASE/'probe_outputs.json',[{k:r[k] for k in ['id','input','condition','status','output'] if k in r} for r in rows])
    protocol.update(status='completed' if all(r['status']=='success' for r in rows) else 'completed_with_failures',
                    successful_generations=sum(r['status']=='success' for r in rows),
                    actual_attempts=sum(len(r['attempts']) for r in rows))
    save(BASE/'probe_protocol.json',protocol)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','run']);a=p.parse_args()
    globals()[a.mode]()

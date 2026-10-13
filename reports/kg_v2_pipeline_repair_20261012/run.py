"""Versioned before/after validation. Preserve old runs; no quality-selected reruns."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
mode=sys.argv[1]
sys.path.insert(0,str(ROOT/'current_kg/experiments'))
sys.path.insert(0,str(ROOT/'kg_v2'))
if mode in {'analyze','baseline'}:sys.path.insert(0,str(HERE/'before'))
from run_seeded_kg import save,sha,check_response,error_fields
from model_client import connection

def read(p):return json.loads(p.read_text())

def config():
    return read(ROOT/'reports/kg_v2_factorial_20261012/protocol.json')['config']

def init():
    assert not (HERE/'before').exists()
    (HERE/'before').mkdir()
    paths=['kg_v2/'+n for n in ['facts.jsonl','graph.json','sentence_retrieval.py','query.py','run_translation.py']]
    for path in paths:shutil.copyfile(ROOT/path,HERE/'before'/Path(path).name)
    old=ROOT/'reports/kg_v2_factorial_20261012'
    save(HERE/'baseline_jobs.json',[{**j,'condition':'before'} for j in read(old/'jobs.json') if j['condition']=='A'])
    save(HERE/'baseline_outputs.json',[{**r,'condition':'before','provenance':'reused_frozen_A'} for r in read(old/'outputs.json') if r['condition']=='A'])
    save(HERE/'analysis.json',read(old/'analysis.json'))
    probes=read(ROOT/'reports/kg_v2_advisory_20261012/new_contrast_probes.json')['items']
    save(HERE/'new_inputs.json',[{'id':r['id'],'standard':r['input']} for r in probes])
    save(HERE/'protocol.json',{'status':'initialized','before_hashes':{p:sha(ROOT/p) for p in paths},
         'prior_artifacts':{str(p.relative_to(ROOT)):sha(p) for p in old.glob('*.json')},
         'design':'before/after development repair; 50 reused frozen baselines + 20 new paired probes',
         'quality_policy':'one first pass per input; at most one flagged preservation repair, saved separately; no human quality-based reruns',
         'limitations':['Multiple pipeline changes are bundled, not an isolated factor ablation.',
                        '20 model-authored probes and 50 known inputs are not independent human gold.']})

def analyze():
    from run_auto_analysis_development import analyze_one
    from source_analysis_guard import guard_analysis
    from sentence_retrieval import morphology,semantic_guard
    call,endpoint=connection(timeout=180);cfg=config()
    def work(row):
        path=HERE/'analysis_requests'/(row['id']+'.json')
        result=read(path) if path.exists() else analyze_one(call,cfg,row,HERE)
        if result['status']!='validated' and all(a.get('error_type')=='URLError' for a in result['attempts']):
            save(HERE/'blocked_network_attempts'/(row['id']+'.json'),result)
            result=analyze_one(call,cfg,row,HERE)
        # Additional attempts only with schema feedback, using the prior validated runner.
        if result['status']!='validated':
            sys.path.insert(0,str(ROOT/'reports/kg_v2_factorial_20261012'))
            from experiment import repair_analysis
            result=repair_analysis(call,cfg,row,result,path)
        return result
    results=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        for f in as_completed([pool.submit(work,r) for r in read(HERE/'new_inputs.json')]):
            r=f.result();results.append(r);print(r['id'],r['status'],flush=True)
    assert all(r['status']=='validated' for r in results)
    items=[]
    for r in sorted(results,key=lambda x:x['id']):
        a,g=guard_analysis(r['normalized_analysis']);item=a['items'][0]
        item,sg=semantic_guard(item,morphology(item['input']));items.append(item)
    original=read(ROOT/'reports/kg_v2_factorial_20261012/analysis.json')['items']
    save(HERE/'analysis.json',{'items':original+items})
    p=read(HERE/'protocol.json');p.update(endpoint_sha256=endpoint,new_analysis_attempts=sum(len(r['attempts']) for r in results));save(HERE/'protocol.json',p)

def execute(jobs,dirname):
    call,_=connection(timeout=180)
    def work(j):
        path=HERE/dirname/(j['id']+'.json')
        if path.exists():
            prev=read(path);assert prev['request']==j['request']
            if prev['status']=='success':return prev
        r={**j,'status':'failed','attempts':[]}
        for _ in range(2):
            start=time.monotonic()
            try:
                response=call('/chat/completions',j['request'])
                r['attempts'].append({'elapsed_seconds':time.monotonic()-start,'response':response})
                r.update(output=check_response(response,j['request']['model']),status='success');break
            except Exception as e:r['attempts'].append(error_fields(e))
        save(path,r);return r
    rows=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        for i,f in enumerate(as_completed([pool.submit(work,j) for j in jobs]),1):
            r=f.result();rows.append(r);print(dirname,i,len(jobs),r['id'],r['status'],flush=True)
    return sorted(rows,key=lambda x:x['id'])

def baseline():
    from sentence_retrieval import SentenceRetriever,morphology
    from run_translation import make_request
    engine=SentenceRetriever(HERE/'before');jobs=[]
    for item in read(HERE/'analysis.json')['items']:
        if not item['id'].startswith('ADVCE'):continue
        m=morphology(item['input']);r=engine.retrieve(item,m)
        save(HERE/'baseline_retrieval'/(item['id']+'.json'),r)
        jobs.append({'id':item['id'],'input':item['input'],'condition':'before','request':make_request(config(),item,m,r['packets']['v2_graph'])})
    prior=read(ROOT/'reports/kg_v2_factorial_20261012/jobs.json')
    save(HERE/'baseline_jobs.json',[{**j,'condition':'before'} for j in prior if j['condition']=='A']+jobs)
    rows=execute(jobs,'baseline_raw')
    old=[{**r,'condition':'before','provenance':'reused_frozen_A'} for r in read(ROOT/'reports/kg_v2_factorial_20261012/outputs.json') if r['condition']=='A']
    save(HERE/'baseline_outputs.json',old+[{k:r[k] for k in ['id','input','condition','output','status'] if k in r} for r in rows])
    assert len(old+rows)==70 and all(r['status']=='success' for r in rows)

def prepare():
    from sentence_retrieval import SentenceRetriever,morphology
    from run_translation import make_request
    engine=SentenceRetriever();jobs=[];retrieval=[]
    for item in read(HERE/'analysis.json')['items']:
        m=morphology(item['input']);r=engine.retrieve(item,m);retrieval.append(r)
        packet=r['packets']['v2_graph']
        from sentence_retrieval import compact,BUDGET
        assert len(compact(packet))<=BUDGET
        counts={}
        for ref in packet['references']:
            b=ref['input_binding'];assert item['input'][slice(*b['span'])]==b['text']
            key=tuple(b['span']);counts[key]=counts.get(key,0)+1
            assert counts[key]<=6 and ref['usability']=='candidate'
            assert all(c['status']=='satisfied' for c in ref['checks']['conditions'])
        jobs.append({'id':item['id'],'input':item['input'],'condition':'after','request':make_request(config(),item,m,r['packets']['v2_graph'])})
    assert len(jobs)==70
    save(HERE/'retrieval.json',retrieval);save(HERE/'jobs.json',jobs)
    p=read(HERE/'protocol.json');p['after_hashes']={str(f.relative_to(ROOT)):sha(f) for f in (ROOT/'kg_v2').glob('*.py')}
    p['after_hashes'].update({n:sha(ROOT/n) for n in ['kg_v2/facts.jsonl','kg_v2/graph.json','kg_v2/advisory_rules.json']})
    p['job_hash']=sha(HERE/'jobs.json');save(HERE/'protocol.json',p)

def run():
    p=read(HERE/'protocol.json');assert p['job_hash']==sha(HERE/'jobs.json')
    assert all(sha(ROOT/n)==v for n,v in p['after_hashes'].items())
    rows=execute(read(HERE/'jobs.json'),'raw')
    save(HERE/'outputs.json',[{k:r[k] for k in ['id','input','condition','output','status'] if k in r} for r in rows])
    assert all(r['status']=='success' for r in rows)

def repair():
    from preservation_check import check_preservation,repair_request
    rows=read(HERE/'outputs.json');jobs={r['id']:r for r in read(HERE/'jobs.json')}
    checks={r['id']:check_preservation(r['input'],r['output']) for r in rows}
    already={read(p)['id']:read(p) for p in (HERE/'repair_raw').glob('*.json')}
    todo=[{**jobs[r['id']],'condition':'single_preservation_repair',
           'request':repair_request(jobs[r['id']]['request'],r['input'],r['output'],checks[r['id']])}
          for r in rows if checks[r['id']]['repair_required'] and r['id'] not in already]
    directory='repair_v2_raw' if already else 'repair_raw'
    save(HERE/(directory+'_jobs.json'),todo)
    fixed={**already,**{r['id']:r for r in execute(todo,directory)}}
    # Each input is repaired at most once, including earlier checker revisions.
    save(HERE/'repair_jobs.json',[{k:r[k] for k in ['id','input','condition','request']} for r in fixed.values()])
    final=[]
    for r in rows:
        row={**r,'first_output':r['output'],'first_check':checks[r['id']],
             'final_check':checks[r['id']],'repair_attempted':r['id'] in fixed,'selection':'first_pass'}
        if r['id'] in fixed:
            rr=fixed[r['id']]
            if rr['status']=='success':
                c=check_preservation(r['input'],rr['output'])
                row.update(repair_output=rr['output'],repair_check=c)
                old={(x['kind'],x['sentence_index']) for x in checks[r['id']]['flags']}
                new={(x['kind'],x['sentence_index']) for x in c['flags']}
                if not c['repair_required'] and new<=old:
                    row.update(output=rr['output'],final_check=c,selection='single_preservation_repair')
                else:row['selection']='first_pass_repair_not_accepted'
            else:row['selection']='first_pass_repair_failed'
        final.append(row)
    save(HERE/'final_outputs.json',final)

if __name__=='__main__':globals()[mode]()

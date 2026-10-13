"""Frozen latest-construction generation: same 70 inputs/settings, no analysis calls."""
import json,sys,shutil,time,hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path[:0]=[str(ROOT/'kg_v2'),str(ROOT/'current_kg/experiments')]
from sentence_retrieval import SentenceRetriever,morphology,compact,BUDGET
from run_translation import make_request
from run_seeded_kg import check_response
from model_client import connection
from preservation_check import generate_checked

def read(p):return json.loads(p.read_text())
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def prepare():
    assert not (HERE/'protocol.json').exists()
    previous=ROOT/'reports/kg_v2_pipeline_repair_20261012'
    analysis=read(previous/'analysis.json')
    cfg=read(ROOT/'reports/kg_v2_factorial_20261012/protocol.json')['config']
    jobs=[];retrieval=[];engine=SentenceRetriever()
    for item in analysis['items']:
        m=morphology(item['input']);r=engine.retrieve(item,m);packet=r['packets']['v2_graph']
        assert len(compact(packet))<=BUDGET
        jobs.append({'id':item['id'],'input':item['input'],'condition':'construction_after',
                     'request':make_request(cfg,item,m,packet)})
        retrieval.append(r)
    save(HERE/'analysis.json',analysis);save(HERE/'jobs.json',jobs);save(HERE/'retrieval.json',retrieval)
    shutil.copyfile(previous/'final_outputs.json',HERE/'baseline_outputs.json')
    deps=list((ROOT/'kg_v2').glob('*.py'))+[ROOT/'kg_v2'/n for n in ['facts.jsonl','graph.json','advisory_rules.json']]
    hashes={}
    for p in deps:
        dest=HERE/'snapshot'/p.name;dest.parent.mkdir(exist_ok=True);shutil.copyfile(p,dest);hashes[p.name]=sha(dest)
    old={j['id']:j for j in read(previous/'jobs.json')}
    save(HERE/'protocol.json',{'status':'prepared','config':cfg,'inputs':len(jobs),
       'design':'70 fresh generations with latest construction retrieval; prior 70 final outputs are frozen comparison',
       'analysis_policy':'reused exact prior Qwen analysis; current Kiwi and retrieval rerun',
       'quality_policy':'one first output; at most one rule-triggered preservation repair; no quality-selected reruns',
       'snapshot_hashes':hashes,'job_sha256':sha(HERE/'jobs.json'),
       'changed_requests':[j['id'] for j in jobs if j['request']!=old[j['id']]['request']],
       'baseline_path':str(previous.relative_to(ROOT)),'baseline_sha256':sha(previous/'final_outputs.json'),
       'analysis_calls':0,'limitations':['Development inputs, not independent human gold.',
         'Same requests may yield different outputs despite same seed.','Bundled retrieval changes, not factorial A/B/C/D.']})
    print('PREPARED',len(jobs),flush=True)

def generate():
    protocol=read(HERE/'protocol.json')
    assert sha(HERE/'jobs.json')==protocol['job_sha256']
    assert all(sha(HERE/'snapshot'/p)==h for p,h in protocol['snapshot_hashes'].items())
    assert all(sha(ROOT/'kg_v2'/p)==h for p,h in protocol['snapshot_hashes'].items())
    call,endpoint=connection(timeout=180)
    models=call('/models')
    assert protocol['config']['requested_model'] in [x['id'] for x in models['data']]
    protocol.update(status='generating',endpoint_sha256=endpoint);save(HERE/'protocol.json',protocol)
    def work(job):
        path=HERE/'raw'/(job['id']+'.json')
        if path.exists():
            prev=read(path);assert prev['request']==job['request']
            if prev['status']=='success':return prev
            raise RuntimeError('Prior failed attempt exists; inspect before rerunning.')
        requests=[]
        def recorded(route,request):
            start=time.monotonic();record={'request':request}
            requests.append(record)
            try:
                response=call(route,request);record.update(response=response,status='success')
                return response
            except Exception as e:
                record.update(status='failed',error_type=type(e).__name__)
                raise
            finally:record['elapsed_seconds']=time.monotonic()-start
        result={**job,'status':'failed'}
        try:result.update(generate_checked(recorded,job['request'],job['input'],check_response),status='success')
        except Exception as e:result['error_type']=type(e).__name__
        result['calls']=requests;save(path,result);return result
    rows=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        for i,f in enumerate(as_completed([pool.submit(work,j) for j in read(HERE/'jobs.json')]),1):
            row=f.result();rows.append(row);print(i,70,row['id'],row['status'],row.get('selection'),flush=True)
    rows.sort(key=lambda x:x['id'])
    save(HERE/'outputs.json',rows)
    keys=['id','input','condition','status','output','first_output','first_check','final_check',
          'repair_attempted','selection','repair_output','repair_check']
    save(HERE/'final_outputs.json',[{k:r[k] for k in keys if k in r} for r in rows])
    protocol.update(status='completed' if all(r['status']=='success' for r in rows) else 'completed_with_failures',
        first_outputs=sum(r['status']=='success' for r in rows),
        translation_calls=sum(len(r['calls']) for r in rows),
        repair_attempted=sum(r.get('repair_attempted',False) for r in rows),
        repair_accepted=sum(r.get('selection')=='single_preservation_repair' for r in rows))
    save(HERE/'protocol.json',protocol)
    print('FINISHED',protocol['status'],flush=True)

if __name__=='__main__':globals()[sys.argv[1]]()


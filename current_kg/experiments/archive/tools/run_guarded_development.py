"""Frozen replay of 30 model analyses plus eight fresh probes, before/after repair."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import argparse,datetime as dt,importlib.util,json,sys,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from copy import deepcopy
from pathlib import Path
from importlib.metadata import version
from run_auto_analysis_development import BASE,GRAMMAR,SEED,analyze_one
from run_seeded_kg import connection,read,save,sha,payload,check_response,error_fields
from run_manual_kg_development import retrieve
from source_analysis_guard import guard_analysis

PRIOR=BASE/'archive/runs/automatic_kg_20261002T042957751249Z'

def frozen():
    names=['archive/tools/run_guarded_development.py','source_analysis_guard.py','run_manual_kg_development.py','analysis_input.py',
           'run_auto_analysis_development.py','run_seeded_kg.py','requirements-analysis.txt']
    paths=[BASE/n for n in names]+[GRAMMAR/'grammar.graph.json',GRAMMAR/'analysis_contract.json',GRAMMAR/'query_review.py',BASE/'inputs/development_30.config.json',PRIOR/'automatic_analysis.json',PRIOR/'automatic_retrieval.json',PRIOR/'snapshot/experiments/run_manual_kg_development.py']
    return {str(p.relative_to(BASE.parent)):sha(p) for p in paths}

def old_retrieve(graph,a):
    path=PRIOR/'snapshot/experiments/run_manual_kg_development.py'
    spec=importlib.util.spec_from_file_location('frozen_old_manual_retriever',path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod.retrieve(graph,a)

def prepare(call,folder,config):
    # Authored only after guard implementation/tests; never provided to implementation tests.
    fresh=['약속 장소에 벌써 도착했어요.','봉투 좀 건네줄래?','저녁에는 제가 설거지할게요.',
           '길이 얼었으니까 조심해서 걸어요.','시간이 남으면 도서관에 들르자.',
           '민수가 "먼저 가세요"라고 말했어.','할아버지께서는 벌써 주무셨나요?',
           '서두르지 않아도 괜찮아요.']
    rows=[{'id':f'HOLD{i:03}','standard':s} for i,s in enumerate(fresh,1)]
    save(folder/'fresh_inputs.json',rows)
    records=[]
    # Kiwi is used only after model analysis, never offered as dialect answers.
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs=[pool.submit(analyze_one,call,config,row,folder) for row in rows]
        for job in as_completed(jobs):
            r=job.result();records.append(r);print(r['id']+' '+r['status'],flush=True)
    if any(r['status']!='validated' for r in records):
        raise ValueError('Fresh model analysis failed; raw attempts saved, no manual replacement')
    records.sort(key=lambda r:r['id'])
    old=read(PRIOR/'automatic_analysis.json')
    old['items'] += [r['normalized_analysis']['items'][0] for r in records]
    save(folder/'unguarded_analysis.json',old)
    guarded,audit=guard_analysis(old);save(folder/'guarded_analysis.json',guarded);save(folder/'guard_audit.json',audit)
    graph=read(GRAMMAR/'grammar.graph.json')
    for label,fn,a in [('prior_code',old_retrieve,old),('retrieval_only',retrieve,old),('full_repair',retrieve,guarded)]:
        save(folder/(label+'_retrieval.json'),{'items':fn(graph,a)})
    manifest=read(folder/'manifest.json');manifest.update(status='prepared',prepared_hashes={name:sha(folder/name) for name in ['unguarded_analysis.json','guarded_analysis.json','guard_audit.json','prior_code_retrieval.json','retrieval_only_retrieval.json','full_repair_retrieval.json','fresh_inputs.json']})
    save(folder/'manifest.json',manifest)
    print('READY='+str(folder),flush=True)

def translate(call,config,row,index,packets,folder):
    conditions=['prior_code','full_repair']
    if index%2:conditions.reverse()
    for condition in conditions:
        path=folder/'translations'/(row['id']+'_'+condition+'.json')
        if path.exists():raise ValueError('Refusing overwrite')
        req=payload(config,row['input'],SEED,packets[condition][row['id']]['prompt_packet'])
        result={'id':row['id'],'input':row['input'],'condition':condition,'attempts':[],'request':req,'status':'failed'}
        for attempt in range(2):
            audit={};start=time.monotonic()
            try:
                response=call('/chat/completions',req);audit['response']=response
                output=check_response(response,config['requested_model'])
                result.update(status='succeeded',output=output,response=response)
            except Exception as error:audit.update(error_fields(error))
            audit['elapsed_seconds']=round(time.monotonic()-start,3);result['attempts'].append(audit)
            save(path,result)
            if result['status']=='succeeded' or audit.get('error_type') not in {'TimeoutError','URLError'}:break
    return row['id']

def main():
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','generate']);p.add_argument('--folder',type=Path);p.add_argument('--execute',action='store_true');args=p.parse_args()
    if not args.execute:raise SystemExit('Use --execute')
    call,endpoint=connection();config=read(BASE/'inputs/development_30.config.json')
    if config['requested_model'] not in [m['id'] for m in call('/models')['data']]:raise ValueError('Model unavailable')
    if args.stage=='prepare':
        stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');folder=BASE/'archive/runs'/('guarded_kg_'+stamp)
        folder.mkdir(parents=True,exist_ok=False);(folder/'analysis_requests').mkdir();(folder/'translations').mkdir()
        manifest={'status':'preparing','dependencies':frozen(),'endpoint_sha256':endpoint,'config':config,'seed':SEED,
                  'packages':{n:version(n) for n in ['kiwipiepy','kiwipiepy_model','numpy','jsonschema']},
                  'design':'30 prior automatic analyses replayed unchanged; 8 new Qwen analyses. Retrieval-only intermediate isolates target-loop repair. Prior and full-repair translation pairs are generated in this run.',
                  'limitations':'Development probes, not independent naturalness evaluation. Full repair also replaces unverified preservation prose with a common preservation instruction.'}
        save(folder/'manifest.json',manifest)
        for name in manifest['dependencies']:
            dest=folder/'snapshot'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((BASE.parent/name).read_bytes())
        print('RUN_FOLDER='+str(folder),flush=True);prepare(call,folder,config)
    else:
        folder=args.folder.resolve();manifest=read(folder/'manifest.json')
        if manifest['dependencies']!=frozen():raise ValueError('Code/input changed since prepare')
        if manifest['endpoint_sha256']!=endpoint:raise ValueError('Endpoint changed')
        if manifest['status']!='prepared':raise ValueError('Already run or not prepared')
        if any(sha(folder/n)!=h for n,h in manifest['prepared_hashes'].items()):raise ValueError('Prepared artifact changed')
        if read(folder/'pre_generation_review.json')['status']!='reviewed_for_development_run':raise ValueError('Review first')
        packets={c:{r['id']:r for r in read(folder/(c+'_retrieval.json'))['items']} for c in ['prior_code','full_repair']}
        rows=read(folder/'guarded_analysis.json')['items']
        manifest['status']='generating';save(folder/'manifest.json',manifest)
        with ThreadPoolExecutor(max_workers=3) as pool:
            jobs=[pool.submit(translate,call,config,row,i,packets,folder) for i,row in enumerate(rows)]
            for job in as_completed(jobs):print(job.result()+' pair saved',flush=True)
        items=[{'id':row['id'],'input':row['input'],'conditions':{c:read(folder/'translations'/(row['id']+'_'+c+'.json')) for c in packets}} for row in rows]
        manifest['completed']=sum(o['status']=='succeeded' for r in items for o in r['conditions'].values())
        manifest['status']='succeeded' if manifest['completed']==len(rows)*2 else 'partial_failure';save(folder/'manifest.json',manifest)
        result={'manifest':manifest,'guard_audit':read(folder/'guard_audit.json'),'items':items}
        save(folder/'comparison.json',result);save(BASE/'archive/reports'/folder.name/'comparison.json',result)
        print(json.dumps({'status':manifest['status'],'completed':manifest['completed']}),flush=True)
if __name__=='__main__':main()

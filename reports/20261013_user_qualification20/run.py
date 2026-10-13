"""Frozen production pipeline on 20 user-supplied inputs; no production changes."""
import csv,json,sys,shutil,hashlib,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path[:0]=[str(ROOT/'kg_v2'),str(ROOT/'current_kg/experiments')]
from model_client import connection
from run_auto_analysis_development import analyze_one
from source_analysis_guard import guard_analysis
from sentence_retrieval import SentenceRetriever,morphology,semantic_guard,compact,BUDGET
from run_translation import make_request
from run_seeded_kg import check_response
from preservation_check import generate_checked

def read(p):return json.loads(p.read_text())
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify():
 p=read(HERE/'protocol.json')
 assert sha(HERE/'inputs.json')==p['inputs_sha256']
 for n,h in p['production_hashes'].items():
  assert sha(ROOT/n)==h,n
  assert sha(HERE/'snapshot'/n)==h,n
 return p

def prepare():
 assert not (HERE/'protocol.json').exists()
 with (HERE/'inputs.tsv').open() as f:inputs=[{'id':f"QUAL{int(r['number']):03}",'number':int(r['number']),'standard':r['standard']} for r in csv.DictReader(f,delimiter='\t')]
 assert len(inputs)==20 and [r['number'] for r in inputs]==list(range(1,21))
 save(HERE/'inputs.json',inputs)
 deps=list((ROOT/'kg_v2').glob('*.py'))+list((ROOT/'current_kg/experiments').glob('*.py'))+[ROOT/'kg_v2'/n for n in ['facts.jsonl','graph.json','advisory_rules.json']]+[ROOT/'current_kg/grammar/analysis_contract.json']
 hashes={}
 for f in deps:
  n=f.relative_to(ROOT);dest=HERE/'snapshot'/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,dest);hashes[str(n)]=sha(f)
 prior=read(ROOT/'reports/20261013_terminal_generation/protocol.json')
 assert all(sha(ROOT/'kg_v2'/n)==h for n,h in prior['snapshot_hashes'].items()),'Production differs from latest70'
 save(HERE/'protocol.json',{'status':'prepared','date':'2026-10-13','input_count':20,'input_origin':'User-supplied numbered standard Korean; verbatim, one independent input per number, 15/17 retain multiple sentences.',
 'design':'Single current production path; no A/B/C/D, no KG/retrieval/prompt changes.',
 'config':prior['config'],'seed':20260923,'analysis_policy':'Fresh production analyze_one for every input; at most two attempts with schema/source-binding feedback. No hand-written analysis or silent fallback.',
 'generation_policy':'Same generate_checked: first pass, preservation screening for every successful result, at most one triggered repair. All attempts retained.',
 'production_hashes':hashes,'inputs_sha256':sha(HERE/'inputs.json'),'runner_sha256':sha(Path(__file__)),
 'prior70_protocol':'reports/20261013_terminal_generation/protocol.json','prior70_same_production_snapshot':True,
 'target_style_prompt_added':False,'max_workers':2,
 'limitations':['Different source inputs from previous70, so no paired quality comparison or causal claim.','Fresh model analysis can be wrong even when schema-valid.','Automated screening is not dialect quality evaluation.','No conversation context across numbered inputs.']})
 print('PREPARED 20 user inputs; current production hashes matched latest70.',flush=True)

def execute():
 protocol=verify();assert sha(Path(__file__))==protocol['runner_sha256'];cfg=protocol['config'];inputs=read(HERE/'inputs.json')
 call,endpoint=connection(timeout=180)
 assert cfg['requested_model'] in [x['id'] for x in call('/models')['data']]
 protocol.update(status='analyzing',endpoint_sha256=endpoint);save(HERE/'protocol.json',protocol)
 def analyze(row):
  p=HERE/'analysis_requests'/(row['id']+'.json')
  if p.exists():
   old=read(p);assert old['input']==row['standard'];return old
  return analyze_one(call,cfg,row,HERE)
 analyses=[]
 with ThreadPoolExecutor(max_workers=2) as pool:
  for i,f in enumerate(as_completed([pool.submit(analyze,r) for r in inputs]),1):
   r=f.result();analyses.append(r);print('ANALYSIS',i,20,r['id'],r['status'],'attempts',len(r['attempts']),flush=True)
 analyses.sort(key=lambda r:r['id']);save(HERE/'analysis_results.json',analyses)
 protocol.update(status='retrieving',analysis_calls=sum(len(r['attempts']) for r in analyses),analysis_validated=sum(r['status']=='validated' for r in analyses));save(HERE/'protocol.json',protocol)
 engine=SentenceRetriever();items=[];retrieval=[];guards=[];jobs=[];failures=[]
 for r in analyses:
  if r['status']!='validated':failures.append({'id':r['id'],'input':r['input'],'status':'analysis_failed','output':None});continue
  try:
   a,g=guard_analysis(r['normalized_analysis']);item=a['items'][0]
   m=morphology(item['input']);item,sg=semantic_guard(item,m)
   x=engine.retrieve(item,m);packet=x['packets']['v2_graph'];assert len(compact(packet))<=BUDGET
   req=make_request(cfg,item,m,packet)
   assert req['messages'][0]['content']==cfg['system_prompt']
   items.append(item);retrieval.append(x);guards.append({'id':r['id'],'source_guard':g,'semantic_guard':sg})
   jobs.append({'id':r['id'],'input':r['input'],'condition':'current_terminal_pipeline','request':req})
   print('RETRIEVAL',r['id'],'references',len(packet['references']),flush=True)
  except Exception as e:
   failures.append({'id':r['id'],'input':r['input'],'status':'retrieval_failed','error_type':type(e).__name__,'error':str(e)[:1500],'output':None});print('RETRIEVAL FAILED',r['id'],type(e).__name__,flush=True)
 save(HERE/'analysis.json',{'items':items});save(HERE/'analysis_guards.json',guards);save(HERE/'retrieval.json',retrieval);save(HERE/'jobs.json',jobs)
 protocol.update(status='generating',prepared_jobs=len(jobs),jobs_sha256=sha(HERE/'jobs.json'));save(HERE/'protocol.json',protocol)
 def generate(job):
  p=HERE/'raw'/(job['id']+'.json')
  if p.exists():
   old=read(p);assert old['request']==job['request'];return old
  attempts=[]
  def recorded(route,request):
   rec={'request':request};attempts.append(rec);start=time.monotonic()
   try:response=call(route,request);rec.update(status='success',response=response);return response
   except Exception as e:rec.update(status='failed',error_type=type(e).__name__);raise
   finally:rec['elapsed_seconds']=time.monotonic()-start
  result={**job,'status':'failed'}
  try:result.update(generate_checked(recorded,job['request'],job['input'],check_response),status='success')
  except Exception as e:result.update(error_type=type(e).__name__)
  result['calls']=attempts;save(p,result);return result
 outputs=[]
 with ThreadPoolExecutor(max_workers=2) as pool:
  for i,f in enumerate(as_completed([pool.submit(generate,j) for j in jobs]),1):
   r=f.result();outputs.append(r);print('GENERATION',i,len(jobs),r['id'],r['status'],r.get('selection'),flush=True)
 outputs.sort(key=lambda r:r['id']);save(HERE/'outputs.json',outputs)
 keys=['id','input','condition','status','output','first_output','first_check','final_check','repair_attempted','selection','repair_output','repair_check','error_type']
 final=[{k:r[k] for k in keys if k in r} for r in outputs]+failures;final.sort(key=lambda r:r['id']);assert len(final)==20
 save(HERE/'final_outputs.json',final);verify()
 protocol.update(status='completed' if all(r['status']=='success' for r in final) else 'completed_with_failures',successful_translations=sum(r['status']=='success' for r in final),translation_calls=sum(len(r['calls']) for r in outputs),repair_attempted=sum(r.get('repair_attempted',False) for r in outputs),repair_accepted=sum(r.get('selection')=='single_preservation_repair' for r in outputs),production_unchanged_after=True)
 save(HERE/'protocol.json',protocol);print('FINISHED',protocol['status'],protocol['successful_translations'],'/20',flush=True)

if __name__=='__main__':globals()[sys.argv[1]]()

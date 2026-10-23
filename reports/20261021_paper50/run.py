"""Frozen, outcome-selected 50-case comparison. No production modifications."""
import csv,copy,datetime,hashlib,json,random,shutil,sys,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
sys.path[:0]=[str(ROOT/'kg_v2'),str(ROOT/'current_kg/experiments')]
from sentence_retrieval import SentenceRetriever,morphology,compact
from run_translation import make_request
from model_client import connection
from preservation_check import generate_checked
from run_seeded_kg import check_response
def read(p):return json.loads(Path(p).read_text())
def save(p,x):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
GROUPS={'DEV':'002 003 004 005 007 011 012 013 014 017 019 020 021 022 026 028 029 030',
 'LONG':'001 002 003 004','NEW':'001 004 005 006 007 008 009 012',
 'ADVCE':'001A 001B 002A 002B 003A 003B 005A 005B 006A 006B 008A 008B 010A 010B',
 'QUAL':'002 003 005 017 018 020'}
CAUTIONS={'DEV013':'낼은 전국 구어에서도 쓰이므로 그 자체를 방언 성공으로 세지 않음.',
 'DEV022':'묵제의 청유 해석은 독립 화자 검토 필요.', 'DEV029':'갠찮더라의 표기 적합성은 추가 검토 필요.',
 'LONG001':'만나자꼬 했는데 등 인용 표현의 변환은 부분적임.',
 'LONG002':'올 등 어휘 축약 적합성은 추가 검토 필요.',
 'LONG003':'맛있소/괜찮소 등 높임 계열 혼용이 남지만 요청과 의미는 대체로 보존됨.',
 'LONG004':'이빠이 어휘 선택은 목표 말투 적합성 검토 필요.',
 'NEW007':'천천히 와는 미변환; 묵다 어휘 대응만 반영된 부분 성공.',
 'NEW008':'아니야는 미변환; 니 대명사 대응만 반영된 부분 성공.',
 'NEW009':'옇다 어휘 대응만 반영; 반말 종결은 표준어 형태가 남음.',
 'ADVCE001A':'짐은 지역 고유 표지로 확정하지 않음.',
 'ADVCE002A':'계셔예의 자연스러움은 독립 화자 확인 필요.',
 'ADVCE003B':'저절로→절로는 방언 고유 변환으로 세지 않음.',
 'ADVCE006B':'원문 자체가 나는+존대 혼합이므로 그대로 보존하는 것을 감점하지 않음.',
 'QUAL017':'할라고는 나타났지만 하거든요는 남아 있는 부분 변환.'}
def prepare():
 assert not (P/'protocol.json').exists(),'Already frozen; resume execute instead.'
 ids=[g+n for g,nums in GROUPS.items() for n in nums.split()];assert len(ids)==len(set(ids))==50
 rows={};analyses={};provenance={}
 for folder in ['20261013_terminal_generation','20261013_user_qualification20']:
  base=ROOT/'reports'/folder
  for r in read(base/'final_outputs.json'):rows[r['id']]=r;provenance[r['id']]=str(base.relative_to(ROOT))
  for a in read(base/'analysis.json')['items']:analyses[a['id']]=a
 dataset=[];audit=[]
 for sid,r in rows.items():
  chosen=sid in ids;identical=r['input']==r.get('output')
  reason=('원문 완전 동일 출력 제외' if identical else '상대적으로 의미·높임·구조 보존과 방언 실현이 나은 사례 선정' if chosen else '높임/의미/구조 오류 또는 방언 실현 부족을 고려한 수동 제외')
  audit.append({'id':sid,'input':r['input'],'prior_output':r.get('output'),'selected':chosen,'source_identical':identical,'reason':reason,'source_folder':provenance[sid]})
 for no,sid in enumerate(ids,1):
  r=rows[sid];assert r['status']=='success' and r['output']!=r['input']
  dataset.append({'number':no,'id':sid,'standard':r['input'],'selection_basis':'Prior KG output manually judged relatively usable; outcome-selected, not held-out.',
   'selection_note':CAUTIONS.get(sid,'주요 의미·높임을 유지하면서 어휘 또는 종결의 방언 변환이 관찰됨. 정답 판정은 아님.'),
   'prior_output':r['output'],'source_folder':provenance[sid]})
 assert len({x['standard'] for x in dataset})==50
 save(P/'논문용_테스트_데이터셋.json',dataset);save(P/'selection_audit.json',audit)
 with (P/'논문용_테스트_데이터셋.tsv').open('w',newline='') as f:
  w=csv.writer(f,delimiter='\t',lineterminator='\n');w.writerow(['number','id','standard']);w.writerows((r['number'],r['id'],r['standard']) for r in dataset)
 (P/'논문용_테스트_데이터셋.txt').write_text('논문용 테스트 데이터셋 v1 — 기존 KG 결과를 보고 선정한50개 사례; 독립 평가셋 아님\n\n'+'\n'.join(f"{r['number']:02}. [{r['id']}] {r['standard']}" for r in dataset)+'\n')
 cfg=read(ROOT/'reports/20261013_terminal_generation/protocol.json')['config'];engine=SentenceRetriever();jobs=[];retrieval=[];items=[]
 for d in dataset:
  item=copy.deepcopy(analyses[d['id']]);assert item['input']==d['standard'];m=morphology(item['input']);r=engine.retrieve(item,m);retrieval.append(r);items.append(item)
  kg=make_request(cfg,item,m,r['packets']['v2_graph'])
  prefix,bodytext=kg['messages'][1]['content'].split('\n',1);body=json.loads(bodytext)
  abody=copy.deepcopy(body);abody['transformation_plan']=[];abody['graph_paths']=[];abody['preservation']['supporting_knowledge']=[]
  analysis=copy.deepcopy(kg);analysis['messages'][1]['content']=prefix+'\n'+compact(abody)
  plain=copy.deepcopy(kg);plain['messages'][1]['content']=item['input']
  for condition,request in [('P',plain),('A',analysis),('K',kg)]:jobs.append({'id':d['id'],'input':d['standard'],'condition':condition,'request':request})
  # A and K differ only in the three knowledge-bearing fields; all analysis and policies are shared.
  test=copy.deepcopy(body);test['transformation_plan']=[];test['graph_paths']=[];test['preservation']['supporting_knowledge']=[];assert test==abody
  assert not abody['transformation_plan'] and not abody['graph_paths'] and not abody['preservation']['supporting_knowledge']
 save(P/'analysis.json',{'items':items});save(P/'retrieval.json',retrieval);save(P/'jobs.json',jobs)
 deps=list((ROOT/'kg_v2').glob('*.py'))+[ROOT/'kg_v2'/n for n in ['facts.jsonl','graph.json','advisory_rules.json','source_registry.json','fact.schema.json']]+list((ROOT/'current_kg/experiments').glob('*.py'))+[ROOT/'current_kg/grammar/analysis_contract.json']
 hashes={}
 for f in deps:
  rel=f.relative_to(ROOT);dst=P/'snapshot'/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,dst);hashes[str(rel)]=sha(f)
 save(P/'protocol.json',{'status':'prepared','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'dataset_name':'논문용_테스트_데이터셋','dataset_version':1,
 'dataset_sha256':sha(P/'논문용_테스트_데이터셋.json'),'jobs_sha256':sha(P/'jobs.json'),'runner_sha256':sha(__file__),'production_hashes':hashes,
 'config':cfg,'seed':20260923,'input_count':50,'conditions':{'P':'Fixed system instruction + original input only.','A':'Same analyzed input, Kiwi, source preservation policy and instructions as K; transformation_plan, graph_paths and preservation.supporting_knowledge empty.','K':'Current KG v2 retrieved knowledge and transformation plans.'},
 'analysis_policy':'Reuse frozen prior Qwen analysis equally for A/K; fresh deterministic Kiwi and current retrieval. Zero fresh Qwen analysis calls.',
 'generation_policy':'150 fresh first-pass calls; same preservation screen for all; at most one rule-triggered repair per output. Main comparison uses first passes; repairs reported separately. No selection-based reruns.',
 'selection_policy':'Manually select relatively usable prior KG outputs after excluding unchanged output. Selection is outcome-dependent and favors K. Selection frozen before new generation; no replacement after results.',
 'max_workers':2,'order_seed':20261021,'independent_gold':False,'limitations':['Outcome-selected development sample, not an unbiased population estimate.','One generation per cell; stochastic server behavior possible despite fixed seed.','Reviewer is Codex, not an independent dialect-speaker panel.','Model ID does not independently verify model weights/checkpoint.','P versus K is whole-pipeline comparison; A versus K isolates the supplied knowledge package including composition plans, not graph topology alone.']})
 print('FROZEN 50 selected inputs, 150 jobs; no production edits.',flush=True)
def verify():
 p=read(P/'protocol.json');assert sha(P/'논문용_테스트_데이터셋.json')==p['dataset_sha256'];assert sha(P/'jobs.json')==p['jobs_sha256'];assert sha(__file__)==p['runner_sha256']
 for n,h in p['production_hashes'].items():assert sha(ROOT/n)==h and sha(P/'snapshot'/n)==h,n
 return p
def execute():
 p=verify();call,endpoint=connection(timeout=180);models=call('/models');assert p['config']['requested_model'] in [x['id'] for x in models['data']]
 save(P/'model_identity.json',models);p.update(status='running',endpoint_sha256=endpoint);save(P/'protocol.json',p)
 jobs=read(P/'jobs.json');random.Random(p['order_seed']).shuffle(jobs)
 def work(j):
  path=P/'raw'/(j['id']+'_'+j['condition']+'.json')
  if path.exists():
   old=read(path);assert old['request']==j['request'];return old
  attempts=[]
  def record(route,req):
   attempt={'request':req};attempts.append(attempt);start=time.monotonic()
   try:res=call(route,req);attempt.update(status='success',response=res);return res
   except Exception as e:attempt.update(status='failed',error_type=type(e).__name__);raise
   finally:attempt['elapsed_seconds']=time.monotonic()-start
  result={**j,'status':'failed'}
  try:result.update(generate_checked(record,j['request'],j['input'],check_response),status='success')
  except Exception as e:result.update(error_type=type(e).__name__)
  result['calls']=attempts;save(path,result);return result
 out=[]
 with ThreadPoolExecutor(max_workers=2) as pool:
  for i,f in enumerate(as_completed([pool.submit(work,j) for j in jobs]),1):
   r=f.result();out.append(r)
   if i%10==0 or r['status']!='success':print('GENERATED',i,150,r['id'],r['condition'],r['status'],flush=True)
 out.sort(key=lambda r:(r['id'],r['condition']));save(P/'outputs.json',out)
 keys=['id','input','condition','status','output','first_output','first_check','final_check','repair_attempted','selection','repair_output','repair_check','error_type']
 save(P/'final_outputs.json',[{k:r[k] for k in keys if k in r} for r in out]);verify()
 p.update(status='completed' if all(r['status']=='success' for r in out) else 'completed_with_failures',successful_outputs=sum(r['status']=='success' for r in out),generation_calls=sum(len(r['calls']) for r in out),repair_attempted=sum(r.get('repair_attempted',False) for r in out),repair_accepted=sum(r.get('selection')=='single_preservation_repair' for r in out),production_unchanged=True,completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());save(P/'protocol.json',p)
 print('FINISHED',p['status'],p['successful_outputs'],p['generation_calls'],flush=True)
if __name__=='__main__':globals()[sys.argv[1]]()

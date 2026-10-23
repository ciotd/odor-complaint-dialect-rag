"""One-factor preservation-text diagnostic on saved requests; no KG or analysis changes."""
import argparse,json,datetime as dt
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from run_seeded_kg import connection,check_response,error_fields,save,sha
BASE=Path(__file__).resolve().parent
IDS={'DEV002','DEV013','DEV024','DEV026','DEV027','HOLD005'}
COMMON='원문의 의미·부정·발화 의도·청자 높임·주체 높임·시제를 보존하세요. 형태 분석 미확인은 허용 조건이 아닙니다.'
def packet(req):
 return json.loads(req['messages'][1]['content'].split('<문법_KG_참고>\n')[1].split('\n</문법_KG_참고>')[0])
def variants(original):
 changed=deepcopy(original);user=changed['messages'][1]['content']
 prefix,tail=user.split('<문법_KG_참고>\n',1);raw,suffix=tail.split('\n</문법_KG_참고>',1)
 p=json.loads(raw);p['preserve']=COMMON
 changed['messages'][1]['content']=prefix+'<문법_KG_참고>\n'+json.dumps(p,ensure_ascii=False,separators=(',',':'))+'\n</문법_KG_참고>'+suffix
 a,b=packet(original),packet(changed)
 assert [k for k in a if a[k]!=b[k]]==['preserve']
 assert {k:v for k,v in original.items() if k!='messages'}=={k:v for k,v in changed.items() if k!='messages'}
 assert original['messages'][0]==changed['messages'][0]
 return {'original_note':original,'common_note':changed}
def worker(call,row,index):
 requests=variants(row['conditions']['prior_code']['request']);outputs=[]
 for repeat in range(2):
  order=list(requests)
  if (index+repeat)%2:order.reverse()
  for condition in order:
   req=requests[condition];out={'condition':condition,'repeat':repeat,'request':req}
   try:
    response=call('/chat/completions',req);out.update(response=response,output=check_response(response,req['model']),status='succeeded')
   except Exception as e:out.update(status='failed',**error_fields(e))
   outputs.append(out)
 return {'id':row['id'],'input':row['input'],'outputs':outputs}
def main():
 p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');args=p.parse_args()
 source=BASE/'reports/latest/comparison.json';data=json.loads(source.read_text());rows=[r for r in data['items'] if r['id'] in IDS]
 for row in rows:variants(row['conditions']['prior_code']['request'])
 if not args.execute:print('6 requests verified: only preserve differs, no network');return
 call,endpoint=connection();model=rows[0]['conditions']['prior_code']['request']['model']
 if model not in [m['id'] for m in call('/models')['data']]:raise ValueError('Model unavailable')
 stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');path=BASE/'reports/diagnostics'/('preservation_only_'+stamp+'.json')
 result={'source_sha256':sha(source),'runner_sha256':sha(Path(__file__)),'endpoint_sha256':endpoint,'design':'6 selected problem cases, only packet.preserve changes; two repeats with identical seed. Not a representative quality evaluation.','status':'running','items':[]}
 save(path,result)
 with ThreadPoolExecutor(max_workers=3) as pool:
  jobs=[pool.submit(worker,call,r,i) for i,r in enumerate(rows)]
  for job in as_completed(jobs):
   row=job.result();result['items'].append(row);save(path,result);print(row['id']+' saved',flush=True)
 result['items'].sort(key=lambda r:r['id']);result['completed']=sum(o['status']=='succeeded' for r in result['items'] for o in r['outputs']);result['status']='succeeded' if result['completed']==24 else 'partial_failure';save(path,result)
 print(str(path),flush=True)
if __name__=='__main__':main()

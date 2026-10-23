"""Retry only transport failures with no response; retain original attempts."""
import time
from run import P,read,save,verify,connection,generate_checked,check_response
verify();call,_=connection(timeout=180)
for job in read(P/'jobs.json'):
 path=P/'raw'/(job['id']+'_'+job['condition']+'.json');old=read(path)
 if old['status']=='success':continue
 assert old.get('error_type') in {'TimeoutError','ConnectionResetError','URLError'}
 assert all('response' not in c for c in old['calls'])
 save(P/'transport_failures'/path.name,old)
 calls=[]
 def record(route,req):
  a={'request':req};calls.append(a);t=time.monotonic()
  try:r=call(route,req);a.update(status='success',response=r);return r
  except Exception as e:a.update(status='failed',error_type=type(e).__name__);raise
  finally:a['elapsed_seconds']=time.monotonic()-t
 result={**job,'status':'failed','transport_retry':True}
 try:result.update(generate_checked(record,job['request'],job['input'],check_response),status='success')
 except Exception as e:result.update(error_type=type(e).__name__)
 result['calls']=old['calls']+calls;save(path,result)
 print('TRANSPORT RETRY',job['id'],job['condition'],result['status'],flush=True)

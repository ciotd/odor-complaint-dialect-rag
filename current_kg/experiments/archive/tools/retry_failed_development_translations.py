"""Retry transport failures only; preserve initial outputs and publish a new comparison."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import argparse
from copy import deepcopy
import datetime as dt
from pathlib import Path
import time
from run_seeded_kg import connection, check_response, error_fields, read, save, sha
from run_auto_analysis_development import assert_frozen, BASE


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder',type=Path);parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    if not args.execute:raise SystemExit('Use --execute')
    folder=args.folder.resolve();assert_frozen(folder)
    report=read(folder/'comparison.json');call,endpoint=connection()
    if endpoint!=report['manifest']['endpoint_sha256']:raise ValueError('Endpoint changed')
    retry_dir=folder/'translation_transport_retries';retry_dir.mkdir(exist_ok=False)
    (retry_dir/'runner.py').write_bytes(Path(__file__).read_bytes())
    for row in report['items']:
        for condition,original in list(row['conditions'].items()):
            if original['status']=='succeeded':continue
            if original.get('error_type') not in {'TimeoutError','URLError'}:continue
            result={'id':row['id'],'input':row['input'],'condition':condition,
                    'request':deepcopy(original['request']),'initial_failed_attempt':original}
            start=time.monotonic()
            try:
                response=call('/chat/completions',result['request']);result['response']=response
                result['output']=check_response(response,report['manifest']['model']);result['status']='succeeded'
            except Exception as error:result.update(status='failed',**error_fields(error))
            result['elapsed_seconds']=round(time.monotonic()-start,3)
            save(retry_dir/(row['id']+'_'+condition+'.json'),result)
            row['conditions'][condition]=result
            print(row['id']+' '+condition+' '+result['status'],flush=True)
    manifest=report['manifest'];manifest['initial_status']=manifest['status']
    manifest['transport_retry_runner_sha256']=sha(Path(__file__))
    manifest['transport_retries']=sum('initial_failed_attempt' in o for r in report['items'] for o in r['conditions'].values())
    manifest['completed']=sum(o['status']=='succeeded' for r in report['items'] for o in r['conditions'].values())
    manifest['status']='recovered_succeeded' if manifest['completed']==len(report['items'])*3 else 'partial_failure'
    manifest['retry_ended_at_utc']=dt.datetime.now(dt.timezone.utc).isoformat()
    save(folder/'comparison.recovered.json',report)
    durable=BASE/'archive/reports'/folder.name/'recovered.comparison.json'
    if durable.exists():raise ValueError('Refusing overwrite')
    save(durable,report)
    print(str(durable),flush=True)

if __name__=='__main__':main()

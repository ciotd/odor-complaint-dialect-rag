"""Explicit, logged extra structural repair after the initial two-attempt protocol.

No human analysis or KG candidate is supplied. Successful analyses are immutable.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import argparse
from copy import deepcopy
import json
from pathlib import Path
import time
from run_auto_analysis_development import assert_frozen, adapt
from run_seeded_kg import connection, check_response, error_fields, read, save, sha


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder',type=Path)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    if not args.execute: raise SystemExit('Use --execute')
    folder=args.folder.resolve();assert_frozen(folder)
    manifest=read(folder/'manifest.json');call,endpoint=connection()
    if endpoint!=manifest['endpoint_sha256']:raise ValueError('Endpoint changed')
    rows={r['id']:r for r in read(folder/'inputs.json')}
    manifest['additional_structural_repair']={'runner_sha256':sha(Path(__file__)),
        'reason':'Initial format and binding checks can fail sequentially; one extra validation-feedback attempt, no semantic/manual correction.',
        'max_total_attempts':3,'items':[]}
    (folder/'additional_repair_runner.py').write_bytes(Path(__file__).read_bytes())
    for path in sorted((folder/'analysis_requests').glob('*.json')):
        record=read(path)
        if record['status']=='validated' or len(record['attempts'])!=2:continue
        previous=record['attempts'][-1]
        if 'validation_error' not in previous:continue
        req=deepcopy(previous['request'])
        req['messages'] = req['messages'] + [
            {'role':'assistant','content':previous['response']['choices'][0]['message']['content']},
            {'role':'user','content':'원문과의 결속/JSON 규격 오류를 수정하고 JSON 전체를 다시 출력하세요. 원문: '+rows[record['id']]['standard']+'\n검증 오류: '+previous['validation_error']}]
        audit={'request':req,'protocol':'additional_structural_repair'};start=time.monotonic()
        try:
            response=call('/chat/completions',req);audit['response']=response
            raw=json.loads(check_response(response,manifest['model']))
            normalized=adapt(rows[record['id']],raw)
            record.update(status='validated',raw_analysis=raw,normalized_analysis=normalized)
        except Exception as e:
            audit.update(error_fields(e))
        audit['elapsed_seconds']=round(time.monotonic()-start,3)
        record['attempts'].append(audit);save(path,record)
        manifest['additional_structural_repair']['items'].append(record['id'])
        print(record['id']+' '+record['status'],flush=True)
    save(folder/'manifest.json',manifest)

if __name__=='__main__':main()

"""Publish readable copies and execution statistics; no inferred quality scores."""
import argparse
from collections import Counter
import json
from pathlib import Path
import shutil
from run_controlled_retrieval import CONDITIONS,compact
from run_seeded_kg import save,sha


def summarize(folder, out=None):
    out=out or Path(__file__).resolve().parent/'reports/controlled_development'
    out.mkdir(parents=True,exist_ok=True)
    if (out/'summary.json').exists() and json.loads((out/'summary.json').read_text())['run']!=str(folder):
        raise ValueError('Another run already occupies this report directory; choose --out')
    p=json.loads((folder/'protocol.json').read_text());rs=json.loads((folder/'retrieval.json').read_text())
    outputs=json.loads((folder/'outputs.json').read_text());by={(r['id'],r['condition']):r for r in outputs}
    identical_requests=[];different_inputs=[]
    for r in rs:
        c,d=[by[(r['id'],condition)] for condition in ['record_hybrid','graph_hybrid']]
        item={'id':r['id'],'same_output':c.get('output')==d.get('output')}
        (identical_requests if c['request']==d['request'] else different_inputs).append(item)
        pc,pd=[r['packets'][condition] for condition in ['record_hybrid','graph_hybrid']]
        assert pd['references'][:len(pc['references'])]==pc['references']
        for k in ['model','seed','temperature','top_p','top_k','max_tokens','chat_template_kwargs']:
            assert c['request'][k]==d['request'][k]
        assert c['request']['messages'][0]==d['request']['messages'][0]
        body_c,body_d=[json.loads(x['request']['messages'][1]['content'].split('\n',1)[1]) for x in [c,d]]
        assert body_c['analysis']==body_d['analysis'] and body_c['standard']==body_d['standard']
    costs={}
    for condition in CONDITIONS:
        group=[r for r in outputs if r['condition']==condition];usage=Counter();seconds=0
        for r in group:
            for a in r['attempts']:
                seconds+=a['seconds']
                for key,value in a.get('response',{}).get('usage',{}).items():
                    if isinstance(value,(int,float)):usage[key]+=value
        chars=[r['reference_chars'][condition] for r in rs]
        costs[condition]={'successful':sum(r['status']=='success' for r in group),
                          'usage':dict(usage),'summed_request_seconds':round(seconds,3),
                          'mean_attempt_seconds':round(seconds/sum(len(r['attempts']) for r in group),3),
                          'reference_chars_min':min(chars),'reference_chars_max':max(chars)}
    summary={'run':str(folder),'status':p['status'],'successful_outputs':p['completed'],
             'actual_generation_attempts':p['actual_generation_attempts'],'new_analysis_calls':p.get('analysis_calls_this_run',0),
             'conditions':CONDITIONS,'same_request_record_graph':identical_requests,
             'different_request_record_graph':different_inputs,
             'identical_request_different_output_ids':[r['id'] for r in identical_requests if not r['same_output']],
             'different_request_different_output_ids':[r['id'] for r in different_inputs if not r['same_output']],
             'query_truncations':p['query_truncations'],'dropped_cards':sum(len(r['dropped']) for r in rs),
             'costs':costs,'quality_scores':'not assigned; independent review pending',
             'protocol_sha256':sha(folder/'protocol.json'),'outputs_sha256':sha(folder/'outputs.json'),
             'retrieval_sha256':sha(folder/'retrieval.json'),
             'interpretation':'Diagnostic outputs do not establish a quality gain. No-expansion identical-request differences show seed is not an absolute reproducibility guarantee.'}
    save(out/'summary.json',summary)
    for name in ['comparison.txt','comparison.tsv','retrieval.tsv','blind_review.tsv','protocol.json','neo4j_paths.json']:
        if (folder/name).exists():shutil.copyfile(folder/name,out/name)
    # Run-specific observations are written only after reading actual outputs.
    print(json.dumps({k:summary[k] for k in ['successful_outputs','actual_generation_attempts','identical_request_different_output_ids','different_request_different_output_ids','dropped_cards']},ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder',type=Path);p.add_argument('--out',type=Path)
    args=p.parse_args();summarize(args.folder,args.out)

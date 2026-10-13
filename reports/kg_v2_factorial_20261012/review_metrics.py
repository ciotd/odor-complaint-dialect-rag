"""Descriptive audit, deliberately not a dialect translation accuracy metric."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import statistics

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]


def read(p):return json.loads(p.read_text())


def main():
    rows=read(BASE/'retrieval.json');jobs=read(BASE/'jobs.json');outputs=read(BASE/'outputs.json')
    by={(r['id'],r['condition']):r for r in outputs}
    stats={'not_accuracy':True,'retrieval':{},'generation':{}}
    for mode in ['baseline','hybrid']:
        refs=[f for r in rows for f in r[mode]['packets']['v2_graph']['references']]
        stats['retrieval'][mode]={'bound_references':len(refs),
            'without_structured_conditions':sum(not f['conditions'] for f in refs),
            'with_textual_constraints':sum(bool(f['constraints']) for f in refs),
            'zero_reference_ids':[r['id'] for r in rows if not r[mode]['packets']['v2_graph']['references']]}
    exact_groups=defaultdict(list)
    for j in jobs:
        key=hashlib.sha256(json.dumps(j['request'],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        exact_groups[key].append((j['id'],j['condition']))
    repeated=[]
    for key,members in exact_groups.items():
        if len(members)<2:continue
        vals=[by[m].get('output') for m in members]
        repeated.append({'request_sha256':key,'members':members,'distinct_outputs':len(set(vals))})
    stats['generation']['identical_request_groups']=repeated
    old={(r['id'],r['condition']):r for r in read(ROOT/'kg_v2/reports/translation_20261012_ending_repair/outputs.json')}
    drift=[]
    for r in outputs:
        if r['condition']=='A' and (r['id'],'v2_graph') in old and r.get('output')!=old[r['id'],'v2_graph'].get('output'):
            drift.append({'id':r['id'],'previous':old[r['id'],'v2_graph'].get('output'),'now':r.get('output')})
    stats['generation']['A_changed_from_previous_identical_request']=drift
    lengths={c:[len(j['request']['messages'][1]['content']) for j in jobs if j['condition']==c] for c in 'ABCD'}
    stats['generation']['user_character_lengths']={c:{'median':statistics.median(v),'max':max(v),'total':sum(v)} for c,v in lengths.items()}
    stats['generation']['length_reduction_total_fraction']={a+'_'+b:1-sum(lengths[b])/sum(lengths[a]) for a,b in [('A','C'),('B','D')]}
    for group,prefixes in [('development',('DEV','LONG')),('new_challenge',('NEW',))]:
        subset=[r for r in rows if r['id'].startswith(prefixes)]
        changed=[]
        for r in subset:
            a=[(f['id'],f['input_binding']['span']) for f in r['baseline']['packets']['v2_graph']['references']]
            b=[(f['id'],f['input_binding']['span']) for f in r['hybrid']['packets']['v2_graph']['references']]
            if a!=b:changed.append(r['id'])
        stats['retrieval'][group]={'sentences':len(subset),'selection_or_order_changed_ids':changed}
    analysis_attempts=[read(p) for p in sorted((BASE/'analysis_requests').glob('*.json'))]
    stats['new_analysis']={'validated':sum(r['status']=='validated' for r in analysis_attempts),
                           'total_requests':sum(len(r['attempts']) for r in analysis_attempts),
                           'repairs':{r['id']:len(r['attempts']) for r in analysis_attempts if len(r['attempts'])>1}}
    (BASE/'review_metrics.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in stats.items() if k!='generation'},ensure_ascii=False,indent=2))
    print('A repeat drift:',len(drift),'/',len(old)//4)
    print('Identical request groups:',len(repeated),'with differing outputs:',sum(r['distinct_outputs']>1 for r in repeated))


if __name__=='__main__':main()

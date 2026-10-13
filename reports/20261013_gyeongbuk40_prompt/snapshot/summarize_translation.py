"""Descriptive experiment metrics; these are not dialect accuracy scores."""
import hashlib
import json
from pathlib import Path
from collections import defaultdict
from run_translation import CONDITIONS, DEFAULT


def digest(obj):
    return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True).encode()).hexdigest()


def summarize(folder=DEFAULT):
    report=Path(__file__).resolve().parent/'reports/translation_20261012'
    rows=json.loads((folder/'outputs.json').read_text());retrieval=json.loads((folder/'retrieval.json').read_text())
    by={(r['id'],r['condition']):r for r in rows};metrics={}
    for subset,ids in [('all',sorted({r['id'] for r in rows})),
                       ('short',sorted({r['id'] for r in rows if r['id'].startswith('DEV')})),
                       ('long',sorted({r['id'] for r in rows if r['id'].startswith('LONG')}))]:
        metrics[subset]={'inputs':len(ids),'conditions':{}}
        for c in CONDITIONS:
            selected=[by[sid,c] for sid in ids]
            metrics[subset]['conditions'][c]={
                'successful':sum(r['status']=='success' for r in selected),
                'exactly_unchanged':sum(r.get('output','').strip()==r['input'].strip() for r in selected)}
    same_request=[];same_output=[];changed_with_same=[]
    for sid in sorted({r['id'] for r in rows}):
        a,b=by[sid,'v2_direct'],by[sid,'v2_graph']
        identical=digest(a['request'])==digest(b['request'])
        if identical:same_request.append(sid)
        if a.get('output')==b.get('output'):same_output.append(sid)
        elif identical:changed_with_same.append(sid)
    selections={}
    for c in CONDITIONS:
        sets=[tuple(sorted(f['id'] for f in r['packets'][c]['references'])) for r in retrieval]
        selections[c]={'distinct_statement_sets':len(set(sets)),'empty_packets':sum(not s for s in sets),
                       'reference_counts':{r['id']:len(r['packets'][c]['references']) for r in retrieval}}
    result={'metrics':metrics,'selection':selections,
            'graph_paths':{r['id']:len(r['packets']['v2_graph']['graph_paths']) for r in retrieval if r['packets']['v2_graph']['graph_paths']},
            'v2_direct_graph_identical_request_ids':same_request,
            'v2_direct_graph_identical_output_ids':same_output,
            'different_outputs_despite_identical_request_ids':changed_with_same,
            'interpretation_limits':['Exact preservation is not automatically a translation error.',
               'Different outputs for identical requests demonstrate that the seed did not guarantee reproducibility in this run.',
               'More distinct cards, changes or graph edges do not establish better grammar or naturalness.']}
    (report/'metrics.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    hashes=[{'id':r['id'],'condition':r['condition'],'request_sha256':digest(r['request']),
             'output_sha256':digest(r.get('output'))} for r in rows]
    (report/'request_output_hashes.json').write_text(json.dumps(hashes,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'metrics':metrics,'graph_path_sentences':len(result['graph_paths']),
                     'v2_same_request_count':len(same_request),'v2_same_output_count':len(same_output),
                     'same_request_different_outputs':changed_with_same},ensure_ascii=False,indent=2))


if __name__=='__main__':summarize()

"""Measure actual serialized references from the frozen 50-input factorial run.

No synthetic candidates or estimated token counts. Characters = Python len(str).
"""
import csv
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import statistics

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'kg_v2_factorial_20261012'


def read(name):return json.loads((SOURCE/name).read_text())
def compact(value):return json.dumps(value,ensure_ascii=False,separators=(',',':'))
def mean(values):return statistics.mean(values) if values else None


def main():
    jobs=read('jobs.json');retrieval={r['id']:r for r in read('retrieval.json')}
    analysis={i['id']:i for i in read('analysis.json')['items']}
    segments=[];inputs=[]
    for job in jobs:
        sid=job['id'];condition=job['condition'];request=job['request']
        raw=request['messages'][1]['content'].split('\n',1)[1];body=json.loads(raw)
        assert raw==compact(body), 'Exact serialization differs'
        groups=defaultdict(list);objects={}
        if condition in 'AB':
            for ref in body['references']:
                groups[tuple(ref['input_binding']['span'])].append(ref)
            packet={k:body[k] for k in ['references','graph_paths']}
            base=retrieval[sid]['baseline' if condition=='A' else 'hybrid']['packets']['v2_graph']
            assert packet==base
        else:
            for group in body['transformation_plan']:
                span=tuple(group['span']);assert span not in groups
                groups[span]=group['candidates'];objects[span]=group
            packet={k:body[k] for k in ['transformation_plan','graph_paths','plan_policy']}
        local=[]
        for span,refs in groups.items():
            assert 1<=len(refs)<=6
            row={'id':sid,'condition':condition,'start':span[0],'end':span[1],
                 'source_segment':job['input'][slice(*span)],'candidate_count':len(refs),
                 'candidate_array_characters':len(compact(refs)),
                 'candidate_object_characters_sum':sum(len(compact(r)) for r in refs),
                 'largest_candidate_characters':max(len(compact(r)) for r in refs),
                 'segment_representation_characters':len(compact(objects[span])) if span in objects else len(compact(refs)),
                 'candidate_ids':[r['id'] for r in refs]}
            local.append(row);segments.append(row)
        inputs.append({'id':sid,'condition':condition,'source':job['input'],
                       'analysis_clause_count':len(analysis[sid]['clauses']),
                       'delivered_segment_count':len(local),'candidate_count':sum(r['candidate_count'] for r in local),
                       'mean_candidates_per_nonempty_segment':mean([r['candidate_count'] for r in local]),
                       'largest_segment_candidate_array_characters':max([r['candidate_array_characters'] for r in local],default=0),
                       'mean_segment_candidate_array_characters':mean([r['candidate_array_characters'] for r in local]),
                       'knowledge_packet_characters':len(compact(packet)),
                       'user_message_characters':len(request['messages'][1]['content']),
                       'system_message_characters':len(request['messages'][0]['content'])})
    summary={}
    for cohort,prefixes in [('all50',('DEV','LONG','NEW')),('previous38',('DEV','LONG')),('new12',('NEW',))]:
        summary[cohort]={}
        for condition in 'ABCD':
            ins=[r for r in inputs if r['condition']==condition and r['id'].startswith(prefixes)]
            segs=[r for r in segments if r['condition']==condition and r['id'].startswith(prefixes)]
            lengths=[r['candidate_array_characters'] for r in segs]
            summary[cohort][condition]={
                'input_count':len(ins),'analysis_clause_count_total':sum(r['analysis_clause_count'] for r in ins),
                'analysis_clauses_per_input_mean':mean([r['analysis_clause_count'] for r in ins]),
                'delivered_segment_count_total':len(segs),
                'delivered_segments_per_input_mean_including_zero':len(segs)/len(ins),
                'zero_segment_input_ids':[r['id'] for r in ins if not r['delivered_segment_count']],
                'candidate_count_total':sum(r['candidate_count'] for r in segs),
                'candidates_per_delivered_segment_pooled_mean':mean([r['candidate_count'] for r in segs]),
                'candidates_per_segment_mean_of_nonempty_input_means':mean([r['mean_candidates_per_nonempty_segment'] for r in ins if r['delivered_segment_count']]),
                'candidate_count_distribution':dict(sorted(Counter(r['candidate_count'] for r in segs).items())),
                'candidate_array_characters_per_segment_mean':mean(lengths),
                'candidate_array_characters_per_segment_median':statistics.median(lengths),
                'candidate_array_characters_largest_segment':max(lengths),
                'per_input_largest_segment_characters_mean_including_zero':mean([r['largest_segment_candidate_array_characters'] for r in ins]),
                'per_segment_largest_single_candidate_characters_mean':mean([r['largest_candidate_characters'] for r in segs]),
                'segment_representation_characters_mean':mean([r['segment_representation_characters'] for r in segs]),
                'packet_characters_mean':mean([r['knowledge_packet_characters'] for r in ins]),
                'packet_characters_max':max(r['knowledge_packet_characters'] for r in ins),
                'user_message_characters_mean':mean([r['user_message_characters'] for r in ins]),
                'user_message_characters_max':max(r['user_message_characters'] for r in ins),
                'largest_segment_examples':sorted(segs,key=lambda r:-r['candidate_array_characters'])[:3]}
    omissions={}
    for mode in ['baseline','hybrid']:
        all_omissions=[(sid,x) for sid,r in retrieval.items() for x in r[mode]['selection_audit']['v2_graph']['omitted']]
        omissions[mode]={reason:{'records':sum(x['reason']==reason for _,x in all_omissions),
                     'affected_input_ids':sorted({sid for sid,x in all_omissions if x['reason']==reason})}
                     for reason in sorted({x['reason'] for _,x in all_omissions})}
    result={'definitions':{
        'input':'One saved input ID; LONG and some NEW inputs contain multiple orthographic sentences. 50 inputs, not 200 independent sentences.',
        'segment':'Unique input_binding.span with >=1 delivered candidate within one condition. Overlapping/nested lexical and clause spans counted separately. Not a partition or a count of all potential search units.',
        'candidates':'Delivered records; same fact on different spans counted separately.',
        'characters':'Python len of exact compact JSON serialization with ensure_ascii=False; Unicode characters, not bytes/tokens.',
        'candidate_array':'All candidate objects for one span in a JSON array; includes metadata and quotes actually sent, excluding shared graph paths, full analysis and prompt. For C/D excludes common per-segment preserve metadata, which is reported separately.',
        'average_maximum':'Mean across all input IDs of each input largest candidate-array length, zero for inputs without references. Also report global max and mean largest single candidate separately.',
        'budget':'24,000 characters is the whole baseline/hybrid reference packet, NOT per segment and NOT the whole user prompt. 2,000 characters are reserved for graph paths during reference selection. Plan serialization has no separate 24k cap.'},
        'source_hashes':{n:hashlib.sha256((SOURCE/n).read_bytes()).hexdigest() for n in ['jobs.json','retrieval.json','analysis.json']},
        'summary':summary,'omission_records_not_unique_rules':omissions}
    for name,value in [('retrieval_statistics.json',result),('segment_lengths.json',segments),('input_lengths.json',inputs)]:
        (HERE/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    for name,rows in [('segment_lengths.tsv',segments),('input_lengths.tsv',inputs)]:
        with (HERE/name).open('w') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter='\t',lineterminator='\n');w.writeheader();w.writerows(rows)
    for cohort,by in summary.items():
        print(cohort)
        for c,r in by.items():
            print(c,'segments',r['delivered_segment_count_total'],'per input',round(r['delivered_segments_per_input_mean_including_zero'],3),
                  'refs/segment',round(r['candidates_per_delivered_segment_pooled_mean'],3),
                  'chars/segment',round(r['candidate_array_characters_per_segment_mean'],2),
                  'mean(input maxima)',round(r['per_input_largest_segment_characters_mean_including_zero'],2),
                  'max',r['candidate_array_characters_largest_segment'])
    print('omissions',json.dumps(omissions,ensure_ascii=False))


if __name__=='__main__':main()

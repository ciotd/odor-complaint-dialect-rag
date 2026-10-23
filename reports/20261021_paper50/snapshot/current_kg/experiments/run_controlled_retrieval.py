"""Fixed-analysis comparison using shared, source-bound KG candidate selection.

prepare performs retrieval only. Generation consumes frozen requests separately.
Historical runs retain their original runner and protocol snapshots.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
import random
import time

from run_seeded_kg import connection,check_response,error_fields,save,sha

BASE=Path(__file__).resolve().parent
GRAMMAR=BASE.parent/'grammar'
ANALYSIS=BASE/'archive/runs/guarded_kg_20261002T063104410680Z/guarded_analysis.json'
CONDITIONS=['prompt_only','source_hybrid','record_hybrid','graph_hybrid']
RELATIONS=['has_applicability_constraint','has_inflection_description','has_construction_component',
           'shares_quotative_construction','contracts_to','combines_with','excludes_combination',
           'variant_of','same_usage_candidate','contrasts_in_function']
BUDGET=24000
SEED=20260923


def compact(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))


def analysis_card(item):
    return [{'text':c['text'],'span':c['span'],'role':c['role'],
             'features':{k:v for k,v in c['features'].items() if v is not None},
             'observed_politeness':c.get('observed_politeness'),
             'observed_subject_honorific':c.get('observed_subject_honorific'),
             'tense_or_modality':c.get('tense_or_modality'),
             'preserved_candidate_features':c.get('preserved_candidate_features',{})} for c in item['clauses']]


def record_card(record):
    k=record['knowledge']
    return {'id':record['id'],'source_id':record['source_id'],
            **{key:k[key] for key in ['label','forms','scope','details','gaps','evidence']},
            'source_examples':k.get('source_examples',[]),
            'relations':[{key:r[key] for key in ['subject','predicate','object','conditions','application','evidence_keys','assertion_mode'] if key in r}
                         for r in k['relations']],
            'status':'conditional_reference_not_approved_for_generation'}


def expansion(seeds,graph,records):
    """One cross-record edge in either direction; never shared-concept clique traversal."""
    found=[]
    for e in graph['edges']:
        if e['type'] not in RELATIONS or e.get('properties',{}).get('status')=='held_scope_tension':continue
        a,b=e['source'].split(':')[0],e['target'].split(':')[0]
        if a==b or a not in records or b not in records:continue
        for start,end,direction in [(a,b,'outgoing'),(b,a,'incoming')]:
            if start in seeds and end not in seeds:
                found.append({'record_id':end,'seed_record_id':start,'direction':direction,'edge':e})
    found.sort(key=lambda p:(RELATIONS.index(p['edge']['type']),seeds.index(p['seed_record_id']),p['record_id'],p['edge']['id']))
    chosen=[];seen=set()
    for p in found:
        if p['record_id'] in seen:continue
        chosen.append(p);seen.add(p['record_id'])
        if len(chosen)==3:break
    return chosen


def add_card(packet,card,path=None):
    candidate=json.loads(compact(packet));candidate['references'].append(card)
    if path is not None:candidate['graph_paths'].append(path)
    if len(compact(candidate))>BUDGET:return False
    packet.update(candidate);return True


def make_request(config,item,packet):
    # Identical envelope, analysis, and instructions in every condition. Only references/paths vary.
    body={'standard':item['input'],'analysis':analysis_card(item),**packet}
    user=('다음 입력의 standard를 변환하세요. analysis는 오류가 있을 수 있는 관찰값이며 원문이 우선합니다. '
          'references와 graph_paths는 조건부 참고 자료입니다. 관련성이 없거나 조건이 맞지 않으면 사용하지 마세요. '
          '연결된 기록끼리 조건을 상속하거나 예문을 무조건 치환하지 마세요. '
          '부정·시제·인용·전언 의미와 높임을 유지하고, 바꿀 근거가 없는 구성은 유지하세요.\n'+compact(body))
    return {'model':config['requested_model'],**config['generation'],'seed':SEED,
            'messages':[{'role':'system','content':config['system_prompt']},{'role':'user','content':user}]}


def prepare(folder,query_mode='raw_sentence',input_path=None,analysis_path=None):
    from embedding_retrieval import EmbeddingIndex,query_text
    from integrated_retrieval import IntegratedRetriever, MAX_HOPS, MAX_PER_VIEW
    from analysis_input import normalize_analysis
    input_path=input_path or BASE/'inputs/development_30.jsonl'
    analysis_path=analysis_path or ANALYSIS
    config=json.loads((BASE/'inputs/development_30.config.json').read_text())
    config['dataset']=input_path.name
    rows=[json.loads(x) for x in input_path.read_text().splitlines() if x.strip()]
    analysis=normalize_analysis(json.loads(analysis_path.read_text()))
    frozen={x['id']:x for x in analysis['items']}
    if not rows or len({r['id'] for r in rows})!=len(rows):
        raise ValueError('Inputs must be nonempty with unique IDs')
    if len(frozen)!=len(analysis['items']) or any(r['id'] not in frozen for r in rows):
        raise ValueError('Analysis must have unique IDs and cover every input')
    items=[frozen[r['id']] for r in rows]
    if any(i['input']!=r['standard'] for i,r in zip(items,rows)):
        raise ValueError('Analysis text differs from input')
    folder.mkdir(parents=True,exist_ok=False)
    (folder/'inputs.jsonl').write_bytes(input_path.read_bytes())
    graph=json.loads((GRAMMAR/'grammar.graph.json').read_text())
    dependencies={str(p.relative_to(BASE.parent)):sha(p) for p in [
        BASE/'integrated_retrieval.py',BASE/'source_bindings.py',BASE/'analysis_input.py',
        BASE/'embedding_retrieval.py',BASE/'source_retrieval.py',BASE/'source_analysis_guard.py',
        GRAMMAR/'query_review.py',GRAMMAR/'analysis_contract.json',GRAMMAR/'source_evidence/summary.json']}
    # Write the method before retrieving or inspecting any new output.
    protocol={'status':'preparing','created_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
              'conditions':CONDITIONS,'query_mode':query_mode,'dependencies':dependencies,
              'analysis':'cached automatic guarded analysis; same across all conditions',
              'analysis_calls_this_run':0,'translation_calls_planned':len(items)*len(CONDITIONS),'repetitions':1,'seed':SEED,
              'method':'integrated_source_bound_assertion_retrieval_v1',
              'max_per_binding':MAX_PER_VIEW,'top_k_search':6,'graph_hops':MAX_HOPS,
              'graph_directions':['outgoing'],'graph_relations_priority':RELATIONS,
              'budget_reference_unicode_characters':BUDGET,'rrf_k':60,'rrf_pool':50,
              'condition_filter':'Function/form/hybrid discovery; independently bound application slots, conditions, politeness and exclusions. Mismatch/unknown audit only.',
              'exclusion':'held_scope_tension edges excluded; common concept/source hubs not traversed',
              'limitations':['All sentences are development data.','No independent naturalness evaluation.',
                            'Reference amount differs; graph contrast tests expansion as a system component, not content-matched topology alone.',
                            'prompt_only retains same cached analysis/instructions; this is not raw-sentence-only baseline.',
                            'Cached analysis is development input, not gold; morphological binding is a hypothesis.',
                            'Source condition is raw excerpt RAG; KG conditions deliver only matched assertions.',
                            'No generation quality conclusion from execution success.'],
              'config':config,'network_timeout_seconds':60,'input_sha256':sha(input_path),
              'analysis_sha256':sha(analysis_path),'graph_sha256':sha(GRAMMAR/'grammar.graph.json'),
              'records_sha256':sha(GRAMMAR/'records.jsonl'),'runner_sha256':sha(Path(__file__)),
              'embedding_runner_sha256':sha(BASE/'embedding_retrieval.py')}
    save(folder/'protocol.json',protocol)
    save(folder/'analysis.json',{'items':items})
    save(folder/'snapshot.graph.json',graph)
    for filename in ['run_controlled_retrieval.py','embedding_retrieval.py','source_retrieval.py',
                     'integrated_retrieval.py','source_bindings.py','analysis_input.py','source_analysis_guard.py']:
        (folder/filename).write_bytes((BASE/filename).read_bytes())
    (folder/'snapshot.records.jsonl').write_bytes((GRAMMAR/'records.jsonl').read_bytes())
    idx=EmbeddingIndex();engine=IntegratedRetriever(graph,idx);results=[];jobs=[]
    for i,item in enumerate(items):
        query=item['input'] if query_mode=='raw_sentence' else query_text(item)
        rank=idx.search_all(query);sources=idx.search_all(query,'source_unit')
        p0={'references':[],'graph_paths':[]};ps={'references':[],'graph_paths':[]}
        dropped=[]
        for hit in sources['hybrid'][:3]:
            unit=idx.source.units[hit['id']]
            card={'id':hit['id'],'text':hit['text'],'span':hit['span'],
                  'source_unit':{k:v for k,v in unit.items() if k!='text'}}
            if not add_card(ps,card):dropped.append({'condition':'source_hybrid','id':hit['id'],'reason':'budget'})
        integrated=engine.retrieve_item(item)
        pr=integrated['packets']['record_hybrid'];pg=integrated['packets']['graph_hybrid']
        seeds=list(dict.fromkeys(r['record_id'] for r in pr['references']))
        paths=pg['graph_paths']
        dropped.extend({'condition':c,**d} for c,ds in integrated['omitted'].items() for d in ds)
        packets=dict(zip(CONDITIONS,[p0,ps,pr,pg]))
        requests={c:make_request(config,item,p) for c,p in packets.items()}
        result={'id':item['id'],'input':item['input'],'query':query,'query_audit':idx.query_audit[query],
                'record_ranking':rank,'source_ranking':sources,'seed_record_ids':seeds,'expansion_candidates':paths,
                'packets':packets,'dropped':dropped,'integrated_retrieval':integrated,
                'reference_chars':{c:len(compact(p)) for c,p in packets.items()}}
        results.append(result)
        # Rotation prevents all conditions being confounded with one chronological block.
        order=CONDITIONS[i%4:]+CONDITIONS[:i%4]
        jobs.extend({'id':item['id'],'condition':c,'input':item['input'],'request':requests[c]} for c in order)
        print(item['id'],'selected='+','.join(r['id'] for r in pg['references']),
              'bindings='+str(len(integrated['bindings'])),flush=True)
    save(folder/'retrieval.json',results);save(folder/'jobs.json',jobs)
    if any(sha(BASE.parent/name)!=value for name,value in dependencies.items()):
        protocol.update(status='superseded_code_changed_during_preparation')
        save(folder/'protocol.json',protocol)
        raise ValueError('Code/index changed during retrieval; preserve this run and start a new one')
    protocol.update(status='prepared',embedding_model=idx.model_selection,embedding_index_sha256=idx.fingerprint,
                    chunks=len(idx.chunks),query_truncations=sum(r['query_audit']['truncated'] for r in results),
                    graph_expansion_active=sum(bool(r['packets']['graph_hybrid']['graph_paths']) for r in results),
                    prepared_artifact_sha256={name:sha(folder/name) for name in ['jobs.json','retrieval.json','analysis.json']},
                    pre_generation_review={'status':'pending'})
    save(folder/'protocol.json',protocol)
    with (folder/'retrieval.tsv').open('w') as f:
        w=csv.writer(f,delimiter='\t');w.writerow(['id','standard','lexical_top6','dense_top6','hybrid_top6','graph_neighbors','dropped'])
        for r in results:w.writerow([r['id'],r['input'],*[','.join(h['id'] for h in r['record_ranking'][m]) for m in ['lexical','dense','hybrid']],','.join(p['assertion_id'] for p in r['packets']['graph_hybrid']['graph_paths']),compact(r['dropped'])])


def verify_generation_inputs(folder, protocol):
    if protocol.get('method')=='integrated_source_bound_assertion_retrieval_v1':
        review=protocol.get('pre_generation_review',{})
        if review.get('status') not in {'passed_retrieval_checks','reviewed_with_documented_gaps'}:
            raise ValueError('Complete and record pre-generation retrieval checks first')
        if review['status']=='reviewed_with_documented_gaps' and (
                review.get('packet_integrity_passed') is not True or not review.get('known_gaps')):
            raise ValueError('Record verified packet integrity and the known gaps explicitly')
        if any(sha(folder/name)!=value for name,value in protocol['prepared_artifact_sha256'].items()):
            raise ValueError('Frozen generation inputs changed')


def generate(folder):
    protocol=json.loads((folder/'protocol.json').read_text());jobs=json.loads((folder/'jobs.json').read_text())
    verify_generation_inputs(folder,protocol)
    call,endpoint=connection();models=[m['id'] for m in call('/models')['data']]
    if protocol['config']['requested_model'] not in models:raise RuntimeError('Model unavailable')
    raw=folder/'raw';raw.mkdir(exist_ok=True)
    protocol.update(status='generating',endpoint_sha256=endpoint,models=models,workers=2)
    save(folder/'protocol.json',protocol)
    def work(job):
        path=raw/(job['id']+'_'+job['condition']+'.json')
        if path.exists():
            old=json.loads(path.read_text())
            if old['request']!=job['request']:raise ValueError('Saved request differs')
            if old.get('status')=='success':return old
        result={**job,'attempts':[],'status':'failed'}
        for attempt in range(2):
            started=time.monotonic()
            try:
                response=call('/chat/completions',job['request'])
                result['attempts'].append({'seconds':time.monotonic()-started,'response':response})
                result['output']=check_response(response,job['request']['model']);result['status']='success';break
            except Exception as error:
                result['attempts'].append({'seconds':time.monotonic()-started,**error_fields(error)})
        save(path,result);return result
    outputs=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        tasks=[pool.submit(work,j) for j in jobs]
        for n,f in enumerate(as_completed(tasks),1):
            r=f.result();outputs.append(r)
            print(f"{n}/{len(jobs)} {r['id']} {r['condition']} {r['status']}",flush=True)
    order={(j['id'],j['condition']):i for i,j in enumerate(jobs)}
    outputs.sort(key=lambda r:order[(r['id'],r['condition'])]);save(folder/'outputs.json',outputs)
    by={(r['id'],r['condition']):r for r in outputs};sentences={r['id']:r['input'] for r in outputs}
    lines=[]
    with (folder/'comparison.tsv').open('w') as f:
        w=csv.writer(f,delimiter='\t');w.writerow(['id','standard',*CONDITIONS])
        for sid in sorted(sentences):
            vals=[by[(sid,c)].get('output','[FAILED]') for c in CONDITIONS]
            w.writerow([sid,sentences[sid],*vals]);lines.extend([sid+' '+sentences[sid],*[c+': '+v for c,v in zip(CONDITIONS,vals)],''])
    (folder/'comparison.txt').write_text('\n'.join(lines))
    # Blind sheet intentionally has no model-generated quality judgments.
    rng=random.Random(SEED);shuffled=list(outputs);rng.shuffle(shuffled)
    with (folder/'blind_review.tsv').open('w') as f:
        w=csv.writer(f,delimiter='\t');w.writerow(['blind_id','standard','output','meaning_1to5','politeness_1to5','grammar_1to5','naturalness_1to5','notes'])
        for n,r in enumerate(shuffled,1):w.writerow([f'B{n:03}',r['input'],r.get('output','[FAILED]'),'','','','',''])
    save(folder/'blind_key.json',{f'B{n:03}':{'id':r['id'],'condition':r['condition']} for n,r in enumerate(shuffled,1)})
    protocol.update(status='completed' if all(r['status']=='success' for r in outputs) else 'completed_with_failures',
                    completed=sum(r['status']=='success' for r in outputs),
                    actual_generation_attempts=sum(len(r['attempts']) for r in outputs),
                    completed_utc=dt.datetime.now(dt.timezone.utc).isoformat(),quality_evaluation='pending independent human review')
    save(folder/'protocol.json',protocol)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['prepare','generate']);p.add_argument('--folder',type=Path,required=True)
    p.add_argument('--query-mode',choices=['raw_sentence','analysis_json'],default='raw_sentence')
    p.add_argument('--inputs',type=Path);p.add_argument('--analysis',type=Path)
    a=p.parse_args()
    if a.mode=='prepare':prepare(a.folder.resolve(),a.query_mode,a.inputs,a.analysis)
    else:generate(a.folder.resolve())

if __name__=='__main__':main()

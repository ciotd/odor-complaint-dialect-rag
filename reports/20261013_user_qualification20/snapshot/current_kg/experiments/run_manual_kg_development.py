"""Function-first manual-analysis KG development run. No hardcoded sentence-to-rule seeds."""
import argparse
from collections import Counter
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys
import time

BASE = Path(__file__).resolve().parent
GRAMMAR = BASE.parent / 'grammar'
sys.path.insert(0, str(GRAMMAR))
from query_review import inspect_conditions, index_conditions
from run_seeded_kg import connection, payload, check_response, error_fields

from analysis_input import normalize_analysis, targets_for, route_functions, CONTRACT_PATH, POLICY_ID

def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v): p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')

def retrieve(graph, analysis):
    analysis=normalize_analysis(analysis)
    nodes={n['id']:n for n in graph['nodes']}
    edges=graph['edges']
    condition_index=index_conditions(graph)
    outputs=[]
    for item in analysis['items']:
        clauses=[]
        packet={'analysis_origin':analysis['origin'],'style_policy':analysis['policy']['style_policy'],
                'preserve':item['preservation_note'],'unqueried_structures':item['unqueried_structure_note'],
                'clauses':[],'warning':'아래는 조건이 일치해 이번 개발 실험의 참고 후보로 선택한 자료입니다. 원문 의미·높임·시제·의도가 유지될 때 활용하세요. generation_approved:false는 독립 검증 미실시 표시이며 이번 실험에서 참고를 금지한다는 뜻이 아닙니다. 예외와 출처 범위를 보존하세요.'}
        for clause in item['clauses']:
            known={k:v for k,v in clause['features'].items() if v is not None}
            funcs, route_gaps=route_functions(clause)
            targets=targets_for(clause)
            # Connectives do not acquire a speech level from an unknown addressee relation.
            # Evaluate candidates with an empty target; genuinely required target conditions
            # remain unknown in inspect_conditions and cannot pass.
            if clause['role']=='connective' and not targets:
                targets=[{}]
            analysis_gaps=route_gaps + (['unknown_observed_politeness'] if not targets else [])
            target_slot='clause.connective' if clause['role']=='connective' else 'clause.final_ending'
            candidates=[]
            for edge in edges:
                if edge['type']!='realizes' or edge['target'] not in {'concept:'+f for f in funcs}:continue
                aid=edge['properties'].get('assertion_id')
                if aid is None:continue
                ap=nodes[aid]['properties']['application']
                form=nodes[edge['source']]['properties']['text']
                candidate={k:v for k,v in clause['preserved_candidate_features'].items() if v is not None}
                # Read suffix components from actual combines_with -> has_surface_form paths.
                components=[]
                for surface in edges:
                    if surface['type']=='has_surface_form' and surface['target']==edge['source']:
                        components += [nodes[c['target']]['properties'].get('text') for c in edges
                                       if c['type']=='combines_with' and c['source']==surface['source']]
                suffixes=set(components)&{'요','예','-요','-예'}
                if len(suffixes)==1:candidate['following_form']=next(iter(suffixes)).lstrip('-')
                scenarios=[]
                for target in targets:
                    diagnostic=inspect_conditions(graph,edge['source'],known,candidate,target,_index=condition_index)
                    a=next(a for a in diagnostic['base_assertions'] if a['assertion_id']==aid)
                    reasons=[]
                    if ap['target']!=target_slot:reasons.append('wrong_application_slot')
                    if a['assessment']['status']!='match':reasons.append('condition_'+a['assessment']['status'])
                    if a['source_review']!='author_checked':reasons.append('source_review_pending')
                    if a['assertion_mode'] not in ['source_statement','extractor_interpretation']:reasons.append('not_general_statement')
                    if diagnostic['matched_explicit_exclusions']:reasons.append('explicit_exclusion')
                    if known.get('speech_act')=='request' and known.get('sentence_type')=='interrogative' and edge['target']!='concept:REQUEST':
                        reasons.append('question_function_alone_does_not_establish_request_usage')
                    # Do not promote match on POS/function alone into a style decision.
                    all_fields={c['field'] for m in ['all','any'] for c in a['assessment']['conditions'][m]}
                    if clause['role']=='main' and not all_fields & {'speech_level','addressee_treatment'}:
                        reasons.append('target_politeness_not_structured')
                    scenarios.append({'target':target,'candidate_features':candidate,'reasons':reasons,
                                      'diagnostic':diagnostic,'eligible':not reasons})
                candidates.append({'assertion_id':aid,'record_id':edge['properties']['record_id'],
                    'form':form,'function_path':[edge['target'],edge['source'],aid],
                    'function_edge_id':edge['id'],'scenarios':scenarios})
            # All discoveries remain in the audit. Prompt size is bounded by a declared cap.
            eligible=[]
            for c in candidates:
                valid=[s for s in c['scenarios'] if s['eligible']]
                if valid:
                    best=valid[0];a=next(a for a in best['diagnostic']['base_assertions'] if a['assertion_id']==c['assertion_id'])
                    specificity=sum(len(a['assessment']['conditions'][m]) for m in ['all','any'])
                    eligible.append((specificity,c,best,a))
            eligible.sort(key=lambda x:(-x[0],x[1]['assertion_id']))
            chosen=[];seen=set()
            for score,c,best,a in eligible:
                key=(c['form'],c['record_id'])
                if key in seen:continue
                seen.add(key)
                if len(chosen)>=6:continue
                chosen.append({'assertion_id':c['assertion_id'],'record_id':c['record_id'],'form':c['form'],
                    'target_hypothesis':best['target'],'candidate_features':best['candidate_features'],
                    'conditions':a['assessment']['conditions'],'scope':a['scope'],'details':a['details'],
                    'gaps':a['gaps'],'evidence':a['evidence'],
                    'related_constraints':[{'link_id':r['link_id'],'relation':r['relation'],'limits':r['limits'],
                        'link_status':r['link_status'],'condition_inheritance':False,
                        'assertions':[{'assertion_id':x['assertion_id'],'predicate':x['predicate'],
                            'object':x['object'],'assessment':x['assessment'],'source_review':x['source_review'],
                            'scope':x['scope'],'details':x['details']} for x in r['assertions']]}
                        for r in best['diagnostic']['references']],
                    'generation_approved':False})
            selected_ids={c['assertion_id'] for c in chosen}
            for c in candidates:
                c['disposition']='sent_as_conditional_reference' if c['assertion_id'] in selected_ids else 'eligible_not_sent_cap_or_duplicate' if any(s['eligible'] for s in c['scenarios']) else 'held_or_excluded'
                # Static source text is already in the hashed graph and selected prompt packet.
                # Keep all decisions/paths without repeating entire records for every scenario.
                for scenario in c['scenarios']:
                    diagnostic=scenario['diagnostic']
                    def brief(a):
                        return {k:a[k] for k in ['assertion_id','predicate','assessment','source_review','assertion_mode']}
                    scenario['diagnostic']={
                        'base_assertions':[brief(a) for a in diagnostic['base_assertions']],
                        'references':[{**{k:r[k] for k in ['link_id','relation','from','to','link_status','limits','condition_inheritance']},
                                       'assertions':[brief(a) for a in r['assertions']]} for r in diagnostic['references']],
                        'matched_explicit_exclusions':diagnostic['matched_explicit_exclusions'],
                        'held_assertions':diagnostic['held_assertions'], 'generation_approved':False}
            clauses.append({'clause_id':clause['clause_id'],'analysis':clause,'derived_targets':targets,'analysis_gaps':analysis_gaps,'searched_functions':sorted(funcs),
                            'candidates':candidates,'selected_assertion_ids':sorted(selected_ids)})
            packet['clauses'].append({'clause_id':clause['clause_id'],'text':clause['text'],
                'role':clause['role'],'input_analysis':known,'candidates':chosen,
                'analysis_gaps':analysis_gaps,'annotations':clause['annotations'],
                'observed_politeness':clause['observed_politeness'],
                'observed_subject_honorific':clause.get('observed_subject_honorific', 'unknown'),
                'tense_or_modality':clause.get('tense_or_modality', 'unknown'),
                'coverage_note':'No eligible KG reference for this clause; this is a retrieval gap, not grammatical impossibility.' if not chosen else 'Conditions matched under stated style hypotheses; scope/gaps remain.'})
        outputs.append({'id':item['id'],'input':item['input'],'clauses':clauses,'prompt_packet':packet})
    return outputs

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['validate','prepare','run'])
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    gp=GRAMMAR/'grammar.graph.json';ap=BASE/'inputs/development_30.manual_analysis.json';rp=BASE/'archive/legacy_development/development_30.manual_retrieval.json'
    dependencies={'analysis_adapter_sha256':sha(BASE/'analysis_input.py'),
                  'analysis_contract_sha256':sha(CONTRACT_PATH),'style_policy_id':POLICY_ID}
    if args.mode=='validate':
        normalized=normalize_analysis(read(ap))
        result={'status':'validated_manual_input_not_automatic_analysis', **dependencies,
                'source_analysis_sha256':sha(ap),'normalized_analysis':normalized,
                'item_count':len(normalized['items']),
                'clause_count':sum(len(i['clauses']) for i in normalized['items'])}
        save(BASE/'archive/diagnostics/analysis_validation.results.json',result)
        print(json.dumps({k:v for k,v in result.items() if k!='normalized_analysis'},ensure_ascii=False))
        return
    if args.mode=='prepare':
        result={**dependencies,'graph_sha256':sha(gp),'analysis_sha256':sha(ap),'runner_sha256':sha(Path(__file__)),
            'query_engine_sha256':sha(GRAMMAR/'query_review.py'),
            'status':'prepared_not_generated','selection_policy':'function routes, all/any conditions and linked exclusions; style evidence required for main clauses; max6 per clause, condition count descending, ID tie break; no sentence IDs for rule selection',
            'items':retrieve(read(gp),read(ap))}
        save(rp,result)
        for item in result['items']:
            print(item['id'],[(c['clause_id'],c['selected_assertion_ids']) for c in item['clauses']])
        return
    if not args.execute:raise SystemExit('Use --execute for the authorized model run')
    retrieval=read(rp)
    if any(retrieval.get(k)!=v for k,v in dependencies.items()):raise ValueError('Stale analysis adapter, contract or style policy')
    if retrieval['graph_sha256']!=sha(gp) or retrieval['analysis_sha256']!=sha(ap) or retrieval['runner_sha256']!=sha(Path(__file__)):raise ValueError('Stale retrieval')
    if retrieval['query_engine_sha256']!=sha(GRAMMAR/'query_review.py'):raise ValueError('Stale query engine')
    approval=retrieval.get('pre_generation_review',{})
    if approval.get('status')!='reviewed_for_development_run':raise ValueError('Review retrieval before generation')
    dataset=[json.loads(l) for l in (BASE/'inputs/development_30.jsonl').read_text().splitlines()]
    if [(r['id'],r['standard']) for r in dataset]!=[(r['id'],r['input']) for r in retrieval['items']]:raise ValueError('Dataset mismatch')
    durable=BASE/'archive/legacy_development/development_30.manual_kg_results.json'
    if durable.exists():raise ValueError('Existing results are immutable; choose a new version before rerun')
    config=read(BASE/'inputs/development_30.config.json');seed=20260923
    config={**config,'condition':'kg_function_retrieval_manual_analysis','kg_used':True}
    stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');folder=BASE/'archive/runs'/('manual_kg_'+stamp);folder.mkdir(parents=True)
    manifest={**dependencies,'started_at_utc':stamp,'status':'running','completed':0,'condition':'kg_function_retrieval_manual_analysis',
        'config':config,'seed':seed,'graph_sha256':sha(gp),'analysis_sha256':sha(ap),'retrieval_sha256':sha(rp),
        'runner_sha256':sha(Path(__file__)),'dataset_sha256':sha(BASE/'inputs/development_30.jsonl'),
        'baseline':'not_rerun; historical baseline is not a same-time controlled comparison',
        'checkpoint_and_quantization':'not_verified','folder':str(folder.relative_to(BASE.parent.parent))}
    outputs=[]
    save(folder/'retrieval.json',retrieval);save(folder/'analysis.json',read(ap));save(folder/'manifest.json',manifest)
    (folder/'grammar.graph.json').write_bytes(gp.read_bytes())
    (folder/'analysis_input.py').write_bytes((BASE/'analysis_input.py').read_bytes())
    (folder/'analysis_contract.json').write_bytes(CONTRACT_PATH.read_bytes())
    (folder/'runner.py').write_bytes(Path(__file__).read_bytes())
    (folder/'query_review.py').write_bytes((GRAMMAR/'query_review.py').read_bytes())
    try:
        call,endpoint_hash=connection();manifest['endpoint_sha256']=endpoint_hash
        probes=[p for p in (BASE/'archive/runs').glob('seed_probe_*/probe.json')
                if read(p).get('endpoint_sha256')==endpoint_hash and read(p).get('seed')==seed
                and read(p)['validation'].get('numeric_seed_accepted')
                and read(p)['validation'].get('invalid_seed_rejected')]
        if not probes:raise RuntimeError('No matching saved seed capability probe')
        manifest['seed_probe_sha256']=sha(sorted(probes)[-1])
        manifest['seed_probe_note']='Existing endpoint probe; seed is supplied on every request, not a deterministic guarantee.'
        manifest['available_models']=[m['id'] for m in call('/models')['data']]
        if config['requested_model'] not in manifest['available_models']:raise RuntimeError('Requested model unavailable')
        for row in retrieval['items']:
            req=payload(config,row['input'],seed,row['prompt_packet']);start=time.monotonic()
            response=call('/chat/completions',req)
            out={'id':row['id'],'input':row['input'],'request':req,'response':response,
                 'output':response['choices'][0]['message'].get('content'),'elapsed_seconds':round(time.monotonic()-start,3)}
            with (folder/'outputs.jsonl').open('a') as f:f.write(json.dumps(out,ensure_ascii=False)+'\n')
            outputs.append(out);check_response(response,config['requested_model'])
            manifest['completed']+=1;save(folder/'manifest.json',manifest)
            print(row['id']+' saved',flush=True)
        manifest['status']='succeeded'
    except Exception as e:manifest.update(status='failed',**error_fields(e))
    finally:
        manifest['ended_at_utc']=dt.datetime.now(dt.timezone.utc).isoformat();save(folder/'manifest.json',manifest)
        save(durable,{'manifest':manifest,'items':outputs})
        print(json.dumps({k:manifest.get(k) for k in ['status','completed','folder','error_type','http_status']},ensure_ascii=False),flush=True)
    if manifest['status']!='succeeded':raise SystemExit(1)

if __name__=='__main__':main()

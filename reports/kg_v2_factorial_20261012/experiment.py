"""Frozen 2x2 experiment: conditional statement retrieval x generation packaging.

Run init -> analyze -> prepare -> run -> report. Does not mutate production KG.
No model-authored dialect answers enter retrieval, prompts, or automatic labels.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
import csv
import hashlib
import html
import importlib.util
import json
from pathlib import Path
import random
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT/'current_kg/experiments'))
sys.path.insert(0, str(ROOT/'kg_v2'))
from run_seeded_kg import connection, check_response, error_fields, save, sha
from run_translation import make_request, config
from sentence_retrieval import morphology, semantic_guard, compact
from source_analysis_guard import guard_analysis
from semantic_retrieval import SemanticIndex, load_experimental_retriever

OLD = ROOT/'kg_v2/reports/translation_20261012_ending_repair'
CONDITIONS = ['A', 'B', 'C', 'D']
NEW = [
    ('NEW001', '저기 창가에 앉아 있는 분이 제 선생님이에요.', '명사 서술과 청자 높임'),
    ('NEW002', '저는 어제 도서관에서 책을 빌렸어요.', '과거와 청자 높임'),
    ('NEW003', '아버지께서는 아직 저녁을 안 드셨어요.', '부정·과거·주체와 청자 높임'),
    ('NEW004', '회의가 벌써 시작했나요?', '파생 서술어와 판정 의문'),
    ('NEW005', '이 서류는 어디에 놓으면 될까요?', '간접 질문과 청자 높임'),
    ('NEW006', '계단이 어두우니까 조심해서 내려오세요.', '지시·이동 방향·높임'),
    ('NEW007', '내가 먼저 먹고 있을 테니까 천천히 와.', '선행 순서와 연결 활용'),
    ('NEW008', '그건 네 잘못이 아니야.', '부정 서술과 비높임'),
    ('NEW009', '동생이 좋아하는 과자를 가방에 넣었어.', '관형절과 과거'),
    ('NEW010', '할아버지, 안경을 어디에 두셨어요? 제가 같이 찾아드릴게요.', '호칭·과거 질문·높임'),
    ('NEW011', '오늘은 시간이 없어서 먼저 갈게요. 남은 일은 내일 제가 할게요.', '순서·의도·복수 문장 높임'),
    ('NEW012', '그 물건을 버리라고 한 건 아니었어요. 잠깐 다른 곳에 옮겨 달라는 뜻이었어요.', '인용·부정·과거·간접 요청'),
]


def read(path):
    return json.loads(path.read_text())


def dependencies():
    paths = [ROOT/'kg_v2'/n for n in ['facts.jsonl','graph.json','sentence_retrieval.py','query.py','run_translation.py']]
    paths += [OLD/n for n in ['analysis.json','jobs.json','retrieval.json','outputs.json']]
    paths += [ROOT/'current_kg/experiments'/n for n in ['run_auto_analysis_development.py','source_analysis_guard.py','analysis_input.py','run_controlled_retrieval.py','run_seeded_kg.py','inputs/development_30.config.json']]
    return {str(p.relative_to(ROOT)):sha(p) for p in paths}


def check_frozen():
    assert dependencies() == read(HERE/'protocol.json')['dependencies'], 'Frozen source changed'


def init():
    if (HERE/'protocol.json').exists():
        raise ValueError('Experiment already initialized')
    save(HERE/'new_inputs.json', [{'id':i,'standard':s,'diagnostic_focus':f} for i,s,f in NEW])
    save(HERE/'protocol.json', {
        'status':'initialized', 'design':'2x2 retrieval x generation packaging',
        'conditions':{'A':'current graph retrieval/current packet','B':'hybrid conditional statement retrieval/current packet',
                      'C':'current graph retrieval/segment transformation plan','D':'hybrid conditional statement retrieval/segment transformation plan'},
        'dependencies':dependencies(), 'new_inputs_sha256':sha(HERE/'new_inputs.json'),
        'config':config(), 'seed':20260923,'repetitions':1,'new_analyses':12,'planned_generations':200,
        'policy':'No KG edits, shared analysis repairs, generation retries based on quality, or gold dialect answers.',
        'new_set_status':'Prospectively fixed challenge inputs before any outputs; authored from known failure categories, not independent held-out evaluation.',
        'semantic_policy':'Local pinned multilingual-e5-small; source/target patterns, functions, structured conditions and scope indexed. Evidence/notes retained in records; evidence quote bodies are not embedded. Lexical exact identity guard and grammar function/role/register guards remain. Cosine reranks within existing route/style tiers; top-12 semantic discoveries per unit are condition-checked. No threshold fitted to outputs.',
        'packaging_policy':'Same selected IDs, spans, facts, conditions, constraints, scope, notes and graph edges within A/C and B/D. Plan omits evidence quote bodies and administrative check logs but retains source/page pointers; this is a presentation bundle, not pure token-length ablation. Raw evidence remains in retrieval logs.',
        'limitations':['Analysis errors intentionally shared and not repaired in this experiment.',
                      'Structured conditions only; textual constraints and sense remain unresolved.',
                      'Known route priority still favors lexical facts; this is not an experiment on all possible retrieval improvements.',
                      'One sample per condition; no checkpoint immutability guarantee or statistical significance claim.',
                      'No independent native-speaker gold; automatic flags are screening only.']})
    print('Frozen 38 development + 12 prospective challenge inputs, 200 generations.')


def analyze():
    from run_auto_analysis_development import analyze_one
    check_frozen()
    call, endpoint = connection()
    cfg = config()
    assert cfg['requested_model'] in [x['id'] for x in call('/models')['data']]
    rows = read(HERE/'new_inputs.json')
    def work(row):
        path = HERE/'analysis_requests'/(row['id']+'.json')
        result=read(path) if path.exists() else analyze_one(call,cfg,row,HERE)
        if result['status']=='validated':return result
        return repair_analysis(call,cfg,row,result,path)
    results=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        for future in as_completed([pool.submit(work,r) for r in rows]):
            result=future.result();results.append(result)
            print(result['id'],result['status'],flush=True)
    assert all(r['status']=='validated' for r in results), 'Some analyses failed; inspect preserved attempts'
    items=[]; audits=[]
    for result in sorted(results,key=lambda x:x['id']):
        normalized,guard=guard_analysis(result['normalized_analysis'])
        item=normalized['items'][0];morph=morphology(item['input'])
        item,semantic=semantic_guard(item,morph)
        items.append(item);audits.append({'id':item['id'],'guard':guard,'semantic_guard':semantic})
    save(HERE/'new_analysis.json',{'items':items});save(HERE/'new_analysis_guards.json',audits)
    p=read(HERE/'protocol.json');p.update(status='analyzed',endpoint_sha256=endpoint)
    save(HERE/'protocol.json',p)


def repair_analysis(call,cfg,row,result,path):
    """Bounded schema-only feedback; preserve all original attempts, no gold labels."""
    import jsonschema
    from run_auto_analysis_development import adapt,raw_schema
    # Existing analyzer truncates a verbose exception before all missing keys.
    # Use concise validator messages; never provide linguistic answer values.
    for _ in range(max(0,4-len(result['attempts']))):
        previous=result['attempts'][-1]
        content=previous.get('response',{}).get('choices',[{}])[0].get('message',{}).get('content','')
        try:
            raw=json.loads(content)
            errors=[str(list(e.path))+': '+e.message for e in jsonschema.Draft7Validator(raw_schema()).iter_errors(raw)]
        except ValueError:errors=['Output must be valid JSON.']
        errors=errors[:40] or [previous.get('validation_error','Source text spans and required fields must be valid.')[:1500]]
        req=deepcopy(result['attempts'][0]['request'])
        req['messages'] += [{'role':'assistant','content':content},
            {'role':'user','content':'원문 분석을 다시 출력하세요. 아래는 형식 오류 목록입니다. 모든 필수 필드를 올바른 위치에 포함하고 원문에 있는 구간만 사용하세요.\n'+'\n'.join(errors)}]
        attempt={'request':req,'repair_kind':'concise_schema_feedback_only'};start=time.monotonic()
        try:
            response=call('/chat/completions',req);attempt['response']=response
            raw=json.loads(check_response(response,cfg['requested_model']))
            if not raw.get('source_units'):raise ValueError('source_units required')
            normalized=adapt(row,raw)
            result.update(status='validated',raw_analysis=raw,normalized_analysis=normalized)
        except (ValueError,jsonschema.ValidationError) as e:attempt['validation_error']=str(e)[:2500]
        except Exception as e:attempt.update(error_fields(e))
        attempt['elapsed_seconds']=time.monotonic()-start;result['attempts'].append(attempt);save(path,result)
        if result['status']=='validated':break
    return result


def plan_packet(packet,item):
    """Preserve candidate constraints; distinguish evidence, derivation, and guesses."""
    groups={}
    for ref in packet['references']:
        b=ref['input_binding'];key=tuple(b['span'])
        if key not in groups:
            relevant=[c for c in item['clauses'] if c['span'][0]<=key[0] and key[1]<=c['span'][1]]
            groups[key]={'target_text':b['text'],'span':list(key),
                         'preserve':[{'clause_id':c['clause_id'],'features':c['features'],
                                      'listener_politeness':c['observed_politeness'],
                                      'subject_honorific':c['observed_subject_honorific'],
                                      'tense_or_modality':c['tense_or_modality']} for c in relevant],
                         'candidates':[]}
        candidate={k:deepcopy(ref[k]) for k in ['id','source_id','type','source_pattern','target_pattern','functions','conditions','constraints','scope','claim_status','usability','notes']}
        candidate.update(binding=deepcopy(b),
                         evidence_pages=[e['pdf_page'] for e in ref['evidence']],
                         status='conditional_candidate_not_validated_surface')
        groups[key]['candidates'].append(candidate)
    return {'transformation_plan':list(groups.values()), 'graph_paths':deepcopy(packet['graph_paths']),
            'plan_policy':'후보는 대안이며 모두 적용하지 않는다. 대상 구간에만 적용하고 원문의 의미·부정·시제·주체 높임·청자 높임·이동 방향·인용을 보존한다. 조건과 문맥이 불확실하면 억지로 치환하지 않는다. 기본형·인용형을 완성 활용형으로 복사하지 않는다. derived_composition_not_attested_surface는 규칙 조합이며 문헌의 실제 완성형이 아니다.'}


def make_plan_request(cfg,item,morph,packet):
    req=make_request(cfg,item,morph,packet)
    prefix,raw=req['messages'][1]['content'].split('\n',1)
    body=json.loads(raw);body.pop('references');body.pop('graph_paths')
    body.update(plan_packet(packet,item))
    prefix=prefix.replace('references와 graph_paths는','transformation_plan과 graph_paths는')
    req['messages'][1]['content']=prefix+'\n'+compact(body)
    return req


def prepare():
    check_frozen()
    if (HERE/'jobs.json').exists():
        raise ValueError('Prepared inputs are frozen; use new folder for changes')
    items=read(OLD/'analysis.json')['items']+read(HERE/'new_analysis.json')['items']
    index=SemanticIndex(HERE)
    engine=load_experimental_retriever(HERE,index)
    from sentence_retrieval import SentenceRetriever
    baseline=SentenceRetriever(); cfg=config(); jobs=[]; retrieval=[]
    old_jobs={(j['id'],j['condition']):j for j in read(OLD/'jobs.json')}
    for n,item in enumerate(items):
        morph=morphology(item['input']);a=baseline.retrieve(item,morph);b=engine.retrieve(item,morph)
        pa=a['packets']['v2_graph'];pb=b['packets']['v2_graph']
        requests={'A':make_request(cfg,item,morph,pa),'B':make_request(cfg,item,morph,pb),
                  'C':make_plan_request(cfg,item,morph,pa),'D':make_plan_request(cfg,item,morph,pb)}
        if item['id'].startswith(('DEV','LONG')):
            assert requests['A']==old_jobs[item['id'],'v2_graph']['request'], 'A must exactly reproduce previous request'
        for condition in CONDITIONS[n%4:]+CONDITIONS[:n%4]:
            jobs.append({'id':item['id'],'input':item['input'],'condition':condition,'request':requests[condition]})
        retrieval.append({'id':item['id'],'input':item['input'],'baseline':a,'hybrid':b,'semantic_audit':deepcopy(index.last_audit)})
        print(item['id'],'baseline',len(pa['references']),'hybrid',len(pb['references']),flush=True)
    save(HERE/'analysis.json',{'items':items});save(HERE/'retrieval.json',retrieval);save(HERE/'jobs.json',jobs)
    p=read(HERE/'protocol.json');p.update(status='prepared',sentences=len(items),embedding=index.metadata,
        frozen_inputs={name:sha(HERE/name) for name in ['analysis.json','retrieval.json','jobs.json','new_inputs.json','new_analysis.json','semantic_index.json','experiment.py','semantic_retrieval.py','snapshots/sentence_retrieval.py','snapshots/query.py','snapshots/run_translation.py','snapshots/experimental_retriever.py']})
    save(HERE/'protocol.json',p)
    validate()


def validate():
    check_frozen();p=read(HERE/'protocol.json')
    for name,digest in p['frozen_inputs'].items():assert sha(HERE/name)==digest,name
    jobs=read(HERE/'jobs.json');rows=read(HERE/'retrieval.json');by={(j['id'],j['condition']):j for j in jobs}
    assert len(jobs)==len(by)==4*len(rows)==200
    for row in rows:
        requests=[by[row['id'],c]['request'] for c in CONDITIONS]
        settings=[{k:v for k,v in r.items() if k!='messages'} for r in requests]
        assert all(x==settings[0] for x in settings)
        assert all(r['messages'][0]==requests[0]['messages'][0] for r in requests)
        bodies=[json.loads(r['messages'][1]['content'].split('\n',1)[1]) for r in requests]
        for body in bodies[1:]:
            for key in ['standard','analysis','source_morphology']:assert body[key]==bodies[0][key]
        for raw,planned in [(bodies[0],bodies[2]),(bodies[1],bodies[3])]:
            refs={(r['id'],tuple(r['input_binding']['span'])):r for r in raw['references']}
            candidates={(c['id'],tuple(g['span'])):c for g in planned['transformation_plan'] for c in g['candidates']}
            assert refs.keys()==candidates.keys()
            for key,ref in refs.items():
                c=candidates[key]
                for field in ['source_pattern','target_pattern','functions','conditions','constraints','scope','notes','claim_status','usability']:
                    assert c[field]==ref[field]
                assert c['evidence_pages']==[e['pdf_page'] for e in ref['evidence']]
            assert raw['graph_paths']==planned['graph_paths']
        for mode in ['baseline','hybrid']:
            packet=row[mode]['packets']['v2_graph'];ids={f['id'] for f in packet['references']}
            assert len(compact(packet))<=24000
            for f in packet['references']:
                assert f['usability']=='candidate' and not f['checks']['rejected']
                assert all(c['status']=='satisfied' for c in f['checks']['conditions'])
                b=f['input_binding'];assert row['input'][slice(*b['span'])]==b['text']
            for edge in packet['graph_paths']:assert edge['source'] in ids and edge['target'] in ids
    save(HERE/'validation.json',{'status':'passed','sentences':len(rows),'requests':len(jobs),
        'checks':['frozen KG/code/inputs','A exactly matched old requests during prepare','same analysis/morphology/settings/system',
                  'A/C and B/D equal candidate identities/bindings/constraints/scope/notes/pages/paths','no failed or unknown structured conditions','exact source bindings','reference budget and graph endpoints']})
    print('Validation passed: 200 requests, frozen KG, paired contents, shared analysis.')


def run():
    validate();call,endpoint=connection();p=read(HERE/'protocol.json');jobs=read(HERE/'jobs.json')
    assert config()['requested_model'] in [x['id'] for x in call('/models')['data']]
    p.update(status='running',endpoint_sha256=endpoint);save(HERE/'protocol.json',p)
    def work(job):
        path=HERE/'raw'/(job['id']+'_'+job['condition']+'.json')
        if path.exists():
            old=read(path);assert old['request']==job['request']
            if old['status']=='success':return old
        row={**job,'status':'failed','attempts':[]}
        for _ in range(2):
            start=time.monotonic()
            try:
                response=call('/chat/completions',job['request'])
                row['attempts'].append({'seconds':time.monotonic()-start,'response':response})
                row.update(output=check_response(response,job['request']['model']),status='success');break
            except Exception as e:row['attempts'].append({'seconds':time.monotonic()-start,**error_fields(e)})
        save(path,row);return row
    rows=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        for n,future in enumerate(as_completed([pool.submit(work,j) for j in jobs]),1):
            r=future.result();rows.append(r);print(n,len(jobs),r['id'],r['condition'],r['status'],flush=True)
    rows.sort(key=lambda r:(r['id'],r['condition']))
    save(HERE/'outputs.json',[{k:r[k] for k in ['id','input','condition','status','output'] if k in r} for r in rows])
    p.update(status='completed' if all(r['status']=='success' for r in rows) else 'completed_with_failures',
             successful_generations=sum(r['status']=='success' for r in rows),actual_attempts=sum(len(r['attempts']) for r in rows))
    save(HERE/'protocol.json',p);report()


def report():
    import statistics
    rows=read(HERE/'outputs.json');by={(r['id'],r['condition']):r for r in rows};jobs=read(HERE/'jobs.json')
    retrieval=read(HERE/'retrieval.json');lines=[];htmlrows=[]
    with (HERE/'comparison.tsv').open('w') as f:
        writer=csv.writer(f,delimiter='\t',lineterminator='\n');writer.writerow(['id','standard',*CONDITIONS])
        for sid in sorted({r['id'] for r in rows}):
            standard=by[sid,'A']['input'];vals=[by[sid,c].get('output','[FAILED]') for c in CONDITIONS]
            writer.writerow([sid,standard,*vals]);lines.extend([sid+' '+standard,*[c+': '+v for c,v in zip(CONDITIONS,vals)],''])
            htmlrows.append('<article><h2>'+html.escape(sid)+' '+html.escape(standard)+'</h2>'+''.join('<p><b>'+c+'</b> '+html.escape(v)+'</p>' for c,v in zip(CONDITIONS,vals))+'</article>')
    (HERE/'comparison.txt').write_text('\n'.join(lines))
    (HERE/'comparison.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>KG v2 2×2 비교</title><style>body{max-width:1100px;margin:30px auto;font:17px/1.7 sans-serif;padding:16px}article{border-top:1px solid #bbb}b{display:inline-block;width:35px}input{width:95%;padding:12px;position:sticky;top:0}</style><h1>KG v2 조회 × 생성 입력 비교</h1><p>A 현재 조회·현재 입력 / B 혼합 조회·현재 입력 / C 현재 조회·변환 계획 / D 혼합 조회·변환 계획</p><input placeholder="문장 ID 또는 표현 검색" oninput="document.querySelectorAll(\'article\').forEach(e=>e.hidden=!e.textContent.toLowerCase().includes(this.value.toLowerCase()))">'+''.join(htmlrows)+'</html>')
    changes=[]
    for r in retrieval:
        a={(f['id'],tuple(f['input_binding']['span'])) for f in r['baseline']['packets']['v2_graph']['references']}
        b={(f['id'],tuple(f['input_binding']['span'])) for f in r['hybrid']['packets']['v2_graph']['references']}
        changes.append({'id':r['id'],'added':sorted(b-a),'removed':sorted(a-b),'identical_selection':a==b,
                        'semantic_proposed':sum(x['status']=='proposed' for x in r['semantic_audit']['discoveries'])})
    save(HERE/'retrieval_changes.json',changes)
    summary={'successful_generations':sum(r['status']=='success' for r in rows),
             'selection_changed_sentences':sum(not x['identical_selection'] for x in changes),
             'median_user_characters':{c:statistics.median(len(j['request']['messages'][1]['content']) for j in jobs if j['condition']==c) for c in CONDITIONS},
             'output_difference_counts':{a+'_'+b:sum(by[s,a].get('output')!=by[s,b].get('output') for s in {r['id'] for r in rows}) for a,b in [('A','B'),('A','C'),('B','D'),('C','D')]},
             'warning':'Output differences and retrieval counts are NOT translation quality scores.'}
    save(HERE/'summary.json',summary)
    blind=list(rows);random.Random(20260923).shuffle(blind)
    with (HERE/'blind_review.tsv').open('w') as f:
        w=csv.writer(f,delimiter='\t',lineterminator='\n');w.writerow(['blind_id','standard','output','meaning','listener_politeness','subject_honorific','tense_negation','naturalness','notes'])
        for i,r in enumerate(blind,1):w.writerow([f'R{i:03}',r['input'],r.get('output','[FAILED]'),'','','','','',''])
    save(HERE/'blind_key.json',{f'R{i:03}':{'id':r['id'],'condition':r['condition']} for i,r in enumerate(blind,1)})
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['init','analyze','prepare','validate','run','report'])
    globals()[parser.parse_args().mode]()

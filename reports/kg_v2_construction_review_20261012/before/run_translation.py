"""Frozen paired generation experiment and live text -> analysis -> KG v2 -> LLM."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import datetime as dt
import json
from pathlib import Path
import random
import sys
import time

BASE = Path(__file__).resolve().parent
OLD = BASE.parent/'current_kg/experiments'
sys.path.insert(0, str(OLD))
from run_seeded_kg import connection, check_response, error_fields, save, sha
from run_controlled_retrieval import analysis_card
from sentence_retrieval import SentenceRetriever, morphology, semantic_guard, compact, BUDGET

CONDITIONS = ['no_kg', 'legacy_graph', 'v2_direct', 'v2_graph']
SEED = 20260923
DEFAULT = BASE/'local/translation_20261012_final'


def make_request(config, item, morph, packet):
    from transformation_plan import package_plan
    # Legacy packets use a different contract. Preserve them verbatim for the
    # legacy comparison instead of pretending they contain v2 bound statements.
    packaged=(package_plan(packet,item) if all('input_binding' in r for r in packet['references']) else packet)
    body = {'standard': item['input'], 'analysis': analysis_card(item),
            'source_morphology': morph, **packaged}
    instruction = ('standard를 자연스러운 경상도 방언으로 변환하세요. analysis와 source_morphology는 '
        '원문 분석의 가설이며 원문이 우선입니다. transformation_plan 또는 references와 graph_paths는 조건부 참고 자료입니다. '
        '의미·지역·시대·높임·결합 조건이 맞는 자료를 선택하고 관련 없는 자료는 사용하지 마세요. '
        '조건 미확인은 적용 허용이 아니며 연결된 진술끼리 조건을 상속하지 않습니다. '
        '기본형 대응과 완성 활용형을 구별하고 원문의 부정·시제·높임·인용·발화 의도를 유지하세요. '
        'preservation의 관형절·겸양·주체와 청자 높임·이동 관점 보존을 어휘 치환보다 우선하세요. '
        '모델 조언 후보는 원문 확인형이 아니며 불확실하면 원문의 구조를 보존하세요. '
        '표에 없는 활용형은 표에 실린 확인형으로 주장하지 마세요. 원문에 없는 내용을 추가하지 말고 변환한 발화만 출력하세요.\n')
    return {'model': config['requested_model'], **config['generation'], 'seed': SEED,
            'messages': [{'role': 'system', 'content': config['system_prompt']},
                         {'role': 'user', 'content': instruction+compact(body)}]}


def config():
    template=json.loads((OLD/'inputs/development_30.config.json').read_text())
    return {k:template[k] for k in ['requested_model','system_prompt','generation']}


def prepare(folder):
    if folder.exists():
        raise ValueError('Use a new folder; frozen runs are not overwritten')
    folder.mkdir(parents=True)
    engine = SentenceRetriever(); cfg = config(); jobs = []; retrieval = []; items = []; dependencies = {}
    legacy_engine = None; guard_changes = []
    for name in ['integrated_retrieval_20261008_dev30_final', 'long_dialogue_20261008_generation']:
        root = OLD/'archive/runs'/name
        analysis = json.loads((root/'analysis.json').read_text())['items']
        old = {r['id']: r for r in json.loads((root/'retrieval.json').read_text())}
        for filename in ['analysis.json', 'retrieval.json']:
            dependencies[str((root/filename).relative_to(BASE.parent))] = sha(root/filename)
        for item in analysis:
            assert old[item['id']]['input'] == item['input']
            morph = morphology(item['input']); item, changes = semantic_guard(item, morph)
            legacy_packet = old[item['id']]['packets']['graph_hybrid']
            if changes:
                if legacy_engine is None:
                    from embedding_retrieval import EmbeddingIndex
                    from integrated_retrieval import IntegratedRetriever
                    legacy_engine = IntegratedRetriever(json.loads((OLD.parent/'grammar/grammar.graph.json').read_text()), EmbeddingIndex())
                legacy_packet = legacy_engine.retrieve_item(item)['packets']['graph_hybrid']
                guard_changes.append({'id':item['id'],'changes':changes,'legacy_retrieval':'recomputed_with_same_guarded_analysis'})
            r = engine.retrieve(item, morph)
            r['packets'] = {'no_kg': {'references': [], 'graph_paths': []},
                            'legacy_graph': legacy_packet, **r['packets']}
            rotation = len(items) % len(CONDITIONS)
            order = CONDITIONS[rotation:]+CONDITIONS[:rotation]
            for c in order:
                jobs.append({'id': item['id'], 'input': item['input'], 'condition': c,
                             'request': make_request(cfg, item, morph, r['packets'][c])})
            retrieval.append(r); items.append(item)
            print(item['id'], {c: len(p['references']) for c,p in r['packets'].items()},
                  'paths', len(r['packets']['v2_graph']['graph_paths']), flush=True)
    save(folder/'jobs.json', jobs); save(folder/'retrieval.json', retrieval); save(folder/'analysis.json', {'items':items})
    for filename in ['sentence_retrieval.py', 'query.py', 'run_translation.py',
                     'transformation_plan.py','preservation_check.py','advisory_rules.json']:
        (folder/filename).write_bytes((BASE/filename).read_bytes())
        dependencies[str((BASE/filename).relative_to(BASE.parent))]=sha(BASE/filename)
    protocol = {'status': 'prepared', 'created_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'conditions': CONDITIONS, 'sentences': len(items), 'planned_calls': len(jobs), 'seed': SEED,
        'config': cfg, 'repetitions': 1, 'reference_budget_characters': BUDGET,
        'analysis': 'Same cached Qwen clause analysis plus fresh deterministic Kiwi morphology in all four conditions.',
        'legacy_retrieval': 'Cached final graph_hybrid packets for unchanged analysis; recomputed with the existing retriever wherever the shared source guard changes analysis.',
        'shared_analysis_guard_changes': guard_changes,
        'v2_retrieval': 'Source-bound morphology including same-eojeol derived predicates, guarded function routing, documentary candidates plus explicitly attributed bounded model composition, preservation-only support, compact plans, and optional compiled inflection edges.',
        'post_generation_policy':'Conservative preservation screening; at most one repair; first and repaired outputs both retained. Screening is not linguistic accuracy.',
        'frozen_hashes': {n:sha(folder/n) for n in ['jobs.json','retrieval.json','analysis.json']},
        'kg_hashes': {n:sha(BASE/n) for n in ['facts.jsonl','graph.json']},
        'dependency_hashes': dependencies,
        'limitations': ['Development inputs previously seen; not a held-out benchmark.',
            'One seed and one repetition; same endpoint model ID does not prove immutable checkpoint.',
            'Candidate scope/sense and free-text constraints require generator interpretation.',
            'Speech-style ranking is a retrieval preference, not a validated dialect-register equivalence or generated-politeness guarantee.',
            'Legacy-v2 compares the complete retrieval systems, not isolated graph topology.',
            'Direct vs graph adds both inflection statements and edges; not content-matched topology ablation.',
            'Naturalness requires human dialect-speaker review; automatic change rates are not accuracy.']}
    audit(folder, protocol)
    save(folder/'protocol.json', protocol)


def audit(folder, protocol):
    rows = json.loads((folder/'retrieval.json').read_text()); jobs = json.loads((folder/'jobs.json').read_text())
    ids = {(j['id'],j['condition']) for j in jobs}
    assert len(ids) == len(rows)*4 == len(jobs)
    for r in rows:
        for mode in ['v2_direct','v2_graph']:
            p = r['packets'][mode]; by = {f['id']:f for f in p['references']}
            assert len(compact(p)) <= BUDGET
            for f in p['references']:
                assert f['usability'] == 'candidate' and not f['checks']['rejected']
                assert all(c['status']=='satisfied' for c in f['checks']['conditions'])
                b=f['input_binding']; assert r['input'][slice(*b['span'])] == b['text']
            for edge in p['graph_paths']:
                assert edge['source'] in by and edge['target'] in by
        related = [j['request'] for j in jobs if j['id']==r['id']]
        for req in related[1:]:
            assert {k:v for k,v in req.items() if k!='messages'} == {k:v for k,v in related[0].items() if k!='messages'}
            assert req['messages'][0] == related[0]['messages'][0]
            prefix,body=req['messages'][1]['content'].split('\n',1)
            refprefix,refbody=related[0]['messages'][1]['content'].split('\n',1)
            assert prefix==refprefix
            a=json.loads(body);b=json.loads(refbody)
            variable={'references','graph_paths','transformation_plan','preservation','plan_policy'}
            assert {k:v for k,v in a.items() if k not in variable} == {k:v for k,v in b.items() if k not in variable}
    protocol['pre_generation_review'] = {'status':'passed','sentences':len(rows),
        'checks':['same generation settings and source analysis across conditions','exact input span bindings',
                  'no blocked/reference-only/unknown-condition v2 candidates','graph endpoints included','packet budget'],
        'v2_graph_active_sentences':sum(bool(r['packets']['v2_graph']['graph_paths']) for r in rows)}


def generate(folder, reuse=None):
    protocol=json.loads((folder/'protocol.json').read_text())
    assert protocol['pre_generation_review']['status']=='passed'
    assert all(sha(folder/n)==h for n,h in protocol['frozen_hashes'].items())
    jobs=json.loads((folder/'jobs.json').read_text()); call, endpoint=connection()
    assert protocol['config']['requested_model'] in [x['id'] for x in call('/models')['data']]
    protocol.update(status='generating',endpoint_sha256=endpoint); save(folder/'protocol.json',protocol)
    reused=set()
    if reuse:
        for j in jobs:
            if j['condition'] not in {'no_kg','legacy_graph'}:continue
            old=json.loads((reuse/'raw'/(j['id']+'_'+j['condition']+'.json')).read_text())
            if old['status']=='success' and old['request']==j['request']:
                save(folder/'raw'/(j['id']+'_'+j['condition']+'.json'),old)
                reused.add((j['id'],j['condition']))
    def work(job):
        path=folder/'raw'/(job['id']+'_'+job['condition']+'.json')
        if path.exists():
            old=json.loads(path.read_text()); assert old['request']==job['request']
            if old['status']=='success':return old
        result={**job,'status':'failed','attempts':[]}
        for attempt in range(2):
            start=time.monotonic()
            try:
                from preservation_check import generate_checked
                checked=generate_checked(call,job['request'],job['input'],check_response)
                result['attempts'].append({'seconds':time.monotonic()-start,'response':checked['response']})
                result.update(checked,status='success');break
            except Exception as e:result['attempts'].append({'seconds':time.monotonic()-start,**error_fields(e)})
        save(path,result);return result
    outputs=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        for n,f in enumerate(as_completed([pool.submit(work,j) for j in jobs]),1):
            r=f.result();outputs.append(r);print(n,len(jobs),r['id'],r['condition'],r['status'],flush=True)
    outputs.sort(key=lambda r:(r['id'],CONDITIONS.index(r['condition'])))
    save(folder/'outputs.json',outputs)
    protocol.update(status='completed' if all(r['status']=='success' for r in outputs) else 'completed_with_failures',
                    successful_calls=sum(r['status']=='success' for r in outputs),
                    actual_attempts=sum(len(r['attempts']) for r in outputs),
                    reused_results=len(reused), reuse_source=str(reuse.resolve().relative_to(BASE)) if reuse else None,
                    new_generation_attempts=sum(len(r['attempts']) for r in outputs if (r['id'],r['condition']) not in reused))
    save(folder/'protocol.json',protocol); export(folder)


def export(folder):
    name='translation_20261012' if folder.resolve()==DEFAULT.resolve() else folder.name
    report=BASE/'reports'/name
    if (report/'protocol.json').exists():
        prior=json.loads((report/'protocol.json').read_text())
        current=json.loads((folder/'protocol.json').read_text())
        if prior['frozen_hashes']!=current['frozen_hashes']:
            raise ValueError('Report destination belongs to different frozen inputs; use a distinct run name')
    report.mkdir(parents=True,exist_ok=True)
    rows=json.loads((folder/'outputs.json').read_text()); by={(r['id'],r['condition']):r for r in rows}
    lines=[]
    with (report/'comparison.tsv').open('w') as f:
        w=csv.writer(f,delimiter='\t',lineterminator='\n');w.writerow(['id','standard',*CONDITIONS])
        for sid in sorted({r['id'] for r in rows}):
            standard=by[sid,'no_kg']['input']; vals=[by[sid,c].get('output','[FAILED]') for c in CONDITIONS]
            w.writerow([sid,standard,*vals]);lines += [sid+' '+standard,*[c+': '+v for c,v in zip(CONDITIONS,vals)],'']
    (report/'comparison.txt').write_text('\n'.join(lines))
    save(report/'outputs.json',[{k:r[k] for k in ['id','input','condition','status','output'] if k in r} for r in rows])
    for n in ['protocol.json','retrieval.json','analysis.json','jobs.json']:(report/n).write_bytes((folder/n).read_bytes())
    shuffled=list(rows);random.Random(SEED).shuffle(shuffled)
    with (report/'blind_review.tsv').open('w') as f:
        w=csv.writer(f,delimiter='\t',lineterminator='\n');w.writerow(['blind_id','standard','output','meaning','politeness','grammar','naturalness','notes'])
        for i,r in enumerate(shuffled,1):w.writerow([f'B{i:03}',r['input'],r.get('output','[FAILED]'),'','','','',''])
    save(report/'blind_key.json',{f'B{i:03}':{'id':r['id'],'condition':r['condition']} for i,r in enumerate(shuffled,1)})


def translate(text, folder):
    from run_auto_analysis_development import analyze_one
    from source_analysis_guard import guard_analysis
    from model_client import connection as analysis_connection
    if folder.exists():raise ValueError('Use a new output folder')
    folder.mkdir(parents=True);cfg=config();call,_=analysis_connection(timeout=180)
    result=analyze_one(call,cfg,{'id':'LIVE001','standard':text},folder)
    if result['status']!='validated':raise ValueError('Input analysis failed; inspect preserved request')
    analysis,guard=guard_analysis(result['normalized_analysis']);item=analysis['items'][0]
    morph=morphology(item['input']);item,semantic=semantic_guard(item,morph);analysis['items']=[item]
    save(folder/'analysis.json',analysis);save(folder/'analysis_guard.json',guard)
    save(folder/'semantic_guard.json',semantic)
    r=SentenceRetriever().retrieve(item,morph);save(folder/'retrieval.json',r)
    req=make_request(cfg,item,r['morphology'],r['packets']['v2_graph'])
    from preservation_check import generate_checked
    result=generate_checked(call,req,text,check_response)
    save(folder/'result.json',result);print(result['output'])
    if result['final_check']['flags']:
        print('보존 검사: 검토 필요 — '+', '.join(f['kind'] for f in result['final_check']['flags']),file=sys.stderr)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','generate','export','translate'])
    p.add_argument('--folder',type=Path,default=DEFAULT);p.add_argument('--text');p.add_argument('--reuse-baselines',type=Path);a=p.parse_args()
    if a.mode=='translate':
        if not a.text:p.error('--text is required')
        translate(a.text,a.folder)
    elif a.mode=='generate':generate(a.folder,a.reuse_baselines)
    else:globals()[a.mode](a.folder)

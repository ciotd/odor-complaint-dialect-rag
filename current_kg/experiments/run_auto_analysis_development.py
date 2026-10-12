"""Qwen input analysis and three-condition development comparison; no sentence-specific rules."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
import datetime as dt
import json
from pathlib import Path
import sys
import time
import jsonschema

from analysis_input import (CONTRACT_PATH, POLICY_ID, TARGET_FIELDS, CANDIDATE_FIELDS,
                            normalize_analysis)
from run_manual_kg_development import retrieve
from run_seeded_kg import connection, payload, check_response, error_fields, sha, read, save

BASE = Path(__file__).resolve().parent
GRAMMAR = BASE.parent / 'grammar'
SEED = 20260923
CONDITIONS = ['no_kg', 'manual_analysis_kg', 'automatic_analysis_kg']
POLICY = {
    'style_policy_id': POLICY_ID, 'target_region': None,
    'no_seed_assertions_or_target_dialect_forms': True,
    'style_policy': '관찰된 존댓말은 HAEYO_LEVEL/HAISOCHE/informal_high, 반말은 HAECHE/HAERACHE/informal_low를 개발용 대안으로 조회. 동일 어체라는 주장이 아니며 원문 높임 보존이 우선.',
    'candidate_features': '분석된 선어말 형태를 유지하는 최소 구성 가정. KG 후보의 요구값에서 역으로 채우지 않음.',
    'selection': '기존 기능 경로·조건·제외 기준 및 절당 6개 상한 유지.',
}


def raw_schema():
    features = read(CONTRACT_PATH)['features']
    properties = {k: {'type': ['string', 'null'], **({'enum': v['values'] + [None]} if 'values' in v else {})}
                  for k, v in features.items() if k not in TARGET_FIELDS | CANDIDATE_FIELDS}
    clause = {'type': 'object', 'additionalProperties': False, 'properties': {
        'text': {'type': 'string', 'minLength': 1},
        'occurrence': {'type': 'integer', 'minimum': 0},
        'role': {'enum': ['main', 'connective']},
        'features': {'type': 'object', 'properties': properties, 'additionalProperties': False},
        'observed_politeness': {'enum': ['polite', 'non_polite', 'unknown']},
        'observed_subject_honorific': {'enum': ['not_observed', 'si_in_benefactive_auxiliary', 'lexical', 'si', 'unknown']},
        'tense_or_modality': {'enum': ['present', 'past', 'modal', 'retrospective', 'unknown']},
        'observed_prefinals': {'type': ['array', 'null'], 'items': {'enum': ['-시-', '-었-', '-겠-', '-더-']}, 'uniqueItems': True},
        'predicate_evidence': {'type': 'string', 'minLength': 1},
        'note': {'type': 'string'},
    }}
    clause['required'] = list(clause['properties'])
    return {'type': 'object', 'additionalProperties': False, 'required': ['preservation_note', 'unqueried_structure_note', 'clauses'],
            'properties': {'preservation_note': {'type': 'string', 'minLength': 1},
                           'unqueried_structure_note': {'type': 'string', 'minLength': 1},
                           'clauses': {'type': 'array', 'minItems': 1, 'maxItems': 12, 'items': clause},
                           'source_units': source_unit_schema()}}



def source_unit_schema():
    contract=read(CONTRACT_PATH)['features']
    unit={'type':'object','additionalProperties':False,'properties':{
        'text':{'type':'string','minLength':1},'occurrence':{'type':'integer','minimum':0},
        'kind':{'type':'string','minLength':1},'parent_index':{'type':['integer','null'],'minimum':0},
        'meaning':{'type':'string','minLength':1},
        'form_queries':{'type':'array','minItems':1,'maxItems':4,'items':{'type':'string','minLength':1,'maxLength':240}},
        'semantic_queries':{'type':'array','minItems':1,'maxItems':4,'items':{'type':'string','minLength':1,'maxLength':240}},
        'features':{'type':'object','additionalProperties':False,'properties':{
            k:{'enum':contract[k]['values']+[None]} for k in ['clause_relation','quotation_type']}}}}
    unit['required']=list(unit['properties'])
    return {'type':'array','maxItems':24,'items':unit}


def analysis_system():
    definitions = {k: v for k, v in read(CONTRACT_PATH)['features'].items()
                   if k not in TARGET_FIELDS | CANDIDATE_FIELDS}
    return '''표준어 발화의 입력 분석기다. 번역하거나 방언 표현을 제안하지 말고 JSON 객체 하나만 출력한다.
원문에서 확인할 수 있는 정보만 분석한다. KG 후보/목표 말투/정답/문장 ID는 제공되지 않는다.
1. 독립적인 종결 서술부마다 main을 만든다. 연결어미가 있는 앞절은 필요하면 connective로 추가한다.
main의 text는 연결절을 포함한 문장 전체여도 되지만 features는 해당 종결 서술부만 분석한다.
연결절의 text는 원문의 연속 부분 문자열이어야 한다. 인용·관형절·보조용언·조사·관용 구성 등은 source_units에 원문 부분 문자열로 따로 보존한다. 기존 clauses에 억지로 main/connective로 끼워 넣지 않는다. 분석하지 못한 부분만 unqueried_structure_note에 남긴다.
2. text는 띄어쓰기와 문장부호까지 그대로 복사한다. occurrence는 같은 문자열이 원문에 여러 번 나타날 때 0부터 세는 순번이다. 문자 위치와 식별자는 코드가 계산한다.
3. sentence_type은 문장 형식, speech_act는 발화 의도로 구별한다. 질문 형태의 부탁을 정보 질문으로 바꾸지 않는다.
question_type은 실제 의문 해석에만 쓴다. 선택 질문을 단순 의문사 질문으로 강제하지 않는다. 규격에 없는 기능은 null로 남긴다.
4. observed_politeness는 청자 높임이다. -시-/계시다는 주체 높임으로 별도 분석한다. 종결 표현에 나타난 높임을 사용한다.
연결절 자체에 청자 높임이 드러나지 않으면 unknown으로 둔다. 이후 종결절 높임을 연결절에 복사하지 않는다.
5. host_form은 해당 어미가 결합하는 서술부 바탕의 사전형이다. 보조용언·의존명사 구성이면 단순히 문장 첫 동사를 선택하지 않는다.
이다는 host_pos=copula, host_class=nominal_copula; 아니다는 host_class=negative_copula로 구분한다.
6. observed_prefinals는 해당 서술부에서 분석한 선어말어미를 앞에서 뒤 순서로 기록한다. -았-/-였-은 -었-으로 정규화한다.
선어말 없음이 확인되면 [], 확인 불가능하거나 지원되지 않는 형태가 있으면 null이다. 과거 사건을 뜻한다는 이유만으로 -었-을 만들어 넣지 않는다.
predicate_evidence에는 해당 분석의 근거가 되는 원문 서술부 문자열을 그대로 복사한다. '-ㄹ게'의 의지만 보고 '-겠-'이 있다고 분석하지 않는다.
7. features에는 정의된 입력 특징만 넣고, 근거 없는 항목은 생략하거나 null로 둔다. 표현의 자연스러움·지역·목표 높임·방언 활용형을 추측하지 않는다.
note에는 불확실한 분석을 적고, preservation_note에는 반드시 보존할 의미·부정·양태·의도를 적는다. 분석 범위가 제한되면 명시한다.
8. source_units에는 문장 전체와 그 안의 의미 있는 구성을 부모→자식 순으로 기록한다. kind는 자유로운 표준어 문법 설명이며 닫힌 분류에 맞추지 않는다. parent_index는 앞에 나온 부모의 0 기반 순번, 없으면 null이다. text/occurrence는 원문에 정확히 결속한다.
단어마다 잘게 나누는 것보다 변환에 필요한 구성을 보존한다. 인용 연결과 보고 서술어, 본용언과 보조용언, 관형형과 의존명사가 함께 의미를 이루면 그 전체를 하나의 상위 구성으로 반드시 남기고 필요한 하위 구성도 연결한다. 단순 주어·목적어·시간 부사는 별도 조회가 필요한 이유가 없으면 독립 단위로 늘리지 않는다.
form_queries는 원문 복사뿐 아니라 표준어 구성의 어휘 기본형·어미 결합 형태를 포함한다. 문법 용어는 검색용 가설로만 쓰며 관형절에 주절의 과거를 복사하지 않는다.
meaning에는 원문 의미만 기술한다. form_queries에는 표준어 구성의 기본형/문자열, semantic_queries에는 이 구성을 설명하는 검색용 풀이를 1~4개 적는다. 목표 방언형이나 정답을 추측해 검색어에 넣지 않는다. 인용 내용과 보고 서술부, 일반 행동 서술을 구별한다. 이 자유 설명은 검색용 가설이며 확정 문법 조건이 아니다.
9. source_units의 features에는 해당 원문 구성 자체의 clause_relation 또는 quotation_type을 규격값으로 기입한다. 판단할 수 없으면 null, 해당하지 않으면 {}로 둔다. 연결 구성의 관계를 설명문에만 남기지 않는다. 원문 구성의 의미를 분석하며 목표 방언·KG 요구값은 추측하지 않는다. 상위 문장의 높임/시제를 하위 구성에 복사하지 않는다.
입력 특징 정의:\n''' + json.dumps(definitions, ensure_ascii=False) + '\n출력 JSON schema:\n' + json.dumps(raw_schema(), ensure_ascii=False)


def locate(sentence, text, occurrence):
    starts = [i for i in range(len(sentence)) if sentence.startswith(text, i)]
    if occurrence >= len(starts):
        raise ValueError('clause text/occurrence does not bind to source')
    start = starts[occurrence]
    return [start, start + len(text)]


def candidate_assumptions(prefinals, host_pos):
    if prefinals is None:
        return {}
    if not prefinals:
        return {'prefinal_profile': 'none', **({'preceding_form': 'verb_stem_direct'} if host_pos == 'verb' else {})}
    if any(p in {'-었-', '-겠-', '-더-'} for p in prefinals):
        profile = 'switching_prefinal_present'
    else:
        profile = 'subject_honorific_only'
    return {'prefinal_profile': profile, 'preceding_form': prefinals[-1]}


def adapt(row, raw):
    jsonschema.validate(raw, raw_schema())
    clauses = []
    seen = set()
    for index, c in enumerate(raw['clauses'], 1):
        span = locate(row['standard'], c['text'], c['occurrence'])
        key = (tuple(span), c['role'])
        if key in seen:
            raise ValueError('duplicate clause span and role')
        seen.add(key)
        if c['predicate_evidence'] not in c['text']:
            raise ValueError('predicate evidence does not occur in clause')
        features = c['features']
        if c['role'] == 'main' and 'sentence_type' not in features:
            raise ValueError('main clause must supply sentence_type, possibly null')
        if c['role'] == 'connective' and 'clause_relation' not in features:
            raise ValueError('connective must supply clause_relation, possibly null')
        cid = row['id'] + ':c' + str(index)
        clauses.append({'clause_id': cid, 'predicate_complex_id': cid + ':predicate',
            'text': c['text'], 'span': span, 'role': c['role'], 'features': features,
            'observed_politeness': c['observed_politeness'],
            'observed_subject_honorific': c['observed_subject_honorific'],
            'tense_or_modality': c['tense_or_modality'],
            'preserved_candidate_features': candidate_assumptions(c['observed_prefinals'], features.get('host_pos')),
            'scope_note': c['note'], 'candidate_analysis_limit': '원문 선어말을 유지하는 가정이며 방언 활용형 선택의 정답이 아님.'})
    if not any(c['role'] == 'main' for c in clauses):
        raise ValueError('at least one main clause is required')
    item={'id':row['id'],'input':row['standard'],'preservation_note':raw['preservation_note'],
          'unqueried_structure_note':raw['unqueried_structure_note'],'clauses':clauses}
    if 'source_units' in raw:
        item['source_units']=[{'unit_id':row['id']+':u'+str(i+1),'text':u['text'],
            'span':locate(row['standard'],u['text'],u['occurrence']),
            **{k:u[k] for k in ['kind','parent_index','meaning','form_queries','semantic_queries','features'] if k in u}}
            for i,u in enumerate(raw['source_units'])]
    return normalize_analysis({'version': '1.2' if 'source_units' in raw else '1.1', 'origin': 'qwen_automatic_analysis_with_deterministic_adapter',
        'status': 'development_annotations_not_independent_gold', 'policy': deepcopy(POLICY),
        'items': [item]})


def dependencies():
    paths = [Path(__file__), BASE/'analysis_input.py', BASE/'run_manual_kg_development.py',
             BASE/'run_seeded_kg.py', BASE/'source_analysis_guard.py', BASE/'source_retrieval.py', GRAMMAR/'source_inventory.py', GRAMMAR/'source_evidence/summary.json', BASE/'requirements-analysis.txt', BASE/'inputs/development_30.config.json', BASE/'inputs/development_30.jsonl',
             BASE/'inputs/development_30.manual_analysis.json', CONTRACT_PATH, GRAMMAR/'query_review.py', GRAMMAR/'grammar.graph.json']
    return {str(p.relative_to(BASE.parent)): sha(p) for p in paths}


def assert_frozen(folder):
    if read(folder/'manifest.json')['dependencies'] != dependencies():
        raise ValueError('Inputs/code/KG changed since this run; start a new run')


def analyze_one(call, config, row, folder):
    path = folder/'analysis_requests'/(row['id']+'.json')
    messages = [{'role': 'system', 'content': analysis_system()}, {'role': 'user', 'content': row['standard']}]
    record = {'id': row['id'], 'input': row['standard'], 'attempts': [], 'status': 'failed'}
    for attempt in range(2):
        req = {'model': config['requested_model'], 'messages': deepcopy(messages), 'seed': SEED,
               'temperature': 0, 'top_p': 1, 'max_tokens': 4200,
               'chat_template_kwargs': {'enable_thinking': False}, 'response_format': {'type': 'json_object'}}
        audit = {'request': req}; start = time.monotonic()
        try:
            response = call('/chat/completions', req); audit['response'] = response
            content = check_response(response, config['requested_model'])
            raw = json.loads(content)
            if 'source_units' not in raw or not raw['source_units']:
                raise ValueError('source_units with source-bound constructions required for live analysis')
            normalized = adapt(row, raw)
            record.update(status='validated', raw_analysis=raw, normalized_analysis=normalized)
        except (ValueError, jsonschema.ValidationError) as error:
            # Repair only invalid structure/binding; never provide human reference or KG answers.
            audit['validation_error'] = str(error)[:2500]
            messages += [{'role': 'assistant', 'content': audit.get('response', {}).get('choices', [{}])[0].get('message', {}).get('content', '')},
                         {'role': 'user', 'content': 'JSON 검증 실패. 원문 분석을 규격에 맞게 다시 출력하세요. 오류: '+audit['validation_error']}]
        except Exception as error:
            audit.update(error_fields(error))
            audit['elapsed_seconds'] = round(time.monotonic()-start, 3)
            record['attempts'].append(audit); save(path, record)
            return record
        audit['elapsed_seconds'] = round(time.monotonic()-start, 3)
        record['attempts'].append(audit); save(path, record)
        if record['status'] == 'validated':
            break
    return record


def prepare(folder, call=None, config=None):
    assert_frozen(folder)
    rows = read(folder/'inputs.json'); graph = read(GRAMMAR/'grammar.graph.json')
    records = [read(folder/'analysis_requests'/(r['id']+'.json')) for r in rows]
    valid = [r for r in records if r['status'] == 'validated']
    if len(valid) != len(rows):
        raise ValueError('Some analyses failed; retained raw attempts. Do not silently fall back to manual input.')
    analysis = deepcopy(valid[0]['normalized_analysis'])
    analysis['items'] = [r['normalized_analysis']['items'][0] for r in valid]
    analysis = normalize_analysis(analysis)
    # Raw model annotations stay archived; all normal automatic retrieval uses source grounding.
    from source_analysis_guard import guard_analysis
    from importlib.metadata import version
    save(folder/'unguarded_analysis.json', analysis)
    analysis, source_audit = guard_analysis(analysis)
    analysis = normalize_analysis(analysis)
    save(folder/'source_guard_audit.json', source_audit)
    save(folder/'automatic_analysis.json', analysis)
    manual = normalize_analysis(read(BASE/'inputs/development_30.manual_analysis.json'))
    save(folder/'manual_analysis.json', manual)
    results = {}
    mode=read(folder/'manifest.json').get('retrieval_mode','function')
    if mode=='hybrid' and call is None:
        raise ValueError('Hybrid preparation requires explicit --execute for semantic review')
    if mode=='hybrid':
        from source_retrieval import SourceIndex,retrieve_broad
        source_index=SourceIndex()
    for name, value in [('manual', manual), ('automatic', analysis)]:
        results[name] = retrieve_broad(graph,value,source_index,call,config) if mode=='hybrid' else retrieve(graph,value)
        save(folder/(name+'_retrieval.json'), {'items': results[name]})
    comparison = []
    for m, a in zip(results['manual'], results['automatic']):
        def brief(x):
            return [{'clause_id': c['clause_id'], 'text': c['analysis']['text'], 'role': c['analysis']['role'],
                     'features': c['analysis']['features'], 'observed_politeness': c['analysis']['observed_politeness'],
                     'preserved_candidate_features': c['analysis']['preserved_candidate_features'],
                     'selected_assertion_ids': c['selected_assertion_ids'], 'analysis_gaps': c['analysis_gaps'],
                     'searched_functions': c['searched_functions']} for c in x['clauses']]
        comparison.append({'id': m['id'], 'input': m['input'], 'manual': brief(m), 'automatic': brief(a),
            'selected_ids_equal': {v for c in m['clauses'] for v in c['selected_assertion_ids']} ==
                                  {v for c in a['clauses'] for v in c['selected_assertion_ids']}})
    save(folder/'analysis_comparison.json', {'manual_is_not_gold': True, 'items': comparison})
    manifest = read(folder/'manifest.json')
    manifest.update(status='prepared_not_generated', analysis_validated=len(valid),
                    source_guard='source_morphology_guard_v1',
                    morphology_packages={n:version(n) for n in ['kiwipiepy','kiwipiepy_model']},
                    first_attempt_validated=sum(len(r['attempts']) == 1 for r in valid),
                    prepared_hashes={name:sha(folder/name) for name in ['automatic_analysis.json','manual_analysis.json','automatic_retrieval.json','manual_retrieval.json','unguarded_analysis.json','source_guard_audit.json']})
    save(folder/'manifest.json', manifest)


def translate_one(call, config, row, index, packets, folder):
    order = CONDITIONS[index % 3:] + CONDITIONS[:index % 3]
    for condition in order:
        path = folder/'translations'/(row['id']+'_'+condition+'.json')
        if path.exists():
            raise ValueError('Refusing to overwrite translation')
        packet = None if condition == 'no_kg' else packets[condition][row['id']]['prompt_packet']
        req = payload(config, row['standard'], SEED, packet)
        result = {'id': row['id'], 'condition': condition, 'input': row['standard'], 'request': req}
        start = time.monotonic()
        try:
            response = call('/chat/completions', req); result['response'] = response
            result['output'] = check_response(response, config['requested_model']); result['status'] = 'succeeded'
        except Exception as error:
            result.update(status='failed', **error_fields(error))
        result['elapsed_seconds'] = round(time.monotonic()-start, 3)
        save(path, result)
    return row['id']


def summarize(folder):
    manifest = read(folder/'manifest.json'); rows = read(folder/'inputs.json')
    items = []
    for row in rows:
        outputs = {c:read(folder/'translations'/(row['id']+'_'+c+'.json')) for c in CONDITIONS}
        items.append({'id': row['id'], 'input': row['standard'], 'conditions': outputs})
    manifest.update(completed=sum(o['status']=='succeeded' for i in items for o in i['conditions'].values()),
                    ended_at_utc=dt.datetime.now(dt.timezone.utc).isoformat())
    manifest['status'] = 'succeeded' if manifest['completed']==len(rows)*3 else 'partial_failure'
    save(folder/'manifest.json', manifest)
    report = {'manifest': manifest, 'analysis_comparison': read(folder/'analysis_comparison.json'), 'items': items,
              'evaluation': 'pending_exploratory_review_not_independent_native_speaker_evaluation'}
    save(folder/'comparison.json', report)
    durable = BASE/'archive/reports'/folder.name/'comparison.json'
    if durable.exists():
        raise ValueError('Refusing to overwrite durable comparison')
    save(durable, report)
    print(json.dumps({'status': manifest['status'], 'completed': manifest['completed'], 'comparison': str(durable)}, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['analyze', 'prepare', 'generate'])
    parser.add_argument('--folder', type=Path)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--workers', type=int, default=3)
    parser.add_argument('--retrieval', choices=['function','hybrid'], default='function')
    args = parser.parse_args()
    config = read(BASE/'inputs/development_30.config.json')
    if args.stage == 'prepare':
        call=connection()[0] if args.execute else None
        prepare(args.folder.resolve(),call,config); return
    if not args.execute:
        raise SystemExit('Use --execute for authorized model calls')
    call, endpoint_hash = connection()
    models = [m['id'] for m in call('/models')['data']]
    if config['requested_model'] not in models:
        raise ValueError('Requested Qwen unavailable')
    if args.stage == 'analyze':
        stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        folder = BASE/'archive/runs'/('automatic_kg_'+stamp)
        folder.mkdir(parents=True, exist_ok=False)
        (folder/'analysis_requests').mkdir(); (folder/'translations').mkdir()
        rows = [json.loads(line) for line in (BASE/'inputs/development_30.jsonl').read_text().splitlines()]
        save(folder/'inputs.json', rows)
        save(folder/'manifest.json', {'status':'analyzing', 'started_at_utc':stamp, 'dependencies':dependencies(),
            'endpoint_sha256':endpoint_hash, 'model':config['requested_model'], 'config':config, 'seed':SEED,
            'conditions':CONDITIONS, 'retrieval_mode':args.retrieval, 'workers':args.workers, 'generation_approved':False,
            'limitation':'Development inputs already seen; manual annotations are not gold. Single seed, no native-speaker evaluation. Provider checkpoint/quantization unverified.'})
        snapshot = folder/'snapshot'; snapshot.mkdir()
        for name in dependencies():
            dest=snapshot/name; dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes((BASE.parent/name).read_bytes())
        (folder/'analysis_system.txt').write_text(analysis_system())
        save(folder/'analysis_output.schema.json', raw_schema())
        print('RUN_FOLDER='+str(folder), flush=True)
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = [executor.submit(analyze_one, call, config, row, folder) for row in rows]
            for f in as_completed(futures):
                r=f.result(); print(r['id']+' analysis '+r['status'], flush=True)
        prepare(folder,call,config)
        print('READY_FOR_RETRIEVAL_REVIEW='+str(folder), flush=True)
    else:
        folder = args.folder.resolve(); assert_frozen(folder)
        manifest=read(folder/'manifest.json')
        if manifest['endpoint_sha256'] != endpoint_hash: raise ValueError('Endpoint changed')
        if manifest['status']!='prepared_not_generated': raise ValueError('Not prepared, or already generated')
        review=read(folder/'pre_generation_review.json')
        if review.get('status')!='reviewed_for_development_run': raise ValueError('Review retrieval first')
        if any(sha(folder/name)!=value for name,value in manifest['prepared_hashes'].items()):
            raise ValueError('Prepared inputs changed')
        manifest.update(status='generating', pre_generation_review_sha256=sha(folder/'pre_generation_review.json'))
        save(folder/'manifest.json',manifest)
        packets={name+'_analysis_kg':{i['id']:i for i in read(folder/(name+'_retrieval.json'))['items']} for name in ['manual','automatic']}
        rows=read(folder/'inputs.json')
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures=[executor.submit(translate_one,call,config,row,i,packets,folder) for i,row in enumerate(rows)]
            for f in as_completed(futures): print(f.result()+' three conditions saved',flush=True)
        summarize(folder)

if __name__ == '__main__':
    main()

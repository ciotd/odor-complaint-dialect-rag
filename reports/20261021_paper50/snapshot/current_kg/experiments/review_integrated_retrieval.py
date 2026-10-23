"""Pre-generation review: fresh automatic analysis, then frozen KG retrieval only.

New probes are development generalisation checks, not an independent test set.
No dialect answers or KG IDs are supplied to the analysis model.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
import csv
import json
from pathlib import Path

from run_auto_analysis_development import analyze_one, adapt
from source_analysis_guard import guard_analysis
from analysis_input import normalize_analysis
from run_seeded_kg import connection, read, save, sha, check_response
from integrated_retrieval import IntegratedRetriever, GRAMMAR

BASE = Path(__file__).resolve().parent
PROBES = [
    ('NEW01','지수가 내일 도서관에 간다고 했어요.'),
    ('NEW02','지수가 어제 청소를 했어요.'),
    ('NEW03','누가 그 상자를 옮겼어?'),
    ('NEW04','네가 그 상자를 옮겼어?'),
    ('NEW05','누가 그 상자를 옮겼어요?'),
    ('NEW06','버스를 기다리는 동안 음악을 들었어요.'),
    ('NEW07','상자를 옮기다가 잠깐 쉬었어요.'),
    ('NEW08','안내원이 이쪽으로 들어오라고 하셨어요.'),
]
CONFIRMATION_PROBES = [
    ('NEW01','형이 모레 부산에 간다고 했어요.'),
    ('NEW02','형이 아침에 운동을 했어요.'),
    ('NEW03','어디에서 그 우산을 샀어?'),
    ('NEW04','여기에서 그 우산을 샀어?'),
    ('NEW05','어디에서 그 우산을 샀어요?'),
    ('NEW06','학교로 걸어가는 동안 전화를 받았어요.'),
    ('NEW07','설거지를 하다가 잠시 앉았어요.'),
    ('NEW08','직원이 저쪽에서 기다리라고 하셨어요.'),
]


def analyze(folder,confirmation=False,inputs=None):
    folder.mkdir(parents=True,exist_ok=False)
    (folder/'analysis_requests').mkdir()
    rows=([json.loads(line) for line in inputs.read_text().splitlines() if line.strip()] if inputs
          else [{'id':sid,'standard':text} for sid,text in (CONFIRMATION_PROBES if confirmation else PROBES)])
    save(folder/'inputs.json',rows)
    config=read(BASE/'inputs/development_30.config.json')
    save(folder/'config.json',config)
    for name in ['run_auto_analysis_development.py','source_analysis_guard.py','source_bindings.py','integrated_retrieval.py','analysis_input.py',Path(__file__).name]:
        (folder/name).write_bytes((BASE/name).read_bytes())
    (folder/'analysis_contract.json').write_bytes((GRAMMAR/'analysis_contract.json').read_bytes())
    call,endpoint=connection()
    save(folder/'analysis_manifest.json',{'status':'running','endpoint_sha256':endpoint,
         'inputs_sha256':sha(folder/'inputs.json'),'graph_sha256':sha(GRAMMAR/'grammar.graph.json'),
         'translation_calls':0,'purpose':'unseen_sentence_development_retrieval_probes_not_evaluation_gold'})
    results=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(analyze_one,call,config,row,folder) for row in rows]
        for f in as_completed(futures):
            r=f.result();results.append(r)
            print(r['id'],r['status'],flush=True)
    finish_analysis(folder,rows,results)


def finish_analysis(folder,rows,results):
    if any(r['status']!='validated' for r in results):
        m=read(folder/'analysis_manifest.json');m.update(status='analysis_validation_failed',
            analysis_calls=sum(len(r['attempts']) for r in results));save(folder/'analysis_manifest.json',m)
        raise ValueError('Analysis failed; no manual fallback')
    by={r['id']:r for r in results}
    value=by[rows[0]['id']]['normalized_analysis']
    value['items']=[by[r['id']]['normalized_analysis']['items'][0] for r in rows]
    save(folder/'model_analysis.json',value)
    guarded,audit=guard_analysis(value)
    save(folder/'analysis.json',normalize_analysis(guarded));save(folder/'source_guard.json',audit)
    m=read(folder/'analysis_manifest.json');m.update(status='analyzed_not_generated',analysis_calls=sum(len(r['attempts']) for r in results))
    save(folder/'analysis_manifest.json',m)


def resume(folder):
    """At most two additional schema repairs using only the recorded validation error."""
    from copy import deepcopy
    import jsonschema
    rows=read(folder/'inputs.json');config=read(folder/'config.json');call,_=connection()
    results=[]
    for row in rows:
        path=folder/'analysis_requests'/(row['id']+'.json');r=read(path)
        while r['status']!='validated' and len(r['attempts'])<4:
            last=r['attempts'][-1]
            if 'validation_error' not in last or 'response' not in last:
                break
            req=deepcopy(last['request'])
            req['messages'] += [
                {'role':'assistant','content':check_response(last['response'],config['requested_model'])},
                {'role':'user','content':'JSON 검증 실패. 원문 분석을 규격에 맞게 다시 출력하세요. 오류: '+last['validation_error']}]
            attempt={'request':req}
            response=call('/chat/completions',req);attempt['response']=response
            try:
                raw=json.loads(check_response(response,config['requested_model']))
                if not raw.get('source_units'):raise ValueError('source_units required')
                value=adapt(row,raw)
                r.update(status='validated',raw_analysis=raw,normalized_analysis=value)
            except (ValueError,jsonschema.ValidationError) as error:
                attempt['validation_error']=str(error)[:2500]
            r['attempts'].append(attempt);save(path,r)
            print(row['id'],r['status'],'attempts='+str(len(r['attempts'])),flush=True)
        results.append(r)
    finish_analysis(folder,rows,results)


def retrieve(folder):
    from embedding_retrieval import EmbeddingIndex
    idx=EmbeddingIndex();engine=IntegratedRetriever(read(GRAMMAR/'grammar.graph.json'),idx)
    results=engine.retrieve(read(folder/'analysis.json'))
    save(folder/'retrieval.json',results)
    save(folder/'retrieval_manifest.json',{'graph_sha256':sha(GRAMMAR/'grammar.graph.json'),
         'analysis_sha256':sha(folder/'analysis.json'),'embedding_model':idx.model_selection,
         'index_sha256':idx.fingerprint,'code_sha256':{n:sha(BASE/n) for n in ['integrated_retrieval.py','source_bindings.py','analysis_input.py','embedding_retrieval.py']},
         'translation_calls':0,'status':'retrieved_not_generated'})
    for r in results:
        print(r['id'],r['input'],','.join(c['id'] for c in r['packets']['graph_hybrid']['references']),flush=True)


def report(dev_folder,probe_folder,out):
    dev=read(dev_folder/'retrieval.json')
    results=[r['integrated_retrieval'] for r in dev]+read(probe_folder/'retrieval.json')
    out.mkdir(parents=True,exist_ok=True)
    lines=['통합 조회 — 생성 전 점검 (번역 결과 아님)',
           '기존 30문장: 저장된 자동 분석 재사용. 신규 8문장: Qwen 자동 분석 + 원문 형태 확인.',
           '신규 문장도 개발 진단 자료이며 독립 평가셋/자연스러움 검증이 아니다.','']
    checks=[];reasons=Counter();empty=[]
    with (out/'retrieval_integration.tsv').open('w') as f:
        w=csv.writer(f,delimiter='\t');w.writerow(['id','standard','binding','source_text','features','selected_assertions','graph_edge_ids','rejection_reasons'])
        for r in results:
            lines += [r['id']+' '+r['input']]
            cards=r['packets']['graph_hybrid']['references']
            if not cards:empty.append(r['id'])
            decisions={(d['assertion_id'],d['binding_id']):d for d in r['decisions']}
            for c in cards:
                d=decisions[c['id'],c['binding_id']]
                checks.append({'id':r['id'],'assertion':c['id'],'binding':c['binding_id'],
                               'pass':d['eligible'] and any(not s['reasons'] for s in d['scenarios']) and c['conditions']['status']=='match'})
            for v in r['bindings']:
                selected=[c['id'] for c in cards if c['binding_id']==v['id']]
                paths=[e['id'] for p in r['packets']['graph_hybrid']['graph_paths'] if p['binding_id']==v['id'] for e in p['edges']]
                why=Counter(reason for d in r['decisions'] if d['binding_id']==v['id'] and not d['eligible']
                            for s in d['scenarios'] for reason in s['reasons'])
                reasons.update(why)
                w.writerow([r['id'],r['input'],v['id'],v['text'],json.dumps(v['features'],ensure_ascii=False),','.join(selected),','.join(dict.fromkeys(paths)),json.dumps(why,ensure_ascii=False)])
                if selected or v['features'].get('source_form'):
                    lines += ['  위치: '+v['text']+' '+str(v['span']),
                              '  분석: '+json.dumps(v['features'],ensure_ascii=False),
                              '  전달: '+(', '.join(selected) or '없음 — 조건/적용 위치 미충족 또는 분량 제한'),
                              '  관계: '+(', '.join(dict.fromkeys(paths)) or '직접 발견 경로')]
            lines+=['']
    by={r['id']:r for r in results}
    def selected(sid):return {c['id'] for c in by[sid]['packets']['graph_hybrid']['references']}
    def forms(sid):return {c['relation']['subject'].get('text') for c in by[sid]['packets']['graph_hybrid']['references']}
    probes={
        'quote_contraction_reached':'GYS-O004:A5' in selected('NEW01'),
        'lexical_hada_not_quote':'GYS-O004:A5' not in selected('NEW02'),
        'content_no': '-노' in forms('NEW03') and '-나' not in forms('NEW03'),
        'polar_na': '-나' in forms('NEW04') and '-노' not in forms('NEW04'),
        'polite_not_bare_no_na':not forms('NEW05') & {'-노','-나'},
        'modifier_not_daga':'GYS-R045:A1' not in selected('NEW06'),
        'transition_reached':'GYS-R045:A1' in selected('NEW07'),
        'command_quote_not_statement':'GYS-R007:A1' not in selected('NEW08') and 'GYS-O004:A5' in selected('NEW08'),
    }
    summary={'status':'pre_generation_retrieval_checked' if all(c['pass'] for c in checks) and all(probes.values()) else 'review_gaps_found',
             'items':len(results),'existing_development':len(dev),'new_automatic_probes':len(results)-len(dev),
             'sent_cards':len(checks),'all_sent_cards_match':all(c['pass'] for c in checks),'new_probe_checks':probes,
             'zero_candidate_items':empty,'rejection_scenario_counts':dict(reasons),'translation_calls':0,
             'development_run':str(dev_folder),'probe_run':str(probe_folder),
             'same_record_graph_cards':sum(r['packets']['record_hybrid']['references']==r['packets']['graph_hybrid']['references'] for r in dev),
             'same_record_graph_packets':sum(r['packets']['record_hybrid']==r['packets']['graph_hybrid'] for r in dev),
             'first_probe_run':'integrated_probes_20261008: development failure preserved; used to repair typed source-unit binding',
             'limits':['Supported morphological bindings are partial.','Semantic similarity is not application approval.',
                       'Condition match is against supplied analysis, which can be semantically wrong.',
                       'No automatic dialect inflection synthesis.','No translation quality claim.']}
    # Full rankings/conditions already live in immutable run artifacts; do not
    # scatter a second 40+ MB copy among the human-facing reports.
    save(out/'retrieval_integration.json',{'summary':summary,'packet_checks':checks,
         'full_audit_artifacts':[{'path':str(p),'sha256':sha(p)} for p in [
             dev_folder/'retrieval.json',dev_folder/'jobs.json',dev_folder/'protocol.json',
             probe_folder/'retrieval.json',probe_folder/'analysis.json',probe_folder/'retrieval_manifest.json']]})
    overview=['조회 통합 최종 점검 — 번역 생성 0회',
              f"기존 30문장 + 수정 후 신규 8문장. 신규 대조 {sum(probes.values())}/8 충족.",
              '전달 카드의 조건 일치는 입력 분석값에 대한 판정이며 그 분석값의 의미 정확성을 보장하지 않음.',
              '기존 30문장 C/D 선택 카드 동일: '+str(summary['same_record_graph_cards'])+'건; 전체 패킷 동일: '+str(summary['same_record_graph_packets'])+'건.',
              '후보 없음: '+', '.join(empty),
              '신규 대조 결과: '+json.dumps(probes,ensure_ascii=False),
              '실패한 대조는 분석/조회 한계로 남김. 문장별 정답으로 분석값을 덮어쓰지 않음.','']
    (out/'retrieval_integration.txt').write_text('\n'.join(overview+lines)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['analyze','resume','retrieve','report'])
    p.add_argument('--folder',type=Path,required=True);p.add_argument('--dev-folder',type=Path)
    p.add_argument('--inputs',type=Path)
    p.add_argument('--confirmation',action='store_true')
    p.add_argument('--out',type=Path,default=BASE/'reports/source_expansion');a=p.parse_args()
    if a.mode=='analyze':analyze(a.folder,a.confirmation,a.inputs)
    elif a.mode=='resume':resume(a.folder)
    elif a.mode=='retrieve':retrieve(a.folder)
    else:report(a.dev_folder,a.folder,a.out)

if __name__=='__main__':main()

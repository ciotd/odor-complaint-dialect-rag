"""Visible development diagnostic for the extended analysis and source/KG retrieval.

No per-sentence KG seeds or target forms. Original requests/responses are preserved.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
import datetime as dt
import json
from pathlib import Path
from threading import Lock

from run_auto_analysis_development import analyze_one,SEED
from source_analysis_guard import guard_analysis
from analysis_input import normalize_analysis
from run_seeded_kg import connection,read,save,sha,payload,check_response,error_fields
from source_retrieval import SourceIndex,retrieve_broad

BASE=Path(__file__).resolve().parent
GRAMMAR=BASE.parent/'grammar'
REPORTS=BASE/'reports/source_expansion'
LOCK=Lock()
# Diagnostic cases, not evaluation gold. Four familiar controls + four new probes.
DEFAULT_INPUTS=[
 {'id':'CONTROL01','standard':'너 어제 뭐했어?'},
 {'id':'CONTROL02','standard':'너 오늘 아침에 국밥 먹었어?'},
 {'id':'CONTROL03','standard':'동생이 오늘은 늦게 온다고 했어.'},
 {'id':'CONTROL04','standard':'집에 가는 길에 빵을 샀어.'},
 {'id':'PROBE01','standard':'민수가 내일 회의에 못 온다고 했어요.'},
 {'id':'PROBE02','standard':'어제 저녁에 숙제를 했어요.'},
 {'id':'PROBE03','standard':'비가 와도 약속 장소에 갈 거예요.'},
 {'id':'PROBE04','standard':'친구가 올 때까지 책을 읽었어요.'},
]


def event(message):
    with LOCK:
        line='[확장 조회] '+message
        print(line,flush=True)
        REPORTS.mkdir(parents=True,exist_ok=True)
        with (REPORTS/'progress.txt').open('a') as f:f.write(line+'\n')


def execute_one(row,call,config,graph,index,folder,translate):
    event(row['id']+' 원문: '+row['standard'])
    result={'id':row['id'],'input':row['standard']}
    analysis=analyze_one(call,config,row,folder)
    result['analysis']=analysis
    if analysis['status']!='validated':
        event(row['id']+' 분석 실패 — 실패 기록 보존, 수동 분석으로 대체하지 않음')
        save(folder/'items'/(row['id']+'.json'),result);return result
    value,audit=guard_analysis(analysis['normalized_analysis']);value=normalize_analysis(value)
    result.update(guarded_analysis=value,source_guard_audit=audit)
    units=value['items'][0].get('source_units',[])
    event(row['id']+' 원문에 결속한 구성: '+' / '.join(u['text']+' ['+u['kind']+']' for u in units))
    retrieval=retrieve_broad(graph,value,index,call,config)[0];result['retrieval']=retrieval
    status=retrieval['extended_retrieval']['semantic_review']['status']
    event(row['id']+' 의미 관련성 검토: '+status)
    for b in retrieval['prompt_packet']['additional_source_references']:
        evidence=b['retrieval_evidence']
        decision=next(v for v in retrieval['extended_retrieval']['semantic_review']['selected'] if v['id']==evidence['id'] and v['input_unit_id']==evidence['input_unit_id'])
        event(row['id']+' '+evidence['id']+' → 모델 관련성 추정: '+decision['reason']+' | 원문 인용: '+evidence['evidence_quote'][:100].replace('\n',' '))
    if translate and status!='validated_relevance_hypotheses':
        result['translation']={'status':'not_generated_retrieval_review_failed'}
        event(row['id']+' 관련성 검토 실패로 생성 보류; 기본 후보만으로 조용히 대체하지 않음')
    elif translate:
        req=payload(config,row['standard'],SEED,retrieval['prompt_packet']);result['translation']={'request':req}
        try:
            response=call('/chat/completions',req)
            result['translation'].update(response=response,output=check_response(response,config['requested_model']),status='succeeded')
            event(row['id']+' 생성 원문: '+result['translation']['output'])
        except Exception as error:
            result['translation'].update(status='failed',**error_fields(error));event(row['id']+' 생성 실패, 기록 보존')
    save(folder/'items'/(row['id']+'.json'),result)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true');p.add_argument('--translate',action='store_true')
    p.add_argument('--inputs',type=Path);p.add_argument('--workers',type=int,default=2);args=p.parse_args()
    rows=[json.loads(l) for l in args.inputs.read_text().splitlines()] if args.inputs else DEFAULT_INPUTS
    if not args.execute:print(json.dumps({'inputs':rows,'network_called':False},ensure_ascii=False,indent=2));return
    stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder=BASE/'archive/runs'/('source_expansion_'+stamp);folder.mkdir(parents=True)
    index=SourceIndex();graph=read(GRAMMAR/'grammar.graph.json');config=read(BASE/'inputs/development_30.config.json')
    call,endpoint_hash=connection()
    deps=[Path(__file__),BASE/'source_retrieval.py',BASE/'analysis_input.py',BASE/'run_auto_analysis_development.py',BASE/'source_analysis_guard.py',BASE/'run_manual_kg_development.py',BASE/'run_seeded_kg.py',GRAMMAR/'grammar.graph.json',GRAMMAR/'source_inventory.py',GRAMMAR/'source_evidence/summary.json']
    report={'run_id':stamp,'mode':'development_diagnostic_not_controlled_quality_comparison','config':config,
            'seed':SEED,'endpoint_sha256':endpoint_hash,'source_inventory':index.summary,'status':'running',
            'dependencies':{str(x.relative_to(BASE.parent)):sha(x) for x in deps},'items':[]}
    for path in deps:
        dest=folder/'snapshot'/path.relative_to(BASE.parent);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(path.read_bytes())
    save(folder/'inputs.json',rows);save(folder/'manifest.json',report)
    event('시작 '+stamp+' / 원문과 근거를 보존하는 개발 진단')
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures={pool.submit(execute_one,row,call,config,graph,index,folder,args.translate):row for row in rows}
        for f in as_completed(futures):
            try:report['items'].append(f.result())
            except Exception as error:
                row=futures[f];report['items'].append({'id':row['id'],'input':row['standard'],'status':'failed',**error_fields(error)})
                event(row['id']+' 처리 실패: '+type(error).__name__)
            save(folder/'manifest.json',report)
    positions={row['id']:i for i,row in enumerate(rows)};report['items'].sort(key=lambda r:positions[r['id']])
    report['status']='completed' if all(x.get('retrieval',{}).get('extended_retrieval',{}).get('semantic_review',{}).get('status')=='validated_relevance_hypotheses' and (not args.translate or x.get('translation',{}).get('status')=='succeeded') for x in report['items']) else 'partial_failure'
    report['ended_at_utc']=dt.datetime.now(dt.timezone.utc).isoformat()
    save(folder/'manifest.json',report)
    out=REPORTS/('retrieval_'+stamp+'.json');save(out,report)
    lines=['원문 구성·KG·문헌 확장 조회 개발 진단',report['status'],
           '기존 기능 조회 + 원문 형태/설명 질의의 어휘 검색 + Qwen 의미 관련성 검토.',
           '의미 검토는 후보 24개 내에서 수행. 조건 충족·자연스러움·전체 문헌 검수 완료를 뜻하지 않음.','']
    for x in report['items']:
        lines += [x['id']+' '+x['input']]
        if 'retrieval' not in x:lines+=['처리 실패',''];continue
        r=x['retrieval']
        lines += ['기존 기능 후보: '+', '.join(v for c in r['clauses'] for v in c['selected_assertion_ids'])]
        for u in r['extended_retrieval']['input_units']:lines+=['입력 구성: '+u['text']+' | '+u['kind']+' | '+u['meaning']]
        for b in r['prompt_packet']['additional_source_references']:
            e=b['retrieval_evidence'];lines+=['추가 근거: '+e['id']+' | 적용 승인 아님','원문 인용: '+e['evidence_quote']]
        lines+=['분량 제한으로 제외: '+json.dumps(r['extended_retrieval']['omitted'],ensure_ascii=False)]
        if 'translation' in x:lines+=['생성 원문: '+x['translation'].get('output','실패')]
        lines+=['']
    out.with_suffix('.txt').write_text('\n'.join(lines)+'\n')
    event('완료 '+report['status']+' / '+str(out.relative_to(BASE.parent)))


if __name__=='__main__':main()

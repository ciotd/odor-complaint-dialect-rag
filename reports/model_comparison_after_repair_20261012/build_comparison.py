"""Reproduce the aligned comparison from frozen outputs; no generation calls."""
import csv
import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
LATEST = ROOT / 'reports/kg_v2_pipeline_repair_20261012'
PEERS = ROOT / 'reports/model_comparison_20261012/comparison.json'

# Qualitative observations, not human gold labels or an accuracy rubric.
NOTES = {
 'DEV001': '세 결과 모두 좋네예. Qwen은 오늘→올, Sonnet은 참→억수로를 선택한다. 어휘 선택과 강조 정도의 차이를 문법 오류와 구분한다.',
 'DEV002': 'Astra는 가는을 보존한다. Sonnet은 가는→오는으로 이동 관점을 바꾼다. Qwen은 1회 보존 재검토 후 원문과 완전히 같다. 동일 출력 자체가 비문이라는 뜻은 아니다.',
 'DEV003': '세 결과가 완전히 같다: 이 음식은 생각보다 맵네예. 국소적 높임 종결 변환은 최신 Qwen도 수행한다.',
 'DEV004': 'Astra와 Qwen은 제 친구라예로 일치한다. Sonnet은 내 친구라예로 바꾸어 원문의 겸양 제를 유지하지 않는다.',
 'DEV005': 'Astra와 Sonnet은 좋아→좋다. Qwen은 원문 유지. 세 표현의 방언 자연스러움 우열은 별도 화자 평가가 필요하다.',
 'DEV006': 'Astra와 Qwen은 할머니를 문장의 주체로 유지한다. Sonnet은 할매요라는 호격으로 바꾼다. Qwen의 시고 계셔예는 어휘 실현 및 지역 적합성 검토가 필요하며, 주체 높임 표지는 남아 있다.',
 'DEV007': 'Astra는 안 묵었다, Sonnet은 안 먹었다, Qwen은 안 묵었어. 부정·과거는 보존하고 어휘와 종결 선택이 다르다.',
 'DEV008': 'Astra/Sonnet은 마이 와가, Qwen은 마이 와서. Qwen은 너무라는 명시적 정도 표현을 생략한다. 못/몬 부정과 높임은 남아 있다.',
 'DEV009': 'Astra/Sonnet은 아이다. Qwen은 원문 그대로이고 이번 조회 references도 0개이다. KG 전체에 관련 정보가 없다는 결론은 이 기록만으로 낼 수 없다.',
 'DEV010': 'Astra 같아예, Sonnet 같심더, Qwen 같어예. 추정·가능성은 유지되며 높임 말투와 모음 실현이 다르다. 특정 표기만으로 정오를 단정하지 않는다.',
 'DEV011': 'Astra와 Qwen은 출발했나예로 일치한다. Sonnet은 출발했는교. 의문·과거·높임을 함께 비교해야 한다.',
 'DEV012': '세 결과 모두 뒀노. Qwen만 목적격 조사를 유지한다. 조사 생략은 이 사례에서 핵심 의미 차이를 만들지 않는다.',
 'DEV013': 'Astra 될까예, Qwen 낼…될까예로 높임 질문을 유지한다. Sonnet 되겠노는 원문의 청자 높임 유지 여부가 문제다.',
 'DEV014': '세 결과 모두 안 했노. Astra/Sonnet은 왜→와, Qwen은 왜를 유지한다. 선택적 어휘 치환의 차이다.',
 'DEV015': 'Astra 누구 꺼라예, Sonnet 누구 껀교, Qwen 누구 거여. Qwen의 명사 의문문 종결과 높임 해석을 추가 검토해야 한다. 여라는 표면형만으로 무조건 비높임으로 처리하지 않는다.',
 'DEV016': 'Astra/Sonnet은 가는 기가/돌아가는 기가 구조를 쓴다. Qwen은 가노/돌아가노로 단순화한다. 선택질문의 기능 및 종결어미 분포를 검토할 대상이다. 이번 전달 후보는 지금/너 어휘 대응뿐이다.',
 'DEV017': 'Astra/Sonnet 주이소, Qwen 주세예. Qwen의 제한된 종결 조합 정책이 반영된 차이이며 주세예를 자동 오류로 분류하지 않는다.',
 'DEV018': 'Astra와 Qwen은 도와줄래를 유지하고 것→거만 바꾼다. Sonnet은 도와주끼가. 요청의 행동 주체·의향 해석은 화자 검토 대상이며, 변환량 자체로 우열을 매기지 않는다.',
 'DEV019': 'Astra/Sonnet 걸으이소, Qwen 걸으세예. Astra는 미끄러우니께도 사용한다. 명령의 높임을 유지하면서 연결어미와 말투가 다르다.',
 'DEV020': 'Astra/Sonnet은 딴 사람…하지 마라. Qwen은 원문 유지. 금지 의미는 모두 남아 있다.',
 'DEV021': 'Astra/Sonnet은 기다려/기다리 주이소, Qwen은 기다려 주세예. 세 결과 모두 제가를 유지하고 마지막을 볼게예/보께예로 변환한다.',
 'DEV022': 'Astra/Sonnet 묵자, Qwen 묵제. 이번 조회에 JO2018 청유형 -자→-제/-제이가 있으므로 묵제를 단순 화행 오류로 취급하면 안 된다. 지역·화자 적합성은 별도다.',
 'DEV023': 'Astra 괜찮아예, Sonnet 괜찮심더, Qwen 아팄는데…개찮어예. Qwen은 어휘·음운 표기까지 더 바꾸며 해당 실현의 적합성은 확인이 필요하다. 생소함만으로 오류 판정하지 않는다.',
 'DEV024': 'Astra/Sonnet은 도착할…기다리라. Qwen은 올…기다려. 도착을 오다로 바꾼 이동 관점은 문맥 의존적이며, 의미 등가성을 추가 확인할 대상이다.',
 'DEV025': 'Astra/Sonnet은 해도 된다, Qwen은 낼 해도 돼. 허용 의미를 유지하고 서로 다른 구간을 변환한다.',
 'DEV026': 'Astra 나왔어예, Sonnet 나왔심더, Qwen 나왔어예. Qwen 늦으까와 Sonnet 늦을까 싶어가는 서로 다른 실현이며 지역별 자연스러움은 미확정이다.',
 'DEV027': 'Astra 온다 캤다, Sonnet 온다 카더라, Qwen 온다고 했어. Qwen에는 오늘→올 한 후보만 전달되었다. 인용·보고 구성의 변환 근거 전달 누락이 확인된다. Sonnet 회상 말투가 원문과 완전히 동일한 정보인지는 별도다.',
 'DEV028': '세 결과 모두 부정·과거·높임을 유지한다. Astra는 버리라는→버리라 카는 구성을 바꾸고, Qwen과 Sonnet은 주로 마지막 종결을 바꾼다.',
 'DEV029': 'Astra는 원문과 같다. Sonnet은 조사 일부를 생략하고 Qwen은 괜찮더라→갠찮더라. 원문 동일 여부는 곧 번역 실패 여부가 아니다.',
 'DEV030': 'Astra 자라, Sonnet 자라/하께, Qwen 원문 그대로. 명령·의향 의미는 모두 유지한다. 최신 Qwen의 방언 표현 선택 폭이 작은 사례다.',
 'LONG001': 'Astra/Sonnet은 만나자 캤는데와 고파가 등 구성을 변환한다. Qwen은 만나자고 했는데를 유지하고 지금 짐을 중복 생성한다. 지금→짐 대응은 실제 전달되었다. 앞에는 시간 용법 문헌 근거가 있어 자동 오류가 아니다.',
 'LONG002': 'Astra 묵어 봤나, Sonnet 무 봤나, Qwen 묵어 봤어. Qwen 맛있대는 문헌의 회상 -대 가능성을 반영해야 하며 표면형만 보고 전언으로 바뀌었다고 판단하지 않는다.',
 'LONG003': 'Astra/Qwen은 제가 유지, Sonnet은 내가로 변경. Qwen 잘 못→모는 정도 표현 잘의 생략과 방언 부정형 해석을 따로 검토해야 한다. 요청 종결은 주이소 대 주세예로 다르다.',
 'LONG004': 'Astra/Qwen은 제가와 모셔다드리다를 유지한다. Sonnet은 내가로 바꾼다. Qwen 이빠이의 대화 상황 적합성은 추가 검토 대상이며 출처 없는 오타로 단정할 수 없다.',
 'LONG005': 'Astra/Sonnet은 온다 캤다, 묵을라 카는데 등 복합 구성을 바꾼다. Qwen은 온다고 했어/묵으려고 하는데로 남는다. 전달 목록에 해당 인용·의도 구성의 후보가 없다. 먼저→앞에는 문헌에 시간 용법이 있다.',
 'LONG006': 'Astra는 가는 길을 유지한다. Sonnet은 오는 길로 이동 관점을 바꾼다. Qwen은 가노 길로 관형절 구조를 손상시킨다. 보존 지침이 입력에 있고 검사도 탐지했지만 1회 재검토 결과가 동일했다.',
 'LONG007': '세 결과 모두 찾고 있노. Sonnet은 놨다 아이가/봐라까지 바꾸고 Qwen은 정지 등 어휘를 바꾼다. 정지의 생소함과 오류 여부를 혼동하지 않는다.',
 'LONG008': 'Astra 힘드셨지예, Sonnet 힘들었지예, Qwen 힘드셨죠. Sonnet은 주체 높임 및 제가→내가의 겸양을 줄인다. Qwen은 -죠→-지예 후보를 전달받았으나 사용하지 않았다. 따라서 후보 부재만으로 설명할 수 없다.',
}

def read(path):
    return json.loads(path.read_text())

latest = {r['id']: r for r in read(LATEST / 'final_outputs.json')}
peers = read(PEERS)
retrieval = {r['id']: r for r in read(LATEST / 'retrieval.json')}
jobs = {r['id']: r for r in read(LATEST / 'jobs.json')}
assert len(peers) == len(NOTES) == 38
rows = []
for old in peers:
    key = old['id']
    new = latest[key]
    assert old['standard'] == new['input']
    assert new['status'] == 'success'
    row = dict(id=key, standard=old['standard'],
               astra=old['outputs']['astra_high_no_kg'],
               sonnet=old['outputs']['sonnet_user_supplied'],
               qwen_latest=new['output'], review=NOTES[key],
               qwen_repair_attempted=new['repair_attempted'],
               qwen_selection=new['selection'])
    rows.append(row)

stats = {'matched_inputs': len(rows), 'short_inputs': 30, 'long_inputs': 8,
         'excluded_latest_inputs_without_peer_outputs': len(latest) - len(rows),
         'measurement': 'Exact Python string equality; descriptive only, not accuracy.'}
stats['unchanged_from_source'] = {
    model: [r['id'] for r in rows if r[model] == r['standard']]
    for model in ['astra', 'sonnet', 'qwen_latest']}
stats['qwen_exact_agreement_with'] = {
    model: [r['id'] for r in rows if r[model] == r['qwen_latest']]
    for model in ['astra', 'sonnet']}

diagnostics = []
for key in ['DEV009', 'DEV016', 'DEV022', 'DEV027', 'LONG001', 'LONG005', 'LONG006', 'LONG008']:
    packet = retrieval[key]['packets']['v2_graph']
    payload = json.loads(jobs[key]['request']['messages'][-1]['content'].split('\n', 1)[1])
    diagnostics.append({
        'id': key,
        'selected_candidates': [
            {k: f.get(k) for k in ['id', 'source_pattern', 'target_pattern',
                                    'input_binding', 'retrieval_route', 'origin']}
            for f in packet['references']],
        'actual_generation_transformation_plan': payload['transformation_plan'],
        'actual_generation_preservation': payload['preservation'],
        'first_check': latest[key]['first_check'],
        'final_check': latest[key]['final_check'],
        'repair_output': latest[key].get('repair_output'),
        'interpretation': NOTES[key],
    })

summary = '''최신 KG 파이프라인 결과와 Astra·Claude Sonnet 비교 (2026-10-12)

비교 범위와 조건
기존 공통 DEV 30개 + LONG 8개, 총 38개 입력을 원문 문자열로 대조했다. LONG은 여러 문장으로 이루어진 입력이다. 최신 70개 중 동등한 두 모델 출력이 없는 32개는 제외했다. Qwen은 final_outputs.json의 최종 선택 output을 사용했다. 이 작업에서 재생성이나 생산 코드 수정은 하지 않았다.
Astra는 외부 근거 없이 요청된 gpt-6-astra/high의 38개 일괄 출력이다. 원시 사전학습 체크포인트 실험이 아니다. Sonnet은 사용자 제공 출력으로 프롬프트·세부 설정을 검증하지 못했다. Qwen은 분석·KG·모델 조언·변환 계획·제한적 보존 재검토를 포함하는 시스템 출력이다. 모델·프롬프트·배치 방식·재검토가 다르므로 KG 효과만을 분리한 비교가 아니다. 세 모델의 출력 모두 방언 화자가 검증한 정답이 아니다.

관찰된 차이
1. 국소적 높임 종결의 격차는 일부 줄었다. 맵네예(DEV003), 제 친구라예(DEV004), 출발했나예(DEV011)에서 최신 Qwen과 Astra 출력이 완전히 같다. 단, 동일 결과가 곧 화자 평가 통과를 뜻하지 않는다.
2. Qwen의 부족함은 어휘 치환뿐 아니라 구성 단위에서 두드러진다. 온다고 했어→온다 캤다, 먹으려고 하는데→묵을라 카는데처럼 인용부와 보고 동사, 의도 표현 전체를 함께 처리하는 변환이 최신 출력에서는 부족하다. DEV027/LONG005의 실제 전달 목록에서도 해당 구성 후보가 없다.
3. 후보가 있어도 적용이 안정적이지 않다. LONG008에는 -죠→-지예와 선어말어미 보존 지침을 실제로 전달했지만 힘드셨죠가 남았다. LONG001은 지금→짐을 전달했는데 지금 짐으로 중복 실현했다. 후보 부재, 후보 미사용, 잘못된 실현은 다른 문제다.
4. 보호 지침과 검사만으로 오류가 없어지지는 않았다. LONG006의 가는 길→가노 길은 관형절 보존 지침이 전달된 상태에서 발생했다. 검사에서 탐지됐지만 1회 재검토에서도 같은 출력을 반환했다. 탐지와 복구 성공을 구분해야 한다.
5. Sonnet의 표현 다양성과 충실도는 별개다. DEV002/LONG006에서 가는→오는, DEV006에서 할머니께서→할매요, DEV004/LONG003/LONG004/LONG008에서 제/제가→내/내가가 관찰된다. LONG008에서는 힘드셨→힘들었으로 주체 높임도 줄었다. 이것만으로 전체 Sonnet의 품질 순위를 확정할 수는 없다.
6. Astra는 이 표본의 주요 비교 사례에서 의미·높임 유지와 방언 구성 변환을 함께 수행한다. 다만 DEV018의 도와줄래 유지, DEV029의 원문 전체 유지처럼 모든 구간을 바꾸지는 않는다. 원문 유지율을 곧 실패율로 해석해서는 안 된다.
7. 주세예/걸으세예 대 주이소/걸으이소는 현재 제한된 조합 규칙과 표현 선택의 차이다. 먼저→앞에, 회상 -대, 청유 -제에는 로컬 문헌 근거가 있으므로 익숙한 표준어 직관만으로 오역 처리하지 않았다. 지역·세대·대화 상황 적합성은 여전히 별도 검토가 필요하다.

원인에 대한 판단 범위
실제 입력에서 확인한 것은 후보가 없거나, 후보를 전달해도 출력이 따르지 않거나, 보호 지침을 어긴 경우가 함께 있다는 점이다. 따라서 KG를 더 크게 만들거나 후보 수를 일괄 늘리는 단일 처방으로 설명할 수 없다. DEV027은 오늘→올 하나뿐이므로 해당 사례는 후보를 너무 많이 전달했다는 설명과 맞지 않는다. 반대로 긴 입력의 후보 경쟁·정보량 영향은 통제 실험 전에는 원인으로 확정할 수 없다.
LONG008의 실제 계획에는 preserve.listener_politeness=unknown 및 speech_act=ask_intention이라는 캐시 분석과, 후보 binding의 politeness=polite가 함께 있다. 입력 속성의 일관성을 다시 점검할 구체적 단서다. 이것이 -지예 미사용을 일으켰다는 인과관계는 아직 검증하지 않았다.

비교에서 도출한 다음 실험
가. 인용·의도 구성: DEV027/LONG001/LONG005의 원문 구간과 KG 구성 진술 연결을 추적하고, 전달 실패가 분석·매칭·필터 중 어디서 생기는지 기록한다. KG 전체에 규칙이 없다고 단정하지 않는다.
나. 후보 적용: LONG008 같은 정확한 대상 어미·조합 지침이 있는 입력에서 불필요한 어휘 후보를 줄인 조건과 현재 조건을 같은 Qwen 설정으로 비교한다. 형태소 조합과 완성형을 제공하는 조건도 구분한다. 문헌 직접형과 모델 조합형의 출처 구분은 유지한다.
다. 적용 통제: LONG001의 중복과 LONG006의 관형절 손상처럼 모델이 지정 구간을 넘겨 고치는 경우를 별도 평가한다. 생성 수정 내역을 원문 구간과 정렬하여 탐지하고, 재검토 실패 출력은 성공으로 표시하지 않는다.
라. 평가: 후보 도달률, 선택 후보의 올바른 실현, 의미·높임 보존, 화자 자연스러움을 구분한다. 같은 Qwen의 무근거/현재 KG/검토한 최소 계획 조건으로 비교해야 KG 및 전달 방식의 효과를 더 잘 분리할 수 있다. 기존 38개는 개발용이며 일반화 확인에는 새 입력이 필요하다.

판단
최신 Qwen은 높임 종결 변환을 전혀 못하는 단계는 아니다. 주요 격차는 구성 단위의 근거 전달과 문장 전체에서 그 근거를 안정적으로 실현하는 데 남아 있다. Astra·Sonnet 출력은 이 격차를 발견하는 참고자료이며, 모든 표현을 그대로 KG의 사실로 추가할 정답지는 아니다.
'''

def dump(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

dump('comparison.json', rows)
dump('descriptive_stats.json', stats)
dump('retrieval_diagnostics.json', diagnostics)
with (OUT / 'comparison.tsv').open('w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter='\t')
    w.writeheader()
    w.writerows(rows)

summary += '\n기술 통계 (품질 점수가 아님)\n'
for model, ids in stats['unchanged_from_source'].items():
    summary += f'원문 완전 동일 {model}: {len(ids)}/38; {", ".join(ids) or "없음"}\n'
for model, ids in stats['qwen_exact_agreement_with'].items():
    summary += f'최신 Qwen과 {model} 완전 동일: {len(ids)}/38; {", ".join(ids)}\n'
(OUT / 'analysis.txt').write_text(summary)
text = summary + '\n전체 38개 입력 대조\n'
for r in rows:
    text += f'\n{r["id"]}\n원문: {r["standard"]}\nAstra: {r["astra"]}\nSonnet: {r["sonnet"]}\n최신 Qwen: {r["qwen_latest"]}\n검토: {r["review"]}\n'
(OUT / 'comparison.txt').write_text(text)

e = html.escape
parts = ['<!doctype html><html lang="ko"><meta charset="utf-8"><title>최신 KG·Astra·Sonnet 비교</title>',
         '<style>body{font-family:sans-serif;margin:24px;line-height:1.65;color:#18212c}pre{white-space:pre-wrap;max-width:1100px}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccd3dc;padding:12px;vertical-align:top}th{background:#edf3fa;position:sticky;top:0}td{min-width:170px}td:first-child{min-width:70px}.wrap{overflow-x:auto}</style>',
         '<h1>최신 KG 파이프라인 · Astra · Claude Sonnet 비교</h1>',
         '<pre>' + e(summary) + '</pre><div class="wrap"><table><thead><tr>',
         ''.join('<th>' + x + '</th>' for x in ['ID', '원문', 'Astra high', 'Sonnet (사용자 제공)', '최신 Qwen + KG', '검토']),
         '</tr></thead><tbody>']
for r in rows:
    parts.append('<tr id="' + r['id'] + '">' + ''.join('<td>' + e(r[k]) + '</td>' for k in ['id', 'standard', 'astra', 'sonnet', 'qwen_latest', 'review']) + '</tr>')
parts.append('</tbody></table></div></html>')
(OUT / 'comparison.html').write_text('\n'.join(parts))

inputs = [PEERS, LATEST / 'final_outputs.json', LATEST / 'retrieval.json',
          LATEST / 'jobs.json', ROOT / 'reports/astra_high_no_kg_20261012/protocol.json']
dump('provenance.json', {
    'scope': '38 matched inputs; saved final outputs only; no new model calls',
    'reviewer': 'Codex qualitative review, not independent human dialect annotation',
    'limitations': ['Models, prompts, batching and repair differ.',
                    'Sonnet original settings unverified.',
                    'No human gold or overall accuracy/ranking claimed.',
                    'Current outputs are development examples, not held-out evaluation.'],
    'sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}})
print(json.dumps(stats, ensure_ascii=False, indent=2))
print(f'Wrote {len(rows)} aligned rows to {OUT}')

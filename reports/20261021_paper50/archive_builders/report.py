"""Render an auditable bilingual-key/Korean-explanation research handoff, offline."""
import collections,csv,datetime,html,json,statistics,sys
from pathlib import Path
P=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(P))
import run
read=run.read;save=run.save
protocol=run.verify();dataset=read(P/'논문용_테스트_데이터셋.json');outputs=read(P/'outputs.json')
assert len(outputs)==150 and all(r['status']=='success' for r in outputs)
rows={(r['id'],r['condition']):r for r in outputs}
retrieval={r['id']:r for r in read(P/'retrieval.json')}
analysis={r['id']:r for r in read(P/'analysis.json')['items']}
methods=read(P/'methods.json');rubric=read(P/'evaluation_rubric.json')
notes={r['id']:r for r in csv.DictReader((P/'annotation_notes.tsv').open(),delimiter='\t')}
overrides={(r['id'],r['condition']):r for r in csv.DictReader((P/'final_annotation_overrides.tsv').open(),delimiter='\t')}
assert set(overrides)=={(r['id'],r['condition']) for r in outputs if r['selection']=='single_preservation_repair'}
dims=['meaning','register','fluency','dialect'];dimnames=['의미 보존','높임 보존','문장 자연스러움','방언 표현 실현']
cn={'P':'P · 원문만','A':'A · 분석만','K':'K · KG 사용'}
def compact(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def pretty(x):return json.dumps(x,ensure_ascii=False,indent=2)
def e(x):return html.escape(str(x))
annotations=[]
for d in dataset:
 for c in 'PAK':
  n=notes[d['id']];r=rows[d['id'],c];override=overrides.get((d['id'],c))
  annotations.append({'id':d['id'],'condition':c,'input':d['standard'],'first_output':r['first_output'],
   'first_scores':dict(zip(dims,map(int,n[c]))),'first_note':n[c+'_note'],'final_output':r['output'],
   'final_scores':dict(zip(dims,map(int,override['scores'] if override else n[c]))),
   'final_note':override['note'] if override else n[c+'_note'],'reviewer':'Codex, non-blind qualitative review, not independent human validation'})
save(P/'annotations.json',annotations);amap={(a['id'],a['condition']):a for a in annotations}
metrics={'input_count':50,'condition_count':3,'generation_calls':protocol['generation_calls'],'transport_failed_calls':2,'conditions':{}}
for c in 'PAK':
 rs=[r for r in outputs if r['condition']==c];aa=[a for a in annotations if a['condition']==c]
 m={'first_identical':sum(r['first_output']==r['input'] for r in rs),'final_identical':sum(r['output']==r['input'] for r in rs),
 'first_flagged':sum(bool(r['first_check']['flags']) for r in rs),'final_flagged':sum(bool(r['final_check']['flags']) for r in rs),
 'repairs':sum(r['repair_attempted'] for r in rs),'accepted':sum(r['selection']=='single_preservation_repair' for r in rs),
 'first_flag_types':dict(collections.Counter(f['kind'] for r in rs for f in r['first_check']['flags'])),
 'user_chars_mean':round(statistics.mean(len(r['request']['messages'][1]['content']) for r in rs),1),
 'prompt_tokens_mean':round(statistics.mean(r['response']['usage']['prompt_tokens'] for r in rs),1)}
 for phase in ['first','final']:
  m[phase+'_scores']={k:{'distribution':{str(i):sum(a[phase+'_scores'][k]==i for a in aa) for i in range(3)},'mean':round(statistics.mean(a[phase+'_scores'][k] for a in aa),2)} for k in dims}
 metrics['conditions'][c]=m
traces=[];packet_chars=[];plan_chars=[];groups=[];candidatecounts=[];groupchars=[];omits=collections.Counter();origins=collections.Counter();routes=collections.Counter();conditionstatuses=collections.Counter();edgecounts=[]
for d in dataset:
 sid=d['id'];r=rows[sid,'K'];prefix,bodytext=r['request']['messages'][1]['content'].split('\n',1);body=json.loads(bodytext);ret=retrieval[sid];packet=ret['packets']['v2_graph']
 refs={(v['id'],tuple(v['input_binding']['span'])):v for v in packet['references']}
 packet_chars.append(len(compact(packet)));plan_chars.append(len(compact(body['transformation_plan'])));groups.append(len(body['transformation_plan']));edgecounts.append(len(body['graph_paths']))
 omits.update(v['reason'] for v in ret['selection_audit']['v2_graph']['omitted'])
 entries=[]
 for group in body['transformation_plan']:
  candidatecounts.append(len(group['candidates']));groupchars.append(len(compact(group['candidates'])))
  for cand in group['candidates']:
   ref=refs[cand['id'],tuple(group['span'])];b=cand['binding'];conv=b.get('ending_conversion') or b.get('construction_conversion') or {};pref=conv.get('preferred_surface')
   routes[ref['retrieval_route']]+=1;origins[cand['origin']]+=1
   conditionstatuses.update(t['status'] for t in ref['checks']['conditions'])
   entry={'span':group['span'],'target_text':group['target_text'],'id':cand['id'],'type':cand['type'],
    'source':cand['source_pattern']['text'],'target':cand['target_pattern']['text'],'origin':cand['origin'],'preferred_surface':pref,
    'preferred_surface_observed':bool(pref and pref in r['first_output']),
    'candidate_text_observed':bool(cand['target_pattern']['text'].lstrip('-') and cand['target_pattern']['text'].lstrip('-') in r['first_output']),
    'evidence_pages':cand['evidence_pages'],'supporting_fact_ids':cand.get('supporting_fact_ids',[]),'checks':ref['checks'],
    'retrieval_route':ref['retrieval_route'],'constraints':cand['constraints'],'scope':cand['scope'],'conversion':conv}
   entries.append(entry)
 traces.append({'id':sid,'groups':len(body['transformation_plan']),'candidates':entries,'graph_paths':body['graph_paths'],
  'packet_chars':len(compact(packet)),'plan_chars':len(compact(body['transformation_plan'])),'user_chars':len(r['request']['messages'][1]['content']),
  'proposal_count':ret['proposal_count'],'rejected_count':len(ret['rejected']),'omitted':ret['selection_audit']['v2_graph']['omitted']})
tm={x['id']:x for x in traces};save(P/'candidate_trace.json',traces)
def stats(a):return {'mean':round(statistics.mean(a),2),'min':min(a),'max':max(a),'sum':sum(a)}
metrics['retrieval']={'groups_per_input':stats(groups),'candidates_per_group':stats(candidatecounts),'candidate_json_chars_per_group':stats(groupchars),
 'packet_chars_per_input':stats(packet_chars),'plan_chars_per_input':stats(plan_chars),'graph_edges_per_input':stats(edgecounts),
 'candidate_origins':dict(origins),'candidate_routes':dict(routes),'structured_condition_statuses':dict(conditionstatuses),'omission_reasons':dict(omits),
 'preferred_surface_count':sum(bool(c['preferred_surface']) for t in traces for c in t['candidates']),
 'preferred_surface_observed_count':sum(c['preferred_surface_observed'] for t in traces for c in t['candidates'])}
metrics['pairwise_identical_first']={a+b:sum(rows[d['id'],a]['first_output']==rows[d['id'],b]['first_output'] for d in dataset) for a,b in [('P','A'),('P','K'),('A','K')]}
save(P/'metrics.json',metrics)
with (P/'comparison.tsv').open('w',newline='') as f:
 w=csv.writer(f,delimiter='\t',lineterminator='\n');w.writerow(['id','standard','P_first','A_first','K_first','P_final','A_final','K_final'])
 for d in dataset:w.writerow([d['id'],d['standard']]+[rows[d['id'],c][key] for key in ['first_output','output'] for c in 'PAK'])
(P/'translations.txt').write_text('\n\n'.join(f"{d['number']:02}. {d['id']}\n원문: {d['standard']}\n"+'\n'.join(f"{cn[c]} 최초: {rows[d['id'],c]['first_output']}\n{cn[c]} 최종: {rows[d['id'],c]['output']}" for c in 'PAK') for d in dataset)+'\n')

# One semantic document rendered both as self-contained HTML and native Notion text.
parts=[];notion=[]
def heading(title,anchor=None):
 parts.append(f'<h2 id="{e(anchor or title)}">{e(title)}</h2>');notion.append('## '+title+'\n')
def para(s):parts.append('<p>'+e(s)+'</p>');notion.append(s+'\n')
def bullets(items):parts.append('<ul>'+''.join('<li>'+e(s)+'</li>' for s in items)+'</ul>');notion.append('\n'.join('- '+s for s in items)+'\n')
def table(headers,data):
 data=list(data);parts.append('<div class="scroll"><table><thead><tr>'+''.join('<th>'+e(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+e(v)+'</td>' for v in row)+'</tr>' for row in data)+'</tbody></table></div>')
 notion.append('<table header-row="true">\n<tr>'+''.join('<td>'+e(x)+'</td>' for x in headers)+'</tr>\n'+ '\n'.join('<tr>'+''.join('<td>'+e(v).replace('\n','<br>')+'</td>' for v in row)+'</tr>' for row in data)+'\n</table>\n')
def code(s,language='json',native=True):
 parts.append('<pre><code>'+e(s)+'</code></pre>')
 if native:notion.append('```'+language+'\n'+s+'\n```\n')
def linkfile(path,label):parts.append(f'<p><a href="{e(path)}">{e(label)}</a></p>')
heading('1. 이번 실험에서 확인한 핵심','summary')
para('작성일 2026-10-21 · 논문 초안 작성자를 위한 연구 이관 자료 · 운영 KG와 조회·생성 코드는 변경하지 않았다.')
bullets([
 '동일한 Qwen3.8-27B 서버 모델에 원문만(P), 분석만(A), KG 자료 포함(K)을 각각 제공했다. 총 150개 최초 출력과 46개 재검토 출력을 저장했다. 응답이 없던 통신 실패 2회를 포함한 요청 시도는 198회다.',
 '최초 출력에서 높임 보존에 뚜렷한 문제가 없다고 평가한 사례는 P 23/50, A 18/50, K 49/50이었다. 충분한 방언 표현이 관찰된 사례는 P 3/50, A 2/50, K 41/50이었다. 이는 Codex의 사례 판정이며 공인 정확도나 독립 화자 평가 점수가 아니다.',
 'KG의 기능별 종결 계획은 친구라예·했어예·했는교·주이소·께예 등의 실현을 돕는 양상을 보였다. 분석 JSON을 추가하는 것만으로 같은 개선이 나오지는 않았다.',
 'KG에도 오류가 남았다. DEV002의 가는→가던은 재검토로 복원됐지만, NEW007의 온나 후보 미반영과 LONG003의 높임 계열 혼용은 남았다. 단어를 많이 바꾸는 것만으로 자연스러움을 설명할 수 없다.',
 '결과는 이번 50개 사례에서의 동작과 오류 양상을 보여 준다.'
])
heading('2. 비교 조건과 무엇을 비교하는지','design')
para('대상 50개는 이전 KG 번역 결과가 상대적으로 양호했던 사례에서 선정했으므로, 아래 결과는 이 사례들에서의 비교이며 새로운 문장 전반의 성능을 나타내지는 않는다.')
table(['조건','생성기에 제공한 내용','비교가 답하는 질문'],[
 ['P 원문만','동일한 system 지시 + 표준어 원문. 최초 요청에 분석·Kiwi·KG 없음','이 설정에서 Qwen이 스스로 어느 정도 바꾸는가?'],
 ['A 분석만','K와 같은 공통 지시·Qwen 분석·Kiwi·원문 보존 지침. transformation_plan·graph_paths·supporting_knowledge는 빈 배열','분석 정보를 전달하는 것만으로 달라지는가?'],
 ['K KG 사용','A의 정보 + 조회 후보·구간별 변환 계획·출처·연결 관계·보존용 지식','분석 입력 위에 실제 지식 묶음을 더하면 달라지는가?']])
bullets(['A는 KG 조회 결과를 생성 입력에서 비우는 비교 조건이다. 실행 준비 단계에서는 같은 조회 결과로 A/K 요청을 만들었으므로 “A 준비 과정에서 조회 코드조차 실행하지 않았다”는 뜻은 아니다.',
 'P와 A는 입력의 길이·구조·공통 지시도 다르다. A와 K는 지식이 들어가는 세 필드만 다르지만, 지식 길이와 구체적인 변환 지침까지 함께 바뀐다. 그래프 연결 구조만의 효과를 분리한 비교는 아니다.',
 '기존 A/B/C/D 실험과 명칭을 혼동하지 않도록 이번에는 P/A/K를 사용했다. 과거 A/B/C/D는 조회 방식(기존/의미 검색 추가)과 전달 형식(기존/변환 계획)의 2×2 비교였다. 이번 실행은 현재 최종 조회 방식을 고정한 3조건 비교이며 과거 결과를 새 비교 수치에 섞지 않았다.',
 '이번 50건의 Qwen 분석은 기존 실험의 저장 결과를 재사용했다. Kiwi와 현재 조회는 다시 수행했고, 번역 생성 150건은 새로 호출했다. 생성 모델을 재학습하거나 Claude/Astra 번역을 정답으로 제공하지 않았다.'])
cfg=protocol['config'];req=rows['DEV004','K']['request']
table(['항목','실제 설정'],[['모델 식별자',req['model']],['최대 출력 토큰',req['max_tokens']],['temperature / top_p / top_k',f"{req['temperature']} / {req['top_p']} / {req['top_k']}"],['seed / 추론 표시 설정',f"{req['seed']} / enable_thinking=false"],['실행 순서','seed 20261021로 150개 요청 순서를 섞음; 동시 요청 2개'],['분석 호출','기존 분석 고정 재사용. 이번 새 분석 모델 호출 0회'],['재검토','모든 조건에 같은 검사. 강한 경고가 있으면 최대 1회; 새 오류가 생기거나 강한 경고가 남으면 최초 결과 유지'],['통신 재시도','ADVCE005A_K, ADVCE008A_K만 응답 없음으로 동일 요청 재시도. 원래 실패 기록 별도 보존'],['모델 검증 범위','서버 /models 및 응답의 ID 확인. 실제 가중치·학습 데이터·체크포인트는 별도 확인하지 못함']])
heading('3. 평가 기준과 전체 결과','results')
table(['평가 축','보는 내용','판정 2 / 1 / 0'],[[dimnames[i],rubric['dimensions'][k],'2: 뚜렷한 문제 없음·충분한 실현 / 1: 부분 보존·부분 실현·우려 / 0: 뚜렷한 손상·미실현'] for i,k in enumerate(dims)])
bullets(['원문과 출력을 직접 읽고 의미·높임·문장 연결·방언 실현을 구분했다. 네 축 점수를 합쳐 하나의 성능 점수로 만들지 않았다.',
 '평가자는 이 보고서를 작성한 Codex다. 조건을 알고 평가했으며 독립 방언 화자의 눈가림 평가가 아니다. 지역·세대에 따른 자연스러움이 불명확한 형태는 사례 메모에 남겼다.',
 '정답 번역이 없으므로 정답 문자열과의 일치율을 계산하지 않았다. -다·-라처럼 표준어에도 있는 형태, 낼·짐 같은 일반 축약만으로 충분한 방언 실현을 인정하지 않았다.',
 '최초 출력은 세 조건의 기본 생성 차이를, 최종 출력은 동일 검사와 최대 1회 재검토까지 포함한 운영 결과를 보여 준다. 재검토 후 결과도 같은 기준으로 직접 확인했고, 바뀐 32건의 판정 근거를 별도 기록했다.'])
for phase,title in [('first','최초 출력: 각 판정에 해당하는 건수'),('final','재검토 후 최종 출력: 각 판정에 해당하는 건수')]:
 para(title+' — 표의 숫자는 순서대로 2점 / 1점 / 0점 건수이며 각 칸 합계는 50이다.')
 table(['평가 축','P 원문만','A 분석만','K KG 사용'],[[dimnames[i]]+[' / '.join(str(metrics['conditions'][c][phase+'_scores'][k]['distribution'][str(j)]) for j in [2,1,0]) for c in 'PAK'] for i,k in enumerate(dims)])
table(['자동 기록 · 50건 기준','P','A','K'],[[label]+[metrics['conditions'][c][key] for c in 'PAK'] for key,label in [('first_identical','최초: 원문과 글자 단위 완전 동일'),('final_identical','최종: 원문과 글자 단위 완전 동일'),('first_flagged','최초: 검사 경고가 있는 입력'),('repairs','재검토 호출 입력'),('accepted','재검토 결과를 채택한 입력'),('final_flagged','최종: 검사 경고가 남은 입력')]])
para('원문 완전 동일 여부는 공백·문장부호까지 포함한 정확한 비교다. 동일하지 않다는 것만으로 방언 변환 성공은 아니다. 자동 경고는 오류 탐지 결과이고, 위의 수동 정성 판정과 다른 지표다.')
bullets(['자동 재검토는 P/A의 높임을 상당 부분 되살렸지만 표준어 원문 또는 표준어 정중체로 되돌리는 경우가 많았다. 보존 검사만으로 방언 표현의 생성을 확보하지 못했다.',
 '자동 검사 통과도 충분하지 않았다. P/ADVCE001A의 “기차 지금 정차하고 계신가요?”는 기차에 불필요한 높임을 붙였고, A/QUAL002의 “거라”는 높임이 복원되지 않았지만 최종 강한 경고가 남지 않았다.',
 '후보 제공과 적용은 별개다. K/NEW007은 온나를 받았지만 와를 유지했고, P/DEV017은 KG 없이도 K와 같은 주이소를 생성했다. 개별 출력의 자연스러움을 KG만의 효과로 자동 계산하지 않았다.'])
heading('4. 실제 전달량과 후보의 성격','payload')
ms=metrics['retrieval']
table(['측정값','평균','최소','최대','계산 대상'],[[label,ms[k]['mean'],ms[k]['min'],ms[k]['max'],scope] for k,label,scope in [
 ('groups_per_input','입력당 대상 구간 수','50개 K 요청의 transformation_plan 그룹'),('candidates_per_group','구간당 후보 수','실제 전달된 모든 구간; 합계 후보/합계 구간'),
 ('candidate_json_chars_per_group','구간당 후보 배열 글자 수','candidate JSON 전체: 속성명·조건·출처 포함, 압축 직렬화'),
 ('packet_chars_per_input','입력당 조회 자료 묶음 글자 수','계획으로 줄이기 전 references+관계+보존 정보'),('plan_chars_per_input','입력당 변환 계획 글자 수','생성기에 실제 전달된 transformation_plan 전체'),('graph_edges_per_input','입력당 명시 관계 경로 수','실제 graph_paths 배열 항목 수')]])
table(['조건','전체 user 메시지 평균 글자 수','실제 최초 요청 prompt 토큰 평균'],[[cn[c],metrics['conditions'][c]['user_chars_mean'],metrics['conditions'][c]['prompt_tokens_mean']] for c in 'PAK'])
bullets(['입력 1건은 긴 발화에서 여러 문장을 포함할 수 있다. 구간은 단어 하나일 수도, 종결을 가진 절 전체일 수도 있으며 서로 겹칠 수 있다. 따라서 구간 수는 띄어쓰기 단어 수나 문장 수와 다르다.',
 '후보는 해당 구간에 쓸 수 있을지 검토하는 대안이다. 모든 후보를 한꺼번에 적용하라는 뜻이 아니다. 같은 후보 ID가 서로 다른 구간에 붙으면 각각 하나로 세었다.',
 '구간당 최대 6개 후보. 24,000자는 구간마다가 아니라 입력 한 건의 조회 자료 묶음 전체 제한이다. 관계 경로용 2,000자를 미리 남겨 후보 추가는 22,000자 선에서 제한한다. 이후 분석과 지시를 합친 user 메시지에는 이 제한이 그대로 적용되지 않는다.',
 '글자 수는 Python len 기준으로 JSON의 속성명·공백 없는 구분기호까지 포함한다. 토큰 수는 서버의 usage.prompt_tokens로 system·user·대화 형식이 모두 포함된다. 글자와 토큰은 다른 단위다.',
 '최대 6개·글자 제한의 영향은 후보 제외 기록으로 확인할 수 있다. 다만 이번에는 후보 수를 바꿔 재실험하지 않았으므로 너무 많아서/적어서 실패했다고 인과적으로 단정할 수 없다.'])
omitlabels={'per_binding_cap':'구간당 6개 제한','packet_budget':'입력당 전체 글자 제한','construction_alternative_cap':'같은 구간의 복합 구성 대안 제한'}
originlabels={'documentary_KG':'문헌에서 구조화한 항목','documentary_components_with_analyst_composition':'문헌 구성요소를 입력에 맞게 조합한 계획','model_advice_not_documentary_fact':'문헌 직접 확인형이 아닌 모델 조언'}
table(['후보 제외 사유','구간·후보 처리 건수'],[[omitlabels.get(k,k),v] for k,v in omits.items()])
table(['전달 후보의 출처 성격','구간에 붙은 후보 건수'],[[originlabels.get(k,k),v] for k,v in origins.items()])
para('이번 50건에 실제 전달된 후보는 문헌 항목 134건과 문헌 구성요소를 조합한 계획 55건이었다. 별도 MODEL_ADVICE 후보는 실제 전달되지 않았다. 모델 조언으로 발전시킨 운영 정책과 문헌 조합 코드의 영향까지 없다는 뜻은 아니다.')
table(['조회 경로 코드','쉬운 설명','전달 후보 수'],[[k,v,routes[k]] for k,v in {
 'function_bound_terminal':'원문 끝의 기능·높임에 묶인 종결 계획',
 'bound_lexical_mapping':'원문 단어의 기본형과 뜻에 묶은 어휘 대응',
 'source_form':'원문에 나타난 표현 형태와 맞춘 후보',
 'clause_function':'평서·질문 등 절의 기능으로 찾은 후보',
 'source_bound_construction':'인용·의도 등 여러 요소가 결합한 원문 구성 후보',
 'lexical_to_inflection':'어휘 대응에서 연결 관계를 따라 찾은 활용 후보'}.items()])
para(f"전체 50건 중 {sum(bool(t['graph_paths']) for t in traces)}건에서 명시적인 graph_paths가 전달됐고 경로 항목은 총 11개였다. 대부분은 출처·조건을 포함한 지식 항목과 변환 계획 자체를 사용했다. 따라서 K의 개선을 모두 다단계 관계 탐색의 효과로 설명할 수 없다.")
para(f"구체적인 추천 표면형이 붙은 후보 {ms['preferred_surface_count']}건 중 {ms['preferred_surface_observed_count']}건은 그 문자열이 최초 출력에 나타났다. 이는 활용이 달라지면 놓칠 수 있고 짧은 문자열이면 우연히 일치할 수 있는 관찰이다. 지식 사용률·정확도·검색 재현율로 해석하지 않는다.")
heading('5. 전체 처리 순서: 문헌에서 번역까지','method')
table(['순서','무엇을 하는가','산출물·주의점','관련 파일'],methods['steps'])
heading('6. 원문 7종과 KG 구축','kg')
registry=read(P/'snapshot/kg_v2/source_registry.json')['sources']
table(['출처 ID','소개','원본 PDF 상대 경로'],[[s['source_id'],methods['source_notes'].get(s['source_id'],s['title']),s['file']['path']] for s in registry])
bullets(['총 474쪽은 PDF 파일의 페이지 수다. 논문 인쇄 페이지와 다를 수 있어 근거는 pdf_page로 추적한다. PDF는 프로젝트 로컬 자료이며 이 보고서에 원문 파일 자체를 공개 첨부하지 않는다.',
 'PDF 텍스트 추출은 프로그램이, 내용 선택·구조화는 Astra가 담당했다. 이후 Astra 작업자 3개와 조정자의 검토, 후속 조언자·반례 검토자·문헌 대조자 검토를 거쳤다. 같은 모델 계열의 다중 검토가 독립 화자 검증을 대신하지는 않는다.',
 '현재 자료는 학술 문헌과 공동 편집 위키가 섞여 있다. 과거 조사 발화와 현대 용법, 경북과 경남의 범위를 모든 화자에게 공통인 단일 규칙으로 보아서는 안 된다.'])
para('지식 항목(진술)은 “어떤 표현이 어떤 조건에서 어떻게 쓰이는가”를 기록한 한 묶음이다. JSON은 이 묶음의 저장 형식이고, 그래프는 같은 정보를 연결 구조로 펼친 표현이다.')
table(['속성','뜻','쓰임'],methods['fact_fields'])
table(['구분','무엇을 나누는가','예'],[['지식 유형 9개','한 지식 항목이 설명하는 내용','단어 대응인지, 어미인지, 활용인지'],['노드 유형 8개','그래프에 저장하는 요소','지식 항목, 표현, 조건, 근거, 문헌'],['관계 유형 19개','요소 사이 연결의 뜻','이 항목의 입력 표현이다 / 이 쪽의 근거가 뒷받침한다']])
para('예: “명사 뒤 예요를 라예로 표현할 수 있다”는 어미 지식 항목 하나다. 중심 노드에서 입력 표현·대응 표현·조건·근거로 연결되고, 근거는 PDF 쪽과 문헌으로 이어진다. 지식 유형 ending은 어미 조회 경로의 후보를 찾는 데 쓰이고, 노드 유형 Evidence는 출처를 따라갈 때 쓰인다. 두 분류는 같은 것을 중복해서 세는 것이 아니다.')
graph=read(P/'snapshot/kg_v2/graph.json');facts=[json.loads(l) for l in (P/'snapshot/kg_v2/facts.jsonl').read_text().splitlines()]
example_fact=next(f for f in facts if f['id']=='NAMU_GRAMMAR_20260908:v2:ending_repair:0001')
parts.append('<details><summary>실제 지식 항목 JSON: DEV004 종결 계획을 뒷받침한 자료</summary>')
code(pretty(example_fact),native=False);parts.append('</details>')
notion.append('실제 지식 JSON 예시는 첨부 HTML의 6절에서 펼칠 수 있다. 항목 ID: NAMU_GRAMMAR_20260908:v2:ending_repair:0001.\n')
nc=collections.Counter(n['type'] for n in graph['nodes']);ec=collections.Counter(n['type'] for n in graph['edges']);fc=collections.Counter(f['type'] for f in facts)
for name,desc,counts in [('지식 유형',methods['fact_types'],fc),('노드 유형',methods['node_types'],nc),('관계 유형',methods['edge_types'],ec)]:
 para(name+' 전체 목록');table(['코드 이름','쉬운 설명','개수'],[[k,v,counts[k]] for k,v in desc.items()])
bullets(['외부 모델 번역은 정답 지식으로 그대로 넣지 않았다. 문헌으로 다시 확인한 부분은 출처 있는 항목·조건·조회 경로로 보완했고, 문헌에 직접 없는 제안은 advisory_rules.json에서 model_advice_not_documentary_fact로 구별했다.',
 '문헌의 어미 구성요소를 원문에 맞게 조합한 PLAN 항목은 실행 시 만든 적용 계획이다. 3,767개 문헌 항목과 같은 의미의 새 문헌 근거가 아니며, 완성 발화 전체가 원문에 나왔다는 뜻도 아니다.',
 '사용자가 요청한 종결 계열 우선 선택은 운영 정책으로 코드에 반영돼 있다. 따라서 K는 순수한 문헌 검색뿐 아니라 구조화한 근거·조합 규칙·우선순위·전달 지시를 묶은 제안 시스템이다.'])
heading('7. Qwen·Kiwi 분석, 조회와 조건 검사','retrieval')
table(['단계','입력','출력','누가 판단하는가'],[
 ['Qwen 분석','표준어 전체 발화','절 위치, 평서/질문/요청, 높임, 시제, 서술 유형 등의 JSON 가설','Qwen. 이번에는 저장 분석 재사용'],
 ['Kiwi','동일 표준어','형태소·품사·위치. 코드가 기본형과 어미 묶음을 정리','Kiwi + Python'],
 ['원문 대조','두 분석과 실제 글자 위치','원문에 붙인 구간, 기본형, 기능, 높임 등의 조회 조건','Python. 불확실한 분석은 확정 정답 아님'],
 ['후보 찾기','조회 조건','어휘/활용/종결/복합 구성에 맞는 지식 항목','Python 로컬 그래프 조회'],
 ['조건 확인','후보 조건 + 입력/후보 속성','충족·불일치·모름, 추가 검토 이유','Python 규칙 검사'],
 ['후보 정렬·묶기','조건 검사 후 후보','우선순위·구간 균형·최대6개·전체 글자 제한을 적용한 자료','Python'],
 ['실제 적용','원문·분석·후보·보존 지침','방언 발화 텍스트','Qwen 생성 모델']])
bullets(['조회 코드는 Python이다. JSON은 조회 코드 그 자체가 아니라 코드가 읽는 분석값·후보·생성 요청의 형식이다. Qwen이 임의의 Cypher나 Python을 작성해 실행시키는 구조가 아니다.',
 '현재 조회는 기본형/표현 일치와 문장 기능을 함께 사용한다. 예를 들어 먹다의 대응을 찾고 candidate_has_inflection 관계로 활용을 따라가거나, 높임 평서문이라는 기능에 맞는 종결 계획을 먼저 만든다.',
 'Qwen과 Kiwi를 각각 사용하지만, “항상 두 모델이 동시에 병렬 실행된다”는 뜻은 아니다. 이번 실행은 기존 Qwen 분석을 읽고 Kiwi·조회·요청 구성을 순서대로 수행했다. 병렬 실행 2개는 번역 API 요청에 관한 설정이다.',
 '시제·높임·화행 등 보존 목표 전체가 하나의 완전한 검사기로 증명되는 것은 아니다. 값으로 적힌 조건은 코드가 검사하지만, 자연어 의미·지역·시대·예외는 검토 지시로 남을 수 있다.'])
table(['조건 판정','뜻','현재 처리'],[['satisfied 충족','필요한 값과 실제 값이 같음','후보 자격 검토를 계속함. 최종 자연스러움 보증 아님'],['failed 불일치','필요한 값과 실제 값이 다름','제외'],['unknown 모름','필요한 값이 없거나 불명확','현재 문장 조회에서 제외'],['조건 배열이 비어 있음','검사할 구조화 조건이 없음','아무 조건이나 맞는다는 증거가 아님. 자연어 범위·뜻 검토가 필요']])
heading('8. 생성 프롬프트와 실제 한 사례의 전체 흐름','prompt')
para('system 메시지는 매 요청에 공통인 역할·목표 지시다. user 메시지도 프롬프트의 일부이며 원문과 해당 입력의 분석·지식 자료가 들어간다. 자연어 지시와 JSON 데이터가 함께 프롬프트를 구성한다.')
para('이번 실험의 정확한 고정 system 지시');code(req['messages'][0]['content'],'text')
para('분석용 Qwen 지시는 생성 지시와 다르다. “번역하거나 방언 표현을 제안하지 말고 JSON 객체 하나만 출력”하도록 요구하고, 평서/질문/요청·높임·시제의 분석값과 원문 구성을 출력하게 한다. 현재 분석 코드의 요청 기본값은 temperature=0, top_p=1, max_tokens=4200이다. 이번 실험은 그 단계의 저장 분석을 재사용했으므로 이 설정으로 새 분석 50건을 호출했다고 보고하지 않는다. 분석 프롬프트와 JSON 출력 규격은 snapshot/current_kg/experiments/run_auto_analysis_development.py의 analysis_system/raw_schema에서 확인할 수 있다.')
para('A/K의 정확한 공통 user 지시');code(req['messages'][1]['content'].split('\n',1)[0],'text')
table(['user JSON 속성','무엇이 들어가는가','A와 K의 차이'],[
 ['standard','번역할 표준어 전체 발화','동일'],['analysis','Qwen의 절·기능·높임·시제 분석 가설','동일'],['source_morphology','Kiwi 단어/어미, 기본형, 글자 위치','동일'],['transformation_plan','대상 구간별 후보·조건·추천형·출처·보존 사항','A 빈 배열 / K 실제 자료'],['graph_paths','선택한 어휘와 활용 지식 사이 연결','A 빈 배열 / K 조회된 연결'],['preservation','원문의 의미·높임·수식·이동 관점 보존 지침','지침은 동일; supporting_knowledge만 A에서 비움'],['plan_policy','후보는 대안이며 보존을 우선하라는 공통 고정 지시','동일']])
sid='DEV004';b=json.loads(rows[sid,'K']['request']['messages'][1]['content'].split('\n',1)[1]);t=tm[sid]
table(['DEV004 처리 단계','실제 기록의 요약'],[
 ['원문',rows[sid,'K']['input']],['Qwen 분석',compact(b['analysis'])],
 ['Kiwi 결과','친구: 명사 / 이: 명사 서술 / 예요: 종결. 실제 위치·형태소는 아래 JSON 참조'],
 ['조회 결과','; '.join(c['id'] for c in t['candidates'])],
 ['생성에 전달한 추천','; '.join(str(c['preferred_surface']) for c in t['candidates'])],
 ['원문 근거','; '.join(f"{x['source_id']} PDF {x['pdf_page']}쪽" for c in t['candidates'] for x in c['evidence_pages'])],
 ['첫 생성',rows[sid,'K']['first_output']],['자동 검사',compact(rows[sid,'K']['first_check'])],['최종 선택',rows[sid,'K']['output']]])
parts.append('<details><summary>DEV004 실제 user JSON 전체 펼치기 — 편집한 가상 예시가 아님</summary>');code(pretty(b),native=False);parts.append('</details>')
notion.append('DEV004의 전체 요청 JSON은 첨부 HTML과 raw/DEV004_K.json에 보존되어 있다. 표의 요약은 실제 요청에서 추출했다.\n')
bullets(['DEV004는 라예가 전달되고 출력에도 친구라예가 나타난 사례다. 문헌의 관련 구성요소와 입력 조건을 바탕으로 만든 계획의 실현이지, 문헌에 이 전체 발화가 실려 있다는 뜻은 아니다.',
 '반대로 NEW007은 먹다 관련 후보와 온나 추천을 함께 받았지만 묵고만 적용됐다. 조회 성공만으로 생성 적용 성공을 판단해서는 안 된다.',
 '구간 후보와 출처 페이지, 조건 판정·검토 이유·추천형의 표면 관찰을 아래 50건 상세표와 candidate_trace.json에서 모두 확인할 수 있다.'])
heading('9. 생성 후 보존 검사: 할 수 있는 것과 한계','checks')
table(['검사 대상','실제 구현 개요','주요 한계'],[
 ['청자 높임','원문 높임 끝과 출력의 명백한 반말 끝을 규칙으로 비교','목록에 없는 거라 등은 놓칠 수 있음'],['겸양 저/제','제가·저는 등이 내가·나는 등으로 바뀌었는지 검사','나처럼 목록 밖 축약은 놓칠 수 있음'],['부정·과거','Kiwi와 표면 패턴으로 부정 및 과거 흔적 확인','방언 형태를 잘못 분석할 수 있어 검토 경고로 처리'],['이동 관점','가는 길 ↔ 오는 길 교환 등 명시 패턴 검사','모든 이동 의미 변화를 포괄하지 못함'],['명사 앞 문장 구조','같은 서술어와 뒤 명사를 맞춰 -는→-던, 종결형 오치환 검사','대응 형태가 크게 바뀌면 놓칠 수 있음'],['주체 높임','께서·시·계시다 등의 존재 확인','불필요하게 추가한 높임이나 자연스러움을 전부 판정하지 못함'],['문장 수·질문 부호','입출력 문장 대응과 ? 차이 확인','부호 차이만으로 문장 의도를 확정하지 않음']])
para('강한 경고가 있으면 동일 요청의 대화 뒤에 최초 출력과 수정 지시를 붙여 1회 다시 호출한다. 새 강한 경고가 없고 경고 종류가 늘지 않은 경우에만 채택한다. KG나 코드를 자동으로 수정하는 단계는 아니다. 최종 경고 0개와 언어적으로 올바른 번역은 다르다.')
heading('10. 확정한 50개 표준어 예문','dataset')
para('아래 목록이 고정한 논문용_테스트_데이터셋 v1이다. 원래 출처는 DEV/LONG/NEW/ADVCE가 reports/20261013_terminal_generation, QUAL은 reports/20261013_user_qualification20이다.')
table(['번호','ID','확정 표준어 원문'],[[d['number'],d['id'],d['standard']] for d in dataset])
linkfile('논문용_테스트_데이터셋.txt','표준어 50건 목록 TXT');linkfile('논문용_테스트_데이터셋.tsv','표준어 50건 목록 TSV')
heading('11. 50건 실제 결과와 근거','cases')
para('각 행의 평가는 [의미, 높임, 자연스러움, 방언 실현] 순서다. 최초·최종이 같으면 동일로 표시한다. 상세 후보 표의 “표면 관찰”은 추천형이 출력에 글자 그대로 나타났는지만 뜻하며, 모델 내부의 지식 사용 증명이 아니다.')
para('상세표의 검토 표시: textual_constraints_require_review는 글로 적힌 제약 검토, source_scope_requires_review는 지역·시대 범위 검토, claim_status_requires_review는 근거 성격 검토, interpreted_condition_requires_review는 해석해서 만든 조건 검토, sense_requires_review는 단어 뜻 검토를 뜻한다. 이 표시는 오류 확정이나 모든 조건 검사 완료를 뜻하지 않는다.')
parts.append('<label class="filter">사례 찾기 <input id="search" placeholder="ID, 원문 또는 표현 검색" aria-label="사례 검색"></label>')
native_cases=[]
for d in dataset:
 sid=d['id'];parts.append(f'<article class="case" id="{sid}"><h3>{d["number"]:02}. {sid}</h3><p class="source">{e(d["standard"])}</p>')
 before=len(notion);table(['조건','최초 번역','정성 판정·근거','최종 번역 / 최종 판정'],[[cn[c],rows[sid,c]['first_output'],str(list(amap[sid,c]['first_scores'].values()))+' '+amap[sid,c]['first_note'],('최초와 동일' if rows[sid,c]['output']==rows[sid,c]['first_output'] else rows[sid,c]['output']+' / '+str(list(amap[sid,c]['final_scores'].values()))+' '+amap[sid,c]['final_note'])] for c in 'PAK'])
 native_cases.append('## '+sid+'\n\n원문: '+d['standard']+'\n\n'+notion.pop())
 parts.append('<details><summary>조회 후보 · 자동 검사 · 원본 요청 펼치기</summary>')
 t=tm[sid];parts.append(f'<p>조회 제안 {t["proposal_count"]}건 → 실제 전달 {t["groups"]}개 구간·{len(t["candidates"])}개 후보. 관계 경로 {len(t["graph_paths"])}개. 자료 묶음 {t["packet_chars"]:,}자 / 전체 user {t["user_chars"]:,}자.</p>')
 cr=[]
 for ca in t['candidates']:
  pref=ca['preferred_surface'];status='추천형 없음: 형태 적용은 직접 확인 필요' if not pref else ('추천형 관찰됨' if ca['preferred_surface_observed'] else '추천형 그대로는 안 나타남')
  checks=ca['checks'];ct='; '.join(f"{x['field']}: {x.get('actual')} → {x['status']}" for x in checks['conditions']) or '구조화 조건 없음'
  reviews='; '.join(checks.get('review_reasons',[]))
  cr.append([ca['target_text'],ca['id']+'\n'+ca['retrieval_route'],ca['source']+' → '+ca['target']+(('\n추천: '+str(pref)) if pref else ''),ca['origin']+'\n'+'; '.join(f"{p['source_id']} p.{p['pdf_page']}" for p in ca['evidence_pages']),ct+'\n검토: '+reviews,status])
 table(['대상 구간','후보 ID / 조회 경로','대응·추천','근거 성격 / PDF 쪽','조건 판정·검토 이유','최초 K 출력 표면 관찰'],cr);notion.pop()
 for c in 'PAK':
  r=rows[sid,c];parts.append('<p>'+e(cn[c])+': 최초 검사 '+e(compact(r['first_check']))+'<br>최종 검사 '+e(compact(r['final_check']))+f' · <a href="raw/{sid}_{c}.json">원본 요청·응답</a></p>')
 parts.append('</details></article>')
(P/'notion_cases.txt').write_text('\n'.join(native_cases))
heading('12. 결과 해석과 남은 문제','interpretation')
table(['관찰','실제 예','해석','후속 확인 방법'],[
 ['기능에 맞는 종결 개선','DEV004 친구라예 / DEV011 출발했는교 / DEV021 보께예','구체적인 기능·높임·추천형을 함께 준 K에서 안정적으로 드러남','동일 문법의 새로운 입력을 따로 고정해 확인'],
 ['분석만으로는 부족','A의 친구임, 맵다요, 높임 소실','분석은 원문 설명이지 방언 형태를 생성하는 구체적 예시가 아님. 실제 방언 후보의 역할이 있음','A/K의 길이·지시 효과를 별도 실험으로 분리'],
 ['KG 없이도 성공','DEV017 세 조건 주이소','모든 성공이 KG로 새로 생긴 것은 아님','중복 성공과 K에만 관찰된 개선을 구별'],
 ['조회됐지만 적용 안 됨','NEW007 온나 전달, 출력은 와','검색 누락보다 생성 적용의 병목으로 추정','같은 후보를 더 명확하게 전달하는 실험; 현재는 변경 안 함'],
 ['구성 표현은 부분 변환','LONG001 만나자꼬 했는데 / NEW012 인용 표현 유지','단일 어미 변환보다 인용·의도 전체 결합의 연결과 적용이 덜 안정적','구성 후보의 대상 범위·바깥 시제·안쪽 인용 연결을 추적'],
 ['의미 회귀와 수정','DEV002 가는→가던→가는','KG가 있어도 원문 수식 의미를 바꿀 수 있음. 검사가 이 사례는 복원','검사의 놓침·잘못 경고를 독립 평가'],
 ['말투 혼용·어휘 범위','LONG003 맛있소/주이소, LONG004 이빠이, LONG002 올','문헌에 존재하는 표현도 동일 화자 맥락의 자연스러움을 보장하지 못함','지역·세대 화자 판단으로 후보 범위 보완'],
 ['검사 통과와 정답의 차이','최종 P/ADVCE001A 계신가요, A/QUAL002 거라','표면 패턴 검사의 범위 밖 오류가 남음','방언 화자 평가와 의미·높임 항목별 누락 점검']])
bullets(['위 해석은 이번 로그와 출력의 관찰에 근거한 원인 가설이다. 후보 개수·문장 길이·특정 규칙 하나의 인과효과를 별도 실험으로 증명한 것은 아니다.',
 '이번 50개 발화에서는 동일 생성 모델에 조건부 KG 자료와 변환 계획을 제공했을 때 높임과 종결 표현의 보존·실현이 개선되는 양상을 관찰했다.',
 '후속 평가는 새로운 입력과 조건을 가린 복수 방언 화자 평가로 확장할 수 있다.'])
heading('13. 연구원 이관 파일과 재현 범위','handoff')
table(['파일','용도'],[
 ['report.html','이 보고서. 인터넷 연결 없이 열 수 있고 인쇄/PDF 저장 가능'],['논문용_테스트_데이터셋.json / .tsv / .txt','고정 50개 원문과 선정 시 정보'],['selection_audit.json','기존 90건 전체의 선정·제외 근거'],['comparison.tsv / translations.txt','150개 최초 및 최종 출력 전체 비교'],['annotations.json / annotation_notes.tsv / final_annotation_overrides.tsv','조건별·축별 수동 정성 판정과 설명'],['metrics.json','집계 수치와 실제 전달량'],['candidate_trace.json / retrieval.json','후보·조건·출처·관계·제외 기록'],['jobs.json / raw/ / outputs.json','실제 생성 요청·응답·검사·재검토 기록'],['analysis.json','고정 재사용한 Qwen 분석'],['protocol.json / model_identity.json','실험 설정·파일 해시·서버 모델 응답'],['transport_failures/','응답 없는 통신 실패 2건의 원래 기록'],['snapshot/','이번 실험에서 사용한 KG·조회·생성·검사 코드와 데이터 복사본'],['run.py / recover_transport.py / report.py','실험 준비·생성, 통신 복구, 오프라인 보고서 재생성'],['verification.json','150건·고정 데이터·생산 파일 불변 검증 결과']])
para('보고서와 표는 프로젝트 루트에서 아래 명령으로 다시 만들 수 있다. API 호출은 하지 않는다. 실험 재호출은 run.py execute가 담당하지만 기존 raw 파일이 있으면 재사용하므로, 새 반복 실험은 별도 경로·버전으로 준비해야 한다.')
code('.venv/retrieval/bin/python reports/20261021_paper50/report.py','bash')
table(['고정 대상','SHA-256'],[['데이터셋 JSON',protocol['dataset_sha256']],['150개 최초 요청 jobs.json',protocol['jobs_sha256']],['실행 코드 run.py',protocol['runner_sha256']]])
para('이전 기준 결과 위치: reports/20261013_terminal_generation/translations.txt (70건), reports/20261013_user_qualification20/translations.txt (수정한 20건). 이번 자료는 reports/20261021_paper50에 모았으며 이전 실험은 덮어쓰지 않았다.')
para('평가 항목을 구분하고 평가자·절차·한계를 공개하는 설계는 자연어 생성 평가 연구의 일반적인 권고를 참고했다. 이 보고서의 자동 모델 평가는 그 논문의 독립 사람 평가를 수행했다는 뜻이 아니다.')
parts.append('<p>참고: <a href="https://aclanthology.org/W19-8643/">van der Lee et al. (2019), Best practices for the human evaluation of automatically generated text</a></p>')
notion.append('[평가 설계 참고 논문](https://aclanthology.org/W19-8643/)\n')
bullets(methods['boundaries'])
css='''body{font-family:Arial,"Noto Sans KR",sans-serif;color:#172938;background:#f3f6fa;margin:0;line-height:1.7}main{max-width:1400px;margin:auto;background:white;padding:36px}h1{font-size:29px;line-height:1.4}h2{margin-top:46px;border-bottom:2px solid #26778c;padding-bottom:8px}h3{color:#155c72}p,li{max-width:1120px}table{border-collapse:collapse;width:100%;font-size:14px;line-height:1.6}th,td{border:1px solid #cbd5df;padding:10px;text-align:left;vertical-align:top;white-space:pre-wrap;overflow-wrap:anywhere}th{background:#e8f1f5}tr:nth-child(even){background:#f8fafc}.scroll{overflow:auto;margin:18px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#eff3f7;padding:16px;font-size:13px}details{background:#f8fafc;border:1px solid #ccd8df;padding:15px;margin:14px 0}summary{cursor:pointer;font-weight:600}a{color:#126784}.case{border-top:3px solid #c6dde6;margin:30px 0;padding-top:12px}.case> .scroll table{table-layout:fixed}.case th:first-child{width:8%}.source{font-size:17px;font-weight:bold;background:#eef6f7;padding:15px}nav{display:flex;gap:15px;flex-wrap:wrap;padding:15px;background:#e8f1f5}input{padding:10px;width:300px;max-width:90%;font-size:16px}.filter{display:block;margin:20px 0}.meta{color:#4b6373}.hidden{display:none}@media print{body{background:white}main{max-width:none;padding:0}nav,.filter{display:none}details{display:block}details>*{display:block!important}table{font-size:10px}h2{break-before:page}tr{break-inside:avoid}.case{break-before:page}.hidden{display:block}}'''
doc='<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>'+e(methods['title'])+'</title><style>'+css+'</style></head><body><main><h1>'+e(methods['title'])+'</h1><p class="meta">50개 발화 · 3조건 · 최초/최종 출력 · 실제 요청·근거 추적 · 2026-10-21</p><nav>'+''.join(f'<a href="#{a}">{s}</a>' for a,s in [('summary','핵심'),('results','결과'),('method','방법'),('kg','KG'),('prompt','실제 흐름'),('dataset','50개 원문'),('cases','150개 비교'),('handoff','이관 파일')])+'</nav>'+''.join(parts)+'''</main><script>document.getElementById('search').addEventListener('input',function(){let q=this.value.toLowerCase();document.querySelectorAll('.case').forEach(x=>x.classList.toggle('hidden',!x.textContent.toLowerCase().includes(q)));});</script></body></html>'''
(P/'report.html').write_text(doc);(P/'notion_report.txt').write_text('\n'.join(notion))
run.verify()
verification={'verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'unique_inputs':len({d['standard'] for d in dataset}),'successful_cells':len(outputs),'annotations':len(annotations),'accepted_repair_annotations':len(overrides),'production_hashes_unchanged':True,'frozen_requests_unchanged':True,'dataset_unchanged':True,'html_bytes':len(doc.encode()),'metrics_sha256':run.sha(P/'metrics.json'),'report_sha256':run.sha(P/'report.html')}
save(P/'verification.json',verification)
print(pretty({'verification':verification,'metrics':metrics}))

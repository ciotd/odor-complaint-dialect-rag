"""Readable revision; reuse frozen experimental results without new model calls."""
import html,json
from pathlib import Path
P=Path(__file__).resolve().parents[1]
def read(name):return json.loads((P/name).read_text())
def esc(s):return html.escape(str(s))
metrics=read('metrics.json');data=read('논문용_테스트_데이터셋.json')
rows={(r['id'],r['condition']):r for r in read('final_outputs.json')}
methods=read('methods.json');h=[];n=[]
labels={'P':'원문만 제공','A':'문장 분석 추가','K':'문장 분석과 KG 지식 추가'}
def heading(s):h.append('<h2>'+esc(s)+'</h2>');n.append('## '+s+'\n')
def para(s):h.append('<p>'+esc(s)+'</p>');n.append(s+'\n')
def bullets(ss):h.append('<ul>'+''.join('<li>'+esc(s)+'</li>' for s in ss)+'</ul>');n.append('\n'.join('- '+s for s in ss)+'\n')
def table(cols,rs,native=True):
 rs=list(rs);h.append('<div class="table"><table><thead><tr>'+''.join('<th>'+esc(s)+'</th>' for s in cols)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+esc(s)+'</td>' for s in r)+'</tr>' for r in rs)+'</tbody></table></div>')
 if native:n.append('<table header-row="true">\n<tr>'+''.join('<td>'+esc(s)+'</td>' for s in cols)+'</tr>\n'+'\n'.join('<tr>'+''.join('<td>'+esc(s)+'</td>' for s in r)+'</tr>' for r in rs)+'\n</table>\n')
heading('1. 연구 목적')
para('본 연구는 표준어를 경상도 방언으로 변환할 때, 문장 분석과 방언 지식을 함께 제공하는 방법이 번역에 어떤 도움을 주는지 살펴본다. 동일한 언어 모델 Qwen에 제공하는 정보를 달리하고, 원래 의미와 높임이 유지되는지, 자연스러운 방언 표현이 나타나는지를 비교했다.')
para('KG(지식 그래프)는 방언 표현과 사용 조건, 출처를 서로 연결해 놓은 지식 모음이다. 예를 들어 “먹다와 묵다의 대응”, “질문할 때 쓰는 어미”, “높임말을 유지하는 방법”을 찾아 번역에 참고하도록 한다.')
heading('2. 제안 방법: 문장을 분석하고 알맞은 방언 지식을 제공')
table(['단계','쉽게 설명하면','결과'],[
 ['① 방언 지식 준비','학술 문헌 3종과 웹 자료 4종, 총 7종의 PDF에서 텍스트를 추출한다. Astra가 표현·사용 조건·근거를 정리하고 검토한다.','3,767개 지식 항목을 표현·조건·출처와 연결'],
 ['② 표준어 분석','Qwen은 질문인지 설명인지, 높임말인지 등을 분석한다. Kiwi는 단어와 어미를 나누어 살핀다.','어느 부분을 어떻게 바꿔야 하는지 찾는 데 필요한 정보'],
 ['③ 맞는 지식 찾기','분석 결과를 이용해 KG에서 관련 표현을 찾고, 확인 가능한 사용 조건을 검사한다.','해당 문장에 참고할 방언 후보'],
 ['④ 변환 방법 전달','어느 부분에 어떤 후보를 쓸 수 있는지, 무엇을 유지해야 하는지 정리해 원문과 함께 준다.','Qwen이 참고할 짧은 변환 계획'],
 ['⑤ 방언 문장 생성','Qwen이 전체 문맥을 보면서 방언 문장을 만든다.','첫 번역 결과'],
 ['⑥ 의미·높임 확인','검사 코드가 일부 의미 변화와 높임 손실을 찾는다. 뚜렷한 경고가 있으면 Qwen에 한 번 수정을 요청한다.','검사 및 수정 후 최종 번역']])
para('방언 지식은 참고 자료다. 조회된 후보가 있어도 모델이 사용하지 않거나 잘못 사용할 수 있으므로, “자료를 찾았는가”와 “번역에 제대로 반영됐는가”를 따로 확인했다.')
heading('3. 비교 실험 조건')
para('세 조건 모두 같은 표준어를 입력하고, 같은 Qwen 모델에 “의미와 높임을 유지하면서 자연스러운 경상도 방언으로 바꿔 달라”고 요청한다. 차이는 번역할 때 참고할 정보를 얼마나 주는지다. P·A·K는 모델 이름이 아니라 실험 조건을 구별하는 표시다.')
table(['실험 조건','기존 표시','AI에게 제공하는 것','확인하려는 점'],[
 ['원문만 제공','P','공통 번역 지시 + 표준어 원문','모델이 이미 알고 있는 지식만으로 얼마나 번역하는가?'],
 ['문장 분석 추가','A','공통 번역 지시 + 원문 + 문장의 의미·높임·단어·어미 분석과 보존 지침. 방언 참고 자료는 주지 않음','문장을 분석해 알려 주는 것만으로 번역이 좋아지는가?'],
 ['문장 분석과 KG 지식 추가','K','문장 분석 조건의 모든 정보 + 해당 문장에 맞는 방언 표현 후보·사용 조건·출처·변환 지침','분석에 더해 방언 지식을 제공하면 어떤 도움이 되는가?']])
para('같은 문장으로 보면 차이가 더 분명하다. 아래는 실제 입력에 담긴 정보를 쉽게 풀어쓴 설명이다.')
table(['조건','“아까 문 앞에 있던 사람이 제 친구예요.”를 번역할 때'],[
 [labels['P'],'원문을 읽고 스스로 사투리 표현을 만들어야 한다.'],
 [labels['A'],'원문에 더해 “친구라고 설명하는 문장이고, 듣는 사람에게 높임말을 쓰고 있다”는 분석을 받는다. 그러나 사용할 방언 어미는 알려 주지 않는다.'],
 [labels['K'],'같은 분석에 더해 “이 문장의 예요에는 라예를 후보로 검토하고, 제라는 표현과 높임 수준은 유지하라”는 자료를 받는다.']])
bullets(['원문만 제공 ↔ 문장 분석 추가: 분석 정보를 더한 차이를 본다.',
 '문장 분석 추가 ↔ 문장 분석과 KG 지식 추가: 방언 후보와 적용 지침을 더한 차이를 본다.',
 '원문만 제공 ↔ 문장 분석과 KG 지식 추가: 제안한 시스템 전체가 기본 번역에 비해 어떤 차이를 만드는지 본다.'])
heading('4. 실험 설정과 평가 방법')
table(['항목','실험 내용'],[
 ['대상','표준어 발화 50개. 한 발화가 여러 문장으로 이루어진 경우도 포함'],
 ['생성 모델','Qwen3.8-27B: 세 조건 모두 동일'],
 ['비교 결과','50개 × 3조건 = 최초 번역 150개. 같은 검사 절차를 적용한 최종 번역도 함께 저장'],
 ['분석 정보','기존 Qwen 분석을 두 분석 조건에서 동일하게 사용. 단어·어미 분석과 KG 조회는 다시 수행'],
 ['평가 기준','의미 보존, 높임 보존, 문장 자연스러움, 방언 표현의 실현'],
 ['평가 방법','정답 번역이 없어 원문과 출력을 항목별로 대조한 Codex의 정성 분석. 독립 방언 화자 평가는 아직 수행하지 않음']])
para('대상 50개는 이전 KG 번역 결과가 상대적으로 양호했던 사례에서 선정했으므로, 아래 결과는 이 사례들에서의 비교이며 새로운 문장 전반의 성능을 나타내지는 않는다.')
heading('5. 실험 결과')
para('이번 50개에서는 문장 분석에 KG 지식까지 제공했을 때 높임과 방언 종결 표현이 더 안정적으로 나타났다. 문장 분석만 추가한 조건에서는 같은 개선이 나타나지 않았다.')
para('아래 표는 첫 번역 결과를 비교한 것이다. 의미·높임·자연스러움은 “뚜렷한 문제 없음”, 방언 표현은 “충분히 나타남”으로 평가한 건수다. 각 열의 대상은 50개이며 정확도 점수를 뜻하지 않는다.')
table(['평가 항목',labels['P'],labels['A'],labels['K']],[[label]+[f"{metrics['conditions'][c]['first_scores'][key]['distribution']['2']} / 50" for c in 'PAK'] for key,label in [('meaning','원래 의미 유지'),('register','높임 수준 유지'),('fluency','문장이 자연스럽게 이어짐'),('dialect','방언 표현이 충분히 나타남')]])
para('실제 첫 번역 예시')
table(['원문',labels['P'],labels['A'],labels['K']],[[rows[sid,'P']['input']]+[rows[sid,c]['first_output'] for c in 'PAK'] for sid in ['DEV004','DEV011','DEV017','NEW007']])
bullets(['친구예요: KG 조건에서는 친구라예가 나와 설명하는 문장과 높임을 함께 유지했다.',
 '출발했나요?: KG 조건에서는 출발했는교?로 바뀌어 과거의 질문과 높임을 함께 유지했다.',
 '문 좀 닫아 주세요: 세 조건 모두 주이소를 생성했다. 모든 성공이 KG 때문에 새로 생긴 것은 아니다.',
 '천천히 와: KG가 온나를 후보로 전달했지만 번역에서는 와가 남았다. 조회 성공이 적용 성공을 보장하지 않는 사례다.'])
para('자동 수정 후에는 원문만 제공한 조건과 문장 분석 조건에서도 높임이 일부 회복됐다. 다만 표준어로 되돌아온 사례가 많았다. 따라서 의미·높임을 지키는 것과 사투리 표현을 만들어 내는 것은 따로 살펴봐야 한다.')
table(['자동 수정 후 관찰',labels['P'],labels['A'],labels['K']],[[label]+[metrics['conditions'][c][key] for c in 'PAK'] for key,label in [('repairs','수정 요청을 받은 입력 수'),('accepted','수정된 번역을 채택한 입력 수'),('final_identical','최종 번역이 원문과 완전히 같은 입력 수')]])
heading('6. 결과 해석')
table(['확인한 점','해석'],[
 ['문장 분석만으로는 충분하지 않았다.','어떤 문장인지 설명하는 정보와 실제 사용할 방언 표현은 역할이 다르다.'],
 ['구체적인 방언 후보와 사용 지침이 도움이 되는 양상이 나타났다.','KG 조건에서 라예·는교·주이소·께예 등의 종결 표현이 더 안정적으로 나타났다.'],
 ['후보 미적용과 말투 혼용은 남았다.','온나를 주어도 사용하지 않는 사례와 맛있소·주이소 같은 높임 계열이 섞이는 사례가 있었다.'],
 ['검사가 모든 오류를 잡지는 못했다.','KG 조건의 가는 길→가던 길 변화는 수정됐지만, 다른 조건에서는 기차에 계신가요를 붙여도 검사를 통과했다.'],
 ['이 실험은 KG 지식과 변환 지침을 묶어 제공한 효과를 비교했다.','그래프 연결 자체만의 효과나 모든 새로운 문장에서의 성능을 따로 입증한 것은 아니다.']])
para('이번 사례 비교에서, 문장 분석과 함께 적용 가능한 방언 지식을 제공하는 방식은 높임과 종결 표현을 유지하는 데 도움이 되는 양상을 보였다. 남은 과제는 찾아낸 후보를 문맥에 맞게 적용하고, 여러 어미가 결합된 표현과 말투의 일관성을 다루는 것이다.')
heading('부록. 결과와 근거를 더 확인하려면')
h.append('<details><summary>50개 원문과 세 조건의 첫 번역 펼치기</summary>')
table(['ID','원문',labels['P'],labels['A'],labels['K']],[[d['id'],d['standard']]+[rows[d['id'],c]['first_output'] for c in 'PAK'] for d in data],native=False)
h.append('</details>')
h.append('<details><summary>원문 자료 7종과 기술 설명 펼치기</summary>')
table(['자료','내용'],list(methods['source_notes'].items()),native=False)
table(['세 조건에 공통으로 적용한 생성 설정','값'],[['모델','Qwen3.8-27B'],['출력 길이 상한','512 토큰'],['표현 선택 관련 설정','temperature 0.3 / top_p 0.8 / top_k 20'],['난수 설정','seed 20260923'],['추론 표시 설정','enable_thinking=false']],native=False)
h.append('<p>상세한 지식 유형·노드·관계, 실제 요청 형식, 설정과 개별 오류 근거는 <a href="report.html">기존 상세 보고서</a>에 보관했다. 자료 출처와 결과 기록은 그대로 유지했다.</p></details>')
h.append('<p><a href="논문용_테스트_데이터셋.txt">표준어 50개 목록</a> · <a href="translations.txt">최초·최종 번역 전체</a> · <a href="report.html">기술 상세 보고서</a></p>')
n.append('전체 원문·번역·개별 판정은 아래 하위 페이지에서, 자료 출처와 기술 설명은 첨부된 상세 보고서에서 확인할 수 있다.\n')
style='''body{margin:0;background:#f3f6f8;color:#213343;font-family:Arial,"Noto Sans KR",sans-serif;line-height:1.85}main{max-width:1100px;padding:40px;margin:auto;background:#fff}h1{font-size:29px;line-height:1.45}h2{font-size:22px;margin-top:42px;border-bottom:2px solid #3a7c89;padding-bottom:8px}p,li{font-size:16px}table{width:100%;border-collapse:collapse;font-size:14px;line-height:1.65}th,td{border:1px solid #d1dce2;padding:12px;vertical-align:top;text-align:left;overflow-wrap:anywhere}th{background:#e7f1f3}.table{overflow-x:auto;margin:20px 0}details{background:#f5f8fa;padding:15px;margin:18px 0}summary{cursor:pointer;font-weight:bold}a{color:#216b86}.lead{border-left:5px solid #3a7c89;padding:12px 20px;background:#edf5f5}.date{color:#5b6f80}@media print{body{background:white}main{max-width:none;padding:0}h2{break-after:avoid}tr{break-inside:avoid}details:not([open]){display:none}}'''
doc='<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>문장 분석과 방언 지식을 활용한 표준어–경상도 방언 변환 실험</title><style>'+style+'</style></head><body><main><h1>문장 분석과 방언 지식을 활용한<br>표준어–경상도 방언 변환 실험</h1><p class="date">학술대회 논문 작성용 정리 · 50개 발화 · 세 가지 조건 비교 · 2026-10-22 개정</p><p class="lead">동일한 모델에 원문만 제공한 경우, 문장 분석을 추가한 경우, 분석과 방언 지식을 함께 제공한 경우를 비교했다.</p>'+''.join(h)+'</main></body></html>'
(P/'easy_report.html').write_text(doc);(P/'notion_easy_report.txt').write_text('\n'.join(n))
assert len(data)==50 and len(rows)==150
print(json.dumps({'html_bytes':len(doc.encode()),'conditions':labels,'new_model_calls':0},ensure_ascii=False))

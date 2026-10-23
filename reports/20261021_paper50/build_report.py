"""Build the single conference report from frozen evidence; no model calls."""
import collections,html,json,re,sys
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P))
import run
run.verify()
def read(n):return json.loads((P/n).read_text())
def e(s):return html.escape(str(s))
D=read('논문용_테스트_데이터셋.json');M=read('metrics.json');A=read('annotations.json');O=read('final_outputs.json');T=read('candidate_trace.json');METHOD=read('methods.json')
OM={(x['id'],x['condition']):x for x in O};AM={(x['id'],x['condition']):x for x in A};TM={x['id']:x for x in T}
CN={'P':'원문만 제공','A':'문장 분석 추가','K':'분석과 KG 지식 추가'}
DIM={'meaning':'의미 보존','register':'높임 보존','fluency':'문장 자연스러움','dialect':'방언 표현'}
COL={'P':'#718298','A':'#458fb2','K':'#087f73'}
S=read('snapshot/kg_v2/source_registry.json')['sources'];SN={x['source_id']:x['title'] for x in S}
F=[json.loads(l) for l in (P/'snapshot/kg_v2/facts.jsonl').read_text().splitlines()];G=read('snapshot/kg_v2/graph.json')
FC=collections.Counter(x['type'] for x in F);NC=collections.Counter(x['type'] for x in G['nodes']);EC=collections.Counter(x['type'] for x in G['edges'])
assert len(D)==50 and len(A)==len(O)==150
parts=[]
def section(id,title):parts.append(f'<section id="{id}"><h2>{e(title)}</h2>')
def end():parts.append('</section>')
def p(s,cls=''):parts.append(f'<p class="{cls}">{e(s)}</p>')
def ul(ss):parts.append('<ul>'+''.join('<li>'+e(s)+'</li>' for s in ss)+'</ul>')
def table(head,rows):parts.append('<div class="table-wrap"><table><thead><tr>'+''.join('<th scope="col">'+e(x)+'</th>' for x in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+e(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table></div>')
def svgtext(x,y,s,size=22,anchor='start',fill='#213549',bold=False):return f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" fill="{fill}" font-weight="{700 if bold else 400}">{e(s)}</text>'
def make_bars(phase):
 s='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1120 560" role="img" aria-label="평가 항목별 긍정 판정 건수, 조건당 50개" class="chart"><rect width="1120" height="560" fill="white"/>'
 for i,(key,label) in enumerate(DIM.items()):
  x=20+(i%2)*560;y=25+(i//2)*280;s+=svgtext(x,y+12,label,26,bold=True)
  for j,c in enumerate('PAK'):
   v=M['conditions'][c][phase+'_scores'][key]['distribution']['2'];yy=y+49+j*54
   s+=svgtext(x,yy+23,CN[c],19)
   s+=f'<rect x="{x+201}" y="{yy}" width="270" height="30" rx="4" fill="#edf1f4"/><rect x="{x+201}" y="{yy}" width="{v/50*270}" height="30" rx="4" fill="{COL[c]}"/>'
   s+=svgtext(x+486,yy+23,f'{v}/50',20,bold=True)
  s+=svgtext(x+201,y+244,'0',16,fill='#667587')+svgtext(x+471,y+244,'50개',16,anchor='end',fill='#667587')
 s+='</svg>';return s
def network():
 s='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1120 710" role="img" aria-label="지식 항목과 표현, 조건, 기능, 원문 근거의 연결 예시" class="chart"><defs><marker id="kg-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 Z" fill="#677c8b"/></marker></defs><rect width="1120" height="710" fill="white"/>'
 def edge(x1,y1,x2,y2,label,lx,ly):return f'<path d="M{x1},{y1} L{x2},{y2}" stroke="#677c8b" stroke-width="2" fill="none" marker-end="url(#kg-arrow)"/>'+svgtext(lx,ly,label,18)
 s+=edge(470,230,220,130,'입력 표현',345,171)+edge(650,230,900,130,'대응 표현',690,171)
 s+=edge(435,285,240,345,'적용 조건',280,320)+edge(685,285,880,345,'사용 기능',755,320)
 s+=edge(495,315,245,510,'주의 사항',370,450)+edge(625,315,700,500,'근거',675,420)
 s+=edge(795,540,910,540,'수록 쪽',812,525)+edge(1000,580,1000,630,'출처',1010,615)
 def box(x,y,w,h,title,lines,color='#f0f5f7'):
  r=f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{color}" stroke="#78909e" stroke-width="1.5"/>'+svgtext(x+w/2,y+32,title,23,'middle',bold=True)
  for j,line in enumerate(lines):r+=svgtext(x+w/2,y+65+j*29,line,20,'middle')
  return r
 s+=box(70,50,270,95,'표현 노드',['-이에요'])+box(780,50,270,95,'표현 노드',['-이라예'])
 s+=box(410,205,300,110,'지식 항목 노드',['이에요 ↔ 이라예','내용 분류: 종결어미'],'#dcefeb')
 s+=box(40,345,320,125,'조건 노드',['이다 구성인지 확인','과거·높임 중간 어미 여부 확인'])
 s+=box(790,345,280,95,'기능 노드',['설명하는 문장'])
 s+=box(50,510,340,130,'제약 노드',['명사·시제·높임 보존','지역·세대의 사용 범위 확인'])
 s+=box(520,500,275,100,'근거 노드',['원문의 대응표·예문'])
 s+=box(910,500,200,80,'페이지 노드',['PDF 22·28쪽'])
 s+=box(850,630,260,75,'문헌 노드',['동남 방언/문법'])
 return s+'</svg>'

section('overview','연구 목적')
p('표준어를 경상도 방언으로 바꿀 때는 단어뿐 아니라 질문·요청·높임 표현도 함께 다뤄야 한다. 이 연구는 같은 언어 모델에 제공하는 정보를 달리하여, 문장 분석과 방언 지식이 의미와 높임을 유지하는 데 어떤 도움을 주는지 살펴본다.')
parts.append('<div class="numbers"><div><strong>50</strong><span>표준어 발화</span></div><div><strong>3</strong><span>비교 조건</span></div><div><strong>150</strong><span>새로 생성한 최초 번역</span></div></div>')
table(['용어','이 보고서에서의 뜻'],[
 ['KG · 지식 그래프','방언 표현, 사용 조건, 출처를 서로 연결한 지식 모음'],['지식 항목','하나의 대응 표현이나 사용법을 조건·근거와 함께 기록한 묶음'],
 ['노드 / 관계','노드는 저장하는 요소, 관계는 요소 사이 연결의 의미'],['속성','표현·지역·쪽 번호처럼 각 요소에 적어 둔 정보'],
 ['변환 계획','어느 구간에 어떤 후보를 쓰고 무엇을 유지할지 정리한 지침'],['프롬프트','모델에 전달하는 작업 지시와 입력 자료'],['Qwen / Kiwi','Qwen은 문장 분석·생성 모델, Kiwi는 단어와 어미를 나누어 분석하는 도구']])
end()
section('related','설계에 참고한 연구')
parts.append('<div class="references"><article><h3>관련 지식을 찾아 모델의 입력에 제공</h3><p><a href="https://aclanthology.org/2023.nlrse-1.7/">Baek·Aji·Saffari (2023), Knowledge-Augmented Language Model Prompting for Zero-Shot Knowledge Graph Question Answering</a></p><p>질문과 관련된 그래프 지식을 찾아 텍스트로 정리하고 모델의 입력에 더하는 KAPING 방법이다. 이 연구에서는 “필요한 지식을 찾아 생성 입력에 제공한다”는 관점을 참고했다. 현재 방언 변환은 기본형·문법 조건과 일부 관계를 이용해 후보를 찾는다.</p></article><article><h3>평가 항목을 나누고 판단 근거를 기록</h3><p><a href="https://aclanthology.org/W19-8643/">van der Lee 외 (2019), Best practices for the human evaluation of automatically generated text</a></p><p>생성문 평가의 항목과 절차를 명확하게 제시하는 연구다. 의미·높임·자연스러움·방언 표현을 구분하고 사례별 근거를 기록하는 데 참고했다. 이번 평가는 독립적인 사람 평가가 아니라 Codex의 정성 분석이다.</p></article></div>')
parts.append('<details><summary>지식 구축·입력 분석·결과 해석의 배경 연구</summary><div class="table-wrap"><table><thead><tr><th>연구</th><th>핵심 아이디어와 연결점</th></tr></thead><tbody><tr><td><a href="https://aclanthology.org/2024.emnlp-main.548/">EDC · Zhang와 Soh (2024)</a></td><td>문장에서 지식을 추출하고 관계의 뜻을 정리·통합한다. 여러 문헌의 정보를 공통 구조로 묶는 문제를 이해하는 배경이다.</td></tr><tr><td><a href="https://arxiv.org/abs/2402.18025">LingoLLM · Zhang 외 (2024)</a></td><td>형태 분석·사전·문법 설명을 모델 입력에 제공한다. 입력 분석과 언어 지식을 함께 사용하는 접근의 선행 사례다.</td></tr><tr><td><a href="https://arxiv.org/abs/2305.18846">SURGE · Kang 외 (2023)</a></td><td>관련 그래프 정보를 찾고 생성문에 반영하도록 학습한다. 우리 분석에서는 “찾았는가”와 “출력에 반영됐는가”를 구분하는 관점을 참고한다.</td></tr></tbody></table></div><p>이 연구들의 학습·검색 알고리즘을 그대로 구현한 것은 아니다. 현재 시스템의 실제 동작은 아래 처리 과정과 비교 조건에 따른다.</p></details>')
end()
section('pipeline','전체 처리 과정')
pipeline=(P/'figures/kg_pipeline_K.svg').read_text();pipeline=re.sub(r'<\?xml.*?\?>','',pipeline);pipeline=re.sub(r'width="180mm" height="118.75mm"','class="pipeline"',pipeline)
parts.append('<figure>'+pipeline+'<figcaption>문장 분석과 KG 지식을 함께 제공하는 조건의 처리 구조. 원문만 제공하는 조건은 분석·지식 자료를 생략하고, 문장 분석 조건은 방언 후보와 관계 정보를 생략한다.</figcaption></figure>')
table(['모듈','하는 일','다음 단계에 전달하는 것'],[
 ['지식 구축','PDF에서 텍스트를 추출하고 Astra로 대응 표현·조건·근거를 정리·검토','지식 항목과 그래프'],
 ['문장 분석','Qwen이 문장 의미·질문/요청·높임을 분석하고 Kiwi가 단어·어미를 분석','원문 구간, 기본형, 기능, 높임, 시제 정보'],
 ['조회와 변환안 작성','지식 항목을 검색하고 어휘–활용 연결을 따라가며, 종결·복합 표현의 적용안을 작성','조건을 확인한 후보와 입력 구간별 적용안'],
 ['후보 선택','기능·높임·구체적인 대응을 고려하고 중복과 분량을 제한','원문에 맞춰 선택한 후보'],
 ['생성 입력 구성','원문·분석·변환 계획·선택된 관계·보존 지침을 묶음','Qwen에 전달할 입력'],
 ['번역과 보존 검사','Qwen이 번역하고 코드가 일부 의미·높임 변화를 검사. 강한 경고가 있으면 최대 한 번 수정 요청','최초 출력과 최종 선택 결과']])
p('조건 검사는 조회 과정에 포함된다. 종결 변환안도 후보를 최종 선택하기 전에 만들어질 수 있다. 두 조회 방식은 독립적인 병렬 에이전트가 아니라 같은 조회 코드 안에서 사용하는 경로다.')
end()
section('knowledge','최종 KG 구성')
p(f'7종·474쪽의 자료를 바탕으로 지식 항목 {len(F):,}개를 구성했다. 그래프에는 노드 {len(G["nodes"]):,}개와 관계 {len(G["edges"]):,}개가 있다. 지식 항목은 JSON 형식으로 저장하고, 같은 정보를 노드와 관계로 펼친 그래프도 함께 저장한다.')
table(['구축 순서','수행 내용'],[['1. 원문 추출','PDF 변환 프로그램(pdftotext)이 쪽별 텍스트를 추출한다. 복잡한 표 등은 원문 이미지와 대조한다.'],['2. 지식 작성','Astra가 표현의 대응, 사용 조건, 예외, 출처와 쪽 번호를 공통 형식으로 작성한다.'],['3. 분담 검토','전체 문헌 작업 후 남은 항목은 Astra 작업자 3개가 나누어 검토하고 조정자가 통합·원문 대조한다.'],['4. 구조 검사와 연결','코드가 필수 정보·근거 페이지·인용문을 확인하고 지식 항목을 표현·조건·근거 노드와 연결한다.']])
parts.append('<figure>'+network()+'<figcaption>실제 “-이에요 ↔ -이라예” 지식 항목의 연결 구조를 읽기 쉽게 묶은 예. 조건·제약·근거는 실제 그래프에서 여러 노드로 나뉜다.</figcaption></figure>')
table(['구분','무엇을 구분하는가','구성'],[
 ['지식 유형 9개','항목이 설명하는 내용','어휘 대응, 활용, 어미, 복합 구성, 조사, 음운, 사용 설명, 제약, 배경'],
 ['노드 유형 8개','저장하는 요소','지식 항목, 표현, 조건, 제약, 기능, 근거, 페이지, 문헌'],
 ['관계 유형 19개','연결의 의미','입력·대응 표현 연결, 조건·기능 연결, 근거·출처 연결, 사용·제약 설명, 어휘–활용 연결']])
table(['지식 항목에 담는 정보','역할','예시'],[['입력 표현과 대응 표현','무엇을 무엇으로 바꿀 수 있는가','-이에요 ↔ -이라예'],['기능과 적용 조건','지금 문장에 사용할 수 있는가','설명하는 문장, 이다 구성'],['범위와 제약','어느 지역·상황에서 주의해야 하는가','지역·세대 차이, 시제·높임 보존'],['원문 근거','어디에서 확인한 정보인가','출처 문서, PDF 쪽, 인용문']])
p('지식 항목은 그래프와 별개인 추가 지식이 아니라, 표현·조건·근거를 한 묶음으로 다루는 단위다. 현재 조회는 이 항목을 직접 찾는 방식과 일부 어휘–활용 관계를 따라가는 방식을 함께 사용한다.')
p('문헌에서 직접 확인한 정보, 문헌의 구성요소를 입력에 맞게 조합한 변환안, 외부 모델의 조언은 출처 성격을 구별한다. 이번 50건에 실제 전달된 후보는 문헌 항목 134건과 문헌 구성요소를 조합한 계획 55건이었다.')
parts.append('<details><summary>자료 7종과 지식 유형별 규모</summary>')
table(['자료','내용','PDF 쪽수'],[[s['title'],METHOD['source_notes'].get(s['source_id'],s['title']),s['file']['pages']] for s in S])
table(['지식 내용','항목 수'],[[v,FC[k]] for k,v in METHOD['fact_types'].items()]);parts.append('</details>')
end()
section('conditions','비교 조건과 생성 지시')
table(['조건','모델에 제공하는 것','확인하는 차이'],[[CN['P']+' (P)','공통 번역 지시와 표준어 원문','모델이 스스로 수행하는 변환'],[CN['A']+' (A)','원문 + 문장 분석 + Kiwi 정보 + 원문 보존 지침. 방언 후보는 제외','분석 정보를 추가한 차이'],[CN['K']+' (K)','분석 조건의 정보 + 방언 후보·적용 지침·출처·선택된 관계','구체적인 방언 지식을 추가한 차이']])
p('P·A·K는 모델 이름이 아니라 입력 조건을 구별하는 표시다. 세 조건 모두 동일한 Qwen3.8-27B를 사용했다. 분석 조건과 KG 조건은 같은 분석을 사용하고, 생성기에 전달하는 지식 자료만 달리했다.')
table(['원문 예시','조건별로 추가하는 정보'],[['아까 문 앞에 있던 사람이 제 친구예요.','원문만: 스스로 변환 / 분석 추가: 명사로 설명하는 높임 문장임을 제공 / KG 추가: 예요에 라예를 후보로 추천하고 의미·높임 유지 지시']])
cfg=read('protocol.json')['config'];req=read('raw/DEV004_K.json')['request']
parts.append('<blockquote>'+e(req['messages'][0]['content'])+'</blockquote>')
table(['추가로 전달한 지시','뜻'],[['원문이 우선','분석이나 후보와 원문이 충돌하면 원문을 따른다.'],['조건에 맞는 후보만 사용','제공된 후보를 모두 적용하지 않는다.'],['의미·높임 보존','부정·시제·질문/요청·저/제와 높임을 어휘 치환보다 우선한다.'],['변경 범위 제한','지정한 종결·구성에 적용하며 같은 말끝에 여러 후보를 겹치지 않는다.'],['출력 형식','내용을 추가하지 않고 변환한 발화만 출력한다.']])
parts.append('<details><summary>모델 설정과 실제 전달량</summary>')
table(['설정','공통 값'],[['모델 식별자','Qwen3.8-27B'],['출력 길이 상한','512 토큰'],['표현 선택 설정','temperature 0.3 / top_p 0.8 / top_k 20'],['난수 설정','seed 20260923'],['추론 표시 설정','enable_thinking=false'],['Qwen 분석','저장된 분석을 재사용; 새 분석 모델 호출 없음']])
table(['KG 조건의 전달량','실제 측정값'],[['입력당 대상 구간 수','평균 2.24개, 최소 1개·최대 9개'],['구간당 후보 수','평균 1.69개, 최대 6개'],['구간당 후보 설명 길이','평균 2,248자: 속성 이름·조건·출처를 포함한 직렬화 글자 수'],['입력당 조회 자료 묶음','평균 7,703자; 제한 24,000자는 구간별이 아니라 입력 전체에 적용'],['전체 사용자 메시지 길이','원문만 26.5자 / 분석 추가 4,071.7자 / KG 추가 10,292.2자'],['선택된 관계 경로','50개 중 5개 입력에 전달, 총 11개 연결']]);parts.append('</details>')
p('따라서 이 비교는 그래프 연결만의 효과가 아니라, 지식 후보와 문장에 맞춘 변환 지침을 함께 제공한 효과를 살펴본다.')
end()
section('evaluation','실험 데이터와 평가 방법')
p('대상 50개는 이전 KG 번역 결과가 상대적으로 양호했던 사례에서 선정했으므로, 아래 결과는 이 사례들에서의 비교이며 새로운 문장 전반의 성능을 나타내지는 않는다.')
p('50개 입력에 세 조건을 적용해 최초 번역 150개를 새로 생성했다. 모든 조건에 같은 보존 검사를 적용했고, 수정이 필요한 경우 최대 1회 재검토했다. 주 비교는 최초 출력이며 최종 출력은 별도로 제시한다.')
table(['평가 항목','살펴본 내용'],[['의미 보존','누가 무엇을 하는지, 부정·시간·이동 방향·질문/요청 의도가 유지되는가'],['높임 보존','상대방과 문장 속 인물을 높이는 표현, 저/제의 겸양이 유지되는가'],['문장 자연스러움','문장 구조와 어미 연결이 어색하지 않은가'],['방언 표현','문맥에 맞는 경상도 방언 표현이 충분히 나타나는가']])
p('정답 번역이 없어 원문과 출력을 대조한 Codex의 정성 판정을 사용했다. 독립 방언 화자 평가는 수행하지 않았다. 각 항목은 “뚜렷한 문제 없음·충분한 실현”, “부분 보존·부분 실현 또는 우려”, “뚜렷한 손상·미실현”으로 구분했고, 합산 정확도는 계산하지 않았다.')
end()
section('results','전체 결과')
parts.append('<div class="phase-controls" role="group" aria-label="비교할 출력"><button class="active" data-phase="first" aria-pressed="true">첫 번역</button><button data-phase="final" aria-pressed="false">검사·수정 후 최종 번역</button></div>')
p('그래프는 의미·높임·자연스러움에서 뚜렷한 문제가 없거나, 방언 표현이 충분하다고 판정한 건수다. 각 조건의 전체 입력은 50개다.')
for phase in ['first','final']:
 parts.append(f'<div class="phase-panel" data-show="{phase}"'+(' hidden' if phase=='final' else '')+'>')
 parts.append('<h3>'+('첫 번역 결과' if phase=='first' else '검사·수정 후 최종 결과')+'</h3>'+make_bars(phase))
 table(['평가 항목']+[CN[c] for c in 'PAK'],[[label]+[f"{M['conditions'][c][phase+'_scores'][key]['distribution']['2']} / 50" for c in 'PAK'] for key,label in DIM.items()]);parts.append('</div>')
ul(['첫 번역에서 KG 조건은 높임과 방언 표현을 더 안정적으로 유지하는 양상을 보였다. 문장 분석만 추가한 조건에서는 같은 개선이 나타나지 않았다.',
 '자동 수정은 원문만·분석 조건의 높임을 일부 회복했지만, 표준어로 되돌아온 사례가 많았다. 의미·높임 보존과 방언 표현 실현은 구분해 평가해야 한다.'])
table(['자동 검사·수정 기록']+[CN[c] for c in 'PAK'],[[label]+[M['conditions'][c][key] for c in 'PAK'] for key,label in [('first_identical','첫 번역이 원문과 완전히 같은 입력'),('repairs','수정 요청한 입력'),('accepted','수정본을 채택한 입력'),('final_identical','최종 번역이 원문과 완전히 같은 입력'),('final_flagged','최종 검사 경고가 남은 입력')]])
p('자동 경고가 없다는 것은 번역 정답 판정이 아니다. 기차에 “계신가요”를 붙이거나 높임을 충분히 복원하지 못한 출력이 검사를 통과한 사례도 있었다.')
end()
section('cases','사례별 비교')
table(['관찰','실제 사례','해석'],[['종결과 높임 개선','친구예요 → 친구라예 / 출발했나요? → 출발했는교?','KG 조건에서 문장 기능과 높임에 맞는 종결이 나타남'],['기본 모델도 성공','문 좀 닫아 주이소.','세 조건이 같은 표현을 생성한 사례로, 모든 성공이 KG의 추가 효과는 아님'],['후보가 있어도 미적용','천천히 와 → 온나를 추천했으나 와 유지','조회 성공과 생성 적용 성공은 다름'],['의미 변화와 복원','가는 길 → 가던 길 → 검사 후 가는 길','KG 조건에서도 의미가 달라질 수 있으며 일부는 검사로 복원'],['말투 혼용','맛있소·괜찮소·주이소가 한 발화에 등장','문헌에 있는 형태라도 문맥 전체의 말투 일관성은 별도 과제']])
parts.append('<div class="heat-controls"><label>한눈에 볼 평가 항목 <select id="dimension">'+''.join(f'<option value="{k}"'+(' selected' if k=='register' else '')+'>'+e(v)+'</option>' for k,v in DIM.items())+'</select></label><span id="heat-phase">첫 번역</span></div><div class="legend"><span class="s2">2 문제 없음·충분</span><span class="s1">1 부분·우려</span><span class="s0">0 손상·미실현</span></div><div id="heatmap" class="heatmap" aria-label="50개 입력의 조건별 평가"></div>')
p('색상표에서 입력 번호를 누르면 해당 원문과 세 조건의 번역, 평가 근거, 실제 전달된 후보를 확인할 수 있다. 표의 숫자는 항목별 정성 판정이다.')
parts.append('<label class="search-label">원문·ID 검색 <input id="search" type="search" placeholder="예: 친구, 높임, DEV004"></label>')
for d in D:
 sid=d['id'];t=TM[sid]
 parts.append(f'<details class="case" id="case-{sid}" data-search="{e(sid+" "+d["standard"])}"><summary><span class="case-id">{d["number"]:02} · {sid}</span> {e(d["standard"])}</summary>')
 for phase in ['first','final']:
  parts.append(f'<div class="phase-panel" data-show="{phase}"'+(' hidden' if phase=='final' else '')+'>')
  table(['조건','실제 번역','분석'],[[CN[c],AM[sid,c][phase+'_output'],AM[sid,c][phase+'_note']] for c in 'PAK']);parts.append('</div>')
 parts.append('<details class="candidate"><summary>KG 조건에 실제 전달된 후보와 근거</summary>')
 cr=[]
 for ca in t['candidates']:
  support='; '.join(f"{SN.get(x['source_id'],x['source_id'])} PDF {x['pdf_page']}쪽" for x in ca['evidence_pages'])
  surface=ca['preferred_surface'];obs='추천형 그대로 관찰됨' if surface and ca['preferred_surface_observed'] else '추천형 그대로는 나타나지 않음' if surface else '활용·문맥을 함께 확인해야 함'
  origin='문헌 구성요소를 조합한 계획' if ca['origin']=='documentary_components_with_analyst_composition' else '문헌 지식 항목'
  cr.append([ca['target_text'],ca['source']+' → '+ca['target']+(' / 추천: '+surface if surface else ''),origin+' · '+support,obs])
 table(['입력 구간','대응 후보','근거','첫 출력의 표면 관찰'],cr)
 p('추천형의 글자 일치는 출력에 나타났는지를 확인한 것이며, 모델 내부에서 해당 지식을 사용했다는 증명은 아니다.')
 parts.append('</details></details>')
end()
section('interpretation','결과 해석과 남은 과제')
table(['확인한 점','연구에서의 의미'],[['문장 분석만으로는 충분하지 않음','원문을 설명하는 정보와 실제 방언 표현을 제공하는 정보는 역할이 다르다.'],['조건을 붙인 지식과 적용 지침의 도움','이번 사례에서 높임·질문·약속 등에 맞는 종결 표현이 더 안정적으로 나타났다.'],['관계 탐색의 역할은 제한적','현재 시스템은 지식 항목 검색과 변환 계획의 역할이 크다. 그래프 연결만의 효과로 해석하지 않는다.'],['복합 표현과 말투 일관성은 남은 과제','인용·의도 표현의 부분 변환, 후보 미적용, 높임 계열 혼용을 추가로 다뤄야 한다.']])
p('현재 결과는 구조화한 방언 지식과 문장별 변환 지침을 결합한 시스템의 사례 비교다. 후속 평가는 새로운 입력과 방언 화자 판단을 통해 일반화 여부와 자연스러움을 확인할 수 있다.')
end()
section('files','실제 결과 파일')
parts.append('<div class="downloads"><a href="논문용_테스트_데이터셋.txt">표준어 50개 목록</a><a href="comparison.tsv">세 조건 비교표 TSV</a><a href="translations.txt">최초·최종 번역 TXT</a><a href="figures/kg_pipeline_K.svg">편집 가능한 구조도 SVG</a><a href="figures/kg_pipeline_K.png">논문용 구조도 PNG</a></div>')
p('상세 요청·응답과 검사 기록은 같은 폴더의 raw/, 조회 기록은 retrieval.json, 생성 설정은 protocol.json에 있다. 코드와 KG는 snapshot/에 고정되어 있다. 이 보고서는 저장된 결과를 읽어 만들며 새 번역을 호출하지 않는다.')
end()
payload={d['id']:{c:{'first':AM[d['id'],c]['first_scores'],'final':AM[d['id'],c]['final_scores']} for c in 'PAK'} for d in D}
css='''*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f3f6f8;color:#203447;font-family:Arial,"Noto Sans KR",sans-serif;line-height:1.8}main{max-width:1180px;margin:auto;background:#fff;padding:36px 48px}header{padding:25px 0 18px;border-bottom:3px solid #087f73}h1{font-size:32px;line-height:1.5;margin:5px 0 18px}h2{font-size:25px;margin:0 0 18px;color:#164a55}h3{font-size:19px}section{padding:38px 0;border-bottom:1px solid #dae3e8}nav{display:flex;gap:9px;flex-wrap:wrap;margin-top:24px}nav a,.downloads a{background:#edf5f5;color:#185f69;padding:8px 13px;text-decoration:none;border-radius:6px}a{color:#146c80}.numbers{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;margin:26px 0}.numbers div{border:1px solid #d5e5e3;border-radius:10px;text-align:center;padding:18px}.numbers strong{display:block;font-size:36px;color:#087f73}.numbers span{font-size:15px}table{width:100%;border-collapse:collapse;font-size:14px;line-height:1.7}th,td{border:1px solid #d7e1e6;text-align:left;vertical-align:top;padding:12px;overflow-wrap:anywhere;white-space:pre-wrap}th{background:#edf4f6}th:first-child{min-width:115px}.table-wrap{overflow:auto;margin:20px 0}blockquote{margin:20px 0;border-left:4px solid #087f73;background:#f0f6f5;padding:18px 22px}.references{display:grid;grid-template-columns:1fr 1fr;gap:20px}.references article{background:#f4f7fa;padding:20px;border-radius:10px}.references h3{margin-top:0}figure{margin:22px 0}.pipeline,.chart{display:block;width:100%;height:auto;font-family:Arial,"Noto Sans KR",sans-serif}figcaption{color:#4e6577;font-size:14px;margin-top:12px}details{border:1px solid #d8e3e8;border-radius:8px;padding:15px 18px;margin:15px 0}summary{cursor:pointer;font-weight:600}.candidate{background:#f7f9fb}.case-id{font-size:13px;color:#526f80;margin-right:8px}.case{scroll-margin-top:15px}.phase-controls{display:flex;gap:10px;flex-wrap:wrap;margin:15px 0}button{font:inherit;padding:9px 15px;border:1px solid #087f73;background:white;color:#087f73;border-radius:6px;cursor:pointer}button.active{background:#087f73;color:white}.heat-controls{display:flex;gap:20px;align-items:center;flex-wrap:wrap;margin:25px 0 15px}select,input{font:inherit;padding:8px;border:1px solid #9eb3c0;border-radius:5px}input{max-width:100%}.legend{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:15px}.legend span{padding:5px 9px;border-radius:4px;font-size:13px}.s2{background:#c6e8dd;color:#174939}.s1{background:#fae7b4;color:#674e10}.s0{background:#f3ceca;color:#702a25}.heatmap{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px}.heat-item{border:1px solid #dae2e6;padding:8px;border-radius:6px}.heat-item>a{display:block;font-size:13px;margin-bottom:5px}.heat-cells{display:grid;grid-template-columns:repeat(3,1fr);gap:3px}.heat-cells span{text-align:center;font-size:12px;border-radius:3px;padding:4px}.search-label{display:block;margin-top:26px}.downloads{display:flex;gap:12px;flex-wrap:wrap}[hidden]{display:none!important}footer{color:#647586;font-size:13px;padding-top:25px}@media(max-width:720px){main{padding:18px}h1{font-size:26px}.references{grid-template-columns:1fr}.heatmap{grid-template-columns:repeat(2,minmax(0,1fr))}.numbers{gap:8px}.numbers strong{font-size:28px}}@media print{body{background:white}main{max-width:none;padding:0}nav,.phase-controls,.heat-controls,.search-label{display:none}section{break-inside:auto;padding:22px 0}h2,h3{break-after:avoid}tr{break-inside:avoid}details:not([open]){display:none}.numbers{break-inside:avoid}svg{max-height:160mm}a{color:inherit;text-decoration:none}}'''
script='''let phase="first";const scores=JSON.parse(document.getElementById("scores").textContent);const names={P:"원문만",A:"분석 추가",K:"KG 추가"};function heat(){const dim=document.getElementById("dimension").value;let target=document.getElementById("heatmap");target.replaceChildren();Object.entries(scores).forEach(([id,cc])=>{let item=document.createElement("div");item.className="heat-item";let a=document.createElement("a");a.href="#case-"+id;a.textContent=id;a.onclick=()=>{document.getElementById("case-"+id).open=true;};item.append(a);let cells=document.createElement("div");cells.className="heat-cells";Object.entries(cc).forEach(([c,v])=>{let cell=document.createElement("span");cell.className="s"+v[phase][dim];cell.textContent=names[c]+" "+v[phase][dim];cells.append(cell)});item.append(cells);target.append(item)});}document.querySelectorAll("[data-phase]").forEach(b=>b.onclick=()=>{phase=b.dataset.phase;document.querySelectorAll("[data-show]").forEach(x=>x.hidden=x.dataset.show!==phase);document.querySelectorAll("[data-phase]").forEach(x=>{x.classList.toggle("active",x.dataset.phase===phase);x.setAttribute("aria-pressed",x.dataset.phase===phase)});document.getElementById("heat-phase").textContent=phase==="first"?"첫 번역":"검사·수정 후 최종 번역";heat()});document.getElementById("dimension").onchange=heat;document.getElementById("search").oninput=function(){const q=this.value.toLowerCase();document.querySelectorAll(".case").forEach(x=>x.hidden=!x.textContent.toLowerCase().includes(q))};heat();'''
doc='<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>문장 분석과 KG 지식을 활용한 경상도 방언 변환</title><style>'+css+'</style></head><body><main><header><h1>문장 분석과 KG 지식을 활용한<br>표준어–경상도 방언 변환</h1><p>동일한 Qwen 모델에 원문만 제공한 경우, 문장 분석을 추가한 경우, 분석과 방언 지식을 함께 제공한 경우를 비교한다.</p><nav>'+''.join(f'<a href="#{k}">{v}</a>' for k,v in [('overview','연구 목적'),('pipeline','처리 과정'),('knowledge','KG 구성'),('conditions','비교 조건'),('results','전체 결과'),('cases','50건 상세'),('files','결과 파일')])+'</nav></header>'+''.join(parts)+'<footer>실험: 2026-10-21 · 문서 정리: 2026-10-24</footer></main><script type="application/json" id="scores">'+json.dumps(payload,ensure_ascii=False).replace('<','\\u003c')+'</script><script>'+script+'</script></body></html>'
(P/'report.html').write_text(doc)
(P/'figures/kg_example.svg').write_text(network());(P/'figures/results_first.svg').write_text(make_bars('first'));(P/'figures/results_final.svg').write_text(make_bars('final'))
print(json.dumps({'report':'reports/20261021_paper50/report.html','cases':len(D),'outputs':len(O),'html_bytes':len(doc.encode()),'new_model_calls':0},ensure_ascii=False))

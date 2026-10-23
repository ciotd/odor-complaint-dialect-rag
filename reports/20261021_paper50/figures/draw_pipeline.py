"""Publication vector figure for the executed K condition. Standard library only."""
from pathlib import Path
from html import escape
import subprocess

P=Path(__file__).resolve().parent
W,H=1440,950
parts=[]
def rect(x,y,w,h,fill='#ffffff',stroke='#41576a',r=12,dash=None):
 parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="2"'+(f' stroke-dasharray="{dash}"' if dash else '')+'/>')
def text(x,y,lines,size=26,bold=False,anchor='start',color='#1d2d3a',leading=40):
 if isinstance(lines,str):lines=[lines]
 parts.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{700 if bold else 400}" text-anchor="{anchor}" fill="{color}">'+''.join(f'<tspan x="{x}" dy="{0 if i==0 else leading}">{escape(s)}</tspan>' for i,s in enumerate(lines))+'</text>')
def arrow(points,color='#41576a',dash=None):
 parts.append('<polyline points="'+' '.join(f'{x},{y}' for x,y in points)+f'" fill="none" stroke="{color}" stroke-width="2.6" stroke-linejoin="round" marker-end="url(#arrow)"'+(f' stroke-dasharray="{dash}"' if dash else '')+'/>')
def line(x1,y1,x2,y2):parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#acb9c2" stroke-width="1.5"/>')

# Standard input and the existing knowledge store are two distinct resources.
rect(40,35,280,100,fill='#f4f7fa')
text(180,79,'표준어 원문',29,True,'middle')
text(180,115,'번역할 전체 발화',23,anchor='middle')
rect(395,25,650,120,fill='#edf4f5')
text(720,65,'방언 지식 저장소 (KG)',29,True,'middle')
text(720,104,'표현 · 적용 조건 · 출처 / 어휘–활용 연결',25,anchor='middle')
text(720,135,'지식 항목과 그래프 관계를 함께 사용',22,anchor='middle')

# Four left-to-right stages. The retrieval routes are internal options, not parallel agents.
rect(40,235,280,375)
rect(40,235,280,65,fill='#e8eef4')
text(180,278,'① 원문 분석 정보',27,True,'middle')
text(65,344,['Qwen 문장 분석¹','의미 · 질문/요청 · 높임'],24,leading=38)
line(60,405,300,405)
text(65,450,['Kiwi 단어·어미 분석','기본형 · 어미 · 위치'],24,leading=38)
text(65,559,['같은 원문에 맞춰','두 분석 정보를 사용'],23,leading=32)

rect(365,235,355,375)
rect(365,235,355,65,fill='#e8eef4')
text(542.5,278,'② 조회·변환안 작성',27,True,'middle')
text(388,344,['지식 항목 직접 검색','어휘–활용 관계 탐색','종결·구성 변환안 작성'],25,leading=43)
text(388,481,'위 과정에 조건 검사 포함',23)
line(385,500,700,500)
text(542.5,544,'후보 선택',25,True,'middle')
text(542.5,581,'우선순위 · 중복 · 분량 제한',23,anchor='middle')

rect(765,235,300,375)
rect(765,235,300,65,fill='#e8eef4')
text(915,278,'③ 생성 입력 구성',27,True,'middle')
text(789,345,['원문','문장 분석','구간별 변환 계획','선택된 관계 정보²','의미·높임 보존 지침'],25,leading=45)
text(915,588,'공통 번역 지시와 함께 전달',21,anchor='middle')

rect(1110,235,290,135,fill='#e8f1f3')
text(1255,287,'④ Qwen 번역 생성',27,True,'middle')
text(1255,333,'최초 방언 발화',25,anchor='middle')
rect(1110,455,290,190)
text(1255,500,'⑤ 보존 검사·수정',26,True,'middle')
text(1255,542,['강한 경고 시 Qwen 수정','최대 1회 · 수정본 재검사','검사 결과에 따라 최종 선택'],22,anchor='middle',leading=35)
rect(1110,720,290,90,fill='#e8f1f3')
text(1255,774,'최종 방언 발화',28,True,'middle')

arrow([(180,135),(180,235)])
arrow([(542,145),(542,235)])
arrow([(320,420),(365,420)])
arrow([(720,420),(765,420)])
arrow([(1065,420),(1087,420),(1087,303),(1110,303)])
arrow([(1255,370),(1255,455)])
text(1270,418,'최초 출력',21)
arrow([(1255,645),(1255,720)])

# Clarifications are part of the publication figure, not undocumented exceptions.
text(40,700,'적용 범위: 최근 50개 발화 실험의 KG 사용 조건(K)',25,True)
text(40,750,['¹ Qwen 분석은 저장된 결과를 재사용했으며, Kiwi 분석과 조회는 다시 수행했다.',
              '² 관계 정보는 선택된 후보 사이의 연결이 있을 때만 포함한다.'],23,leading=40)
text(40,875,['조회·변환안 작성과 후보 선택은 코드가 수행한다.',
              'Qwen은 전달된 정보를 참고해 번역하며, 필요할 때 수정 요청을 받는다.'],23,leading=38)

svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="180mm" height="118.75mm" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">
<title id="title">문장 분석과 KG 지식을 활용한 방언 변환 구조</title>
<desc id="desc">표준어의 저장된 Qwen 분석과 Kiwi 분석으로 지식 항목 및 어휘 활용 관계를 조회한다. 조회 중 조건 검사와 변환안 작성을 수행하고 우선순위와 분량에 따라 후보를 선택한다. 원문, 분석, 변환 계획, 선택된 관계와 보존 지침을 Qwen에 제공한다. 생성 후 보존 검사와 필요시 최대 한 번 수정 및 재검사로 최종 출력을 선택한다.</desc>
<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#41576a"/></marker></defs>
<rect width="1440" height="950" fill="white"/>
<g font-family="Noto Sans CJK KR, sans-serif">{''.join(parts)}</g></svg>'''
(P/'kg_pipeline_K.svg').write_text(svg)
subprocess.run(['rsvg-convert','-f','pdf','-o',str(P/'kg_pipeline_K.pdf'),str(P/'kg_pipeline_K.svg')],check=True)
subprocess.run(['rsvg-convert','-d','600','-p','600','-o',str(P/'kg_pipeline_K.png'),str(P/'kg_pipeline_K.svg')],check=True)
subprocess.run(['rsvg-convert','-w','1440','-o',str(P/'kg_pipeline_K_preview.png'),str(P/'kg_pipeline_K.svg')],check=True)
(P/'caption.txt').write_text('그림 1. 문장 분석과 지식 그래프(KG)를 활용한 표준어–경상도 방언 변환 구조. 원문 분석 정보를 이용해 지식 항목과 어휘–활용 관계를 조회하고, 조회 과정에서 조건 검사와 변환안 작성을 수행한다. 선택된 후보를 구간별 변환 계획으로 구성하여 원문·분석·관계 정보·보존 지침과 함께 Qwen에 제공한다. 생성 후 보존 검사를 수행하며, 강한 경고가 있는 경우 최대 1회 수정과 재검사를 거쳐 최종 출력을 선택한다. 본 실험에서는 저장된 Qwen 분석을 재사용했다.\n')
print('Saved SVG, vector PDF, 600 dpi PNG, preview and caption.')

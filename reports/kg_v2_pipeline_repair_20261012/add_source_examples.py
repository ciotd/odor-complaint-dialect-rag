"""Explicit source-reviewed additions; examples are not generalized rewrite rules."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'kg_v2'))
from author_support import Author,pattern,constraint

a=Author('NAMU_HONORIFICS_20260908','advisory_examples',['동남 방언: 원문 범위 확인'])
examples=[
 ('가세예','상대에게 과일을 보고 가도록 권하는 문맥의 높임 표현',
  '할메, 오랜만이라예. 여~어 와서 과일 함 보시고 가세예.', ['request','honorification']),
 ('보실래예','맛보기를 권하는 문맥의 의향 질문. 명사 서술 -이래예와 구분',
  '한 쪼가리 잡사 보\n      실래예?', ['interrogative','request','honorification']),
 ('맛있지예','맛을 확인하는 질문 문맥. 모든 죠의 의미를 확인 질문으로 단정하지 않음',
  '맛있지예. 하나 더 담아 돌라고예?', ['interrogative','honorification'])]
for text,desc,quote,functions in examples:
 a.fact('usage',pattern(text,'dialect'),pattern(desc,'metalinguistic'),26,quote,
        functions=functions,status='attested_example',usability='reference_only',levels=['해예'],
        constraints=[constraint('uncertainty','예문의 화행·형태 분해는 문맥 해석이다. 다른 어간의 완성형으로 자동 일반화하지 않는다.')],
        notes='네 역할 검토 LIT03의 원문 예문 보완. 표준어 대응쌍이나 보편 결합 규칙으로 기록하지 않음.')
path=ROOT/'kg_v2/authored/NAMU_HONORIFICS_20260908_advisory_examples.json'
path.write_text(json.dumps({'source_id':a.source,'facts':a.facts},ensure_ascii=False,indent=2)+'\n')
rpath=ROOT/'kg_v2/reviews/NAMU_HONORIFICS_20260908_full.json'
r=json.loads(rpath.read_text());page=next(p for p in r['pages'] if p['pdf_page']==26)
page['fact_ids']=list(dict.fromkeys(page['fact_ids']+[f['id'] for f in a.facts]))
rpath.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
p=ROOT/'kg_v2/authored/RYU2014_full.json';r=json.loads(p.read_text())
f=next(f for f in r['facts'] if f['id']=='RYU2014:v2:full:0098')
quote='방언에서 관형사형 형태는 표준어와 같다. 그러나 ‘-았던’과\n같은 형태는 방언형에 없었으나 60대에서만 새롭게 쓰고 있다.'
page=next(json.loads(l) for l in (ROOT/'kg_v2/local/pages.jsonl').read_text().splitlines()
          if json.loads(l)['source_id']=='RYU2014' and json.loads(l)['pdf_page']==20)
assert quote in page['text']
if not any(e['pdf_page']==20 and e['quote']==quote for e in f['evidence']):f['evidence'].append({'pdf_page':20,'quote':quote})
f['notes']='관형형 보존 설명 PDF20과 실제 대응표 PDF21을 함께 확인. 보존 정보로 전달하며 종결형 치환 후보로 사용하지 않는다.'
p.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('3 attested examples added as reference_only; relative-clause source evidence expanded.')

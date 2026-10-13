"""Build the central result index. No model calls, moves, or deletions."""
import csv
import hashlib
import html
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / 'reports'
OUT = REPORTS / 'latest'
OUT.mkdir(exist_ok=True)
registry_path = REPORTS / 'experiment_index.json'
registry = json.loads(registry_path.read_text())
for folder, entry, _ in registry['runs']:
    assert (ROOT/folder/entry).is_file(), (folder, entry)
translation = REPORTS / registry['latest_translation_run']
implementation = REPORTS / registry['latest_implementation_run']
comparison = REPORTS / registry['latest_model_comparison']
source = translation / 'final_outputs.json'
rows = json.loads(source.read_text())
order = {'DEV': 0, 'LONG': 1, 'NEW': 2, 'ADVCE': 3}
rows.sort(key=lambda r: (next((v for k,v in order.items() if r['id'].startswith(k)),9), r['id']))
assert len(rows) == len({r['id'] for r in rows})
successful = [r for r in rows if r['status']=='success']
assert all(r.get('output') and r.get('final_check') for r in successful)
def displayed_output(row):
    return row['output'] if row['status']=='success' else '[미생성: '+row['status']+']'

briefing = (REPORTS / registry['briefing_text']).read_text()
(OUT/'briefing.txt').write_text(briefing)
alignment = registry.get('translation_note') or ('최신 인용·의도 조회 수정을 반영한 실제 번역입니다. 품질 개선을 보증하지는 않습니다.'
             if registry['translation_matches_latest_implementation'] else '이후 조회 수정은 이 번역에 반영되지 않았습니다.')
header = f"최신 실행: {registry['latest_translation_run']} — 입력 {len(rows)}개, 최종 번역 {len(successful)}개\n{alignment}\n"
(OUT/'translations.txt').write_text(header+''.join(f"\n{r['id']}\n원문: {r['input']}\n번역: {displayed_output(r)}\n" for r in rows))
with (OUT/'translations.tsv').open('w',newline='') as f:
    w=csv.writer(f,delimiter='\t',lineterminator='\n')
    w.writerow(['id','input','output','screening_status','selection'])
    w.writerows([r['id'],r['input'],displayed_output(r),r.get('final_check',{}).get('status',r['status']),r.get('selection','not_generated')] for r in rows)

e=html.escape
style='<style>body{font-family:sans-serif;max-width:1200px;margin:32px auto;padding:0 18px;line-height:1.7;color:#18212c}a{color:#1752a0}table{border-collapse:collapse;width:100%}td,th{border:1px solid #cad1da;padding:12px;text-align:left;vertical-align:top}th{background:#eef3fa}pre{white-space:pre-wrap;font-family:inherit}.notice{background:#fff4cf;padding:16px}details{margin:24px 0}</style>'
def document(title):
    return '<!doctype html><html lang="ko"><meta charset="utf-8"><title>'+e(title)+'</title>'+style
def link(path,label):
    return '<a href="'+e(os.path.relpath(path,OUT),quote=True)+'">'+e(label)+'</a>'
page=document('최신 실제 번역')
page+='<h1>최신 실제 번역</h1><pre class="notice">'+e(header)+'</pre><p>'+link(OUT/'index.html','안내로 돌아가기')+'</p><table><tr><th>ID</th><th>원문</th><th>최종 번역</th><th>검사</th></tr>'
for r in rows:
    status=(('검토 경고 있음' if r['final_check']['flags'] else '경고 없음 — 품질 보증 아님')
            if r['status']=='success' else '미생성: '+r['status'])
    page+='<tr>'+''.join('<td>'+e(v)+'</td>' for v in [r['id'],r['input'],displayed_output(r),status])+'</tr>'
(OUT/'translations.html').write_text(page+'</table></html>')

management="""최신 안내는 reports/latest/를 사용한다. 이 폴더는 원본에서 재생성하는 보기용 파일이다.
원본 실험 폴더는 스크립트·비교·근거 링크가 참조하므로 일괄 이동/삭제하지 않는다.
새 실험은 reports/<날짜_시각>_<내용>/에 저장하고 reports/experiment_index.json에 등록한다.
번역을 실제 생성한 경우에만 latest_translation_run을 갱신한다. 조회만 검증했으면 latest_implementation_run만 갱신한다.
안내 재생성 명령: python reports/update_index.py
중앙 목록의 briefing_text와 latest_docx도 현재 상태에 맞게 갱신한다. 파일 수정 시간으로 최신 번역을 추정하지 않는다.
유지: 원문·출력·요청·설정·조회 로그·근거·코드/KG 스냅샷·비교 기준선.
삭제 검토: 재생성 가능한 HTML/TXT/TSV 보기 파일, 캐시·임시 파일. 참조와 재생성 방법을 확인한다.
실패 출력은 시행착오 근거이므로 실패했다는 이유만으로 삭제하지 않는다.
과거 DOCX는 작성 당시 기록이다. 최신 DOCX는 중앙 목록의 latest_docx를 따른다.
"""
(OUT/'START_HERE.txt').write_text(header+'\n'+management+'\n보고 요약: briefing.txt\n최종 번역: translations.html / translations.txt / translations.tsv\n전체 안내: index.html\n')
page=document('KG 연구 최신 결과 안내')
page+='<h1>KG 연구 결과 — 여기서 시작</h1><p>기준: '+e(registry['updated'])+'</p><p class="notice">'+e(alignment)+'</p><ol>'
for path,label in [(REPORTS/registry['latest_docx'],registry.get('latest_docx_label','쉽게 설명한 최신 보고서 DOCX')),(OUT/'briefing.txt','보고할 핵심 결론'),(OUT/'translations.html',f'최신 입력{len(rows)}개 원문·번역·실행 상태'),(translation/'comparison.html',registry.get('translation_comparison_label',f'{len(rows)}개 직전·최신 결과 비교 — 최초 출력 포함')),(comparison/registry.get('latest_model_comparison_entry','comparison.html'),registry.get('model_comparison_label','Astra·Claude·최신 Qwen38개 비교')),(implementation/'coordinator_report.txt','최신 KG·조회 수정과 남은 한계')]:
    page+='<li>'+link(path,label)+'</li>'
if registry.get('latest_user_feedback_comparison'):
    page+='<li>'+link(REPORTS/registry['latest_user_feedback_comparison'],registry.get('user_feedback_label','새로 제공한 Sonnet70개와 직전·최신 Qwen 비교 및 피드백 검토'))+'</li>'
page+='</ol><p>터미널: <code>cat reports/latest/translations.txt</code><br>'+link(OUT/'translations.tsv','최종 출력 TSV')+'</p><details><summary>과거 실험·상세 자료</summary><ul>'
for folder,entry,label in registry['runs']:
    page+='<li>'+link(ROOT/folder/entry,label)+'</li>'
page+='</ul></details><details><summary>보관·삭제·새 실험 등록</summary><pre>'+e(management)+'</pre>'+link(REPORTS/'cleanup_inventory.json','파일 중복·용량 조사')+'</details></html>'
(OUT/'index.html').write_text(page)
manifest={k:v for k,v in registry.items() if k!='runs'}
manifest.update(source_output_file=str(source.relative_to(ROOT)),source_output_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),input_count=len(rows),output_count=len(successful),failed_input_ids=[r['id'] for r in rows if r['status']!='success'],model_calls=0,deleted_files=[])
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(f'Built reports/latest: {len(rows)} inputs, {len(successful)} outputs; {len(registry["runs"])} indexed runs; no calls/deletions.')

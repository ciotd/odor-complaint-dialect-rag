"""Locate dataset provenance records without altering experimental evidence."""
import csv,json,re,subprocess,zipfile
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
patterns={
 'dataset_selection':r'기존 개발 사례 중 선정한|선정 시 정보|선정·제외 근거|selection_method_disclosed|선정한 탐색적|Prior KG output|outcome[- ]selected|outcome-dependent|selection_basis|selection_note|KG 결과를 보고|KG 번역 결과가 상대적으로|상대적으로 쓸 만한 50|선정 시 남긴|원문 완전 동일 출력 제외',
 'selection_audit':r'Prior KG output|상대적으로 의미·높임·구조 보존과 방언 실현이 나은 사례 선정|높임/의미/구조 오류 또는 방언 실현 부족을 고려한 수동 제외'}
regex=re.compile('|'.join(patterns.values()),re.I)
items=[]
cmd=['rg','--json','-i','-e',regex.pattern,'--glob','*.{py,json,jsonl,txt,md,html,tsv}','--glob','!scan_record_locations.py','--glob','!record_locations.*','.']
r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
assert r.returncode in (0,1), r.stderr
hits={}
for line in r.stdout.splitlines():
 row=json.loads(line)
 if row['type']=='match':
  d=row['data'];rel=d['path']['text'].removeprefix('./');hits.setdefault(rel,[]).append(d['line_number'])
for rel,lines in sorted(hits.items()):items.append({'path':rel,'kind':'workspace_file','matches':len(lines),'line_numbers':lines})
print('Workspace scanned',len(items),'matches',flush=True)
bundle=P/'논문용_50문장_실험_이관자료.zip'
if bundle.exists():
 with zipfile.ZipFile(bundle) as z:
  for info in z.infolist():
   if Path(info.filename).suffix not in {'.py','.json','.jsonl','.txt','.md','.html','.tsv'} or info.filename.endswith(('record_locations.tsv','record_locations.json','scan_record_locations.py')):continue
   try:s=z.read(info).decode()
   except UnicodeError:continue
   lines=[i for i,l in enumerate(s.splitlines(),1) if regex.search(l)]
   if lines:items.append({'path':str(bundle.relative_to(ROOT))+'!/'+info.filename,'kind':'zip_member','matches':len(lines),'line_numbers':lines})
print('Workspace and bundle scanned',flush=True)
history=subprocess.run(['git','log','--all','--format=%h %s','--name-only','-G','Prior KG output|outcome.selected|selection_basis|KG 번역 결과가 상대적으로','--','reports'],cwd=ROOT,text=True,capture_output=True,check=True).stdout.strip()
(P/'record_locations.json').write_text(json.dumps({'scope':'Non-ignored project text files, local paper50 ZIP and local Git refs; ignored source corpora, caches and credentials excluded. Notion export copies are included as local records. Remote Notion pages and chat history are not a complete filesystem search.','items':items,'git_history_matches':history},ensure_ascii=False,indent=2)+'\n')
with (P/'record_locations.tsv').open('w',newline='') as f:
 w=csv.writer(f,delimiter='\t',lineterminator='\n');w.writerow(['location','kind','matched_lines','line_numbers']);w.writerows([r['path'],r['kind'],r['matches'],','.join(map(str,r['line_numbers']))] for r in items)
print(json.dumps({'workspace_files':sum(r['kind']=='workspace_file' for r in items),'zip_members':sum(r['kind']=='zip_member' for r in items),'git_history_has_matches':bool(history)},ensure_ascii=False))

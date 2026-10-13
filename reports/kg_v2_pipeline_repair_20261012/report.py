"""Report actual before/first/final outputs, without calling flags accuracy."""
from collections import Counter
import csv
import hashlib
import html
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'kg_v2'))
from preservation_check import check_preservation

def read(p):return json.loads(p.read_text())
def save(name,d):(HERE/name).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

before={r['id']:r for r in read(HERE/'baseline_outputs.json')}
final={r['id']:r for r in read(HERE/'final_outputs.json')}
inputs=read(HERE/'analysis.json')['items']
retrieval={r['id']:r for r in read(HERE/'retrieval.json')}
oldretrieval={r['id']:r['baseline'] for r in read(ROOT/'reports/kg_v2_factorial_20261012/retrieval.json')}
for p in (HERE/'baseline_retrieval').glob('*.json'):
 r=read(p);oldretrieval[r['id']]=r
checks={sid:check_preservation(r['input'],r['output']) for sid,r in before.items()}
def measure(ids):
 def flags(which):
  rows=[checks[i] if which=='before' else final[i]['first_check'] if which=='first' else final[i]['final_check'] for i in ids]
  return {'inputs_with_high_confidence_flags':sum(r['repair_required'] for r in rows),
          'inputs_with_any_flags':sum(bool(r['flags']) for r in rows),
          'flag_counts':dict(Counter(f['kind'] for r in rows for f in r['flags']))}
 return {'inputs':len(ids),'before':flags('before'),'first':flags('first'),'final':flags('final'),
         'changed_first_outputs':sum(before[i]['output']!=final[i]['first_output'] for i in ids),
         'repairs_attempted':sum(final[i]['repair_attempted'] for i in ids),
         'repairs_accepted':sum(final[i]['selection']=='single_preservation_repair' for i in ids)}
ids=[r['id'] for r in inputs]
summary={'not_accuracy':True,'all70':measure(ids),'previous50':measure([i for i in ids if not i.startswith('ADVCE')]),
         'new20':measure([i for i in ids if i.startswith('ADVCE')]),
         'zero_reference_before':[i for i in ids if not oldretrieval[i]['packets']['v2_graph']['references']],
         'zero_reference_after':[i for i in ids if not retrieval[i]['packets']['v2_graph']['references']],
         'source_facts':read(ROOT/'kg_v2/reports/build_summary.json')['facts']}
segments=[]
for job in read(HERE/'jobs.json'):
 body=json.loads(job['request']['messages'][1]['content'].split('\n',1)[1])
 for group in body['transformation_plan']:
  segments.append({'id':job['id'],'span':group['span'],'candidate_count':len(group['candidates']),
     'candidate_characters':len(json.dumps(group['candidates'],ensure_ascii=False,separators=(',',':'))),
     'segment_characters':len(json.dumps(group,ensure_ascii=False,separators=(',',':')))})
summary['after_packet_statistics']={
 'delivered_segments':len(segments),'segments_per_input':len(segments)/70,
 'candidates_per_segment':sum(s['candidate_count'] for s in segments)/len(segments),
 'candidate_array_characters_mean':sum(s['candidate_characters'] for s in segments)/len(segments),
 'segment_with_common_information_characters_mean':sum(s['segment_characters'] for s in segments)/len(segments)}
save('summary.json',summary);save('segment_statistics.json',segments)
lines=['KG v2 パイプライン 보완 전후 결과'.replace('パイプライン','파이프라인'),
       'before: 기존50개는 이전A 출력 재사용, 새20개는 수정 전 스냅샷으로 새 생성.',
       'first: 수정 후 최초 생성. final: 명확한 보존 검사 지적에 최대1회 수정 후 선택.',
       '검사 플래그는 정확도·방언 자연스러움 점수가 아니다.','']
records=[]
for sid in ids:
 r=final[sid]
 row={'id':sid,'standard':r['input'],'before':before[sid]['output'],
      'first':r['first_output'],'final':r['output'],'selection':r['selection'],
      'before_flags':','.join(f['kind'] for f in checks[sid]['flags']),
      'first_flags':','.join(f['kind'] for f in r['first_check']['flags']),
      'final_flags':','.join(f['kind'] for f in r['final_check']['flags'])}
 records.append(row)
 lines += [sid+' '+row['standard'],*[k+': '+row[k] for k in ['before','first','final','selection','final_flags']],'']
(HERE/'comparison.txt').write_text('\n'.join(lines)+'\n')
with (HERE/'comparison.tsv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(records[0]),delimiter='\t',lineterminator='\n');w.writeheader();w.writerows(records)
save('comparison.json',records)
markup=['<!doctype html><html lang="ko"><meta charset="utf-8"><title>KG 보완 전후</title><style>body{max-width:1100px;margin:30px auto;font-family:sans-serif;line-height:1.6}article{border-top:2px solid #789;padding:18px 0}th{width:70px}td,th{text-align:left;vertical-align:top;padding:8px}table{width:100%;border-collapse:collapse}tr:nth-child(even){background:#f0f4f7}</style><h1>KG v2 보완 전후: 70개 입력</h1><p>기존50개 기준선 재사용 + 새20개 기준선 생성. 최초/수정 후 출력을 분리. 자동 플래그는 정확도가 아님.</p>']
for r in records:
 markup.append('<article><h2>'+html.escape(r['id'])+'</h2><p>'+html.escape(r['standard'])+'</p><table>'+''.join('<tr><th>'+k+'</th><td>'+html.escape(r[k])+'</td></tr>' for k in ['before','first','final','selection','final_flags'])+'</table></article>')
markup.append('</html>');(HERE/'comparison.html').write_text('\n'.join(markup))
p=read(HERE/'protocol.json')
assert all(sha(ROOT/n)==v for n,v in p['prior_artifacts'].items())
assert all(sha(ROOT/n)==v for n,v in p['after_hashes'].items())
assert len(final)==len(before)==70
p.update(status='completed',first_generations=70,new_baseline_generations=20,
         repair_generations=len(read(HERE/'repair_jobs.json')),prior_outputs_unchanged=True)
save('protocol.json',p)
print(json.dumps(summary,ensure_ascii=False,indent=2))

"""Replay retrieval only; never invoke a translation model."""
import difflib
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'kg_v2'))
from sentence_retrieval import SentenceRetriever, compact
from transformation_plan import package_plan


def read(path):
    return json.loads(path.read_text())


def save(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


prior = ROOT / 'reports/kg_v2_pipeline_repair_20261012'
items = read(prior / 'analysis.json')['items']
before = {r['id']: r for r in read(prior / 'retrieval.json')}
engine = SentenceRetriever()
after, plans, changes = [], [], []
for item in items:
    r = engine.retrieve(item)
    after.append(r)
    packet = r['packets']['v2_graph']
    plans.append({'id': item['id'], **package_plan(packet, item)})
    old = before[item['id']]['packets']['v2_graph']['references']
    new = packet['references']
    identity = lambda f: (f['id'], tuple(f['input_binding']['span']))
    old_ids, new_ids = {identity(f) for f in old}, {identity(f) for f in new}
    changes.append({'id': item['id'], 'input': item['input'],
                    'old_candidates': len(old), 'new_candidates': len(new),
                    'added': [f for f in new if identity(f) not in old_ids],
                    'removed': [f for f in old if identity(f) not in new_ids],
                    'construction_candidates': [f for f in new if f['retrieval_route'] == 'source_bound_construction'],
                    'packet_chars': len(compact(packet)),
                    'omitted': r['selection_audit']['v2_graph']['omitted']})
save('retrieval_after.json', after)
save('plans_after.json', plans)
save('retrieval_changes.json', changes)

newfacts = engine.kg.facts
oldfacts = {f['id']: f for f in map(json.loads, (OUT / 'before/facts.jsonl').read_text().splitlines())}
delta = {'added': [newfacts[k] for k in newfacts.keys() - oldfacts.keys()],
         'removed': [oldfacts[k] for k in oldfacts.keys() - newfacts.keys()],
         'modified': [k for k in oldfacts.keys() & newfacts.keys() if oldfacts[k] != newfacts[k]]}
save('kg_delta.json', delta)
assert len(delta['added']) == 1 and not delta['removed'] and not delta['modified']

summary = {'inputs_replayed': len(items), 'qwen_calls': 0,
           'inputs_with_selected_construction_candidates': [r['id'] for r in changes if r['construction_candidates']],
           'changed_inputs': [r['id'] for r in changes if r['added'] or r['removed']],
           'facts_before': len(oldfacts), 'facts_after': len(newfacts),
           'max_packet_chars': max(r['packet_chars'] for r in changes),
           'translation_quality_evaluated': False,
           'limitations': ['A documentary contraction and derived morphology are distinguished.',
                          'Intention 하다→카다 is not enabled by the quotative rule.',
                          'Prospective/weather -려고 compatibility remains unresolved; conditional candidates only.',
                          'Quotation routing is limited to immediately adjacent identified reporting verbs.',
                          'No new translations or human dialect evaluation.']}
save('summary.json', summary)
tracked = ['kg_v2/facts.jsonl', 'kg_v2/graph.json', 'kg_v2/sentence_retrieval.py',
           'kg_v2/construction_retrieval.py', 'kg_v2/run_translation.py',
           'kg_v2/authored/NAMU20260901_construction_review.json',
           'kg_v2/test_construction_retrieval.py']
save('protocol.json', {'model_calls': {'qwen': 0},
     'review_workers': {'requested_model': 'gpt-6-astra', 'requested_reasoning_effort': 'high',
         'launched': ['construction_advisor', 'construction_literature'],
         'third_worker': 'launch failed: agent thread limit; root handles counterexamples with advisor cross-review',
         'checkpoint_identity': 'requested settings, no independent backend verification'},
     'before_hashes': read(OUT / 'before_hashes.json'),
     'after_hashes': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in tracked},
     'frozen_prior_retrieval_sha256': hashlib.sha256((prior / 'retrieval.json').read_bytes()).hexdigest()})

diffs = []
for path in tracked:
    f = ROOT / path
    old = OUT / 'before' / f.name
    if f.suffix in {'.py', '.json'} and f.name != 'graph.json':
        diffs.extend(difflib.unified_diff(old.read_text().splitlines(True) if old.exists() else [],
                     f.read_text().splitlines(True), fromfile='before/'+path, tofile='after/'+path))
(OUT / 'implementation.diff').write_text(''.join(diffs))
print(json.dumps(summary, ensure_ascii=False, indent=2))

"""Compare retrieval against the frozen 38-input run without any model calls."""
import csv
import hashlib
import json
from pathlib import Path
from collections import Counter

from sentence_retrieval import SentenceRetriever, compact, BUDGET

BASE = Path(__file__).resolve().parent
FROZEN = BASE/'reports/translation_20261012'
OUT = BASE/'reports/speech_style_20261012'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ending_forms(packet):
    return [f['target_pattern']['text'] for f in packet['references']
            if f['type'] in {'ending', 'construction'}]


def run():
    protected = {p: sha(p) for p in list(FROZEN.iterdir()) if p.is_file()}
    protected.update({BASE/n: sha(BASE/n) for n in ['facts.jsonl', 'graph.json']})
    old = {r['id']: r for r in json.loads((FROZEN/'retrieval.json').read_text())}
    items = json.loads((FROZEN/'analysis.json').read_text())['items']
    engine = SentenceRetriever()
    rows, comparison = [], []
    for item in items:
        prior = old[item['id']]
        result = engine.retrieve(item, prior['morphology'])
        rows.append(result)
        for mode in ['v2_direct', 'v2_graph']:
            packet = result['packets'][mode]
            by = {f['id']: f for f in packet['references']}
            assert len(compact(packet)) <= BUDGET
            assert max(Counter(tuple(f['input_binding']['span']) for f in by.values()).values(), default=0) <= 6
            for f in by.values():
                assert f['usability'] == 'candidate' and not f['checks']['rejected']
                assert all(c['status'] == 'satisfied' for c in f['checks']['conditions'])
                a,b = f['input_binding']['span']
                assert item['input'][a:b] == f['input_binding']['text']
            assert all(e['source'] in by and e['target'] in by for e in packet['graph_paths'])
            before, after = ending_forms(prior['packets'][mode]), ending_forms(packet)
            comparison.append({'id': item['id'], 'input': item['input'], 'condition': mode,
                               'before': before, 'after': after,
                               'before_has_ye': any('예' in s for s in before),
                               'after_has_ye': any('예' in s for s in after)})
    summary = {'status': 'retrieval_checks_passed', 'inputs': len(items), 'model_calls': 0,
               'generation_rerun': False, 'quality_improvement': 'not evaluated',
               'policy': 'Source-terminal register ranking; prefer attested 해예 forms for informal polite conversion, retain formal/hasso preferences and condition exclusions.',
               'limitations': ['Register preference is an implementation hypothesis, not linguistic equivalence.',
                              'XSV/XSA predicate attachment remains unsupported by the existing predicate inventory.',
                              'Free-text constraints and generated politeness are not automatically validated.'],
               'conditions': {mode: {'before_inputs_with_ye_reference': sum(r['before_has_ye'] for r in comparison if r['condition']==mode),
                                     'after_inputs_with_ye_reference': sum(r['after_has_ye'] for r in comparison if r['condition']==mode)}
                              for mode in ['v2_direct','v2_graph']},
               'source_register_profiles': dict(Counter(s['register'] for r in rows for s in r['speech_style_profiles'])),
               'code_sha256': sha(BASE/'sentence_retrieval.py'),
               'frozen_analysis_sha256': sha(FROZEN/'analysis.json'),
               'protected_files': len(protected)}
    assert all(sha(p) == digest for p,digest in protected.items())
    summary['protected_files_unchanged'] = True
    OUT.mkdir(parents=True, exist_ok=True)
    for name,value in [('retrieval.json',rows),('comparison.json',comparison),('summary.json',summary)]:
        (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    with (OUT/'comparison.tsv').open('w') as stream:
        writer=csv.writer(stream,delimiter='\t');writer.writerow(['id','input','condition','before','after'])
        for r in comparison:writer.writerow([r['id'],r['input'],r['condition'],' / '.join(r['before']),' / '.join(r['after'])])
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':
    run()

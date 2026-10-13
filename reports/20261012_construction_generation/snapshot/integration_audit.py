"""Audit the three-worker review against the frozen draft and compiled graph."""
from collections import Counter
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
REPORTS = ['jo_review_completion.json', 'grammar_honorific_review_completion.json',
           'other_sources_review_completion.json']


def read(path):
    return json.loads(path.read_text())


def audit():
    baseline = read(BASE/'reports/parallel_review_baseline.json')
    expected = {(r['source_id'], r['pdf_page']) for r in baseline['original_gap_pages']}
    facts = {f['id']: f for f in map(json.loads, (BASE/'facts.jsonl').read_text().splitlines())}
    reviews = {}
    for p in (BASE/'reviews').glob('*.json'):
        doc = read(p)
        for r in doc['pages']:
            reviews[doc['source_id'], r['pdf_page']] = r
    errors, dispositions = [], {}
    old_digests = baseline['fact_digests']
    new_digests = {fid: hashlib.sha256(json.dumps(
        {k:v for k,v in f.items() if k not in ['source_id', 'authoring_file']},
        ensure_ascii=False, sort_keys=True).encode()).hexdigest() for fid,f in facts.items()}
    if set(old_digests)-set(facts):
        errors.append(f'Baseline fact IDs removed: {sorted(set(old_digests)-set(facts))}')
    for filename in REPORTS:
        doc = read(BASE/'reports'/filename)
        for d in doc['gap_dispositions']:
            key = d['source_id'], d['pdf_page']
            if key in dispositions:
                errors.append(f'Duplicate disposition: {key}')
            dispositions[key] = d
            if d['status'] not in {'resolved', 'partial', 'source_limitation'}:
                errors.append(f'Unknown disposition: {key}')
            if not d.get('reason', '').strip():
                errors.append(f'Missing disposition reason: {key}')
            for fid in d.get('fact_ids', []):
                if fid not in facts:
                    errors.append(f'Unknown disposition fact: {fid}')
                elif facts[fid]['source_id'] != key[0]:
                    errors.append(f'Disposition fact has different source: {fid}')
            if d['status'] == 'partial' and not reviews[key]['gaps']:
                errors.append(f'Partial extraction concealed in page ledger: {key}')
    if set(dispositions) != expected:
        errors.append(f'Disposition coverage mismatch: missing={sorted(expected-set(dispositions))}, extra={sorted(set(dispositions)-expected)}')

    ledger_ids = {fid for r in reviews.values() for fid in r['fact_ids']}
    if set(facts)-ledger_ids:
        errors.append(f'Facts absent from page ledger: {sorted(set(facts)-ledger_ids)}')
    graph = read(BASE/'graph.json')
    nodes = {n['id']: n for n in graph['nodes']}
    if len(nodes) != len(graph['nodes']):
        errors.append('Duplicate graph node IDs')
    for e in graph['edges']:
        if e['source'] not in nodes or e['target'] not in nodes:
            errors.append(f'Dangling graph edge: {e}')
        if e['type'] == 'candidate_has_inflection':
            left, right = facts[e['source']], facts[e['target']]
            lp, rp = left['target_pattern'], right['source_pattern']
            if (lp['lemma'] or lp['text']) != (rp['lemma'] or rp['text']):
                errors.append('Inflection edge lemma mismatch')
            if not e['properties'].get('requires_scope_and_sense_review'):
                errors.append('Inflection edge silently approves sense/scope')
    graph_facts = {n['id'] for n in graph['nodes'] if n['type']=='KnowledgeStatement'}
    if graph_facts != set(facts):
        errors.append('Compiled graph and facts disagree')
    summary = read(BASE/'reports/build_summary.json')
    for name in ['facts', 'graph']:
        suffix = '.jsonl' if name=='facts' else '.json'
        if summary[name+'_sha256'] != hashlib.sha256((BASE/(name+suffix)).read_bytes()).hexdigest():
            errors.append(f'Stale build hash: {name}')
    result = {
        'status': 'passed' if not errors else 'failed', 'errors': errors,
        'original_gap_pages': len(expected), 'gap_disposition_counts': dict(Counter(d['status'] for d in dispositions.values())),
        'facts_before': baseline['build']['facts'], 'facts_after': len(facts),
        'net_added_facts': len(facts)-baseline['build']['facts'],
        'modified_existing_facts': sum(new_digests.get(fid)!=value for fid,value in old_digests.items()),
        'remaining_gap_pages': sum(bool(r['gaps']) for r in reviews.values()),
        'newly_recorded_constraint_pages': [
            {'source_id': sid, 'pdf_page': page, 'gaps': r['gaps']}
            for (sid, page), r in reviews.items()
            if r['gaps'] and (sid, page) not in expected],
        'facts_sha256': summary['facts_sha256'], 'graph_sha256': summary['graph_sha256'],
        'checks': ['Every original gap has one explicit review disposition',
                   'Every baseline fact ID is preserved',
                   'Every fact is represented in the page ledger',
                   'Graph statement identities and edge endpoints agree',
                   'Inflection links preserve lemma match and scope/sense review',
                   'Compiled output hashes match the build report'],
        'limits': ['Mechanical audit does not prove semantic entailment or translation quality.',
                   'Three Astra workers and a coordinating Astra are model review, not independent human validation.']}
    (BASE/'reports/integration_audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__=='__main__':
    audit()

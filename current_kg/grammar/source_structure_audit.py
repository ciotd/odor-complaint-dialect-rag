"""Read-only authored-record/graph representation audit; not a linguistic certification.

Source-page readings and their interpretation are documented in current_kg/README.md.
This script inventories every record and reproduces the structural observations.
Run with /usr/bin/python3 source_structure_audit.py [--save].
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from authoring_audit import audit_ending_connections
from query_review import inspect_conditions, index_conditions

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PLACEHOLDER = '원문에 기술된 개별 구성·범위; 동일 의미나 범지역 교환을 보장하지 않음'
MISSING_SURFACES = ['가직으이더', '작으이더', '보핳으이더', '계시이더', '덥우이더', '더우이더']


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit():
    records = [json.loads(line) for line in (BASE / 'records.jsonl').read_text().splitlines()]
    graph = read(BASE / 'grammar.graph.json')
    nodes = {n['id']: n for n in graph['nodes']}
    semantic = {e['properties']['assertion_id']: e for e in graph['edges']
                if 'assertion_id' in e['properties']}
    inventory, mismatches, meaning_only, meaning_present, legacy, placeholder = [], [], [], [], [], []
    types = Counter(n['type'] for n in graph['nodes'])
    for r in records:
        rid, k = r['id'], r['knowledge']
        if nodes[rid]['properties']['details'] != k['details']:
            mismatches.append({'record_id': rid, 'field': 'details'})
        if nodes[rid]['properties']['gaps'] != k['gaps']:
            mismatches.append({'record_id': rid, 'field': 'gaps'})
        for f in k['forms']:
            n = nodes[rid + ':' + f['key']]['properties']
            for key in ('role', 'sense', 'pos'):
                if n[key] != f[key]:
                    mismatches.append({'record_id': rid, 'form': f['key'], 'field': key})
        rows = []
        for i, a in enumerate(k['relations'], 1):
            aid = rid + ':A' + str(i)
            fields = sorted({c['field'] for mode in ('all', 'any') for c in a['conditions'][mode]})
            if fields == ['meaning']:
                meaning_only.append(aid)
            if 'meaning' in fields:
                meaning_present.append(aid)
            if 'feature_sources' not in a['application']:
                legacy.append(aid)
            if any(PLACEHOLDER in c['values'] for mode in ('all', 'any') for c in a['conditions'][mode]):
                placeholder.append(aid)
            for key in ('conditions', 'application', 'assertion_mode'):
                if nodes[aid]['properties'][key] != a[key]:
                    mismatches.append({'assertion_id': aid, 'field': key})
            edge = semantic[aid]
            if edge['type'] != a['predicate'] or edge['properties']['conditions'] != a['conditions']:
                mismatches.append({'assertion_id': aid, 'field': 'semantic_edge'})
            rows.append({'assertion_id': aid, 'predicate': a['predicate'], 'subject': a['subject'],
                         'object': a['object'], 'condition_fields': fields,
                         'target': a['application']['target'],
                         'feature_sources': a['application'].get('feature_sources'),
                         'meaning_values': [v for mode in ('all', 'any') for c in a['conditions'][mode]
                                            if c['field'] == 'meaning' for v in c['values']]})
        inventory.append({'record_id': rid, 'authored_file': r['authored_file'], 'source_id': r['source_id'],
                          'label': k['label'], 'evidence': k['evidence'],
                          'detail_fields_stored_as_prose': [x['field'] for ds in k['details'].values() for x in ds],
                          'source_fidelity': r['review']['source_fidelity'], 'assertions': rows})
    integrity = audit_ending_connections(records, graph)['whole_graph_integrity']
    source_hashes = []
    for s in read(BASE / 'source_registry.json')['sources']:
        if s.get('eligible_for_claims'):
            actual = sha(ROOT / s['file']['path'])
            source_hashes.append({'source_id': s['source_id'], 'path': s['file']['path'],
                                  'sha256': actual, 'matches_registry': actual == s['file']['sha256']})
    index = index_conditions(graph)
    def inspect(start, known, candidate=None, target=None):
        packet = inspect_conditions(graph, start, known, candidate, target, _index=index)
        return {'base': [{'assertion_id': a['assertion_id'], 'predicate': a['predicate'],
                          'status': a['assessment']['status'], 'conditions': a['assessment']['conditions']}
                         for a in packet['base_assertions']],
                'matched_explicit_exclusions': packet['matched_explicit_exclusions']}
    # Synthetic feature probes, not new translation examples or generalization evaluation.
    probes = {
        'H028_function_connections': [e for e in graph['edges']
                                      if e['source'] == 'GYS-H028:F2' and 'assertion_id' in e['properties']],
        'H028_with_declarative_polite_features': inspect('GYS-H028:F2', {'sentence_type': 'declarative'},
                                                       target={'speech_level': 'HAEYO_LEVEL'}),
        'O004_without_meaning': inspect('GYS-O004:F3', {'sentence_type': 'declarative'}),
        'O004_with_P001_quotative_label': inspect('GYS-O004:F3', {'meaning': 'quotative_rago_hada'}),
        'O004_with_prose_password': inspect('GYS-O004:F3', {'meaning': PLACEHOLDER}),
        'Y015_with_actual_following_component': inspect('GYS-Y015:A1', {}, {'following_form': '끔'}),
        'Y015_with_legacy_meaning_label': inspect('GYS-Y015:A1', {'meaning': 'georo_kkeum_combination'}),
    }
    missing = []
    for form in MISSING_SURFACES:
        missing.append({'source_id': 'NAMU_HONORIFICS_20260908', 'pdf_page': 14, 'surface': form,
                        'exact_form_matches': [r['id'] + ':' + f['key'] for r in records
                                               for f in r['knowledge']['forms'] if form == f['text']],
                        'record_text_matches': [r['id'] for r in records
                                                if form in json.dumps(r['knowledge'], ensure_ascii=False)],
                        'limit': 'Exact-string inventory; semantic absence is assessed in the manual source review.'})
    return {
        'audit_date': '2026-09-29', 'status': 'representation_audit_not_full_source_validation',
        'snapshot_sha256': {name: sha(BASE / name) for name in ('records.jsonl', 'grammar.graph.json',
                                                              'analysis_contract.json', 'build.py', 'query_review.py')},
        'auditor_sha256': sha(Path(__file__)),
        'scope': {'structural_records': len(records), 'all_source_pages_rechecked': False,
                  'source_reading_notes': '../README.md: 문헌→KG 구조화 감사 — 2026-09-29',
                  'generation_performed': False, 'kg_modified': False},
        'summary': {'records': len(records), 'assertions': len(semantic), 'nodes': len(graph['nodes']),
                    'edges': len(graph['edges']), 'node_types': dict(types),
                    'meaning_only_assertions': len(meaning_only),
                    'records_with_meaning_only_assertions': sum(any(x['condition_fields'] == ['meaning']
                                                                  for x in r['assertions']) for r in inventory),
                    'assertions_with_meaning': len(meaning_present), 'legacy_binding_assertions': len(legacy),
                    'generic_caution_used_as_condition': len(placeholder),
                    'detail_entries_stored_as_prose': sum(len(ds) for r in records
                                                         for ds in r['knowledge']['details'].values()),
                    'authored_to_graph_mismatches': len(mismatches),
                    'integrity_issue_counts': {k: len(v) for k, v in integrity.items()}},
        'source_hashes': source_hashes, 'integrity': integrity, 'export_mismatches': mismatches,
        'meaning_only_assertion_ids': meaning_only, 'legacy_binding_assertion_ids': legacy,
        'generic_caution_assertion_ids': placeholder, 'missing_surface_checks': missing,
        'diagnostic_probes': probes, 'record_inventory': inventory,
        'limitations': ['meaning-only counts are not counts of mistranslations or false source assertions.',
                        'Prose details are retained, not lost during export; they are not executable constraints.',
                        'Probe match means encoded conditions match; it does not approve generation.',
                        'This audit does not certify all source statements or source coverage.'],
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--save', action='store_true')
    args = parser.parse_args()
    result = audit()
    if args.save:
        (BASE / 'source_structure_audit.results.json').write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result['summary'], ensure_ascii=False, indent=2))

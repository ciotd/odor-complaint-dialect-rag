"""Validate saved extraction bundles and reconstruct an auditable draft graph.

No legacy claim input, network, generation, or automatic linguistic inference.
Run with --export to save the deterministic graph via apply_patch.
"""
import argparse
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parents[1] / 'design_probe'))
from probe import Graph, require, validate


def read_bundles():
    paths = [HERE / 'namu_grammar_batch_001.json']
    paths += sorted(HERE.glob('namu_grammar_batch_*_p*.json'))
    paths = [p for p in paths if not p.name.endswith('.coverage.json')]
    return [(p, json.loads(p.read_text())) for p in paths]


def check_content(data):
    entities = {x['id']: x for x in data['entities']}
    evidence = {x['id'] for x in data['evidence']}
    for e in entities.values():
        require(all(r in evidence for r in e['properties'].get('evidence_refs', [])),
                'unresolved entity evidence')
    for c in data['claims']:
        for a in c['assertions']:
            content = a['content']
            require(content.get('operational_status', 'draft_not_approved') in
                    {'held', 'draft_not_approved'}, 'invalid operational status')
            if content.get('operational_status') == 'held':
                require(bool(c['gaps']), 'held claim requires reason')
            for entry in content.get('entries', []):
                if 'usage_ref' in entry:
                    require(entry['usage_ref'] in entities and
                            entities[entry['usage_ref']]['type'] == 'Usage',
                            'unresolved inventory usage')
            if 'paradigm' not in content:
                continue
            headers = content['headers']
            require(headers and all(type(h) is str and h for h in headers), 'bad headers')
            for row in content['paradigm']:
                require(row['usage_ref'] in entities, 'unresolved table usage')
                require(entities[row['usage_ref']]['properties']['lemma'] == row['lemma'],
                        'table lemma mismatch')
                require(len(row['forms']) == len(headers), 'table width mismatch')
                for cell in row['forms']:
                    require(type(cell) is list and cell and
                            all(type(f) is str and f for f in cell), 'bad table cell')
            for hold in content.get('cell_holds', []):
                require(0 <= hold['row'] < len(content['paradigm']) and
                        0 <= hold['column'] < len(headers) and hold['reason'], 'bad cell hold')


def build(loaded, registry, schema):
    merged = dict(format_version='3.0-draft.1', status='extraction_draft',
                  entities=[], evidence=[], claims=[], policies=[])
    for path, data in loaded:
        validate(data, registry, schema=schema)
        check_content(data)
        if path.name != 'namu_grammar_batch_001.json':
            ledger=json.loads(path.with_suffix('.coverage.json').read_text())
            require({e['source_id'] for e in data['evidence']} == {ledger['source_id']},
                    'coverage source mismatch')
            listed=[cid for unit in ledger['units'] for cid in unit['claim_ids']]
            require(listed==[c['id'] for c in data['claims']], 'coverage claim mismatch')
            for unit,c in zip(ledger['units'],data['claims']):
                require(bool(unit['hold']) == (c['assertions'][0]['content'].get('operational_status')=='held'),
                        'coverage hold mismatch')
        for key in ['entities', 'evidence', 'claims', 'policies']:
            merged[key].extend(data[key])
    validate(merged, registry, schema=schema)  # also rejects cross-bundle ID collisions
    check_content(merged)
    graph = Graph(merged, registry)
    counts = dict(table_cells=0, table_realizations=0, missing_cells=0, held_cells=0,
                  inventory_candidates=0, explicit_form_candidates=0)

    def node(id_, type_, properties):
        require(id_ not in graph.nodes, 'derived graph id collision')
        graph.nodes[id_] = dict(id=id_, type=type_, properties=copy.deepcopy(properties))

    def edge(source, relation, target, **properties):
        graph.edges.append(dict(source=source, relation=relation, target=target,
                                properties=properties))

    for c in merged['claims']:
        for a in c['assertions']:
            content = a['content']
            status = content.get('operational_status', 'draft_not_approved')
            # The first bundle is preserved exactly. Its caveats still block promotion.
            if (content.get('operationalized') is False or content.get('original_consulted') is False
                    or a['kind'] in {'historical_account', 'tentative_realization'}):
                status = 'held'
            for ri, row in enumerate(content.get('paradigm', [])):
                for ci, (header, forms) in enumerate(zip(content['headers'], row['forms'])):
                    counts['table_cells'] += 1
                    key = a['id'] + f'.table.{ri}.{ci}'
                    hold = next((h for h in content.get('cell_holds', [])
                                 if h['row'] == ri and h['column'] == ci), None)
                    missing = forms == ['-']
                    cell_status = 'held' if hold else status
                    node(key, 'Construction', dict(source_header=header, source_row=row['lemma'],
                         source_forms=forms, claim_ref=c['id'], assertion_ref=a['id'],
                         evidence_refs=c['evidence_refs'], operational_status=cell_status,
                         missing_source_cell=missing, hold=hold,
                         interpretation='exact table cell; header may be an ending, grammatical role, or number',
                         condition_scope='claim conditions retained on assertion; not silently applied to every column'))
                    edge(row['usage_ref'], 'participates_in', key)
                    edge(key, 'scoped_by', c['id'])
                    edge(key, 'derived_from', a['id'])
                    if missing:
                        counts['missing_cells'] += 1
                        continue
                    if hold:
                        counts['held_cells'] += 1
                    for fi, form in enumerate(forms):
                        fid = key + f'.form.{fi}'
                        node(fid, 'Form', dict(text=form, layer=row['lemma'],
                             operational_status=cell_status, evidence_refs=c['evidence_refs']))
                        edge(key, 'records_form' if hold else 'realizes_as', fid,
                             candidate_only=True, operational_status=cell_status)
                        counts['table_realizations'] += 1
            # Explicit inventory entries only; do not parse free prose, slashes, or ambiguous analyses.
            for ei, entry in enumerate(content.get('entries', [])):
                if not entry.get('forms'):
                    continue
                key = a['id'] + f'.inventory.{ei}'
                node(key, 'Construction', dict(source_entry=entry, claim_ref=c['id'],
                     operational_status=status, evidence_refs=c['evidence_refs'],
                     interpretation='source-listed candidates; no unconditional substitution'))
                for target in ([entry['usage_ref']] if 'usage_ref' in entry else a['target_refs']):
                    edge(target, 'participates_in', key)
                edge(key, 'scoped_by', c['id'])
                edge(key, 'derived_from', a['id'])
                for fi, form in enumerate(entry['forms']):
                    fid = key + f'.form.{fi}'
                    node(fid, 'Form', dict(text=form, operational_status=status))
                    edge(key, 'lists_candidate', fid, candidate_only=True)
                    counts['inventory_candidates'] += 1
            explicit = []
            if isinstance(content.get('forms'), list):
                explicit.append(dict(forms=content['forms'], source_slot='forms'))
            for entry in content.get('combinations', []):
                if entry.get('ending') and entry.get('form'):
                    explicit.append(dict(forms=[entry['form']], source_slot='combinations',
                                         ending=entry['ending']))
            for i, entry in enumerate(explicit):
                require(all(isinstance(f,str) and f for f in entry['forms']), 'bad explicit forms')
                key=a['id']+f'.explicit.{i}'
                node(key,'Construction',dict(source_entry=entry, claim_ref=c['id'],
                     operational_status=status, evidence_refs=c['evidence_refs'],
                     interpretation='explicit source forms with original claim conditions and restrictions'))
                for target in a['target_refs']:
                    edge(target,'participates_in',key)
                edge(key,'scoped_by',c['id'])
                edge(key,'derived_from',a['id'])
                if a['condition'] is not None:
                    edge(key,'condition',a['id']+'.condition')
                for fi,form in enumerate(entry['forms']):
                    fid=key+f'.form.{fi}'
                    node(fid,'Form',dict(text=form,operational_status=status))
                    edge(key,'lists_candidate',fid,candidate_only=True)
                    counts['explicit_form_candidates']+=1
    require(all(e['source'] in graph.nodes and e['target'] in graph.nodes for e in graph.edges),
            'dangling derived edge')
    # Lossless reconstruction check; annotations, exception text and holds remain reachable.
    require([graph.nodes[c['id']]['properties'] for c in merged['claims']] == merged['claims'],
            'claim round-trip mismatch')
    return merged, graph, counts


def audit(loaded, registry, schema):
    merged, graph, counts = build(loaded, registry, schema)
    checks = []

    def check(name, ok):
        require(ok, name)
        checks.append(name)

    source = next(s for s in registry['sources'] if s['source_id'] == 'NAMU_GRAMMAR_20260908')
    check('PDF hash unchanged', hashlib.sha256((ROOT / source['file']['path']).read_bytes()).hexdigest()
          == source['file']['sha256'])
    check('existing formal claims preserved', len(loaded[0][1]['claims']) == 15)

    def cell(cid, row, col):
        return graph.nodes[cid + '.a.table.' + str(row) + '.' + str(col)]

    def forms(cid, row, col):
        id_ = cell(cid, row, col)['id']
        return [graph.nodes[x]['properties']['text'] for x in graph.neighbors(id_, 'realizes_as')]

    prefix = 'NAMU_GRAMMAR_20260908'
    check('original 두다 past variants are both linked', forms(prefix+'-C0004', 2, 3) == ['돘다', '둤다'])
    check('missing 돌다 cell is not a surface form', forms(prefix+'-B002-C005', 0, 2) == [])
    check('묵다 regular and irregular variants coexist', forms(prefix+'-B002-C001', 0, 0) == ['묵어', '무우'])
    check('source duplicate 삐가 cell held', forms(prefix+'-B004-C005', 2, 2) == [])
    check('causative spelling and pronunciation distinct',
          forms(prefix+'-B004-C008',0,0) == ['빠줗다'] and forms(prefix+'-B004-C008',1,0) == ['빠주타'])
    check('counting and adnominal roles distinct',
          forms(prefix+'-B011-C001',1,2) == ['시','세'] and
          forms(prefix+'-B011-C001',3,2) == ['시나','세나'])
    check('all derived cells retain claim scope', all(graph.neighbors(n['id'], 'scoped_by')
          for n in graph.nodes.values() if '.table.' in n['id'] and n['type']=='Construction'))
    # Semantic OR must actually be queryable, not one concatenated label.
    aid=prefix+'-B007-C013.a.condition'
    target=prefix+'-B007-C013.usage'
    check('구로 purpose accepted / manner rejected / unknown preserved',
          [graph.evaluate(aid,{target:{'meaning':v}}) for v in ['목적','강조','방식',None]]
          == [True,True,False,None])
    check('구로/그로 explicit forms linked without adding 고로',
          [graph.nodes[x]['properties']['text'] for x in graph.neighbors(
              prefix+'-B007-C013.a.explicit.0','lists_candidate')] == ['-구로','-그로'])
    mutations = [
        ('bad table usage rejected', lambda d: d['claims'][0]['assertions'][0]['content']['paradigm'][0].update(usage_ref='missing')),
        ('table width mismatch rejected', lambda d: d['claims'][0]['assertions'][0]['content']['paradigm'][0]['forms'].pop()),
        ('entity evidence missing rejected', lambda d: d['entities'][0]['properties']['evidence_refs'].append('missing')),
        ('operational promotion rejected', lambda d: d['claims'][0]['assertions'][0]['content'].update(operational_status='approved')),
    ]
    for name, mutate in mutations:
        changed=copy.deepcopy(loaded[0][1]); mutate(changed)
        try:
            check_content(changed)
        except (ValueError, KeyError, TypeError):
            rejected=True
        else:
            rejected=False
        check(name,rejected)
    try:
        build(loaded+[loaded[0]],registry,schema)
    except ValueError:
        rejected=True
    else:
        rejected=False
    check('cross-bundle duplicate IDs rejected',rejected)
    return merged, graph, dict(passed=True, bundle_count=len(loaded), claim_count=len(merged['claims']),
             nodes=len(graph.nodes), edges=len(graph.edges), counts=counts, checks=checks,
             limitations=['draft graph, not an operational generator', 'no linguistic truth or modern naturalness validation'])


def export(path, data):
    text=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
    if path.exists():
        patch='*** Update File: '+str(path)+'\n@@\n'
        patch+=''.join('-'+x+'\n' for x in path.read_text().splitlines())
    else:
        patch='*** Add File: '+str(path)+'\n'
    patch+=''.join('+'+x+'\n' for x in text.splitlines())
    subprocess.run(['apply_patch'],input='*** Begin Patch\n'+patch+'*** End Patch\n',
                   text=True,check=True,capture_output=True)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--export',action='store_true')
    parser.add_argument('--check-receipt',action='store_true')
    args=parser.parse_args()
    loaded=read_bundles()
    schema=json.loads((HERE/'bundle.schema.json').read_text())
    registry=json.loads((HERE.parent/'source_registry.json').read_text())
    merged,graph,result=audit(loaded,registry,schema)
    if args.check_receipt:
        receipt=json.loads((HERE/'background_run/NAMU_GRAMMAR_20260908.receipt.json').read_text())
        require(receipt['source_id']=='NAMU_GRAMMAR_20260908', 'receipt source mismatch')
        require(receipt['status'] in {'extracted_draft','extracted_with_holds'}, 'receipt status')
        require(receipt['claim_count']==len(merged['claims']), 'receipt count mismatch')
        require(receipt['bundles']==[str(p.relative_to(ROOT)) for p,d in loaded], 'receipt bundles mismatch')
        require([p['page'] for p in receipt['pages']]==list(range(1,52)), 'receipt page completeness')
        evidence={e['id']:e for e in merged['evidence']}
        claims={c['id']:c for c in merged['claims']}
        seen=set()
        for page in receipt['pages']:
            require(page['status'] in {'extracted','context_only','held'} and page['reason'], 'page disposition missing')
            require(len(page['claim_ids'])==len(set(page['claim_ids'])), 'page duplicate claim refs')
            for cid in page['claim_ids']:
                require(cid in claims, 'page unknown claim')
                require(any(page['page'] in evidence[eid]['pdf_pages'] for eid in claims[cid]['evidence_refs']),
                        'page claim evidence mismatch')
                seen.add(cid)
        require(seen==set(claims), 'receipt omits stored claim')
        require(receipt['validation']['passed'] is True and receipt['validation']['commands'], 'receipt validation missing')
        saved=json.loads((HERE/'namu_grammar.graph.json').read_text())
        require(saved['nodes']==list(graph.nodes.values()) and saved['edges']==graph.edges,
                'saved graph not reproducible')
        require(saved['bundles']==[dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                                   for p,d in loaded], 'saved graph bundle digest mismatch')
        result['receipt_and_saved_graph']='passed'
    if args.export:
        export(HERE/'namu_grammar.graph.json',dict(format_version='v3-draft-graph.1',
             bundles=[dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p,d in loaded],
             status='draft_not_operational', nodes=list(graph.nodes.values()),edges=graph.edges,
             validation=result))
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()

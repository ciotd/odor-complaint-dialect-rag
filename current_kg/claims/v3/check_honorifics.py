"""Audit the honorifics extraction and export all saved v3 grammar bundles.

No generation, linguistic inference, media retrieval, or legacy-claim input.
The original grammar checker and its receipt remain independently reproducible.
"""
import argparse
import copy
import hashlib
import json
import re
import subprocess
from pathlib import Path
from check_all_v3 import HERE, ROOT, audit, build, export, read_bundles, require

SID = 'NAMU_HONORIFICS_20260908'


def run(export_graph=False, check_receipt=False):
    schema = json.loads((HERE / 'bundle.schema.json').read_text())
    registry = json.loads((HERE.parent / 'source_registry.json').read_text())
    paths = sorted(p for p in HERE.glob('namu_honorifics_batch_*_p*.json')
                   if not p.name.endswith('.coverage.json'))
    require(bool(paths), 'no honorifics bundles')
    loaded = [(p, json.loads(p.read_text())) for p in paths]
    # Later source bundles must remain present in the shared all-bundle export.
    from check_phonology import read_phonology, extend_graph
    phonology = read_phonology()
    from check_overview import read_overview, extend_graph as extend_overview
    overview = read_overview()
    from check_ryu2014 import read_ryu, extend_graph as extend_ryu
    ryu = read_ryu()
    from check_jo2018 import read_jo, extend_graph as extend_jo
    jo = read_jo()
    all_loaded = read_bundles() + loaded + phonology + overview + ryu + jo
    merged, graph, result = audit(all_loaded, registry, schema)
    if phonology:
        result['phonology_counts'] = extend_graph(graph, phonology)
        result.update(nodes=len(graph.nodes), edges=len(graph.edges))
    if overview:
        result['overview_counts'] = extend_overview(graph, overview)
        result.update(nodes=len(graph.nodes), edges=len(graph.edges))
    if ryu:
        result['ryu_counts'] = extend_ryu(graph, ryu)
        result.update(nodes=len(graph.nodes), edges=len(graph.edges))
    if jo:
        result['jo_counts'] = extend_jo(graph, jo)
        result.update(nodes=len(graph.nodes), edges=len(graph.edges))
    source = next(s for s in registry['sources'] if s['source_id'] == SID)
    require(hashlib.sha256((ROOT/source['file']['path']).read_bytes()).hexdigest()
            == source['file']['sha256'], 'honorifics PDF hash changed')
    claims = {c['id']: c for _, d in loaded for c in d['claims']}
    evidence = {e['id']: e for _, d in loaded for e in d['evidence']}
    pdf_text=subprocess.run(['pdftotext','-layout',str(ROOT/source['file']['path']),'-'],
                            check=True,capture_output=True,text=True).stdout.split('\f')
    normalize=lambda text: re.sub(r'\s+','',text)
    for e in evidence.values():
        original=normalize(''.join(pdf_text[p-1] for p in e['pdf_pages']))
        require(all(normalize(excerpt) in original for excerpt in e['excerpt'].split('\n[…]\n')),
                'evidence excerpt absent from declared PDF pages: '+e['id'])
    require(all(cid.startswith(SID+'-B') for cid in claims), 'honorifics ID namespace')
    checks = []

    def check(name, ok):
        require(ok, name)
        checks.append(name)

    def condition(cid, facts):
        return graph.evaluate(SID+cid+'.a.condition', {SID+cid+'.usage': facts})

    for cid, final, expected in [('-B002-C003','모음',True),('-B002-C003','ㄹ',True),
                                 ('-B002-C003','ㄹ을 제외한 자음',False),
                                 ('-B002-C004','ㄹ을 제외한 자음',True)]:
        check('요/소 '+cid+' '+final, condition(cid,dict(base_style='하소체 1형',
              sentence_function='평서',realized_stem_final=final)) is expected)
    check('요 condition does not authorize imperative', condition('-B002-C003',
          dict(base_style='하소체 1형',sentence_function='명령',realized_stem_final='모음')) is False)
    check('missing stem final remains unknown', condition('-B003-C005',
          dict(base_style='니껴형',predicate_pos='형용사')) is None)
    check('verb meaning does not match adjective rule', condition('-B003-C006',
          dict(base_style='니껴형',predicate_pos='동사',realized_stem_final='모음')) is False)
    table = SID+'-B003-C010'
    # Every source row is explicit; no inferred dictionary lemma is required.
    for row, expected in enumerate([['맑으이더'],['궁급으이더'],['가직니더','가직으이더'],
            ['작니더','작으이더'],['좋니더','좋으이더'],['보핳니더','보핳으이더'],['계시니더','계시이더']]):
        cell=table+f'.a.table.{row}.0'
        forms=[graph.nodes[x]['properties']['text'] for x in graph.neighbors(cell,'realizes_as')]
        check('honorifics exception table row '+str(row), forms == expected)
        check('requoted table row remains held '+str(row),
              graph.nodes[cell]['properties']['operational_status']=='held')
        check('table row usage participates '+str(row),
              cell in graph.neighbors(table+f'.row{row}', 'participates_in'))
    check('exception reachable from both adjective rules', all(table in graph.neighbors(
          SID+cid,'exception_to',True) for cid in ['-B003-C005','-B003-C006']))
    check('adjective exception not propagated to verb rule',
          table not in graph.neighbors(SID+'-B003-C007','exception_to',True))
    for i,expected in enumerate(['동사','형용사','동사','형용사']):
        uid=SID+f'-B003-C008.sense{i}'
        check('sense-specific usage '+str(i),graph.nodes[uid]['properties']['pos']==expected and
              graph.neighbors(uid,'participates_in')==[SID+f'-B003-C008.a.inventory.{i}'])
    check('요/예 alternation is logical OR', all(condition('-B004-C005',
          dict(base_construction='하게체 의문형',attached_particle=p)) is True for p in ['요','예']))
    check('declared evidence excerpts present in source PDF',True)
    for _,d in loaded:
        for c in d['claims']:
            for a in c['assertions']:
                for entry in a['content'].get('entries',[]):
                    require(isinstance(entry,dict) and isinstance(entry.get('forms'),list)
                            and entry['forms'] and all(isinstance(f,str) and f for f in entry['forms']),
                            'malformed honorifics inventory')
                for example in a['content'].get('source_rejected',[]):
                    require(example not in a['content'].get('forms',[]), 'rejected form promoted')
    # Negative checks retain strong source/ref/condition/coverage validation.
    for name, mutate in [
        ('honorifics dangling condition blocked', lambda d: d['claims'][0]['assertions'][0].update(
            condition=dict(op='eq',target='missing',feature='style',value='test'))),
        ('honorifics source substitution blocked', lambda d: d['evidence'][0].update(source_id='JO2018')),
        ('honorifics table width blocked', lambda d: d['claims'][9]['assertions'][0]['content']['paradigm'][0]['forms'].append(['x'])),
        ('honorifics inventory usage blocked', lambda d: d['claims'][0]['assertions'][0]['content'].update(
            entries=[dict(forms=['x'],usage_ref='missing')])),
    ]:
        changed=copy.deepcopy(loaded)
        index=2 if 'table width' in name else 0
        mutate(changed[index][1])
        try:
            build(read_bundles()+changed,registry,schema)
        except (ValueError,KeyError,TypeError):
            rejected=True
        else:
            rejected=False
        check(name,rejected)
    result.update(honorifics_claim_count=len(claims), honorifics_bundle_count=len(loaded),
                  honorifics_held_claim_count=sum(any(a['content'].get('operational_status')=='held'
                    for a in c['assertions']) for c in claims.values()), honorifics_checks=checks)
    graph_path=HERE/'current_kg.graph.json'
    payload=dict(format_version='v3-draft-graph.1',status='draft_not_operational',
        bundles=[dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                 for p,_ in all_loaded],nodes=list(graph.nodes.values()),edges=graph.edges,validation=result)
    if export_graph:
        export(graph_path,payload)
    if check_receipt:
        receipt=json.loads((HERE/'background_run'/f'{SID}.receipt.json').read_text())
        require(receipt['source_id']==SID and receipt['status'] in
                {'extracted_draft','extracted_with_holds'}, 'receipt identity/status')
        require(receipt['claim_count']==len(claims), 'receipt count')
        require(receipt['bundles']==[str(p.relative_to(ROOT)) for p in paths], 'receipt bundles')
        require([p['page'] for p in receipt['pages']]==list(range(1,36)), 'receipt page completeness')
        seen=set()
        for page in receipt['pages']:
            require(page['status'] in {'extracted','context_only','held'} and page['reason'], 'page status/reason')
            require(len(page['claim_ids'])==len(set(page['claim_ids'])), 'duplicate page refs')
            if page['status']=='extracted': require(page['claim_ids'], 'extracted page without claims')
            for cid in page['claim_ids']:
                require(cid in claims, 'receipt unresolved claim')
                require(any(page['page'] in evidence[e]['pdf_pages'] for e in claims[cid]['evidence_refs']),
                        'receipt page/evidence mismatch')
                seen.add(cid)
        require(seen==set(claims), 'receipt omitted claim')
        require(receipt['validation']['passed'] and receipt['validation']['commands'], 'receipt validation')
        saved=json.loads(graph_path.read_text())
        for key in ['bundles','nodes','edges']:
            require(saved[key]==payload[key], 'all-bundle graph not reproducible: '+key)
        result['receipt_and_saved_graph']='passed'
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--export',action='store_true')
    parser.add_argument('--check-receipt',action='store_true')
    args=parser.parse_args()
    print(json.dumps(run(args.export,args.check_receipt),ensure_ascii=False,indent=2))

"""Strict phonology content audit and deterministic, layer-aware table export.

All inputs are saved v3 bundles and the registered read-only PDF. No generation.
Representation tables are not ending paradigms: never split grouped source cells
or treat a standard-language/orthographic column as a dialect pronunciation.
"""
import argparse
import copy
import hashlib
import json
import re
import subprocess
from check_all_v3 import HERE, ROOT, audit, export, read_bundles, require

SID = 'NAMU_PHONOLOGY_20260908'


def read_phonology():
    return [(p, json.loads(p.read_text())) for p in sorted(HERE.glob('namu_phonology_batch_*_p*.json'))
            if not p.name.endswith('.coverage.json')]


def normalize(text):
    return re.sub(r'\s+', '', text)


def validate_content(loaded):
    headers_allowed = {'표준어 발음', '동남 방언 발음', '형태소 중시 표기', '발음 중시 표기',
                       '기호1', '기호2', '기호', '준말', '표준어 표기·발음', '동남방언 표기·발음'}
    for _, data in loaded:
        evidence = {e['id']: e for e in data['evidence']}
        entities = {e['id']: e for e in data['entities']}
        for claim in data['claims']:
            require(claim['id'].startswith(SID+'-B'), 'phonology ID namespace')
            for assertion in claim['assertions']:
                co = assertion['content']
                require(co['operational_status'] in {'held', 'draft_not_approved'}, 'phonology status')
                require(co.get('source_analysis') and co.get('extractor_interpretation')
                        and co.get('generation_policy'), 'analysis/policy separation missing')
                evtext = normalize(''.join(evidence[e]['excerpt'] for e in claim['evidence_refs']))
                for entry in co.get('entries', []):
                    require(entry.get('usage_ref') in entities and entities[entry['usage_ref']]['type']=='Usage',
                            'phonology entry usage missing')
                    require(entry.get('source_expression') and normalize(entry['source_expression']) in evtext,
                            'entry source expression absent from evidence')
                    require(isinstance(entry.get('forms'),list) and entry['forms'] and
                            all(isinstance(f,str) and f and normalize(f) in evtext for f in entry['forms']),
                            'entry form absent from evidence')
                table = co.get('representation_table')
                if table is None:
                    continue
                require(set(table)=={'headers','rows','interpretation'}, 'representation table keys')
                headers = table['headers']
                require(isinstance(headers,list) and headers and len(headers)==len(set(headers))
                        and all(h in headers_allowed for h in headers), 'representation headers')
                require(table['interpretation'] and table['rows'], 'empty representation table')
                for row in table['rows']:
                    require(set(row)=={'usage_ref','source_expression','cells','note'}, 'representation row keys')
                    uid = row['usage_ref']
                    require(uid in entities and entities[uid]['type']=='Usage', 'representation usage missing')
                    require(entities[uid]['properties']['source_expression']==row['source_expression'],
                            'representation usage mismatch')
                    require(normalize(row['source_expression']) in evtext, 'table source expression absent')
                    require(isinstance(row['cells'],list) and len(row['cells'])==len(headers),
                            'representation table width')
                    require(row['note'], 'representation row note missing')
                    for cell in row['cells']:
                        require(cell is None or (isinstance(cell,str) and cell and normalize(cell) in evtext),
                                'representation cell absent from evidence')


def extend_graph(graph, loaded):
    """Only source-explicit single-cell forms are linked as realizations.

    Grouped /, comma, parenthesis and bracket cells stay opaque source records.
    Their individual mapping requires review; no cross product is inferred.
    """
    validate_content(loaded)
    counts = dict(representation_rows=0, representation_cells=0, blank_cells=0,
                  single_form_links=0, grouped_cells_retained=0)

    def node(id_, type_, **properties):
        require(id_ not in graph.nodes, 'phonology graph ID collision')
        graph.nodes[id_] = dict(id=id_, type=type_, properties=properties)

    def edge(source, relation, target, **properties):
        graph.edges.append(dict(source=source,relation=relation,target=target,properties=properties))

    for _, data in loaded:
        for claim in data['claims']:
            for a in claim['assertions']:
                co = a['content']; table = co.get('representation_table')
                if not table:
                    continue
                for ri, row in enumerate(table['rows']):
                    counts['representation_rows'] += 1
                    rid = a['id']+f'.representation.{ri}'
                    node(rid,'Construction',source_expression=row['source_expression'],
                         source_row=copy.deepcopy(row),claim_ref=claim['id'],assertion_ref=a['id'],
                         evidence_refs=claim['evidence_refs'],operational_status=co['operational_status'],
                         interpretation='exact source row; layer correspondence, not inferred ending segmentation')
                    edge(row['usage_ref'],'participates_in',rid)
                    edge(rid,'scoped_by',claim['id']); edge(rid,'derived_from',a['id'])
                    if a['condition'] is not None:
                        edge(rid,'condition',a['id']+'.condition')
                    for ci, (header, cell) in enumerate(zip(table['headers'],row['cells'])):
                        counts['representation_cells'] += 1
                        cellid=rid+f'.cell.{ci}'
                        node(cellid,'RepresentationCell',text=cell,layer=header,source_column=ci,
                             missing_source_cell=cell is None,operational_status=co['operational_status'])
                        edge(rid,'records_representation',cellid,source_header=header)
                        if cell is None:
                            counts['blank_cells'] += 1
                            continue
                        # A grouped input also blocks false individual-input/output pairing.
                        grouped = any(ch in cell+row['source_expression'] for ch in '/,()[]')
                        reference_layer=header.startswith('표준어') or header=='형태소 중시 표기'
                        if grouped:
                            counts['grouped_cells_retained'] += 1
                            continue
                        if reference_layer:
                            continue
                        fid=cellid+'.form'
                        node(fid,'Form',text=cell,representation_layer=header,
                             evidence_refs=claim['evidence_refs'],operational_status=co['operational_status'],
                             orthographic_output_approved=False)
                        edge(cellid,'transcribes',fid)
                        edge(rid,'records_form' if co['operational_status']=='held' else 'realizes_as',fid,
                             representation_layer=header,candidate_only=True)
                        counts['single_form_links'] += 1
    require(all(e['source'] in graph.nodes and e['target'] in graph.nodes for e in graph.edges),
            'phonology dangling graph edge')
    return counts


def run(export_graph=False, check_receipt=False):
    loaded=read_phonology()
    require(loaded, 'no phonology bundles')
    honor=[(p,json.loads(p.read_text())) for p in sorted(HERE.glob('namu_honorifics_batch_*_p*.json'))
           if not p.name.endswith('.coverage.json')]
    from check_overview import read_overview, extend_graph as extend_overview
    overview=read_overview()
    from check_ryu2014 import read_ryu, extend_graph as extend_ryu
    ryu=read_ryu()
    from check_jo2018 import read_jo, extend_graph as extend_jo
    jo=read_jo()
    all_loaded=read_bundles()+honor+loaded+overview+ryu+jo
    schema=json.loads((HERE/'bundle.schema.json').read_text())
    registry=json.loads((HERE.parent/'source_registry.json').read_text())
    merged,graph,result=audit(all_loaded,registry,schema)
    counts=extend_graph(graph,loaded)
    if overview:
        result['overview_counts']=extend_overview(graph,overview)
    if ryu:
        result['ryu_counts']=extend_ryu(graph,ryu)
    if jo:
        result['jo_counts']=extend_jo(graph,jo)
    source=next(s for s in registry['sources'] if s['source_id']==SID)
    require(hashlib.sha256((ROOT/source['file']['path']).read_bytes()).hexdigest()==source['file']['sha256'],
            'phonology PDF hash changed')
    pages=subprocess.run(['pdftotext','-layout',str(ROOT/source['file']['path']),'-'],
                         text=True,capture_output=True,check=True).stdout.split('\f')
    require(len(pages)==9 and not pages[-1].strip(), 'PDF page count changed')
    claims={c['id']:c for _,d in loaded for c in d['claims']}
    evidence={e['id']:e for _,d in loaded for e in d['evidence']}
    for e in evidence.values():
        text=normalize(''.join(pages[p-1] for p in e['pdf_pages']))
        require(all(normalize(s) in text for s in e['excerpt'].split('\n[…]\n')),
                'phonology excerpt absent from declared PDF pages: '+e['id'])
    checks=[]
    def check(name, ok):
        require(ok,name); checks.append(name)
    def cid(batch,local): return SID+f'-B{batch:03}-C{local:03}'
    c=cid(1,5); target=c+'.usage'
    check('ㅕ requires actual initial consonant; unknown stays unknown',
          [graph.evaluate(c+'.a.condition',{target:dict(input_vowel='ㅕ',syllable_has_initial_consonant=v)})
           for v in [True,False,None]]==[True,False,None])
    c=cid(2,2); target=c+'.usage'
    check('ㄴ environments use OR and do not mandate deletion',
          all(graph.evaluate(c+'.a.condition',{target:dict(consonant='ㄴ',source_following_segment=v)}) is True
              for v in ['-ㅣ','-이','-히','-ㅡ','-으']) and
          graph.evaluate(c+'.a.condition',{target:dict(consonant='ㄴ',source_following_segment='-아')}) is False
          and claims[c]['assertions'][0]['content']['mandatory'] is False)
    row=c+'.a.representation.0'
    check('걸으니 pronunciation and both nasal notations keep distinct layers',
          [(graph.nodes[f]['properties']['text'],graph.nodes[f]['properties']['representation_layer'])
           for f in graph.neighbors(row,'realizes_as')]==
          [('걸으이','발음 중시 표기'),('걸으~이','기호1'),('걸으~이~','기호2')])
    check('orthographic 걸으니 is not a pronunciation output',
          not graph.neighbors(row+'.cell.0','transcribes'))
    check('ㄴ two tables consolidated into 12 rows',
          len(claims[c]['assertions'][0]['content']['representation_table']['rows'])==12)
    row=cid(3,2)+'.a.representation.6'
    check('이게/요게 grouped cell not automatically paired or split',
          not graph.neighbors(row,'realizes_as') and
          graph.nodes[row+'.cell.2']['properties']['text']=='예/이')
    row=cid(3,1)+'.a.representation.0'
    check('source blank is retained without generated form',
          graph.nodes[row+'.cell.2']['properties']['missing_source_cell'] and
          not graph.neighbors(row+'.cell.2','transcribes'))
    check('requoted assimilation table cannot yield approved realization',
          not graph.neighbors(cid(2,1)+'.a.representation.3','realizes_as'))
    check('archaic quotation glyph held without guessed modern form',
          claims[cid(4,12)]['assertions'][0]['content']['operational_status']=='held' and
          not graph.neighbors(cid(4,12)+'.a.explicit.0','lists_candidate'))
    c=cid(4,10);target=c+'.usage'
    check('quotation correspondence limited to -라고 하다',
          [graph.evaluate(c+'.a.condition',{target:dict(source_construction=v)})
           for v in ['-라고 하다','-다고 하다',None]]==[True,False,None])
    for name,mutate in [
        ('table width rejected',lambda d:d[1][1]['claims'][1]['assertions'][0]['content']['representation_table']['rows'][0]['cells'].pop()),
        ('table unknown usage rejected',lambda d:d[1][1]['claims'][1]['assertions'][0]['content']['representation_table']['rows'][0].update(usage_ref='missing')),
        ('invented source form rejected',lambda d:d[0][1]['claims'][4]['assertions'][0]['content']['entries'][0]['forms'].append('문헌에없는가짜형')),
        ('empty cell not treated as blank',lambda d:d[1][1]['claims'][1]['assertions'][0]['content']['representation_table']['rows'][0]['cells'].__setitem__(0,'')),
    ]:
        changed=copy.deepcopy(loaded);mutate(changed)
        try: validate_content(changed)
        except (ValueError,KeyError,TypeError): rejected=True
        else: rejected=False
        check(name,rejected)
    result.update(phonology_claim_count=len(claims),phonology_bundle_count=len(loaded),
                  phonology_held_claim_count=sum(c['assertions'][0]['content']['operational_status']=='held'
                                               for c in claims.values()),phonology_counts=counts,
                  phonology_checks=checks,nodes=len(graph.nodes),edges=len(graph.edges))
    payload=dict(format_version='v3-draft-graph.1',status='draft_not_operational',
        bundles=[dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                 for p,_ in all_loaded],nodes=list(graph.nodes.values()),edges=graph.edges,validation=result)
    if export_graph: export(HERE/'current_kg.graph.json',payload)
    if check_receipt:
        receipt=json.loads((HERE/'background_run'/f'{SID}.receipt.json').read_text())
        require(receipt['source_id']==SID and receipt['status']=='extracted_with_holds','receipt identity/status')
        require(receipt['claim_count']==len(claims),'receipt count')
        require(receipt['bundles']==[str(p.relative_to(ROOT)) for p,_ in loaded],'receipt bundles')
        require([p['page'] for p in receipt['pages']]==list(range(1,9)),'receipt page completeness')
        seen=set()
        for page in receipt['pages']:
            require(page['status'] in {'extracted','context_only','held'} and page['reason'],'page status/reason')
            require(len(page['claim_ids'])==len(set(page['claim_ids'])),'duplicate page claim')
            if page['status']=='extracted': require(page['claim_ids'],'extracted page empty')
            for c in page['claim_ids']:
                require(c in claims and any(page['page'] in evidence[e]['pdf_pages']
                        for e in claims[c]['evidence_refs']),'receipt page evidence mismatch')
                seen.add(c)
        require(seen==set(claims),'receipt omitted claim')
        require(receipt['validation']['passed'] and receipt['validation']['commands'],'receipt validation')
        saved=json.loads((HERE/'current_kg.graph.json').read_text())
        for key in ['bundles','nodes','edges']:
            require(saved[key]==payload[key],'graph reconstruction mismatch: '+key)
        result['receipt_and_saved_graph']='passed'
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--export',action='store_true')
    parser.add_argument('--check-receipt',action='store_true')
    args=parser.parse_args()
    print(json.dumps(run(args.export,args.check_receipt),ensure_ascii=False,indent=2))

"""RYU2014 source audit and deterministic table-to-grammar graph conversion.

Only local PDF and saved v3 bundles are read. Whole source examples stay whole:
no automatic morphological segmentation, generation, or legacy claim input.
All file mutations, including exports, use apply_patch through export().
"""
import argparse
import copy
import hashlib
import json
import re
import subprocess
from check_all_v3 import HERE, ROOT, audit, export, read_bundles, require

SID = 'RYU2014'


def read_ryu():
    return [(p, json.loads(p.read_text())) for p in sorted(HERE.glob('ryu2014_batch_*_p*.json'))
            if not p.name.endswith('.coverage.json')]


def normalize(s):
    return re.sub(r'\s+', '', s)


def validate_content(loaded):
    for path, data in loaded:
        ledger = json.loads(path.with_suffix('.coverage.json').read_text())
        require(ledger['audit']['text_read'] and ledger['audit']['pdftotext_layout'], 'reading audit')
        require([p['page'] for p in ledger['page_dispositions']] == ledger['body_pages'], 'body page ledger')
        evidence = {e['id']: e for e in data['evidence']}
        for c in data['claims']:
            require(c['id'].startswith(SID+'-B'), 'RYU namespace')
            source = normalize(''.join(evidence[e]['excerpt'] for e in c['evidence_refs']))
            pages = {p for e in c['evidence_refs'] for p in evidence[e]['pdf_pages']}
            def attested(s):
                # Hyphens are metalinguistic boundary notation, not invented letters.
                require(isinstance(s, str) and s.strip(), 'empty source expression')
                q = normalize(s)
                visual = [v for v in ledger['audit'].get('visual_transcriptions', [])
                          if v['claim_id']==c['id'] and v['page'] in pages and
                          v['page'] in ledger['audit']['pdf_pages_visually_checked']]
                return q in source or q.strip('-') in source or any(
                    normalize(v['text'])==q for v in visual)
            for a in c['assertions']:
                co = a['content']
                for key in ['source_locator','source_analysis','extractor_interpretation','generation_policy']:
                    require(isinstance(co.get(key), str) and co[key], 'attribution missing: '+key)
                require(co.get('operational_status') in {'held','draft_not_approved'}, 'invalid approval')
                # Survey rates may occur in source evidence, never in grammar content.
                require('%' not in json.dumps(co, ensure_ascii=False), 'survey rate leaked into grammar')
                def no_rates(value):
                    if isinstance(value,dict):
                        require(not set(value) & {'probability','usage_rate','percentage','percent','sampling_weight'}, 'numeric survey rate in grammar')
                        for child in value.values():no_rates(child)
                    elif isinstance(value,list):
                        for child in value:no_rates(child)
                no_rates(co)
                for f in co.get('forms', []):
                    require(attested(f), 'form absent: '+c['id']+' '+f)
                for e in co.get('source_examples', []):
                    require(e['judgment']=='source_attestation_not_acceptability_test', 'example judgment inflated')
                    require(attested(e['text']), 'example absent: '+c['id']+' '+e['text'])
                for row in co.get('construction_rows', []):
                    require(set(row) <= {'usage','ending','surface','hold','layer','features','speech_level'}, 'unknown row field')
                    require(row.get('usage') and attested(row['ending']), 'row usage/ending absent: '+c['id'])
                    require(row['layer']=='whole_source_example', 'example layer conflated')
                    require(row.get('hold') is None or isinstance(row['hold'],str) and row['hold'], 'row hold')
                    if row['surface'] is None:
                        require(row['hold'], 'missing source cell without reason')
                    else:
                        require(attested(row['surface']), 'row example absent: '+c['id']+' '+row['surface'])
                    require(all(isinstance(k,str) and k and isinstance(v,str) and v
                                for k,v in row.get('features',{}).items()), 'row conditions malformed')
                for row in co.get('source_derivations', []):
                    require(set(row)=={'usage','suffix','ending','surface'} and row['usage'], 'derivation structure')
                    require(all(attested(row[k]) for k in ['suffix','ending','surface']), 'derivation source missing')
                    require(a['condition'] is not None, 'derivation conditions missing')
                for row in co.get('attested_combinations', []):
                    require(set(row)=={'usage','base','ending','surface'} and row['usage'], 'combination structure')
                    require(all(attested(row[k]) for k in ['base','ending','surface']), 'combination source missing')
                for row in co.get('lexical_usage_entries', []):
                    require(set(row)=={'source_expression','forms','source_example'}, 'lexical entry structure')
                    require(row['forms'] and all(attested(f) for f in row['forms']), 'lexical form absent')
                    require(attested(row['source_expression']) and attested(row['source_example']), 'lexical evidence absent')
                for pair in co.get('source_pairs', []):
                    require(set(pair)=={'source','dialect'} and pair['dialect'], 'source pair structure')
                    require(attested(pair['source']) and all(attested(f) for f in pair['dialect']), 'pair source absent')
                if co.get('original_consulted') is False:
                    require(co['operational_status']=='held', 'requotation promoted')


def extend_graph(graph, loaded):
    validate_content(loaded)
    counts = dict(table_rows=0, held_rows=0, absent_rows=0, example_links=0,
                  suffix_ending_realizations=0, explicit_combinations=0,
                  lexical_usages=0, source_pairs=0, held_edges_demoted=0)
    # The shared builder keeps older sources' historical behavior. For RYU, a
    # held form is retained for audit but never exposed by a candidate relation.
    for e in graph.edges:
        if e['source'].startswith(SID+'-') and e['relation'] in {'lists_candidate','realizes_as'}:
            if graph.nodes[e['source']]['properties'].get('operational_status')=='held':
                e['relation']='records_form'; counts['held_edges_demoted']+=1

    def node(id_, type_, **p):
        require(id_ not in graph.nodes, 'RYU derived ID collision')
        graph.nodes[id_] = dict(id=id_, type=type_, properties=copy.deepcopy(p))

    def edge(s, r, t, **p):
        graph.edges.append(dict(source=s, relation=r, target=t, properties=p))

    def scope(key, c, a, status):
        edge(key,'scoped_by',c['id']); edge(key,'derived_from',a['id'])
        if a['condition'] is not None: edge(key,'condition',a['id']+'.condition')
        for eid in c['evidence_refs']: edge(key,'supported_by',eid)

    def construction(key, c, a, row, features):
        status = 'held' if row.get('hold') else a['content']['operational_status']
        uid=key+'.usage'
        node(uid,'Usage',label=row['usage'],features=features,claim_ref=c['id'])
        node(key,'Construction',source_entry=row,operational_status=status,
             evidence_refs=c['evidence_refs'],claim_ref=c['id'],not_operationally_approved=True)
        for parent in a['target_refs']: edge(parent,'has_subusage',uid)
        edge(uid,'participates_in',key); scope(key,c,a,status)
        cond=key+'.condition'; node(cond,'Condition',op='all'); edge(key,'condition',cond)
        for i,(feature,value) in enumerate(features.items()):
            atom=cond+f'.{i}'; node(atom,'Condition',op='eq',feature=feature,value=value)
            edge(atom,'evaluates',uid); edge(cond,'operand',atom,index=i)
        return status

    def form(key, slot, text, layer, status, relation):
        fid=key+'.'+slot
        node(fid,'Form',text=text,layer=layer,operational_status=status)
        edge(key,'records_form' if status=='held' else relation,fid,
             operational_status=status,candidate_only=True)

    for _,data in loaded:
        for c in data['claims']:
            for a in c['assertions']:
                co=a['content']
                for i,row in enumerate(co.get('construction_rows', [])):
                    key=a['id']+f'.source_table.{i}'
                    features=dict(source_usage=row['usage'],**row.get('features',{}))
                    if row.get('speech_level'):features['speech_level']=row['speech_level']
                    status=construction(key,c,a,row,features)
                    form(key,'ending',row['ending'],'source_ending_or_auxiliary_schema',status,'combines_with')
                    counts['table_rows']+=1
                    if status=='held': counts['held_rows']+=1
                    if row['surface'] is None:
                        graph.nodes[key]['properties']['missing_source_cell']=True
                        counts['absent_rows']+=1
                    else:
                        form(key,'example',row['surface'],'whole_source_example',status,'exemplified_by')
                        counts['example_links']+=1
                for i,row in enumerate(co.get('source_derivations', [])):
                    key=a['id']+f'.derivation.{i}'
                    status=construction(key,c,a,row,dict(source_usage=row['usage'],causative_suffix=row['suffix'],following_ending=row['ending']))
                    form(key,'suffix',row['suffix'],'source_causative_suffix',status,'combines_with')
                    form(key,'ending',row['ending'],'source_imperative_ending',status,'combines_with')
                    form(key,'surface',row['surface'],'source_explicit_inflection',status,'realizes_as')
                    counts['suffix_ending_realizations']+=1
                for i,row in enumerate(co.get('attested_combinations', [])):
                    key=a['id']+f'.combination.{i}'
                    status=construction(key,c,a,row,dict(source_usage=row['usage'],source_base=row['base'],source_ending=row['ending']))
                    form(key,'base',row['base'],'source_explicit_base',status,'has_base')
                    if row['ending']=='(생략)':
                        graph.nodes[key]['properties']['source_omission']=True
                    else:form(key,'ending',row['ending'],'source_particle',status,'combines_with')
                    form(key,'surface',row['surface'],'source_explicit_phrase_form',status,'realizes_as')
                    counts['explicit_combinations']+=1
                for i,row in enumerate(co.get('lexical_usage_entries', [])):
                    key=a['id']+f'.lexical.{i}'
                    entry=dict(row,usage=row['source_expression'])
                    status=construction(key,c,a,entry,dict(source_correspondence=row['source_expression']))
                    for j,f in enumerate(row['forms']):
                        form(key,f'form.{j}',f,'source_adverb_form',status,'lists_candidate')
                    form(key,'example',row['source_example'],'whole_source_example',status,'exemplified_by')
                    counts['lexical_usages']+=1
                for i,row in enumerate(co.get('source_pairs', [])):
                    key=a['id']+f'.pair.{i}'
                    status=construction(key,c,a,dict(row,usage=row['source']),dict(source_correspondence=row['source']))
                    for j,f in enumerate(row['dialect']):form(key,f'form.{j}',f,'explicit_correspondence',status,'lists_candidate')
                    counts['source_pairs']+=1
    require(all(e['source'] in graph.nodes and e['target'] in graph.nodes for e in graph.edges), 'dangling RYU edge')
    return counts


def run(export_graph=False, check_receipt=False):
    from check_phonology import read_phonology, extend_graph as extend_phonology
    from check_overview import read_overview, extend_graph as extend_overview
    loaded=read_ryu(); require(loaded, 'no RYU bundles')
    honor=[(p,json.loads(p.read_text())) for p in sorted(HERE.glob('namu_honorifics_batch_*_p*.json')) if not p.name.endswith('.coverage.json')]
    phonology=read_phonology(); overview=read_overview()
    from check_jo2018 import read_jo, extend_graph as extend_jo
    jo=read_jo()
    all_loaded=read_bundles()+honor+phonology+overview+loaded+jo
    discovered={p for p in HERE.glob('*.json') if not p.name.endswith('.coverage.json')
                and set(json.loads(p.read_text())) >= {'format_version','entities','evidence','claims','policies'}}
    require(discovered=={p for p,_ in all_loaded}, 'unhandled saved bundle')
    schema=json.loads((HERE/'bundle.schema.json').read_text());registry=json.loads((HERE.parent/'source_registry.json').read_text())
    merged,graph,result=audit(all_loaded,registry,schema)
    result['phonology_counts']=extend_phonology(graph,phonology)
    result['overview_counts']=extend_overview(graph,overview)
    result['ryu_counts']=extend_graph(graph,loaded)
    if jo:result['jo_counts']=extend_jo(graph,jo)
    source=next(s for s in registry['sources'] if s['source_id']==SID)
    require(hashlib.sha256((ROOT/source['file']['path']).read_bytes()).hexdigest()==source['file']['sha256'], 'RYU PDF hash changed')
    pages=subprocess.run(['pdftotext','-layout',str(ROOT/source['file']['path']),'-'],text=True,capture_output=True,check=True).stdout.split('\f')
    require(len(pages)==39 and not pages[-1].strip(), 'RYU PDF page count')
    claims={c['id']:c for _,d in loaded for c in d['claims']}; evidence={e['id']:e for _,d in loaded for e in d['evidence']}
    for e in evidence.values():
        require(normalize(e['excerpt']) in normalize(''.join(pages[p-1] for p in e['pdf_pages'])), 'excerpt absent: '+e['id'])
    ledgers=[json.loads(p.with_suffix('.coverage.json').read_text()) for p,_ in loaded]
    dispositions=[p for ledger in ledgers for p in ledger['page_dispositions']]
    require([p['page'] for p in dispositions]==list(range(1,39)), 'whole-source page ledger')
    for (path,data),ledger in zip(loaded,ledgers):
        local_e={e['id']:e for e in data['evidence']}
        for p in ledger['page_dispositions']:
            expected=[c['id'] for c in data['claims'] if any(p['page'] in local_e[e]['pdf_pages'] for e in c['evidence_refs'])]
            require(p['claim_ids']==expected, 'local coverage references')
        require(all(i['issue'] and i['location'] and (i['claim_id'] is None or i['claim_id'] in claims)
                    for i in ledger['open_items']), 'hold ledger reference')
    survey=ledgers[-1]['source_context']['attitude_survey']
    require(survey['elderly']['date']=='2014-08-18' and survey['children']['date']=='2014-08-25', 'survey dates conflated')
    for q in survey['questions']:
        require(sum(q['children_counts'])==45 and sum(q['elderly_counts'])==40, 'attitude table counts')
    for p,t in ledgers[-1]['source_context']['context_page_excerpts'].items():
        require(normalize(t) in normalize(pages[int(p)-1]), 'context excerpt changed')

    checks=[]
    def check(name,ok):require(ok,name);checks.append(name)
    key='RYU2014-B005-C002.a.derivation.0'
    check('깨아라 connects -우- and -아라 with source conditions',
          [graph.nodes[f]['properties']['text'] for f in graph.neighbors(key,'combines_with')]==['-우-','-아라'] and
          [graph.nodes[f]['properties']['text'] for f in graph.neighbors(key,'realizes_as')]==['깨아라'] and
          'RYU2014-B005-C002.a.condition' in graph.neighbors(key,'condition'))
    uid=key+'.usage'; condition=key+'.condition'
    facts={uid:dict(source_usage='깨아라 사동 명령',causative_suffix='-우-',following_ending='-아라')}
    check('suffix and ending conditions are both necessary',graph.evaluate(condition,facts) is True)
    del facts[uid]['following_ending']
    check('missing ending condition stays unknown',graph.evaluate(condition,facts) is None)
    facts[uid]['following_ending']='-고'
    check('different ending rejected by source derivation',graph.evaluate(condition,facts) is False)
    for i,text in enumerate(['깨아라','돋가라','낮차라']):
        key=f'RYU2014-B005-C002.a.derivation.{i}'
        check('explicit causative inflection '+text,[graph.nodes[f]['properties']['text'] for f in graph.neighbors(key,'realizes_as')]==[text])
    check('held RYU rows/forms never expose a generation candidate',not any(
        e['source'].startswith(SID+'-') and e['relation'] in {'lists_candidate','realizes_as','exemplified_by','combines_with'} and
        graph.nodes[e['source']]['properties'].get('operational_status')=='held' for e in graph.edges))
    key='RYU2014-B003-C003.a.source_table.1'
    check('absent propositive -세 has no surface example',graph.nodes[key]['properties']['missing_source_cell'] and not any(
        graph.nodes[e['target']]['properties'].get('layer')=='whole_source_example' for e in graph.edges if e['source']==key))
    for key in ['RYU2014-B003-C003.a.source_table.5','RYU2014-B005-C007.a.source_table.0']:
        check('mismatched source example held '+key,graph.nodes[key]['properties']['operational_status']=='held' and not graph.neighbors(key,'exemplified_by'))
    key='RYU2014-B004-C014.a.source_table.'
    check('same 생일인 surface retains different source tense conditions',
          graph.nodes[key+'3.usage']['properties']['features']['source_tense']=='현재' and
          graph.nodes[key+'4.usage']['properties']['features']['source_tense']=='과거')
    check('original claim fields survive graph conversion',all(graph.nodes[c['id']]['properties']==c for c in merged['claims']))
    # Negative tests guard the new nested contracts without relaxing old checks.
    mutations=[
        ('invented surface rejected',2,lambda d:d['claims'][0]['assertions'][0]['content']['construction_rows'][0].update(surface='출처에 없는 예문입니다')),
        ('missing cell without hold rejected',2,lambda d:d['claims'][2]['assertions'][0]['content']['construction_rows'][1].update(hold=None)),
        ('survey percentage in grammar rejected',0,lambda d:d['claims'][0]['assertions'][0]['content'].update(probability='20%')),
        ('numeric survey probability rejected',0,lambda d:d['claims'][0]['assertions'][0]['content'].update(probability=0.2)),
        ('unsupported suffix rejected',4,lambda d:d['claims'][1]['assertions'][0]['content']['source_derivations'][0].update(suffix='-미제시-')),
        ('derivation without conditions rejected',4,lambda d:d['claims'][1]['assertions'][0].update(condition=None)),
    ]
    for name,i,mutate in mutations:
        path,data=loaded[i];changed=copy.deepcopy(data);mutate(changed)
        try:validate_content([(path,changed)])
        except (ValueError,KeyError,TypeError):rejected=True
        else:rejected=False
        check(name,rejected)
    result.update(nodes=len(graph.nodes),edges=len(graph.edges),ryu_claim_count=len(claims),ryu_checks=checks,
                  ryu_held_claim_count=sum(c['assertions'][0]['content']['operational_status']=='held' for c in claims.values()),
                  ryu_open_issue_count=sum(len(l['open_items']) for l in ledgers),ryu_pdf_sha256=source['file']['sha256'])
    payload=dict(format_version='v3-draft-graph.1',status='draft_not_operational',
                 bundles=[dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p,_ in all_loaded],
                 nodes=list(graph.nodes.values()),edges=graph.edges,validation=result)
    if export_graph:export(HERE/'current_kg.graph.json',payload)
    if check_receipt:
        receipt=json.loads((HERE/'background_run/RYU2014.receipt.json').read_text())
        require(receipt['source_id']==SID and receipt['status']=='extracted_with_holds', 'receipt identity')
        require(receipt['bundles']==[str(p.relative_to(ROOT)) for p,_ in loaded], 'receipt bundles')
        require(receipt['claim_count']==len(claims), 'receipt claim count')
        require([p['page'] for p in receipt['pages']]==list(range(1,39)), 'receipt pages')
        seen=set()
        for page,disposition in zip(receipt['pages'],dispositions):
            expected=[cid for cid,c in claims.items() if any(page['page'] in evidence[e]['pdf_pages'] for e in c['evidence_refs'])]
            require(page['claim_ids']==expected, 'receipt page/evidence mismatch')
            require(page['status']==disposition['status'] and page['reason']==disposition['reason'], 'receipt disposition changed')
            require(page['status'] in {'extracted','context_only','held'} and page['reason'], 'page status')
            if page['status']=='extracted':require(expected, 'empty extracted page')
            if page['status']=='context_only':require(not expected, 'context page with extraction')
            seen.update(expected)
        require(seen==set(claims), 'receipt omitted claim')
        require(receipt['open_issues']==[i['location']+': '+i['issue'] for l in ledgers for i in l['open_items']], 'receipt holds omitted')
        require(receipt['validation']['passed'] is True and receipt['validation']['commands'], 'receipt validation')
        saved=json.loads((HERE/'current_kg.graph.json').read_text())
        for k in ['bundles','nodes','edges']:require(saved[k]==payload[k], 'graph reconstruction mismatch: '+k)
        result['receipt_and_saved_graph']='passed'
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--export',action='store_true');p.add_argument('--check-receipt',action='store_true')
    args=p.parse_args();print(json.dumps(run(args.export,args.check_receipt),ensure_ascii=False,indent=2))

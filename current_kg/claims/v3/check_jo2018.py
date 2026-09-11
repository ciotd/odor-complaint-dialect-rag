"""Validate JO2018 draft extraction and reconstruct all saved v3 bundles.

Reads local source only. Does not issue a whole-source receipt or infer morphology.
New nested contracts retain literal table blanks, source analyses and holds.
Whole-page review and complete grammatical extraction are separate states.
"""
import argparse
import copy
import hashlib
import json
import re
import subprocess
from check_all_v3 import HERE, ROOT, audit, export, read_bundles, require

SID = 'JO2018'


def export_graph_delta(path, payload):
    """Use exact full-file patch context; repeated JSON blocks are ambiguous hunks.

    Avoid quadratic line matching on the large graph. Unchanged exports are no-ops.
    """
    after = json.dumps(payload, ensure_ascii=False, indent=2) + '\n'
    if path.exists() and path.read_text() == after:
        return
    export(path, payload)
    require(json.loads(path.read_text()) == payload, 'graph export differs from requested payload')


def read_jo():
    return [(p, json.loads(p.read_text())) for p in sorted(HERE.glob('jo2018_batch_*_p*.json'))
            if not p.name.endswith('.coverage.json')]


def norm(s):
    return re.sub(r'\s+', '', s)


def validate_receipt(receipt, loaded):
    """A receipt certifies page disposition, never resolution of extraction holds."""
    require(set(receipt)=={'source_id','status','bundles','pages','claim_count','validation','open_issues'},
            'receipt fields')
    ledgers=[json.loads(p.with_suffix('.coverage.json').read_text()) for p,_ in loaded]
    expected=[entry for ledger in ledgers for entry in ledger['page_dispositions']]
    require([e['page'] for e in expected]==list(range(1,266)), 'receipt before full page review')
    require(receipt['source_id']==SID, 'receipt source')
    require(receipt['pages']==expected, 'receipt dispositions do not match reviewed coverage')
    require(receipt['bundles']==[str(p.relative_to(ROOT)) for p,_ in loaded], 'receipt bundles')
    require(type(receipt['claim_count']) is int and
            receipt['claim_count']==sum(len(d['claims']) for _,d in loaded), 'receipt claim count')
    holds=any(l['open_items'] for l in ledgers)
    require(receipt['status']==('extracted_with_holds' if holds else 'extracted_draft'), 'receipt holds hidden')
    require(isinstance(receipt['open_issues'],list) and
            all(isinstance(x,str) and x for x in receipt['open_issues']) and
            (bool(receipt['open_issues']) or not holds), 'receipt issues missing')
    v=receipt['validation']
    require(set(v)=={'passed','commands'} and v['passed'] is True and v['commands'] and
            all(isinstance(x,str) and x for x in v['commands']), 'receipt validation missing')


def validate_content(loaded, pages):
    claim_ids={c['id'] for _,data in loaded for c in data['claims']}
    claims_by_id={c['id']: c for _,data in loaded for c in data['claims']}
    for path, data in loaded:
        ledger = json.loads(path.with_suffix('.coverage.json').read_text())
        ev = {e['id']: e for e in data['evidence']}
        require(ledger['audit']['text_read'] and ledger['audit']['pdftotext_layout'], 'reading audit')
        for e in ev.values():
            require(e['source_id'] == SID, 'JO source substitution')
            require(norm(e['excerpt']) in norm(''.join(pages[p-1] for p in e['pdf_pages'])), 'JO excerpt absent: '+e['id'])
        for c in data['claims']:
            require(c['id'].startswith(SID+'-B'), 'JO namespace')
            raw = norm(''.join(ev[e]['excerpt'] for e in c['evidence_refs']))
            def attested(s):
                require(isinstance(s, str) and s and (norm(s) in raw or norm(s).strip('-') in raw), 'unattested JO expression: '+str(s))
            def no_rates(x):
                if isinstance(x, dict):
                    require(not set(x) & {'probability','usage_rate','percentage','percent','sampling_weight','counts','printed_total','printed_subtotal'}, 'rate/count in grammar')
                    for v in x.values(): no_rates(v)
                elif isinstance(x, list):
                    for v in x: no_rates(v)
            for a in c['assertions']:
                co = a['content']; no_rates(co)
                require('%' not in json.dumps(co,ensure_ascii=False),'percentage in grammar')
                for k in ['source_locator','source_analysis','extractor_interpretation','generation_policy']:
                    require(isinstance(co.get(k),str) and co[k], 'missing attribution '+k)
                require(co['operational_status'] in {'held','draft_not_approved'}, 'JO promotion')
                if co.get('reported_source'):require(co['operational_status']=='held', 'requotation promoted')
                for link in co.get('cross_bundle_qualifies', []):
                    require(set(link)=={'target','basis'} and link['basis']=='extractor_comparison', 'cross-bundle attribution')
                    require(link['target'] in claim_ids and link['target']!=c['id'], 'cross-bundle claim missing')
                for f in co.get('forms', []):attested(f)
                for f in co.get('source_rejected', []):
                    attested(f);require(f not in co.get('forms',[]), 'rejection promoted')
                for ex in co.get('source_examples', []):
                    require(ex['judgment']=='source_attestation_not_acceptability_test', 'example judgment')
                    attested(ex['text'])
                for values in co.get('source_inventory',{}).values():
                    require(isinstance(values,list) and values,'inventory shape')
                    for f in values:attested(f)
                for f, reason in co.get('source_inventory_holds', {}).items():
                    require(f in [x for xs in co['source_inventory'].values() for x in xs]
                            and isinstance(reason,str) and reason, 'inventory hold member/reason')
                for seq in co.get('explicit_sequence_schemas', []):
                    require(set(seq)=={'base','preceding','ending','optional_postposed'}, 'sequence fields')
                    for value in seq.values():attested(value)
                    require(155 in ledger['audit']['pdf_pages_visually_checked'], 'figure3 visual audit')
                if 'explicit_sequence_schemas' in co:
                    require(co['explicit_sequence_schemas']==[
                        dict(base='어간',preceding='-시이-',ending='-소',optional_postposed='-이'),
                        dict(base='어간',preceding='-이시-',ending='-소',optional_postposed='-이')],
                        'figure3 sequence alignment')
                for item in co.get('interaction_pairs', []):
                    require(set(item)=={'speaker','listener','forms'} and item['forms'], 'interaction fields')
                    attested(item['speaker']);attested(item['listener'])
                    for f in item['forms']:attested(f)
                for item in co.get('postposed_element_constraints', []):
                    require(set(item)=={'base','element','omissible','meaning'}
                            and type(item['omissible']) is bool, 'postposed constraint fields')
                    attested(item['base']);attested(item['element'])
                    if item['meaning'] is not None:attested(item['meaning'])
                if 'postposed_element_constraints' in co:
                    require([(x['base'],x['element'],x['omissible']) for x in co['postposed_element_constraints']]
                            ==[('-ㅂ시더','-이',True),('-시데이','-이',False)], 'PDF180 optional/required contrast')
                for binding in co.get('inflection_cell_links', []):
                    require(set(binding)=={'target_claim','row','column','surface','ending','basis'}, 'inflection link fields')
                    require(binding['basis']=='extractor_comparison', 'inflection link attribution')
                    require(binding['target_claim'] in claims_by_id, 'inflection link target')
                    target=claims_by_id[binding['target_claim']]['assertions'][0]['content']
                    ri,ci=binding['row'],binding['column']
                    require(type(ri) is int and type(ci) is int and 0<=ri<len(target['inflection_rows'])
                            and 0<=ci<len(target['inflection_headers']), 'inflection link coordinates')
                    row=target['inflection_rows'][ri]
                    require(binding['surface']==row['cells'][ci] and binding['surface'] is not None, 'inflection link surface')
                    attested(binding['ending'])
                    require(binding['surface'].endswith(binding['ending'].lstrip('-')), 'inflection ending literal suffix')
                    def atoms(tree):
                        if tree['op']=='eq':return [tree]
                        return [v for arg in tree['args'] for v in atoms(arg)]
                    require(a['condition'] is not None and a['condition']['op']=='all', 'inflection link scope required')
                    features={v['feature']:v['value'] for v in atoms(a['condition'])}
                    require(features.get('speech_level')==row['speech_level'] and
                            features.get('sentence_function')==target['inflection_headers'][ci], 'inflection link function/level')
                for group in co.get('source_inventory_groupings', []):
                    require(set(group)=={'members','printed_joiner','pdf_page'} and group['printed_joiner']=='/', 'inventory visual grouping')
                    require(group['pdf_page'] in ledger['audit']['pdf_pages_visually_checked'], 'inventory grouping visual audit')
                    require(len(group['members'])>1, 'inventory grouping members')
                    inventory=[f for fs in co['source_inventory'].values() for f in fs]
                    for f in group['members']:attested(f);require(f in inventory, 'ungrounded inventory grouping')
                for ending, targets in co.get('attachment_by_ending', {}).items():
                    attested(ending)
                    require(targets and len(targets)==len(set(targets)), 'attachment targets')
                    for target in targets:attested(target)
                for row in co.get('ending_function_rows', []):
                    require(set(row)=={'ending','function','features','hold'} and row['features'], 'ending/function row')
                    attested(row['ending']);attested(row['function'])
                    require(row['hold'] is None or isinstance(row['hold'],str) and row['hold'], 'ending/function hold')
                    require(all(isinstance(k,str) and k and isinstance(v,str) and v for k,v in row['features'].items()), 'ending/function features')
                for row in co.get('sense_rows',[]):
                    require(row['usage'] and row['forms'],'sense scope')
                    for f in row['forms']:attested(f)
                    if 'correspondence' in row:attested(row['correspondence'])
                for row in co.get('construction_rows', []):
                    require(set(row)=={'usage','ending','surface','layer','features','hold'}, 'JO row structure')
                    require(row['usage'] and row['layer']=='source_surface', 'JO row layer')
                    attested(row['ending']);attested(row['surface'])
                    require(row['hold'] is None or isinstance(row['hold'],str) and row['hold'], 'row hold')
                    require(row['features'] and all(isinstance(k,str) and k and isinstance(v,str) and v for k,v in row['features'].items()), 'row features')
                for ending, stems in co.get('lexical_restriction',{}).items():
                    attested(ending)
                    require(stems and all(isinstance(s,str) for s in stems), 'lexical restriction')
                    for stem in stems:attested(stem)
                    matches=[r for r in co['construction_rows'] if r['ending']==ending]
                    require(matches and all(r['features']['stem'] in stems for r in matches), 'lexical scope conflict')
                if 'overlap_rows' in co:
                    require(co['overlap_headers']==['감탄법','서술법','의문법','명령법','청유법'], 'overlap columns')
                    require(47 in ledger['audit']['pdf_pages_visually_checked'], 'overlap visual audit')
                    for row in co['overlap_rows']:
                        require(set(row)=={'style','speech_level','ending','cells'}, 'overlap row fields')
                        require(len(row['cells'])==5 and all(x in [None,'○'] for x in row['cells']), 'overlap cells')
                        for key in ['style','speech_level','ending']:attested(row[key])
                    require(len(co['overlap_rows'])==19, 'overlap row count')
                    # Manually read from PDF47's actual circle/blank columns.
                    expected=['11000','11000','11000','11010','11100','11011','11010','11000','11000','11100','11010','11100','11100','11100','11100','11100','11100','11000','11100']
                    require([''.join('1' if v=='○' else '0' for v in r['cells']) for r in co['overlap_rows']]==expected,'PDF47 visual cell alignment')
                if 'inflection_rows' in co:
                    require(co['inflection_headers']==['서술법','의문법','명령법','청유법'], 'inflection headers')
                    require(65 in ledger['audit']['pdf_pages_visually_checked'], 'inflection visual audit')
                    for row in co['inflection_rows']:
                        require(set(row)=={'lemma','speech_level','cells'} and len(row['cells'])==4, 'inflection row')
                        attested(row['lemma']);attested(row['speech_level'])
                        for f in row['cells']:
                            if f is None: require(co.get('missing_cell_reason'), 'unexplained blank')
                            else:attested(f)
                    require([r['cells'] for r in co['inflection_rows']]==[[None,None,'가이소','가입시다'],['갔소','갔소','가소','갑시다'],['가네','가는가','가게','가세'],['간다','가나','가라','가자']],'PDF65 visual cell alignment')
                for row in co.get('classification_rows', []):
                    require(set(row)=={'function','features'} and row['features'], 'classification row')
                    attested(row['function'])
                    if 'source_ending' in row['features']:attested(row['features']['source_ending'])
        require([p['page'] for p in ledger['page_dispositions']]==ledger['body_pages'], 'JO page ledger')
        for p in ledger['page_dispositions']:
            expected=[c['id'] for c in data['claims'] if any(p['page'] in ev[e]['pdf_pages'] for e in c['evidence_refs'])]
            require(p['claim_ids']==expected and p['reason'], 'JO coverage refs')
            require(p['status'] in {'extracted','context_only','held'}, 'JO page status')
            require((p['status']=='extracted')==bool(expected), 'extracted status mismatch')
        ids={c['id'] for c in data['claims']}
        for item in ledger['open_items']:
            require(item['location'] and item['issue'] and (item['claim_id'] is None or item['claim_id'] in ids), 'hold reference')
        period=ledger['source_context']['corpus_period_basis']
        require(period['page']==29 and norm(period['excerpt']) in norm(pages[28]),'corpus period provenance')
        require(period['publication_year']==2018 and period['individual_utterance_date'] is None,'publication and utterance conflated')
        for table in ledger['source_context'].values():
            if not isinstance(table,dict) or table.get('kind')!='source_frequency_context_not_generation':continue
            require(table['page'] in ledger['audit']['pdf_pages_visually_checked'], 'frequency table visual audit')
            require(table['no_generation_weight'] is True and table['missing_mark'], 'frequency scope')
            require(table['columns']==['상주','구미','대구','달성','성주','군위','경주','영덕','안동','예천','봉화'], 'frequency columns')
            for row in table['rows']:
                require(norm(row['ending']).strip('-') in norm(pages[table['page']-1]), 'frequency ending absent')
                require(len(row['counts'])==len(table['columns']), 'frequency table width')
                require(all(v is None or type(v) is int and v>=0 for v in row['counts']), 'frequency cells')
                require(type(row['printed_total']) is int and row['printed_total']>=0, 'printed frequency total')


def extend_graph(graph, loaded):
    counts=dict(source_rows=0,inflection_cells=0,overlap_cells=0,missing_cells=0,realizations=0,held_realizations=0,ending_schemas=0,ending_function_rows=0,attachment_rows=0,sequence_schemas=0,postposed_constraints=0,inflection_ending_links=0,held_form_paths_blocked=0)
    held_forms={}
    for _,d in loaded:
        for c in d['claims']:
            for a in c['assertions']:
                co=a['content']
                held_forms[c['id']]={r['surface'] for r in co.get('construction_rows',[]) if r['hold']}
                held_forms[c['id']].update(co.get('source_inventory_holds',{}))
    for e in graph.edges:
        if e['source'].startswith(SID+'-') and e['relation'] in {'lists_candidate','realizes_as'} and graph.nodes[e['source']]['properties'].get('operational_status')=='held':
            e['relation']='records_form'
        if e['relation'] in {'lists_candidate','realizes_as'}:
            source=graph.nodes[e['source']]['properties'];target=graph.nodes[e['target']]['properties']
            if target.get('text') in held_forms.get(source.get('claim_ref'),set()):
                e['relation']='records_form';e['properties']['operational_status']='held'
                target['operational_status']='held';counts['held_form_paths_blocked']+=1
    def node(i,t,**props):
        require(i not in graph.nodes,'JO graph collision')
        graph.nodes[i]=dict(id=i,type=t,properties=copy.deepcopy(props))
    def edge(s,r,t,**props):graph.edges.append(dict(source=s,relation=r,target=t,properties=props))
    def construction(key,c,a,features,hold=None):
        status='held' if hold or a['content']['operational_status']=='held' else 'draft_not_approved'
        node(key,'Construction',operational_status=status,hold=hold,claim_ref=c['id'],evidence_refs=c['evidence_refs'])
        uid=key+'.usage';node(uid,'Usage',features=features)
        for parent in a['target_refs']:edge(parent,'has_subusage',uid)
        edge(uid,'participates_in',key);edge(key,'scoped_by',c['id']);edge(key,'derived_from',a['id'])
        for e in c['evidence_refs']:edge(key,'supported_by',e)
        if a['condition'] is not None:edge(key,'condition',a['id']+'.condition')
        cond=key+'.condition';node(cond,'Condition',op='all');edge(key,'condition',cond)
        for i,(k,v) in enumerate(features.items()):
            atom=cond+f'.{i}';node(atom,'Condition',op='eq',feature=k,value=v);edge(atom,'evaluates',uid);edge(cond,'operand',atom,index=i)
        return status
    def form(key,slot,value,layer,status,relation):
        f=key+'.'+slot;node(f,'Form',text=value,layer=layer,operational_status=status)
        edge(key,'records_form' if status=='held' else relation,f,candidate_only=True,operational_status=status)
    for _,d in loaded:
        for c in d['claims']:
            for a in c['assertions']:
                co=a['content']
                for link in co.get('cross_bundle_qualifies', []):
                    edge(c['id'],'qualifies',link['target'],basis=link['basis'],evidence_refs=c['evidence_refs'])
                for i,row in enumerate(co.get('construction_rows',[])):
                    key=a['id']+f'.source_row.{i}'
                    status=construction(key,c,a,dict(row['features'],source_ending=row['ending']),row['hold'])
                    form(key,'ending',row['ending'],'source_ending_or_explicit_sequence',status,'combines_with')
                    form(key,'surface',row['surface'],'source_surface',status,'realizes_as')
                    counts['source_rows']+=1;counts['realizations' if status!='held' else 'held_realizations']+=1
                for i,row in enumerate(co.get('inflection_rows',[])):
                    for j,(function,surface) in enumerate(zip(co['inflection_headers'],row['cells'])):
                        key=a['id']+f'.inflection.{i}.{j}'
                        status=construction(key,c,a,dict(lemma=row['lemma'],speech_level=row['speech_level'],sentence_function=function),co['missing_cell_reason'] if surface is None else None)
                        counts['inflection_cells']+=1
                        if surface is None:counts['missing_cells']+=1;continue
                        form(key,'surface',surface,'source_table_inflection_unsegmented',status,'realizes_as');counts['realizations']+=1
                for i,row in enumerate(co.get('overlap_rows',[])):
                    for j,(function,mark) in enumerate(zip(co['overlap_headers'],row['cells'])):
                        key=a['id']+f'.overlap.{i}.{j}'
                        status=construction(key,c,a,dict(style=row['style'],speech_level=row['speech_level'],sentence_function=function),None if mark else '원표 빈칸: 금지 판정 아님')
                        counts['overlap_cells']+=1
                        graph.nodes[key]['properties']['source_mark']=mark
                        if mark:form(key,'ending',row['ending'],'source_ending_schema',status,'combines_with')
                for i,row in enumerate(co.get('classification_rows',[])):
                    key=a['id']+f'.classification.{i}'
                    status=construction(key,c,a,dict(row['features'],sentence_function=row['function']))
                    if 'source_ending' in row['features']:
                        form(key,'ending',row['features']['source_ending'],'source_ending_schema',status,'combines_with')
                for group,values in co.get('source_inventory',{}).items():
                    for i,value in enumerate(values):
                        key=a['id']+f'.ending_inventory.{group}.{i}'
                        status=construction(key,c,a,dict(source_inventory_group=group),co.get('source_inventory_holds',{}).get(value))
                        form(key,'ending',value,'source_ending_schema_unexpanded',status,'combines_with')
                        counts['ending_schemas']+=1
                for i,seq in enumerate(co.get('explicit_sequence_schemas',[])):
                    key=a['id']+f'.sequence.{i}'
                    status=construction(key,c,a,dict(base=seq['base'],preceding=seq['preceding']))
                    form(key,'preceding',seq['preceding'],'source_sequence_schema',status,'combines_with')
                    form(key,'ending',seq['ending'],'source_ending_schema',status,'combines_with')
                    form(key,'postposed',seq['optional_postposed'],'source_optional_postposed',status,'optionally_combines_with')
                    for index,slot in enumerate(['preceding','ending','postposed']):
                        edge(key,'sequence_member',key+'.'+slot,index=index,optional=slot=='postposed')
                    counts['sequence_schemas']+=1
                for i,item in enumerate(co.get('postposed_element_constraints',[])):
                    key=a['id']+f'.postposed.{i}'
                    status=construction(key,c,a,dict(base=item['base'],element=item['element']))
                    graph.nodes[key]['properties'].update(omissible=item['omissible'],source_meaning=item['meaning'])
                    form(key,'ending',item['base'],'source_ending_schema',status,'combines_with')
                    form(key,'element',item['element'],'source_postposed_element',status,
                         'optionally_combines_with' if item['omissible'] else 'requires_element')
                    counts['postposed_constraints']+=1
                for i,binding in enumerate(co.get('inflection_cell_links',[])):
                    key=a['id']+f'.inflection_binding.{i}'
                    cell=binding['target_claim']+f'.a.inflection.{binding["row"]}.{binding["column"]}'
                    status=construction(key,c,a,dict(source_surface=binding['surface']))
                    edge(key,'links_source_cell',cell,basis='extractor_comparison')
                    edge(key,'scoped_by',binding['target_claim'])
                    for ev in graph.nodes[binding['target_claim']]['properties']['evidence_refs']:edge(key,'supported_by',ev)
                    form(key,'ending',binding['ending'],'source_ending_schema',status,'combines_with')
                    edge(key,'records_form' if status=='held' else 'realizes_as',cell+'.surface',candidate_only=True,operational_status=status)
                    counts['inflection_ending_links']+=1
                for ending,targets in co.get('attachment_by_ending',{}).items():
                    for i,target in enumerate(targets):
                        key=a['id']+f'.attachment.{ending}.{i}'
                        status=construction(key,c,a,dict(attachment_target=target,source_ending=ending))
                        form(key,'ending',ending,'source_ending_schema',status,'combines_with')
                        counts['attachment_rows']+=1
                for i,row in enumerate(co.get('ending_function_rows',[])):
                    key=a['id']+f'.ending_function.{i}'
                    status=construction(key,c,a,dict(row['features'],sentence_function=row['function']),row['hold'])
                    form(key,'ending',row['ending'],'source_ending_schema',status,'combines_with')
                    counts['ending_function_rows']+=1
    require(all(e['source'] in graph.nodes and e['target'] in graph.nodes for e in graph.edges),'JO dangling edge')
    return counts


def run(do_export=False, check_saved=False, check_receipt=False):
    from check_phonology import read_phonology, extend_graph as phonology_graph
    from check_overview import read_overview, extend_graph as overview_graph
    from check_ryu2014 import read_ryu, extend_graph as ryu_graph
    honorifics=[(p,json.loads(p.read_text())) for p in sorted(HERE.glob('namu_honorifics_batch_*_p*.json')) if not p.name.endswith('.coverage.json')]
    ph,ov,ry,jo=read_phonology(),read_overview(),read_ryu(),read_jo()
    loaded=read_bundles()+honorifics+ph+ov+ry+jo
    discovered={p for p in HERE.glob('*.json') if not p.name.endswith('.coverage.json')
                and set(json.loads(p.read_text())) >= {'format_version','entities','evidence','claims','policies'}}
    require(discovered=={p for p,_ in loaded},'unhandled saved bundle in JO all-source export')
    registry=json.loads((HERE.parent/'source_registry.json').read_text());schema=json.loads((HERE/'bundle.schema.json').read_text())
    src=next(s for s in registry['sources'] if s['source_id']==SID)
    require(hashlib.sha256((ROOT/src['file']['path']).read_bytes()).hexdigest()==src['file']['sha256'],'JO hash changed')
    pages=subprocess.run(['pdftotext','-layout',str(ROOT/src['file']['path']),'-'],text=True,capture_output=True,check=True).stdout.split('\f')
    require(len(pages)==266 and not pages[-1].strip(),'JO page count')
    validate_content(jo,pages)
    merged,graph,result=audit(loaded,registry,schema)
    result['phonology_counts']=phonology_graph(graph,ph);result['overview_counts']=overview_graph(graph,ov);result['ryu_counts']=ryu_graph(graph,ry)
    result['jo_counts']=extend_graph(graph,jo)
    checks=[]
    def check(name,ok):require(ok,name);checks.append(name)
    # Source-specific assertions: blank cells and ambiguous analyses stay unavailable.
    key='JO2018-B005-C013.a.source_row.2';uid=key+'.usage'
    facts={uid:dict(stem='오-',sentence_function='명령법',source_ending='-ㄴ나')}
    check('온나 explicit stem and ending',graph.evaluate(key+'.condition',facts) is True and [graph.nodes[f]['properties']['text'] for f in graph.neighbors(key,'realizes_as')]==['온나'])
    facts[uid]['stem']='도-';check('온나 wrong stem blocked',graph.evaluate(key+'.condition',facts) is False)
    del facts[uid]['stem'];check('온나 unknown stem remains unknown',graph.evaluate(key+'.condition',facts) is None)
    key='JO2018-B004-C010.a.condition';uid='JO2018-B004-C010.usage'
    check('해여 하소 친밀 condition',[graph.evaluate(key,{uid:dict(cooccurring_style='하소체',relationship=r)}) for r in ['친밀한 관계','낯선 관계']]==[True,False])
    check('가다 empty 하이소 declarative has no invented form',not graph.neighbors('JO2018-B005-C004.a.inflection.0.0','realizes_as'))
    check('held -겠세 analysis not promoted',not graph.neighbors('JO2018-B003-C003.a.source_row.0','realizes_as'))
    check('군 interrogative blank preserved',graph.nodes['JO2018-B003-C002.a.overlap.17.2']['properties']['source_mark'] is None)
    check('held JO candidates blocked',not any(e['source'].startswith(SID+'-') and e['relation'] in {'lists_candidate','realizes_as','combines_with'} and graph.nodes[e['source']]['properties'].get('operational_status')=='held' for e in graph.edges))
    check('claim roundtrip',all(graph.nodes[c['id']]['properties']==c for c in merged['claims']))
    if any(c['id']=='JO2018-B013-C015' for _,d in jo for c in d['claims']):
        key='JO2018-B010-C012.a.classification.1';uid=key+'.usage'
        facts={uid:dict(predicate_pos='동사',attachment='어간 직접 결합',meaning='정중하게 권함',source_ending='-구려',sentence_function='명령법')}
        check('구려 command source ending linked',graph.evaluate(key+'.condition',facts) is True and [graph.nodes[f]['properties']['text'] for f in graph.neighbors(key,'combines_with')]==['-구려'])
        facts[uid]['attachment']='선어말어미 -겠-';check('구려 command rejects prefinal attachment',graph.evaluate(key+'.condition',facts) is False)
        del facts[uid]['attachment'];check('구려 missing attachment stays unknown',graph.evaluate(key+'.condition',facts) is None)
        keys=['JO2018-B010-C010.a.attachment.-ㅁ세.'+str(i) for i in range(2)]
        check('ㅁ세 adjective outside explicit targets',all(graph.evaluate(k+'.condition',{k+'.usage':dict(attachment_target='형용사',source_ending='-ㅁ세')}) is False for k in keys))
        check('ㅁ세 verb target linked',any(graph.evaluate(k+'.condition',{k+'.usage':dict(attachment_target='동사',source_ending='-ㅁ세')}) is True for k in keys))
        key='JO2018-B011-C015.a.source_row.1';uid=key+'.usage'
        check('좋아래이 exclamation does not license verb',graph.evaluate(key+'.condition',{uid:dict(sentence_function='서술법',predicate_pos='동사',meaning='감탄',source_ending='-래이')}) is False)
        check('cross-bundle 소 qualification retained','JO2018-B008-C013' in graph.neighbors('JO2018-B009-C007','qualifies'))
        check('pending question distinctions not promoted',all(not graph.neighbors('JO2018-B013-C015.a.ending_function.'+str(i),'combines_with') for i in range(4)))
        inv=[n for n in graph.nodes.values() if '.ending_inventory.' in n['id'] and n['type']=='Construction']
        check('ending inventories are schemas not surfaces',inv and all(not graph.neighbors(n['id'],'realizes_as') for n in inv))
        check('ambiguous 하소 inventory withheld',all(not graph.neighbors(n['id'],'combines_with') for n in inv if n['id'].startswith('JO2018-B013-C002.')))
    if len(jo)>=17:
        key='JO2018-B016-C005.a.condition';uid='JO2018-B016-C005.usage'
        facts={uid:dict(speech_level='해라체',sentence_function='명령법',lexeme='보다')}
        check('래 command licenses source 보다 only',graph.evaluate(key,facts) is True)
        facts[uid]['lexeme']='쓰다';check('래 does not inherit 래이 verbs',graph.evaluate(key,facts) is False)
        del facts[uid]['lexeme'];check('래 unknown lexeme stays unknown',graph.evaluate(key,facts) is None)
        key='JO2018-B015-C019.a.condition';uid='JO2018-B015-C019.usage'
        facts={uid:dict(speech_level='하게체',sentence_function='명령법',predicate_pos='동사',attachment='어간 직접 결합',participant_scope='청자만')}
        check('세 command listener-only match',graph.evaluate(key,facts) is True)
        facts[uid]['participant_scope']='화자와 청자';check('세 inclusive participants not command match',graph.evaluate(key,facts) is False)
        del facts[uid]['participant_scope'];check('세 missing participants unknown',graph.evaluate(key,facts) is None)
        seq='JO2018-B015-C010.a.sequence.'
        check('figure3 two orders without invented surfaces',all(
            [graph.nodes[e['target']]['properties']['text'] for e in graph.edges if e['source']==seq+str(i) and e['relation']=='sequence_member']
            ==[preceding,'-소','-이'] and not graph.neighbors(seq+str(i),'realizes_as')
            for i,preceding in enumerate(['-시이-','-이시-'])))
        post='JO2018-B017-C013.a.postposed.'
        check('시더이 optional and 시데이 required 이',
              bool(graph.neighbors(post+'0','optionally_combines_with')) and
              bool(graph.neighbors(post+'1','requires_element')) and
              not graph.neighbors(post+'1','optionally_combines_with'))
        check('held subrow not leaked through explicit forms',not any(
            e['source'].startswith('JO2018-B015-C006.') and e['relation'] in {'lists_candidate','realizes_as'}
            and graph.nodes[e['target']]['properties'].get('text')=='있이이소' for e in graph.edges))
        check('held 시데이 blocked through inventory and list',not any(
            e['source'].startswith('JO2018-B017-C008.') and e['relation'] in {'lists_candidate','combines_with'}
            and graph.nodes[e['target']]['properties'].get('text')=='-시데이' for e in graph.edges))
        bindings=[n for n in graph.nodes.values() if n['type']=='Construction' and '.inflection_binding.' in n['id']]
        original_ids={'JO2018-B015-C002','JO2018-B015-C012','JO2018-B015-C015',
                      'JO2018-B016-C001','JO2018-B017-C001'}
        original_bindings=[n for n in bindings if n['id'].split('.a.')[0] in original_ids]
        check('five original table cells linked to source endings',len(original_bindings)==5 and all(
            graph.neighbors(n['id'],'links_source_cell') and graph.neighbors(n['id'],'combines_with')
            and len(graph.neighbors(n['id'],'supported_by'))>=2 for n in original_bindings))
        check('table binding surface objects reused',all(graph.neighbors(n['id'],'realizes_as')[0].startswith('JO2018-B005-C004.a.inflection.') for n in bindings))
    if len(jo)>=24:
        check('seven table cells with two propositive bindings',len(bindings)==7 and
              {n['id'].split('.a.')[0] for n in bindings if n not in original_bindings}==
              {'JO2018-B018-C001','JO2018-B018-C010'})
        key='JO2018-B018-C010.a.condition';uid='JO2018-B018-C010.usage'
        facts={uid:dict(speech_level='해라체',sentence_function='청유법',predicate_pos='동작 동사',
                       subject='1인칭 복수',honorific_si_prefinal_present=False,tense_prefinal_present=False)}
        check('자 inclusive dynamic verb matches',graph.evaluate(key,facts) is True)
        facts[uid]['subject']='3인칭';check('자 third person blocked',graph.evaluate(key,facts) is False)
        facts[uid]['subject']='2인칭';facts[uid]['tense_prefinal_present']=True
        check('자 tense prefinal blocked',graph.evaluate(key,facts) is False)
        facts[uid]['tense_prefinal_present']=False;del facts[uid]['subject']
        check('자 unknown subject not promoted',graph.evaluate(key,facts) is None)
        check('held 갑시요 and 서지예 not realization candidates',all(
            not graph.neighbors(cid+'.a.source_row.0','realizes_as')
            for cid in ['JO2018-B022-C008','JO2018-B022-C010']))
        for index,pitch,function in [(0,'상승조','의문법'),(1,'하강조','서술법')]:
            key=f'JO2018-B020-C005.a.classification.{index}';uid=key+'.usage'
            check('래여 '+pitch+' scoped function',graph.evaluate(key+'.condition',
                  {uid:dict(sentence_final_pitch=pitch,sentence_function=function)}) is True)
        key='JO2018-B019-C010.a.ending_function.2';uid=key+'.usage'
        facts={uid:dict(predicate_pos='동사',preceding='회상 -드(더)-',source_ending='-라',sentence_function='서술법')}
        check('라 verb requires retrospective',graph.evaluate(key+'.condition',facts) is True)
        facts[uid]['preceding']='없음';check('라 bare verb not licensed as declarative',graph.evaluate(key+'.condition',facts) is False)
    mutations=[('invented form',lambda d:d[4][1]['claims'][12]['assertions'][0]['content']['construction_rows'][0].update(surface='없는원문형')),
               ('wrong lexical stem',lambda d:d[4][1]['claims'][12]['assertions'][0]['content']['construction_rows'][0]['features'].update(stem='먹-')),
               ('numeric probability',lambda d:d[0][1]['claims'][0]['assertions'][0]['content'].update(probability=0.2)),
               ('overlap table width',lambda d:d[2][1]['claims'][1]['assertions'][0]['content']['overlap_rows'][0]['cells'].pop()),
               ('invented circle in blank',lambda d:d[2][1]['claims'][1]['assertions'][0]['content']['overlap_rows'][17]['cells'].__setitem__(2,'○')),
               ('source forms swapped between functions',lambda d:d[4][1]['claims'][3]['assertions'][0]['content']['inflection_rows'][2]['cells'].reverse()),
               ('false source',lambda d:d[0][1]['evidence'][0].update(source_id='RYU2014'))]
    if len(jo)>=13:
        mutations += [
            ('missing cross-bundle target',lambda d:d[8][1]['claims'][6]['assertions'][0]['content']['cross_bundle_qualifies'][0].update(target='JO2018-B999-C999')),
            ('misattributed cross-bundle target',lambda d:d[8][1]['claims'][6]['assertions'][0]['content']['cross_bundle_qualifies'][0].update(basis='source_statement')),
            ('invented attachment category',lambda d:d[9][1]['claims'][9]['assertions'][0]['content']['attachment_by_ending']['-ㅁ세'].append('감탄사')),
            ('invented function ending',lambda d:d[12][1]['claims'][14]['assertions'][0]['content']['ending_function_rows'][0].update(ending='-없는어미')),
            ('frequency in grammar',lambda d:d[8][1]['claims'][0]['assertions'][0]['content'].update(counts=[242])),
            ('ungrounded visual grouping',lambda d:d[11][1]['claims'][4]['assertions'][0]['content']['source_inventory_groupings'][0]['members'].append('-없는어미')),
        ]
    if len(jo)>=17:
        mutations += [
            ('figure3 reversed source order',lambda d:d[14][1]['claims'][9]['assertions'][0]['content']['explicit_sequence_schemas'].reverse()),
            ('required 이 made optional',lambda d:d[16][1]['claims'][12]['assertions'][0]['content']['postposed_element_constraints'][1].update(omissible=True)),
            ('unknown inventory hold',lambda d:d[16][1]['claims'][7]['assertions'][0]['content']['source_inventory_holds'].update({'-없는형':'hold'})),
            ('table binding wrong function',lambda d:d[14][1]['claims'][1]['assertions'][0]['content']['inflection_cell_links'][0].update(row=1,column=1,surface='갔소',ending='-소')),
            ('table binding invented surface',lambda d:d[14][1]['claims'][1]['assertions'][0]['content']['inflection_cell_links'][0].update(surface='가시이소')),
            ('table binding false attribution',lambda d:d[14][1]['claims'][1]['assertions'][0]['content']['inflection_cell_links'][0].update(basis='source_statement')),
        ]
    for name,mutate in mutations:
        changed=copy.deepcopy(jo);mutate(changed)
        try:validate_content(changed,pages)
        except (ValueError,KeyError,TypeError):rejected=True
        else:rejected=False
        check(name+' rejected',rejected)
    ledgers=[json.loads(p.with_suffix('.coverage.json').read_text()) for p,_ in jo]
    read_pages=[p['page'] for l in ledgers for p in l['page_dispositions']]
    require(read_pages==list(range(1,max(read_pages)+1)),'partial ledger gap/duplicate')
    result['jo_all_pages_reviewed']=read_pages==list(range(1,266))
    result['jo_extraction_holds_remain']=any(l['open_items'] for l in ledgers)
    result['jo_whole_source_complete_definition']='모든 문법 구조화·분석 보류까지 해소되었음. 전체 쪽 읽기·분류 완료는 jo_all_pages_reviewed로 별도 표시.'
    if check_receipt:
        receipt=json.loads((HERE/'background_run/JO2018.receipt.json').read_text())
        validate_receipt(receipt,jo)
        for name,mutate in [
            ('missing last page',lambda d:d['pages'].pop()),
            ('false context instead of held',lambda d:d['pages'][226].update(status='context_only')),
            ('wrong count',lambda d:d.update(claim_count=d['claim_count']+1)),
            ('hidden holds',lambda d:d.update(status='extracted_draft')),
            ('missing bundle',lambda d:d['bundles'].pop()),
        ]:
            changed=copy.deepcopy(receipt);mutate(changed)
            try:validate_receipt(changed,jo)
            except ValueError:rejected=True
            else:rejected=False
            check('receipt '+name+' rejected',rejected)
        result['jo_receipt_checked']=True
    discrepancies=[]
    for ledger in ledgers:
        for table in ledger['source_context'].values():
            if not isinstance(table,dict) or table.get('kind')!='source_frequency_context_not_generation':continue
            for row in table['rows']:
                observed_sum=sum(v for v in row['counts'] if v is not None)
                for field in ['printed_total','printed_subtotal']:
                    if field in row and observed_sum!=row[field]:
                        discrepancies.append(dict(page=table['page'],ending=row['ending'],field=field,printed=row[field],sum_of_displayed_numbers=observed_sum,action='preserved_source_context_not_generation'))
    result['jo_frequency_discrepancies']=discrepancies
    result.update(jo_claim_count=sum(len(d['claims']) for _,d in jo),jo_checks=checks,jo_held_claim_count=sum(a['content']['operational_status']=='held' for _,d in jo for c in d['claims'] for a in c['assertions']),jo_open_issue_count=sum(len(l['open_items']) for l in ledgers),jo_last_processed_page=max(read_pages),jo_total_pages=265,jo_whole_source_complete=False,nodes=len(graph.nodes),edges=len(graph.edges))
    payload=dict(format_version='v3-draft-graph.1',status='draft_not_operational',bundles=[dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p,_ in loaded],nodes=list(graph.nodes.values()),edges=graph.edges,validation=result)
    if do_export:export_graph_delta(HERE/'current_kg.graph.json',payload)
    if check_saved:
        saved=json.loads((HERE/'current_kg.graph.json').read_text())
        for k in ['bundles','nodes','edges']:require(saved[k]==payload[k],'JO all-bundle reconstruction '+k)
        result['saved_graph_reconstructed']=True
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--export',action='store_true');parser.add_argument('--check-saved',action='store_true');parser.add_argument('--check-receipt',action='store_true');args=parser.parse_args()
    print(json.dumps(run(args.export,args.check_saved,args.check_receipt),ensure_ascii=False,indent=2))

"""NAMU20260901 source/coverage audit and deterministic grammar relations.

Only saved v3 bundles and the registered local PDF are inputs. Ending inventory
cells are schemas, never expanded into invented surface inflections. Q/A cells
whose reading order was broken by pdftotext were checked on PDF 27 visually.
"""
import argparse
import copy
import hashlib
import json
import re
import subprocess
from check_all_v3 import HERE, ROOT, audit, export, read_bundles, require

SID = 'NAMU20260901'


def read_overview():
    return [(p, json.loads(p.read_text())) for p in sorted(HERE.glob('namu_overview_batch_*_p*.json'))
            if not p.name.endswith('.coverage.json')]


def normalize(text):
    return re.sub(r'\s+', '', text)


def validate_content(loaded):
    for path, data in loaded:
        ev = {e['id']: e for e in data['evidence']}
        entities = {e['id']: e for e in data['entities']}
        ledger = json.loads(path.with_suffix('.coverage.json').read_text())
        require(ledger['audit']['text_read'] and ledger['audit']['pdftotext_layout'], 'reading audit missing')
        require([p['page'] for p in ledger['page_dispositions']] == ledger['body_pages'], 'coverage body pages')
        for c in data['claims']:
            require(c['id'].startswith(SID+'-B'), 'overview ID namespace')
            text = normalize(''.join(ev[e]['excerpt'] for e in c['evidence_refs']))
            for a in c['assertions']:
                co = a['content']
                require(all(co.get(k) for k in ['source_analysis','extractor_interpretation','generation_policy']),
                        'source / extraction / policy separation missing')
                require(co.get('operational_status') in {'held','draft_not_approved'}, 'unapproved status')
                for entry in co.get('entries', []):
                    require(entry.get('usage_ref') in entities and entities[entry['usage_ref']]['type']=='Usage',
                            'entry usage reference')
                    require(entry.get('source_expression') and entry.get('forms'), 'empty entry')
                    require(all(isinstance(f,str) and f and normalize(f) in text for f in entry['forms']),
                            'entry form absent from evidence: '+c['id'])
                for row in co.get('paradigm', []):
                    require(normalize(row['lemma']) in text and
                            all(normalize(f) in text for cell in row['forms'] for f in cell),
                            'paradigm source form absent')
                table = co.get('ending_inventory_table')
                if table:
                    require(table['headers'] and len(set(table['headers']))==len(table['headers']), 'inventory headers')
                    require(table['interpretation'] and table['rows'], 'inventory interpretation')
                    require(set(ev[c['evidence_refs'][0]]['pdf_pages']) <= {3,4}, 'inventory source pages')
                    require({3,4} <= set(ledger['audit']['pdf_pages_visually_checked']), 'inventory visual check missing')
                    for row in table['rows']:
                        require(row['usage_ref'] in entities and entities[row['usage_ref']]['type']=='Usage', 'table usage')
                        require(row['speech_act'] and len(row['cells'])==len(table['headers']), 'inventory width')
                        require(all(isinstance(cell,str) and cell for cell in row['cells']), 'inventory empty cell')
                decision = co.get('decision_table')
                if decision:
                    require(27 in ledger['audit']['pdf_pages_visually_checked'], 'Q/A visual check missing')
                    expected = [('체언','판정','-가','이게 그거가','응/아니'),
                                ('체언','설명','-고','왜 그거고','왜냐하면...(설명)'),
                                ('용언','판정','-나','오늘 머 하나','응/아니'),
                                ('용언','설명','-노','오늘 머 하노','오늘은...(설명)')]
                    require([tuple(r[k] for k in ['target_class','question_function','ending','source_question','source_answer'])
                             for r in decision] == expected, 'visually transcribed Q/A cells changed')


def extend_graph(graph, loaded):
    validate_content(loaded)
    counts = dict(ending_inventory_cells=0, ending_schemas=0, empty_inventory_cells=0,
                  copied_inventory_cells=0, question_combinations=0, paradigm_surface_forms=0,
                  held_edges_demoted=0)
    # Preserve existing source snapshots and their historical graph semantics.
    # In this source, held material can only be recorded, never queried as a candidate.
    for e in graph.edges:
        if e['source'].startswith(SID+'-') and e['relation'] in {'lists_candidate','realizes_as'}:
            if graph.nodes[e['source']]['properties'].get('operational_status')=='held':
                e['relation']='records_form'; counts['held_edges_demoted']+=1

    def node(id_, type_, **properties):
        require(id_ not in graph.nodes, 'overview derived ID collision')
        graph.nodes[id_]=dict(id=id_,type=type_,properties=properties)

    def edge(source,relation,target,**properties):
        graph.edges.append(dict(source=source,relation=relation,target=target,properties=properties))

    def scope(key,c,a):
        edge(key,'scoped_by',c['id']); edge(key,'derived_from',a['id'])
        if a['condition'] is not None: edge(key,'condition',a['id']+'.condition')

    for _, data in loaded:
        for c in data['claims']:
            for a in c['assertions']:
                co=a['content']; status=co['operational_status']
                # The generic builder already creates Usage -> cell -> Form.
                # Link actual participation of the named ending/particle as well.
                for ri,row in enumerate(co.get('paradigm',[])):
                    for ci,header in enumerate(co['headers']):
                        cell=a['id']+f'.table.{ri}.{ci}'; ending=cell+'.ending'
                        node(ending,'Form',text=header,layer='source_particle_or_ending',evidence_refs=c['evidence_refs'])
                        edge(cell,'combines_with',ending)
                        if a['condition'] is not None:edge(cell,'condition',a['id']+'.condition')
                        counts['paradigm_surface_forms']+=len(row['forms'][ci])
                # Inventory entries keep their original usage label and claim scope.
                for ei,entry in enumerate(co.get('entries',[])):
                    key=a['id']+f'.inventory.{ei}'
                    if a['condition'] is not None:edge(key,'condition',a['id']+'.condition')
                table=co.get('ending_inventory_table')
                if table:
                    for ri,row in enumerate(table['rows']):
                        for ci,(header,cell) in enumerate(zip(table['headers'],row['cells'])):
                            key=a['id']+f'.ending_table.{ri}.{ci}'
                            node(key,'Construction',speech_act=row['speech_act'],speech_level=header,
                                 source_cell=cell,claim_ref=c['id'],evidence_refs=c['evidence_refs'],
                                 operational_status=status,not_surface_inflection=True)
                            edge(row['usage_ref'],'participates_in',key);scope(key,c,a)
                            counts['ending_inventory_cells']+=1
                            if cell=='(없음)':
                                graph.nodes[key]['properties']['source_absent']=True
                                counts['empty_inventory_cells']+=1
                            elif cell=='명령과 동일':
                                command_row=next(i for i,r in enumerate(table['rows']) if r['speech_act']=='명령')
                                edge(key,'same_inventory_as',a['id']+f'.ending_table.{command_row}.{ci}',
                                     basis='source_explicit_cell_reference')
                                counts['copied_inventory_cells']+=1
                            else:
                                fid=key+'.schema'
                                node(fid,'Form',text=cell,layer='ending_inventory_schema',
                                     operational_status=status,orthographic_output_approved=False)
                                edge(key,'records_ending_schema',fid,not_surface_inflection=True)
                                counts['ending_schemas']+=1
                for i,row in enumerate(co.get('decision_table',[])):
                    key=a['id']+f'.question.{i}'; uid=key+'.usage';ending=key+'.ending'
                    node(uid,'Usage',target_class=row['target_class'],question_function=row['question_function'])
                    node(key,'Construction',source_question=row['source_question'],source_answer=row['source_answer'],
                         operational_status=status,claim_ref=c['id'],regional_caveat=co['regional_caveat'],
                         evidence_refs=c['evidence_refs'])
                    node(ending,'Form',text=row['ending'],layer='ending_schema',operational_status=status)
                    edge(uid,'participates_in',key);scope(key,c,a);edge(key,'combines_with',ending)
                    # Two independent conditions; interrogative spelling is not the criterion.
                    cond=key+'.condition';node(cond,'Condition',op='all');edge(key,'condition',cond)
                    for j,(feature,value) in enumerate([('target_class',row['target_class']),('question_function',row['question_function'])]):
                        atom=cond+f'.{j}';node(atom,'Condition',op='eq',feature=feature,value=value)
                        edge(atom,'evaluates',uid);edge(cond,'operand',atom,index=j)
                    fid=key+'.example';node(fid,'Form',text=row['source_question'],layer='whole_source_question',
                                          operational_status=status)
                    edge(key,'exemplified_by',fid,not_unconditional_substitution=True)
                    counts['question_combinations']+=1
    require(all(e['source'] in graph.nodes and e['target'] in graph.nodes for e in graph.edges),'dangling overview edge')
    return counts


def run(export_graph=False,check_receipt=False):
    from check_phonology import read_phonology, extend_graph as extend_phonology
    loaded=read_overview();require(loaded,'no overview bundles')
    honor=[(p,json.loads(p.read_text())) for p in sorted(HERE.glob('namu_honorifics_batch_*_p*.json'))
           if not p.name.endswith('.coverage.json')]
    phonology=read_phonology()
    from check_ryu2014 import read_ryu, extend_graph as extend_ryu
    ryu=read_ryu()
    from check_jo2018 import read_jo, extend_graph as extend_jo
    jo=read_jo()
    all_loaded=read_bundles()+honor+phonology+loaded+ryu+jo
    # Ensure future bundles cannot be silently omitted from an "all bundle" export.
    discovered={p for p in HERE.glob('*.json') if not p.name.endswith('.coverage.json')
                and set(json.loads(p.read_text())) >= {'format_version','entities','evidence','claims','policies'}}
    require(discovered=={p for p,_ in all_loaded},'unhandled saved bundle in all-source export')
    schema=json.loads((HERE/'bundle.schema.json').read_text());registry=json.loads((HERE.parent/'source_registry.json').read_text())
    merged,graph,result=audit(all_loaded,registry,schema)
    result['phonology_counts']=extend_phonology(graph,phonology)
    result['overview_counts']=extend_graph(graph,loaded)
    if ryu:result['ryu_counts']=extend_ryu(graph,ryu)
    if jo:result['jo_counts']=extend_jo(graph,jo)
    source=next(s for s in registry['sources'] if s['source_id']==SID)
    require(hashlib.sha256((ROOT/source['file']['path']).read_bytes()).hexdigest()==source['file']['sha256'],'overview PDF changed')
    pages=subprocess.run(['pdftotext','-layout',str(ROOT/source['file']['path']),'-'],text=True,capture_output=True,check=True).stdout.split('\f')
    require(len(pages)==56 and not pages[-1].strip(),'overview PDF page count')
    claims={c['id']:c for _,d in loaded for c in d['claims']};evidence={e['id']:e for _,d in loaded for e in d['evidence']}
    for e in evidence.values():
        text=normalize(''.join(pages[p-1] for p in e['pdf_pages']))
        require(all(normalize(s) in text for s in e['excerpt'].split('\n[…]\n')),'excerpt absent: '+e['id'])
    ledgers=[json.loads(p.with_suffix('.coverage.json').read_text()) for p,_ in loaded]
    dispositions=[page for ledger in ledgers for page in ledger['page_dispositions']]
    require([p['page'] for p in dispositions]==list(range(1,56)),'whole-source coverage missing/duplicate')
    checks=[]
    def check(name,ok):require(ok,name);checks.append(name)
    cid=lambda b,c:SID+f'-B{b:03}-C{c:03}'
    check('50 inventory cells retain 5 absent and 2 command references',
          result['overview_counts']['ending_inventory_cells']==50 and
          result['overview_counts']['empty_inventory_cells']==5 and
          result['overview_counts']['copied_inventory_cells']==2)
    check('southern 하소 의문 keeps eastern qualifier opaque',
          graph.nodes[cid(1,1)+'.a.ending_table.1.2']['properties']['source_cell']=='-요/-소, -(느)ㄴ교(동부)')
    check('northern 하게 statement stays in its own column',
          graph.nodes[cid(1,7)+'.a.ending_table.0.3']['properties']['source_cell']=='-(으)이, -네, -(이)ㄷ세')
    check('held overview output cannot be a candidate edge',not any(
          e['source'].startswith(SID+'-') and e['relation'] in {'lists_candidate','realizes_as'} and
          graph.nodes[e['source']]['properties'].get('operational_status')=='held' for e in graph.edges))
    for i,(lemma,form) in enumerate([('정낭','정나아'),('방','바아'),('반티이(반팅이)','반타아'),('양페이(양펜이)','양파아'),('구디이(구딩이)','구다아')]):
        key=cid(5,7)+f'.a.table.{i}.0'
        check('Pohang explicit inflection '+lemma,
              [graph.nodes[f]['properties']['text'] for f in graph.neighbors(key,'realizes_as')]==[form] and
              graph.nodes[graph.neighbors(key,'combines_with')[0]]['properties']['text']=='에')
    key=cid(6,6)+'.a.question.2';target=key+'.usage'
    check('머 spelling is not sufficient for explanation question',
          graph.nodes[key]['properties']['source_question']=='오늘 머 하나' and
          [graph.evaluate(key+'.condition',{target:dict(target_class='용언',question_function=v)})
           for v in ['판정','설명',None]]==[True,False,None])
    check('wrong predicate type rejects nominal question combination',
          graph.evaluate(cid(6,6)+'.a.question.0.condition',
            {cid(6,6)+'.a.question.0.usage':dict(target_class='용언',question_function='판정')}) is False)
    check('translation X is not a dialect grammaticality X',
          claims[cid(4,2)]['assertions'][0]['content']['judgment_target']=='translation_not_dialect_grammaticality' and
          len(claims[cid(4,2)]['assertions'][0]['content']['pairs'])==10)
    check('copula preending switch retains 시 counterexample',
          claims[cid(6,8)]['assertions'][0]['content']['switch_preendings']==['-었-','-겠-','-더-'] and
          claims[cid(6,8)]['assertions'][0]['content']['not_switching_example']=='사람이시가?')
    check('copula switching requires a listed preending and matching predicate',
          [graph.evaluate(cid(6,8)+'.switch.condition',
             {cid(6,8)+'.usage':dict(predicate_lemma='-이다',preceding_preending=v)})
           for v in ['-었-','-겠-','-더-','-시-',None]] == [True,True,True,False,None])
    check('rhetorical exclamation preserves both situation alternatives',
          [graph.evaluate(cid(6,10)+'.a.condition',
             {cid(6,10)+'.usage':dict(sentence_type='수사의문문',exclamatory_interrogative_omitted=True,
                                    discourse_situation=v)})
           for v in ['뜻밖의 일에 감탄','상대 행동 이해 불가','평범한 서술',None]] == [True,True,False,None])
    check('nasal insertion inconsistency is held rather than silently generalized',
          claims[cid(2,18)]['assertions'][0]['content']['operational_status']=='held' and
          [graph.evaluate(cid(2,18)+'.a.condition',
             {cid(2,18)+'.usage':dict(preceding_coda=v,following_onset='ㅣ계 이중모음의 ㅇ')})
           for v in ['ㄴ','ㄹ','ㅂ',None]] == [True,True,False,None])
    check('nickname generation needs two syllables and affectionate address',
          [graph.evaluate(cid(8,1)+'.a.condition',{cid(8,1)+'.usage':dict(name_length_syllables=n,address_function='애칭')})
           for n in [2,3,None]]==[True,False,None])
    check('declarative modesty needs falling contour',
          [graph.evaluate(cid(4,5)+'.a.condition',{cid(4,5)+'.usage':dict(sentence_type='평서문',terminal_contour=v)})
           for v in ['하강','상승',None]]==[True,False,None])
    for name, mutate in [
        ('inventory width rejected',lambda d:d[0][1]['claims'][0]['assertions'][0]['content']['ending_inventory_table']['rows'][0]['cells'].pop()),
        ('missing inventory usage rejected',lambda d:d[0][1]['claims'][0]['assertions'][0]['content']['ending_inventory_table']['rows'][0].update(usage_ref='absent')),
        ('source-absent realization rejected',lambda d:d[4][1]['claims'][6]['assertions'][0]['content']['paradigm'][0]['forms'][0].append('만든형태')),
        ('Q/A inversion rejected',lambda d:d[5][1]['claims'][5]['assertions'][0]['content']['decision_table'][2].update(ending='-노'))]:
        changed=copy.deepcopy(loaded);mutate(changed)
        try:validate_content(changed)
        except (ValueError,KeyError,TypeError):rejected=True
        else:rejected=False
        check(name,rejected)
    result.update(nodes=len(graph.nodes),edges=len(graph.edges),overview_claim_count=len(claims),
                  overview_held_claim_count=sum(c['assertions'][0]['content']['operational_status']=='held' for c in claims.values()),
                  overview_checks=checks,overview_pdf_sha256=source['file']['sha256'])
    payload=dict(format_version='v3-draft-graph.1',status='draft_not_operational',
                 bundles=[dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p,_ in all_loaded],
                 nodes=list(graph.nodes.values()),edges=graph.edges,validation=result)
    if export_graph:export(HERE/'current_kg.graph.json',payload)
    if check_receipt:
        receipt=json.loads((HERE/'background_run'/f'{SID}.receipt.json').read_text())
        require(receipt['source_id']==SID and receipt['status']=='extracted_with_holds','receipt identity')
        require(receipt['claim_count']==len(claims),'receipt count')
        require(receipt['bundles']==[str(p.relative_to(ROOT)) for p,_ in loaded],'receipt bundles')
        require([p['page'] for p in receipt['pages']]==list(range(1,56)),'receipt pages')
        seen=set()
        for page, disposition in zip(receipt['pages'],dispositions):
            expected=[cid_ for cid_,c in claims.items() if any(page['page'] in evidence[e]['pdf_pages'] for e in c['evidence_refs'])]
            require(page['claim_ids']==expected,'page claim/evidence completeness')
            require(page['status']==disposition['status'] and page['reason']==disposition['reason'],'page disposition mismatch')
            require(page['status'] in {'extracted','context_only','held'} and page['reason'],'page disposition')
            if page['status']=='extracted':require(expected,'empty extracted page')
            if page['status']=='context_only':require(not expected,'context page has unreported extraction')
            seen.update(expected)
        require(seen==set(claims),'receipt omitted claim')
        require(receipt['validation']['passed'] and receipt['validation']['commands'],'receipt validation')
        expected_issues=[f"{i['location']}: {i['issue']}" for ledger in ledgers for i in ledger['open_items']]
        require(receipt['open_issues']==expected_issues,'receipt omits or changes holds')
        saved=json.loads((HERE/'current_kg.graph.json').read_text())
        for key in ['bundles','nodes','edges']:require(saved[key]==payload[key],'saved graph reconstruction: '+key)
        result['receipt_and_saved_graph']='passed'
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--export',action='store_true');parser.add_argument('--check-receipt',action='store_true')
    args=parser.parse_args();print(json.dumps(run(args.export,args.check_receipt),ensure_ascii=False,indent=2))

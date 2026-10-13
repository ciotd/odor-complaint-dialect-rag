"""Validate source-grounded facts and compile a separate, provenance-bearing KG."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re

import jsonschema

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized(text):
    return re.sub(r'\s+', '', text)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')


def validate_fact(fact, source, pages):
    if not fact['id'].startswith(source+':v2:'):
        raise ValueError('Fact ID must be source-scoped: '+fact['id'])
    if fact['claim_status']=='negative_example' and fact['usability']=='candidate':
        raise ValueError('Negative examples cannot become positive candidates')
    for c in fact['conditions']:
        if c['field']=='meaning':
            raise ValueError('Opaque exact-match meaning conditions are not supported')
        if c['op'] in {'in','not_in'} and (not isinstance(c['value'],list) or not c['value']):
            raise ValueError('Membership conditions require nonempty lists')
        if c['op']=='exists' and not isinstance(c['value'],bool):
            raise ValueError('Existence condition requires a boolean')
    if fact['type']=='inflection':
        for c in fact['conditions']:
            if c['field'] in {'lemma','host_form'} and c['owner']=='input' and fact['source_pattern']['domain']=='dialect':
                raise ValueError('Dialect inflection must inspect selected candidate, not require a dialect input')
    for e in fact['evidence']:
        key=(source,e['pdf_page'])
        if key not in pages:
            raise ValueError('Unknown evidence page: '+str(key))
        if normalized(e['quote']) not in normalized(pages[key]['text']):
            raise ValueError(f"Evidence does not occur in source: {fact['id']} p{e['pdf_page']}: {e['quote']}")


def compile_graph(facts, registry, pages, reviews):
    nodes, edges = {}, []
    def node(nid, kind, properties):
        if nid in nodes:
            return
        nodes[nid]={'id':nid,'type':kind,'properties':properties}
    def edge(source, kind, target, **props):
        edges.append({'source':source,'type':kind,'target':target,'properties':props})
    for s in registry['sources']:
        node('source:'+s['source_id'],'Source',s)
        for dependency in s.get('source_dependencies',[]):
            edge('source:'+s['source_id'],'document_dependency',
                 'source:'+dependency['related_source_id'],**dependency)
    for (sid,pno),page in sorted(pages.items()):
        pid=f'source:{sid}:p{pno}'
        review=reviews.get((sid,pno))
        node(pid,'SourcePage',{'source_id':sid,'pdf_page':pno,'text_sha256':page['text_sha256'],
                              'review':review,'review_status':'reviewed' if review else 'pending'})
        edge(pid,'part_of','source:'+sid)
    predicates={'lexical_mapping':'lexical_correspondence','inflection':'attested_or_described_inflection',
                'ending':'ending_realization','construction':'construction_correspondence',
                'particle':'particle_correspondence','phonology':'phonological_correspondence',
                'usage':'describes_usage','constraint':'restricts','context':'documents'}
    for f in facts:
        fid=f['id'];sid=f['source_id']
        node(fid,'KnowledgeStatement',{k:v for k,v in f.items() if k not in ['source_pattern','target_pattern','evidence']})
        for role in ['source','target']:
            eid=fid+':'+role
            node(eid,'ExpressionUse',{**f[role+'_pattern'],'source_id':sid,'scope':f['scope']})
            edge(fid,role+'_expression',eid)
        edge(fid+':source',predicates[f['type']],fid+':target',statement_id=fid,
             claim_status=f['claim_status'],usability=f['usability'])
        for n,c in enumerate(f['conditions'],1):
            cid=fid+':condition:'+str(n);node(cid,'Condition',c);edge(fid,'requires',cid)
        for n,c in enumerate(f['constraints'],1):
            cid=fid+':constraint:'+str(n);node(cid,'Constraint',c);edge(fid,'has_constraint',cid)
        for function in f['functions']:
            cid='function:'+function;node(cid,'Function',{'name':function});edge(fid,'describes_function',cid)
        for n,e in enumerate(f['evidence'],1):
            eid=fid+':evidence:'+str(n);node(eid,'Evidence',e)
            edge(fid,'supported_by',eid);edge(eid,'located_on',f'source:{sid}:p{e["pdf_page"]}')
    # This is an explicit structural candidate link, not a proof of sense equivalence.
    # Source/region/sense conditions still have to be checked at query time.
    inflections={}
    for f in facts:
        if f['type']=='inflection':
            p=f['source_pattern'];lemma=p['lemma'] or p['text']
            inflections.setdefault(lemma,[]).append(f)
    for f in facts:
        if f['type']!='lexical_mapping':
            continue
        p=f['target_pattern'];lemma=p['lemma'] or p['text']
        for form in inflections.get(lemma,[]):
            edge(f['id'],'candidate_has_inflection',form['id'],
                 match='target_lemma_equals_inflection_lemma',requires_scope_and_sense_review=True)
    return {'version':'2.0-draft','nodes':list(nodes.values()),'edges':edges,
            'policy':'Expression identities remain source/statement scoped; surface equality is not semantic equivalence.'}


def build(require_full=False):
    registry=read(BASE/'source_registry.json')
    pages={(p['source_id'],p['pdf_page']):p for p in
           (json.loads(line) for line in (BASE/'local/pages.jsonl').read_text().splitlines())}
    expected={(s['source_id'],n) for s in registry['sources'] for n in range(1,s['file']['pages']+1)}
    if set(pages)!=expected:
        raise ValueError('Extracted page inventory differs from source registry')
    for p in pages.values():
        if hashlib.sha256(p['text'].encode()).hexdigest()!=p['text_sha256']:
            raise ValueError('Extracted text hash mismatch')
    for s in registry['sources']:
        if digest(ROOT/s['file']['path'])!=s['file']['sha256']:
            raise ValueError('Source PDF changed: '+s['source_id'])
    for item in read(BASE/'reports/legacy_baseline.json')['protected_files']:
        if digest(ROOT/item['path'])!=item['sha256']:
            raise ValueError('Legacy file changed: '+item['path'])
    schema=read(BASE/'fact.schema.json');facts=[];ids=set()
    for path in sorted((BASE/'authored').glob('*.json')):
        doc=read(path);jsonschema.validate(doc,schema)
        for fact in doc['facts']:
            validate_fact(fact,doc['source_id'],pages)
            if fact['id'] in ids:
                raise ValueError('Duplicate fact: '+fact['id'])
            ids.add(fact['id']);facts.append({**fact,'source_id':doc['source_id'],'authoring_file':str(path.relative_to(BASE))})
    reviews={};fact_index={f['id']:f for f in facts}
    for path in sorted((BASE/'reviews').glob('*.json')):
        doc=read(path)
        for r in doc['pages']:
            key=(doc['source_id'],r['pdf_page'])
            if key in reviews or key not in pages:
                raise ValueError('Duplicate/unknown reviewed page: '+str(key))
            if r['disposition'] not in {'knowledge','context','front_matter','bibliography','blank','mixed','unreadable'}:
                raise ValueError('Invalid review disposition')
            if not r['note'].strip() or not isinstance(r['gaps'],list):
                raise ValueError('Review note and explicit gap list required')
            if set(r['fact_ids'])-ids:
                raise ValueError('Unknown fact in review: '+str(key))
            for fid in r['fact_ids']:
                f=fact_index[fid]
                if f['source_id']!=key[0] or key[1] not in {e['pdf_page'] for e in f['evidence']}:
                    raise ValueError('Reviewed fact is not supported on reviewed page: '+fid)
            if r['disposition']=='knowledge' and not r['fact_ids'] and not r['gaps']:
                raise ValueError('Knowledge page needs facts or explicit gaps: '+str(key))
            reviews[key]=r
    pending=sorted(set(pages)-set(reviews))
    if require_full and pending:
        raise ValueError(f'{len(pending)} source pages have not been reviewed')
    graph=compile_graph(facts,registry,pages,reviews)
    (BASE/'facts.jsonl').write_text(''.join(json.dumps(f,ensure_ascii=False)+'\n' for f in facts))
    save(BASE/'graph.json',graph)
    bysource=[]
    for s in registry['sources']:
        sid=s['source_id'];rs=[r for (source,_),r in reviews.items() if source==sid]
        bysource.append({'source_id':sid,'pages':s['file']['pages'],'reviewed_pages':len(rs),
                         'facts':sum(f['source_id']==sid for f in facts),'gap_pages':sum(bool(r['gaps']) for r in rs)})
    summary={'status':'full_source_draft' if not pending else 'in_progress',
             'source_pages':len(pages),'reviewed_pages':len(reviews),'pending_pages':len(pending),
             'facts':len(facts),'fact_types':dict(Counter(f['type'] for f in facts)),
             'claim_statuses':dict(Counter(f['claim_status'] for f in facts)),
             'nodes':len(graph['nodes']),'edges':len(graph['edges']),'sources':bysource,
             'legacy_preservation':'all hashed legacy files unchanged',
             'semantic_completeness':'not implied by page coverage; inspect review notes and gaps',
             'translation_quality':'not evaluated','authoring_model':'gpt-6-astra',
             'facts_sha256':digest(BASE/'facts.jsonl'),'graph_sha256':digest(BASE/'graph.json')}
    save(BASE/'reports/build_summary.json',summary)
    with (BASE/'reports/page_coverage.tsv').open('w') as stream:
        writer=csv.writer(stream,delimiter='\t');writer.writerow(['source_id','pdf_page','status','disposition','facts','gaps','note'])
        for (sid,n),p in sorted(pages.items()):
            r=reviews.get((sid,n),{})
            writer.writerow([sid,n,'reviewed' if r else 'pending',r.get('disposition',''),','.join(r.get('fact_ids',[])),
                             json.dumps(r.get('gaps',[]),ensure_ascii=False),r.get('note','')])
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--require-full',action='store_true')
    build(parser.parse_args().require_full)

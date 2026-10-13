"""Add a separate KG v2 snapshot to local Neo4j; render queried data to PNG/SVG.

No existing graph is deleted. Figures are Graphviz renderings of verified Neo4j
query results, not screenshots of the Neo4j Browser UI.
"""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import textwrap

BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE.parent/'current_kg/grammar'))
from neo4j_view import request

OUT=BASE/'reports/neo4j'
COLORS={'Source':'#d5e9f9','SourcePage':'#e5f2ff','Evidence':'#fff0c2',
        'KnowledgeStatement':'#d9ecff','ExpressionUse':'#d9f2e6','Condition':'#f4ddea',
        'Constraint':'#fae2d7','Function':'#e7dff7'}
NAMES={'Source':'문헌','SourcePage':'원문 페이지','Evidence':'인용 근거',
       'KnowledgeStatement':'지식 진술','ExpressionUse':'출처별 표현',
       'Condition':'적용 조건','Constraint':'제약·불확실성','Function':'문법 기능'}


def save(name,data):
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')


def load():
    raw=(BASE/'graph.json').read_bytes();graph=json.loads(raw);snap=hashlib.sha256(raw).hexdigest()
    request('CREATE CONSTRAINT kg_v2_snapshot_id IF NOT EXISTS FOR (n:KGv2Node) REQUIRE (n.snapshot,n.id) IS UNIQUE')
    grouped=defaultdict(list)
    for n in graph['nodes']:
        assert re.fullmatch('[A-Za-z_][A-Za-z0-9_]*',n['type'])
        p=n['properties'];label=p.get('text',p.get('title',p.get('name',n['id'])))
        grouped[n['type']].append({'id':n['id'],'snapshot':snap,'kg_type':n['type'],
            'label':str(label),'properties_json':json.dumps(p,ensure_ascii=False,sort_keys=True)})
    for kind,rows in grouped.items():
        for i in range(0,len(rows),400):
            request(f'UNWIND $rows AS row MERGE (n:KGv2Node:`{kind}` {{snapshot:row.snapshot,id:row.id}}) SET n += row',{'rows':rows[i:i+400]})
        print('nodes',kind,len(rows),flush=True)
    grouped=defaultdict(list)
    for i,e in enumerate(graph['edges']):
        assert re.fullmatch('[A-Za-z_][A-Za-z0-9_]*',e['type'])
        grouped[e['type']].append({'id':f'edge:{i}','source':e['source'],'target':e['target'],
            'properties_json':json.dumps(e.get('properties',{}),ensure_ascii=False,sort_keys=True)})
    for kind,rows in grouped.items():
        for i in range(0,len(rows),400):
            request(f'''UNWIND $rows AS row
MATCH (a:KGv2Node {{snapshot:$s,id:row.source}}),(b:KGv2Node {{snapshot:$s,id:row.target}})
MERGE (a)-[r:`{kind}` {{snapshot:$s,id:row.id}}]->(b) SET r.properties_json=row.properties_json''',{'rows':rows[i:i+400],'s':snap})
        print('edges',kind,len(rows),flush=True)
    nr=request('MATCH (n:KGv2Node {snapshot:$s}) RETURN n.id,n.kg_type,n.properties_json',{'s':snap})
    er=request('MATCH (a:KGv2Node {snapshot:$s})-[r]->(b:KGv2Node {snapshot:$s}) RETURN r.id,a.id,type(r),b.id,r.properties_json',{'s':snap})
    actual_n={i:(t,json.loads(p)) for i,t,p in nr}
    actual_e={i:(a,t,b,json.loads(p)) for i,a,t,b,p in er}
    assert len(nr)==len(graph['nodes']) and actual_n=={n['id']:(n['type'],n['properties']) for n in graph['nodes']}
    assert len(er)==len(graph['edges']) and actual_e=={f'edge:{i}':(e['source'],e['type'],e['target'],e.get('properties',{})) for i,e in enumerate(graph['edges'])}
    save('verification.json',{'status':'exact_node_edge_property_roundtrip_passed','snapshot_sha256':snap,
        'nodes':len(nr),'edges':len(er),'neo4j_version':request('CALL dbms.components() YIELD versions RETURN versions')[0][0],
        'namespace':'KGv2Node; existing KGNode data preserved',
        'rendering':'PNG/SVG from verified Neo4j query rows using Graphviz; not Browser screenshots'})
    figures(snap,nr,er)


def dot_graph(name,title,nodes,edges):
    q=lambda x:json.dumps(str(x),ensure_ascii=False)
    lines=['digraph G {','rankdir=LR; bgcolor="white"; pad=0.4; nodesep=0.35; ranksep=0.8;',
      'graph [fontname="Noto Sans CJK KR",fontsize=20,labelloc=t,label='+q(title)+'];',
      'node [shape=box,style="rounded,filled",fontname="Noto Sans CJK KR",fontsize=12,margin="0.16,0.1",color="#7b8994"];',
      'edge [fontname="Noto Sans CJK KR",fontsize=9,color="#8796a5",arrowsize=0.65];']
    for nid,label,kind in nodes:
        lines.append(f'{q(nid)} [label={q(label)},fillcolor={q(COLORS[kind])}];')
    for a,label,b in edges:
        lines.append(f'{q(a)} -> {q(b)} [label={q(label)}];')
    lines.append('}');path=OUT/(name+'.dot');path.write_text('\n'.join(lines)+'\n')
    for fmt in ['png','svg']:
        subprocess.run(['dot','-T'+fmt,'-Gdpi=140',str(path),'-o',str(OUT/(name+'.'+fmt))],check=True)


def figures(snap,nr,er):
    types={i:t for i,t,p in nr};counts=Counter(types.values())
    rel=Counter((types[a],t,types[b]) for _,a,t,b,_ in er)
    grouped=defaultdict(list)
    for (a,t,b),n in sorted(rel.items()):grouped[a,b].append((t,n))
    edges=[]
    for (a,b),rows in grouped.items():
        label='\n'.join(t+f'  {n:,}' for t,n in rows)
        if a==b=='ExpressionUse':label=f'어휘·활용·어미 등 {len(rows)}종 대응\n'+f'{sum(n for t,n in rows):,}개 관계'
        edges.append((a,label,b))
    dot_graph('schema',f'KG v2 전체 구성 — Neo4j 조회 집계\n{len(nr):,}개 노드 · {len(er):,}개 관계 | 유형별 집계이며 실제 단일 노드가 아님',
              [(t,NAMES[t]+'\n'+t+f'\n{n:,}개',t) for t,n in counts.items()],edges)
    save('schema_counts.json',{'nodes':dict(counts),'edges':[{'from':a,'relation':t,'to':b,'count':n} for (a,t,b),n in rel.items()]})
    focus=['NAMU_GRAMMAR_20260908:v2:full:1057','NAMU_GRAMMAR_20260908:v2:full:0239']
    # Actual Neo4j subgraph query, bounded to two source-grounded statements and evidence locations.
    ids=request('''MATCH (f:KGv2Node {snapshot:$s}) WHERE f.id IN $focus
OPTIONAL MATCH (f)-[:source_expression|target_expression|requires|has_constraint|supported_by|describes_function]->(n:KGv2Node)
OPTIONAL MATCH (n)-[:located_on]->(p:KGv2Node)-[:part_of]->(src:KGv2Node)
RETURN collect(DISTINCT f.id)+collect(DISTINCT n.id)+collect(DISTINCT p.id)+collect(DISTINCT src.id)''',{'s':snap,'focus':focus})[0][0]
    ids=set(ids);nodes=[]
    for nid,kind,pj in nr:
        if nid not in ids:continue
        p=json.loads(pj)
        if kind=='KnowledgeStatement':label=('어휘 대응: 먹다 → 묵다' if nid==focus[0] else '활용: 묵다 + -고 → 묵고')+'\n'+nid.split(':v2:')[-1]
        elif kind=='ExpressionUse':label=p['text']+'\n'+p['domain']+' · '+nid.rsplit(':',1)[-1]
        elif kind=='Condition':label=f"{p['owner']}.{p['field']}\n{p['op']} {p['value']}"
        elif kind=='Evidence':label=f"원문 인용 · PDF {p['pdf_page']}쪽\n"+'\n'.join(textwrap.wrap(p['quote'].replace('\n',' ')[:65],24))+'…'
        elif kind=='SourcePage':label=f"문법 PDF {p['pdf_page']}쪽"
        elif kind=='Source':label='동남 방언 / 문법\n원문 문헌'
        else:label='\n'.join(textwrap.wrap(p.get('description',p.get('name',''))[:100],25))
        nodes.append((nid,label,kind))
    es=[(a,t,b) for _,a,t,b,_ in er if a in ids and b in ids]
    dot_graph('eating_path','먹다 → 묵다 → 묵고 — 실제 Neo4j 부분 그래프\n조건·원문 근거까지 표시 | 연결 자체가 적용 승인은 아님',nodes,es)
    save('eating_path.json',{'focus':focus,'nodes':[{'id':n,'label':l,'type':t} for n,l,t in nodes],
                             'edges':[{'source':a,'type':t,'target':b} for a,t,b in es]})
    (OUT/'inspection.cypher').write_text(f'''// Neo4j Browser: http://127.0.0.1:17474/browser/
:param snapshot => '{snap}';
// Actual lexical -> inflection statements and their source/target expressions.
MATCH (l:KGv2Node {{snapshot:$snapshot,id:'{focus[0]}'}})-[r:candidate_has_inflection]->(i:KGv2Node {{id:'{focus[1]}'}})
OPTIONAL MATCH (l)-[a:source_expression|target_expression|requires|supported_by]->(x:KGv2Node)
OPTIONAL MATCH (i)-[b:source_expression|target_expression|requires|supported_by]->(y:KGv2Node)
RETURN l,r,i,a,x,b,y;

// Other lexical/inflection paths (bounded to keep Browser readable).
MATCH (l:KGv2Node {{snapshot:$snapshot}})-[r:candidate_has_inflection]->(i:KGv2Node {{snapshot:$snapshot}})
RETURN l,r,i LIMIT 40;
''')
    print('PNG/SVG saved:',OUT,flush=True)


if __name__=='__main__':load()

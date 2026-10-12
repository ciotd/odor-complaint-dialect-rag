"""Local Neo4j mirror of the authored JSON graph; no grammar or retrieval policy edits.

Install/start/load are explicit commands. Credentials and DB files remain under
current_kg/.runtime (gitignored); inspection Cypher and verification are public.
"""
import argparse
import base64
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import tarfile
import urllib.request

BASE = Path(__file__).resolve().parent
RUNTIME = BASE.parent / '.runtime'
VERSION = '5.26.31'
SHA256 = 'f8fc23340561405f1ff10ca6ac2d317d095d3c74509a616883c45d7a61f5cfec'
DIST = f'neo4j-community-{VERSION}'
INSTALL = RUNTIME / DIST
AUTH = RUNTIME / 'neo4j-auth.json'
REPORTS = BASE.parent / 'experiments/reports/neo4j'
HTTP = 'http://127.0.0.1:17474'
BOLT = 'bolt://127.0.0.1:17687'


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def install():
    RUNTIME.mkdir(parents=True, exist_ok=True)
    archive = RUNTIME / (DIST + '-unix.tar.gz')
    url = 'https://dist.neo4j.org/' + archive.name
    if not archive.exists():
        print('Downloading official Neo4j distribution', flush=True)
        with urllib.request.urlopen(url, timeout=60) as src, archive.open('wb') as dst:
            while chunk := src.read(1024 * 1024):
                dst.write(chunk)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256:
        raise ValueError('Neo4j archive checksum mismatch; retained for inspection')
    if not INSTALL.exists():
        with tarfile.open(archive) as src:
            for member in src.getmembers():
                target = (RUNTIME / member.name).resolve()
                if not target.is_relative_to(RUNTIME.resolve()) or member.issym() or member.islnk():
                    raise ValueError('Unsafe archive path')
            src.extractall(RUNTIME, filter='data')
    if not AUTH.exists():
        auth = {'username':'neo4j','password':secrets.token_urlsafe(24),'http':HTTP,'bolt':BOLT}
        fd = os.open(AUTH, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd,'w') as f: json.dump(auth,f)
        result = subprocess.run([str(INSTALL/'bin/neo4j-admin'),'dbms','set-initial-password',auth['password']],
                                capture_output=True,text=True)
        if result.returncode: raise RuntimeError('Initial password setup failed; credentials retained locally')
    config = '\n'.join([
        'server.default_listen_address=127.0.0.1',
        'server.default_advertised_address=127.0.0.1',
        'server.http.enabled=true','server.http.listen_address=127.0.0.1:17474',
        'server.http.advertised_address=127.0.0.1:17474',
        'server.https.enabled=false','server.bolt.enabled=true',
        'server.bolt.listen_address=127.0.0.1:17687','server.bolt.advertised_address=127.0.0.1:17687',
        'server.memory.heap.initial_size=256m','server.memory.heap.max_size=512m',
        'server.memory.pagecache.size=256m','dbms.security.auth_enabled=true',
        'dbms.usage_report.enabled=false','',
    ])
    (INSTALL/'conf/neo4j.conf').write_text(config)
    save(RUNTIME/'installation.json',{'version':VERSION,'archive_sha256':SHA256,'download_url':url,
                                    'http':HTTP,'bolt':BOLT,'source_of_truth':'grammar/grammar.graph.json'})
    print('Installed Neo4j',VERSION,'with checksum verification; credentials:',AUTH)


def request(statement, parameters=None):
    auth = json.loads(AUTH.read_text())
    token = base64.b64encode((auth['username']+':'+auth['password']).encode()).decode()
    body = {'statements':[{'statement':statement,'parameters':parameters or {}}]}
    req = urllib.request.Request(HTTP+'/db/neo4j/tx/commit',data=json.dumps(body).encode(),
                                 headers={'Content-Type':'application/json','Authorization':'Basic '+token})
    with urllib.request.urlopen(req,timeout=60) as response: result = json.load(response)
    if result['errors']: raise RuntimeError(json.dumps(result['errors'],ensure_ascii=False))
    return [row['row'] for row in result['results'][0]['data']]


def properties(item, snapshot):
    # Keep exact nested properties for roundtrip; expose scalar fields for Browser.
    props = item.get('properties',{})
    flat = {k:v for k,v in props.items() if isinstance(v,(str,int,float,bool))}
    flat.update(id=item['id'],snapshot=snapshot,kg_type=item['type'],
                properties_json=json.dumps(props,ensure_ascii=False,sort_keys=True))
    if 'label' not in flat:
        flat['label']=str(props.get('text',props.get('name',item['id'])))
    return flat


def graph_data():
    raw = (BASE/'grammar.graph.json').read_bytes()
    graph=json.loads(raw); snapshot=hashlib.sha256(raw).hexdigest()
    for item in graph['nodes']+graph['edges']:
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',item['type']):
            raise ValueError('Unexpected graph type')
    return graph,snapshot


def queries(snapshot):
    # Browser :param commands, then run individual MATCH sections.
    return f'''// Existing JSON graph mirror. No vector index and no LLM-generated Cypher.
:param snapshot => '{snapshot}';
:param function_id => 'concept:CONTENT_QUESTION';
:param record_id => 'GYS-Y009';

// Node/relationship type counts (run separately).
MATCH (n:KGNode {{snapshot:$snapshot}}) RETURN n.kg_type AS type, count(*) AS count ORDER BY type;
MATCH (:KGNode {{snapshot:$snapshot}})-[r]->(:KGNode {{snapshot:$snapshot}})
RETURN type(r) AS type, count(*) AS count ORDER BY type;

// First-stage function candidates: same realizes edge set as Python, not final selection.
MATCH (u:ExpressionUse {{snapshot:$snapshot}})-[r:realizes]->(f:GrammarConcept {{snapshot:$snapshot,id:$function_id}})
RETURN u,r,f;

// Record -> statements -> their subjects, objects, conditions and source locations.
MATCH (k:KnowledgeRecord {{snapshot:$snapshot,id:$record_id}})-[c:contains_assertion]->(a:Assertion {{snapshot:$snapshot}})
OPTIONAL MATCH (a)-[r]->(n:KGNode {{snapshot:$snapshot}})
RETURN k,c,a,r,n LIMIT 120;

// Quotation/contraction relationships, independent of function entry.
MATCH (a:KGNode {{snapshot:$snapshot}})-[r]->(b:KGNode {{snapshot:$snapshot}})
WHERE type(r) IN ['contracts_to','shares_quotative_construction','combines_with']
RETURN a,r,b LIMIT 100;

// Verbatim source examples (distinct from author-created illustrative examples).
MATCH (k:KnowledgeRecord {{snapshot:$snapshot}})-[r:has_source_example]->(e:SourceExample {{snapshot:$snapshot}})
OPTIONAL MATCH (e)-[s:supported_at]->(p:SourceLocation {{snapshot:$snapshot}})
RETURN k,r,e,s,p;

// A missing function-entry edge is a reachability observation, not missing grammar.
MATCH (u:ExpressionUse {{snapshot:$snapshot}})
WHERE NOT (u)-[:realizes]->(:GrammarConcept {{snapshot:$snapshot}})
RETURN u LIMIT 100;
'''


def load_graph():
    graph,snapshot=graph_data()
    request('CREATE CONSTRAINT kg_snapshot_id IF NOT EXISTS FOR (n:KGNode) REQUIRE (n.snapshot,n.id) IS UNIQUE')
    groups=defaultdict(list)
    for n in graph['nodes']: groups[n['type']].append(properties(n,snapshot))
    for label,items in groups.items():
        for i in range(0,len(items),400):
            request(f'UNWIND $rows AS row MERGE (n:KGNode:`{label}` {{snapshot:row.snapshot,id:row.id}}) SET n += row',{'rows':items[i:i+400]})
    groups=defaultdict(list)
    for e in graph['edges']:
        groups[e['type']].append({'source':e['source'],'target':e['target'],'props':properties(e,snapshot)})
    for kind,items in groups.items():
        for i in range(0,len(items),400):
            request(f'''UNWIND $rows AS row
MATCH (a:KGNode {{snapshot:$snapshot,id:row.source}}),(b:KGNode {{snapshot:$snapshot,id:row.target}})
MERGE (a)-[r:`{kind}` {{snapshot:$snapshot,id:row.props.id}}]->(b) SET r += row.props''',
                    {'rows':items[i:i+400],'snapshot':snapshot})
    verify(graph,snapshot)


def verify(graph=None,snapshot=None):
    if graph is None:graph,snapshot=graph_data()
    nodes=request('MATCH (n:KGNode {snapshot:$snapshot}) RETURN n.id,n.kg_type,n.properties_json',{'snapshot':snapshot})
    edges=request('MATCH (a:KGNode {snapshot:$snapshot})-[r]->(b:KGNode {snapshot:$snapshot}) RETURN r.id,a.id,type(r),b.id,r.properties_json',{'snapshot':snapshot})
    expected_n={n['id']:(n['type'],n.get('properties',{})) for n in graph['nodes']}
    expected_e={e['id']:(e['source'],e['type'],e['target'],e.get('properties',{})) for e in graph['edges']}
    actual_n={nid:(kind,json.loads(p)) for nid,kind,p in nodes}
    actual_e={eid:(source,kind,target,json.loads(p)) for eid,source,kind,target,p in edges}
    if len(nodes)!=len(expected_n) or actual_n!=expected_n:raise ValueError('Node roundtrip mismatch')
    if len(edges)!=len(expected_e) or actual_e!=expected_e:raise ValueError('Edge roundtrip mismatch')
    functions=sorted({e['target'] for e in graph['edges'] if e['type']=='realizes'})
    matches=[]
    for function in functions:
        cypher=request('MATCH (:KGNode {snapshot:$snapshot})-[r:realizes]->(f:GrammarConcept {snapshot:$snapshot,id:$function}) RETURN r.id',
                       {'snapshot':snapshot,'function':function})
        expected=sorted(e['id'] for e in graph['edges'] if e['type']=='realizes' and e['target']==function)
        if sorted(x[0] for x in cypher)!=expected:raise ValueError('Function entry mismatch: '+function)
        matches.append({'function_id':function,'edges':len(expected),'equal':True})
    report={'status':'roundtrip_and_entry_queries_verified','neo4j_version':request('CALL dbms.components() YIELD versions RETURN versions')[0][0],
            'snapshot_sha256':snapshot,'nodes':len(nodes),'edges':len(edges),
            'node_types':dict(Counter(n['type'] for n in graph['nodes'])),
            'edge_types':dict(Counter(e['type'] for e in graph['edges'])),
            'function_entry_comparisons':matches,
            'limitations':['Storage and first-stage entry parity only; condition evaluation remains Python.',
                           'No new grammar validation, embedding search, or translation evaluation.',
                           'Graph connections displayed by Browser are not automatically execution traces.']}
    save(REPORTS/'verification.json',report)
    REPORTS.mkdir(parents=True,exist_ok=True)
    (REPORTS/'inspection.cypher').write_text(queries(snapshot))
    schema_figure(graph,snapshot)
    print(json.dumps({k:report[k] for k in ['status','neo4j_version','nodes','edges']},ensure_ascii=False))
    print('Function entry comparisons:',len(matches),'Browser:',HTTP+'/browser/')


def schema_figure(graph=None,snapshot=None):
    """All node types, selected relation families; counts are computed, not invented."""
    if graph is None:graph,snapshot=graph_data()
    types={n['id']:n['type'] for n in graph['nodes']}
    counts=Counter(types.values())
    selected={'contains_assertion','subject','written_as','realizes','requires_all','requires_any',
              'requires_analysis_of','supported_at','in_source','applies_at','illustrates_assertion','object',
              'has_source_example','has_illustrative_example'}
    edges=Counter((types[e['source']],e['type'],types[e['target']]) for e in graph['edges'] if e['type'] in selected)
    lines=['digraph KG {','rankdir=LR; bgcolor="white"; pad=0.35; nodesep=0.5; ranksep=1.1;',
           f'graph [fontname="DejaVu Sans",fontsize=15,label="Current grammar KG: node types and selected relations\\n{len(graph["nodes"])} nodes / {len(graph["edges"])} edges; structure, not a runtime trace",labelloc=t];',
           'node [shape=box,style="rounded,filled",fillcolor="#eef4fb",color="#476582",fontname="DejaVu Sans",fontsize=12];',
           'edge [fontname="DejaVu Sans",fontsize=10,color="#63788c"];']
    for kind,count in sorted(counts.items()):lines.append(f'"{kind}" [label="{kind}\\n{count}"];')
    for (source,kind,target),count in sorted(edges.items()):
        lines.append(f'"{source}" -> "{target}" [label="{kind} ({count})"];')
    lines.append('}')
    REPORTS.mkdir(parents=True,exist_ok=True)
    path=REPORTS/'schema.dot';path.write_text('\n'.join(lines)+'\n')
    if shutil.which('dot'):subprocess.run(['dot','-Tsvg',str(path),'-o',str(REPORTS/'schema.svg')],check=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['install','start','load','verify','status','figure'])
    args=p.parse_args()
    if args.action=='install':install()
    elif args.action=='start':os.execv(str(INSTALL/'bin/neo4j'),[str(INSTALL/'bin/neo4j'),'console'])
    elif args.action=='load':load_graph()
    elif args.action=='verify':verify()
    elif args.action=='figure':schema_figure()
    else:print(request('RETURN 1 AS reachable'))

if __name__=='__main__':main()

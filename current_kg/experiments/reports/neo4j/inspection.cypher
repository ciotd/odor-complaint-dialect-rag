// Existing JSON graph mirror. No vector index and no LLM-generated Cypher.
:param snapshot => '6725eb02e5f1cf284f402661f4b82b2b53b267b7430da63f02595e8ec35ee0bc';
:param function_id => 'concept:CONTENT_QUESTION';
:param record_id => 'GYS-Y009';

// Node/relationship type counts (run separately).
MATCH (n:KGNode {snapshot:$snapshot}) RETURN n.kg_type AS type, count(*) AS count ORDER BY type;
MATCH (:KGNode {snapshot:$snapshot})-[r]->(:KGNode {snapshot:$snapshot})
RETURN type(r) AS type, count(*) AS count ORDER BY type;

// First-stage function candidates: same realizes edge set as Python, not final selection.
MATCH (u:ExpressionUse {snapshot:$snapshot})-[r:realizes]->(f:GrammarConcept {snapshot:$snapshot,id:$function_id})
RETURN u,r,f;

// Record -> statements -> their subjects, objects, conditions and source locations.
MATCH (k:KnowledgeRecord {snapshot:$snapshot,id:$record_id})-[c:contains_assertion]->(a:Assertion {snapshot:$snapshot})
OPTIONAL MATCH (a)-[r]->(n:KGNode {snapshot:$snapshot})
RETURN k,c,a,r,n LIMIT 120;

// Quotation/contraction relationships, independent of function entry.
MATCH (a:KGNode {snapshot:$snapshot})-[r]->(b:KGNode {snapshot:$snapshot})
WHERE type(r) IN ['contracts_to','shares_quotative_construction','combines_with']
RETURN a,r,b LIMIT 100;

// Verbatim source examples (distinct from author-created illustrative examples).
MATCH (k:KnowledgeRecord {snapshot:$snapshot})-[r:has_source_example]->(e:SourceExample {snapshot:$snapshot})
OPTIONAL MATCH (e)-[s:supported_at]->(p:SourceLocation {snapshot:$snapshot})
RETURN k,r,e,s,p;

// A missing function-entry edge is a reachability observation, not missing grammar.
MATCH (u:ExpressionUse {snapshot:$snapshot})
WHERE NOT (u)-[:realizes]->(:GrammarConcept {snapshot:$snapshot})
RETURN u LIMIT 100;

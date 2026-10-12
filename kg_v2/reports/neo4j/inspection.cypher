// Neo4j Browser: http://127.0.0.1:17474/browser/
:param snapshot => 'cb88c00d4f989e45dc193936812fbce70551ee59328e8bed6785f7366ba445c7';
// Actual lexical -> inflection statements and their source/target expressions.
MATCH (l:KGv2Node {snapshot:$snapshot,id:'NAMU_GRAMMAR_20260908:v2:full:1057'})-[r:candidate_has_inflection]->(i:KGv2Node {id:'NAMU_GRAMMAR_20260908:v2:full:0239'})
OPTIONAL MATCH (l)-[a:source_expression|target_expression|requires|supported_by]->(x:KGv2Node)
OPTIONAL MATCH (i)-[b:source_expression|target_expression|requires|supported_by]->(y:KGv2Node)
RETURN l,r,i,a,x,b,y;

// Other lexical/inflection paths (bounded to keep Browser readable).
MATCH (l:KGv2Node {snapshot:$snapshot})-[r:candidate_has_inflection]->(i:KGv2Node {snapshot:$snapshot})
RETURN l,r,i LIMIT 40;

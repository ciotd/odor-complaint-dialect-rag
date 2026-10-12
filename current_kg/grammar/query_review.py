"""Read-only graph relation review; not a sentence parser or generation gate.

Starts at a grammatical function, follows realizes/variant_of/qualifies and
reports actual graph edges, source locations and unresolved conditions.
Only is/one_of conditions with scalar, manually supplied values are evaluated.
"""
import argparse
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent


def condition_status(condition, known):
    value = known.get(condition["field"])
    if value is None or not isinstance(value, str):
        return "unknown"
    if condition["operator"] not in {"is", "one_of"}:
        return "unknown"
    return "match" if value in condition["values"] else "mismatch"


def assess(conditions, known):
    evaluated = {mode: [{**c, "result": condition_status(c, known)} for c in items]
                 for mode, items in conditions.items()}
    all_values = [c["result"] for c in evaluated["all"]]
    any_values = [c["result"] for c in evaluated["any"]]
    if "mismatch" in all_values or (any_values and all(x == "mismatch" for x in any_values)):
        status = "mismatch"
    elif "unknown" in all_values or (any_values and "match" not in any_values):
        status = "unknown"
    else:
        status = "match"
    return {"status": status, "conditions": evaluated}


def assess_bound(conditions, application, input_features, candidate_features=None, target_features=None):
    """Evaluate explicitly bound fields; never infer candidate values from rule requirements."""
    providers = application.get('feature_sources')
    if providers is None:
        return {**assess(conditions, input_features), 'binding': 'legacy_flat'}
    scopes = {'input': input_features, 'candidate': candidate_features or {}, 'target': target_features or {}}
    fields = {c['field'] for m in ('all','any') for c in conditions[m]}
    if not fields <= set(providers):
        raise ValueError('Missing condition value provider')
    known = {field: scopes[providers[field]].get(field) for field in fields}
    return {**assess(conditions, known), 'binding': 'explicit', 'feature_sources': providers}


def index_conditions(graph):
    """Reusable read-only index for a fixed graph snapshot."""
    nodes = {n['id']: n for n in graph['nodes']}
    outgoing = {}
    semantic = {}
    subjects = {}
    for edge in graph['edges']:
        outgoing.setdefault(edge['source'], []).append(edge)
        aid = edge['properties'].get('assertion_id')
        if aid:
            semantic[aid] = edge
            subjects.setdefault(edge['source'], []).append(aid)
    return nodes, outgoing, semantic, subjects


def inspect_conditions(graph, start, input_features, candidate_features=None, target_features=None, _index=None):
    """One-hop condition/exception diagnostic for stages 1/2, not a generation selector."""
    nodes, outgoing, semantic, subjects = _index if _index is not None else index_conditions(graph)
    if start not in nodes or nodes[start]['type'] not in {'ExpressionUse','Assertion'}:
        raise ValueError('Start must be an existing use or assertion')
    own = [start] if nodes[start]['type']=='Assertion' else subjects.get(start, [])

    def packet(aid):
        e = semantic[aid]; a = nodes[aid]['properties']; rid = e['properties']['record_id']
        record = nodes[rid]['properties']
        actual = {m:[nodes[x['target']]['properties'] for x in outgoing.get(aid, [])
                     if x['type']=='requires_'+m] for m in ('all','any')}
        def canonical(rows):
            return sorted(json.dumps({k:c[k] for k in ('field','operator','values','evidence_keys')},sort_keys=True) for c in rows)
        if any(canonical(actual[m]) != canonical(a['conditions'][m]) for m in actual):
            raise ValueError('Missing/corrupt condition edges: '+aid)
        return {'assertion_id':aid,'record_id':rid,'predicate':e['type'],
                'subject':nodes[e['source']]['properties'], 'object':nodes[e['target']]['properties'],
                'assessment':assess_bound(actual,a['application'],input_features,candidate_features,target_features),
                'source_review':record['review']['source_fidelity'],'assertion_mode':a['assertion_mode'],
                'evidence': [nodes[x] for x in a['evidence_ids']], 'scope':record['scope'],
                'details':record['details'],'gaps':record['gaps']}
    own_packets=[packet(aid) for aid in own]
    origins=set(own)|{start}
    refs=[]
    for e in (edge for origin in sorted(origins) for edge in outgoing.get(origin, [])):
        if e['source'] not in origins or e['type'] not in {'has_applicability_constraint','has_construction_component',
                'has_inflection_description','contrasts_in_function','scope_tension_with'}:
            continue
        end=e['target']
        targets=[end] if nodes[end]['type']=='Assertion' else subjects.get(end, [])
        refs.append({'link_id':e['properties']['integration_id'],'relation':e['type'],
                     'from':e['source'],'to':end,'link_status':e['properties']['status'],
                     'limits':e['properties']['limits'], 'condition_inheritance':False,
                     'assertions':[packet(aid) for aid in targets]})
    blocked=[a['assertion_id'] for ref in refs if ref['relation']=='has_applicability_constraint'
             and ref['link_status']!='held_scope_tension' for a in ref['assertions']
             if a['source_review']=='author_checked' and a['predicate'] in {'excludes_combination','excludes_function'}
             and a['assessment']['status']=='match']
    # A prohibition on the starting use itself is as binding as a linked one.
    blocked += [a['assertion_id'] for a in own_packets
                if a['source_review']=='author_checked'
                and a['predicate'] in {'excludes_combination','excludes_function'}
                and a['assessment']['status']=='match']
    blocked = sorted(set(blocked))
    held=[a['assertion_id'] for a in own_packets if a['source_review']!='author_checked']
    held += [a['assertion_id'] for ref in refs for a in ref['assertions']
          if ref['link_status']=='held_scope_tension' or a['source_review']!='author_checked']
    return {'start':start,'input_features':input_features,'candidate_features':candidate_features or {},
            'target_features':target_features or {},'base_assertions':own_packets,'references':refs,
            'matched_explicit_exclusions':blocked,'held_assertions':held,
            'generation_approved':False,'status':'condition_and_exception_diagnostic_only'}


def review(graph, function_id, known, candidate_features=None, target_features=None):
    nodes = {n["id"]: n for n in graph["nodes"]}
    edges = graph["edges"]
    outgoing, incoming = {}, {}
    for e in edges:
        outgoing.setdefault(e["source"], []).append(e)
        incoming.setdefault(e["target"], []).append(e)

    def at(key, kind, reverse=False):
        return [e for e in (incoming if reverse else outgoing).get(key, []) if e["type"] == kind]

    def record_packet(rid):
        semantics = [e for e in edges if e["properties"].get("record_id") == rid]
        locations = [nodes[e["target"]] for e in at(rid, "supported_at")]
        source_edges = at(rid, "from_source")
        construction_paths = []
        for combination in (e for e in semantics if e["type"] == "combines_with"):
            for surface in (e for e in semantics if e["type"] == "has_surface_form"
                            and e["source"] == combination["source"]):
                for interpretation in (e for e in semantics if e["type"] == "has_interpretation"
                                       and e["source"] == surface["target"]):
                    path = [combination, surface, interpretation]
                    construction_paths.append({
                        "edges": path,
                        "nodes": [nodes[x] for x in sorted({i for p in path
                                                            for i in (p["source"], p["target"])})],
                        "status": "connected_construction_not_application_approval"})
        return {"record": nodes[rid], "semantic_triples": semantics,
                "construction_paths": construction_paths,
                "evidence_locations": locations,
                "source_edges": source_edges,
                "sources": [nodes[e["target"]] for e in source_edges]}

    candidates = []
    for e in at(function_id, "realizes", reverse=True):
        aid = e["properties"].get("assertion_id")
        if aid is None:
            continue
        application_edges = at(aid, "applies_at")
        if not any(x["target"] == "target:clause.final_ending" for x in application_edges):
            continue
        rid = e["properties"]["record_id"]
        assertion = nodes[aid]["properties"]
        conditions = {mode: [nodes[c["target"]]["properties"]
                             for c in at(aid, "requires_" + mode)]
                      for mode in ("all", "any")}
        # Missing condition edges are corruption, not evidence of unrestricted use.
        expected = assertion["conditions"]
        condition_keys = lambda items: sorted(json.dumps({k: c[k] for k in
            ("field", "operator", "values", "evidence_keys")}, sort_keys=True) for c in items)
        integrity = all(condition_keys(conditions[m]) == condition_keys(expected[m])
                        for m in ("all", "any"))
        assessment = assess_bound(conditions, assertion["application"], known, candidate_features, target_features) if integrity else {
            "status": "invalid_graph", "conditions": conditions}
        variants = at(e["source"], "variant_of", reverse=True)
        # Related knowledge is reported, never treated as inheriting the base use's conditions.
        links = at(rid, "qualifies") + at(rid, "qualifies", reverse=True)
        related = sorted({x["target"] if x["source"] == rid else x["source"] for x in links})
        evidence_edges = []
        for mode in ("all", "any"):
            for c in at(aid, "requires_" + mode):
                evidence_edges.extend(at(c["target"], "supported_at"))
        candidates.append({
            "record_id": rid, "form": nodes[e["source"]]["properties"]["text"],
            "condition_assessment": assessment,
            "function_edge": e, "application_edges": application_edges,
            "condition_edges": at(aid, "requires_all") + at(aid, "requires_any"),
            "condition_evidence_edges": evidence_edges,
            "variants": [{"form": nodes[v["source"]]["properties"]["text"], "edge": v,
                          "condition_assessment": assess_bound(v["properties"]["conditions"],
                              nodes[v["properties"]["assertion_id"]]["properties"]["application"],
                              known, candidate_features, target_features)}
                         for v in variants],
            "knowledge": record_packet(rid), "related_record_edges": links,
            "related_knowledge": [record_packet(x) for x in related],
        })
    return {"function_id": function_id, "manual_features": known,
            "status": "relation_review_not_generation_approval",
            "limitations": ["자동 문장 분석·방언 생성은 하지 않는다.",
                            "match는 제공된 조건의 일치이며 모든 문법·지역·맥락 적합성 판정이 아니다.",
                            "기본형 조건을 연결된 복합 구성에 상속하지 않는다.",
                            "표시되는 edge는 근거 연결이며 DB 엔진의 실행 경로 로그가 아니다.",
                            "조회 결과 없음은 문법적 불가능을 뜻하지 않는다."],
            "candidates": sorted(candidates, key=lambda c: c["record_id"])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--condition-cases", action="store_true", help="Run stored stage 1/2 manual condition diagnostics")
    parser.add_argument("--question-type", choices=["polar", "content"], default="content")
    parser.add_argument("--speech-level")
    parser.add_argument("--save", action="store_true", help="Save this review in query_review.results.json")
    args = parser.parse_args()
    path = BASE / "grammar.graph.json"
    raw = path.read_bytes()
    if args.condition_cases:
        integration = json.loads((BASE / "integration.json").read_text())
        case_rows = integration["condition_exception_review"]["diagnostic_cases"] + integration.get("ending_expansion_review", {}).get("diagnostic_cases", [])
        cases = [{"label": row["label"], **inspect_conditions(json.loads(raw), **{k:v for k,v in row.items() if k!="label"})}
                 for row in case_rows]
        result = {"status":"stage_1_2_condition_exception_diagnostics", "graph_sha256":hashlib.sha256(raw).hexdigest(),
                  "origin":"manual_feature_cases_not_translation_results", "cases":cases}
        if args.save:
            (BASE / "query_review.results.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
        print(json.dumps([{"label":r["label"],"base_statuses":[a["assessment"]["status"] for a in r["base_assertions"]],
                           "exclusions":r["matched_explicit_exclusions"],"held":r["held_assertions"]} for r in cases],ensure_ascii=False,indent=2))
        return
    known = {"question_type": args.question_type, "sentence_type": "interrogative"}
    target = {"speech_level": args.speech_level} if args.speech_level else {}
    result = review(json.loads(raw), "concept:" + ("POLAR_QUESTION" if args.question_type == "polar"
                                                 else "CONTENT_QUESTION"), known, target_features=target)
    result["graph_sha256"] = hashlib.sha256(raw).hexdigest()
    if args.save:
        destination = BASE / "query_review.results.json"
        destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    summary = [{"record": c["record_id"], "form": c["form"],
                "status": c["condition_assessment"]["status"],
                "variants": [v["form"] for v in c["variants"]],
                "related": [k["record"]["id"] for k in c["related_knowledge"]]}
               for c in result["candidates"]]
    print(json.dumps({"manual_features": known, "candidates": summary,
                      "generation_test": "not_performed"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

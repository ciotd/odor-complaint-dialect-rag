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


def review(graph, function_id, known):
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
        assessment = assess(conditions, known) if integrity else {
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
                          "condition_assessment": assess(v["properties"]["conditions"], known)}
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
    parser.add_argument("--question-type", choices=["polar", "content"], default="content")
    parser.add_argument("--speech-level")
    parser.add_argument("--save", action="store_true", help="Save this review in query_review.results.json")
    args = parser.parse_args()
    path = BASE / "grammar.graph.json"
    raw = path.read_bytes()
    known = {"question_type": args.question_type, "sentence_type": "interrogative"}
    if args.speech_level:
        known["speech_level"] = args.speech_level
    result = review(json.loads(raw), "concept:" + ("POLAR_QUESTION" if args.question_type == "polar"
                                                 else "CONTENT_QUESTION"), known)
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

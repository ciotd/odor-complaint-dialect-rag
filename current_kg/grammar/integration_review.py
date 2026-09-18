"""Offline path inspection of authored cross-source relations, not generation approval."""
import argparse
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent


def review(graph, start, relations):
    if not 1 <= len(relations) <= 6:
        raise ValueError("Specify one to six explicit relation steps")
    nodes = {n["id"]: n for n in graph["nodes"]}
    if start not in nodes:
        raise ValueError("Unknown start node")
    outgoing = {}
    for edge in graph["edges"]:
        outgoing.setdefault(edge["source"], []).append(edge)
    paths = [(start, [])]
    held = []
    for relation in relations:
        following = []
        for current, path in paths:
            for edge in outgoing.get(current, []):
                if edge["type"] != relation:
                    continue
                owners = [nodes.get(endpoint.split(":")[0], {}) for endpoint in
                          (edge["source"], edge["target"])]
                unresolved = any(owner.get("properties", {}).get("review", {}).get(
                    "source_fidelity") == "needs_review" for owner in owners)
                if edge["properties"].get("status") == "held_scope_tension" or unresolved:
                    held.append(edge)
                    continue
                following.append((edge["target"], path + [edge]))
        paths = following
    results = []
    for end, path in paths:
        evidence_ids = sorted({eid for edge in path for eid in edge["properties"].get("evidence_ids", [])})
        if not evidence_ids or any(eid not in nodes for eid in evidence_ids):
            raise ValueError("Path lacks available evidence")
        results.append({"end": nodes[end], "edges": path,
                        "evidence": [nodes[eid] for eid in evidence_ids],
                        "conditions": [{"edge_id": edge["id"], "conditions": edge["properties"].get("conditions"),
                                        "limits": edge["properties"].get("limits")} for edge in path],
                        "operational": False})
    return {"start": start, "relations": relations, "paths": results,
            "held_edges": held, "status": "graph_paths_only_not_condition_or_generation_approval"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="GYS-R011:F1")
    parser.add_argument("--relations", nargs="+", default=["has_inflection_description", "has_surface_form"])
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()
    raw = (BASE / "grammar.graph.json").read_bytes()
    result = review(json.loads(raw), args.start, args.relations)
    result["graph_sha256"] = hashlib.sha256(raw).hexdigest()
    value = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.save:
        (BASE / "integration_review.results.json").write_text(value)
    print(value)


if __name__ == "__main__":
    main()

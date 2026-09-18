"""Read-only audit of saved knowledge, with optional derived report export.

Counts are implementation diagnostics, not linguistic correctness or completeness scores.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent


def audit():
    records = [json.loads(line) for line in (BASE / "records.jsonl").read_text().splitlines() if line.strip()]
    raw_graph = (BASE / "grammar.graph.json").read_bytes()
    graph = json.loads(raw_graph)
    integration = json.loads((BASE / "integration.json").read_text())
    progress = json.loads((BASE / "progress.json").read_text())
    by_id = {r["id"]: r for r in records}
    used_forms = {endpoint for e in graph["edges"]
                  if "assertion_id" in e["properties"] or "integration_id" in e["properties"]
                  for endpoint in (e["source"], e["target"])}
    disconnected_forms = []
    meaning_only = []
    for r in records:
        k = r["knowledge"]
        for f in k["forms"]:
            if r["id"] + ":" + f["key"] not in used_forms:
                disconnected_forms.append({"record_id": r["id"], "form_key": f["key"], "text": f["text"]})
        for i, relation in enumerate(k["relations"], 1):
            fields = {c["field"] for side in ("all", "any") for c in relation["conditions"][side]}
            if fields == {"meaning"}:
                meaning_only.append(r["id"] + ":A" + str(i))
    sections = []
    for source in integration["processing_inventory"]["sources"]:
        for section in source["sections"]:
            lo, hi = section["pages"]
            rows = [r for r in records if r["source_id"] == source["source_id"] and
                    any(lo <= e["page"] <= hi for e in r["knowledge"]["evidence"])]
            sections.append({"source_id": source["source_id"], **section,
                             "record_ids": [r["id"] for r in rows],
                             "exhaustive_statement_adjudication": False,
                             "note": "구간에 근거를 둔 기록 목록이며 모든 설명의 전수 판정 완료가 아님"})
    links = []
    for link in integration["links"]:
        left = by_id[link["from"].split(":")[0]]
        right = by_id[link["to"].split(":")[0]]
        links.append({**link, "cross_source": left["source_id"] != right["source_id"],
                      "endpoint_needs_review": any(r["review"]["source_fidelity"] == "needs_review" for r in (left, right))})
    return {"status": "partial_authoring_not_full_completion", "graph_sha256": hashlib.sha256(raw_graph).hexdigest(),
            "records": len(records), "by_source": dict(Counter(r["source_id"] for r in records)),
            "nodes": len(graph["nodes"]), "edges": len(graph["edges"]),
            "semantic_edges": sum("assertion_id" in e["properties"] for e in graph["edges"]),
            "integration_edges": len(links), "cross_source_links": sum(l["cross_source"] for l in links),
            "held_links": sum(l["status"] == "held_scope_tension" or l["endpoint_needs_review"] for l in links),
            "records_needing_review": [r["id"] for r in records if r["review"]["source_fidelity"] == "needs_review"],
            "forms_without_semantic_or_integration_edge": disconnected_forms,
            "meaning_only_condition_assertions": meaning_only,
            "null_example_records": [r["id"] for r in records if not r["knowledge"]["illustrative_examples"]],
            "section_inventory": sections, "integration_links": links, "issues": integration["issues"],
            "rejected_links": integration.get("review_rejected_links", []),
            "page_status_counts": progress["page_status_counts"]}


def render(result):
    def cell(v):
        return str(v).replace("|", "\\|").replace("\n", " ")
    lines = ["# 전체 작성·연결 점검 결과", "", "기준: 2026-09-17 직접 작성본. 이 파일은 `authoring_audit.py --save`로 재생성한다.", "",
             "## 완료와 미완료", "",
             "원문 전 범위의 검토·처리방침과 개별 문법 설명의 전수 작성은 다르다. **현재 전수 작성·판정 완료를 입증하지 못했으며, 전체 완성본이 아니다.**", "",
             f"이번 요청 전 147건에서 {result['records']}건으로 증가했다. 독립 검토·생성 승인은 여전히 0건이다.", "",
             f"그래프 {result['nodes']:,}노드·{result['edges']:,}엣지 중 문법 진술 {result['semantic_edges']}개, 통합·대조 {result['integration_edges']}개다. 후자의 교차 문헌 연결은 {result['cross_source_links']}개다.", "",
             "## 작성본에서 발견한 공백", "",
             f"- 근거 해석 재검토 기록: {len(result['records_needing_review'])}건.",
             f"- 기능·결합·통합 엣지에 아직 참여하지 않는 표현 노드: {len(result['forms_without_semantic_or_integration_edge'])}개. 목록에 적었다고 용법 연결까지 끝난 것은 아니다.",
             f"- 조건이 자유 서술형 meaning에만 있는 관계: {len(result['meaning_only_condition_assertions'])}개. 모두 오류라는 뜻은 아니지만 자동 입력과 조건 판정의 연결을 완료한 것으로 볼 수 없다.",
             f"- 설명용 예문이 null인 기록: {len(result['null_example_records'])}건. 불확실한 예문을 만들어 채우지 않았다.",
             f"- 충돌 또는 끝점 기록의 재검토 상태 때문에 경로 반환을 보류하는 통합 관계: {result['held_links']}개.", "",
             "구체적인 ID와 쪽 구간별 작성 기록은 [authoring_audit.results.json](authoring_audit.results.json)에 있다. 이 수치를 자연스러움·정확성·원문 포괄률로 해석하지 않는다.", "",
             "## 자료별 작성", "", "| 자료 ID | 기록 수 |", "|---|---:|"]
    lines += [f"| {sid} | {n} |" for sid, n in result["by_source"].items()]
    lines += ["", "## 모든 통합·대조 관계의 이유와 한계", "",
              "same_usage_candidate는 동일성 확정이 아니며, shares_function_with는 상호 치환 가능성을 뜻하지 않는다. 위키 네 문서를 독립 근거 네 개로 세지 않는다.", "",
              "| ID | 출발 → 관계 → 도착 | 연결 이유 | 제한·보류 |", "|---|---|---|---|"]
    for l in result["integration_links"]:
        state = " / 경로 보류" if l["status"] == "held_scope_tension" or l["endpoint_needs_review"] else " / 작성자 제안"
        lines.append("| " + " | ".join(map(cell, [l["id"], f"{l['from']} → {l['relation']} → {l['to']}", l["reason"], l["limits"] + state])) + " |")
    lines += ["", "### 검토 후 채택하지 않은 연결", ""]
    lines += [f"- {l['id']}: {l['reason']}" for l in result["rejected_links"]]
    lines += ["", "## 알려진 문제의 처리 상태", "", "| 문제 | 대응 | 상태 |", "|---|---|---|"]
    lines += ["| " + " | ".join(map(cell, [i["problem"], i["action"], i["status"]])) + " |" for i in result["issues"]]
    lines += ["", "## 남은 작업 — 이 보고로 대체하지 않음", "",
              "1. 각 원문의 개별 설명·표 항목과 작성 기록을 대조해 누락을 작성하거나 근거 있는 배경/보류/제외 판정을 남긴다. 구간 단위 장부만으로 전수 판정을 선언하지 않는다.",
              "2. 설명문에만 남은 용법별 결합 조건을 관계로 연결하고, 같은 기록 안에 나열만 된 표현을 필요한 경우 분리한다. 원문에 없는 조건은 추정하지 않는다.",
              "3. 보류된 원문 충돌·희소 예·재인용·글자 및 음성 문제를 해결 가능한 범위에서 검토한다. 독립 화자 판단이 필요한 항목은 계속 미승인으로 둔다.",
              "4. 전체 지식의 독립 검토와 입력 분석·생성·통제된 비교는 아직 수행하지 않았다.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()
    result = audit()
    if args.save:
        (BASE / "authoring_audit.results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        (BASE / "작성검토.md").write_text(render(result))
    print(json.dumps({k: v for k, v in result.items() if k in {"status", "records", "nodes", "edges", "semantic_edges", "integration_edges", "cross_source_links", "held_links", "by_source", "page_status_counts"}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

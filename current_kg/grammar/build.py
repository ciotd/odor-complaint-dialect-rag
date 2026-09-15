#!/usr/bin/python3
"""Offline validation/export of directly authored grammar knowledge; no model calls."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import subprocess
import unicodedata
from jsonschema import Draft202012Validator

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
ORDER = ["NAMU_PHONOLOGY_20260908", "NAMU_GRAMMAR_20260908", "RYU2014",
         "NAMU_HONORIFICS_20260908", "NAMU20260901", "JO2018"]
GROUPS = {
 "UNITS": ("단위와 품사", "MORPHEME:형태소 WORD:단어 NOUN:명사 PRONOUN:대명사 NUMERAL:수사 VERB:동사 ADJECTIVE:형용사 COPULA:계사 DETERMINER:관형사 ADVERB:부사 INTERJECTION:감탄사 PARTICLE:조사 ENDING:어미"),
 "MORPHOLOGY": ("형태 구성과 결합", "INFLECTION:활용 DERIVATION:파생 STEM:어간 PREFINAL_ENDING:선어말어미 FINAL_ENDING:종결어미 CONNECTIVE_ENDING:연결어미 TRANSFORMATIVE_ENDING:전성어미 CASE_PARTICLE:격조사 AUXILIARY_PARTICLE:보조사 CONJUNCTIVE_PARTICLE:접속조사 ALLOMORPH:이형태 AUXILIARY_PREDICATE:보조용언"),
 "SYNTAX": ("문장 구조와 성분", "CLAUSE:절 PREDICATE:서술어 SUBJECT:주어 OBJECT:목적어 COMPLEMENT:보어 ARGUMENT:논항 MODIFIER:수식 COORDINATION:대등접속 SUBORDINATION:종속접속 EMBEDDING:내포 QUOTATION:인용 NOMINALIZATION:명사절화 RELATIVIZATION:관형절화 ELLIPSIS:생략 WORD_ORDER:어순"),
 "FUNCTION": ("문법 기능과 적용 범위", "TENSE:시제 PAST:과거 PRESENT:현재 FUTURE:미래 ASPECT:상 PROGRESSIVE:진행 RESULTATIVE:결과상 MODALITY:양태 GUESS:추측 INTENTION:의도 OBLIGATION:의무 POSSIBILITY:가능 NEGATION:부정 ABILITY_NEGATION:능력부정 PROHIBITION:금지 CAUSATIVE:사동 PASSIVE:피동 CAUSE:이유 PURPOSE:목적 CONDITION:조건 CONCESSION:양보 MANNER:방식 FOCUS:초점 EMPHASIS:강조 TOPIC:화제 COMPARISON:비교 SCOPE:적용범위"),
 "DISCOURSE": ("문장 유형과 높임 및 담화", "DECLARATIVE:평서 INTERROGATIVE:의문 POLAR_QUESTION:판정의문 CONTENT_QUESTION:설명의문 IMPERATIVE:명령 HORTATIVE:청유 EXCLAMATIVE:감탄 HONORIFICS:높임 SUBJECT_HONORIFIC:주체높임 OBJECT_HONORIFIC:객체높임 ADDRESSEE_HONORIFIC:상대높임 SPEECH_LEVEL:상대높임등급 ADDRESS:호칭 PERSON:인칭 DISCOURSE_MARKER:담화표지 USAGE:사용맥락"),
 "PHONOLOGY": ("음운과 표기", "VOWEL:모음 CONSONANT:자음 PITCH:성조 CONTRACTION:축약 DELETION:탈락 ASSIMILATION:동화 INSERTION:첨가 ORTHOGRAPHY:표기"),
}

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def encoded(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()

def read(path):
    return json.loads(Path(path).read_text())

def save(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")
    temp.replace(path)

def ontology():
    result = [{"id": "GRAMMAR", "label": "공통 문법", "parent": None}]
    for group, (label, members) in GROUPS.items():
        result.append({"id": group, "label": label, "parent": "GRAMMAR"})
        for item in members.split():
            key, title = item.split(":")
            result.append({"id": key, "label": title, "parent": group})
    return result

CONCEPT_IDS = {c["id"] for c in ontology()}
SCHEMA = read(BASE / "record.schema.json")
VALIDATOR = Draft202012Validator(SCHEMA)

def sources():
    registry = read(ROOT / "current_kg/claims/source_registry.json")
    selected = {s["source_id"]: s for s in registry["sources"]
                if s.get("eligible_for_claims") and s.get("file", {}).get("path", "").endswith(".pdf")}
    if set(selected) != set(ORDER):
        raise ValueError("Eligible PDF set differs from approved six sources")
    return [selected[key] for key in ORDER]

def source_pages(source):
    path = ROOT / source["file"]["path"]
    if digest(path.read_bytes()) != source["file"]["sha256"]:
        raise ValueError("Source hash changed: " + source["source_id"])
    info = subprocess.check_output(["pdfinfo", str(path)], text=True)
    count = int(re.search(r"^Pages:\s+(\d+)", info, re.M)[1])
    text = subprocess.check_output(["pdftotext", "-layout", str(path), "-"], text=True)
    pages = text.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    if len(pages) != count or count != source["file"]["pages"]:
        raise ValueError("PDF page count mismatch: " + source["source_id"])
    return pages

def contract_hash():
    return digest(encoded({"schema": SCHEMA, "analysis_contract": read(BASE / "analysis_contract.json"),
                           "ontology": ontology(), "protocol": "direct-authoring-0.2"}))

def prepare():
    manifest_sources = []
    for source in sources():
        pages = source_pages(source)
        manifest_sources.append({"source_id": source["source_id"], "file": source["file"],
            "pages": [{"page": i + 1, "text_sha256": digest(p), "characters": len(p)}
                      for i, p in enumerate(pages)]})
    manifest = {"version": "0.2", "sources": manifest_sources,
                "total_pages": sum(len(s["pages"]) for s in manifest_sources)}
    path = BASE / "manifest.json"
    if path.exists() and read(path)["sources"] != manifest_sources:
        raise ValueError("Source content changed; review before replacing manifest")
    save(path, manifest)
    save(BASE / "ontology.json", {"status": "analytic_scaffold_not_source_assertions", "concepts": ontology()})
    return manifest

def validate_record(record, target, supplied):
    VALIDATOR.validate(record)
    forms = {f["key"] for f in record["forms"]}
    evidences = {e["key"] for e in record["evidence"]}
    if len(forms) != len(record["forms"]) or len(evidences) != len(record["evidence"]):
        raise ValueError("Duplicate local key")
    if not set(record["concepts"]) <= CONCEPT_IDS:
        raise ValueError("Unknown concept ID")
    epages = {e["page"] for e in record["evidence"]}
    if not epages <= set(supplied) or not epages & set(target):
        raise ValueError("Evidence outside supplied pages or no target evidence")
    if record["kind"] not in record["details"]:
        raise ValueError("Missing type-specific detail array")
    def refs(keys):
        if not set(keys) <= evidences:
            raise ValueError("Unknown evidence key")
    for scope in record["scope"].values():
        refs(scope["evidence_keys"])
        if scope["basis"] in {"unknown", "not_applicable"} and scope["values"]:
            raise ValueError("Unknown scope must not assert values")
        if scope["basis"] in {"stated", "source_context"} and (not scope["evidence_keys"] or not scope["values"]):
            raise ValueError("Stated scope lacks evidence/value")
    contract = read(BASE / "analysis_contract.json")
    for rel in record["relations"]:
        application = rel["application"]
        if application["target"] not in contract["targets"]:
            raise ValueError("Unknown analysis target")
        if not set(application["input_features"]) <= set(contract["features"]):
            raise ValueError("Unknown analysis feature")
        used = {c["field"] for c in rel["conditions"]["all"] + rel["conditions"]["any"]}
        if not used <= set(application["input_features"]):
            raise ValueError("Condition field missing from input bridge")
        if not used and application["target"] != "knowledge.context":
            raise ValueError("Explicit retrieval features required")
        for condition in rel["conditions"]["all"] + rel["conditions"]["any"]:
            spec = contract["features"][condition["field"]]
            if "values" in spec and not set(condition["values"]) <= set(spec["values"]):
                raise ValueError("Condition values outside shared analysis vocabulary")
        if rel["subject"] not in forms and rel["subject"] not in {"concept:" + c for c in CONCEPT_IDS}:
            raise ValueError("Unknown subject")
        obj = rel["object"]
        if obj["kind"] == "form" and obj["ref"] not in forms:
            raise ValueError("Unknown object form")
        if obj["kind"] == "concept" and obj["ref"] not in CONCEPT_IDS:
            raise ValueError("Unknown object concept")
        refs(rel["evidence_keys"])
        for condition in rel["conditions"]["all"] + rel["conditions"]["any"]:
            refs(condition["evidence_keys"])
    for details in record["details"].values():
        for detail in details:
            refs(detail["evidence_keys"])
    if not record["illustrative_examples_note"].strip():
        raise ValueError("Example status/reason required")
    for example in record["illustrative_examples"] or []:
        refs(example["basis_evidence_keys"])
        if example["focus_form_key"] is not None and example["focus_form_key"] not in forms:
            raise ValueError("Unknown example focus form")
        if example["relation_index"] > len(record["relations"]):
            raise ValueError("Unknown example relation")
        relation = record["relations"][example["relation_index"] - 1]
        related_forms = {relation["subject"]}
        if relation["object"]["kind"] == "form":
            related_forms.add(relation["object"]["ref"])
        if example["focus_form_key"] is None and not relation["subject"].startswith("concept:"):
            raise ValueError("Null example focus requires a concept subject")
        if example["focus_form_key"] is not None and example["focus_form_key"] not in related_forms:
            raise ValueError("Example focus outside illustrated relation")
        if not set(example["basis_evidence_keys"]) & set(relation["evidence_keys"]):
            raise ValueError("Example basis must include illustrated relation evidence")

def graph(records, source_list):
    nodes, edges = {}, []
    def node(key, kind, **props):
        value = {"id": key, "type": kind, "properties": props}
        if key in nodes and nodes[key] != value:
            raise ValueError("Graph node identity collision: " + key)
        nodes[key] = value
        return key
    def edge(a, rel, b, **props):
        edges.append({"source": a, "type": rel, "target": b, "properties": props})
    for c in ontology():
        node("concept:" + c["id"], "GrammarConcept", label=c["label"], status="analytic_scaffold")
        if c["parent"]:
            edge("concept:" + c["id"], "classified_under", "concept:" + c["parent"])
    contract = read(BASE / "analysis_contract.json")
    for key, definition in contract["features"].items():
        node("analysis:" + key, "AnalysisFeature", **definition, status="adapter_design_not_source_fact")
    for key, definition in contract["targets"].items():
        node("target:" + key, "ApplicationTarget", **definition, status="adapter_design_not_source_fact")
    for source in source_list:
        sid = source["source_id"]
        node("source:" + sid, "Source", title=source["title"], file=source["file"],
             independent_evidence_group="namuwiki_shared_lineage" if sid.startswith("NAMU") else sid)
    for wrapper in records:
        validate_admission(wrapper)
        r, rid, sid = wrapper["knowledge"], wrapper["id"], wrapper["source_id"]
        node(rid, "KnowledgeRecord", record_kind=r["kind"], label=r["label"], scope=r["scope"],
             details=r["details"], gaps=r["gaps"], review=wrapper["review"], operational=False,
             illustrative_examples_note=r["illustrative_examples_note"],
             illustrative_example_count=len(r["illustrative_examples"] or []))
        edge(rid, "from_source", "source:" + sid)
        for link in wrapper.get("links", []):
            edge(rid, link["relation"], link["record_id"], status="author_link")
        for concept in r["concepts"]:
            edge(rid, "about", "concept:" + concept)
        evmap, fmap = {}, {}
        for ev in r["evidence"]:
            eid = "evidence:" + digest(encoded([sid, ev["page"], ev["locator"]]))[:24]
            evmap[ev["key"]] = node(eid, "SourceLocation", source_id=sid, page=ev["page"], locator=ev["locator"])
            edge(rid, "supported_at", eid)
            edge(eid, "in_source", "source:" + sid)
        for form in r["forms"]:
            spelling = unicodedata.normalize("NFC", form["text"].strip())
            surface = node("surface:" + digest(spelling)[:24], "SurfaceForm", text=spelling)
            fid = node(rid + ":" + form["key"], "ExpressionUse", text=spelling, role=form["role"],
                       sense=form["sense"], pos=form["pos"])
            fmap[form["key"]] = fid
            edge(rid, "describes", fid)
            edge(fid, "written_as", surface)
        for index, rel in enumerate(r["relations"], 1):
            aid = node(rid + f":A{index}", "Assertion", assertion_mode=rel["assertion_mode"],
                       scope=r["scope"], conditions=rel["conditions"], application=rel["application"], operational=False,
                       evidence_ids=[evmap[e] for e in rel["evidence_keys"]])
            obj = rel["object"]
            if obj["kind"] == "form":
                target = fmap[obj["ref"]]
            elif obj["kind"] == "concept":
                target = "concept:" + obj["ref"]
            else:
                target = node(aid + ":value", "Value", text=obj["ref"])
            edge(rid, "contains_assertion", aid)
            edge(aid, "applies_at", "target:" + rel["application"]["target"])
            for feature in rel["application"]["input_features"]:
                edge(aid, "requires_analysis_of", "analysis:" + feature)
            subject = fmap.get(rel["subject"], rel["subject"])
            edge(aid, "subject", subject)
            edge(aid, "object", target)
            edge(subject, rel["predicate"], target, assertion_id=aid, record_id=rid,
                 conditions=rel["conditions"], scope=r["scope"], evidence_ids=[evmap[e] for e in rel["evidence_keys"]],
                 assertion_mode=rel["assertion_mode"], operational=False)
            for mode, conditions in rel["conditions"].items():
                for j, condition in enumerate(conditions):
                    cid = node(aid + f":{mode}:{j}", "Condition", **condition,
                               evidence_ids=[evmap[e] for e in condition["evidence_keys"]])
                    edge(aid, "requires_" + mode, cid)
                    for evidence_key in condition["evidence_keys"]:
                        edge(cid, "supported_at", evmap[evidence_key])
        for i, example in enumerate(r["illustrative_examples"] or [], 1):
            xid = node(rid + f":X{i}", "IllustrativeExample", **example,
                       independent_evidence=False, evaluation_gold=False, operational=False)
            edge(rid, "has_illustrative_example", xid)
            edge(xid, "illustrates_assertion", rid + f":A{example['relation_index']}")
            if example["focus_form_key"] is not None:
                edge(xid, "highlights_form", fmap[example["focus_form_key"]])
            for supporting_id in example.get("supporting_record_ids", []):
                edge(xid, "uses_knowledge_from", supporting_id)
            for key in example["basis_evidence_keys"]:
                edge(xid, "based_on_grammar_at", evmap[key])
    edges = list({encoded(e): e for e in edges}.values())
    for e in edges:
        if e["source"] not in nodes or e["target"] not in nodes:
            raise ValueError("Dangling graph edge")
        e["id"] = "edge:" + digest(encoded(e))[:24]
    return {"schema_version": "0.2", "status": "directly_authored_draft_not_operational",
            "nodes": sorted(nodes.values(), key=lambda n: n["id"]), "edges": sorted(edges, key=lambda e: e["id"])}

def collect(manifest):
    page_index = {(s["source_id"], p["page"]) for s in manifest["sources"] for p in s["pages"]}
    records, coverage, ids = [], {}, set()
    for path in sorted((BASE / "authored").glob("*.json")):
        bundle = read(path)
        if bundle["schema_version"] != "0.2" or bundle["author"]["method"] != "direct_source_reading":
            raise ValueError("Only directly authored current-schema bundles are accepted")
        sid, read_pages = bundle["source_id"], bundle["read_pages"]
        if not read_pages or len(set(read_pages)) != len(read_pages):
            raise ValueError("Invalid read-page list")
        if any((sid, p) not in page_index for p in read_pages):
            raise ValueError("Authoring pages outside approved source")
        for wrapper in bundle["records"]:
            rid, knowledge = wrapper["id"], wrapper["knowledge"]
            if rid in ids:
                raise ValueError("Duplicate stable record ID")
            ids.add(rid)
            validate_record(knowledge, read_pages, read_pages)
            validate_admission(wrapper)
            review = wrapper["review"]
            if review["source_fidelity"] not in {"author_checked", "needs_review"}:
                raise ValueError("Invalid author review status")
            if review["generation"] != "not_approved" or review["independent_review"] != "not_performed":
                raise ValueError("No automatic generation or independent-review approval")
            records.append({**wrapper, "source_id": sid, "producer": bundle["author"],
                            "authored_file": str(path.relative_to(ROOT)),
                            "review": {**review, "structure": "passed"}})
        for entry in bundle["coverage"]:
            key = (sid, entry["page"])
            if key in coverage or entry["page"] not in read_pages:
                raise ValueError("Duplicate or unread coverage page")
            if entry["status"] not in {"partial", "draft_complete", "context_only", "needs_review"}:
                raise ValueError("Invalid page coverage status")
            if not entry["reason"].strip():
                raise ValueError("Coverage reason required")
            if entry["remaining"] and entry["status"] not in {"partial", "needs_review"}:
                raise ValueError("Page with remaining work cannot be completed")
            if entry["status"] in {"draft_complete", "partial"} and not any(
                entry["page"] in [e["page"] for e in w["knowledge"]["evidence"]] for w in bundle["records"]):
                raise ValueError("Covered page has no linked knowledge")
            coverage[key] = {**entry, "source_id": sid}
    for record in records:
        for example in record["knowledge"]["illustrative_examples"] or []:
            if not set(example.get("supporting_record_ids", [])) <= ids:
                raise ValueError("Unknown supporting example record")
        for link in record.get("links", []):
            if link["record_id"] not in ids or link["relation"] not in {"illustrates", "qualifies", "contrasts_with"}:
                raise ValueError("Invalid cross-record link")
    return records, coverage

def validate_admission(wrapper):
    """Source-only background is not active grammar knowledge."""
    k = wrapper["knowledge"]
    if all(r["application"]["target"] == "knowledge.context" for r in k["relations"]):
        if not (wrapper.get("admission") == "held_grammar_candidate" and k["forms"]
                and wrapper["review"]["source_fidelity"] == "needs_review"
                and wrapper["review"]["generation"] == "not_approved"):
            raise ValueError("Source-only context belongs in source_notes, not active grammar records")

def render_example_review(records):
    """Human-readable view of authored review notes; not an independent review."""
    reviewed = [r for r in records if "example_review" in r]
    with_examples = [r for r in reviewed if r["knowledge"]["illustrative_examples"]]
    count = sum(len(r["knowledge"]["illustrative_examples"] or []) for r in reviewed)
    lines = ["# 문법 기록 예문 재검수", "",
             "작성자: Codex. 원문·기존 기록 대조 및 설명용 예문 작성 결과. 독립 검토나 자연스러움 검증 결과가 아닙니다.", "",
             f"검수 기록 {len(reviewed)}건 / 예문 있는 기록 {len(with_examples)}건 / 예문 {count}개 / null {len(reviewed) - len(with_examples)}건.", "",
             "아래 예문은 모두 작성자가 구성했습니다. 참고 근거는 문법 설명의 출처이지 문장 자체의 출처가 아닙니다. 표준어 대응·뜻·문법 기능·맥락도 작성자의 설명입니다.", "",
             "한 기록의 일부 용법에만 예문을 붙일 수 있습니다. 예문이 없는 관계 번호를 함께 표시합니다. 전체 문장이 특정 지역의 자연스러운 말투라는 승인은 아닙니다.", "",
             "수정 원본은 authored/*.json이며 이 문서는 build.py export로 재생성하는 파생 파일입니다.", ""]
    labels = {"examples_added_or_rechecked": "예문 작성·재검수",
              "held_uncertain": "불확실하여 보류", "not_sentence_applicable": "대응 문장 예문 해당 없음"}
    source_titles = {s["source_id"]: s["title"] for s in sources()}
    def cell(value):
        return str(value).replace("|", "\\|").replace("\n", " ")
    for r in sorted(reviewed, key=lambda r: r["id"]):
        k, review = r["knowledge"], r["example_review"]
        examples = k["illustrative_examples"] or []
        lines += [f"## {r['id']} — {k['label']}", "",
                  f"상태: {labels[review['decision']]} / 검수일: {review['reviewed_on']}", "",
                  f"근거: {source_titles[r['source_id']]} / PDF 쪽: {', '.join(map(str, review['source_pages']))}", "",
                  f"작성 원본: [{r['authored_file']}]({ROOT / r['authored_file']})", "",
                  review["note"], ""]
        if not examples:
            lines += ["예문: `null`", ""]
        else:
            lines += ["| 번호 | 표준어 | 설명용 방언 문장 | 뜻 | 문법 기능 |",
                      "|---|---|---|---|---|"]
            for i, x in enumerate(examples, 1):
                lines.append("| " + " | ".join(map(cell, [i, x["standard_sentence"], x["dialect_sentence"], x["meaning"], x["grammar_function"]])) + " |")
            lines.append("")
            for i, x in enumerate(examples, 1):
                lines += [f"예문 {i} 맥락: {x.get('context', '별도 맥락 미기록')}", "",
                          f"연결: {r['id']}:A{x['relation_index']} / 참고 근거 키: {', '.join(x['basis_evidence_keys'])} / 함께 참고한 기록: {', '.join(x.get('supporting_record_ids', [])) or '없음'}", ""]
        remaining = review["remaining_relation_indexes"]
        lines += ["이 기록에서 아직 예문이 없는 관계 번호: " + (", ".join(map(str, remaining)) if remaining else "없음") + ".", ""]
    return "\n".join(lines)

def artifacts(manifest):
    records, coverage = collect(manifest)
    ancillary = read(BASE / "source_notes.json")
    retired = read(BASE / "retired/context_records_2026-09-15.json")
    active_ids = {r["id"] for r in records}
    if active_ids & {r["id"] for r in retired["original_records"]}:
        raise ValueError("Retired context record re-entered active grammar")
    for note in ancillary["notes"]:
        if note["in_grammar_graph"] or note["generation_evidence"]:
            raise ValueError("Source/background notes must not become generation evidence")
        if not set(note["related_record_ids"]) <= active_ids:
            raise ValueError("Source note references missing grammar record")
    result_graph = graph(records, sources())
    pages, counts, by_source = [], {}, {}
    for source in manifest["sources"]:
        sid = source["source_id"]
        for page in source["pages"]:
            entry = coverage.get((sid, page["page"]),
                {"source_id": sid, "page": page["page"], "status": "pending", "reason": "", "remaining": []})
            pages.append(entry)
            counts[entry["status"]] = counts.get(entry["status"], 0) + 1
        by_source[sid] = {"total_pages": len(source["pages"]),
            "records": sum(r["source_id"] == sid for r in records),
            "page_status": {status: sum(p["source_id"] == sid and p["status"] == status for p in pages)
                            for status in sorted({p["status"] for p in pages if p["source_id"] == sid})}}
    gaps = [{"record_id": r["id"], "question": g} for r in records for g in r["knowledge"]["gaps"]]
    gaps += [{"source_id": p["source_id"], "page": p["page"], "question": item} for p in pages for item in p["remaining"]]
    linkage = []
    for record in records:
        for i, relation in enumerate(record["knowledge"]["relations"], 1):
            linkage.append({"record_id": record["id"], "assertion_id": record["id"] + f":A{i}",
                "application": relation["application"], "conditions": relation["conditions"],
                "evidence": [e for e in record["knowledge"]["evidence"] if e["key"] in relation["evidence_keys"]],
                "source_id": record["source_id"], "operational": False})
    progress = {"contract_sha256": contract_hash(), "mode": "direct_authoring_offline", "background_worker": False,
        "total_pages": manifest["total_pages"], "page_status_counts": counts, "records": len(records),
        "nodes": len(result_graph["nodes"]), "edges": len(result_graph["edges"]),
        "semantic_edges": sum("assertion_id" in e["properties"] for e in result_graph["edges"]),
        "author_checked_records": sum(r["review"]["source_fidelity"] == "author_checked" for r in records),
        "independently_reviewed_records": 0, "generation_approved_records": 0, "sources": by_source, "pages": pages}
    progress["illustrative_examples"] = {
        "reviewed_records": sum("example_review" in r for r in records),
        "records_with_examples": sum(bool(r["knowledge"]["illustrative_examples"]) for r in records),
        "example_count": sum(len(r["knowledge"]["illustrative_examples"] or []) for r in records),
        "null_records": sum(r["knowledge"]["illustrative_examples"] is None for r in records),
        "held_uncertain": sum(r.get("example_review", {}).get("decision") == "held_uncertain" for r in records),
        "not_sentence_applicable": sum(r.get("example_review", {}).get("decision") == "not_sentence_applicable" for r in records),
        "illustrated_relations": sum(len({x["relation_index"] for x in r["knowledge"]["illustrative_examples"] or []}) for r in records),
        "naturalness_test_performed": False}
    progress["excluded_from_grammar"] = {
        "retired_record_count": len(retired["original_records"]),
        "source_note_count": len(ancillary["notes"]),
        "independent_records_discarded": sum(d["action"] == "discarded" for d in retired["decisions"]),
        "notes_in_graph": False}
    return {"records": records, "example_review.md": render_example_review(records), "grammar.graph.json": result_graph, "progress.json": progress,
            "gaps.json": gaps, "analysis_links.json": linkage}

def export(manifest):
    data = artifacts(manifest)
    temp = BASE / "records.jsonl.tmp"
    temp.write_text("".join(encoded(r) + "\n" for r in data.pop("records")))
    temp.replace(BASE / "records.jsonl")
    for name, value in data.items():
        if name.endswith(".md"):
            (BASE / name).write_text(value)
        else:
            save(BASE / name, value)
    return {k: v for k, v in data["progress.json"].items() if k not in {"pages", "sources"}}

def check(manifest):
    # Read-only: do not repair output while claiming to check its reproducibility.
    data = artifacts(manifest)
    actual_records = [json.loads(line) for line in (BASE / "records.jsonl").read_text().splitlines()]
    if actual_records != data.pop("records"):
        raise ValueError("records.jsonl differs from authored inputs")
    for name, expected in data.items():
        actual = (BASE / name).read_text() if name.endswith(".md") else read(BASE / name)
        if actual != expected:
            raise ValueError(name + " does not reproduce from authored inputs")
    return {"structure_and_reproduction": "passed", "records": len(actual_records),
            "independent_linguistic_validation": "not_performed", "generation_test": "not_performed"}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "export", "check", "status"])
    args = parser.parse_args()
    if args.command == "prepare":
        manifest = prepare()
        print(encoded({"total_pages": manifest["total_pages"], "source_count": len(manifest["sources"])}))
    elif args.command == "export":
        print(encoded(export(read(BASE / "manifest.json"))))
    elif args.command == "check":
        print(encoded(check(read(BASE / "manifest.json"))))
    else:
        print(json.dumps({k: v for k, v in read(BASE / "progress.json").items() if k != "pages"},
                         ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()

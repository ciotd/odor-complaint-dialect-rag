"""Software fixtures are not dialect evidence. Actual records are checked separately."""
import ast
import copy
import json
from pathlib import Path
import tempfile
import unittest
from jsonschema.exceptions import ValidationError
from unittest.mock import patch
import build

def fixture():
    return {
        "kind": "construction", "label": "synthetic fixture",
        "concepts": ["INTERROGATIVE"],
        "forms": [{"key": "F1", "text": "TEST_ONLY", "role": "unspecified", "sense": None, "pos": None}],
        "relations": [{"subject": "F1", "predicate": "realizes",
                       "object": {"kind": "concept", "ref": "INTERROGATIVE"},
                       "conditions": {"all": [], "any": [
                           {"field": "question_type", "operator": "is", "values": ["polar"], "evidence_keys": ["E1"]},
                           {"field": "question_type", "operator": "is", "values": ["content"], "evidence_keys": ["E1"]}]},
                       "application": {"target": "clause.final_ending", "input_features": ["question_type"],
                                       "mapping_note": "synthetic mapping fixture"},
                       "assertion_mode": "source_statement", "evidence_keys": ["E1"]}],
        "scope": {key: {"values": [], "basis": "unknown", "evidence_keys": []}
                  for key in ["region", "period", "generation", "register"]},
        "evidence": [{"key": "E1", "page": 1, "locator": "synthetic fixture"}],
        "details": {"construction": []}, "gaps": [],
        "illustrative_examples": None, "illustrative_examples_note": "Software fixture; no linguistic example."}

class Tests(unittest.TestCase):
    def example_record(self):
        bundle = build.read(build.BASE / "authored/namu_inflection_01.json")
        return copy.deepcopy(next(r for r in bundle["records"] if r["id"] == "GYS-I035")["knowledge"])

    def test_example_is_separate_from_source_evidence(self):
        record = self.example_record()
        build.validate_record(record, [5], [5])
        g = build.graph([{"id": "TEST", "source_id": "SRC", "knowledge": record, "review": {}}],
                        [{"source_id": "SRC", "title": "fixture", "file": {}}])
        node = next(n for n in g["nodes"] if n["type"] == "IllustrativeExample")
        self.assertEqual("author_constructed", node["properties"]["origin"])
        self.assertFalse(node["properties"]["independent_evidence"])
        self.assertFalse(node["properties"]["evaluation_gold"])
        self.assertFalse(node["properties"]["operational"])
        links = [e for e in g["edges"] if e["source"] == node["id"]]
        self.assertTrue(any(e["type"] == "illustrates_assertion" and e["target"] == "TEST:A2" for e in links))
        self.assertFalse(any(e["type"] == "supported_at" for e in links))

    def test_example_unknown_relation_rejected(self):
        record = self.example_record()
        record["illustrative_examples"][0]["relation_index"] = 999
        with self.assertRaises(ValueError):
            build.validate_record(record, [5], [5])

    def test_example_mismatched_focus_rejected(self):
        record = self.example_record()
        record["illustrative_examples"][0]["focus_form_key"] = "F9"
        with self.assertRaises(ValueError):
            build.validate_record(record, [5], [5])

    def test_example_cannot_claim_naturalness_or_source_origin(self):
        for field, value in [("origin", "source"), ("naturalness", "verified")]:
            record = self.example_record()
            record["illustrative_examples"][0][field] = value
            with self.assertRaises(ValidationError):
                build.validate_record(record, [5], [5])

    def test_null_example_requires_reason(self):
        record = fixture()
        build.validate_record(record, [1], [1])
        record["illustrative_examples_note"] = "   "
        with self.assertRaises(ValueError):
            build.validate_record(record, [1], [1])

    def test_general_rule_example_does_not_require_invented_form(self):
        bundle = build.read(build.BASE / "authored/namu_inflection_01.json")
        record = next(r for r in bundle["records"] if r["id"] == "GYS-I003")["knowledge"]
        self.assertEqual([], record["forms"])
        self.assertIsNone(record["illustrative_examples"][0]["focus_form_key"])
        build.validate_record(record, bundle["read_pages"], bundle["read_pages"])

    def test_null_focus_not_allowed_for_expression_relation(self):
        record = self.example_record()
        record["illustrative_examples"][0]["focus_form_key"] = None
        with self.assertRaises(ValueError):
            build.validate_record(record, [5], [5])

    def test_review_inventory_and_example_coverage(self):
        records, _ = build.collect(build.read(build.BASE / "manifest.json"))
        original_ids = ({f"GYS-Q{i:03}" for i in range(1, 17)} |
                        {f"GYS-H{i:03}" for i in range(1, 3)} |
                        {f"GYS-I{i:03}" for i in list(range(1, 18)) + list(range(20, 57))})
        selected = {r["id"]: r for r in records if r["id"] in original_ids}
        retired = build.read(build.BASE / "retired/context_records_2026-09-15.json")
        retired_ids = {r["id"] for r in retired["original_records"]}
        self.assertFalse(retired_ids & set(selected))
        self.assertEqual(original_ids, set(selected) | retired_ids)
        for r in selected.values():
            k, review = r["knowledge"], r["example_review"]
            examples = k["illustrative_examples"] or []
            covered = {e["relation_index"] for e in examples}
            self.assertEqual(covered, set(review["illustrated_relation_indexes"]))
            self.assertEqual(set(range(1, len(k["relations"]) + 1)) - covered,
                             set(review["remaining_relation_indexes"]))
            self.assertEqual({e["page"] for e in k["evidence"]}, set(review["source_pages"]))
            self.assertFalse(review["naturalness_test_performed"])
            self.assertFalse(review["independent_review"])
            if not examples:
                self.assertIn(review["decision"], {"held_uncertain", "not_sentence_applicable"})
                self.assertTrue(review["note"].strip())
            for e in examples:
                self.assertTrue(e["context"].strip())
                self.assertEqual("author_constructed", e["origin"])
                self.assertEqual("not_verified", e["naturalness"])

    def test_example_report_is_derived_from_records(self):
        records, _ = build.collect(build.read(build.BASE / "manifest.json"))
        report = build.render_example_review(records)
        for r in records:
            if "example_review" in r:
                self.assertIn("## " + r["id"] + " — ", report)
                self.assertIn(r["example_review"]["note"], report)
                for e in r["knowledge"]["illustrative_examples"] or []:
                    self.assertIn(e["standard_sentence"], report)
                    self.assertIn(e["dialect_sentence"], report)

    def test_retired_source_only_records_cannot_be_readmitted(self):
        archive = build.read(build.BASE / "retired/context_records_2026-09-15.json")
        self.assertEqual(6, len(archive["original_records"]))
        for wrapper in archive["original_records"]:
            with self.assertRaises(ValueError):
                build.validate_admission(wrapper)

    def test_concrete_uncertain_form_can_remain_held(self):
        records, _ = build.collect(build.read(build.BASE / "manifest.json"))
        w = next(r for r in records if r["id"] == "GYS-I055")
        build.validate_admission(w)
        bad = copy.deepcopy(w)
        bad["review"]["source_fidelity"] = "author_checked"
        with self.assertRaises(ValueError):
            build.validate_admission(bad)

    def test_six_context_records_reclassified_outside_graph(self):
        data = build.artifacts(build.read(build.BASE / "manifest.json"))
        active = {r["id"]: r for r in data["records"]}
        archive = build.read(build.BASE / "retired/context_records_2026-09-15.json")
        old_ids = {r["id"] for r in archive["original_records"]}
        self.assertFalse(old_ids & set(active))
        self.assertFalse(old_ids & {n["id"] for n in data["grammar.graph.json"]["nodes"]})
        self.assertFalse(old_ids & {r["record_id"] for r in data["analysis_links.json"]})
        notes = build.read(build.BASE / "source_notes.json")
        self.assertFalse({n["id"] for n in notes["notes"]} & {n["id"] for n in data["grammar.graph.json"]["nodes"]})
        replacement = active["GYS-I057"]
        k = replacement["knowledge"]
        self.assertEqual({"싸우다", "싸오다"}, {f["text"] for f in k["forms"]})
        self.assertEqual(["경남 일부 지역"], k["scope"]["region"]["values"])
        self.assertEqual("predicate.lexical_choice", k["relations"][0]["application"]["target"])
        self.assertIsNone(k["illustrative_examples"])
        self.assertEqual("not_approved", replacement["review"]["generation"])
        self.assertEqual("needs_review", replacement["review"]["source_fidelity"])

    def test_valid(self):
        build.validate_record(fixture(), [1], [1, 2])

    def test_context_can_use_concept_without_expression(self):
        record = fixture()
        record["forms"] = []
        relation = record["relations"][0]
        relation["subject"] = "concept:INTERROGATIVE"
        relation["conditions"] = {"all": [], "any": []}
        relation["application"]["target"] = "knowledge.context"
        relation["application"]["input_features"] = []
        build.validate_record(record, [1], [1])
        relation["application"]["target"] = "clause.final_ending"
        with self.assertRaises(ValueError):
            build.validate_record(record, [1], [1])

    def test_unknown_concept_subject_rejected(self):
        record = fixture()
        record["relations"][0]["subject"] = "concept:NONEXISTENT"
        with self.assertRaises(ValueError):
            build.validate_record(record, [1], [1])

    def test_front_section_source_spellings_regression(self):
        # Author-checked PDF transcription regression, not naturalness evidence.
        bundle = build.read(build.BASE / "authored/namu_inflection_01.json")
        forms = {r["id"]: {f["text"] for f in r["knowledge"]["forms"]}
                 for r in bundle["records"]}
        self.assertIn("뼀다", forms["GYS-I020"])
        self.assertNotIn("뺐다", forms["GYS-I020"])
        self.assertIn("둤다", forms["GYS-I028"])
        self.assertNotIn("뒀다", forms["GYS-I028"])
        self.assertTrue({"배아", "배우고"} <= forms["GYS-I035"])
        record = next(r for r in bundle["records"] if r["id"] == "GYS-I035")
        self.assertEqual(8, len(record["knowledge"]["relations"]))
        self.assertTrue(all(r["assertion_mode"] == "example_only"
                            for r in record["knowledge"]["relations"]))

    def test_work_plan_covers_all_sources_without_claiming_completion(self):
        plan = build.read(build.BASE / "work_plan.json")
        records, _ = build.collect(build.read(build.BASE / "manifest.json"))
        ids = {r["id"] for r in records}
        self.assertEqual(6, len(plan["sources"]))
        self.assertEqual(452, sum(len(s["all_page_numbers"]) for s in plan["sources"]))
        for source in plan["sources"]:
            self.assertEqual(list(range(1, source["total_pages"] + 1)), source["all_page_numbers"])
            for section in source["sections"]:
                self.assertTrue(set(section["record_ids"]) <= ids)
                if section["status"] == "draft_complete":
                    self.assertFalse(section["remaining"])
        self.assertTrue(any(section["status"] == "pending" for source in plan["sources"]
                            for section in source["sections"]))

    def test_unknown_reference(self):
        record = fixture()
        record["relations"][0]["evidence_keys"] = ["E999"]
        with self.assertRaises(ValueError):
            build.validate_record(record, [1], [1])

    def test_unknown_region_not_universal(self):
        record = fixture()
        record["scope"]["region"]["values"] = ["부산"]
        with self.assertRaises(ValueError):
            build.validate_record(record, [1], [1])

    def test_source_context_needs_evidence(self):
        record = fixture()
        record["scope"]["region"] = {"values": ["test"], "basis": "source_context", "evidence_keys": []}
        with self.assertRaises(ValueError):
            build.validate_record(record, [1], [1])

    def test_context_only_evidence_rejected(self):
        with self.assertRaises(ValueError):
            build.validate_record(fixture(), [2], [1, 2])

    def test_bridge_must_name_condition_features(self):
        record = fixture()
        record["relations"][0]["application"]["input_features"] = ["speech_level"]
        with self.assertRaises(ValueError):
            build.validate_record(record, [1], [1])

    def test_bridge_values_must_use_common_vocabulary(self):
        record = fixture()
        record["relations"][0]["conditions"]["any"][0]["values"] = ["unknown_typo"]
        with self.assertRaises(ValueError):
            build.validate_record(record, [1], [1])

    def test_shared_concept_not_shared_sense(self):
        records = [{"id": f"test:{sid}", "source_id": sid, "knowledge": fixture(), "review": {}}
                   for sid in ["A", "B"]]
        source_list = [{"source_id": sid, "title": sid, "file": {}} for sid in ["A", "B"]]
        result = build.graph(records, source_list)
        self.assertEqual(result, build.graph(copy.deepcopy(records), source_list))
        self.assertEqual(1, sum(n["type"] == "SurfaceForm" for n in result["nodes"]))
        self.assertEqual(2, sum(n["type"] == "ExpressionUse" for n in result["nodes"]))
        semantics = [e for e in result["edges"] if e["type"] == "realizes"]
        self.assertEqual({"concept:INTERROGATIVE"}, {e["target"] for e in semantics})
        for edge in semantics:
            self.assertFalse(edge["properties"]["operational"])
            self.assertEqual(2, len(edge["properties"]["conditions"]["any"]))
        bridges = [e for e in result["edges"] if e["type"] == "requires_analysis_of"]
        self.assertEqual({"analysis:question_type"}, {e["target"] for e in bridges})

    def test_actual_manifest_complete_no_duplicates(self):
        manifest = build.read(build.BASE / "manifest.json")
        pages = [(s["source_id"], p["page"]) for s in manifest["sources"] for p in s["pages"]]
        self.assertEqual(452, len(pages))
        self.assertEqual(452, len(set(pages)))
        self.assertNotIn("batches", manifest)

    def test_no_network_or_model_runner(self):
        tree = ast.parse((build.BASE / "build.py").read_text())
        roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(a.name.split(".")[0] for a in node.names)
            if isinstance(node, ast.ImportFrom):
                roots.add((node.module or "").split(".")[0])
        self.assertFalse(roots & {"urllib", "httpx", "requests", "openai", "socket"})
        for name in ["run", "extract", "api", "credentials", "MODEL"]:
            self.assertFalse(hasattr(build, name))

    def test_direct_authorship_and_conflict_not_promoted(self):
        records, _ = build.collect(build.read(build.BASE / "manifest.json"))
        self.assertGreater(len(records), 0)
        self.assertTrue(all(r["producer"]["method"] == "direct_source_reading" for r in records))
        self.assertTrue(all(r["producer"]["agent"] == "Codex" for r in records))
        conflict = next(r for r in records if r["id"] == "GYS-Q007")
        self.assertEqual("needs_review", conflict["review"]["source_fidelity"])
        self.assertEqual("not_approved", conflict["review"]["generation"])

    def test_unresolved_page_cannot_be_complete(self):
        original = build.BASE
        bundle = build.read(original / "authored/namu_interrogatives_01.json")
        bundle["coverage"][2]["status"] = "draft_complete"
        with tempfile.TemporaryDirectory(dir=original) as folder:
            base = Path(folder)
            (base / "authored").mkdir()
            (base / "authored/test.json").write_text(json.dumps(bundle))
            (base / "analysis_contract.json").write_text((original / "analysis_contract.json").read_text())
            with patch.object(build, "BASE", base), self.assertRaises(ValueError):
                build.collect(build.read(original / "manifest.json"))

    def test_two_documents_share_function_without_scope_merging(self):
        records, _ = build.collect(build.read(build.BASE / "manifest.json"))
        result = build.graph(records, build.sources())
        record_sources = {r["id"]: r["source_id"] for r in records}
        linked_sources = {record_sources[e["properties"]["record_id"]] for e in result["edges"]
                          if e["type"] == "realizes" and e["target"] == "concept:INTERROGATIVE"}
        self.assertGreaterEqual(len(linked_sources), 2)
        restriction = next(r for r in records if r["id"] == "GYS-H002")
        self.assertEqual(["부산 일부 지역"], restriction["knowledge"]["scope"]["region"]["values"])
        self.assertEqual("not_approved", restriction["review"]["generation"])

    def test_check_is_read_only(self):
        names = ["records.jsonl", "grammar.graph.json", "progress.json", "gaps.json", "analysis_links.json", "example_review.md"]
        before = {name: (build.BASE / name).read_bytes() for name in names}
        build.check(build.read(build.BASE / "manifest.json"))
        self.assertEqual(before, {name: (build.BASE / name).read_bytes() for name in names})

if __name__ == "__main__":
    unittest.main()

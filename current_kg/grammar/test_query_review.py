"""Bounded graph-review checks, not independent linguistic certification.

Expected HAGECHE polar/content distinctions: honorific PDF p19; yo composition:
p34 note 67. Values were hand-specified after source reading, not inferred by
the query output. The same author wrote data and tests; no independent gold.
"""
import copy
import json
import unittest
from pathlib import Path
from query_review import assess, review


class QueryReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = json.loads((Path(__file__).parent / "grammar.graph.json").read_text())

    def run_query(self, question="content", level="HAGECHE", graph=None):
        known = {"sentence_type": "interrogative", "question_type": question}
        if level is not None:
            known["speech_level"] = level
        result = review(self.graph if graph is None else graph,
                       "concept:" + ("CONTENT_QUESTION" if question == "content" else "POLAR_QUESTION"), known)
        return {c["record_id"]: c for c in result["candidates"]}

    def test_hage_content_follows_variant_and_qualification(self):
        found = self.run_query()["GYS-H004"]
        self.assertEqual("match", found["condition_assessment"]["status"])
        self.assertEqual(["-(느)ㄴ공"], [v["form"] for v in found["variants"]])
        related = {x["record"]["id"]: x for x in found["related_knowledge"]}
        self.assertEqual({"GYS-Q013", "GYS-H005"}, set(related))
        combination = related["GYS-H005"]
        self.assertEqual(1, len(combination["construction_paths"]))
        self.assertEqual({"combines_with", "has_surface_form", "has_interpretation"},
                         {e["type"] for e in combination["semantic_triples"]})
        self.assertEqual(34, combination["evidence_locations"][0]["properties"]["page"])
        # Both documents remain traceable; same lineage is not independent corroboration.
        source_ids = {x["id"] for r in [found["knowledge"], related["GYS-Q013"]]
                      for x in r["sources"]}
        self.assertEqual({"source:NAMU_GRAMMAR_20260908", "source:NAMU_HONORIFICS_20260908"}, source_ids)

    def test_polar_question_does_not_return_content_use(self):
        found = self.run_query(question="polar")
        self.assertIn("GYS-H003", found)
        self.assertNotIn("GYS-H004", found)
        self.assertEqual("-(느)ㄴ가", found["GYS-H003"]["form"])

    def test_missing_level_is_unknown_not_permission(self):
        self.assertEqual("unknown", self.run_query(level=None)["GYS-H004"]["condition_assessment"]["status"])

    def test_different_level_conflicts_only_with_base_use(self):
        self.assertEqual("mismatch", self.run_query(level="HAECHE")["GYS-H004"]["condition_assessment"]["status"])

    def test_removing_function_edge_changes_retrieval(self):
        graph = copy.deepcopy(self.graph)
        graph["edges"] = [e for e in graph["edges"] if not (
            e["source"] == "GYS-H004:F1" and e["type"] == "realizes")]
        self.assertNotIn("GYS-H004", self.run_query(graph=graph))

    def test_removing_qualification_loses_composition(self):
        graph = copy.deepcopy(self.graph)
        graph["edges"] = [e for e in graph["edges"] if not (
            e["source"] == "GYS-H005" and e["type"] == "qualifies")]
        found = self.run_query(graph=graph)["GYS-H004"]
        self.assertNotIn("GYS-H005", {x["record"]["id"] for x in found["related_knowledge"]})

    def test_missing_condition_edge_is_not_unrestricted(self):
        graph = copy.deepcopy(self.graph)
        graph["edges"] = [e for e in graph["edges"] if not (
            e["source"] == "GYS-H004:A1" and e["type"] == "requires_all")]
        self.assertEqual("invalid_graph", self.run_query(graph=graph)["GYS-H004"]["condition_assessment"]["status"])

    def test_removing_combination_breaks_semantic_path_not_record_link(self):
        graph = copy.deepcopy(self.graph)
        graph["edges"] = [e for e in graph["edges"] if not (
            e["source"] == "GYS-H005:F1" and e["type"] == "combines_with")]
        found = self.run_query(graph=graph)["GYS-H004"]
        packet = next(x for x in found["related_knowledge"] if x["record"]["id"] == "GYS-H005")
        self.assertEqual([], packet["construction_paths"])

    def test_unsupported_operator_is_unknown(self):
        conditions = {"all": [{"field": "stem_length", "operator": "at_least", "values": ["2"]}], "any": []}
        self.assertEqual("unknown", assess(conditions, {"stem_length": "3"})["status"])


if __name__ == "__main__":
    unittest.main()

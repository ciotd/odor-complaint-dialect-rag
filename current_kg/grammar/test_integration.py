"""Implementation checks; not independent linguistic judgments."""
import copy
import unittest
import build
import integration_review


class IntegrationChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = build.read(build.BASE / "manifest.json")
        cls.records, _ = build.collect(cls.manifest)
        cls.graph = build.graph(cls.records, build.sources())
        build.integrate(cls.graph, cls.records)

    def test_all_grammar_sources_have_authored_records(self):
        self.assertEqual(set(build.ORDER), {r["source_id"] for r in self.records})

    def test_methodology_not_dialect_evidence(self):
        self.assertFalse(any(r["source_id"] == "SONG2025_SEJONG" for r in self.records))

    def test_whole_page_inventory_without_gaps_or_duplicates(self):
        registry = build.read(build.ROOT / "current_kg/grammar/source_registry.json")
        sizes = {s["source_id"]: s["file"]["pages"] for s in registry["sources"]}
        inventory = build.read(build.BASE / "integration.json")["processing_inventory"]
        for source in inventory["sources"]:
            pages = [p for section in source["sections"] for p in range(section["pages"][0], section["pages"][1] + 1)]
            self.assertEqual(list(range(1, sizes[source["source_id"]] + 1)), pages)
            self.assertTrue(all(section["writing_status"] != "complete" for section in source["sections"]))

    def test_cross_source_inflection_paths_exist(self):
        result = integration_review.review(self.graph, "GYS-R011:F1", ["has_inflection_description", "has_surface_form"])
        self.assertEqual(12, len(result["paths"]))
        for path in result["paths"]:
            self.assertEqual({"RYU2014", "NAMU_GRAMMAR_20260908"}, {e["properties"]["source_id"] for e in path["evidence"]})
            self.assertFalse(path["operational"])

    def test_removing_integration_edge_breaks_paths(self):
        graph = copy.deepcopy(self.graph)
        graph["edges"] = [e for e in graph["edges"] if e["properties"].get("integration_id") != "INT001"]
        result = integration_review.review(graph, "GYS-R011:F1", ["has_inflection_description", "has_surface_form"])
        self.assertEqual([], result["paths"])

    def test_removing_surface_edges_breaks_second_step(self):
        graph = copy.deepcopy(self.graph)
        graph["edges"] = [e for e in graph["edges"] if not (e["source"] == "GYS-I020:F1" and e["type"] == "has_surface_form")]
        self.assertEqual([], integration_review.review(graph, "GYS-R011:F1", ["has_inflection_description", "has_surface_form"])["paths"])

    def test_scope_tension_not_allowed_path(self):
        result = integration_review.review(self.graph, "GYS-G001:F1", ["scope_tension_with"])
        self.assertEqual([], result["paths"])
        self.assertEqual(1, len(result["held_edges"]))

    def test_negative_function_is_explicit_not_positive_interpretation(self):
        row = next(r for r in self.records if r["id"] == "GYS-Y012")
        self.assertEqual("excludes_function", row["knowledge"]["relations"][0]["predicate"])

    def test_market_example_not_required_place(self):
        row = next(r for r in self.records if r["id"] == "GYS-H001")
        conditions = row["knowledge"]["relations"][0]["conditions"]["all"]
        self.assertEqual(["informal_friendly"], next(c["values"] for c in conditions if c["field"] == "register"))

    def test_integration_not_automatic_equivalence(self):
        links = [e for e in self.graph["edges"] if "integration_id" in e["properties"]]
        declared = build.read(build.BASE / "integration.json")["links"]
        self.assertEqual(len(declared), len(links))
        self.assertGreaterEqual(len(links), 50)
        self.assertTrue(all(not e["properties"]["equivalence_asserted"] for e in links))

    def test_unresolved_record_not_accepted_as_path(self):
        result = integration_review.review(self.graph, "GYS-H019:F1", ["same_usage_candidate"])
        self.assertEqual([], result["paths"])
        self.assertTrue(result["held_edges"])

    def test_request_to_inflection_cross_document_path(self):
        result = integration_review.review(self.graph, "GYS-J031:F1", ["has_inflection_description", "has_surface_form"])
        self.assertTrue(result["paths"])
        self.assertTrue(all(not p["operational"] for p in result["paths"]))

    def test_removed_request_link_breaks_path(self):
        graph = copy.deepcopy(self.graph)
        graph["edges"] = [e for e in graph["edges"] if e["properties"].get("integration_id") != "INT035"]
        self.assertEqual([], integration_review.review(graph, "GYS-J031:F1", ["has_inflection_description", "has_surface_form"])["paths"])

    def test_homograph_usage_nodes_are_separate(self):
        record = next(r for r in self.records if r["id"] == "GYS-G061")
        forms = record["knowledge"]["forms"]
        self.assertEqual(forms[0]["text"], forms[1]["text"])
        self.assertNotEqual(forms[0]["sense"], forms[1]["sense"])
        relations = record["knowledge"]["relations"]
        self.assertTrue(any(r["predicate"] == "contrasts_with" for r in relations))

    def test_unseen_topics_not_turned_into_prohibition(self):
        row = next(r for r in self.records if r["id"] == "GYS-R060")
        self.assertEqual("needs_review", row["review"]["source_fidelity"])
        self.assertFalse(any(r["predicate"].startswith("excludes_") for r in row["knowledge"]["relations"]))

    def test_nominal_future_has_explicit_components(self):
        row = next(r for r in self.records if r["id"] == "GYS-J055")
        relations = row["knowledge"]["relations"]
        self.assertEqual(4, sum(r["predicate"] == "combines_with" for r in relations))

    def test_ra_content_question_exception_is_example_not_global_rule(self):
        row = next(r for r in self.records if r["id"] == "GYS-J061")
        exceptions = [r for r in row["knowledge"]["relations"] if r["subject"] == "F1" and r["object"]["ref"] == "CONTENT_QUESTION"]
        self.assertEqual(1, len(exceptions))
        self.assertEqual("example_only", exceptions[0]["assertion_mode"])

    def test_triple_export_has_only_semantic_or_integration_rows(self):
        rows = build.render_triples(self.graph).splitlines()
        expected = sum("assertion_id" in e["properties"] or "integration_id" in e["properties"] for e in self.graph["edges"])
        self.assertEqual(expected + 1, len(rows))


if __name__ == "__main__":
    unittest.main()

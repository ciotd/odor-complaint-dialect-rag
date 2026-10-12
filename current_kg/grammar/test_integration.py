"""Implementation checks; not independent linguistic judgments."""
import copy
import unittest
import build
import integration_review
import authoring_audit


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

    def test_ending_audit_covers_inventory_and_preserves_interpretation_distinction(self):
        result = authoring_audit.audit_ending_connections(self.records, self.graph)
        self.assertEqual(len(self.records), len(result["records"]))
        self.assertEqual({r["id"] for r in self.records}, {r["record_id"] for r in result["records"]})
        row = next(r for r in result["records"] if r["record_id"] == "GYS-H005")
        self.assertTrue(row["realizes_assertions"])
        self.assertTrue(row["interpretation_assertions"])
        self.assertTrue(all(not v for v in result["whole_graph_integrity"].values()))

    def test_ending_audit_detects_removed_condition_edge(self):
        graph = copy.deepcopy(self.graph)
        graph["edges"] = [e for e in graph["edges"] if not
                          (e["source"] == "GYS-Q002:A1" and e["type"] == "requires_all")]
        result = authoring_audit.audit_ending_connections(self.records, graph)
        self.assertIn({"assertion_id": "GYS-Q002:A1", "mode": "all"},
                      result["whole_graph_integrity"]["condition_edge_mismatches"])

    def test_ending_audit_does_not_count_metadata_as_semantic_connection(self):
        graph = copy.deepcopy(self.graph)
        form = "GYS-Q002:F1"
        graph["edges"] = [e for e in graph["edges"] if not
                          (form in (e["source"], e["target"]) and
                           ("assertion_id" in e["properties"] or "integration_id" in e["properties"]))]
        result = authoring_audit.audit_ending_connections(self.records, graph)
        row = next(r for r in result["records"] if r["record_id"] == "GYS-Q002")
        self.assertIn(form, {f["id"] for f in row["unconnected_forms"]})
        self.assertNotIn(form, result["whole_graph_integrity"]["isolated_node_ids"])

    def test_work_queue_covers_all_selected_records_without_false_completion(self):
        result = authoring_audit.audit_ending_connections(self.records, self.graph)
        selected = [r for r in result['records'] if r['tier'] != 'outside_selected_scope']
        # Three source-table quotation records were added on 2026-10-08.
        self.assertEqual(277, len(selected))
        self.assertTrue({'GYS-G072', 'GYS-G073', 'GYS-G074'} <= {r['record_id'] for r in selected})
        self.assertTrue(all(r['condition_work']['next_actions'] for r in selected))
        self.assertTrue(all(r['condition_work']['exception_coverage']=='not_exhaustively_reviewed' for r in selected))
        self.assertTrue(all(not r['condition_work']['no_known_restriction_asserted'] for r in selected))
        # Fully bound data may still contain unstructured meaning conditions.
        self.assertTrue(any(r['condition_work']['pending_semantic_conditions'] and
                            not r['condition_work']['pending_feature_bindings'] for r in selected))

    def test_ending_audit_detects_missing_endpoint_and_evidence(self):
        graph = copy.deepcopy(self.graph)
        graph["edges"][0]["target"] = "missing:node"
        assertion = next(n for n in graph["nodes"] if n["id"] == "GYS-Q002:A1")
        assertion["properties"]["evidence_ids"] = ["missing:evidence"]
        result = authoring_audit.audit_ending_connections(self.records, graph)
        self.assertIn(graph["edges"][0]["id"], result["whole_graph_integrity"]["dangling_edges"])
        self.assertIn({"assertion_id": "GYS-Q002:A1", "relation": "evidence_ids"},
                      result["whole_graph_integrity"]["assertion_link_errors"])

    def test_function_repair_preserves_composed_question_and_restricted_intention(self):
        semantics = [e for e in self.graph["edges"] if "assertion_id" in e["properties"]]
        h5 = [e for e in semantics if e["properties"]["record_id"] == "GYS-H005" and e["type"] == "realizes"]
        self.assertEqual(["GYS-H005:F3"], [e["source"] for e in h5])
        y10 = next(e for e in semantics if e["source"] == "GYS-Y010:F1" and e["target"] == "concept:INTERROGATIVE")
        fields = {c['field']: c['values'] for c in y10['properties']['conditions']['all']}
        self.assertEqual(['ask_intention'], fields['speech_act'])
        self.assertEqual(['addressee'], fields['intention_holder'])

    def test_new_imperative_forms_are_not_lemmas_or_generalized_examples(self):
        semantics = [e for e in self.graph["edges"] if "assertion_id" in e["properties"]]
        uses = [e for e in semantics if e["properties"]["record_id"] == "GYS-I050" and e["type"] == "realizes"]
        self.assertEqual(11, len(uses))
        self.assertFalse({e["source"] for e in uses} & {"GYS-I050:F" + str(i) for i in range(1,5)})
        example = next(e for e in semantics if e["source"] == "GYS-R023:F2" and e["target"] == "concept:IMPERATIVE")
        self.assertEqual("example_only", example["properties"]["assertion_mode"])

    def test_function_review_does_not_turn_negative_or_ambiguous_guidance_into_permission(self):
        review = build.read(build.BASE / "integration.json")["function_route_review"]
        rows = {r["record_id"]:r for r in review["decisions"]}
        self.assertEqual("negative_constraint",rows["GYS-Y012"]["decision"])
        self.assertFalse(rows["GYS-Q011"]["assertions"])
        self.assertFalse(rows["GYS-Q009"]["assertions"])
        semantic_ids = {e["properties"]["assertion_id"] for e in self.graph["edges"] if "assertion_id" in e["properties"]}
        self.assertTrue({aid for r in rows.values() for aid in r["assertions"]} <= semantic_ids)

    def test_triple_export_has_only_semantic_or_integration_rows(self):
        rows = build.render_triples(self.graph).splitlines()
        expected = sum("assertion_id" in e["properties"] or "integration_id" in e["properties"] for e in self.graph["edges"])
        self.assertEqual(expected + 1, len(rows))


if __name__ == "__main__":
    unittest.main()

"""Bounded graph-review checks, not independent linguistic certification.

Expected HAGECHE polar/content distinctions: honorific PDF p19; yo composition:
p34 note 67. Values were hand-specified after source reading, not inferred by
the query output. The same author wrote data and tests; no independent gold.
"""
import copy
import json
import unittest
from pathlib import Path
from query_review import assess, review, inspect_conditions


class QueryReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = json.loads((Path(__file__).parent / "grammar.graph.json").read_text())

    def run_query(self, question="content", level="HAGECHE", graph=None):
        known = {"sentence_type": "interrogative", "question_type": question}
        target = {"speech_level": level} if level is not None else {}
        result = review(self.graph if graph is None else graph,
                       "concept:" + ("CONTENT_QUESTION" if question == "content" else "POLAR_QUESTION"), known,
                       target_features=target)
        return {c["record_id"]: c for c in result["candidates"]}

    def test_hage_content_follows_variant_and_qualification(self):
        found = self.run_query()["GYS-H004"]
        self.assertEqual("match", found["condition_assessment"]["status"])
        self.assertEqual(["-(느)ㄴ공"], [v["form"] for v in found["variants"]])
        related = {x["record"]["id"]: x for x in found["related_knowledge"]}
        self.assertEqual({"GYS-Q013", "GYS-H005"}, set(related))
        combination = related["GYS-H005"]
        self.assertEqual(1, len(combination["construction_paths"]))
        self.assertEqual({"combines_with", "has_surface_form", "has_interpretation", "realizes"},
                         {e["type"] for e in combination["semantic_triples"]})
        self.assertIn(34, {e["properties"]["page"] for e in combination["evidence_locations"]})
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

    def test_nider_basic_distribution_and_lexical_exception(self):
        values = {"host_form":"맑다","host_pos":"adjective","sentence_type":"declarative"}
        r = inspect_conditions(self.graph,"GYS-H022:F1",values,{"attachment_coda":"present"},{"addressee_treatment":"very_high"})
        self.assertTrue(all(x["assessment"]["status"]=="match" for x in r["base_assertions"]))
        self.assertEqual(["GYS-H023:A7"],r["matched_explicit_exclusions"])
        values["host_form"]="부르다"
        r = inspect_conditions(self.graph,"GYS-H022:F1",values,{"attachment_coda":"absent"},{"addressee_treatment":"very_high"})
        self.assertTrue(all(x["assessment"]["status"]=="mismatch" for x in r["base_assertions"]))
        values["host_pos"]="verb"
        r = inspect_conditions(self.graph,"GYS-H022:F1",values,{"attachment_coda":"absent"},{"addressee_treatment":"very_high"})
        self.assertTrue(all(x["assessment"]["status"]=="match" for x in r["base_assertions"]))


    def test_se_directive_requires_addressee_action_not_joint_action(self):
        values = {'sentence_type':'imperative', 'host_pos':'verb', 'action_participants':'addressee_only'}
        candidate = {'preceding_form':'verb_stem_direct'}
        a = inspect_conditions(self.graph, 'GYS-J029:F1', values, candidate)
        self.assertEqual('match', a['base_assertions'][0]['assessment']['status'])
        values['action_participants'] = 'speaker_and_addressee'
        a = inspect_conditions(self.graph, 'GYS-J029:F1', values, candidate)
        self.assertEqual('mismatch', a['base_assertions'][0]['assessment']['status'])

    def test_onna_is_not_generalized_to_unrelated_verb(self):
        a = inspect_conditions(self.graph, 'GYS-J032:F1', {'sentence_type':'imperative','host_form':'먹다'})
        self.assertEqual('mismatch', a['base_assertions'][0]['assessment']['status'])

    def test_georo_exclusion_is_retrieved_even_after_base_mismatch(self):
        a = inspect_conditions(self.graph, 'GYS-Y010:F1', {'sentence_type':'interrogative','speech_act':'guess_answer'})
        self.assertEqual(['GYS-Y012:A1'], a['matched_explicit_exclusions'])
        self.assertTrue(all(x['assessment']['status']=='mismatch' for x in a['base_assertions']))
        graph = copy.deepcopy(self.graph)
        graph['edges'] = [e for e in graph['edges'] if not (e['source']=='GYS-Y010:F1'
                          and e['target']=='GYS-Y012:A1' and e['type']=='has_applicability_constraint')]
        self.assertEqual([], inspect_conditions(graph, 'GYS-Y010:F1',
            {'sentence_type':'interrogative','speech_act':'guess_answer'})['matched_explicit_exclusions'])

    def test_request_function_and_candidate_stem_are_separate(self):
        values = {'speech_act':'request','beneficiary':'speaker','preceding_form':'도-'}
        a = inspect_conditions(self.graph, 'GYS-J031:F1', values)
        self.assertTrue(all(x['assessment']['status']=='unknown' for x in a['base_assertions']))
        a = inspect_conditions(self.graph, 'GYS-J031:F1', values, {'preceding_form':'도-'})
        self.assertTrue(all(x['assessment']['status']=='match' for x in a['base_assertions']))
        found = review(self.graph, 'concept:REQUEST', values, {'preceding_form':'도-'})
        self.assertIn('GYS-J031', {r['record_id'] for r in found['candidates']})

    def test_target_level_not_read_from_input_after_migration(self):
        values = {'sentence_type':'declarative', 'speech_level':'HAISOCHE'}
        a = inspect_conditions(self.graph, 'GYS-H014:F1', values)
        self.assertEqual('unknown', a['base_assertions'][0]['assessment']['status'])
        a = inspect_conditions(self.graph, 'GYS-H014:F1', values, target_features={'speech_level':'HAISOCHE'})
        self.assertEqual('match', a['base_assertions'][0]['assessment']['status'])

    def test_western_hasoche_rieul_is_not_other_consonant(self):
        values = {'sentence_type':'declarative'}
        candidate = {'attachment_coda_class':'rieul_final'}
        target = {'speech_level':'HASOCHE','region':'경북 서부'}
        yo = inspect_conditions(self.graph, 'GYS-H018:A1', values, candidate, target)
        so = inspect_conditions(self.graph, 'GYS-H018:A2', values, candidate, target)
        self.assertEqual('match', yo['base_assertions'][0]['assessment']['status'])
        self.assertEqual('mismatch', so['base_assertions'][0]['assessment']['status'])
        unknown = inspect_conditions(self.graph, 'GYS-H018:A1', values, {}, target)
        self.assertEqual('unknown', unknown['base_assertions'][0]['assessment']['status'])

    def test_nengyo_formal_restriction_is_reachable(self):
        a = inspect_conditions(self.graph, 'GYS-H019:F1',
            {'sentence_type':'interrogative','host_pos':'verb'},
            target_features={'speech_level':'HAISOCHE','region':'부산','register':'formal'})
        self.assertIn('GYS-H002:A1', a['matched_explicit_exclusions'])

    def test_clause_relation_and_self_question_are_not_interchangeable(self):
        a = inspect_conditions(self.graph, 'GYS-R005:F1', {'clause_relation':'cause'})
        self.assertEqual('mismatch', a['base_assertions'][0]['assessment']['status'])
        a = inspect_conditions(self.graph, 'GYS-Q012:A4',
            {'question_type':'content','sentence_type':'interrogative','response_orientation':'addressee'})
        self.assertEqual('mismatch', a['base_assertions'][0]['assessment']['status'])

    def test_existential_footnote_survives_verb_condition_mismatch(self):
        a = inspect_conditions(self.graph, 'GYS-J034:F1', {'sentence_type':'hortative',
            'host_pos':'adjective','host_form':'있다','action_participants':'speaker_and_addressee'},
            {'prefinal_profile':'none'})
        own = {x['assertion_id']:x['assessment']['status'] for x in a['base_assertions']}
        self.assertEqual('mismatch', own['GYS-J034:A1'])
        self.assertEqual('match', own['GYS-J034:A3'])
        self.assertFalse(a['generation_approved'])

    def test_exception_still_visible_when_basic_distribution_mismatches(self):
        r = inspect_conditions(self.graph,"GYS-H022:F2",{"host_form":"좋다","host_pos":"adjective","sentence_type":"declarative"},{"attachment_coda":"present"})
        matched = {a["assertion_id"] for ref in r["references"] for a in ref["assertions"] if a["assessment"]["status"]=="match"}
        self.assertIn("GYS-H023:A4",matched)
        self.assertEqual("mismatch",r["base_assertions"][0]["assessment"]["status"])

    def test_yo_suffix_and_target_level_have_separate_providers(self):
        inp={"sentence_type":"interrogative","question_type":"content","following_form":"요"}
        r=inspect_conditions(self.graph,"GYS-H005:F3",inp,{}, {"speech_level":"HAEYO_LEVEL"})
        self.assertTrue(all(a["assessment"]["status"]=="unknown" for a in r["base_assertions"]))
        r=inspect_conditions(self.graph,"GYS-H005:F3",inp,{"following_form":"요"},{"speech_level":"HAEYO_LEVEL"})
        self.assertTrue(all(a["assessment"]["status"]=="match" for a in r["base_assertions"]))
        self.assertTrue(r["references"])
        self.assertTrue(all(ref["condition_inheritance"] is False for ref in r["references"]))
        r=inspect_conditions(self.graph,"GYS-H005:F3",inp,{"following_form":"요"},{"speech_level":"HAGECHE"})
        self.assertEqual("mismatch",next(a for a in r["base_assertions"] if a["predicate"]=="realizes")["assessment"]["status"])

    def test_past_change_and_si_conflict_are_reachable_from_base(self):
        r=inspect_conditions(self.graph,"GYS-Q003:A1",{"question_type":"polar","host_class":"nominal_copula","nominal_coda":"present"},{"prefinal_profile":"switching_prefinal_present"},{"speech_level":"HAERACHE"})
        self.assertEqual("mismatch",r["base_assertions"][0]["assessment"]["status"])
        other={a["assertion_id"]:a for ref in r["references"] for a in ref["assertions"]}
        self.assertEqual("match",other["GYS-Q006:A1"]["assessment"]["status"])
        self.assertIn("GYS-Q007:A1",r["held_assertions"])

    def test_removing_exception_link_loses_exclusion_and_missing_conditions_raise(self):
        g=copy.deepcopy(self.graph)
        g["edges"]=[e for e in g["edges"] if not(e["source"]=="GYS-H022:F1" and e["target"]=="GYS-H023:A7")]
        r=inspect_conditions(g,"GYS-H022:F1",{"host_form":"맑다","host_pos":"adjective"},{"attachment_coda":"present"})
        self.assertFalse(r["matched_explicit_exclusions"])
        g=copy.deepcopy(self.graph)
        g["edges"]=[e for e in g["edges"] if not(e["source"]=="GYS-H023:A7" and e["type"]=="requires_all")]
        with self.assertRaises(ValueError):inspect_conditions(g,"GYS-H022:F1",{})

    def test_unsupported_operator_is_unknown(self):
        conditions = {"all": [{"field": "stem_length", "operator": "at_least", "values": ["2"]}], "any": []}
        self.assertEqual("unknown", assess(conditions, {"stem_length": "3"})["status"])


if __name__ == "__main__":
    unittest.main()

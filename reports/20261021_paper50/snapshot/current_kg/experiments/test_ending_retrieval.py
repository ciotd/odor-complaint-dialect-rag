"""Regression tests for lossless diagnostic retrieval, not dialect accuracy."""
import copy
import json
from pathlib import Path
import unittest
from review_ending_retrieval import review

BASE=Path(__file__).resolve().parent


class EndingRetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph=json.loads((BASE.parent/'grammar/grammar.graph.json').read_text())
        cls.items=json.loads((BASE/'inputs/ending_review.inputs.json').read_text())['items']

    def candidates(self, graph=None, item=None):
        result=review(graph or self.graph, item or self.items[1])
        return {c['assertion_id']:c for c in result['clauses'][0]['candidates']}

    def test_unknown_style_is_visible_and_scenarios_are_not_approval(self):
        c=self.candidates()['GYS-Q002:A1']
        self.assertEqual(c['assessment']['status'],'unknown')
        scenarios={s['speech_level']:s for s in c['style_scenarios']}
        self.assertEqual(scenarios['HAERACHE']['assessment']['status'],'match')
        self.assertFalse(scenarios['HAERACHE']['target_style_confirmed'])
        self.assertFalse(c['generation_approved'])

    def test_repaired_question_function_and_pos_mismatch(self):
        cs=self.candidates()
        self.assertEqual(cs['GYS-H019:A4']['assessment']['status'],'match')
        self.assertEqual(cs['GYS-H019:A5']['assessment']['status'],'mismatch')
        self.assertIn('record_gaps_require_review',cs['GYS-H019:A4']['unresolved_or_exclusion_reasons'])

    def test_missing_condition_edge_is_corruption_not_unrestricted_use(self):
        graph=copy.deepcopy(self.graph)
        graph['edges']=[e for e in graph['edges'] if not
                        (e['source']=='GYS-Q002:A1' and e['type']=='requires_all')]
        c=self.candidates(graph)['GYS-Q002:A1']
        self.assertEqual(c['assessment']['status'],'invalid_graph')
        self.assertEqual(c['decision'],'invalid_graph')

    def test_sentence_id_does_not_select_knowledge(self):
        item=copy.deepcopy(self.items[1]); item['id']='UNSEEN'
        self.assertEqual(self.candidates(item=item),self.candidates())

    def test_input_speech_level_cannot_silently_set_target(self):
        item=copy.deepcopy(self.items[1]); item['clauses'][0]['features']['speech_level']='HAERACHE'
        with self.assertRaises(ValueError): review(self.graph,item)

    def test_source_conflict_is_not_hidden_by_condition_match(self):
        c=self.candidates()['GYS-Q016:A1']
        self.assertIn('source_review_unresolved',c['unresolved_or_exclusion_reasons'])
        self.assertFalse(c['generation_approved'])

    def test_reverse_audit_does_not_call_other_question_subtype_missing(self):
        clause=review(self.graph,self.items[0])['clauses'][0]
        missing=clause['function_classified_records_without_realizes_path']
        self.assertNotIn('GYS-Q002',missing)
        self.assertIn('GYS-Q011',missing)

    def test_wrong_clause_span_rejected(self):
        item=copy.deepcopy(self.items[1]); item['clauses'][0]['span']=[0,1]
        with self.assertRaises(ValueError): review(self.graph,item)


if __name__=='__main__': unittest.main()

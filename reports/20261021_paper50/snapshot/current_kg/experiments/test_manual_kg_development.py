"""Manual-analysis retrieval regressions, not linguistic quality scores."""
import copy
import json
from pathlib import Path
import unittest
from run_manual_kg_development import retrieve
B=Path(__file__).parent

class ManualRetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph=json.loads((B.parent/'grammar/grammar.graph.json').read_text())
        cls.analysis=json.loads((B/'inputs/development_30.manual_analysis.json').read_text())
    def subset(self, number):
        a=copy.deepcopy(self.analysis);a['items']=[a['items'][number-1]];return a
    def test_sentence_id_does_not_pick_rules(self):
        a=self.subset(12);before=retrieve(self.graph,a)[0]['clauses'][0]['selected_assertion_ids']
        a['items'][0]['id']='UNSEEN'
        self.assertEqual(before,retrieve(self.graph,a)[0]['clauses'][0]['selected_assertion_ids'])
        self.assertTrue(before)
    def test_removing_function_route_removes_knowledge(self):
        g=copy.deepcopy(self.graph)
        g['edges']=[e for e in g['edges'] if e['properties'].get('assertion_id')!='GYS-Q002:A1']
        x=retrieve(g,self.subset(12))[0]['clauses'][0]['selected_assertion_ids']
        self.assertNotIn('GYS-Q002:A1',x)
    def test_request_question_is_not_treated_as_information_question(self):
        item=retrieve(self.graph,self.subset(18))[0]
        self.assertEqual([],item['clauses'][0]['selected_assertion_ids'])
        self.assertIn('question_function_alone_does_not_establish_request_usage',
            {r for c in item['clauses'][0]['candidates'] for s in c['scenarios'] for r in s['reasons']})
    def test_wrong_span_fails(self):
        a=self.subset(1);a['items'][0]['clauses'][0]['span']=[0,1]
        with self.assertRaises(ValueError):retrieve(self.graph,a)
    def test_cause_clause_uses_connective_slot(self):
        item=retrieve(self.graph,self.subset(8))[0]
        cause=next(c for c in item['clauses'] if c['analysis']['role']=='connective')
        self.assertIn('GYS-R047:A1',cause['selected_assertion_ids'])
        self.assertNotIn('GYS-H014:A1',cause['selected_assertion_ids'])
    def test_missing_target_style_does_not_become_permission(self):
        a=self.subset(12);a['items'][0]['clauses'][0]['target_scenarios']=[{}]
        with self.assertRaisesRegex(ValueError, 'legacy targets conflict'):
            retrieve(self.graph,a)

if __name__=='__main__':unittest.main()

"""Offline checks for this development experiment, not linguistic validation."""
import copy
import json
from pathlib import Path
import unittest

from build_development_kg_packets import build_packets
from run_seeded_kg import payload, check_response

BASE = Path(__file__).resolve().parent


class SeededKGTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = json.loads((BASE.parent / 'grammar/grammar.graph.json').read_text())
        cls.plan = json.loads((BASE / 'archive/legacy_development/development_30.kg_plan.json').read_text())
        cls.config = json.loads((BASE / 'inputs/development_30.config.json').read_text())

    def test_paired_request_only_differs_in_user_context(self):
        a = payload(self.config, '시간 괜찮으면 같이 점심 먹자.', 20260923)
        b = payload(self.config, '시간 괜찮으면 같이 점심 먹자.', 20260923, {'assertions': []})
        self.assertEqual(a['messages'][0], b['messages'][0])
        self.assertEqual({k:v for k,v in a.items() if k!='messages'},
                         {k:v for k,v in b.items() if k!='messages'})
        self.assertNotEqual(a['messages'][1], b['messages'][1])

    def test_unknown_conditions_and_needs_review_are_held(self):
        items = {x['id']:x for x in build_packets(self.graph,self.plan)}
        self.assertNotIn('GYS-Q001:A1', [a['assertion_id'] for a in items['DEV011']['prompt_packet']['assertions']])
        self.assertIn('GYS-Q001:A1', [a['assertion_id'] for a in items['DEV011']['held']])
        self.assertNotIn('GYS-Q011:A1', [a['assertion_id'] for a in items['DEV013']['prompt_packet']['assertions']])
        self.assertIn('GYS-Q011:A1', [a['assertion_id'] for a in items['DEV013']['held']])

    def test_missing_condition_edge_is_an_error(self):
        graph = copy.deepcopy(self.graph)
        graph['edges'] = [e for e in graph['edges'] if not (e['source']=='GYS-H028:A1' and e['type']=='requires_all')]
        with self.assertRaises(ValueError):
            build_packets(graph, self.plan)

    def test_integration_edge_removal_removes_linked_evidence(self):
        graph = copy.deepcopy(self.graph)
        # The historical plan has only the former free-text meaning annotation.
        # It must now hold the linked condition record until clause_relation is supplied.
        legacy = {x['id']:x for x in build_packets(graph,self.plan)}['DEV022']
        self.assertNotIn('GYS-R005:A1', [a['assertion_id'] for a in legacy['prompt_packet']['assertions']])
        plan = self.condition_plan()
        original = {x['id']:x for x in build_packets(graph,plan)}['DEV022']
        self.assertIn('GYS-R005:A1',[a['assertion_id'] for a in original['prompt_packet']['assertions']])
        graph['edges'] = [e for e in graph['edges'] if e['properties'].get('integration_id')!='INT018']
        changed = {x['id']:x for x in build_packets(graph,plan)}['DEV022']
        self.assertNotIn('GYS-R005:A1',[a['assertion_id'] for a in changed['prompt_packet']['assertions']])

    def test_linked_review_state_prevents_injection(self):
        graph = copy.deepcopy(self.graph)
        next(n for n in graph['nodes'] if n['id']=='GYS-R005')['properties']['review']['source_fidelity']='needs_review'
        item = {x['id']:x for x in build_packets(graph,self.condition_plan())}['DEV022']
        self.assertNotIn('GYS-R005:A1',[a['assertion_id'] for a in item['prompt_packet']['assertions']])

    def condition_plan(self):
        # Manual fixture annotation of DEV022's conditional clause, not an automatic parser
        # or a rewrite of the saved experiment plan/results.
        plan = copy.deepcopy(self.plan)
        for seed in next(x for x in plan['items'] if x['id']=='DEV022')['seeds']:
            seed['manual_known_features']['clause_relation'] = 'condition'
        return plan

    def test_wrong_model_and_truncated_output_rejected(self):
        for model,finish in [('other','stop'),('Qwen3.8-27B','length')]:
            with self.assertRaises(RuntimeError):
                check_response({'model':model,'choices':[{'finish_reason':finish,'message':{'content':'text'}}]},'Qwen3.8-27B')


if __name__ == '__main__':
    unittest.main()

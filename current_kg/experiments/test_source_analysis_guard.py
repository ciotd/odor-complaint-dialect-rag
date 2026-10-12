import copy,json,unittest
from pathlib import Path
from analysis_input import normalize_analysis
from run_manual_kg_development import retrieve
from source_analysis_guard import inspect_source,guard_analysis
B=Path(__file__).parent
class SourceGuardTests(unittest.TestCase):
    def test_polite_ending_and_contracted_past(self):
        r=inspect_source('밥을 먹었어요.','main')
        self.assertEqual('polite',r['politeness']);self.assertEqual(['-었-'],r['prefinals'])
    def test_intention_is_not_get_prefinal(self):
        for s in ['내가 할게.','도와줄래?']:
            r=inspect_source(s,'main');self.assertEqual('non_polite',r['politeness']);self.assertEqual([],r['prefinals'])
        self.assertEqual(['-겠-'],inspect_source('나는 가겠어.','main')['prefinals'])
    def test_quotes_do_not_supply_outer_politeness(self):
        r=inspect_source('그가 “오세요”라고 했어.','main')
        self.assertEqual('non_polite',r['politeness']);self.assertEqual(['-었-'],r['prefinals'])
    def test_connective_has_no_addressee_level(self):
        r=inspect_source('비가 와서','connective')
        self.assertEqual('unknown',r['politeness']);self.assertEqual([],r['prefinals'])
    def test_uncertain_and_nominal_segments_abstain(self):
        self.assertIsNone(inspect_source('그 가게','main')['prefinals'])
        self.assertIsNone(inspect_source('음식이 괜찮더라.','main')['prefinals'])
    def test_unknown_connective_retrieves_but_required_height_still_blocks(self):
        graph=json.loads((B.parent/'grammar/grammar.graph.json').read_text())
        analysis=normalize_analysis(json.loads((B/'inputs/development_30.manual_analysis.json').read_text()))
        analysis['items']=[analysis['items'][7]]
        c=next(c for c in analysis['items'][0]['clauses'] if c['role']=='connective')
        c['observed_politeness']='unknown'
        def selected(g):
            r=retrieve(g,analysis)[0]
            return next(c['selected_assertion_ids'] for c in r['clauses'] if c['analysis']['role']=='connective')
        self.assertIn('GYS-R047:A1',selected(graph))
        aid='GYS-R047:A1';condition={'field':'speech_level','operator':'is','values':['HAEYO_LEVEL'],'evidence_keys':[]}
        node=next(n for n in graph['nodes'] if n['id']==aid)
        node['properties']['conditions']['all'].append(condition)
        node['properties']['application']['feature_sources']['speech_level']='target'
        graph['nodes'].append({'id':'test:required_height','type':'Condition','properties':condition})
        graph['edges'].append({'id':'test:height_edge','source':aid,'target':'test:required_height','type':'requires_all','properties':{}})
        self.assertNotIn(aid,selected(graph))
    def test_main_unknown_height_remains_blocked(self):
        graph=json.loads((B.parent/'grammar/grammar.graph.json').read_text())
        a=normalize_analysis(json.loads((B/'inputs/development_30.manual_analysis.json').read_text()))
        a['items']=[a['items'][11]];a['items'][0]['clauses'][0]['observed_politeness']='unknown'
        self.assertEqual([],retrieve(graph,a)[0]['clauses'][0]['selected_assertion_ids'])
if __name__=='__main__':unittest.main()

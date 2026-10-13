"""Structural regressions; synthetic analyses are test fixtures, not model outputs."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from integrated_retrieval import IntegratedRetriever, GRAMMAR
from source_bindings import bind_item


class EmptySearch:
    def search_all(self, query, kind, limit=6):
        return {'hybrid': []}


class IntegratedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = json.loads((GRAMMAR/'grammar.graph.json').read_text())
        cls.engine = IntegratedRetriever(cls.graph, EmptySearch())

    def result(self, text, clauses=None, engine=None):
        return (engine or self.engine).retrieve_item({'id': 'TEST', 'input': text, 'clauses': clauses or []})

    def ids(self, result):
        return {c['id'] for c in result['packets']['graph_hybrid']['references']}

    def clause(self, text, **features):
        return {'clause_id': 'C', 'text': text, 'span': [0,len(text)], 'role': 'main',
                'features': features, 'observed_politeness': 'non_polite',
                'preserved_candidate_features': {'prefinal_profile': 'switching_prefinal_present', 'preceding_form': '-었-'}}

    def test_quote_reaches_contraction_but_lexical_past_does_not(self):
        self.assertIn('GYS-O004:A5', self.ids(self.result('동생이 온다고 했어.')))
        self.assertNotIn('GYS-O004:A5', self.ids(self.result('숙제를 했어.')))

    def test_specific_hane_not_promoted_from_generic_hada(self):
        self.assertIn('GYS-R008:A2', self.ids(self.result('동생이 온다고 하네.')))
        for text in ['동생이 온다고 했어.', '동생이 온다고 하세요.']:
            self.assertNotIn('GYS-R008:A2', self.ids(self.result(text)))

    def test_inner_command_not_outer_declarative(self):
        r = self.result('일찍 오라고 했어요.')
        self.assertNotIn('GYS-R007:A1', self.ids(r))
        self.assertTrue(any(v['features'].get('quotation_type') == 'command' for v in r['bindings']))

    def test_modifier_and_plain_go_are_not_quote_or_transition(self):
        for text in ['가는 길에 빵을 샀어.', '밥을 먹고 잤어.']:
            self.assertFalse(self.ids(self.result(text)) & {'GYS-O004:A5','GYS-R045:A1','GYS-G072:A1'})

    def test_model_unbound_quotation_feature_is_not_copied(self):
        text = '숙제를 했어.'
        c = self.clause(text, sentence_type='declarative', construction_kind='quotative_hada', source_form='-고 하-')
        r = self.result(text,[c])
        self.assertNotIn('GYS-O004:A5',self.ids(r))
        self.assertNotIn('construction_kind',r['bindings'][0]['features'])

    def test_search_only_does_not_supply_quote_conditions(self):
        class BadSearch:
            def search_all(self, *args, **kwargs):
                return {'hybrid':[{'id':'GYS-O004','score':999}]}
        e = IntegratedRetriever(self.graph, BadSearch())
        text='숙제를 했어.'
        r=self.result(text,[self.clause(text,sentence_type='declarative')],e)
        self.assertNotIn('GYS-O004:A5',self.ids(r))
        self.assertTrue(any(d['assertion_id']=='GYS-O004:A5' and not d['eligible'] for d in r['decisions']))

    def test_no_parent_tense_politeness_leaks_into_inner_views(self):
        text='동생이 온다고 했어요.'
        c=self.clause(text,sentence_type='declarative');c['observed_politeness']='polite'
        r=self.result(text,[c])
        for v in r['bindings'][1:]:
            self.assertEqual([{}],v['targets']);self.assertEqual({},v['candidate_features'])

    def test_form_specific_connective_with_bound_relation(self):
        text='일하느라고 못 갔어요.'
        c=self.clause('일하느라고',clause_relation='cause');c['role']='connective';c['observed_politeness']='unknown'
        r=self.result(text,[c])
        self.assertIn('GYS-G041:A1',self.ids(r))
        self.assertNotIn('GYS-G034:A1',self.ids(r))

    def test_polar_content_question_distinction_and_politeness(self):
        def forms(q,polite):
            text='무엇을 먹었어?' if q=='content' else '국밥을 먹었어?'
            c=self.clause(text,sentence_type='interrogative',question_type=q,host_pos='verb',host_class='predicate_other_than_anida')
            c['observed_politeness']=polite
            r=self.result(text,[c])
            return {x['relation']['subject'].get('text') for x in r['packets']['graph_hybrid']['references']}
        self.assertIn('-노',forms('content','non_polite'))
        self.assertIn('-나',forms('polar','non_polite'))
        self.assertNotIn('-노',forms('polar','non_polite'))
        self.assertNotIn('-나',forms('content','non_polite'))
        self.assertFalse(forms('content','polite') & {'-노','-나'})

    def test_graph_link_removal_removes_path_not_synthetic_lookup(self):
        r=self.result('오라고 하네.')
        self.assertTrue(any(p['edges'] for p in r['packets']['graph_hybrid']['graph_paths']))
        g=deepcopy(self.graph)
        from integrated_retrieval import EXPAND
        g['edges']=[e for e in g['edges'] if e['type'] not in EXPAND]
        e=IntegratedRetriever(g,EmptySearch())
        self.assertEqual([],self.result('오라고 하네.',engine=e)['packets']['graph_hybrid']['graph_paths'])

    def test_every_sent_assertion_has_match_and_application_binding(self):
        r=self.result('동생이 온다고 하네.')
        for c in r['packets']['graph_hybrid']['references']:
            self.assertEqual('match',c['conditions']['status'])
            v=next(v for v in r['bindings'] if v['id']==c['binding_id'])
            self.assertIn(c['application']['target'],v['slots'])

    def test_search_description_is_not_bound_condition(self):
        text='숙제를 했어.'
        views,_=bind_item({'id':'T','input':text,'clauses':[], 'source_units':[
            {'span':[0,len(text)],'text':text,'form_queries':['-고 하다'],'semantic_queries':['인용']} ]})
        self.assertEqual({},views[-1]['features']);self.assertEqual([],views[-1]['slots'])

    def test_typed_semantic_relation_is_bound_to_terminal_connective_only(self):
        text='걷다가 쉬었어요.'
        item={'id':'T','input':text,'clauses':[], 'source_units':[
            {'span':[0,3],'text':'걷다가','form_queries':['걷다'],'semantic_queries':['중단'],
             'features':{'clause_relation':'interruption_transition'}}]}
        result=self.engine.retrieve_item(item)
        self.assertIn('GYS-R045:A1',self.ids(result))
        del item['source_units'][0]['features']
        self.assertNotIn('GYS-R045:A1',self.ids(self.engine.retrieve_item(item)))

if __name__=='__main__':unittest.main()

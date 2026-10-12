import json
from pathlib import Path
import unittest

from sentence_retrieval import SentenceRetriever, morphology, semantic_guard, inflection_ending


class SentenceRetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = SentenceRetriever()

    def item(self, text, function='declarative', qtype=None):
        return {'id':'TEST','input':text,'clauses':[{'clause_id':'TEST:c1','text':text,
            'span':[0,len(text)],'role':'main','observed_politeness':'non_polite',
            'features':{'sentence_type':function,'question_type':qtype}}]}

    def test_full_sentence_reaches_eating_path(self):
        text='나는 배가 고파서 먼저 밥을 먹고 있을게.'
        r=self.engine.retrieve(self.item(text))
        p=r['packets']['v2_graph'];by={f['id']:f for f in p['references']}
        self.assertTrue(any(by[e['target']]['target_pattern']['text']=='묵고' for e in p['graph_paths']))
        self.assertFalse(r['packets']['v2_direct']['graph_paths'])
        self.assertFalse(any(f['type']=='inflection' for f in r['packets']['v2_direct']['references']))

    def test_past_does_not_retrieve_present_surface(self):
        w=next(w for w in morphology('먹었어.')['words'] if w['lemma']=='먹다')
        self.assertIsNone(inflection_ending(w))
        r=self.engine.retrieve(self.item('나는 아직 밥을 안 먹었어.'))
        self.assertFalse(any(f['type']=='inflection' and f['target_pattern']['text']=='묵어'
                            for f in r['packets']['v2_graph']['references']))

    def test_explicit_why_corrects_question_without_mutating_input(self):
        old=self.item('왜 아직 안 와?', 'interrogative', 'polar')
        new,audit=semantic_guard(old,morphology(old['input']))
        self.assertEqual(old['clauses'][0]['features']['question_type'],'polar')
        self.assertEqual(new['clauses'][0]['features']['question_type'],'content')
        self.assertTrue(audit)
        forms={f['target_pattern']['text'] for f in self.engine.retrieve(new)['packets']['v2_graph']['references']}
        self.assertIn('-노',forms);self.assertNotIn('-나',forms)

    def test_copula_ya_is_not_retrieved_as_particle(self):
        r=self.engine.retrieve(self.item('너 지금 어디야?','interrogative','content'))
        self.assertFalse(any(f['type']=='particle' for f in r['packets']['v2_graph']['references']))

    def test_input_span_mismatch_fails_closed(self):
        item=self.item('밥 먹어.');item['clauses'][0]['text']='밥 먹자.'
        with self.assertRaises(ValueError):self.engine.retrieve(item)

    def test_function_route_does_not_override_explicit_source_form(self):
        r=self.engine.retrieve(self.item('밖에 못 나가겠어요.'))
        for f in r['packets']['v2_graph']['references']:
            if f['retrieval_route']=='clause_function':
                self.assertEqual(f['source_pattern']['domain'],'metalinguistic')


if __name__=='__main__':unittest.main()

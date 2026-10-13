import json
from pathlib import Path
import unittest

from sentence_retrieval import SentenceRetriever, morphology, semantic_guard, inflection_ending, speech_style


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

    def test_informal_polite_candidates_survive_cap(self):
        item=self.item('조금 일찍 나왔어요.')
        item['clauses'][0]['observed_politeness']='polite'
        r=self.engine.retrieve(item)
        endings=[f for f in r['packets']['v2_direct']['references'] if f['type']=='ending']
        self.assertTrue(endings)
        self.assertTrue(all('해예' in f['scope']['speech_levels'] for f in endings))
        self.assertTrue(any('예' in f['target_pattern']['text'] for f in endings))
        self.assertLessEqual(len(endings),6)
        self.assertTrue(any(x.get('family')=='polite_declarative'
                            for x in r['terminal_decisions']))
        self.assertFalse(any(f['retrieval_route']=='clause_function' for f in endings))

    def test_polite_past_gets_specific_conversion_and_keeps_past_morpheme(self):
        r=self.engine.retrieve(self.item('어제 숙제를 했어요.'))
        for mode in ['v2_direct','v2_graph']:
            ends=[f for f in r['packets'][mode]['references'] if f['type']=='ending']
            self.assertEqual([f['target_pattern']['text'] for f in ends], ['-어예'])
            plan=ends[0]['input_binding']['ending_conversion']
            self.assertEqual(plan['source_morphemes'], ['하','었','어요'])
            self.assertEqual(plan['preferred_surface'], '했어예')
            self.assertEqual(plan['status'], 'derived_surface_not_attested_complete_utterance')

    def test_modal_and_subject_honorific_are_retained_in_ending_plan(self):
        for text, retained in [('못 나가겠어요.', ['겠']), ('선생님이 오셨어요.', ['시','었'])]:
            with self.subTest(text=text):
                r=self.engine.retrieve(self.item(text))
                plans=[f['input_binding'].get('ending_conversion') for f in r['packets']['v2_graph']['references']]
                self.assertIn(retained, [p['preserve_prefinals'] for p in plans if p])

    def test_copula_citation_forms_reach_direct_correspondence(self):
        for text in ['제 친구예요.', '그 사람은 학생이에요.']:
            with self.subTest(text=text):
                r=self.engine.retrieve(self.item(text))
                ends=[f for f in r['packets']['v2_graph']['references'] if f['type']=='ending']
                self.assertIn('-이라예', [f['target_pattern']['text'] for f in ends])
                self.assertFalse(any(f['retrieval_route']=='clause_function' for f in ends))

    def test_present_copula_conversion_does_not_erase_past(self):
        r=self.engine.retrieve(self.item('그 사람은 학생이었어요.'))
        refs=r['packets']['v2_graph']['references']
        self.assertFalse(any(f['id'].endswith('ending_repair:0001') and
                            f['source_id']=='NAMU_GRAMMAR_20260908' for f in refs))

    def test_copula_ya_declarative_and_question_are_distinct(self):
        r=self.engine.retrieve(self.item('그 사람은 내 친구야.'))
        self.assertTrue(any(f['target_pattern']['text']=='-이라' for f in r['packets']['v2_graph']['references']))
        q=self.engine.retrieve(self.item('너 지금 어디야?', 'interrogative', 'content'))
        self.assertFalse(any(f['target_pattern']['text'] in {'-이라','-다'}
                             for f in q['packets']['v2_graph']['references']))

    def test_pronoun_mapping_preserves_topic_condition_and_notes(self):
        fid='RYU2014:v2:full:0007'
        r=self.engine.retrieve(self.item('나는 차가 좋아.'))
        ref=next(f for f in r['packets']['v2_graph']['references'] if f['id']==fid)
        self.assertEqual(ref['input_binding']['following_particle'], '는')
        self.assertIn('모든 용법', ref['notes'])
        for text in ['나의 친구야.', '나를 기다려.']:
            with self.subTest(text=text):
                r=self.engine.retrieve(self.item(text))
                self.assertFalse(any(f['id']==fid for f in r['packets']['v2_graph']['references']))

    def test_same_ending_fact_binds_to_each_polite_clause(self):
        first='제가 했어요.'; second='동생도 했어요.'; text=first+' '+second
        item=self.item(text)
        item['clauses']=[{'clause_id':f'TEST:c{i}','text':s,'span':[start,start+len(s)],
                         'role':'main','observed_politeness':'polite','features':{'sentence_type':'declarative'}}
                        for i,s,start in [(1,first,0),(2,second,len(first)+1)]]
        refs=self.engine.retrieve(item)['packets']['v2_graph']['references']
        selected=[f for f in refs if f['target_pattern']['text']=='-어예']
        self.assertEqual({f['input_binding']['clause_id'] for f in selected}, {'TEST:c1','TEST:c2'})

    def test_quoted_ending_does_not_receive_outer_conversion(self):
        r=self.engine.retrieve(self.item('선생님은 "괜찮아요"라고 말씀하셨다.'))
        self.assertFalse(any(f['input_binding'].get('ending_conversion')
                             for f in r['packets']['v2_graph']['references']))

    def test_formal_polite_source_keeps_formal_priority(self):
        item=self.item('내일 갑니다.')
        item['clauses'][0]['observed_politeness']='polite'
        endings=[f for f in self.engine.retrieve(item)['packets']['v2_direct']['references'] if f['type']=='ending']
        self.assertTrue(endings)
        self.assertTrue(all('하이소' in f['scope']['speech_levels'] for f in endings))

    def test_fused_jyo_recovers_source_politeness_without_changing_analysis(self):
        item=self.item('많이 힘드셨죠?','interrogative','polar')
        item['clauses'][0]['observed_politeness']='unknown'
        r=self.engine.retrieve(item)
        self.assertEqual(item['clauses'][0]['observed_politeness'],'unknown')
        self.assertEqual(r['speech_style_profiles'][0]['register'],'informal_polite')
        self.assertTrue(any('해예' in f['scope']['speech_levels']
                            for f in r['packets']['v2_direct']['references'] if f['type']=='ending'))

    def test_subject_honorific_does_not_add_polite_endings(self):
        item=self.item('할머니께서 먼저 가셨어.')
        r=self.engine.retrieve(item)
        self.assertEqual(r['speech_style_profiles'][0]['politeness'],'non_polite')
        self.assertFalse(any('해예' in f['scope']['speech_levels']
                             for f in r['packets']['v2_direct']['references'] if f['type']=='ending'))

    def test_quoted_polite_ending_does_not_set_outer_register(self):
        item=self.item('선생님은 "괜찮아요"라고 말씀하셨다.')
        style=speech_style(item['clauses'][0],morphology(item['input']))
        self.assertEqual(style['politeness'],'non_polite')
        self.assertEqual(style['register'],'unknown')

    def test_register_preference_is_bound_separately_for_mixed_utterance(self):
        first='내일 가요.';second='내일 갑니다.';text=first+' '+second
        item=self.item(text)
        item['clauses']=[{'clause_id':f'TEST:c{i}','text':s,'span':[start,start+len(s)],
                         'role':'main','observed_politeness':'polite','features':{'sentence_type':'declarative'}}
                        for i,s,start in [(1,first,0),(2,second,len(first)+1)]]
        r=self.engine.retrieve(item)
        endings=[f for f in r['packets']['v2_direct']['references'] if f['type']=='ending']
        for cid,level in [('TEST:c1','해예'),('TEST:c2','하이소')]:
            selected=[f for f in endings if f['input_binding']['clause_id']==cid]
            self.assertTrue(selected)
            self.assertTrue(all(level in f['scope']['speech_levels'] for f in selected))

    def test_long_polite_utterance_retains_request_candidates(self):
        frozen=Path(__file__).parent/'reports/translation_20261012/analysis.json'
        item=next(i for i in json.loads(frozen.read_text())['items'] if i['id']=='LONG008')
        r=self.engine.retrieve(item)
        endings=[f for f in r['packets']['v2_direct']['references'] if f['type']=='ending']
        self.assertTrue(any(f['input_binding']['clause_id']=='LONG008:c2' and
                            'imperative' in f['functions'] for f in endings))
        self.assertTrue(any(f['input_binding']['clause_id']=='LONG008:c1' and
                            '해예' in f['scope']['speech_levels'] for f in endings))
        self.assertTrue(any(f['input_binding']['clause_id']=='LONG008:c3' and
                            '해예' in f['scope']['speech_levels'] for f in endings))

    def test_formal_request_terminal_is_recognized(self):
        item=self.item('어서 오십시오.','imperative')
        item['clauses'][0]['observed_politeness']='unknown'
        style=speech_style(item['clauses'][0],morphology(item['input']))
        self.assertEqual(style['politeness'],'polite')
        self.assertEqual(style['register'],'formal_polite')


if __name__=='__main__':unittest.main()

import unittest

from sentence_retrieval import SentenceRetriever, morphology
from construction_retrieval import units
from transformation_plan import package_plan


class ConstructionRetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = SentenceRetriever()

    def item(self, text):
        # Deliberately uninformative clause analysis: local structural evidence
        # must survive both a missed clause split and a missing function label.
        return {'id': 'UNSEEN_CONSTRUCTION', 'input': text, 'clauses': [{
            'clause_id': 'c1', 'text': text, 'span': [0, len(text)], 'role': 'main',
            'features': {'sentence_type': 'declarative'},
            'observed_politeness': 'unknown', 'observed_subject_honorific': 'unknown',
            'tense_or_modality': 'unknown'}]}

    def packet(self, text):
        return self.engine.retrieve(self.item(text))['packets']['v2_graph']

    def refs(self, text):
        return [f for f in self.packet(text)['references']
                if f['retrieval_route'] == 'source_bound_construction']

    def contractions(self, text):
        return [f for f in self.refs(text) if f['source_pattern']['features'].get('match_unit')
                == 'quotative_go_hada']

    def test_inner_intention_survives_final_hada_and_unsplit_clause(self):
        text = '책을 읽으려고 하는데 시간이 없어요.'
        refs = self.refs(text)
        self.assertIn('NAMU_GRAMMAR_20260908:v2:full:0732', [f['id'] for f in refs])
        f = next(f for f in refs if f['id'].endswith('full:0732'))
        self.assertEqual(f['input_binding']['text'], '읽으려고')
        self.assertEqual(f['input_binding']['construction']['text'], '읽으려고 하는데')

    def test_three_quotation_families_have_whole_construction_candidates(self):
        for text in ['늦게 온다고 했어요.', '내일 만나자고 했는데 바뀌었어요.', '나가라고 했다.']:
            with self.subTest(text=text):
                self.assertTrue(self.contractions(text))

    def test_inner_and_outer_honorific_past_do_not_migrate(self):
        c = self.contractions('선생님이 오신다고 했어요.')[0]['input_binding']['construction_conversion']
        self.assertEqual(c['preserve_inner_prefinals'], ['시'])
        self.assertEqual(c['preserve_outer_prefinals'], ['었'])
        c = self.contractions('이미 갔다고 하셨어요.')[0]['input_binding']['construction_conversion']
        self.assertEqual(c['preserve_inner_prefinals'], ['었'])
        self.assertEqual(c['preserve_outer_prefinals'], ['시', '었'])

    def test_nominal_quotation_retains_copula(self):
        for text in ['그는 의사라고 했어요.', '그는 학생이라고 했어요.']:
            c = self.contractions(text)[0]['input_binding']['construction']
            self.assertEqual(c['quotation_type'], 'nominal_statement')
            self.assertEqual(c['inner']['lemma'], '이다')

    def test_command_allomorph_keeps_eu(self):
        c = self.contractions('밥을 먹으라고 했어요.')[0]['input_binding']['construction_conversion']
        self.assertIn('으라', c['candidate_morphemes'])

    def test_outer_relative_ending_is_not_replaced_with_terminal(self):
        c = self.contractions('버리라고 한 건 아니었어요.')[0]['input_binding']['construction_conversion']
        self.assertEqual(c['preserve_outer_ending'], 'ᆫ')
        self.assertEqual(c['preserve_outer_prefinals'], [])

    def test_reported_negation_chain_and_inner_negative_are_not_eaten(self):
        text = '안 먹는다고 하지 않았어요.'
        b = self.contractions(text)[0]['input_binding']
        self.assertEqual(b['construction_conversion']['preserve_outer_ending'], '지')
        self.assertEqual(text[b['span'][1]:].strip(), '않았어요.')
        self.assertTrue(text[:b['span'][0]].strip().endswith('안'))

    def test_plain_go_and_sleep_are_not_quotation(self):
        for text in ['밥을 먹고 했어요.', '자고 하니까 피곤해.', '빨래를 하고 잤어요.']:
            with self.subTest(text=text):
                self.assertFalse(self.contractions(text))

    def test_unrelated_reporter_punctuation_and_particle_stop_contraction(self):
        for text in ['온다고 들었어요.', '온다고. 했어요.', '온다고는 했어요.', '온다고 일했어요.']:
            with self.subTest(text=text):
                self.assertFalse(self.contractions(text))

    def test_causal_and_concessive_dago_rago_are_not_quotation(self):
        for text in ['값이 싸다고 샀는데 고장 났어요.', '학생이라고 다 공부를 잘하는 건 아니에요.']:
            self.assertFalse(self.refs(text))

    def test_intention_is_not_quoted_go_contraction(self):
        for text in ['비가 오려고 해요.', '먹으려고 했어요.', '먹으려고 학교에 갔어요.']:
            with self.subTest(text=text):
                self.assertFalse(self.contractions(text))
                self.assertFalse(any(f['id'].startswith('YANG2021') for f in self.refs(text)))

    def test_quotation_suffix_alias_preserves_present_prefix(self):
        for text, ending in [('온다고 했어.', 'ᆫ다꼬'), ('먹는다고 했어.', '는다꼬')]:
            f = next(f for f in self.refs(text) if f['id'] == 'NAMU20260901:v2:full:0003')
            self.assertEqual(f['input_binding']['construction_conversion']['candidate_inner_morphemes'][-1], ending)

    def test_assertion_rule_excluded_from_embedded_quotation(self):
        text = '그 음식이 짜다고 들었어요.'
        item = self.item(text)
        cut = text.index(' 들었')
        item['clauses'] = [dict(item['clauses'][0], text=text[:cut], span=[0, cut], role='connective')]
        refs = self.engine.retrieve(item)['packets']['v2_graph']['references']
        self.assertNotIn('NAMU_GRAMMAR_20260908:v2:full:0755', [f['id'] for f in refs])
        self.assertIn('NAMU20260901:v2:full:0003', [f['id'] for f in refs])

    def test_actual_plan_keeps_composition_and_provenance(self):
        text = '늦게 온다고 했어요.'
        plan = package_plan(self.packet(text), self.item(text))['transformation_plan']
        f = next(c for p in plan for c in p['candidates']
                 if c['source_pattern']['features'].get('match_unit') == 'quotative_go_hada')
        self.assertEqual(f['origin'], 'documentary_KG')
        self.assertEqual(f['binding']['construction_conversion']['status'], 'derived_plan_not_attested_complete_surface')
        self.assertTrue(f['evidence_pages'])

    def test_all_bindings_are_source_substrings(self):
        text = '오는 줄 알았는데 늦게 온다고 했고, 내일 만나자고 했어요.'
        for f in self.refs(text):
            b = f['input_binding']
            self.assertEqual(text[slice(*b['span'])], b['text'])

    def test_reference_only_intention_example_not_promoted(self):
        f = self.engine.kg.facts['NAMU20260901:v2:review_completion:0200']
        self.assertEqual(f['usability'], 'reference_only')


if __name__ == '__main__':
    unittest.main()

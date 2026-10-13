"""Regression tests for the gaps that motivated a separate KG."""
import unittest

from author_support import condition
from query import KG, assess, evaluate_conditions


class QueryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kg = KG()

    def test_standard_lemma_reaches_dialect_inflection(self):
        result = self.kg.lexical_paths('먹다', '-고')
        self.assertTrue(result['paths'])
        self.assertEqual({p['surface'] for p in result['paths']}, {'묵고'})
        for p in result['paths']:
            self.assertEqual(p['input_lemma'], '먹다')
            self.assertEqual(p['selected_candidate']['lemma'], '묵다')
            checks = p['checks']['inflection']['conditions']
            self.assertTrue(all(c['status'] == 'satisfied' for c in checks))
            self.assertTrue(all(f['evidence'] for f in p['statements']))
            self.assertFalse(p['generation_approved'])

    def test_unattested_ending_is_not_synthesized(self):
        self.assertEqual(self.kg.lexical_paths('먹다', '-없는어미')['paths'], [])

    def test_different_senses_are_not_collapsed(self):
        result = self.kg.lexical_paths('버리다', '-고')
        self.assertTrue({'버리고', '베리고', '삐고', '뿌고'} <= {p['surface'] for p in result['paths']})
        for p in result['paths']:
            self.assertIn('sense_requires_review', p['review_reasons'])

    def test_explicit_lexical_selection_constrains_inflection(self):
        lex = next(f for f in self.kg.facts.values() if f['type']=='lexical_mapping'
                   and f['source_pattern']['text']=='버리다' and f['target_pattern']['text']=='베리다')
        result = self.kg.lexical_paths('버리다', '-고', lexical_id=lex['id'])
        self.assertEqual({p['surface'] for p in result['paths']}, {'베리고'})

    def test_missing_condition_is_unknown(self):
        c = condition('candidate', 'tense_aspect_suffix', False, op='exists')
        self.assertEqual(evaluate_conditions([c], {})[0]['status'], 'unknown')
        self.assertEqual(evaluate_conditions([c], {'candidate': {'tense_aspect_suffix': None}})[0]['status'], 'satisfied')
        self.assertEqual(evaluate_conditions([c], {'candidate': {'tense_aspect_suffix': '-었-'}})[0]['status'], 'failed')

    def test_actual_question_constraints_filter_forms(self):
        fs = [f for f in self.kg.facts.values() if f['source_id']=='NAMU_GRAMMAR_20260908'
              and f['type']=='ending' and f['source_pattern']['text']=='의문 종결']
        self.assertEqual(len(fs), 4)
        def forms(qtype, pred):
            owners = {'input': {'question_type': qtype}, 'candidate': {
                'predicate_class': pred, 'tense_or_retrospective_suffix': False}}
            return {f['target_pattern']['text'] for f in fs if not assess(f, owners)['rejected']}
        self.assertEqual(forms('polar', 'predicate_except_negative_copula'), {'-나'})
        self.assertEqual(forms('content', 'predicate_except_negative_copula'), {'-노'})
        self.assertEqual(forms('content', 'nominal_or_copula'), {'-(이)고'})

    def test_negative_examples_and_reference_tables_cannot_apply(self):
        for f in self.kg.facts.values():
            if f['claim_status']=='negative_example' or f['usability']=='reference_only':
                self.assertTrue(assess(f, {})['rejected'])

    def test_original_table_typo_does_not_create_a_rule(self):
        fs = [f for f in self.kg.facts.values() if f['source_id']=='NAMU_GRAMMAR_20260908'
              and f['type']=='inflection' and f['source_pattern']['lemma']=='뿌다'
              and any(c['field']=='ending' and c['value']=='-아/어가' for c in f['conditions'])]
        self.assertTrue(fs)
        for f in fs:
            self.assertIn(f['usability'], {'reference_only', 'blocked'})
            self.assertTrue(assess(f, {'candidate': {
                'lemma': '뿌다', 'ending': '-아/어가'}})['rejected'])

    def test_new_table_preserves_spelling_and_pronunciation_boundary(self):
        result = self.kg.lexical_paths('빠뜨리다', '-고')
        surfaces = {p['surface'] for p in result['paths']}
        self.assertTrue({'빠줗고', '빠주고'} <= surfaces)
        self.assertNotIn('빠주코', surfaces)
        self.assertTrue(all(not p['generation_approved'] for p in result['paths']))


if __name__ == '__main__':
    unittest.main()

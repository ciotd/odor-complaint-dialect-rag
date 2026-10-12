"""Boundary regressions; these do not measure dialect translation quality."""
import copy
import json
from pathlib import Path
import unittest
from analysis_input import normalize_analysis, targets_for, route_functions
from run_manual_kg_development import retrieve

BASE = Path(__file__).parent

class AnalysisInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy = json.loads((BASE/'inputs/development_30.manual_analysis.json').read_text())
        cls.graph = json.loads((BASE.parent/'grammar/grammar.graph.json').read_text())

    def fresh(self):
        data = normalize_analysis(self.legacy)
        data['items'] = [data['items'][11]]
        return data, data['items'][0]['clauses'][0]

    def test_legacy_migration_is_lossless_for_notes_and_does_not_mutate(self):
        source = copy.deepcopy(self.legacy)
        normalized = normalize_analysis(source)
        self.assertEqual(source, self.legacy)
        self.assertEqual(normalized, normalize_analysis(normalized))
        self.assertEqual('lexical_honorific', normalized['items'][5]['clauses'][0]['annotations']['subject_honorific'])
        self.assertEqual('tentative_schedule_question', normalized['items'][12]['clauses'][0]['annotations']['modality'])
        self.assertTrue(all('target_scenarios' not in c for i in normalized['items'] for c in i['clauses']))

    def test_politeness_alone_derives_different_targets(self):
        data, clause = self.fresh()
        self.assertIn({'addressee_treatment':'informal_low'}, targets_for(clause))
        clause['observed_politeness'] = 'polite'
        data = normalize_analysis(data)
        self.assertIn({'addressee_treatment':'informal_high'}, targets_for(data['items'][0]['clauses'][0]))
        self.assertNotIn({'speech_level':'HAERACHE'}, targets_for(clause))

    def test_unknown_politeness_does_not_select_candidates(self):
        data, clause = self.fresh()
        clause['observed_politeness'] = 'unknown'
        result = retrieve(self.graph, data)[0]['clauses'][0]
        self.assertEqual([], result['selected_assertion_ids'])
        self.assertIn('unknown_observed_politeness', result['analysis_gaps'])

    def test_invalid_and_wrong_source_features_fail_before_retrieval(self):
        for key, value in [('sentence_type','question'),('speech_level','HAECHE'),
                           ('prefinal_profile','none'),('modality','tentative_schedule_question'),
                           ('typo_feature','anything')]:
            with self.subTest(key=key):
                data, clause = self.fresh()
                clause['features'][key] = value
                with self.assertRaises(ValueError):
                    retrieve({}, data)  # Validation precedes any graph access.
        data, clause = self.fresh()
        clause['preserved_candidate_features']['host_pos'] = 'verb'
        with self.assertRaises(ValueError): normalize_analysis(data)

    def test_duplicate_bindings_and_out_of_bounds_span_fail(self):
        for field in ['clause_id', 'predicate_complex_id']:
            data, clause = self.fresh()
            extra = copy.deepcopy(clause)
            extra['clause_id'] += ':other'
            extra['predicate_complex_id'] += ':other'
            extra[field] = clause[field]
            data['items'][0]['clauses'].append(extra)
            with self.assertRaisesRegex(ValueError, 'duplicate'): normalize_analysis(data)
        data, clause = self.fresh()
        clause['span'][1] = 9999  # Python slicing alone previously accepted this.
        with self.assertRaisesRegex(ValueError, 'span'): normalize_analysis(data)

    def test_new_input_cannot_supply_manual_target(self):
        data, clause = self.fresh()
        clause['target_scenarios'] = [{'speech_level':'HAECHE'}]
        with self.assertRaisesRegex(ValueError, 'unrecognized fields'): normalize_analysis(data)

    def test_contradictory_question_analysis_fails(self):
        data, clause = self.fresh()
        clause['features']['sentence_type'] = 'declarative'
        with self.assertRaisesRegex(ValueError, 'conflicts'): normalize_analysis(data)

    def test_unknown_feature_and_unimplemented_route_are_explicit(self):
        data, clause = self.fresh()
        clause['features']['sentence_type'] = None
        result = retrieve(self.graph, data)[0]['clauses'][0]
        self.assertEqual([], result['selected_assertion_ids'])
        self.assertEqual(['missing_or_unsupported_function_route:sentence_type'], result['analysis_gaps'])
        clause['role'] = 'connective'
        clause['features'] = {'clause_relation':'concession'}
        normalized = normalize_analysis(data)
        functions, gaps = route_functions(normalized['items'][0]['clauses'][0])
        self.assertEqual({'CONCESSION'}, functions)
        self.assertEqual([], gaps)
        clause['features'] = {'clause_relation':'simultaneous_action'}
        normalized = normalize_analysis(data)
        functions, gaps = route_functions(normalized['items'][0]['clauses'][0])
        self.assertEqual(set(), functions)
        self.assertTrue(gaps)

    def test_unknown_policy_and_observation_typo_fail(self):
        data, clause = self.fresh()
        data['policy']['style_policy_id'] = 'another_policy'
        with self.assertRaises(ValueError): normalize_analysis(data)
        data, clause = self.fresh()
        clause['observed_politeness'] = 'poltie'
        with self.assertRaises(ValueError): normalize_analysis(data)

if __name__ == '__main__': unittest.main()

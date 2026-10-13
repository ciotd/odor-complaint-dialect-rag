import copy
import unittest
import jsonschema
from run_auto_analysis_development import adapt, candidate_assumptions, locate, analysis_system

class AutomaticAnalysisTests(unittest.TestCase):
    def sample(self):
        row={'id':'NEW','standard':'어제 책을 읽었어요.'}
        raw={'preservation_note':'과거 독서와 존댓말 유지','unqueried_structure_note':'추가 구성 없음',
             'clauses':[{'text':row['standard'],'occurrence':0,'role':'main',
                         'features':{'sentence_type':'declarative','host_form':'읽다','host_pos':'verb'},
                         'observed_politeness':'polite','observed_subject_honorific':'not_observed',
                         'tense_or_modality':'past','observed_prefinals':['-었-'],
                         'predicate_evidence':'읽었어요','note':''}]}
        return row,raw
    def test_offsets_and_ids_are_bound_by_code(self):
        row,raw=self.sample();out=adapt(row,raw)['items'][0]['clauses'][0]
        self.assertEqual([0,len(row['standard'])],out['span'])
        self.assertEqual('NEW:c1',out['clause_id'])
        self.assertEqual('-었-',out['preserved_candidate_features']['preceding_form'])
    def test_repeated_span_needs_occurrence(self):
        self.assertEqual([3,5],locate('가자 가자','가자',1))
        with self.assertRaises(ValueError):locate('가자','가자',1)
    def test_missing_source_evidence_and_duplicate_clause_fail(self):
        row,raw=self.sample();raw['clauses'][0]['predicate_evidence']='먹었어요'
        with self.assertRaises(ValueError):adapt(row,raw)
        row,raw=self.sample();raw['clauses'].append(copy.deepcopy(raw['clauses'][0]))
        with self.assertRaises(ValueError):adapt(row,raw)
    def test_model_cannot_supply_candidate_or_target_values(self):
        for key,value in [('speech_level','HAECHE'),('prefinal_profile','none')]:
            row,raw=self.sample();raw['clauses'][0]['features'][key]=value
            with self.assertRaises(jsonschema.ValidationError):adapt(row,raw)
    def test_unknown_prefinals_are_not_invented_from_past_meaning(self):
        row,raw=self.sample();raw['clauses'][0]['observed_prefinals']=None
        out=adapt(row,raw)['items'][0]['clauses'][0]
        self.assertEqual({},out['preserved_candidate_features'])
    def test_prefinal_order_and_none_remain_distinct(self):
        self.assertEqual('-었-',candidate_assumptions(['-시-','-었-'],'verb')['preceding_form'])
        self.assertEqual('subject_honorific_only',candidate_assumptions(['-시-'],'verb')['prefinal_profile'])
        self.assertEqual({'prefinal_profile':'none'},candidate_assumptions([],'adjective'))
    def test_analyzer_prompt_has_no_development_answer_or_rule_id(self):
        prompt=analysis_system()
        self.assertNotIn('DEV012',prompt);self.assertNotIn('GYS-',prompt)
        self.assertNotIn('열쇠',prompt)

if __name__=='__main__':unittest.main()

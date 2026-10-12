"""Source-grounded positive/negative regressions, not naturalness evaluation."""
import json
from pathlib import Path
import unittest
from query_review import inspect_conditions, review

class StructureRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph=json.loads((Path(__file__).parent/'grammar.graph.json').read_text())
    def test_haeye_all_four_functions_and_height(self):
        for typ in ['declarative','interrogative','imperative','hortative']:
            r=review(self.graph,'concept:'+typ.upper(),{'sentence_type':typ},target_features={'addressee_treatment':'informal_high'})
            forms={c['form'] for c in r['candidates'] if c['condition_assessment']['status']=='match'}
            self.assertIn('-아/어예',forms)
            low=inspect_conditions(self.graph,'GYS-H028:F2',{'sentence_type':typ},target_features={'addressee_treatment':'informal_low'})
            self.assertTrue(all(a['assessment']['status']=='mismatch' for a in low['base_assertions']))
    def test_haeye_unknown_height_not_permission(self):
        r=inspect_conditions(self.graph,'GYS-H028:F2',{'sentence_type':'declarative'})
        a=next(x for x in r['base_assertions'] if x['assertion_id']=='GYS-H028:A7')
        self.assertEqual('unknown',a['assessment']['status'])
    def test_northern_height_not_equated_with_other_speech_level(self):
        r=inspect_conditions(self.graph,'GYS-H022:F1',{'sentence_type':'declarative','host_pos':'verb'}, {'attachment_coda':'absent'}, {'addressee_treatment':'informal_low'})
        self.assertEqual('mismatch',next(a for a in r['base_assertions'] if a['assertion_id']=='GYS-H022:A3')['assessment']['status'])
    def test_added_exception_does_not_generalize_to_other_lexeme(self):
        for lemma,expect in [('작다','match'),('밝다','mismatch')]:
            r=inspect_conditions(self.graph,'GYS-H022:F2',{'host_form':lemma,'host_pos':'adjective'})
            a=next(a for ref in r['references'] for a in ref['assertions'] if a['subject']['text']=='작으이더')
            self.assertEqual(expect,a['assessment']['status'])
    def test_georo_kkeum_uses_actual_component_and_own_prohibition(self):
        for start in ['GYS-Y001:F1','GYS-Y001:F2','GYS-Y001:F3','GYS-Y001:F4','GYS-Y002:F2','GYS-Y015:F1']:
            r=inspect_conditions(self.graph,start,{}, {'following_form':'끔'})
            self.assertIn('GYS-Y015:A1',r['matched_explicit_exclusions'])
            r=inspect_conditions(self.graph,start,{}, {'following_form':'만'})
            self.assertNotIn('GYS-Y015:A1',r['matched_explicit_exclusions'])
    def test_auxiliary_and_lexical_doeda_differ(self):
        for role,blocked in [('auxiliary',True),('lexical',False)]:
            r=inspect_conditions(self.graph,'GYS-Y001:F1',{'following_predicate_role':role},{'following_form':'되-'})
            self.assertEqual(blocked,'GYS-Y008:A1' in r['matched_explicit_exclusions'])
    def test_preserved_ge_doeda_not_blocked_by_georo_prohibition(self):
        r=inspect_conditions(self.graph,'GYS-R024:F1',{'following_predicate_role':'auxiliary'},{'following_form':'되-'})
        self.assertNotIn('GYS-Y008:A1',r['matched_explicit_exclusions'])
        self.assertTrue(any(ref['relation']=='contrasts_in_function' for ref in r['references']))
    def test_quotative_context_shared_and_warning_not_condition(self):
        for start in ['GYS-O004:F3','GYS-P001:F1','GYS-P002:F1']:
            for kind,expected in [('quotative_rago_hada','match'),('deictic_geureoda','mismatch')]:
                r=inspect_conditions(self.graph,start,{'construction_kind':kind})
                self.assertTrue(all(a['assessment']['status']==expected for a in r['base_assertions']))
            r=inspect_conditions(self.graph,start,{'meaning':'원문에 기술된 개별 구성·범위; 동일 의미나 범지역 교환을 보장하지 않음'})
            self.assertTrue(all(a['assessment']['status']=='unknown' for a in r['base_assertions']))
if __name__=='__main__':unittest.main()

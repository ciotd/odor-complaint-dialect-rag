"""Regression of source-bound KG assertions; manually supplied features, not parser evaluation."""
import copy
import json
from pathlib import Path
import unittest
from query_review import inspect_conditions,index_conditions

B=Path(__file__).parent
class SourceGroundedRepairs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph=json.loads((B/'grammar.graph.json').read_text());cls.index=index_conditions(cls.graph)
        cls.records={r['id']:r['knowledge'] for r in map(json.loads,(B/'records.jsonl').read_text().splitlines())}
    def inspect(self,aid,features):
        return inspect_conditions(self.graph,aid,features,_index=self.index)
    def status(self,aid,features):return self.inspect(aid,features)['base_assertions'][0]['assessment']['status']
    def test_three_rago_records_agree_on_construction_and_slot(self):
        for aid in ['GYS-G007:A1','GYS-P001:A1','GYS-P016:A3']:
            self.assertEqual('match',self.status(aid,{'construction_kind':'quotative_rago_hada'}))
            self.assertEqual('mismatch',self.status(aid,{'construction_kind':'deictic_geureoda'}))
            self.assertEqual('unknown',self.status(aid,{}))
            self.assertEqual('expression.orthography',self.index[0][aid]['properties']['application']['target'])
        # Removing region prose from input conditions must not erase the source's scope.
        forms={f['key']:f for f in self.records['GYS-P016']['forms']}
        self.assertIn('경북 우세',forms['F2']['sense'])
        self.assertIn('경남 서부/중부',forms['F4']['sense'])
    def test_quoted_statement_not_outer_declarative_or_ordinary_past(self):
        good={'construction_kind':'quotative_reporting','quotation_type':'statement','source_form':'-고'}
        self.assertEqual('match',self.status('GYS-R007:A1',good))
        for change in [{'construction_kind':'lexical_hada'},{'quotation_type':'command'},{'source_form':'-었-'}]:
            self.assertEqual('mismatch',self.status('GYS-R007:A1',{**good,**change}))
        self.assertEqual('unknown',self.status('GYS-R007:A1',{'sentence_type':'declarative'}))
    def test_quote_ha_contraction_does_not_license_lexical_ha(self):
        good={'construction_kind':'quotative_hada','source_form':'-고 하-'}
        self.assertEqual('match',self.status('GYS-O004:A5',good))
        self.assertEqual('mismatch',self.status('GYS-O004:A5',{**good,'construction_kind':'lexical_hada'}))
        self.assertEqual('mismatch',self.status('GYS-O004:A5',{**good,'source_form':'-고 말하-'}))
        self.assertEqual('unknown',self.status('GYS-O004:A5',{'construction_kind':'quotative_hada'}))
    def test_specific_hane_form_not_replacement_for_haesseo_or_haseyo(self):
        for form,expected in [('-고 하네','match'),('-고 했어','mismatch'),('-고 하세요','mismatch')]:
            self.assertEqual(expected,self.status('GYS-R008:A2',{'construction_kind':'quotative_hada','source_form':form}))
        a=self.inspect('GYS-R008:A1',{'construction_kind':'quotative_hada','quotation_type':'command'})['base_assertions'][0]
        self.assertEqual('example_only',a['assertion_mode'])
        self.assertEqual('predicate.construction',self.index[0]['GYS-R008:A1']['properties']['application']['target'])
    def test_contraction_evidence_is_actually_pdf18(self):
        a=self.inspect('GYS-R008:A2',{})['base_assertions'][0]
        self.assertEqual({18},{e['properties']['page'] for e in a['evidence']})
    def test_purpose_and_reason_are_not_quotative_homographs(self):
        for aid,form,relation in [('GYS-G006:A1','-(으)려고','purpose_intention'),('GYS-G041:A1','-느라고','cause')]:
            self.assertEqual('match',self.status(aid,{'source_form':form,'clause_relation':relation}))
            self.assertEqual('mismatch',self.status(aid,{'source_form':'-라고 하다','clause_relation':relation,'construction_kind':'quotative_rago_hada'}))
            self.assertEqual('clause.connective',self.index[0][aid]['properties']['application']['target'])
    def test_all_repaired_connectives_bind_to_connective_slot(self):
        for rid in ['GYS-G006','GYS-G034','GYS-G036','GYS-G037','GYS-G038','GYS-G039','GYS-G041']:
            for a in self.records[rid]['relations']:
                self.assertEqual('clause.connective',a['application']['target'])
                self.assertIn('source_form',a['application']['input_features'])
    def test_daga_rule_cannot_replace_modifier_neun(self):
        self.assertEqual('match',self.status('GYS-R045:A1',{'source_form':'-다가','clause_relation':'interruption_transition'}))
        self.assertEqual('mismatch',self.status('GYS-R045:A1',{'source_form':'-는','clause_relation':'interruption_transition'}))
        self.assertEqual('unknown',self.status('GYS-R045:A1',{'clause_relation':'interruption_transition'}))
    def test_additive_and_contrastive_jiman_are_not_same_use(self):
        self.assertEqual('match',self.status('GYS-G039:A1',{'source_form':'-거니와','clause_relation':'addition'}))
        self.assertEqual('mismatch',self.status('GYS-G038:A1',{'source_form':'-거니와','clause_relation':'addition'}))
    def test_new_table_rows_keep_distinct_source_forms(self):
        for rid,form in [('GYS-G073','-다느니'),('GYS-G074','-다더니')]:
            self.assertEqual('match',self.status(rid+':A1',{'source_form':form}))
            self.assertEqual('mismatch',self.status(rid+':A1',{'source_form':'-더니'}))
            self.assertEqual(28,self.records[rid]['evidence'][0]['page'])
    def test_quoted_marker_reaches_contraction_and_specific_form(self):
        r=self.inspect('GYS-R007:F1',{'construction_kind':'quotative_reporting','quotation_type':'statement','source_form':'-고'})
        ref=next(x for x in r['references'] if x['to']=='GYS-O004:A5')
        self.assertFalse(ref['condition_inheritance'])
        self.assertEqual('mismatch',ref['assertions'][0]['assessment']['status'])
        r=self.inspect('GYS-O004:A5',{'construction_kind':'quotative_hada','source_form':'-고 하-'})
        self.assertTrue(any(x['to']=='GYS-R008:A2' for x in r['references']))
        # Removing the authored link removes the path: no synthetic shortcut in the diagnostic.
        g=copy.deepcopy(self.graph);g['edges']=[e for e in g['edges'] if not(e['source']=='GYS-R007:F1' and e['target']=='GYS-O004:A5')]
        r=inspect_conditions(g,'GYS-R007:F1',{})
        self.assertFalse(any(x['to']=='GYS-O004:A5' for x in r['references']))

if __name__=='__main__':unittest.main()

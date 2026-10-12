"""Tests of grounding and retrieval boundaries, not dialect naturalness."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import Mock

from analysis_input import validate_source_units
from run_auto_analysis_development import adapt
from source_retrieval import SourceIndex,retrieve_broad,semantic_review
from source_inventory import split_page

BASE=Path(__file__).resolve().parent

class SourceExpansionTests(unittest.TestCase):
    def test_page_split_preserves_layout_and_every_character(self):
        page='표 제목\n항목     값\n\n'+('긴 예문\n'*100)+'\n각주 마지막'
        parts=list(split_page(page,80))
        self.assertEqual(page,''.join(t for _,_,t in parts))
        for start,end,text in parts:self.assertEqual(text,page[start:end])

    def test_source_span_and_parent_are_checked(self):
        u={'unit_id':'U1','text':'온다고 했어','span':[0,len('온다고 했어')],'kind':'인용','parent_index':None,
           'meaning':'말한 내용을 전달','form_queries':['다고 하다'],'semantic_queries':['인용 구성']}
        validate_source_units('온다고 했어',[u])
        invalid=copy.deepcopy(u);invalid['text']='왔다고 했어'
        with self.assertRaises(ValueError):validate_source_units('온다고 했어',[invalid])
        invalid=copy.deepcopy(u);invalid['parent_index']=0
        with self.assertRaises(ValueError):validate_source_units('온다고 했어',[invalid])

    def test_legacy_function_candidates_stay_equal_without_semantic_approval(self):
        from run_manual_kg_development import retrieve
        graph=json.loads((BASE.parent/'grammar/grammar.graph.json').read_text())
        analysis=json.loads((BASE/'inputs/development_30.manual_analysis.json').read_text())
        analysis['items']=analysis['items'][:2]
        old=retrieve(graph,analysis);new=retrieve_broad(graph,analysis,SourceIndex())
        for a,b in zip(old,new):
            self.assertEqual(a['clauses'],b['clauses'])
            self.assertEqual([],b['prompt_packet']['additional_source_references'])
            self.assertEqual('not_run_no_model_call',b['extended_retrieval']['semantic_review']['status'])

    def test_semantic_model_cannot_invent_evidence_or_candidate(self):
        index=Mock();index.docs={'R':{'id':'R','type':'kg_record','text':'인용문 설명'}}
        for choice in [dict(id='FAKE',input_unit_id='U',evidence_quote='인용문',reason='관련'),
                       dict(id='R',input_unit_id='U',evidence_quote='없는 예문',reason='관련')]:
            call=Mock(return_value={'model':'M','choices':[{'finish_reason':'stop','message':{'content':json.dumps({'selected':[choice]})}}]})
            result=semantic_review(call,{'requested_model':'M'},{'input':'원문'},[{'unit_id':'U'}],[{'id':'R'}],index)
            self.assertEqual('failed',result['status'])
            self.assertNotIn('selected',result)

    def test_nested_construction_does_not_inherit_whole_clause_conditions(self):
        from source_retrieval import bundle_record
        from query_review import index_conditions
        index=SourceIndex();graph=json.loads((BASE.parent/'grammar/grammar.graph.json').read_text())
        item={'clauses':[{'span':[0,20],'features':{'construction_kind':'quotative_rago_hada'},'preserved_candidate_features':{}}]}
        unit={'unit_id':'U','span':[5,10]}
        packet=bundle_record('GYS-P001',unit,item,index,graph,index_conditions(graph))
        self.assertEqual('unknown',packet['condition_diagnostics'][0]['base_assertions'][0]['assessment']['status'])

    def test_every_unit_reconstructs_its_page(self):
        index=SourceIndex()
        for pid,page in index.pages.items():
            units=sorted([u for u in index.units.values() if u['page_id']==pid],key=lambda u:u['span'][0])
            self.assertEqual(page['text'],''.join(u['text'] for u in units))
        graph=json.loads((BASE.parent/'grammar/grammar.graph.json').read_text())
        known={n['id'] for n in graph['nodes']}|set(index.units)|set(index.pages)
        for e in index.links:
            self.assertIn(e['source'],known);self.assertIn(e['target'],known)


    def test_same_document_can_support_two_input_units(self):
        index=Mock();index.docs={'R':{'id':'R','type':'kg_record','text':'원문 인용 설명'}}
        choices=[{'id':'R','input_unit_id':uid,'evidence_quote':'원문 인용','reason':'관련'} for uid in ['U1','U2']]
        call=Mock(return_value={'model':'M','choices':[{'finish_reason':'stop','message':{'content':json.dumps({'selected':choices})}}]})
        result=semantic_review(call,{'requested_model':'M'},{'input':'원문'},[{'unit_id':'U1'},{'unit_id':'U2'}],[{'id':'R'}],index)
        self.assertEqual('validated_relevance_hypotheses',result['status'])
        self.assertEqual(2,len(result['selected']))

    def test_full_source_review_rejects_edited_quote_and_missing_unit(self):
        from review_source_inventory import validate_review
        units=[{'id':'S','text':'예문은 그대로 남긴다.'}]
        row={'id':'S','kind':'example','summary':'예문','examples':['예문은 그대로 남긴다.'],
             'proposed_record_ids':[],'needs_visual_review':False,'limits':''}
        self.assertEqual([row],validate_review({'units':[row]},units,{'S':[]}))
        row['examples']=['예문을 수정한다.']
        with self.assertRaises(ValueError):validate_review({'units':[row]},units,{'S':[]})
        with self.assertRaises(ValueError):validate_review({'units':[]},units,{'S':[]})


    def test_invalid_one_quote_does_not_discard_other_grounded_evidence(self):
        index=Mock();index.docs={'R':{'id':'R','type':'kg_record','text':'원문 근거'}}
        choices=[{'id':'R','input_unit_id':'U1','evidence_quote':'원문 근거','reason':'관련'},
                 {'id':'R','input_unit_id':'U2','evidence_quote':'만들어낸 예문','reason':'관련'}]
        call=Mock(return_value={'model':'M','choices':[{'finish_reason':'stop','message':{'content':json.dumps({'selected':choices})}}]})
        result=semantic_review(call,{'requested_model':'M'},{'input':'원문'},[{'unit_id':'U1'},{'unit_id':'U2'}],[{'id':'R'}],index)
        self.assertEqual(1,len(result['selected']));self.assertEqual(1,len(result['rejected_selections']))

    def test_unknown_function_does_not_prevent_source_search(self):
        from run_manual_kg_development import retrieve
        graph=json.loads((BASE.parent/'grammar/grammar.graph.json').read_text())
        analysis=json.loads((BASE/'inputs/development_30.manual_analysis.json').read_text())
        from analysis_input import normalize_analysis
        analysis=normalize_analysis(analysis)
        analysis['items']=analysis['items'][:1]
        item=analysis['items'][0]
        for c in item['clauses']:c['features']={};c['observed_politeness']='unknown'
        item['source_units']=[{'unit_id':'UNCLASSIFIED','text':item['input'],'span':[0,len(item['input'])],
                              'kind':'unclassified','parent_index':None,'meaning':'검색 가설',
                              'form_queries':['-라고 하다'],'semantic_queries':['인용 구성 축약']}]
        r=retrieve_broad(graph,analysis,SourceIndex())[0]
        self.assertTrue(r['extended_retrieval']['shortlist'])
        self.assertFalse(any(c['selected_assertion_ids'] for c in r['clauses']))
        for u in r['prompt_packet']['source_units']:
            self.assertNotIn('meaning',u);self.assertNotIn('semantic_queries',u)

    def test_review_restores_only_unique_original_whitespace(self):
        from review_source_inventory import bind_quote
        original='인용문은 줄을\n  바꾸어 기록했다.'
        value,audit=bind_quote(original,'인용문은 줄을 바꾸어 기록했다.')
        self.assertEqual(original,value)
        self.assertEqual('original_whitespace_restored',audit['status'])
        value,audit=bind_quote(original,'인용문을 줄을 바꾸어 기록했다.')
        self.assertIsNone(value)
        self.assertEqual('rejected',audit['status'])
        value,audit=bind_quote('가 나 / 가  나','가나')
        self.assertIsNone(value)

    def test_review_preserves_valid_examples_when_one_is_rejected(self):
        from review_source_inventory import bind_review
        row={'id':'S','kind':'example','summary':'예문','examples':['실제 예문','없는 예문'],
             'proposed_record_ids':[],'needs_visual_review':False,'limits':''}
        result=bind_review({'units':[row]},[{'id':'S','text':'실제 예문'}],{'S':[]})
        self.assertEqual(['실제 예문'],result[0]['examples'])
        self.assertTrue(result[0]['needs_visual_review'])
        self.assertEqual(['실제 예문','없는 예문'],row['examples'])
        self.assertEqual('rejected',result[0]['example_binding_audit'][1]['status'])

    def test_source_recovery_quarantines_links_without_inventing_absence(self):
        from review_source_inventory import recover_rows
        row={'id':'S','kind':'example','summary':'예문','examples':['실제 예문'],
             'proposed_record_ids':['VALID','OUTSIDE'],'needs_visual_review':False,'limits':''}
        rows,rejected=recover_rows({'units':[row]},[{'id':'S','text':'실제 예문'}],{'S':['VALID']})
        self.assertFalse(rejected)
        self.assertEqual(['VALID'],rows[0]['proposed_record_ids'])
        self.assertEqual(['OUTSIDE'],rows[0]['record_link_audit']['rejected_ids'])
        self.assertEqual('needs_candidate_review',rows[0]['record_link_audit']['status'])
        self.assertEqual(['VALID','OUTSIDE'],row['proposed_record_ids'])

    def test_source_recovery_isolates_malformed_and_duplicate_units(self):
        from review_source_inventory import recover_rows
        good={'id':'S','kind':'example','summary':'예문','examples':['실제 예문'],
              'proposed_record_ids':[],'needs_visual_review':False,'limits':''}
        bad={**good,'id':'BAD','extra':'not allowed'}
        units=[{'id':x,'text':'실제 예문'} for x in ['S','BAD','MISSING']]
        rows,rejected=recover_rows({'units':[good,bad]},units,{x['id']:[] for x in units})
        self.assertEqual(['S'],[x['id'] for x in rows])
        self.assertEqual({'BAD','MISSING'},{x['id'] for x in rejected})
        rows,_=recover_rows({'units':[good,good]},units,{x['id']:[] for x in units})
        self.assertEqual([],rows)

if __name__=='__main__':unittest.main()

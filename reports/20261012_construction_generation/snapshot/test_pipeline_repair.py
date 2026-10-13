import unittest
from sentence_retrieval import SentenceRetriever,morphology
from preservation_check import check_preservation,generate_checked
from transformation_plan import package_plan

class PipelineRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.engine=SentenceRetriever()

    def item(self,text,function='declarative',act=None):
        return {'id':'UNSEEN','input':text,'clauses':[{'clause_id':'UNSEEN:1','text':text,
            'span':[0,len(text)],'role':'main','features':{'sentence_type':function,'speech_act':act},
            'observed_politeness':'polite','observed_subject_honorific':'unknown','tense_or_modality':'unknown'}]}

    def test_derived_predicate_is_bound_and_keeps_past(self):
        s='그 배가 어제 입항했나요?'
        m=morphology(s);w=next(w for w in m['words'] if w['lemma']=='입항하다')
        self.assertEqual(w['prefinals'],['었']);self.assertEqual(s[slice(*w['span'])],w['surface'])
        p=self.engine.retrieve(self.item(s,'interrogative'),m)['packets']['v2_graph']
        a=next(f for f in p['references'] if f.get('origin')=='model_advice_not_documentary_fact')
        self.assertIn('었',a['input_binding']['ending_conversion']['candidate_morphemes'])

    def test_nominal_ha_is_not_merged_across_whitespace(self):
        self.assertNotIn('설명하다',[w['lemma'] for w in morphology('설명. 하늘이 맑다.')['words']])

    def test_gyeseyo_honorific_predicate_not_copula(self):
        m=morphology('아버지께서 책을 읽고 계세요.')
        hosts=[w for w in m['words'] if w['ending_tag']=='EF']
        self.assertEqual(hosts[-1]['lemma'],'계시다');self.assertNotEqual(hosts[-1]['tag'],'VCP')

    def test_indirect_request_keeps_question_and_original_ending(self):
        item=self.item('이걸 어디에 두면 될까요?','interrogative','request')
        p=self.engine.retrieve(item)['packets']['v2_graph']
        a=next(f for f in p['references'] if f.get('origin'))
        self.assertIn('까예',a['target_pattern']['text'])
        self.assertNotIn('래예',a['target_pattern']['text'])

    def test_listed_raye_does_not_license_promise(self):
        p=self.engine.retrieve(self.item('내일 제가 연락드릴게요.'))['packets']['v2_graph']
        self.assertNotIn('JO2018:v2:informal:0032',[f['id'] for f in p['references']])

    def test_reference_only_support_is_not_transformation_candidate(self):
        item=self.item('제가 읽는 책을 가져왔어요.')
        p=self.engine.retrieve(item)['packets']['v2_graph']
        self.assertIn('RYU2014:v2:full:0098',[f['id'] for f in p['preservation']['supporting_knowledge']])
        self.assertNotIn('RYU2014:v2:full:0098',[f['id'] for f in p['references']])
        packed=package_plan(p,item)
        self.assertTrue(packed['preservation']['relative_clauses'])

    def test_documentary_examples_remain_reference_only(self):
        facts=[f for f in self.engine.facts if ':advisory_examples:' in f['id']]
        self.assertEqual(len(facts),3)
        self.assertTrue(all(f['claim_status']=='attested_example' and f['usability']=='reference_only' for f in facts))

    def test_clear_politeness_loss_triggers_check(self):
        self.assertTrue(check_preservation('기차가 출발했나요?','기차가 출발했나?')['repair_required'])
        self.assertFalse(check_preservation('기차가 출발했나요?','기차가 출발했나예?')['repair_required'])

    def test_attested_ape_and_dae_not_automatically_errors(self):
        self.assertFalse(check_preservation('먼저 갈게요.','앞에 갈게예.')['repair_required'])
        self.assertFalse(check_preservation('맛있더라.','맛있대.')['repair_required'])

    def test_movement_perspective_is_preserved(self):
        c=check_preservation('집에 가는 길에 샀어요.','집에 오는 길에 샀어예.')
        self.assertIn('movement_perspective_changed',[f['kind'] for f in c['flags']])

    def test_eojeol_boundary_prevents_eoje_from_hiding_humility_loss(self):
        c=check_preservation('저는 어제 편지를 썼어요.','나는 어제 편지를 썼어예.')
        self.assertIn('humility_replaced',[f['kind'] for f in c['flags']])

    def test_relative_ending_split_by_standard_analyzer_is_detected(self):
        c=check_preservation('집에 가는 길이 멀다.','집에 가노 길이 멀다.')
        self.assertIn('relative_clause_became_terminal',[f['kind'] for f in c['flags']])

    def test_question_punctuation_is_review_not_automatic_repair(self):
        c=check_preservation('선생님은 이 길로 걸으세요.','선생님은 이 길로 걸으세예?')
        self.assertIn('question_punctuation_changed',[f['kind'] for f in c['flags']])
        self.assertFalse(c['repair_required'])

    def test_only_one_repair_and_failed_repair_is_not_silently_accepted(self):
        calls=[]
        def call(route,req):calls.append(req);return '왔나?' if len(calls)==1 else '왔다.'
        r=generate_checked(call,{'model':'test','messages':[]},'왔나요?',lambda r,m:r)
        self.assertEqual(len(calls),2);self.assertEqual(r['output'],'왔나?')
        self.assertEqual(r['selection'],'first_pass_repair_not_accepted')

if __name__=='__main__':unittest.main()

"""End-to-end lookup checks, including unseen predicates and contrasting functions."""
import json,unittest
from copy import deepcopy
from pathlib import Path
from sentence_retrieval import SentenceRetriever,compact,BUDGET
from transformation_plan import package_plan

class TerminalRetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.engine=SentenceRetriever()

    def item(self,text,fn='declarative',polite='non_polite',qtype=None):
        return {'id':'UNSEEN_TERMINAL','input':text,'clauses':[{
            'clause_id':'UNSEEN_TERMINAL:1','span':[0,len(text)],'text':text,'role':'main',
            'features':{'sentence_type':fn,'question_type':qtype},
            'observed_politeness':polite,'observed_subject_honorific':'unknown','tense_or_modality':'unknown'}]}

    def plans(self,item):
        r=self.engine.retrieve(item)
        return [f['input_binding']['ending_conversion'] for f in r['packets']['v2_graph']['references']
                if f['retrieval_route']=='function_bound_terminal']

    def test_unseen_polite_functions(self):
        cases=[('모두 도착했어요.','declarative','도착했어예'),
               ('공기가 차네요.','declarative','차네예'),
               ('제가 대표예요.','declarative','라예'),
               ('이분은 담당이에요.','declarative','이라예'),
               ('택배가 도착했나요?','interrogative','도착했는교'),
               ('기계가 작아요?','interrogative','작은교'),
               ('길이 길어요?','interrogative','긴교'),
               ('조용히 말씀하세요.','imperative','말씀하이소'),
               ('문을 열어 주세요.','imperative','주이소'),
               ('천천히 걸으세요.','imperative','걸으이소'),
               ('저를 도와주세요.','imperative','주이소'),
               ('제가 편지를 쓸게요.','declarative','쓰께예'),
               ('제가 자료를 읽을게요.','declarative','읽으께예'),
               ('제가 짐을 도울게요.','declarative','도우께예')]
        for text,fn,expected in cases:
            with self.subTest(text=text):
                ps=self.plans(self.item(text,fn,'polite'))
                self.assertEqual(len(ps),1);self.assertEqual(ps[0]['preferred_surface'],expected)
                self.assertTrue(ps[0]['supporting_fact_ids'])

    def test_past_question_and_statement_contrast(self):
        for text,fn,q,out in [('결제를 취소했어.','declarative',None,'취소했다'),
                              ('결제를 취소했어?','interrogative','polar','취소했나'),
                              ('왜 결제를 취소했어?','interrogative','content','취소했노')]:
            with self.subTest(text=text):
                p=self.plans(self.item(text,fn,qtype=q))[0]
                self.assertEqual(p['preferred_surface'],out)
                self.assertIn('었',p['preserve_prefinals'])

    def test_permission_keeps_question_and_negation(self):
        for text,fn,q,out,family in [
            ('오늘 제출해도 돼.','declarative',None,'된다','casual_permission'),
            ('오늘 제출 안 해도 돼.','declarative',None,'된다','casual_permission'),
            ('오늘 제출해도 돼?','interrogative','polar','되나','casual_question'),
            ('이 기계는 잘돼.','declarative',None,'된다','casual_declarative')]:
            with self.subTest(text=text):
                p=self.plans(self.item(text,fn,qtype=q))[0]
                self.assertEqual(p['preferred_surface'],out);self.assertEqual(p['family'],family)
                a,b=p['source_span']
                if '안' in text:self.assertIn('안',text[:a]+p['preferred_surface']+text[b:])
                if '잘' in text:self.assertIn('잘',text[:a]+p['preferred_surface']+text[b:])

    def test_onna_is_request_only_and_requires_matching_lemma(self):
        for text,fn,q,out in [('천천히 와.','imperative',None,'온나'),
                              ('동생이 천천히 와.','declarative',None,'온다'),
                              ('동생이 천천히 와?','interrogative','polar','오나'),
                              ('천천히 자.','imperative',None,'자라')]:
            with self.subTest(text=text):
                self.assertEqual(self.plans(self.item(text,fn,qtype=q))[0]['preferred_surface'],out)

    def test_seyo_is_not_always_a_command(self):
        for fn,out in [('imperative','걸으이소'),('declarative','걸으시예')]:
            self.assertEqual(self.plans(self.item('천천히 걸으세요.',fn,'polite'))[0]['preferred_surface'],out)
        r=self.engine.retrieve(self.item('선생님은 매일 걸으세요.','interrogative','polite','polar'))
        self.assertTrue(any(d['status']=='blocked' for d in r['terminal_decisions']))
        self.assertTrue(r['packets']['v2_graph']['preservation']['terminal_analysis_review'])
        self.assertFalse(self.plans(self.item('선생님은 매일 걸으세요.','interrogative','polite','polar')))

    def test_fused_honorific_and_past_are_kept(self):
        for text,fn,out in [('할아버지께서 계세요.','declarative','계셔예'),
                            ('선생님께서 가셨어요?','interrogative','가셨는교')]:
            self.assertEqual(self.plans(self.item(text,fn,'polite'))[0]['preferred_surface'],out)

    def test_modal_question_is_not_changed_into_command(self):
        p=self.plans(self.item('제가 열까요?','interrogative','polite','polar'))[0]
        self.assertEqual(p['preferred_surface'],'열까예')
        self.assertNotIn('이소',p['preferred_surface'])

    def test_unknown_question_type_fails_closed(self):
        self.assertEqual(self.plans(self.item('일찍 왔어?','interrogative')),[])
        self.assertEqual(self.plans(self.item('일찍 왔어?','declarative')),[])

    def test_documentary_missing_or_failed_condition_fails_closed(self):
        from terminal_retrieval import select
        from sentence_retrieval import morphology,speech_style,kiwi
        item=self.item('천천히 와.','imperative');m=morphology(item['input'])
        host=next(w for w in m['words'] if w['ending_tag']=='EF');clause=item['clauses'][0]
        facts=deepcopy(self.engine.kg.facts)
        fid='JO2018:v2:imperative:0064';facts[fid]['conditions'][0]['value']='가다'
        r=select(host,clause,speech_style(clause,m),{},facts,item['input'],kiwi().join)
        self.assertEqual(r['status'],'blocked')
        del facts[fid]
        self.assertEqual(select(host,clause,speech_style(clause,m),{},facts,item['input'],kiwi().join)['status'],'blocked')

    def test_existing_70_have_no_seye_or_lgeye_terminal_candidates(self):
        root=Path(__file__).resolve().parents[1]
        items=json.loads((root/'reports/20261012_construction_generation/analysis.json').read_text())['items']
        for item in items:
            with self.subTest(id=item['id']):
                r=self.engine.retrieve(item);packet=r['packets']['v2_graph']
                self.assertLessEqual(len(compact(packet)),BUDGET)
                packed=package_plan(packet,item)
                for group in packed['transformation_plan']:
                    for c in group['candidates']:
                        if c['type']!='ending':continue
                        self.assertNotIn('세예',c['target_pattern']['text'])
                        self.assertNotIn('게예',c['target_pattern']['text'])
                        if c['binding'].get('ending_conversion',{}).get('preferred_surface'):
                            plan=c['binding']['ending_conversion'];a,b=plan['source_span']
                            self.assertEqual(item['input'][a:b],plan['source_text'])
                            for fid in plan['supporting_fact_ids']:self.assertIn(fid,self.engine.kg.facts)

    def test_reporting_terminal_does_not_conflict_with_construction_plan(self):
        item=self.item('민수가 왔다고 했어.')
        packed=package_plan(self.engine.retrieve(item)['packets']['v2_graph'],item)
        conversions=[c['binding']['construction_conversion'] for g in packed['transformation_plan']
                     for c in g['candidates'] if c['binding'].get('construction_conversion',{}).get('outer_morphemes')]
        self.assertTrue(conversions)
        for c in conversions:
            self.assertNotIn('preserve_outer_ending',c)
            self.assertEqual(c['terminal_family'],'casual_declarative')

if __name__=='__main__':unittest.main()

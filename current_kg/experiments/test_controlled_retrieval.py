import json
import sys
from pathlib import Path
import unittest
import tempfile
from run_controlled_retrieval import verify_generation_inputs,sha
from run_controlled_retrieval import expansion,add_card,make_request,record_card,BUDGET,GRAMMAR
sys.path.insert(0,str(GRAMMAR))
from build import verify_source_examples

class ControlledTests(unittest.TestCase):
    def test_documented_gaps_do_not_erase_integrity_requirement(self):
        p={'method':'integrated_source_bound_assertion_retrieval_v1',
           'pre_generation_review':{'status':'reviewed_with_documented_gaps'},'prepared_artifact_sha256':{}}
        with self.assertRaises(ValueError):verify_generation_inputs(Path('.'),p)
        p['pre_generation_review'].update(packet_integrity_passed=True,known_gaps=['known model classification error'])
        verify_generation_inputs(Path('.'),p)
        p['pre_generation_review']['status']='pending'
        with self.assertRaises(ValueError):verify_generation_inputs(Path('.'),p)

    def test_documented_gaps_cannot_bypass_frozen_request_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);f=folder/'jobs.json';f.write_text('original')
            p={'method':'integrated_source_bound_assertion_retrieval_v1',
               'pre_generation_review':{'status':'reviewed_with_documented_gaps','packet_integrity_passed':True,'known_gaps':['documented']},
               'prepared_artifact_sha256':{'jobs.json':sha(f)}}
            verify_generation_inputs(folder,p);f.write_text('changed')
            with self.assertRaises(ValueError):verify_generation_inputs(folder,p)
    def test_quote_must_be_on_cited_page_and_unchanged(self):
        k={'evidence':[{'key':'E1','page':2}],'source_examples':[{'text':'밥 무라 카네.','evidence_key':'E1'}]}
        verify_source_examples(k,['없음','원문 밥 무라 카네. 끝'])
        with self.assertRaises(ValueError):verify_source_examples(k,['밥 무라 카네.','없음'])
        with self.assertRaises(ValueError):verify_source_examples(k,['없음','밥 먹으라 카네.'])
    def test_no_shared_hub_or_held_edge_expansion(self):
        edges=[{'id':str(i),'source':a,'target':b,'type':t,'properties':p} for i,(a,b,t,p) in enumerate([
            ('A:F1','concept:QUESTION','realizes',{}),('B:F1','concept:QUESTION','realizes',{}),
            ('A:F1','C:F1','has_inflection_description',{'status':'held_scope_tension'}),
            ('D:F1','A:F1','has_inflection_description',{}),
            ('D:F1','E:F1','has_inflection_description',{})])]
        out=expansion(['A'],{'edges':edges},{k:{} for k in 'ABCDE'})
        self.assertEqual([x['record_id'] for x in out],['D'])
        self.assertEqual(out[0]['direction'],'incoming')
    def test_budget_does_not_partially_cut_condition_card(self):
        packet={'references':[{'id':'seed'}],'graph_paths':[]};before=json.loads(json.dumps(packet))
        self.assertFalse(add_card(packet,{'conditions':'x'*BUDGET}));self.assertEqual(packet,before)
    def test_only_packet_changes_between_record_and_graph_requests(self):
        cfg={'requested_model':'test','generation':{'temperature':.3},'system_prompt':'fixed'}
        item={'input':'원문','clauses':[]};a={'references':[{'id':'A'}],'graph_paths':[]}
        b={'references':[{'id':'A'},{'id':'B'}],'graph_paths':[{'edge':'e'}]}
        x,y=make_request(cfg,item,a),make_request(cfg,item,b)
        self.assertEqual(x['messages'][0],y['messages'][0]);self.assertEqual(x['seed'],y['seed'])
        ux=x['messages'][1]['content'];uy=y['messages'][1]['content']
        self.assertEqual(ux.split('\n')[0],uy.split('\n')[0])
        px,py=[json.loads(t.split('\n',1)[1]) for t in [ux,uy]]
        self.assertEqual(px['standard'],py['standard']);self.assertEqual(px['analysis'],py['analysis'])
        self.assertEqual(px['references'],py['references'][:1])
    def test_real_source_examples_are_separate_from_authored_examples(self):
        graph=json.loads((GRAMMAR/'grammar.graph.json').read_text())
        nodes=[n for n in graph['nodes'] if n['type']=='SourceExample'];self.assertEqual(len(nodes),6)
        for n in nodes:
            self.assertFalse(n['properties']['evaluation_gold']);self.assertFalse(n['properties']['operational'])
            self.assertTrue(any(e['source']==n['id'] and e['type']=='supported_at' for e in graph['edges']))

if __name__=='__main__':unittest.main()

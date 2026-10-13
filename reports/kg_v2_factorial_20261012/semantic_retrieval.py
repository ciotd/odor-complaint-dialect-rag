"""Experimental retrieval extension; fixed guards, new semantic candidate ranking.

No production source edits. The generated retriever diff has two hooks only:
candidate augmentation, and cosine tie-breaking within route/register tiers.
"""
from collections import defaultdict
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'kg_v2'))
from query import assess
from sentence_retrieval import (PRED,HIGH,LOW,speech_style,speech_style_rank,
                               ending_forms,source_forms,ending_conversion,compact)

LABELS={'declarative':'평서 서술','interrogative':'의문 질문','imperative':'명령 지시',
        'propositive':'청유 제안','polar_question':'판정 의문','content_question':'설명 의문',
        'content':'설명 의문','polar':'판정 의문','polite':'청자 높임','non_polite':'청자 비높임',
        'verb':'동사','adjective':'형용사','copula':'명사 서술 지정사','negative_copula':'부정 지정사',
        'present':'현재','past':'과거','future':'미래','request':'요청','intention':'의도',
        'quotation':'인용','reason':'이유','condition':'조건','contrast':'대조',
        'ending':'어미','construction':'구문','lexical_mapping':'어휘 대응','phonology':'음운',
        'subject_honorific':'주체 높임','speech_level':'말씨 등급','function':'문법 기능',
        'sentence_type':'문장 유형','question_type':'질문 유형','speech_act':'화행',
        'has_prefinals':'선어말어미 존재','tense':'시제','lemma':'기본형','pos':'품사'}


def human(value):
    if isinstance(value,dict):return '; '.join(human(k)+': '+human(v) for k,v in value.items() if v is not None)
    if isinstance(value,list):return ', '.join(human(v) for v in value)
    return LABELS.get(str(value),str(value))


def statement_text(f):
    return '\n'.join([
        '지식 유형: '+human(f['type']),
        '입력 표현: '+human(f['source_pattern']),
        '방언 후보: '+human(f['target_pattern']),
        '문법 기능: '+human(f['functions']),
        '적용 조건: '+human(f['conditions']),
        '사용 범위: '+human(f['scope']),
        '추가 제약: '+human(f['constraints'])])


class SemanticIndex:
    def __init__(self,folder):
        os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
        os.environ['HF_HUB_OFFLINE']='1'
        import torch
        from transformers import AutoTokenizer,AutoModel
        self.torch=torch;torch.set_num_threads(4)
        modeldir=ROOT/'current_kg/.runtime/embedding/model'
        self.tokenizer=AutoTokenizer.from_pretrained(str(modeldir),local_files_only=True)
        self.model=AutoModel.from_pretrained(str(modeldir),local_files_only=True).eval()
        self.folder=folder
        self.facts=[json.loads(x) for x in (ROOT/'kg_v2/facts.jsonl').read_text().splitlines()]
        self.rows=[{'id':f['id'],'text':statement_text(f),'source_id':f['source_id'],
                    'evidence_pages':[e['pdf_page'] for e in f['evidence']]} for f in self.facts]
        self.positions={f['id']:i for i,f in enumerate(self.facts)}
        selection=json.loads((modeldir.parent/'model_selection.json').read_text())
        digest=hashlib.sha256(compact({'rows':self.rows,'model':selection,'chunk_tokens':384,'pooling':'mean of normalized chunks, then normalize'}).encode()).hexdigest()
        cache=folder/'local';cache.mkdir(exist_ok=True)
        matrix=cache/('vectors_'+digest[:16]+'.npy')
        chunks=[];owners=[];sizes=[]
        for i,row in enumerate(self.rows):
            offsets=self.tokenizer(row['text'],add_special_tokens=False,return_offsets_mapping=True)['offset_mapping'];sizes.append(len(offsets))
            for start in range(0,len(offsets),384):
                end=min(start+384,len(offsets));chunks.append(row['text'][offsets[start][0]:offsets[end-1][1]]);owners.append(i)
        if matrix.exists():self.vectors=np.load(matrix)
        else:
            parts=[]
            for start in range(0,len(chunks),24):
                parts.append(self.encode(chunks[start:start+24],'passage: '))
                if start%240==0:print('Embedding',start,'/',len(chunks),flush=True)
            chunkvectors=np.concatenate(parts);self.vectors=np.zeros((len(self.rows),chunkvectors.shape[1]),dtype=np.float32)
            for vector,owner in zip(chunkvectors,owners):self.vectors[owner]+=vector
            self.vectors/=np.linalg.norm(self.vectors,axis=1,keepdims=True)
            np.save(matrix,self.vectors)
        assert self.vectors.shape[0]==len(self.rows)
        self.metadata={'model':selection,'fingerprint':digest,'statements':len(self.rows),'chunks':len(chunks),
                       'multi_chunk_statements':sum(s>384 for s in sizes),'max_statement_tokens':max(sizes),
                       'query_prefix':'query: ','document_prefix':'passage: ','similarity':'cosine',
                       'chunk_pooling':'mean of normalized chunks then normalize; no statement text truncation',
                       'evidence_embedding':'quotes excluded; page pointers retained in index records and complete evidence retained in KG/packets'}
        (folder/'semantic_index.json').write_text(json.dumps({'metadata':self.metadata,'records':self.rows},ensure_ascii=False,indent=2)+'\n')
        self.cache={};self.last_audit={}

    def encode(self,texts,prefix):
        lengths=[len(self.tokenizer(prefix+t,add_special_tokens=True)['input_ids']) for t in texts]
        if max(lengths)>512:raise ValueError('Embedding input exceeds fixed token budget')
        batch=self.tokenizer([prefix+t for t in texts],padding=True,truncation=False,return_tensors='pt')
        with self.torch.inference_mode():
            output=self.model(**batch).last_hidden_state;mask=batch['attention_mask'][...,None]
            vectors=(output*mask).sum(1)/mask.sum(1)
            return self.torch.nn.functional.normalize(vectors,p=2,dim=1).numpy()

    def scores(self,query):
        if query not in self.cache:self.cache[query]=self.vectors@self.encode([query],'query: ')[0]
        return self.cache[query]

    def augment(self,engine,item,morph,proposals,propose):
        self.last_audit={'queries':[],'discoveries':[]}
        existing={(p['fact']['id'],tuple(p['binding']['span'])):p for p in proposals}
        def retrieve_unit(query,binding,owners,allowed,kind,style=None,host=None,function=None):
            if not allowed:return
            scores=self.scores(query)
            ranked=sorted(allowed,key=lambda f:(-float(scores[self.positions[f['id']]]),f['id']))
            span=tuple(binding['span'])
            self.last_audit['queries'].append({'kind':kind,'span':list(span),'query':query,'eligible_pool':len(allowed),
                'top12':[{'id':f['id'],'score':float(scores[self.positions[f['id']]])} for f in ranked[:12]]})
            for f in allowed:
                key=(f['id'],span)
                if key in existing:
                    existing[key]['semantic_score']=float(scores[self.positions[f['id']]])
            for f in ranked[:12]:
                score=float(scores[self.positions[f['id']]])
                if (f['id'],span) in existing:continue
                check=assess(f,owners)
                if check['rejected'] or any(c['status']=='unknown' for c in check['conditions']):
                    self.last_audit['discoveries'].append({'id':f['id'],'span':list(span),'score':score,'status':'rejected','checks':check})
                    continue
                base=100 if kind=='lexical' else 60
                bound=deepcopy(binding)
                if kind=='grammar' and f['source_pattern']['features'].get('match_unit')=='terminal_ending':
                    bound['ending_conversion']=ending_conversion(f,host)
                    base=95
                before=len(proposals)
                # Retain the baseline rule: a selected precise conversion suppresses
                # generic function alternatives for that same source binding.
                route='clause_function' if kind=='grammar' and base==60 else 'semantic_'+kind
                propose(f,bound,owners,route,base,style_rank=speech_style_rank(f,style) if style else 0,route_priority=base)
                if len(proposals)>before:
                    proposals[-1]['semantic_score']=score
                    existing[f['id'],span]=proposals[-1]
                    self.last_audit['discoveries'].append({'id':f['id'],'span':list(span),'score':score,'status':'proposed','checks':check})

        for w in morph['words']:
            following=morph['tokens'][w['token_index']+1] if w['token_index']+1<len(morph['tokens']) else None
            particle=following['form'] if following and following['tag'].startswith('J') else None
            binding={'text':w['surface'],'span':w['span'],'lemma':w['lemma'],'prefinals':w['prefinals'],
                     'ending':w['ending'],'predicate_span':w.get('predicate_span'),'following_particle':particle}
            owners={'input':{'lemma':w['lemma'],'following_particle':particle},'candidate':{},'target':{},'context':{}}
            # Retain identity: semantic relatedness alone cannot license synonyms or antonyms.
            allowed=[f for f in engine.facts if f['type'] in {'lexical_mapping','phonology'}
                     and f['usability']=='candidate' and f['source_pattern']['domain'] in {'standard','shared'}
                     and (f['source_pattern']['lemma'] or f['source_pattern']['text'])==w['lemma']]
            context=[u.get('meaning','') for u in item.get('source_units',[]) if u['span'][0]<=w['span'][0]<u['span'][1]]
            query='어휘 방언 대응. 입력 기본형: '+w['lemma']+'; 구간: '+w['surface']+'; 문맥 의미: '+'; '.join(context)[:240]
            retrieve_unit(query,binding,owners,allowed,'lexical')

        for clause in item['clauses']:
            start,end=clause['span'];words=[w for w in morph['words'] if w['tag'] in PRED and start<=w['span'][0]<end]
            if not words:continue
            host=words[-1];style=speech_style(clause,morph)
            features={k:v for k,v in clause['features'].items() if v is not None}
            function=features.get('sentence_type') if clause['role']=='main' else features.get('clause_relation')
            qtype=features.get('question_type');functions={function}
            if function=='interrogative' and qtype in {'polar','content'}:functions.add(qtype+'_question')
            features.update(function=function,sentence_function=function,host_pos=host['pos'],has_prefinals=bool(host['prefinals']))
            candidate={'lemma':host['lemma'],'pos':host['pos'],
                'predicate_class':'nominal_or_copula' if host['tag']=='VCP' else ('negative_copula' if host['tag']=='VCN' else 'predicate_except_negative_copula'),
                'tense_or_retrospective_suffix':any(p in {'었','았','였','겠','더'} for p in host['prefinals'])}
            owners={'input':features,'candidate':candidate,'target':{},'context':{}}
            binding={'text':clause['text'],'span':clause['span'],'clause_id':clause['clause_id'],
                     'host_lemma':host['lemma'],'ending':host['ending'],'speech_style_preference':style}
            forms=ending_forms(host,function);allowed=[]
            for f in engine.facts:
                if f['type'] not in {'ending','construction'} or f['usability']!='candidate':continue
                sp=f['source_pattern'];literal=sp['domain'] in {'standard','shared'} and sp['text'].startswith('-') and bool(source_forms(sp['text']) & forms)
                if sp['features'].get('match_unit')=='terminal_ending' and (not literal or host['ending_tag']!='EF' or clause['role']!='main' or function not in f['functions']):continue
                if not literal and not set(f['functions']) & functions:continue
                if features.get('speech_act')=='request' and function=='interrogative' and not literal:continue
                levels=set(f['scope']['speech_levels']);polite=style['politeness']
                if levels and ((polite=='polite' and not levels & HIGH) or (polite=='non_polite' and not levels & LOW) or polite=='unknown'):continue
                if not literal and qtype and f['functions'] and not set(f['functions']) & {qtype+'_question','interrogative'}:continue
                allowed.append(f)
            query='문법 변환 지식. '+human({'문법 기능':sorted(functions,key=str),'서술어 품사':host['pos'],
                '입력 종결 연결 표현':host['ending'],'선어말':host['prefinals'],'시제 양태':clause['tense_or_modality'],
                '청자 말투':style,'주체 높임':clause['observed_subject_honorific'],'화행':features.get('speech_act')})
            retrieve_unit(query,binding,owners,allowed,'grammar',style,host,function)


def load_experimental_retriever(folder,index):
    source=(folder/'snapshots/sentence_retrieval.py').read_text()
    anchor='        proposals.sort(key=lambda p: (-p[\'route_priority\'], -p[\'style_rank\'],\n'
    assert source.count(anchor)==1
    source=source.replace(anchor,"        self.semantic_index.augment(self, item, morph, proposals, propose)\n"+anchor)
    anchor="                                      -p['priority'], p['fact']['id']))"
    assert source.count(anchor)==1
    source=source.replace(anchor,"                                      -p.get('semantic_score', 0.0), -p['priority'], p['fact']['id']))")
    path=folder/'snapshots/experimental_retriever.py';path.write_text(source)
    spec=importlib.util.spec_from_file_location('factorial_retriever',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    engine=module.SentenceRetriever(ROOT/'kg_v2');engine.semantic_index=index
    return engine

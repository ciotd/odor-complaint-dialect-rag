"""Pinned, local multilingual E5 retrieval for controlled development comparisons.

All methods search the same exact source-bound chunks; no text leaves this process.
"""
import hashlib
import json
import math
import os
from pathlib import Path
from collections import Counter
import time

import numpy as np

from source_retrieval import SourceIndex,tokens

BASE=Path(__file__).resolve().parent
RUNTIME=BASE.parent/'.runtime/embedding'


def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode()).hexdigest()


def query_text(item):
    # Fixed pre-search serialization. No gold IDs, target dialect output, or manual repairs.
    units=item.get('source_units',[])
    descriptions=[u.get('meaning','') for u in units]
    clauses=[{'원문':c['text'],'문법특징':{k:v for k,v in c['features'].items() if v is not None},'관찰높임':c.get('observed_politeness'),
              '시제양태':c.get('tense_or_modality')} for c in item['clauses']]
    return '표준어: '+item['input']+'\n구성 설명: '+'; '.join(descriptions)+'\n분석: '+json.dumps(clauses,ensure_ascii=False,separators=(',',':'))


class EmbeddingIndex:
    def __init__(self):
        os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
        import torch
        from transformers import AutoTokenizer,AutoModel
        self.torch=torch;torch.set_num_threads(4)
        self.tokenizer=AutoTokenizer.from_pretrained(str(RUNTIME/'model'),local_files_only=True)
        self.model=AutoModel.from_pretrained(str(RUNTIME/'model'),local_files_only=True).eval()
        self.source=SourceIndex()
        self.model_selection=json.loads((RUNTIME/'model_selection.json').read_text())
        self.chunks=[]
        for key,doc in self.source.docs.items():
            raw=doc['text'];offsets=self.tokenizer(raw,add_special_tokens=False,return_offsets_mapping=True)['offset_mapping']
            for start in range(0,len(offsets),320):
                end=min(start+384,len(offsets));left=offsets[start][0];right=offsets[end-1][1]
                text=raw[left:right]
                if not text.strip():continue
                self.chunks.append({'id':f'{key}@{left}:{right}','document_id':key,'kind':doc['type'],
                                    'span':[left,right],'text':text})
                if end==len(offsets):break
        self.fingerprint=digest({'chunks':self.chunks,'model':self.model_selection,'prefix':'passage: ','max_tokens':512})
        self.cache=RUNTIME/('index_'+self.fingerprint[:16]);self.cache.mkdir(exist_ok=True)
        matrix=self.cache/'vectors.npy'
        if matrix.exists():self.vectors=np.load(matrix)
        else:
            vectors=[];started=time.monotonic()
            for i in range(0,len(self.chunks),24):
                vectors.append(self.encode([c['text'] for c in self.chunks[i:i+24]],'passage: '))
                if i%240==0:print(f'Embedding chunks {i}/{len(self.chunks)} elapsed={time.monotonic()-started:.1f}s',flush=True)
            self.vectors=np.concatenate(vectors);np.save(matrix,self.vectors)
            (self.cache/'chunks.json').write_text(json.dumps(self.chunks,ensure_ascii=False))
        if self.vectors.shape!=(len(self.chunks),self.model.config.hidden_size):raise ValueError('Embedding cache shape mismatch')
        self.counts=[tokens(c['text']) for c in self.chunks]
        df=Counter(t for c in self.counts for t in c)
        self.idf={t:math.log(1+(len(self.chunks)-n+.5)/(n+.5)) for t,n in df.items()}
        self.length=np.array([sum(c.values()) for c in self.counts]);self.avg=float(self.length.mean())
        self.query_cache={};self.query_audit={}

    def encode(self,texts,prefix):
        batch=self.tokenizer([prefix+t for t in texts],padding=True,truncation=True,max_length=512,return_tensors='pt')
        with self.torch.inference_mode():
            output=self.model(**batch).last_hidden_state
            mask=batch['attention_mask'][...,None]
            vec=(output*mask).sum(1)/mask.sum(1)
            vec=self.torch.nn.functional.normalize(vec,p=2,dim=1)
        return vec.numpy()

    def search_all(self,query,kind='kg_record',limit=6):
        original=query
        offsets=self.tokenizer(query,add_special_tokens=False,return_offsets_mapping=True)['offset_mapping']
        # Same bounded input for lexical and dense, leaving room for prefix/special tokens.
        if len(offsets)>480:query=query[:offsets[479][1]]
        if query not in self.query_cache:
            self.query_cache[query]=self.encode([query],'query: ')[0]
        length=len(self.tokenizer('query: '+query)['input_ids'])
        if length>512:raise ValueError('Shared query exceeds encoder budget')
        self.query_audit[original]={'original_content_tokens':len(offsets),'effective_tokens_with_prefix':length,
                                    'truncated':query!=original,'effective_query':query}
        dense=self.vectors@self.query_cache[query]
        q=tokens(query)
        lexical=[sum(self.idf[t]*c[t]*2.2/(c[t]+1.2*(.25+.75*self.length[i]/self.avg)) for t in q if t in c)
                 for i,c in enumerate(self.counts)]
        by_doc={'lexical':{},'dense':{}}
        for method,scores in [('lexical',lexical),('dense',dense)]:
            for i,c in enumerate(self.chunks):
                if c['kind']!=kind or (method=='lexical' and scores[i]<=0):continue
                entry={'id':c['document_id'],'chunk_id':c['id'],'span':c['span'],'score':float(scores[i]),'text':c['text']}
                prev=by_doc[method].get(c['document_id'])
                if prev is None or entry['score']>prev['score']:by_doc[method][entry['id']]=entry
        ranked={m:sorted(d.values(),key=lambda x:(-x['score'],x['id'])) for m,d in by_doc.items()}
        merged={}
        for m,hits in ranked.items():
            for rank,h in enumerate(hits[:50],1):
                v=merged.setdefault(h['id'],{**h,'score':0.,'component_ranks':{}})
                v['score']+=1/(60+rank);v['component_ranks'][m]=rank
        ranked['hybrid']=sorted(merged.values(),key=lambda x:(-x['score'],x['id']))
        return {m:rs[:limit] for m,rs in ranked.items()}

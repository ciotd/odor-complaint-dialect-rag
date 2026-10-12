"""Preserve every approved PDF page and bounded units; audit links, not semantic coverage.

Raw text stays local. A page citation or shared surface is not a verified support edge.
"""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
EVIDENCE = BASE / 'source_evidence'
REPORTS = BASE.parent / 'experiments/reports/source_expansion'
FUNCTIONS = {'DECLARATIVE','INTERROGATIVE','IMPERATIVE','HORTATIVE','EXCLAMATIVE',
             'POLAR_QUESTION','CONTENT_QUESTION','REQUEST','INTENTION','CONDITION','CAUSE'}
SLOTS = {'clause.final_ending', 'clause.connective'}


def digest(data):
    return hashlib.sha256(data if isinstance(data,bytes) else data.encode()).hexdigest()


def normalized(text):
    return re.sub(r'[^가-힣A-Za-z0-9]', '', text).lower()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    temp.replace(path)


def event(message):
    REPORTS.mkdir(parents=True,exist_ok=True)
    line='[문헌 대응] '+message
    print(line,flush=True)
    with (REPORTS/'progress.txt').open('a') as f:f.write(line+'\n')


def split_page(text, max_chars=1300):
    """Contiguous, exact offsets cover ALL extracted characters, including whitespace.

    Prefer paragraph boundaries, retaining layout. A split is a search window, not a
    claim that a table/example has been correctly reconstructed. Page remains whole.
    """
    start=0
    while start<len(text):
        end=min(len(text),start+max_chars)
        if end<len(text):
            boundary=text.rfind('\n\n',start+max_chars//3,end)
            if boundary<0:boundary=text.rfind('\n',start+max_chars//3,end)
            if boundary>=0:end=boundary+1
        yield start,end,text[start:end]
        start=end


def structural_routes(record):
    result=[]
    for i,a in enumerate(record['knowledge']['relations'],1):
        entry=a['predicate']=='realizes' and a['object'].get('ref') in FUNCTIONS and a['application']['target'] in SLOTS
        result.append({'assertion_id':record['id']+':A'+str(i),'predicate':a['predicate'],
                       'target':a['application']['target'],'legacy_function_entry':entry,
                       'status':'entry_present_conditions_not_evaluated' if entry else 'outside_legacy_entry',
                       'condition_fields':sorted({c['field'] for group in a['conditions'].values() for c in group})})
    return result


def build_inventory():
    records=[json.loads(l) for l in (BASE/'records.jsonl').read_text().splitlines()]
    sources=[s for s in json.loads((BASE/'source_registry.json').read_text())['sources']
             if s.get('eligible_for_claims') and s['file']['path'].endswith('.pdf')]
    bypage=defaultdict(list)
    for r in records:
        for ev in r['knowledge']['evidence']:bypage[(r['source_id'],ev['page'])].append(r)
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    units=[]; pages=[];links=[];source_summary=[]
    for source in sources:
        sid=source['source_id'];path=ROOT/source['file']['path']
        file_hash=digest(path.read_bytes())
        if file_hash!=source['file']['sha256']:raise ValueError('Source hash mismatch: '+sid)
        raw=subprocess.check_output(['pdftotext','-layout',str(path),'-'],text=True)
        texts=raw.split('\f')
        if texts and not texts[-1].strip():texts.pop()
        if len(texts)!=source['file']['pages']:raise ValueError('Page count mismatch: '+sid)
        count_before=len(units)
        for page_no,text in enumerate(texts,1):
            page_id=f'source:{sid}:p{page_no}'
            cited={r['id']:r for r in bypage[(sid,page_no)]}
            page={'id':page_id,'type':'SourcePage','source_id':sid,'pdf_page':page_no,
                  'source_path':source['file']['path'],'text':text,'text_sha256':digest(text),
                  'citing_record_ids':sorted(cited),'review_status':'extracted_not_semantically_reviewed'}
            pages.append(page)
            parts=list(split_page(text))
            if ''.join(t for _,_,t in parts)!=text:raise ValueError('Lost page text')
            for n,(start,end,part) in enumerate(parts,1):
                uid=page_id+':u'+str(n)
                matches=[]
                for rid,r in cited.items():
                    forms=[f['text'] for f in r['knowledge']['forms']
                           if len(normalized(f['text']))>=2 and normalized(f['text']) in normalized(part)]
                    if forms:matches.append({'record_id':rid,'matched_forms':forms})
                hints=[]
                if re.search(r'표\s*\d|\S\s{3,}\S',part):hints.append('possible_table_or_layout')
                if re.search(r'예[문시]|[ㄱㄴㄷ]\. |[“「]',part):hints.append('possible_example')
                u={'id':uid,'type':'SourceUnit','source_id':sid,'pdf_page':page_no,
                   'source_path':source['file']['path'],'page_id':page_id,'span':[start,end],
                   'text':part,'text_sha256':digest(part),'kind_hints':hints,
                   'citing_record_ids':sorted(cited),'surface_link_candidates':matches,
                   'alignment_status':'surface_overlap_on_cited_page' if matches else 'same_cited_page_only' if cited else 'no_existing_page_citation',
                   'semantic_coverage':'unreviewed','rule_authority':False}
                units.append(u)
                links.append({'source':uid,'type':'part_of','target':page_id})
                for m in matches:
                    links.append({'source':m['record_id'],'type':'surface_overlap_candidate','target':uid,
                                  'matched_forms':m['matched_forms'],'support_verified':False})
            for rid in cited:links.append({'source':rid,'type':'cites_page','target':page_id,'support_verified':False})
        source_summary.append({'source_id':sid,'path':str(path.relative_to(ROOT)),'sha256':file_hash,
                               'pages':len(texts),'units':len(units)-count_before})
        event(f"{sid}: {len(texts)}쪽 / {len(units)-count_before}개 검색 단위 보존. 페이지 본문 복원 일치.")
    for name,data in [('pages.jsonl',pages),('units.jsonl',units)]:
        temp=EVIDENCE/(name+'.tmp')
        with temp.open('w') as f:
            for row in data:f.write(json.dumps(row,ensure_ascii=False)+'\n')
        temp.replace(EVIDENCE/name)
    route_rows=[{'record_id':r['id'],'source_id':r['source_id'],'label':r['knowledge']['label'],
                 'source_evidence':r['knowledge']['evidence'],'routes':structural_routes(r),
                 'declared_gaps':r['knowledge']['gaps'],
                 'gap_status':'author_declared_not_revalidated'} for r in records]
    write_json(EVIDENCE/'links.json',{'edges':links,'record_routes':route_rows})
    with (EVIDENCE/'alignment.tsv').open('w') as f:
        w=csv.writer(f,delimiter='\t');w.writerow(['unit_id','source_id','pdf_page','alignment_status','same_page_records','surface_overlap_records','semantic_coverage'])
        for u in units:w.writerow([u['id'],u['source_id'],u['pdf_page'],u['alignment_status'],','.join(u['citing_record_ids']),','.join(x['record_id'] for x in u['surface_link_candidates']),u['semantic_coverage']])
    summary={'version':'1.0','sources':source_summary,'pages':len(pages),'units':len(units),
             'records':len(records),'alignment_counts':dict(Counter(u['alignment_status'] for u in units)),
             'assertion_routes':dict(Counter(a['status'] for r in route_rows for a in r['routes'])),
             'records_sha256':digest((BASE/'records.jsonl').read_bytes()),
             'script_sha256':digest(Path(__file__).read_bytes()),
             'units_sha256':digest((EVIDENCE/'units.jsonl').read_bytes()),
             'pages_sha256':digest((EVIDENCE/'pages.jsonl').read_bytes()),
             'links_sha256':digest((EVIDENCE/'links.json').read_bytes()),
             'limitations':['Full PDF text extraction is not a full semantic review.',
                            'Units are search windows, not certified table rows or individual examples.',
                            'An uncited unit may be background/reference material, not missing grammar.',
                            'A cited page or surface overlap does not prove support or completeness.']}
    write_json(EVIDENCE/'summary.json',summary)
    for needle in ['캤다','카데','카더래']:
        hits=[u for u in units if needle in u['text']]
        for u in hits[:2]:
            start=u['text'].index(needle);snippet=u['text'][max(0,start-35):start+len(needle)+35].replace('\n',' ')
            event(f"실제 사례 {u['source_id']} {u['pdf_page']}쪽: {snippet} → {u['alignment_status']} / 원문을 보존하되 적용 규칙으로 자동 승인하지 않음")
    event(f"완료: {len(sources)}종 {len(pages)}쪽, {len(units)}개 단위. 의미 누락 확정 건수가 아니라 검토용 대응 목록입니다.")
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--build',action='store_true');args=parser.parse_args()
    if args.build:build_inventory()
    else:print('Use --build to extract approved local PDFs and write the correspondence inventory.')

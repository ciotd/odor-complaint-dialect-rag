"""Coordinator audit: provenance, model proposals, counterexamples, measured inputs."""
import hashlib
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(name,value):(HERE/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def strings(value):
    if isinstance(value,str):yield value
    elif isinstance(value,dict):
        for v in value.values():yield from strings(v)
    elif isinstance(value,list):
        for v in value:yield from strings(v)


def main():
    advisor=read(HERE/'advisor.json');critic=read(HERE/'counterexamples.json');literature=read(HERE/'literature.json')
    stats=read(HERE/'retrieval_statistics.json')
    facts={f['id']:f for f in (json.loads(l) for l in (ROOT/'kg_v2/facts.jsonl').read_text().splitlines())}
    pages={(p['source_id'],p['pdf_page']):p for p in (json.loads(l) for l in (ROOT/'kg_v2/local/pages.jsonl').read_text().splitlines())}
    quote_checks=[]
    for issue in literature['items']:
        assert all(fid in facts for fid in issue['related_fact_ids'])
        for q in issue['exact_quotes']:
            page=pages[q['source_id'],q['pdf_page']]
            assert q['text'] in page['text'],(issue['id'],q)
            quote_checks.append({'issue':issue['id'],'source_id':q['source_id'],'pdf_page':q['pdf_page'],
                                 'exact_match':True,'page_text_sha256':page['text_sha256']})
    model_examples=[]
    for item in critic['items']:
        for pair in item['minimal_pairs']:
            for row in pair['inputs']:
                model_examples.append({**row,'counterexample_issue':item['id'],'pair_id':pair['pair_id'],
                    'must_preserve_difference':pair['must_preserve_difference'],
                    'origin':'model_authored_probe_not_human_gold','generation_status':'not_run'})
    original=read(ROOT/'reports/kg_v2_factorial_20261012/analysis.json')['items']
    assert len(model_examples)==20 and len({r['id'] for r in model_examples})==20
    assert not {r['input'] for r in model_examples}&{r['input'] for r in original}
    normalized={fid:re.sub(r'\s+','',' '.join(strings(f))) for fid,f in facts.items()}
    expression_hits={word:[fid for fid,text in normalized.items() if word in text]
                     for word in ['가세예','보실래예','맛있지예']}
    assert not expression_hits['가세예'] and not expression_hits['보실래예']
    assert '가세예' in pages['NAMU_HONORIFICS_20260908',26]['text']
    assert '보실래예' in re.sub(r'\s+','',pages['NAMU_HONORIFICS_20260908',26]['text'])
    # Exact candidates and evidence are immutable; evaluation corrections live separately.
    protocol=read(ROOT/'reports/kg_v2_factorial_20261012/protocol.json')
    assert all(sha(ROOT/path)==digest for path,digest in protocol['dependencies'].items())
    for path,digest in stats['source_hashes'].items():
        assert sha(ROOT/'reports/kg_v2_factorial_20261012'/path)==digest
    mapping={'ADV001':['LIT05'],'ADV002':['LIT04'],'ADV003':['LIT03','LIT05'],
             'ADV004':['LIT01','LIT03'],'ADV005':['LIT01','LIT02','LIT05'],
             'ADV006':['LIT05'],'ADV007':['LIT08'],'ADV008':['LIT06'],'ADV009':['LIT09','LIT10']}
    reviews={r['proposal_id']:r for r in critic['advisor_review']}
    supplemental=[]
    for proposal in advisor['proposals']:
        pid=proposal['id'];review=reviews[pid]
        supplemental.append({'id':pid,'origin':'model_advice_not_documentary_fact',
            'proposal':proposal,'counterexample_review':review,'related_documentary_issues':mapping[pid],
            'coordinator_status':'design_accepted_for_diagnostic' if review['decision']=='accept' else 'refinement_required_before_diagnostic',
            'source_support_boundary':'Linked documentary issues support specific components only; they do not attest every generated example or the entire proposed rule.',
            'production_KG_active':False,'linguistic_gold':False})
    save('reviewed_advice.json',{'status':'advisory_layer_compiled_not_production_rules','items':supplemental})
    save('new_contrast_probes.json',{'origin':'model_authored_not_independent_gold','status':'not_run','items':model_examples})
    save('coordinator_validation.json',{
        'status':'passed','role_configuration':'3 separate workers + primary coordinator; inherited session model, no explicit override',
        'advice_count':len(supplemental),'counterexample_issue_count':len(critic['items']),
        'literature_issue_count':len(literature['items']),'exact_source_quote_checks':quote_checks,
        'new_contrast_inputs':len(model_examples),'new_inputs_overlap_previous50':0,
        'production_KG_code_previous_experiments_unchanged':True,
        'whitespace_normalized_fact_search':expression_hits,
        'coordinator_direct_image_checks':[{'source_id':s,'pdf_page':p} for s,p in [('RYU2014',27),('RYU2014',20),('NAMU_GRAMMAR_20260908',28),('NAMU_HONORIFICS_20260908',26)]],
        'limitations':['Role separation is not independent human validation.',
                      f'{len(quote_checks)} quotes and targeted pages checked, not a full semantic re-audit of 474 pages.',
                      'No new Qwen translations in this advisory round; no measured new translation improvement.',
                      'Exact string absence indicates missing attested examples; it does not establish absence of every equivalent abstract rule.'],
        'input_hashes':{n:sha(HERE/n) for n in ['advisor.json','counterexamples.json','literature.json','retrieval_statistics.json']}})
    lines=['실제 조회량 측정 결과','',
        '자료: 직전 factorial 실험 jobs.json의 실제 user 메시지를 역직렬화하여 집계.',
        '50개 입력은 DEV30+LONG8+NEW12이다. 여러 문장으로 된 발화도 입력 ID 하나로 센다.',
        '구간은 1개 이상 후보가 전달된 고유 원문 span이다. 어휘 구간과 절 구간은 겹칠 수 있다.',
        '구간수 평균에는 후보 0개인 입력 3개도 포함한다. 구간당 후보 평균은 총 후보/총 전달구간이다.',
        '문자수는 공백·JSON키·인용·이스케이프를 포함한 실제 compact JSON 길이이며 토큰수/바이트수가 아니다.',
        '후보 묶음은 같은 span의 후보들을 배열로 직렬화한 길이. 공유 그래프경로·전체분석·프롬프트는 제외.',
        'C/D의 구간 공통 보존지침은 후보 배열 밖에 있으므로 별도 길이를 함께 제시한다.',
        '평균 최대값 = 각 입력의 가장 긴 후보 구간 길이를 구한 뒤 입력 전체에서 평균. 후보0인 입력은0자.',
        '24,000자는 입력 전체 references+graph_paths 한도이다. 구간별 한도도 전체 프롬프트 한도도 아니다.',
        '후보 선택 중 관계 경로용2,000자를 유보하며 C/D 재구성패킷에는 별도의24,000자 제한이 없다.','']
    for cohort,by in stats['summary'].items():
        lines.append(cohort)
        lines.append('조건 | 입력수 | 전달구간총수 | 입력당구간평균 | 후보총수 | 구간당후보평균 | 구간후보묶음평균자 | 입력별최대구간의평균자 | 관측최대구간자')
        for c,r in by.items():
            lines.append(f"{c} | {r['input_count']} | {r['delivered_segment_count_total']} | {r['delivered_segments_per_input_mean_including_zero']:.4f} | {r['candidate_count_total']} | {r['candidates_per_delivered_segment_pooled_mean']:.4f} | {r['candidate_array_characters_per_segment_mean']:.2f} | {r['per_input_largest_segment_characters_mean_including_zero']:.2f} | {r['candidate_array_characters_largest_segment']}")
        lines.append('')
    lines+=['50개 전체의 추가 길이 통계:',
            '조건 | 구간공통정보포함평균자 | 참고패킷평균자 | 참고패킷최대자 | user메시지평균자 | user메시지최대자']
    for c,r in stats['summary']['all50'].items():
        lines.append(f"{c} | {r['segment_representation_characters_mean']:.2f} | {r['packet_characters_mean']:.2f} | {r['packet_characters_max']} | {r['user_message_characters_mean']:.2f} | {r['user_message_characters_max']}")
    lines+=['','후보수 제한과 길이 제한:',
        'A/C는 150구간 중35구간, B/D는160구간 중37구간이 실제6개 후보를 받았다.',
        '개수 제한 탈락 기록이 있는 입력: A31개/B33개. 길이 제한 탈락 기록이 있는 입력: A10개/B12개.',
        '탈락 기록은 고유한 유효 규칙 수나 반드시 필요한 규칙의 누락 수가 아니다.',
        '평균 후보수가6미만이어도 특정구간은 상한에 도달한다. 평균분량만으로 적정량 판정은 불가.',
        '상세 원자료: segment_lengths.tsv, input_lengths.tsv. 재현: measure_retrieval.py 실행.']
    (HERE/'statistics.txt').write_text('\n'.join(lines)+'\n')
    print('Coordinator audit passed:',len(supplemental),'advice,',len(quote_checks),'quotes,',len(model_examples),'new probes.')


if __name__=='__main__':main()

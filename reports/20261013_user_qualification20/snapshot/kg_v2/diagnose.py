"""Save concrete query paths and an explicit list of extraction gaps."""
from collections import Counter
import hashlib
import json

from query import BASE, KG


def save(name, value):
    (BASE/'reports'/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')


def main():
    kg = KG()
    cases = []
    for lemma, ending in [('먹다', '-고'), ('먹다', '-아/어라'), ('버리다', '-고'),
                          ('데우다', '-고'), ('내리다', '-고'), ('빠뜨리다', '-고'), ('먹다', '-없는어미')]:
        result = kg.lexical_paths(lemma, ending)
        cases.append({'request': result['request'], 'surfaces': sorted({p['surface'] for p in result['paths']}),
                      'paths': [{k:p[k] for k in ['lexical_id','inflection_id','surface','selected_candidate',
                                                'checks','review_reasons','generation_approved']} for p in result['paths']],
                      'rejected_path_count': len(result['rejected_paths']),
                      'lexical_without_inflection': result['lexical_without_inflection']})
    fs = list(kg.facts.values())
    save('query_diagnostics.json', {
        'facts_sha256': hashlib.sha256((BASE/'facts.jsonl').read_bytes()).hexdigest(),
        'graph_sha256': hashlib.sha256((BASE/'graph.json').read_bytes()).hexdigest(),
        'input_analysis': 'manually supplied lemma and requested ending; no sentence parser involved',
        'lexical_statements': sum(f['type']=='lexical_mapping' for f in fs),
        'lexical_statements_with_structural_inflection_edges': len(kg.links),
        'structural_inflection_edges': sum(map(len, kg.links.values())),
        'usability_counts': dict(Counter(f['usability'] for f in fs)),
        'cases': cases, 'translation_quality': 'not evaluated',
        'interpretation': 'A path is a reviewable source-grounded candidate, not a validated translation rule.'})
    gaps = []
    for path in sorted((BASE/'reviews').glob('*.json')):
        doc = json.loads(path.read_text())
        for page in doc['pages']:
            if page['gaps']:
                gaps.append({'source_id': doc['source_id'], **page})
    save('extraction_gaps.json', {'gap_pages': len(gaps), 'pages': gaps,
        'note': 'All pages have been read; these are explicit limits of semantic extraction and source interpretation.'})
    print(json.dumps({'query_cases':len(cases),'gap_pages':len(gaps),
                      'paths':[{**c['request'],'surfaces':c['surfaces']} for c in cases]},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()

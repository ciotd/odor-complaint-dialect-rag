"""Trace source-grounded candidates in KG v2; this is not a sentence translator."""
import argparse
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
MISSING = object()


def evaluate_conditions(conditions, owners):
    """Unknown analysis must not silently satisfy a condition."""
    results = []
    for c in conditions:
        actual = owners.get(c['owner'], {}).get(c['field'], MISSING)
        if actual is MISSING:
            status = 'unknown'
        else:
            op, expected = c['op'], c['value']
            if op == 'exists':
                passed = (actual is not None) == expected
            elif actual is None:
                results.append({**c, 'actual': None, 'status': 'unknown'})
                continue
            elif op == 'eq':
                passed = actual == expected
            elif op == 'in':
                passed = actual in expected
            elif op == 'not_in':
                passed = actual not in expected
            else:
                raise ValueError('Unknown condition operator: ' + op)
            status = 'satisfied' if passed else 'failed'
        results.append({**c, 'actual': None if actual is MISSING else actual, 'status': status})
    return results


def assess(fact, owners):
    checks = evaluate_conditions(fact['conditions'], owners)
    rejected = fact['usability'] != 'candidate' or fact['claim_status'] == 'negative_example'
    rejected = rejected or any(c['status'] == 'failed' for c in checks)
    review = []
    if any(c['status'] == 'unknown' for c in checks):
        review.append('missing_structured_analysis')
    if fact['constraints']:
        review.append('textual_constraints_require_review')
    if any(fact['scope'].values()):
        review.append('source_scope_requires_review')
    if fact['claim_status'] in {'analyst_interpretation', 'author_hypothesis', 'secondary_report'}:
        review.append('claim_status_requires_review')
    if any(c['basis'] == 'analyst_interpretation' for c in checks):
        review.append('interpreted_condition_requires_review')
    if fact['source_pattern']['sense'] or fact['target_pattern']['sense']:
        review.append('sense_requires_review')
    return {'rejected': rejected, 'conditions': checks, 'review_reasons': review}


class KG:
    def __init__(self, base=BASE):
        self.facts = {f['id']: f for f in
                      (json.loads(line) for line in (base/'facts.jsonl').read_text().splitlines())}
        graph = json.loads((base/'graph.json').read_text())
        self.links = {}
        for e in graph['edges']:
            if e['type'] == 'candidate_has_inflection':
                self.links.setdefault(e['source'], []).append(e)

    def lexical_paths(self, lemma, ending=None, *, lexical_id=None,
                      input_features=None, target=None, context=None):
        """Walk compiled graph edges. Lemma/ending are supplied analysis, not guessed."""
        paths, rejected, lexical_without_inflection = [], [], []
        inputs = {**(input_features or {}), 'lemma': lemma}
        for lex in self.facts.values():
            p = lex['source_pattern']
            if lex['type'] != 'lexical_mapping' or p['domain'] not in {'standard', 'shared'}:
                continue
            if (p['lemma'] or p['text']) != lemma or (lexical_id and lex['id'] != lexical_id):
                continue
            tp = lex['target_pattern']
            selected = {**tp['features'], 'lemma': tp['lemma'] or tp['text'], 'host_form': tp['text']}
            if ending is not None:
                selected['ending'] = ending
            owners = {'input': inputs, 'candidate': selected, 'target': target or {}, 'context': context or {}}
            lexcheck = assess(lex, owners)
            if not self.links.get(lex['id']):
                lexical_without_inflection.append(lex['id'])
            for edge in self.links.get(lex['id'], []):
                inf = self.facts[edge['target']]
                infcheck = assess(inf, owners)
                item = {'lexical_id': lex['id'], 'inflection_id': inf['id'],
                        'input_lemma': lemma, 'selected_candidate': selected,
                        'surface': inf['target_pattern']['text'], 'edge': edge,
                        'checks': {'lexical': lexcheck, 'inflection': infcheck},
                        'statements': [lex, inf], 'status': 'needs_review',
                        'generation_approved': False}
                # A lexical identity alone cannot guarantee sense/scope compatibility.
                item['review_reasons'] = sorted(set(lexcheck['review_reasons'] + infcheck['review_reasons']
                    + ['cross_statement_sense_and_scope', 'generation_not_validated']))
                if lexcheck['rejected'] or infcheck['rejected']:
                    item['status'] = 'rejected'
                    rejected.append(item)
                else:
                    paths.append(item)
        return {'request': {'lemma': lemma, 'ending': ending, 'lexical_id': lexical_id},
                'paths': paths, 'rejected_paths': rejected,
                'lexical_without_inflection': lexical_without_inflection,
                'limitations': ['Input morphology is supplied explicitly.',
                    'Textual constraints, senses and regions are not automatically resolved.',
                    'No unattested forms or full sentences are generated.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lemma', required=True)
    parser.add_argument('--ending', help='Use --ending=-고 for an ending beginning with a hyphen')
    parser.add_argument('--lexical-id', help='Explicitly select a reviewed lexical statement, if desired')
    args = parser.parse_args()
    print(json.dumps(KG().lexical_paths(args.lemma, args.ending, lexical_id=args.lexical_id),
                     ensure_ascii=False, indent=2))

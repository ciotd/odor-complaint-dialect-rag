"""Formatting helpers for explicitly authored facts, not automatic interpretation."""
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent


def normalize(text):
    return re.sub(r'\s+', '', text)


def pattern(text, domain='standard', lemma=None, sense=None, **features):
    return dict(text=text, domain=domain, lemma=lemma, sense=sense, features=features)


class Author:
    def __init__(self, source, stem, regions=()):
        self.source, self.stem, self.regions = source, stem, list(regions)
        self.facts, self.reviews = [], []
        self.pages = {p['pdf_page']: p['text'] for p in
                      (json.loads(line) for line in (BASE/'local/pages.jsonl').read_text().splitlines())
                      if p['source_id'] == source}

    def fact(self, kind, source, target, page, quote, *, functions=(), conditions=(),
             constraints=(), status='source_generalization', usability='candidate',
             notes='', regions=None, levels=(), scope_note='', evidence=()):
        refs = [{'pdf_page':page,'quote':quote}, *evidence]
        for ref in refs:
            if normalize(ref['quote']) not in normalize(self.pages[ref['pdf_page']]):
                raise ValueError(f"Unbound quote: {self.source} p{ref['pdf_page']}: {ref['quote']}")
        fact = dict(id=f'{self.source}:v2:{self.stem}:{len(self.facts)+1:04}', type=kind,
                    source_pattern=source if isinstance(source,dict) else pattern(source),
                    target_pattern=target if isinstance(target,dict) else pattern(target,'dialect'),
                    functions=list(functions),conditions=list(conditions),constraints=list(constraints),
                    scope=dict(regions=self.regions if regions is None else list(regions),
                               speech_levels=list(levels),registers=[],period=[],note=scope_note),
                    evidence=refs,claim_status=status,usability=usability,notes=notes)
        self.facts.append(fact)
        return fact['id']

    def page(self, number, disposition, note, *, gaps=(), fact_ids=None):
        refs = fact_ids if fact_ids is not None else [f['id'] for f in self.facts
                if any(e['pdf_page']==number for e in f['evidence'])]
        self.reviews.append(dict(pdf_page=number,disposition=disposition,fact_ids=refs,
                                 note=note,gaps=list(gaps)))

    def save(self):
        for directory, value in [('authored',dict(source_id=self.source,facts=self.facts)),
                                 ('reviews',dict(source_id=self.source,pages=self.reviews))]:
            path = BASE/directory/(self.source+'_'+self.stem+'.json')
            path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
        print(self.source, len(self.facts), 'facts;', len(self.reviews), 'reviewed pages')


def condition(owner, field, value, op='eq', basis='explicit'):
    return dict(owner=owner,field=field,op=op,value=value,basis=basis)


def constraint(kind, description):
    return dict(kind=kind,description=description)

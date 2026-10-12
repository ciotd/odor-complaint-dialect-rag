"""Read fresh PDF text with explicit page boundaries; log access, not review."""
import argparse
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('start', type=int)
    parser.add_argument('end', type=int)
    args = parser.parse_args()
    if args.start < 1 or args.end < args.start:
        parser.error('Invalid PDF page range')
    selected = []
    for line in (BASE/'local/pages.jsonl').read_text().splitlines():
        page = json.loads(line)
        if page['source_id'] == args.source and args.start <= page['pdf_page'] <= args.end:
            selected.append(page)
            print(f"\n=== {args.source} PDF {page['pdf_page']} ===\n{page['text']}")
    if len(selected) != args.end-args.start+1:
        raise ValueError('Incomplete or unknown page range')
    with (BASE/'local/access.jsonl').open('a') as stream:
        stream.write(json.dumps({'source_id':args.source,'start':args.start,'end':args.end,
                                 'status':'printed_not_proof_of_semantic_review'})+'\n')


if __name__ == '__main__':
    main()

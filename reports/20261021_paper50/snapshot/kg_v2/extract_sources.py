"""Reproduce local page text from the seven registered PDFs without reviewing it."""
import hashlib
import json
from pathlib import Path
import subprocess

BASE = Path(__file__).resolve().parent


def extract():
    registry = json.loads((BASE/'source_registry.json').read_text())
    pages = []
    for source in registry['sources']:
        info = source['file']
        pdf = BASE.parent/info['path']
        if hashlib.sha256(pdf.read_bytes()).hexdigest() != info['sha256']:
            raise ValueError('Source PDF changed: ' + str(pdf))
        text = subprocess.check_output(['pdftotext', '-layout', str(pdf), '-']).decode('utf-8')
        chunks = text.split('\f')
        if chunks and not chunks[-1].strip():
            chunks.pop()
        if len(chunks) != info['pages']:
            raise ValueError('Unexpected page count: ' + source['source_id'])
        for number, chunk in enumerate(chunks, 1):
            pages.append({'source_id': source['source_id'], 'pdf_page': number, 'text': chunk,
                          'text_sha256': hashlib.sha256(chunk.encode()).hexdigest()})
    path = BASE/'local/pages.jsonl'
    if path.exists():
        existing = [json.loads(line) for line in path.read_text().splitlines()]
        if existing != pages:
            raise ValueError('Extraction differs from existing page text; review the difference before replacing it')
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(''.join(json.dumps(p, ensure_ascii=False)+'\n' for p in pages))
    print(f'{len(pages)} pages reproduced; no semantic review status changed.')


if __name__ == '__main__':
    extract()

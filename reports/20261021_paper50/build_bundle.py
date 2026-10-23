"""Package the frozen experiment and current report without local credentials."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
P = Path(__file__).resolve().parent
out = P/'논문용_50문장_실험_이관자료.zip'
with ZipFile(out, 'w', ZIP_DEFLATED) as z:
    for f in sorted(P.rglob('*')):
        if not f.is_file() or f.suffix in {'.zip', '.pyc'} or '__pycache__' in f.parts:
            continue
        z.write(f, Path(P.name)/f.relative_to(P))
with ZipFile(out) as z:
    assert z.testzip() is None
    assert [n for n in z.namelist() if n.endswith('.html')] == [P.name+'/report.html']
print('Bundle refreshed: one HTML and original experiment records.')

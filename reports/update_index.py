"""Refresh the one-report entry point without models or duplicate HTML."""
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
registry = json.loads((ROOT / 'reports/experiment_index.json').read_text())
report = ROOT / registry['report']
assert report.is_file(), report
out = ROOT / 'reports/latest'
out.mkdir(exist_ok=True)
manifest = dict(registry, report_sha256=hashlib.sha256(report.read_bytes()).hexdigest())
(out / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
(out / 'START_HERE.txt').write_text(
    '통합 보고서: ../20261021_paper50/report.html\n'
    '표준어 50개·세 조건의 최초/최종 번역, 실험 방법과 분석을 함께 볼 수 있습니다.\n'
    '원본 결과: ../20261021_paper50/translations.txt 및 comparison.tsv\n'
    '보고서 재생성: '+registry['regenerate']+'\n')
print('Updated one-report entry point; no model calls.')

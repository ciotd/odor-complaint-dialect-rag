"""One real Qwen call using test.py connection settings, not its KG.

Reads only literal connection/model/system settings from the old Python file.
Credentials never appear in the report. This is not a comparative evaluation.
"""
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]


def main():
    archived = ROOT / 'test.py'
    settings = {}
    for statement in ast.parse(archived.read_text()).body:
        if isinstance(statement, ast.Assign):
            for target in statement.targets:
                if isinstance(target, ast.Name) and target.id in {'LLM_BASE_URL', 'GATEWAY_TOKEN'}:
                    settings[target.id] = ast.literal_eval(statement.value)
    settings['LLM_URL'] = settings['LLM_BASE_URL'].rstrip('/') + '/chat/completions'
    settings['MODEL'] = 'Qwen3.8-27B'
    settings['SYS'] = '너는 표준 한국어를 경상북도(경북) 방언으로 바꾸는 변환기다. 의미는 그대로 두고 방언 문장 한 줄만 출력한다.'
    token = settings.get('GATEWAY_TOKEN') or os.environ.get('VLLM_API_KEY', '')
    if not token and (ROOT / '.env').exists():
        for line in (ROOT / '.env').read_text().splitlines():
            key, sep, value = line.strip().removeprefix('export ').partition('=')
            if sep and key.strip() == 'VLLM_API_KEY':
                token = value.strip()
                if len(token) >= 2 and token[0] == token[-1] and token[0] in {'"', "'"}:
                    token = token[1:-1]
                break
    sentence = '오늘은 시간이 없어서 내일 다시 갈게.'
    payload = {'model': settings['MODEL'], 'messages': [
        {'role': 'system', 'content': settings['SYS']},
        {'role': 'user', 'content': '다음 표준어 문장을 방언으로 바꿔라.\n' + sentence}],
        'max_tokens': 512, 'temperature': 0.3, 'top_p': 0.8, 'top_k': 20,
        'chat_template_kwargs': {'enable_thinking': False}}
    report = {'kind': 'connection_and_generation_smoke_not_evaluation',
              'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'settings_source': str(archived.relative_to(ROOT)),
              'settings_source_sha256': hashlib.sha256(archived.read_bytes()).hexdigest(),
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'endpoint': settings['LLM_URL'], 'request': payload,
              'input': sentence, 'kg_used': False}
    request = urllib.request.Request(settings['LLM_URL'], data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token})
    start = time.monotonic()
    try:
        models_request = urllib.request.Request(
            settings['LLM_BASE_URL'].rstrip('/') + '/models',
            headers={'Authorization': 'Bearer ' + token})
        with urllib.request.urlopen(models_request, timeout=120) as response:
            models = json.loads(response.read())
        report['available_models'] = [item['id'] for item in models['data']]
        if settings['MODEL'] not in report['available_models']:
            raise RuntimeError('Requested model not available; no fallback permitted')
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.loads(response.read())
        choice = result['choices'][0]
        report.update(status='succeeded', response_model=result.get('model'),
                      output=choice['message'].get('content'), finish_reason=choice.get('finish_reason'),
                      usage=result.get('usage'))
    except urllib.error.HTTPError as error:
        report.update(status='failed', error_type='HTTPError', http_status=error.code)
    except Exception as error:
        report.update(status='failed', error_type=type(error).__name__)
    report['elapsed_seconds'] = round(time.monotonic() - start, 3)
    report['ended_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    return report


if __name__ == '__main__':
    main()

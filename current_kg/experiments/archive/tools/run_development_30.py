"""Run the saved prompt-only development set; never execute test.py or save secrets."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import argparse
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request

BASE = Path(__file__).resolve().parents[2]
ROOT = BASE.parents[1]


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    config_path = BASE / 'inputs/development_30.config.json'
    config = json.loads(config_path.read_text())
    dataset_path = BASE / 'inputs' / config['dataset']
    rows = [json.loads(line) for line in dataset_path.read_text().splitlines()]
    assert len(rows) == 30 and len({r['id'] for r in rows}) == 30
    assert config['condition'] == 'prompt_only' and config['repetitions'] == 1
    if not args.execute:
        print(json.dumps({'validated_inputs': len(rows), 'model': config['requested_model'],
                          'condition': config['condition'], 'network_called': False}))
        return
    settings = {}
    for node in ast.parse((ROOT / 'test.py').read_text()).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {'LLM_BASE_URL', 'GATEWAY_TOKEN'}:
                    settings[target.id] = ast.literal_eval(node.value)
    token = os.environ.get('VLLM_API_KEY') or settings.get('GATEWAY_TOKEN', '')
    if not token and (ROOT / '.env').exists():
        for line in (ROOT / '.env').read_text().splitlines():
            key, sep, value = line.strip().removeprefix('export ').partition('=')
            if sep and key.strip() == 'VLLM_API_KEY':
                token = value.strip().strip('"\'')
                break
    url = settings['LLM_BASE_URL'].rstrip('/')
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder = BASE / 'archive/runs' / ('development_30_' + stamp)
    folder.mkdir(parents=True, exist_ok=False)
    manifest = {'started_at_utc': stamp, 'status': 'running', 'config': config,
                'dataset_sha256': hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
                'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'completed': 0, 'checkpoint_and_quantization': 'not_verified',
                'endpoint_sha256': hashlib.sha256(url.encode()).hexdigest()}
    write_json(folder / 'inputs.json', rows)
    write_json(folder / 'manifest.json', manifest)

    def call(route, payload=None):
        request = urllib.request.Request(url + route,
            data=None if payload is None else json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token})
        with urllib.request.urlopen(request, timeout=config['timeout_seconds']) as response:
            return json.loads(response.read())

    try:
        models = call('/models')
        manifest['available_models'] = [m['id'] for m in models['data']]
        if config['requested_model'] not in manifest['available_models']:
            raise RuntimeError('Requested model unavailable; no fallback')
        for row in rows:
            payload = {'model': config['requested_model'], **config['generation'],
                       'messages': [{'role': 'system', 'content': config['system_prompt']},
                                    {'role': 'user', 'content': row['standard']}]}
            start = time.monotonic()
            response = call('/chat/completions', payload)
            choice = response['choices'][0]
            output = {'id': row['id'], 'input': row['standard'], 'request': payload,
                      'response': response, 'output': choice['message'].get('content'),
                      'elapsed_seconds': round(time.monotonic() - start, 3)}
            with (folder / 'outputs.jsonl').open('a') as stream:
                stream.write(json.dumps(output, ensure_ascii=False) + '\n')
            manifest['completed'] += 1
            write_json(folder / 'manifest.json', manifest)
            print(row['id'] + ' saved', flush=True)
            if response.get('model') != config['requested_model']:
                raise RuntimeError('Response model differs; review required')
            if choice.get('finish_reason') != 'stop' or not output['output']:
                raise RuntimeError('Incomplete output; review required')
        manifest['status'] = 'succeeded'
    except Exception as error:
        manifest['status'] = 'failed'
        manifest['error_type'] = type(error).__name__
        if isinstance(error, urllib.error.HTTPError):
            manifest['http_status'] = error.code
        # Do not persist arbitrary error strings or headers containing credentials.
    finally:
        manifest['ended_at_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        write_json(folder / 'manifest.json', manifest)
        print(json.dumps({'status': manifest['status'], 'completed': manifest['completed'],
                          'result_directory': str(folder), 'error_type': manifest.get('error_type'),
                          'http_status': manifest.get('http_status')}, ensure_ascii=False), flush=True)
    if manifest['status'] != 'succeeded':
        raise SystemExit(1)


if __name__ == '__main__':
    main()

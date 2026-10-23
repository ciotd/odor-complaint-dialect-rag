"""Seed capability probe and paired, manually assisted KG development comparison."""
import argparse
import ast
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def connection():
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

    def call(route, payload=None):
        req = urllib.request.Request(url + route,
            data=None if payload is None else json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token})
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.loads(response.read())
    return call, hashlib.sha256(url.encode()).hexdigest()


def payload(config, sentence, seed, packet=None):
    user = sentence
    if packet is not None:
        user = ('아래 문법 자료는 검토 중인 KG에서 조회한 조건부 참고 정보입니다. '
                '원문 의미·높임에 맞는 경우에만 참고하고, 조건 미확인은 허용으로 해석하지 마세요. '
                '표준어와 공유되는 표현을 억지로 바꾸거나 방언 형태를 모두 넣지 마세요. '
                '지역·시대 범위를 확대하거나 연결된 용법의 조건을 서로 상속하지 마세요.\n'
                '<문법_KG_참고>\n' + json.dumps(packet, ensure_ascii=False, separators=(',', ':')) +
                '\n</문법_KG_참고>\n변환할 표준어 발화:\n' + sentence)
    return {'model': config['requested_model'], **config['generation'], 'seed': seed,
            'messages': [{'role': 'system', 'content': config['system_prompt']},
                         {'role': 'user', 'content': user}]}


def check_response(response, model):
    choice = response['choices'][0]
    if response.get('model') != model:
        raise RuntimeError('Response model mismatch')
    if choice.get('finish_reason') != 'stop' or not choice['message'].get('content'):
        raise RuntimeError('Incomplete output')
    return choice['message']['content']


def error_fields(error):
    result = {'error_type': type(error).__name__}
    if isinstance(error, urllib.error.HTTPError):
        result['http_status'] = error.code
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['probe', 'run'])
    parser.add_argument('--seed', type=int, default=20260923)
    parser.add_argument('--probe-file', type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.probe_file is not None:
        args.probe_file = args.probe_file.resolve()
    config = read(BASE / 'inputs/development_30.config.json')
    rows = [json.loads(x) for x in (BASE / 'inputs' / config['dataset']).read_text().splitlines()]
    if not args.execute:
        print(json.dumps({'mode': args.mode, 'inputs': len(rows), 'seed': args.seed, 'network_called': False}))
        return
    call, endpoint_hash = connection()
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder = BASE / 'archive/runs' / (('seed_probe_' if args.mode == 'probe' else 'seeded_kg_') + stamp)
    folder.mkdir(parents=True, exist_ok=False)
    manifest = {'started_at_utc': stamp, 'seed': args.seed, 'config': config,
                'endpoint_sha256': endpoint_hash, 'runner_sha256': sha(Path(__file__)),
                'dataset_sha256': sha(BASE / 'inputs' / config['dataset']), 'status': 'running', 'completed': 0}
    save(folder / 'manifest.json', manifest)
    try:
        manifest['available_models'] = [x['id'] for x in call('/models')['data']]
        if config['requested_model'] not in manifest['available_models']:
            raise RuntimeError('Requested model unavailable')
        if args.mode == 'probe':
            # An invalid type tests whether the server validates this field instead of silently ignoring it.
            invalid = payload(config, rows[0]['standard'], 'not-an-integer')
            invalid['max_tokens'] = 1
            validation = {'invalid_seed_rejected': False, 'error_mentions_seed': False}
            try:
                call('/chat/completions', invalid)
            except urllib.error.HTTPError as error:
                body = error.read().decode(errors='replace')
                validation.update(http_status=error.code,
                    invalid_seed_rejected=error.code in {400, 422},
                    error_mentions_seed='seed' in body.lower())
            requests = []
            for _ in range(2):
                req = payload(config, rows[0]['standard'], args.seed)
                response = call('/chat/completions', req)
                output = check_response(response, config['requested_model'])
                requests.append({'request': req, 'response': response, 'output': output})
            validation.update(numeric_seed_accepted=True,
                              same_seed_same_output=requests[0]['output'] == requests[1]['output'],
                              limitation='Two identical requests are a local repeatability observation, not a deterministic guarantee.')
            save(folder / 'probe.json', {'seed': args.seed, 'endpoint_sha256': endpoint_hash,
                'model': config['requested_model'], 'validation': validation, 'requests': requests})
            manifest['probe'] = validation
            manifest['completed'] = 2
        else:
            probe = read(args.probe_file)
            if probe['seed'] != args.seed or probe['endpoint_sha256'] != endpoint_hash:
                raise RuntimeError('Probe does not match requested seed/endpoint')
            v = probe['validation']
            if not (v['numeric_seed_accepted'] and v['invalid_seed_rejected'] and v['error_mentions_seed']):
                raise RuntimeError('Seed field validation not confirmed')
            manifest['seed_probe'] = str(args.probe_file.relative_to(ROOT))
            manifest['seed_probe_sha256'] = sha(args.probe_file)
            packets_path = BASE / 'archive/legacy_development/development_30.kg_packets.json'
            packets = read(packets_path)
            if packets['graph_sha256'] != sha(ROOT / 'current_kg/grammar/grammar.graph.json'):
                raise RuntimeError('Stale KG packets')
            annotations = read(BASE / 'archive/legacy_development/development_30.kg_plan.json')
            if packets['plan_sha256'] != sha(BASE / 'archive/legacy_development/development_30.kg_plan.json'):
                raise RuntimeError('Stale annotation packets')
            packet_map = {x['id']: x['prompt_packet'] for x in packets['items']}
            if set(packet_map) != {r['id'] for r in rows}:
                raise RuntimeError('Packet/input mismatch')
            manifest.update(graph_sha256=packets['graph_sha256'], packets_sha256=sha(packets_path),
                analysis_mode='Codex manual clause/function analysis and seed assertion selection; not automatic retrieval',
                conditions=['prompt_only_seeded', 'kg_manual_seeded'], checkpoint_and_quantization='not_verified',
                limitation='Development set and prior baseline outputs already seen. One seed; no causal claim about graph representation alone.')
            save(folder / 'inputs.json', rows)
            save(folder / 'kg_plan.json', annotations)
            save(folder / 'kg_packets.json', packets)
            for index, row in enumerate(rows):
                conditions = ['prompt_only_seeded', 'kg_manual_seeded']
                if index % 2:
                    conditions.reverse()
                for condition in conditions:
                    req = payload(config, row['standard'], args.seed,
                                  packet_map[row['id']] if condition == 'kg_manual_seeded' else None)
                    start = time.monotonic()
                    response = call('/chat/completions', req)
                    output = response['choices'][0]['message'].get('content')
                    result = {'id': row['id'], 'condition': condition, 'input': row['standard'],
                              'request': req, 'response': response, 'output': output,
                              'elapsed_seconds': round(time.monotonic() - start, 3)}
                    with (folder / 'outputs.jsonl').open('a') as stream:
                        stream.write(json.dumps(result, ensure_ascii=False) + '\n')
                    check_response(response, config['requested_model'])
                    manifest['completed'] += 1
                    save(folder / 'manifest.json', manifest)
                    print(row['id'] + ' ' + condition + ' saved', flush=True)
        manifest['status'] = 'succeeded'
    except Exception as error:
        manifest.update(status='failed', **error_fields(error))
    finally:
        manifest['ended_at_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
        save(folder / 'manifest.json', manifest)
        print(json.dumps({'status': manifest['status'], 'completed': manifest['completed'],
                          'directory': str(folder), 'probe': manifest.get('probe'),
                          'error_type': manifest.get('error_type'), 'http_status': manifest.get('http_status')}, ensure_ascii=False), flush=True)
    if manifest['status'] != 'succeeded':
        raise SystemExit(1)


if __name__ == '__main__':
    main()

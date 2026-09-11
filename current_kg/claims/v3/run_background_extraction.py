"""Sequential, logged Codex extraction worker requested by the user.

Runs six document tasks with the CLI's workspace-write sandbox. Generated run
logs/status/receipts are runtime outputs, not new research report documents.
No credentials copied, no git mutations, no Claude or generation experiments.
"""
import datetime
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'current_kg/claims/v3/background_run'
ORDER = ['NAMU_GRAMMAR_20260908', 'NAMU_HONORIFICS_20260908',
         'NAMU_PHONOLOGY_20260908', 'NAMU20260901', 'RYU2014', 'JO2018']


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def log(message):
    line = now() + ' ' + message
    print(line, flush=True)
    with (OUT / 'progress.log').open('a') as stream:
        stream.write(line + '\n')


INSTRUCTIONS = '''
당신은 사용자가 명시적으로 요청한 백그라운드 문헌 Claim 추출 작업자다.
목표는 경상 방언 문법 KG를 통해 자연스러운 방언 생성을 가능하게 하는 것이다.
이번에는 아래 지정한 문헌 전체의 실제 추출을 끝내라. 계획·파일럿만 만들고 끝내지 말라.
사용자에게 소규모 묶음마다 재승인을 묻지 말고 실제 파일을 계속 작성하라.

처음에 current_kg/README.md, current_kg/docs/CLAIM_FORMAT_V3_DRAFT.md,
current_kg/claims/v3/bundle.schema.json, namu_grammar_batch_001.json 및 coverage.json,
current_kg/design_probe/probe.py를 읽어 현재 규약을 확인한다.
추가로 current_kg/docs/KG_FEASIBILITY_2026-09-09.md를 필요한 구간만 참조한다.
자료 통제표는 current_kg/claims/source_registry.json이다.

원본 PDF는 읽기 전용이다. pdftotext -layout으로 실제 구간을 읽고 각주·표·다음쪽 경계를
같이 확인하라. 표가 깨지면 pdftoppm과 이미지 확인을 하라. 문헌에 없는 조건·예문·지역·
시대·표준어 대응을 상식으로 추가하지 말라. 모호한 내용은 보류 장부에 이유와 위치를
기록하되 다른 구간 추출은 계속한다. 통계 사용비율은 생성 문법 Claim에 넣지 않는다.
모든 문장을 기계적으로 Claim화하지 않는다. 조사 방법·목차·참고문헌 등은 맥락으로
분류한다. 문법·형태음운·높임·담화 정보는 생성에 쓰일 조건·대상·결합·실현형을 함께
기록하고, 예외와 유보를 삭제해서 일반 규칙만 과잉 적용 가능하게 만들지 않는다.
재인용·모호한 주장은 추적 가능하게 보존하되 운영 생성에는 보류한다.
경상 전역 공통은 자료가 명확히 뒷받침하지 않으면 붙이지 않는다. 특정 지역에서 확인됨은
그 지역 전용이 아니다. 북쪽/남쪽을 행정구역 경북/경남 전체로 자동 치환하지 않는다.
자료 발행 시점과 발화·조사 시점을 구별한다. 출처의 분석·추출자 해석·생성 정책을 구분한다.

기존 318건, 39규칙, 과거 JSON, archive, AI-Hub와 어휘 JSON은 추출 근거로 읽지 않는다.
기존 시험 11건도 복사하지 않는다. 현재 정식 15건은 보존하고 중복 추출하지 말라.
새 배치는 current_kg/claims/v3/ 아래 문헌과 범위를 식별하는 JSON으로 저장한다.
고유 ID는 Source ID + 고유 batch 번호/범위 + 로컬 번호로 충돌하지 않게 정한다.
구조 변경이 필요하면 기존 규약을 최대한 유지하고 변경 이유를 JSON metadata 또는
진행 로그로 남긴다. 검증기를 약화해서 통과시키지 않는다. 필요한 타입은 정당하게
추가하고 모든 배치 구조·참조·근거·조건 및 기존 회귀 검사를 실행한다.
수정은 apply_patch를 사용하고 사용자 미커밋 변경을 보존한다. git commit/push/reset,
원본 삭제, 외부 통신/자료 수집, Claude 호출, 모델 변경, 생성 API 실험은 하지 않는다.
다른 agent나 별도 background worker를 생성하지 말라. 이 프로세스만 순차 작업한다.
새 README/보고서 파일을 늘리지 말고 기존 안내를 필요한 최소 범위에서 갱신하라.

Claim은 문법 용법→어미/구성과 결합→실현형의 관계로 옮길 수 있게 추출한다.
전체 그래프는 저장된 bundle들로 재구성 가능한 nodes/edges JSON으로 내보내되
근거·주석 노드 개수만으로 생성용 KG가 완성됐다고 하지 않는다. 내부 표의 활용형과
참여 용법/어미를 연결하는 결정적 변환이 가능하면 구현·검증하라. 모호한 분석을 자동
추론하지 않는다. 생성 실험은 이번 작업 범위가 아니다.

구간을 저장할 때마다 progress.log에 사람이 알아볼 문헌/쪽/Claim수/보류 내용을
한 줄 추가한다. 사용자에게는 모든 구간이 처리된 뒤 완료/보류/실패가 구분돼 보여야 한다.
자료 전체를 정말 처리한 경우에만 아래 지정한 receipt JSON을 작성한다:
{
 "source_id": "지정 ID",
 "status": "extracted_draft" 또는 "extracted_with_holds",
 "bundles": ["프로젝트 루트 기준 실제 JSON 경로"],
 "pages": [{"page": 1, "status": "extracted|context_only|held",
            "claim_ids": [], "reason": "처리내용 또는 보류이유"}, ... 마지막 PDF쪽까지],
 "claim_count": 정확한 저장 건수,
 "validation": {"passed": true, "commands": ["실제 실행한 검사"]},
 "open_issues": ["미결 내용과 위치"]
}
한 페이지에 문법과 맥락이 함께 있으면 extracted로 기록하고 세부 이유를 적는다.
held는 원문을 읽었으나 추출을 못한 부분이며 완료로 위장하지 않는다.
모든 페이지를 읽지 않고 receipt의 pages를 기계적으로 채우는 것은 금지한다.
이전 배치가 있으면 읽고 포함하되 중복으로 생성하지 않는다. 작업 길이 때문에 한 번에
끝내지 못하면 현재까지 파일을 저장하고 정확히 미완료라고 종료하라. 정답 검증이나
현대 자연스러움이 검증됐다고 주장하지 않는다.
'''


def verify_receipt(path, source):
    if not path.exists():
        return False, 'completion receipt missing'
    receipt = json.loads(path.read_text())
    rows = receipt.get('pages', [])
    expected = set(range(1, source['file']['pages'] + 1))
    if receipt.get('source_id') != source['source_id'] or {r.get('page') for r in rows} != expected or len(rows) != len(expected):
        return False, 'page coverage missing/duplicated'
    if receipt.get('status') not in ('extracted_draft', 'extracted_with_holds'):
        return False, 'not an extraction completion state'
    if not receipt.get('validation', {}).get('passed'):
        return False, 'validation not reported successful'
    count = 0
    seen = set()
    for rel in receipt.get('bundles', []):
        path = (ROOT / rel).resolve()
        if not path.is_relative_to(ROOT / 'current_kg/claims/v3') or not path.is_file():
            return False, 'invalid output path'
        bundle = json.loads(path.read_text())
        for claim in bundle.get('claims', []):
            if claim['id'] in seen:
                return False, 'duplicate claim id'
            seen.add(claim['id'])
            count += 1
    if not count or count != receipt.get('claim_count'):
        return False, 'claim count mismatch'
    for row in rows:
        if row.get('status') not in ('extracted', 'context_only', 'held') or not row.get('reason'):
            return False, 'page disposition missing'
        if not set(row.get('claim_ids', [])) <= seen:
            return False, 'page has unresolved claim reference'
    return True, receipt['status']


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    lock = (OUT / 'worker.lock').open('a')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('Another extraction runner already holds this lock.')
    registry = json.loads((ROOT / 'current_kg/claims/source_registry.json').read_text())
    sources = {s['source_id']: s for s in registry['sources'] if s['eligible_for_claims']}
    run_id = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    previous_status = OUT / 'status.json'
    if previous_status.exists():
        save(OUT / (run_id + '.previous_status.json'), json.loads(previous_status.read_text()))
    state = {'run_id': run_id, 'started_at': now(), 'pid': os.getpid(), 'status': 'running', 'current_source': None,
             'completed_sources': [], 'failed_sources': [], 'notification': 'progress log + best-effort desktop notification; no chat push guarantee'}
    save(OUT / 'status.json', state)
    log('START actual extraction worker pid=' + str(os.getpid()))
    try:
        for sid in ORDER:
            source = sources[sid]
            receipt = OUT / (sid + '.receipt.json')
            ok, reason = verify_receipt(receipt, source)
            if ok:
                state['completed_sources'].append({'source_id': sid, 'status': reason})
                continue
            state['current_source'] = sid
            save(OUT / 'status.json', state)
            log('EXTRACT ' + sid + ' ' + source['file']['path'])
            # One initial attempt + two safe continuations. No unbounded retry loop.
            for attempt in range(1, 4):
                task = INSTRUCTIONS + '\n이번 문헌: ' + json.dumps(source, ensure_ascii=False)
                task += '\nreceipt 경로: ' + str(receipt.relative_to(ROOT))
                task += '\n진행 로그: current_kg/claims/v3/background_run/progress.log'
                task += '\n시도 번호: ' + str(attempt) + '. 기존 저장 배치부터 확인해 이어서 추출하라.'
                if sid == 'JO2018':
                    task += ('\n재개 지시: 2026-09-11 이전 실행에서 JO PDF1–182, 17배치·218건까지 저장했다. '
                             '실제 최신 파일과 coverage를 확인하고 미처리 PDF183–265부터 이어서 완료하라. '
                             '이미 추출한 앞부분을 다시 시작하거나 기존 배치를 덮어쓰지 말라. '
                             '본문 뒤 참고문헌·부록도 읽고 맥락/추출/보류로 정직하게 구분하라. '
                             '이 안내 이후 추가 저장된 구간이 있으면 그 다음부터 재개한다.')
                command = ['codex', 'exec', '--ephemeral', '--sandbox', 'workspace-write',
                           '--json', '-C', str(ROOT), '-']
                events = OUT / (sid + f'.{run_id}.attempt{attempt}.events.jsonl')
                errors = OUT / (sid + f'.{run_id}.attempt{attempt}.stderr.log')
                with events.open('a') as stdout, errors.open('a') as stderr:
                    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=stdout, stderr=stderr, text=True)
                    state['child_pid'] = process.pid
                    state['attempt'] = attempt
                    state['events_path'] = str(events.relative_to(ROOT))
                    save(OUT / 'status.json', state)
                    process.communicate(task)
                log(f'EXIT {sid} attempt={attempt} code={process.returncode}')
                ok, reason = verify_receipt(receipt, source)
                if process.returncode == 0 and ok:
                    state['completed_sources'].append({'source_id': sid, 'status': reason})
                    break
                log('INCOMPLETE ' + sid + ': ' + reason)
                # Auth/CLI failure: stop instead of burning attempts on all sources.
                if process.returncode != 0:
                    state['failed_sources'].append({'source_id': sid, 'reason': 'CLI error; inspect stderr/events'})
                    raise RuntimeError('CLI failure in ' + sid)
            else:
                state['failed_sources'].append({'source_id': sid, 'reason': reason})
            save(OUT / 'status.json', state)
        state['status'] = 'finished_with_incomplete_sources' if state['failed_sources'] else 'finished_draft_extraction'
    except Exception as error:
        state['status'] = 'stopped_on_error'
        state['error'] = str(error)
        log('ERROR ' + str(error))
    finally:
        state['ended_at'] = now()
        state['current_source'] = None
        state.pop('child_pid', None)
        save(OUT / 'status.json', state)
        log('FINISH ' + state['status'] + '; inspect status.json and receipts for holds')
        if shutil.which('notify-send'):
            subprocess.run(['notify-send', '경상 방언 Claim 추출', state['status'] + ' — background_run/status.json 확인'],
                           timeout=10, check=False)


if __name__ == '__main__':
    main()

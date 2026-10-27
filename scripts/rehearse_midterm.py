"""Record a synthetic Week 7 lifecycle in the isolated nutrichat-week07 stack.

Build/start db, ai and api with compose.week06.yaml first. This script stops/starts
only that project's worker, creates one meal and writes evidence to --output.
It uses the offline demo provider, not Qwen; run from a host with Python and Docker.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = [
    'docker', 'compose', '-p', 'nutrichat-week07', '--env-file', '.env.example',
    '-f', 'compose.yaml', '-f', 'compose.week06.yaml',
]
HTTP = '''import json,sys,urllib.request,urllib.error
method,path,payload = sys.argv[1:]
request = urllib.request.Request('http://api:8000'+path, method=method,
    data=payload.encode() if payload else None,
    headers={'Content-Type':'application/json'})
try:
    response = urllib.request.urlopen(request, timeout=10)
except urllib.error.HTTPError as error:
    response = error
print(json.dumps({'status':response.status,'body':json.load(response)}))
'''


def run(args):
    return subprocess.check_output(args, cwd=ROOT, text=True, timeout=90)


def request(method, path, payload=None, status=200):
    result = json.loads(run(COMPOSE + [
        'exec', '-T', 'api', 'python', '-c', HTTP, method, path,
        json.dumps(payload) if payload is not None else '',
    ]))
    assert result['status'] == status, result
    return result


def database(job_id):
    query = (
        'SELECT row_to_json(t) FROM (SELECT j.id AS job_id,j.status AS job_status,'
        'j.attempts,j.claimed_at,j.completed_at,a.id AS analysis_id,'
        'a.status AS analysis_status,a.revision,a.calories,a.protein_g,a.fat_g,'
        'a.carbs_g,a.confirmed_at FROM jobs j JOIN analyses a ON a.id=j.analysis_id '
        f'WHERE j.id={int(job_id)}) t;'
    )
    return json.loads(run(COMPOSE + [
        'exec', '-T', 'db', 'psql', '-U', 'postgres', '-d', 'maie6000c', '-Atc', query,
    ]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(COMPOSE + ['stop', 'worker'])
    evidence = {
        'observed_at': datetime.now(timezone.utc).isoformat(),
        'source_base_commit': run(['git', 'rev-parse', 'HEAD']).strip(),
        'scope': 'Week 7 checkout; real PostgreSQL and internal HTTP; offline demo provider.',
        'project': 'nutrichat-week07',
        'health': request('GET', '/health/ready'),
    }
    created = request('POST', '/analyses', {'food_text': '100g egg'}, status=201)
    evidence['create'] = created
    meal = created['body']['analysis']
    job_id = created['body']['job']['id']
    path = '/analyses/' + meal['id']
    evidence['before_worker'] = database(job_id)
    assert evidence['before_worker']['analysis_status'] == 'queued'
    assert evidence['before_worker']['job_status'] == 'pending'
    run(COMPOSE + ['up', '-d', '--no-build', 'worker'])
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        result = request('GET', path)
        if result['body']['status'] != 'queued':
            break
        time.sleep(0.5)
    assert result['body']['status'] == 'completed', result
    assert result['body']['calories'] == 155
    evidence['result'] = result
    evidence['after_worker'] = database(job_id)
    assert evidence['after_worker']['job_status'] == 'completed'
    assert evidence['after_worker']['attempts'] == 1
    assert evidence['after_worker']['claimed_at']
    confirmed = request('POST', path + '/confirm', {'revision': result['body']['revision']})
    assert confirmed['body']['status'] == 'confirmed'
    evidence['confirmed'] = confirmed
    evidence['reloaded'] = request('GET', path)
    assert evidence['reloaded'] == confirmed
    evidence['after_confirmation'] = database(job_id)
    evidence['locked_edit'] = request('PATCH', path, {
        'food_text': '200g egg', 'revision': confirmed['body']['revision'],
    }, status=409)
    events = []
    for line in run(COMPOSE + ['logs', '--no-color', '--no-log-prefix', 'worker']).splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get('job_id') == job_id:
            events.append(event)
    assert {'job_claimed', 'job_completed'} <= {e.get('message') for e in events}
    evidence['worker_events'] = events
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2) + '\n')
    print('PASS: queued DB state, worker claim/completion, saved totals, confirmation, '
          'reload, locked correction, health and matching logs')
    print(f'Evidence: {args.output}')


if __name__ == '__main__':
    main()

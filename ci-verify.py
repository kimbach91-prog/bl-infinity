"""Bounded PUBLIC Linux verification with exact archive/source/output custody."""
import datetime
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'verification-output'
OUT.mkdir(exist_ok=True)
PINS = json.loads((ROOT / 'pins.json').read_bytes())
RECEIPT = {'schema': 'deus-one-public-linux-verification/1',
    'task_id': 'TASK-DEUS-ONE-KERNEL-AUDIT-20261018-001',
    'started_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'executor': 'GITHUB_ACTIONS_STANDARD_HOSTED_UBUNTU_PUBLIC_TEST_RESULT',
    'run_id': os.getenv('GITHUB_RUN_ID'), 'run_attempt': os.getenv('GITHUB_RUN_ATTEMPT'),
    'source_commit': os.getenv('GITHUB_SHA'), 'workflow_ref': os.getenv('GITHUB_WORKFLOW_REF'),
    'platform': platform.platform(), 'python': sys.version,
    'policy_revision': PINS['policy_revision'], 'catalog_sha256': PINS['catalog_sha256'],
    'pins': PINS, 'commands': [], 'native_admission': False,
    'private_core_included': False, 'production_deployed': False,
    'persistent_worker_lease_or_physical_capacity_credit': 0, 'success': False}

def run(label, command, cwd, expected_exit=0, expected_tests=None):
    env = dict(os.environ, PYTHONPATH=str(cwd), PYTHONDONTWRITEBYTECODE='1')
    result = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, timeout=120)
    text = result.stdout + result.stderr
    (OUT / (label + '.log')).write_text(text, encoding='utf-8')
    count = re.findall(r'Ran (\d+) tests? in ', text)
    row = {'label': label, 'command': command, 'exit_code': result.returncode,
           'expected_exit': expected_exit, 'tests_run': int(count[-1]) if count else None,
           'log_sha256': hashlib.sha256(text.encode()).hexdigest()}
    RECEIPT['commands'].append(row)
    print(json.dumps(row), flush=True)
    if result.returncode != expected_exit:
        raise AssertionError((label, 'unexpected exit', result.returncode))
    if expected_tests is not None and row['tests_run'] != expected_tests:
        raise AssertionError((label, 'unexpected test count', row['tests_run']))
    return text

try:
    for filename, expected in PINS['fixture_files'].items():
        assert hashlib.sha256((ROOT / filename).read_bytes()).hexdigest() == expected, filename
    for label in ['baseline', 'candidate']:
        pin = PINS[label]
        archive = ROOT / pin['filename']
        assert hashlib.sha256(archive.read_bytes()).hexdigest() == pin['sha256']
        run(label + '-custody', [sys.executable, str(ROOT / 'verify-deus-one-archive.py'),
            str(archive), '--expect-sha256', pin['sha256'], '--expect-source-id', pin['source_id']], ROOT)
        target = ROOT / label
        target.mkdir(exist_ok=False)
        with zipfile.ZipFile(archive) as z:
            for member in z.infolist():
                destination = (target / member.filename).resolve()
                assert destination.is_relative_to(target.resolve())
            z.extractall(target)
    baseline = ROOT / 'baseline'
    candidate = ROOT / 'candidate'
    baseline_regression = run('baseline-confirmed-regressions',
        [sys.executable, '-W', 'error', str(ROOT / 'external-test-compose-r4.py')], baseline,
        expected_exit=1, expected_tests=5)
    assert 'FAILED (errors=3)' in baseline_regression
    run('candidate-release', [sys.executable, '-W', 'error', 'verify_release.py'], candidate)
    suite = run('candidate-full-suite', [sys.executable, '-W', 'error', '-m', 'unittest',
        'discover', '-s', 'tests', '-v'], candidate, expected_tests=PINS['full_suite_expected_tests'])
    assert re.search(r'\nOK\s*$', suite)
    if PINS.get('alias_tests'):
        alias_file = ROOT / 'external-test-alias-r4.py'
        assert hashlib.sha256(alias_file.read_bytes()).hexdigest() == PINS['alias_tests']['sha256']
        before = run('baseline-alias-regressions',
            [sys.executable, '-W', 'error', str(alias_file)], baseline,
            expected_exit=1, expected_tests=PINS['alias_tests']['test_count'])
        assert 'FAILED (' in before
    RECEIPT['success'] = True
except Exception as exc:
    RECEIPT['error'] = type(exc).__name__ + ': ' + str(exc)
finally:
    RECEIPT['finished_at_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (OUT / 'receipt.json').write_text(json.dumps(RECEIPT, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'success': RECEIPT['success'], 'error': RECEIPT.get('error'),
                      'commands': len(RECEIPT['commands'])}), flush=True)
sys.exit(0 if RECEIPT['success'] else 1)

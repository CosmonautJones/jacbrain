"""Run frozen checks on reviewed model solutions. Linux/WSL only; not a sandbox."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time


def generation_candidates(output: Path, task_ids: set[str]) -> dict:
    """Join current generation receipts to content, never discover stale files.

    Hashes address UTF-8 text after newline normalization, matching generation.
    Failed/mismatched records remain failures and are never executed.
    """
    records = json.loads((output / 'model-results.json').read_text(encoding='utf-8'))
    if not isinstance(records, list) or not records:
        raise ValueError('No current generation records to evaluate')
    candidates = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError('Malformed generation record')
        task, arm = record.get('task'), record.get('arm')
        if task not in task_ids or arm not in {'full_guides', 'mcp_search', 'flat', 'graph'}:
            raise ValueError('Unknown task or arm in generation records')
        key = (task, arm)
        if key in candidates:
            raise ValueError('Duplicate task/arm generation record')
        candidate = {'record': record, 'source': None, 'error': None}
        candidates[key] = candidate
        if record.get('error') or record.get('returncode') != 0 or record.get('tool_use_detected') is not False:
            candidate['error'] = 'generation_failed_or_tool_use_unverified'
            continue
        path = output / task / arm
        try:
            source = (path / 'solution.jac').read_text(encoding='utf-8')
            if not source.strip() or hashlib.sha256(source.encode()).hexdigest() != record.get('source_sha256'):
                candidate['error'] = 'source_hash_mismatch'
                continue
            for field, filename in [('input_prompt_sha256', 'prompt.txt'), ('context_sha256', 'context.txt')]:
                if field in record:
                    content = (path / filename).read_text(encoding='utf-8')
                    if hashlib.sha256(content.encode()).hexdigest() != record[field]:
                        candidate['error'] = field + '_mismatch'
                        break
            if candidate['error'] is None:
                candidate['source'] = source
        except (OSError, UnicodeError):
            candidate['error'] = 'missing_or_unreadable_generation_artifact'
    return candidates


def run(argv, cwd, timeout):
    start = time.monotonic()
    proc = subprocess.Popen(argv, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, encoding='utf-8', start_new_session=True)
    timed_out = False
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(proc.pid, signal.SIGKILL)
        stdout, stderr = proc.communicate(timeout=5)
    return {'command': [Path(argv[0]).name, *argv[1:]], 'returncode': proc.returncode,
            'timed_out': timed_out, 'seconds': round(time.monotonic() - start, 3),
            'stdout': stdout.replace(str(cwd), '<trial>'), 'stderr': stderr.replace(str(cwd), '<trial>')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('.jacbrain/evaluation/current'))
    parser.add_argument('--jac', default='jac')
    parser.add_argument('--reviewed', action='store_true', help='Confirm candidate source has been inspected before execution')
    args = parser.parse_args()
    if os.name == 'nt' or not args.reviewed:
        raise SystemExit('Run in Linux/WSL after inspecting source, with --reviewed; execution is not sandboxed.')
    manifest = json.loads((Path(__file__).parent / 'tasks.json').read_text())
    version = subprocess.run([args.jac, '--version'], check=True, capture_output=True, text=True).stdout
    if manifest['jac_version'] not in version:
        raise SystemExit('Compiler version mismatch')
    candidates = generation_candidates(args.output, {task['id'] for task in manifest['tasks']})
    results = []
    for task in manifest['tasks']:
        if hashlib.sha256(task['prompt'].encode()).hexdigest() != task['prompt_sha256']:
            raise SystemExit('Frozen prompt changed')
        fixture_hash = hashlib.sha256(json.dumps(task['files'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        if fixture_hash != task['fixtures_sha256']:
            raise SystemExit('Frozen fixtures changed')
        for (task_id, arm), candidate in candidates.items():
            if task_id != task['id']:
                continue
            if candidate['error']:
                record = {'task': task_id, 'arm': arm, 'compiler': version.strip(),
                          'compile_pass': False, 'behavior_pass': False, 'commands': [],
                          'error': candidate['error']}
                results.append(record)
                (args.output / 'behavior-results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
                print(json.dumps(record), flush=True)
                continue
            source = candidate['source']
            with tempfile.TemporaryDirectory(prefix='jacbrain-trial-') as tmp:
                cwd = Path(tmp)
                for fixture in manifest['shared_files'] + task['files']:
                    path = (cwd / fixture['path']).resolve()
                    if not path.is_relative_to(cwd):
                        raise ValueError('Fixture escapes trial directory')
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(fixture['template'].replace('{{solution}}', source), encoding='utf-8')
                commands = [run([args.jac, 'check'], cwd, manifest['per_command_timeout_seconds'])]
                compile_pass = commands[0]['returncode'] == 0 and not commands[0]['timed_out']
                behavior_pass = False
                if compile_pass:
                    command = run([args.jac, 'run', '--backend', 'python', '--no-cache', task['run_file']],
                                  cwd, manifest['per_command_timeout_seconds'])
                    commands.append(command)
                    lines = command['stdout'].splitlines()
                    behavior_pass = command['returncode'] == 0 and not command['timed_out'] and task['success_marker'] in lines
                    behavior_pass = behavior_pass and not any(x in lines for x in task.get('forbidden_stdout', []))
                    for extra in task.get('additional_runs', []):
                        command = run([args.jac, 'run', '--backend', 'python', '--no-cache', extra['file']],
                                      cwd, manifest['per_command_timeout_seconds'])
                        commands.append(command)
                        behavior_pass = behavior_pass and command['returncode'] == 0 and not command['timed_out']
                        behavior_pass = behavior_pass and [s for s in command['stdout'].splitlines() if s.strip()] == extra['required_stdout_lines']
                record = {'task': task['id'], 'arm': arm, 'compiler': version.strip(),
                          'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
                          'compile_pass': compile_pass, 'behavior_pass': bool(behavior_pass), 'commands': commands,
                          'manual_constraints': 'requires separate source review'}
                results.append(record)
                (args.output / 'behavior-results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
                print(json.dumps({k: record[k] for k in ('task','arm','compile_pass','behavior_pass')}), flush=True)


if __name__ == '__main__':
    main()

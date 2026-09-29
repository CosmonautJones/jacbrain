"""Failed/reused model attempts must never inherit old successful source."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'benchmarks' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


evaluate = load('evaluate')
checker = load('check_solutions')


class BenchmarkIntegrityTests(unittest.TestCase):
    def test_new_run_invalidates_summaries_before_collection_or_jobs(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            for flags in [[], ['--reuse-context', '--generate']]:
                with self.subTest(flags=flags):
                    for filename in ['model-results.json', 'behavior-results.json']:
                        (output / filename).write_text('[{"old":true}]', encoding='utf-8')
                    argv = ['evaluate.py', '--output', str(output), '--db', str(output / 'db'), *flags]
                    with patch.object(evaluate.sys, 'argv', argv), \
                         patch.object(evaluate, 'collect', side_effect=RuntimeError('interrupted')), \
                         patch.object(evaluate.shutil, 'which', return_value='fake'), \
                         patch.object(evaluate, 'ThreadPoolExecutor', side_effect=RuntimeError('interrupted')):
                        with self.assertRaisesRegex(RuntimeError, 'interrupted'):
                            evaluate.main()
                    for filename in ['model-results.json', 'behavior-results.json']:
                        self.assertEqual(json.loads((output / filename).read_text()), [])

    def test_failed_generation_removes_previous_solution(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            arm = output / 'task' / 'graph'
            arm.mkdir(parents=True)
            (arm / 'context.txt').write_text('reference', encoding='utf-8')
            for outcome in [subprocess.TimeoutExpired('fake', 240),
                            subprocess.CompletedProcess([], 0, '', '')]:
                with self.subTest(outcome=type(outcome).__name__):
                    (arm / 'solution.jac').write_text('old solution', encoding='utf-8')
                    kwargs = {'side_effect': outcome} if isinstance(outcome, Exception) else {'return_value': outcome}
                    with patch.object(evaluate.subprocess, 'run', **kwargs):
                        record = evaluate.generate({'id': 'task', 'prompt': 'task'}, 'graph', output, 'fake')
                    self.assertIn('error', record)
                    self.assertFalse((arm / 'solution.jac').exists())

    def test_only_current_successful_hash_matched_generations_are_eligible(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            for arm in ['graph', 'full_guides', 'flat']:
                path = output / 'task' / arm
                path.mkdir(parents=True)
                (path / 'solution.jac').write_text('node Safe {}\n', encoding='utf-8')
            expected = hashlib.sha256(b'node Safe {}\n').hexdigest()
            records = [
                {'task': 'task', 'arm': 'graph', 'returncode': 0,
                 'tool_use_detected': False, 'source_sha256': expected},
                {'task': 'task', 'arm': 'full_guides', 'error': 'model_timeout'},
            ]
            (output / 'model-results.json').write_text(json.dumps(records), encoding='utf-8')
            candidates = checker.generation_candidates(output, {'task'})
            self.assertEqual(set(candidates), {('task', 'graph'), ('task', 'full_guides')})
            self.assertEqual(candidates[('task', 'graph')]['source'], 'node Safe {}\n')
            self.assertIsNone(candidates[('task', 'full_guides')]['source'])
            self.assertIsNotNone(candidates[('task', 'full_guides')]['error'])
            for change in [{'source_sha256': 'wrong'}, {'tool_use_detected': True},
                           {'returncode': 1}]:
                with self.subTest(change=change):
                    (output / 'model-results.json').write_text(json.dumps([{**records[0], **change}]), encoding='utf-8')
                    candidate = checker.generation_candidates(output, {'task'})[('task', 'graph')]
                    self.assertIsNone(candidate['source'])
                    self.assertIsNotNone(candidate['error'])


if __name__ == '__main__':
    unittest.main()

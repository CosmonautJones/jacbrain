"""Real-process regression for descendants retaining an MCP stdout pipe."""
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


class TimeoutTests(unittest.TestCase):
    def test_nonreading_server_cannot_block_large_request_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            release = root / 'release'
            server = root / 'nonreading.py'
            server.write_text(
                'import json, sys, time\n'
                'from pathlib import Path\n'
                'request = json.loads(input())\n'
                'print(json.dumps({"jsonrpc":"2.0", "id":request["id"], "result":{}}), flush=True)\n'
                # Complete initialization, then retain stdin without reading it.
                'deadline = time.monotonic() + 12\n'
                'while not Path(sys.argv[1]).exists() and time.monotonic() < deadline:\n'
                '    time.sleep(0.02)\n', encoding='utf-8')
            harness = (
                'import json, sys, time\n'
                'from jacbrain.validation import JacMCP\n'
                'started = time.monotonic()\n'
                'try:\n'
                '    with JacMCP(json.loads(sys.argv[1]), timeout=0.5) as client:\n'
                '        client.request("tools/call", {"code": "x" * 100000})\n'
                'except RuntimeError as exc:\n'
                '    print(json.dumps({"error": str(exc), "elapsed": time.monotonic()-started}))\n'
            )
            command = [sys.executable, '-u', str(server), str(release)]
            proc = subprocess.Popen(
                [sys.executable, '-u', '-c', harness, json.dumps(command)],
                cwd=Path(__file__).resolve().parents[1],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                encoding='utf-8')
            try:
                try:
                    stdout, stderr = proc.communicate(timeout=6)
                except subprocess.TimeoutExpired:
                    self.fail('MCP send or cleanup blocked on the nonreading server')
                self.assertEqual(proc.returncode, 0, stderr)
                result = json.loads(stdout)
                self.assertIn('write timed out', result['error'])
                self.assertLess(result['elapsed'], 5)
            finally:
                release.touch()
                if proc.poll() is None:
                    try:
                        proc.communicate(timeout=3)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.communicate(timeout=3)
                time.sleep(0.1)

    def test_exited_launcher_with_live_descendant_does_not_block_cleanup(self):
        # Isolate the client in a process so a stream-lock regression cannot hang
        # the test runner. The descendant has both explicit and timed cleanup.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ready, release = root / 'ready', root / 'release'
            child = root / 'child.py'
            child.write_text(
                'import sys, time\n'
                'from pathlib import Path\n'
                'Path(sys.argv[1]).write_text("ready")\n'
                'deadline = time.monotonic() + 12\n'
                'while not Path(sys.argv[2]).exists() and time.monotonic() < deadline:\n'
                '    time.sleep(0.02)\n', encoding='utf-8')
            launcher = root / 'launcher.py'
            launcher.write_text(
                'import subprocess, sys, time\n'
                'from pathlib import Path\n'
                # Inherited stdout is the important part: the launcher exits,
                # but its child keeps the client's stdout reader waiting for EOF.
                'subprocess.Popen([sys.executable, sys.argv[1], sys.argv[2], sys.argv[3]])\n'
                'deadline = time.monotonic() + 3\n'
                'while not Path(sys.argv[2]).exists() and time.monotonic() < deadline:\n'
                '    time.sleep(0.01)\n', encoding='utf-8')
            harness = (
                'import json, sys, time\n'
                'from jacbrain.validation import JacMCP\n'
                'started = time.monotonic()\n'
                'try:\n'
                '    with JacMCP(json.loads(sys.argv[1]), timeout=0.5):\n'
                '        raise AssertionError("unresponsive server unexpectedly initialized")\n'
                'except RuntimeError as exc:\n'
                '    print(json.dumps({"error": str(exc), "elapsed": time.monotonic()-started}))\n'
            )
            command = [sys.executable, '-u', str(launcher), str(child), str(ready), str(release)]
            proc = subprocess.Popen(
                [sys.executable, '-u', '-c', harness, json.dumps(command)],
                cwd=Path(__file__).resolve().parents[1],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                encoding='utf-8')
            try:
                try:
                    stdout, stderr = proc.communicate(timeout=6)
                except subprocess.TimeoutExpired:
                    self.fail('MCP timeout cleanup blocked on a descendant-owned stdout pipe')
                self.assertTrue(ready.exists(), 'fixture descendant never started')
                self.assertEqual(proc.returncode, 0, stderr)
                result = json.loads(stdout)
                self.assertIn('timed out', result['error'])
                self.assertLess(result['elapsed'], 5,
                                'client cleanup waited for descendant lifetime')
            finally:
                release.touch()
                if proc.poll() is None:
                    try:
                        proc.communicate(timeout=3)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.communicate(timeout=3)
                # Give the Windows descendant time to observe the sentinel before
                # TemporaryDirectory removes it. POSIX cleanup may have killed it.
                time.sleep(0.1)


if __name__ == '__main__':
    unittest.main()

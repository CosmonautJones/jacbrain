"""CLI and MCP stay UTF-8 even when the host defaults to Windows cp1252."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from jacbrain.store import Store


class StdioEncodingTests(unittest.TestCase):
    def test_unicode_context_roundtrips_cli_and_mcp_under_cp1252(self):
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / 'brain.sqlite3'
            store = Store(database)
            try:
                store.add(kind='Concept', content='épingle → 字', source_uri='fixture:unicode',
                          project='demo', jac_version='0.37.23')
            finally:
                store.close()
            environment = {**os.environ, 'PYTHONIOENCODING': 'cp1252', 'PYTHONUTF8': '0'}
            command = [sys.executable, '-m', 'jacbrain', '--db', str(database)]
            cwd = Path(__file__).resolve().parents[1]
            cli = subprocess.run(command + ['context', 'épingle', '--project', 'demo'],
                                 cwd=cwd, env=environment, capture_output=True, timeout=10)
            self.assertEqual(cli.returncode, 0, cli.stderr)
            self.assertEqual(json.loads(cli.stdout.decode('utf-8'))['items'][0]['content'], 'épingle → 字')
            request = {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {
                'name': 'context', 'arguments': {'task': 'épingle', 'project': 'demo', 'jac_version': '0.37.23'}}}
            mcp = subprocess.run(command + ['mcp'],
                                 input=(json.dumps(request, ensure_ascii=False) + '\n').encode('utf-8'),
                                 cwd=cwd, env=environment, capture_output=True, timeout=10)
            self.assertEqual(mcp.returncode, 0, mcp.stderr)
            result = json.loads(mcp.stdout.decode('utf-8'))['result']
            self.assertEqual(json.loads(result['content'][0]['text'])['items'][0]['content'], 'épingle → 字')


if __name__ == '__main__':
    unittest.main()

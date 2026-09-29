import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jacbrain.store import Store
from jacbrain.server import serve
from jacbrain.validation import validate_record, decode_tool_result
from jacbrain.validation import JacMCP


class InterfaceTests(unittest.TestCase):
    def test_decode_requires_real_structured_result(self):
        result = {'content': [{'type': 'text', 'text': '{"valid": true, "errors": []}'}]}
        self.assertTrue(decode_tool_result(result)['valid'])
        with self.assertRaises(RuntimeError):
            decode_tool_result({'isError': True, **result})
        with self.assertRaises(RuntimeError):
            decode_tool_result({'content': []})
        with self.assertRaises(RuntimeError):
            decode_tool_result({'content': [None]})

    def test_malformed_compiler_envelope_is_controlled_error(self):
        client = JacMCP(['unused'])
        client.send = lambda value: None
        client.messages.put('{"jsonrpc":"2.0","id":1}')
        with self.assertRaises(RuntimeError):
            client.request('tools/list', {})

    def test_unavailable_validation_never_promotes(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / 'brain.db')
            rec = store.add(kind='Pattern', content='node Example {}', source_uri='test:example',
                            project='test', jac_version='0.37.23')
            with patch('jacbrain.validation.compiler_version', side_effect=RuntimeError('unavailable')):
                with self.assertRaises(RuntimeError):
                    validate_record(store, rec, ['missing-jac'])
            self.assertEqual(store.get(rec)['status'], 'candidate')
            store.close()

    def test_mcp_initialize_tools_and_invalid_requests(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / 'brain.db')
            requests = [
                {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}},
                {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
                {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'},
                {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {
                    'name': 'context', 'arguments': {'task': 'walker', 'project': 'demo', 'jac_version': '0.37.23'}}},
                {'jsonrpc': '2.0', 'id': 4, 'method': 'tools/call', 'params': {'name': 'unknown'}},
            ]
            output = io.StringIO()
            serve(store, io.StringIO('\n'.join(map(json.dumps, requests))), output, ['jac'])
            messages = list(map(json.loads, output.getvalue().splitlines()))
            self.assertEqual(len(messages), 4)
            self.assertEqual(messages[0]['result']['serverInfo']['name'], 'jacbrain')
            self.assertIn('context', [t['name'] for t in messages[1]['result']['tools']])
            self.assertEqual(json.loads(messages[2]['result']['content'][0]['text'])['items'], [])
            self.assertTrue(messages[3]['result']['isError'])
            store.close()

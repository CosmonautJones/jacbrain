"""Opt-in integration tests against a real pinned Jac MCP subprocess."""
import json
import os
from pathlib import Path
import tempfile
import unittest

from jacbrain.store import Store
from jacbrain.validation import validate_record


@unittest.skipUnless(os.environ.get('JACBRAIN_LIVE_JAC') == '1', 'set JACBRAIN_LIVE_JAC=1 for real compiler checks')
class LiveJacTests(unittest.TestCase):
    def test_real_compiler_accepts_and_rejects(self):
        command = json.loads(os.environ.get('JACBRAIN_JAC_COMMAND', '["jac"]'))
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / 'brain.db')
            try:
                for source, expected in [('node Offer { has title: str = "Lunch"; }', 'compiler_validated'),
                                         ('node Broken { has title: ; }', 'candidate')]:
                    identity = store.add(kind='Pattern', content=source, source_uri='fixture:live',
                                         project='integration', jac_version='0.37.23')
                    result = validate_record(store, identity, command)
                    self.assertEqual(result['status'], expected)
                    self.assertEqual(store.get(identity)['status'], expected)
            finally:
                store.close()

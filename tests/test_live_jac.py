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
    def test_installed_reference_import_and_retrieval(self):
        from jacbrain.corpus import sync_guides
        from jacbrain.retrieve import context
        command = json.loads(os.environ.get('JACBRAIN_JAC_COMMAND', '["jac"]'))
        store = Store(':memory:')
        try:
            imported = sync_guides(store, command, uris=['jac://guide/jac-walker-patterns'])
            self.assertEqual(imported['jac_version'], '0.37.23')
            self.assertGreater(imported['chunks'], 1)
            packet = context(store, 'typed report channel walker', 'fresh-project', '0.37.23')
            self.assertTrue(packet['items'])
            self.assertTrue(all(item['source_uri'].startswith('jac://guide/') for item in packet['items']))
            self.assertEqual(context(store, 'walker', 'fresh-project', '0.1.0')['items'], [])
        finally:
            store.close()

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

import json
import tempfile
import unittest
from pathlib import Path

from jacbrain.store import Store, digest
from jacbrain.ingest import ingest_file
from jacbrain.retrieve import context


class GraphTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / 'brain.db')

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def add(self, text='walker finds offers', **kwargs):
        return self.store.add(kind='Concept', content=text, source_uri='test:' + digest(text),
                              project='demo', jac_version='0.37.23', **kwargs)

    def test_idempotent_and_versioned(self):
        first = self.add()
        self.assertEqual(first, self.add())
        other = self.store.add(kind='Concept', content='walker finds offers',
                               source_uri='test:walker finds offers', project='demo', jac_version='other')
        self.assertNotEqual(first, other)
        self.assertEqual(len(self.store.records('demo', '0.37.23')), 1)

    def test_links_enforce_existence_and_kind(self):
        first = self.add()
        with self.assertRaises(ValueError):
            self.store.link(first, 'missing', 'depends_on')
        with self.assertRaises(ValueError):
            self.store.link(first, first, 'invented')

    def test_context_filters_and_serialized_budget(self):
        self.add()
        self.store.add(kind='Concept', content='walker secret', source_uri='test:other',
                       project='private', jac_version='0.37.23')
        packet = context(self.store, 'walker', 'demo', '0.37.23', 2000)
        self.assertEqual(len(packet['items']), 1)
        self.assertNotIn('secret', json.dumps(packet))
        self.assertLessEqual(len(json.dumps(packet, ensure_ascii=False).encode()), 2000)
        self.assertEqual(context(self.store, 'walker', 'demo', 'old', 2000)['items'], [])
        with self.assertRaises(ValueError):
            context(self.store, 'walker', 'demo', '0.37.23', 10)

    def test_graph_expands_only_same_scope(self):
        first = self.add('walker')
        second = self.add('node traversal')
        self.store.link(first, second, 'depends_on')
        result = context(self.store, 'walker', 'demo', '0.37.23', 4000)
        self.assertEqual({x['id'] for x in result['items']}, {first, second})

    def test_long_document_returns_attributed_excerpt(self):
        text = ('ordinary reference prose ' * 300) + 'needlewalker definition' + (' trailing' * 300)
        identity = self.add(text)
        packet = context(self.store, 'needlewalker', 'demo', '0.37.23', 3000)
        self.assertEqual(len(packet['items']), 1)
        item = packet['items'][0]
        self.assertIn('needlewalker', item['content'])
        self.assertTrue(item['is_excerpt'])
        self.assertEqual(item['content_hash'], self.store.get(identity)['content_hash'])
        self.assertEqual(item['content'], text[item['excerpt_start']:item['excerpt_end']])

    def test_ingestion_explicit_file_and_symbols(self):
        path = Path(self.tmp.name) / 'sample.jac'
        path.write_text('node Offer { has title: str; }\nwalker FindOffers {}', encoding='utf-8')
        ids = ingest_file(self.store, path, 'demo', '0.37.23')
        self.assertEqual(len(ids), 3)
        self.assertEqual(ids, ingest_file(self.store, path, 'demo', '0.37.23'))
        with self.assertRaises(ValueError):
            ingest_file(self.store, path.parent, 'demo', '0.37.23')
        secret = path.parent / '.env'
        secret.write_text('secret')
        with self.assertRaises(ValueError):
            ingest_file(self.store, secret, 'demo', '0.37.23')

    def test_receipt_binds_content_and_compiler(self):
        first = self.add()
        with self.assertRaises(ValueError):
            self.store.record_validation(first, 'wrong', '0.37.23', {'valid': True})
        digest = self.store.get(first)['content_hash']
        with self.assertRaises(ValueError):
            self.store.record_validation(first, digest, 'other', {'valid': True})
        self.store.record_validation(first, digest, '0.37.23', {'valid': False, 'errors': ['bad']})
        self.assertEqual(self.store.get(first)['status'], 'candidate')
        self.store.record_validation(first, digest, '0.37.23', {'valid': True, 'errors': []})
        self.assertEqual(self.store.get(first)['status'], 'compiler_validated')
        changed = self.add('different walker')
        self.assertEqual(self.store.get(changed)['status'], 'candidate')

    def test_reingest_excludes_retired_source_and_symbols(self):
        path = Path(self.tmp.name) / 'edited.jac'
        path.write_text('node Retired {}', encoding='utf-8')
        old = ingest_file(self.store, path, 'demo', '0.37.23')
        path.write_text('node Current {}', encoding='utf-8')
        ingest_file(self.store, path, 'demo', '0.37.23')
        packet = context(self.store, 'Retired', 'demo', '0.37.23', 4000)
        self.assertEqual(packet['items'], [])
        self.assertEqual(self.store.get(old[0])['status'], 'superseded')


if __name__ == '__main__':
    unittest.main()

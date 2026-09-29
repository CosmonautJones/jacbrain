import unittest
from unittest.mock import patch

from jacbrain.corpus import PROJECT, _parts, _sections, sync_guides
from jacbrain.store import Store, digest

VERSION = '0.37.23'
A = 'jac://guide/jac-alpha'
B = 'jac://guide/jac-beta'


class FakeMCP:
    documents = {}
    catalog = None
    reads = []

    def __init__(self, command):
        self.command = command

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def request(self, method, params):
        if method == 'resources/list':
            return {'resources': self.catalog if self.catalog is not None else
                    [{'uri': uri, 'name': uri.rsplit('/', 1)[-1]} for uri in self.documents]}
        self.reads.append(params['uri'])
        value = self.documents[params['uri']]
        if isinstance(value, Exception):
            raise value
        if isinstance(value, dict):
            return value
        return {'contents': [{'uri': params['uri'], 'text': value}]}


class CorpusTests(unittest.TestCase):
    def setUp(self):
        self.store = Store(':memory:')
        FakeMCP.catalog = None
        FakeMCP.reads = []
        FakeMCP.documents = {
            A: 'Alpha intro refers to `jac-beta`.\n\n## Walkers\n```jac\n# not a heading\nwalker Example {}\n```\n',
            B: 'Beta introduction.\n\n## Edges\nSee jac://guide/jac-alpha.\n',
        }
        self.version = patch('jacbrain.corpus.compiler_version', return_value=VERSION)
        self.transport = patch('jacbrain.corpus.JacMCP', FakeMCP)
        self.version.start()
        self.transport.start()
        self.addCleanup(self.store.close)
        self.addCleanup(self.version.stop)
        self.addCleanup(self.transport.stop)

    def sync(self, uris=None):
        return sync_guides(self.store, ['jac'], uris=uris)

    def snapshot(self):
        return '\n'.join(self.store.db.iterdump())

    def test_real_shape_import_hashes_metadata_and_fences(self):
        result = self.sync()
        self.assertEqual((result['documents'], result['chunks'], result['edges']), (2, 4, 4))
        rows = list(self.store.db.execute('SELECT g.*,r.content,r.content_hash,r.kind FROM guide_chunks g JOIN records r ON g.record_id=r.id ORDER BY doc_uri,ordinal'))
        self.assertEqual(''.join(row['content'] for row in rows if row['doc_uri'] == A), FakeMCP.documents[A])
        for row in rows:
            self.assertEqual(row['document_hash'], digest(FakeMCP.documents[row['doc_uri']]))
            self.assertEqual(row['content_hash'], digest(row['content']))
        self.assertEqual(rows[1]['section'], 'Walkers')
        self.assertEqual(rows[1]['content'].count('```'), 2)
        self.assertEqual([row['kind'] for row in rows], ['Document', 'Concept', 'Document', 'Concept'])

    def test_idempotent_preserves_status_and_snapshot_hash(self):
        first = self.sync()
        identity = self.store.records(PROJECT, VERSION)[0]['id']
        self.store.db.execute("UPDATE records SET status='reviewed' WHERE id=?", (identity,))
        self.store.db.commit()
        before = self.snapshot()
        second = self.sync()
        self.assertEqual(first, second)
        self.assertEqual(before, self.snapshot())
        self.assertEqual(self.store.get(identity)['status'], 'reviewed')

    def test_partial_refresh_supersedes_removed_sections_preserves_other_guides(self):
        self.sync()
        beta_ids = {r['id'] for r in self.store.records(PROJECT, VERSION) if r['source_uri'].startswith(B)}
        FakeMCP.documents[A] = 'Replacement alpha intro.\n'
        result = self.sync([A])
        current = self.store.records(PROJECT, VERSION)
        self.assertEqual(result['total_documents'], 2)
        self.assertEqual(len(current), 3)
        self.assertTrue(beta_ids <= {r['id'] for r in current})
        new_intro = next(r['id'] for r in current if r['source_uri'].startswith(A))
        self.assertTrue(self.store.db.execute("SELECT 1 FROM edges WHERE target=? AND relation='depends_on'", (new_intro,)).fetchone())

    def test_malformed_or_interrupted_import_leaves_previous_snapshot(self):
        self.sync()
        before = self.snapshot()
        FakeMCP.documents[A] = 'Changed alpha\n'
        for bad in ['', RuntimeError('interrupted'), {'contents': [{'uri': A, 'text': 'wrong URI'}]}]:
            FakeMCP.documents[B] = bad
            with self.assertRaises((ValueError, RuntimeError)):
                self.sync()
            self.assertEqual(before, self.snapshot())

    def test_full_refresh_supersedes_guides_removed_from_catalog(self):
        self.sync()
        old_beta = {r['id'] for r in self.store.records(PROJECT, VERSION) if r['source_uri'].startswith(B)}
        del FakeMCP.documents[B]
        result = self.sync()
        current = self.store.records(PROJECT, VERSION)
        self.assertEqual(result['total_documents'], 1)
        self.assertEqual(len(current), 2)
        self.assertFalse(old_beta & {r['id'] for r in current})
        for identity in old_beta:
            self.assertEqual(self.store.get(identity)['status'], 'superseded')
            self.assertEqual(self.store.neighbors(identity), [])
        # A fresh store with the remaining catalog yields the same full snapshot.
        fresh = Store(':memory:')
        try:
            expected = sync_guides(fresh, ['jac'])
            self.assertEqual(result['snapshot_hash'], expected['snapshot_hash'])
        finally:
            fresh.close()

    def test_transaction_rolls_back_write_failure(self):
        self.sync()
        self.store.db.execute("CREATE TRIGGER reject_new BEFORE INSERT ON records WHEN NEW.content LIKE 'REJECT%' BEGIN SELECT RAISE(ABORT, 'test failure'); END")
        self.store.db.commit()
        before = self.snapshot()
        FakeMCP.documents[A] = 'REJECT this replacement'
        with self.assertRaises(Exception):
            self.sync([A])
        self.assertEqual(before, self.snapshot())

    def test_rejects_duplicate_catalog_selection_version_and_oversized_resources(self):
        FakeMCP.catalog = [{'uri': A}, {'uri': A}]
        with self.assertRaises(ValueError):
            self.sync()
        FakeMCP.catalog = None
        with self.assertRaises(ValueError):
            self.sync([A, A])
        FakeMCP.documents[A] = {'contents': [{'uri': A, 'text': 'x', 'jac_version': '0.1.0'}]}
        with self.assertRaises(ValueError):
            self.sync([A])
        FakeMCP.documents[A] = 'x' * 1_000_001
        with self.assertRaises(ValueError):
            self.sync([A])
        self.assertEqual(self.store.records(PROJECT, VERSION), [])

    def test_version_change_after_fetch_rejected(self):
        with patch('jacbrain.corpus.compiler_version', side_effect=[VERSION, '0.37.24']):
            with self.assertRaises(ValueError):
                self.sync()
        self.assertEqual(self.store.records(PROJECT, VERSION), [])

    def test_duplicate_heading_slugs_do_not_alias_records(self):
        FakeMCP.documents[A] = 'Intro\n## A\nSame\n## A\nSame\n## A-2\nSame\n'
        self.sync([A])
        records = self.store.records(PROJECT, VERSION)
        self.assertEqual(len(records), 4)
        self.assertEqual(len({record['source_uri'] for record in records}), 4)

    def test_large_unicode_sections_are_lossless_and_bounded(self):
        text = '## Long\n' + ('é' * 50_000) + '\n```jac\n' + 'x' * 100_000 + '\n```\n'
        chunks = _parts(text)
        self.assertEqual(''.join(chunks), text)
        self.assertTrue(all(len(chunk.encode('utf-8')) <= 90_000 for chunk in chunks))
        sections = _sections('Intro\n```jac\n## inside fence\n```\n## Real heading\nText\n')
        self.assertEqual([heading for heading, _ in sections], ['Introduction', 'Real heading'])


if __name__ == '__main__':
    unittest.main()

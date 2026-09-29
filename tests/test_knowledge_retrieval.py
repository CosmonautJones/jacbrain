import json
import unittest

from jacbrain.retrieve import context
from jacbrain.store import Store


class KnowledgeRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.store = Store(':memory:')

    def tearDown(self):
        self.store.close()

    def add(self, content, project='@jac-docs', version='0.37.23', uri=None):
        return self.store.add(kind='Concept', content=content, source_uri=uri or 'test:' + content[:40],
                              project=project, jac_version=version)

    def test_shared_guides_visible_without_other_project_leak(self):
        self.add('walker guide')
        self.add('walker private', project='another-project')
        self.add('walker older docs', version='0.1.0')
        result = context(self.store, 'walker', 'my-app', '0.37.23')
        self.assertEqual(len(result['items']), 1)
        self.assertIn('guide', result['items'][0]['content'])
        self.assertEqual(context(self.store, 'walker', 'my-app', '0.37.23', include_guides=False)['items'], [])

    def test_rare_specific_terms_outrank_generic_overlap(self):
        specific = self.add('## Postinit fields\nUse postinit for derived instance fields.')
        self.add('Jac code uses nodes and walkers. ' * 20)
        result = context(self.store, 'How to write Jac code for postinit fields?', 'app', '0.37.23')
        self.assertEqual(result['items'][0]['id'], specific)

    def test_dependency_expansion_can_be_compared_to_flat(self):
        first = self.add('## Collect offers\nOffer collection walker matches.')
        dependency = self.add('## Report channel\nType the reports list explicitly.')
        self.store.link(first, dependency, 'depends_on')
        flat = context(self.store, 'Offer collection', 'app', '0.37.23', expand_graph=False)
        graph = context(self.store, 'Offer collection', 'app', '0.37.23')
        self.assertNotIn(dependency, [item['id'] for item in flat['items']])
        self.assertIn(dependency, [item['id'] for item in graph['items']])
        self.assertLessEqual(len(json.dumps(graph, ensure_ascii=False).encode()), 6000)

    def test_unicode_excerpt_budget_and_matching_text(self):
        self.add('é' * 5000 + ' needle ' + 'é' * 5000)
        packet = context(self.store, 'needle', 'app', '0.37.23', max_bytes=1200)
        self.assertLessEqual(len(json.dumps(packet, ensure_ascii=False).encode()), 1200)
        self.assertIn('needle', packet['items'][0]['content'])

import unittest
from compose import plan, pick, replace, AdmissionError

class TestAliasAndDictionaryKeys(unittest.TestCase):
    def test_alias_list_index_rejected_in_plan(self):
        workflow = {
            'schema': 'deus-one-public-dag/1',
            'workflow_id': 'alias',
            'context_sha256': '0' * 64,
            'steps': [
                {
                    'id': 'source',
                    'family': 'evidence',
                    'payload': {},
                    'depends_on': [],
                    'bindings': []
                },
                {
                    'id': 'consumer',
                    'family': 'evidence',
                    'payload': {'records': [1]},
                    'depends_on': ['source'],
                    'bindings': [
                        {'from_step': 'source', 'output_pointer': '/a', 'payload_pointer': '/records/00'},
                        {'from_step': 'source', 'output_pointer': '/b', 'payload_pointer': '/records/0'}
                    ]
                }
            ]
        }
        with self.assertRaises(AdmissionError):
            plan(workflow)

    def test_valid_dictionary_key_variant_plans_successfully(self):
        workflow = {
            'schema': 'deus-one-public-dag/1',
            'workflow_id': 'dict_keys',
            'context_sha256': '0' * 64,
            'steps': [
                {
                    'id': 'source',
                    'family': 'evidence',
                    'payload': {},
                    'depends_on': [],
                    'bindings': []
                },
                {
                    'id': 'consumer',
                    'family': 'evidence',
                    'payload': {'records': {'00': 1, '0': 2}},
                    'depends_on': ['source'],
                    'bindings': [
                        {'from_step': 'source', 'output_pointer': '/a', 'payload_pointer': '/records/00'},
                        {'from_step': 'source', 'output_pointer': '/b', 'payload_pointer': '/records/0'}
                    ]
                }
            ]
        }
        catalog, order = plan(workflow)
        self.assertEqual(order, ['source', 'consumer'])

    def test_nested_list_and_canonical_pointers(self):
        data = {'matrix': [[10, 20], [30, 40]]}
        self.assertEqual(pick(data, '/matrix/1/0'), 30)
        
        payload = {'matrix': [[10, 20], [30, 40]]}
        replace(payload, '/matrix/1/0', 99)
        self.assertEqual(payload, {'matrix': [[10, 20], [99, 40]]})

    def test_noncanonical_array_indices_rejected(self):
        data = [10, 20]
        with self.assertRaises(AdmissionError):
            pick(data, '/00')
        with self.assertRaises(AdmissionError):
            pick(data, '/-1')
        
        payload = [10, 20]
        with self.assertRaises(AdmissionError):
            replace(payload, '/+1', 99)

if __name__ == '__main__':
    unittest.main()

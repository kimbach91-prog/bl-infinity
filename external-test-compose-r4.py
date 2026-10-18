import unittest
from compose import pick, replace, AdmissionError

class TestComposeExactFinal(unittest.TestCase):
    def test_replace_out_of_bounds_raises_admission_error(self):
        payload = {'records': [1, 2]}
        with self.assertRaises(AdmissionError) as ctx:
            replace(payload, '/records/5', 3)
        self.assertEqual(str(ctx.exception), 'NO_NEW_PAYLOAD_KEYS')
        self.assertEqual(payload, {'records': [1, 2]})

    def test_replace_invalid_index_token_raises_admission_error(self):
        payload = {'records': [1, 2]}
        with self.assertRaises(AdmissionError) as ctx:
            replace(payload, '/records/abc', 3)
        self.assertEqual(str(ctx.exception), 'NO_NEW_PAYLOAD_KEYS')
        self.assertEqual(payload, {'records': [1, 2]})

    def test_pick_missing_key_raises_admission_error(self):
        data = {'a': 1}
        with self.assertRaises(AdmissionError) as ctx:
            pick(data, '/b')
        self.assertEqual(str(ctx.exception), 'BOUNDED_JSON_POINTER')

    def test_existing_error_codes_preserved(self):
        data = {'a': 1}
        with self.assertRaises(AdmissionError) as ctx:
            pick(data, '/a/10')
        self.assertEqual(str(ctx.exception), 'POINTER_NON_CONTAINER')

        payload = {'records': [1, 2]}
        with self.assertRaises(AdmissionError) as ctx:
            replace(payload, '/nonexistent', 3)
        self.assertEqual(str(ctx.exception), 'NO_NEW_PAYLOAD_KEYS')

    def test_valid_operations(self):
        data = {'nested': {'items': [10, 20]}}
        self.assertEqual(pick(data, '/nested/items/1'), 20)
        
        payload = {'nested': {'items': [10, 20]}}
        replace(payload, '/nested/items/1', 99)
        self.assertEqual(payload, {'nested': {'items': [10, 99]}})

if __name__ == '__main__':
    unittest.main()

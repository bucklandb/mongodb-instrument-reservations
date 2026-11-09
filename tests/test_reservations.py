from copy import deepcopy
from datetime import timedelta
import unittest

from src.reservations import (load_records, validate_records, preparation_schedule,
                              preparation_pipeline, find_conflicts, seed_new_demo_collection)


class FakeCollection:
    """Minimal test double for seeding only; not a MongoDB emulator."""
    def __init__(self):
        self.documents = {}
        self.indexes = []

    def create_index(self, key, unique=False):
        self.indexes.append((key, unique))

    def update_one(self, selector, update, upsert=False):
        key = selector['reservation_id']
        doc = self.documents.get(key)
        if '$setOnInsert' in update:
            if doc is None and upsert:
                self.documents[key] = deepcopy(update['$setOnInsert'])
            return
        if '$rename' in update and doc:
            for old, new in update['$rename'].items():
                if old in doc and new not in doc:
                    doc[new] = doc.pop(old)
            return
        if '$rename' not in update:
            raise AssertionError('Unexpected update operation')


class ReservationsTest(unittest.TestCase):
    def setUp(self):
        self.records = load_records()

    def test_expected_ids_and_order(self):
        result = preparation_schedule(list(reversed(self.records)))
        self.assertEqual([r['reservation_id'] for r in result], ['BIO-1001', 'BIO-1002'])
        self.assertTrue(all(r['training_verified'] for r in result))

    def test_confirmed_untrained_is_excluded(self):
        self.records[0]['researcher']['completed_training'] = []
        self.assertEqual([r['reservation_id'] for r in preparation_schedule(self.records)], ['BIO-1002'])

    def test_pending_trained_is_excluded(self):
        self.records[2]['researcher']['completed_training'].append('Plate Reader Training')
        self.assertEqual(len(preparation_schedule(self.records)), 2)

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError):
            validate_records(self.records + [deepcopy(self.records[0])])

    def test_invalid_times_rejected(self):
        self.records[0]['reservation_window']['start'] = self.records[0]['reservation_window']['end']
        with self.assertRaises(ValueError):
            validate_records(self.records)

    def test_naive_times_rejected(self):
        self.records[0]['reservation_window']['start'] = self.records[0]['reservation_window']['start'].replace(tzinfo=None)
        with self.assertRaises(ValueError):
            validate_records(self.records)

    def test_unknown_status_rejected(self):
        self.records[0]['reservation_status'] = 'Approved'
        with self.assertRaises(ValueError):
            validate_records(self.records)

    def test_training_must_be_list(self):
        self.records[0]['researcher']['completed_training'] = 'PCR Safety'
        with self.assertRaises(ValueError):
            validate_records(self.records)

    def test_overlap_blocked_but_adjacent_allowed(self):
        overlap = deepcopy(self.records[0])
        overlap['reservation_id'] = 'BIO-TEST'
        overlap['reservation_window']['start'] += timedelta(minutes=30)
        self.assertEqual(find_conflicts(self.records + [overlap]), [('BIO-1001', 'BIO-TEST')])
        with self.assertRaises(ValueError):
            preparation_schedule(self.records + [overlap])
        overlap['reservation_window']['start'] = self.records[0]['reservation_window']['end']
        overlap['reservation_window']['end'] = overlap['reservation_window']['start'] + timedelta(hours=1)
        self.assertEqual(find_conflicts(self.records + [overlap]), [])

    def test_seed_is_idempotent_and_preserves_existing_values(self):
        collection = FakeCollection()
        seed_new_demo_collection(collection, self.records)
        self.assertEqual(len(collection.documents), 3)
        self.assertNotIn('booking_status', collection.documents['BIO-1001'])
        collection.documents['BIO-1002']['research_purpose'] = 'Edited after seeding'
        seed_new_demo_collection(collection, self.records)
        self.assertEqual(len(collection.documents), 3)
        self.assertEqual(collection.documents['BIO-1002']['research_purpose'], 'Edited after seeding')
        self.assertEqual(collection.indexes[0], ('reservation_id', True))
        self.assertIn('reservation_status', self.records[0])

    def test_empty_seed_rejected(self):
        with self.assertRaises(ValueError):
            seed_new_demo_collection(FakeCollection(), [])

    def test_pipeline_filters_training_and_has_stable_sort(self):
        pipeline = preparation_pipeline()
        self.assertEqual(pipeline[0]['$match']['reservation_status'], 'Confirmed')
        self.assertIn('$expr', pipeline[0]['$match'])
        self.assertIn('$in', pipeline[0]['$match']['$expr'])
        self.assertEqual(pipeline[-1]['$sort'], {'reservation_start': 1, 'reservation_id': 1})

    def test_schedule_does_not_mutate_input(self):
        before = deepcopy(self.records)
        result = preparation_schedule(self.records)
        result[0]['preparation_requirements'].append('Example change')
        self.assertEqual(before, self.records)


if __name__ == '__main__':
    unittest.main()

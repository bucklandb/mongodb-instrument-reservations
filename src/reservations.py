"""Fictional instrument-reservation preparation demo; not access control."""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid

ROOT = Path(__file__).resolve().parents[1]
DEMO_DATABASE = 'portfolio_instrument_demo'
FIXTURE = ROOT / 'data' / 'reservations.json'


def validate_records(records):
    """Validate fixture shape, identity, statuses and aware time intervals."""
    seen = set()
    for record in records:
        key = record['reservation_id']
        if not isinstance(key, str) or not key or key in seen:
            raise ValueError('Reservation IDs must be nonempty and unique')
        seen.add(key)
        if record['reservation_status'] not in {'Confirmed', 'Pending', 'Cancelled'}:
            raise ValueError('Unsupported reservation status')
        researcher = record['researcher']
        instrument = record['instrument']
        for value in (researcher['researcher_id'], researcher['name']['first'],
                      researcher['name']['last'], instrument['asset_id'],
                      instrument['instrument_name'], instrument['training_required'],
                      instrument['lab_location']['building'], instrument['lab_location']['room']):
            if not isinstance(value, str) or not value:
                raise ValueError('Required identifiers and labels must be nonempty strings')
        for values in (researcher['completed_training'], record['preparation_requirements']):
            if not isinstance(values, list) or not all(isinstance(v, str) and v for v in values):
                raise ValueError('Training and preparation must be lists of nonempty strings')
        start, end = (record['reservation_window'][key] for key in ('start', 'end'))
        if any(not isinstance(t, datetime) or t.utcoffset() is None for t in (start, end)):
            raise ValueError('Reservation times must be timezone-aware datetimes')
        if start >= end:
            raise ValueError('Reservation end must be after start')
    return records


def load_records(path=FIXTURE):
    records = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(records, list):
        raise ValueError('Fixture root must be a list')
    for record in records:
        for key in ('start', 'end'):
            record['reservation_window'][key] = datetime.fromisoformat(record['reservation_window'][key])
    return validate_records(records)


def training_verified(record):
    return record['instrument']['training_required'] in record['researcher']['completed_training']


def eligible_records(records):
    return [r for r in records if r['reservation_status'] == 'Confirmed' and training_verified(r)]


def find_conflicts(records):
    """Report overlapping eligible reservations for the same asset; endpoints may touch."""
    validate_records(records)
    eligible = sorted(eligible_records(records), key=lambda r: (r['reservation_window']['start'], r['reservation_id']))
    conflicts = []
    for index, left in enumerate(eligible):
        for right in eligible[index + 1:]:
            if (left['instrument']['asset_id'] == right['instrument']['asset_id']
                    and left['reservation_window']['start'] < right['reservation_window']['end']
                    and right['reservation_window']['start'] < left['reservation_window']['end']):
                conflicts.append((left['reservation_id'], right['reservation_id']))
    return conflicts


def preparation_schedule(records):
    """Return confirmed, training-eligible records; reject ambiguous asset overlaps."""
    validate_records(records)
    if find_conflicts(records):
        raise ValueError('Conflicting eligible reservations require human review')
    result = []
    for record in eligible_records(records):
        result.append({
            'reservation_id': record['reservation_id'],
            'researcher_name': record['researcher']['name']['first'] + ' ' + record['researcher']['name']['last'],
            'instrument': record['instrument']['instrument_name'],
            'asset_id': record['instrument']['asset_id'],
            'lab_location': record['instrument']['lab_location']['building'] + ' - Room ' + record['instrument']['lab_location']['room'],
            'reservation_start': record['reservation_window']['start'],
            'training_required': record['instrument']['training_required'],
            'training_verified': True,
            'preparation_requirements': list(record['preparation_requirements']),
        })
    return sorted(result, key=lambda r: (r['reservation_start'], r['reservation_id']))


def preparation_pipeline():
    """MongoDB equivalent of the fixture eligibility/projection/sort rules."""
    return [
        {'$match': {'reservation_status': 'Confirmed', '$expr': {'$in': [
            '$instrument.training_required', {'$ifNull': ['$researcher.completed_training', []]}
        ]}}},
        {'$project': {
            '_id': 0, 'reservation_id': 1,
            'researcher_name': {'$concat': ['$researcher.name.first', ' ', '$researcher.name.last']},
            'instrument': '$instrument.instrument_name', 'asset_id': '$instrument.asset_id',
            'lab_location': {'$concat': ['$instrument.lab_location.building', ' - Room ', '$instrument.lab_location.room']},
            'reservation_start': '$reservation_window.start',
            'training_required': '$instrument.training_required',
            'training_verified': {'$literal': True}, 'preparation_requirements': 1,
        }},
        {'$sort': {'reservation_start': 1, 'reservation_id': 1}},
    ]


def seed_new_demo_collection(collection, records):
    """Internal seeder: call only for a newly created, dedicated demo collection.

    Repeating against that same collection never deletes or overwrites documents.
    This is not a general schema migration for user collections.
    """
    validate_records(records)
    if not records:
        raise ValueError('At least one fixture record is required')
    if find_conflicts(records):
        raise ValueError('Conflicting fixture reservations')
    collection.create_index('reservation_id', unique=True)
    first = deepcopy(records[0])
    first['booking_status'] = first.pop('reservation_status')
    collection.update_one({'reservation_id': first['reservation_id']}, {'$setOnInsert': first}, upsert=True)
    collection.update_one(
        {'reservation_id': first['reservation_id'], 'booking_status': {'$exists': True}, 'reservation_status': {'$exists': False}},
        {'$rename': {'booking_status': 'reservation_status'}},
    )
    for record in records[1:]:
        collection.update_one({'reservation_id': record['reservation_id']}, {'$setOnInsert': deepcopy(record)}, upsert=True)


def run_mongo_demo(records):
    """Opt-in local-only database writes in a fresh UUID collection, with no deletions."""
    validate_records(records)
    expected = preparation_schedule(records)
    try:
        from pymongo import MongoClient
    except ImportError as error:
        raise RuntimeError('Install requirements-mongo.txt for the opt-in MongoDB run') from error
    name = 'demo_run_' + uuid.uuid4().hex
    client = MongoClient('mongodb://127.0.0.1:27017', serverSelectionTimeoutMS=5000, tz_aware=True)
    try:
        client.admin.command('ping')
        collection = client[DEMO_DATABASE].create_collection(name)
        print(f'Created demonstration collection: {DEMO_DATABASE}.{name}')
        print('This collection is retained. No existing collection is changed or deleted.')
        seed_new_demo_collection(collection, records)
        seed_new_demo_collection(collection, records)  # Explicit repeatability check.
        if collection.count_documents({}) != len(records):
            raise AssertionError('Unexpected document count after repeated seeding')
        actual = list(collection.aggregate(preparation_pipeline()))
        if actual != expected:
            raise AssertionError('MongoDB output differs from the offline reference')
        return actual
    finally:
        client.close()


def json_default(value):
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    raise TypeError(f'Unsupported JSON type: {type(value).__name__}')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mongo', action='store_true', help='Write the fictional fixture to a new collection on local MongoDB')
    args = parser.parse_args(argv)
    records = load_records()
    result = run_mongo_demo(records) if args.mongo else preparation_schedule(records)
    print(json.dumps(result, indent=2, default=json_default))


if __name__ == '__main__':
    main()

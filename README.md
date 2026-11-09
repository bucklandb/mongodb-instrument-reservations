# MongoDB instrument reservations

A small NoSQL demonstration using three fictional biotechnology instrument reservations. Nested researcher, instrument and scheduling data become a chronological preparation list. This is a learning example, not a production booking system or permission to operate laboratory equipment.

## What it demonstrates

- Nested documents and arrays for related records.
- A field migration from `booking_status` to `reservation_status`.
- Repeatable fixture insertion with a unique reservation ID.
- Aggregation that requires both confirmed status and the listed training.
- Validation and tests, including untrained requests and conflicting time windows.

## Quick start: no database required

Use Python 3.11 or newer. From this directory:

```sh
python -m src.reservations
python -m unittest discover -s tests -v
```

The default run reads the fictional JSON fixture and prints **BIO-1001** and **BIO-1002** in time order. It does not connect to a database or change files. The pending BIO-1003 reservation is excluded. The notebook in `notebooks/` runs this same offline demonstration.

## Optional MongoDB demonstration

This path is opt-in and writes data. Use an existing local MongoDB Community Server that you control, listening on `127.0.0.1:27017`. Do not point this demo at a work or shared database.

```sh
python -m pip install -r requirements-mongo.txt
python -m src.reservations --mongo
```

Each run creates a fresh UUID-named collection in the fixed `portfolio_instrument_demo` database. It prints the exact collection name, inserts only fictional records, renames the first record's status field, seeds again to check repeatability, and compares MongoDB's aggregation with the offline result. It never drops a collection, deletes documents or overwrites existing values. The demo collection is retained so you can inspect it. Remove it manually if you no longer need it. No automatic cleanup or reset is included.

The seeding function is internal to this fresh-collection flow. It is not a migration utility for existing user data. Input validation and overlap checks run before any connection is opened. A unique index protects reservation IDs, but there is no transactional booking service or concurrent conflict prevention.

## Changes from the course notebook

The original ALY2100 discussion notebook is preserved separately and is unchanged. This version:

- Replaces the original destructive collection reset with a fresh isolated collection.
- Moves the original three fictional records into an inspectable JSON fixture.
- Uses reserved `example.com` email addresses rather than `example.edu`.
- Assigns UTC to the fictional example times for a reproducible demonstration. The original times were naive; no actual timezone was inferred.
- Filters out confirmed-but-untrained records instead of merely displaying a training flag.
- Adds offline tests, explicit overlap checks and guaranteed connection closure.
- Clears original execution metadata and replaces the old notebook walkthrough with a safe offline walkthrough of the same scenario.

The AI-assisted portfolio refactor is a new adaptation, not a claim that the original code was entirely unaided. See [provenance](docs/provenance.md).

## Verification and limits

The standard-library tests cover fixture validation, eligibility, stable ordering, time handling, overlaps and non-destructive repeatable seeding through a minimal test double. The test double does **not** validate server behavior. The MongoDB pipeline structure is inspected in tests, not executed there.

All 13 offline tests and every code cell of the walkthrough passed on Python 3.12 during preparation. GitHub Actions runs the offline tests on Python 3.12 and 3.13. A native MongoDB server, PyMongo integration and Jupyter UI were **not run** in the preparation environment. The `--mongo` path includes output-equivalence and repeated-seed checks for a future local verification.

This is a snapshot of synthetic reservations, not a live availability query. It does not enforce authentication, real training records, lab safety, working hours, equipment calibration, inventory or concurrent reservations. The overlap check considers only confirmed, training-eligible records. No clinical or operational assurance is implied.

## Dependencies and license

Offline use needs only Python's standard library. Optional PyMongo 4.19.0 is Apache-2.0 licensed. MongoDB Community Server has its own SSPL terms and is not distributed in this project.

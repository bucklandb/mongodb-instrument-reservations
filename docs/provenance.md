# Provenance and scope

This project adapts Benjamin Buckland's original ALY2100 MongoDB discussion notebook, dated July 9, 2026. The source notebook labels all three instrument reservations fictional. Its literal records were extracted without running database commands; the original notebook remains unchanged.

Benjamin confirms that no instructor code was used in this project and that sources used are referenced. The portfolio refactor was prepared with AI assistance in November 2026. It adds a safe offline walkthrough, isolated opt-in database execution, training eligibility filters, explicit time handling, overlap checks, tests and documentation. This is an adaptation rather than the unchanged course submission or a claim of wholly unaided authorship.

## Fictional data

Names, IDs, contact details and reservations are fictional examples. There is no external dataset or employer data input. Email addresses use the reserved `example.com` domain. Original naive times were assigned UTC solely for this example, without inferring a real timezone. The fixture contains three records; two qualify for the preparation list.

Original source SHA-256: `f86dbddd8785c2b4520fcb5ed0326b9f211b69603d154bdde1fdb63213084ecf`.

## Verification scope

The offline reference, all 13 unit tests and the walkthrough's Python cells were executed successfully. Tests use a minimal collection double for repeated seeding; this does not validate MongoDB server behavior. Native MongoDB/PyMongo integration and the Jupyter interface were not run. The optional `--mongo` command checks repeated seeding and output equivalence when used with a local server.

## Dependency references

- PyMongo: https://pypi.org/project/pymongo/ (Apache-2.0).
- MongoDB licensing FAQ: https://www.mongodb.com/legal/licensing/server-side-public-license/faq.

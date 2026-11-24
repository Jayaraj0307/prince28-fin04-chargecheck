# \# ChargeCheck - Database Verification

#

# \## D03 - Database Verification

#

# \## PostgreSQL Index VerificationDocuments table

* ix\_documents\_doc\_type - B-tree index on doc\_type
* ix\_documents\_metadata\_gin - GIN index on JSONB metadata
* ix\_documents\_sha256 - B-tree index on sha256
* pk\_documents - Primary key on id
* uq\_documents\_external\_id - Unique index on external\_id

### Pages table

* ix\_pages\_document\_id - B-tree index on document\_id
* pk\_pages - Primary key on id

## EXPLAIN Query Plan

Query:
EXPLAIN SELECT \* FROM documents WHERE doc\_type = 'record';

Verified output:
Index Scan using ix\_documents\_doc\_type on documents
Index Cond: ((doc\_type)::text = 'record'::text)

Result: PostgreSQL uses ix\_documents\_doc\_type to filter documents by doc\_type.

## Verification Environment

* Database: PostgreSQL
* Database service: Docker Compose
* Index definitions: Verified using pg\_indexes
* Query plan: Verified using EXPLAIN





\## D05 - CI/CD and Production Verification



\### CI/CD Pipeline

\- GitHub Actions runs linting, formatting, database migrations, and tests.

\- The Docker image is built and pushed to GitHub Container Registry.

\- Successful pushes to main trigger production deployment to Render.

\- The CD workflow verifies production health after CI succeeds.



\### Smoke Test

\- Script: `scripts/smoke.py`

\- Endpoint: `/health`

\- Expected HTTP status: 200

\- Expected response status: `ok`

\- Local smoke test passed against the live production API.



\### Rollback Drill

1\. Identify the last known-good production deployment in Render.

2\. Use Render's rollback option to restore that deployment if a release fails.

3\. Run `uv run python scripts/smoke.py`.

4\. Confirm the health endpoint returns HTTP 200.

5\. Record the rollback result and recovery time.



\### Deployment Lead Time

Measure lead time from merging a commit into `main` until the production smoke test passes. Record the actual duration using GitHub Actions and Render deployment timestamps. Do not estimate or invent a duration.

## D06 - Corpus Downloader and Dataset

### Sources and Corpus
- Source URLs: 10 across 8 named banks.
- Original corpus restored: 10 files.
- Valid PDFs: 6; HTML files: 2; invalid PDF files containing HTML: 2.
- Valid PDF pages: 74.
- Total corpus size: 10.16 MB.
- Estimated storage for 2,500 pages: 297.12 MB.
- Indian Bank: one URL blocked by robots; another returned HTML instead of a valid PDF.
- No robots.txt restrictions were bypassed.

### Downloader and Tests
- Downloader supports retries, backoff, per-host delay, concurrency limits, manifest tracking and atomic file downloads.
- Downloader unit tests: 22 passed.
- Full test suite: 40 passed.
- Ruff lint and format checks passed.

### Resume Verification
- Initial run: 8 downloaded, 1 blocked.
- Clean rerun: 8 downloaded, 1 failed.
- Resume rerun: 0 downloaded, 8 skipped, 1 failed.
- No unfinished .part files found.
- Original corpus and manifest restored: 10 files and 13 manifest entries.
- Note: the downloader completed before Ctrl+C, so an actual mid-download interruption was not verified.

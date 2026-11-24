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


## D07 Â· Parser comparison

<!-- parsers:start -->
| File | Parsers (A / B) | Pages | A found | B found | Time (A / B) | Better, why |
|---|---|---|---|---|---|---|
| website-upload-modification-sept26-1c39be84.pdf | PyMuPDF / pypdf | - | FAILED: no_text_layer | FAILED: no_text_layer | 0.01 s / 0.02 s | Neither â€” both need OCR |
| service-charges-e8565b80.html | trafilatura / strip tags | 16 | 125,455 chars, 2 headings, 0 tables | 158,004 chars, 4 headings, 0 tables | 0.58 s / 0.04 s | trafilatura â€” prefer structured extraction; verify content quality |
| compendium-of-service-charges-new-55aed543.pdf | PyMuPDF / pypdf | 21 | 189,588 chars, 15 headings, 28 tables | 50,416 chars, 2 headings, 0 tables | 4.60 s / 0.51 s | PyMuPDF â€” 189,588 chars and 28 tables |
| non-credit-and-non-forex-service-charges-6ab262f | trafilatura / strip tags | 8 | 37,175 chars, 1 headings, 0 tables | 49,805 chars, 1 headings, 0 tables | 0.22 s / 0.03 s | Strip tags â€” more extracted text; inspect quality |
| 9b8f03ee-8845-de32-906b-df3dd5bb58e9-7cf2d229.pdf | PyMuPDF / pypdf | 28 | 83,427 chars, 12 headings, 54 tables | 46,049 chars, 3 headings, 0 tables | 3.69 s / 0.77 s | PyMuPDF â€” 83,427 chars and 54 tables |
| axis-bank-easy-access-savings-account-mid-3058cd.pdf | PyMuPDF / pypdf | 2 | 10,285 chars, 3 headings, 2 tables | 7,256 chars, 1 headings, 0 tables | 0.44 s / 0.10 s | PyMuPDF â€” 10,285 chars and 2 tables |
| soc-burgundy-8e822d49.pdf | PyMuPDF / pypdf | 3 | 4,519 chars, 24 headings, 4 tables | 3,633 chars, 0 headings, 0 tables | 0.52 s / 0.10 s | PyMuPDF â€” 4,519 chars, 24 headings and 4 tables |
| digital-savings-account-in-person-kyc-ee44d92f.pdf | PyMuPDF / pypdf | 3 | 7,903 chars, 8 headings, 3 tables | 6,966 chars, 1 headings, 0 tables | 0.51 s / 0.05 s | PyMuPDF â€” 7,903 chars, 8 headings and 3 tables |
<!-- parsers:end -->


### D07 Â· Parsing my corpus

- Files parsed: 8 Â· parsed successfully: 8 Â· failed: 0 Â· pages in Postgres: 98
- Parsing coverage: 100% of the 8 downloaded documents

### Failures by reason

| Reason | Files | What I did |
|---|---:|---|
| no_text_layer | 1 | Retried using Tesseract OCR with English language data |

- The one I fixed: Revision of Inland Service Charges effective 20 October 2026, reason: no_text_layer, fix: OCR using Tesseract with `eng`.

### What I saw when I read my parsed pages

- A page where the heading path is right: Not confirmed yet; the five inspected pages had empty heading lists.
- Something that came out wrong: Revision of Inland Service Charges, page 17 â€” OCR produced duplicated and merged text.
- A table: Revision of Inland Service Charges, page 13 â€” extracted as loose text with pipe separators rather than a clean Markdown grid.

### My parser choice

- For PDFs I use PyMuPDF because it extracted 189,588 characters and 28 tables from the compendium PDF, compared with pypdf's 50,416 characters and zero tables.
- A kind of document in my corpus that neither parser handles well: scanned PDFs without a text layer; these require OCR.

### One thing that went wrong today, and how I fixed it

One scanned PDF failed with `no_text_layer`. I installed Tesseract OCR and reran the parser with `--retry-failed --ocr eng`. It successfully extracted 17 pages.

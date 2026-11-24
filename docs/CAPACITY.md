# ChargeCheck Corpus Capacity

## Measured baseline

- Valid PDF files: 6
- Invalid PDF files containing HTML: 2
- HTML files: 2
- Measured PDF pages: 74
- Total corpus size: 10.16 MB
- Average PDF size per page: 121.70 KB
- Target corpus: 2,500 pages
- Estimated PDF storage: 297.12 MB
- Estimated 10x storage: 2,971.15 MB

## Capacity answers

1. **Embedding cost:** Cannot be calculated accurately yet. Extract text, count tokens, select an embedding model and apply its current per-token price.

2. **PostgreSQL storage:** Initially plan for at least 1 GB, including extracted text, metadata and vector embeddings. Monitor actual usage.

3. **Least certain estimate:** The 297.12 MB storage estimate. It extrapolates from only 74 measured pages.

4. **10x growth:** Use batch processing, database indexes, pagination, monitoring and backups. Keep original PDFs in file/object storage.

## Known gaps

- Two Indian Bank files contain HTML despite their .pdf extensions.
- Only 74 valid PDF pages were measured.
- HTML page sizes are excluded from the PDF storage estimate.
- Embedding costs and actual database storage have not yet been measured.
- Source coverage and document formats need further validation.

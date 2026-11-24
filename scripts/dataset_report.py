import argparse
import json
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
MANIFEST = ROOT / "data" / "manifest.jsonl"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--full-pages", type=int, required=True)
    args = parser.parse_args()

    records = [
        json.loads(line)
        for line in MANIFEST.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    # Keep only the latest manifest record for each URL.
    latest_records = {}
    for record in records:
        latest_records[record["url"]] = record

    downloaded = [
        record for record in latest_records.values() if record.get("status") == "downloaded"
    ]

    files = sorted(path for path in RAW.rglob("*") if path.is_file())
    total_bytes = sum(path.stat().st_size for path in files)

    pdf_files = [p for p in files if p.suffix.lower() == ".pdf"]
    html_files = [p for p in files if p.suffix.lower() in {".html", ".htm"}]

    page_count = 0
    for path in pdf_files:
        try:
            page_count += len(PdfReader(str(path)).pages)
        except Exception as exc:
            print(f"WARNING: Could not read {path}: {exc}")

    pdf_bytes = sum(p.stat().st_size for p in pdf_files)
    average_page_bytes = pdf_bytes / page_count if page_count else 0
    estimated_bytes = average_page_bytes * args.full_pages

    banks = sorted({r.get("source", "Unknown") for r in downloaded})

    dataset = [
        "# ChargeCheck Dataset",
        "",
        "## Current corpus",
        f"- Downloaded files: {len(files)}",
        f"- PDF files: {len(pdf_files)}",
        f"- HTML files: {len(html_files)}",
        f"- PDF pages measured: {page_count}",
        f"- Total size: {total_bytes / (1024 * 1024):.2f} MB",
        f"- Banks represented in manifest: {len(banks)}",
        "",
        "## Sources",
    ]

    for record in downloaded:
        dataset.append(
            f"- **{record.get('source', 'Unknown')}** — "
            f"[{record.get('title', 'Untitled')}]({record.get('url', '')}) "
            f"— {record.get('path', 'No local path')}"
        )

    dataset += [
        "",
        "## Known gaps",
        "- Review blocked, failed and invalid sources.",
    ]

    (ROOT / "DATASET.md").write_text(
        "\n".join(dataset) + "\n",
        encoding="utf-8",
    )

    capacity = [
        "# ChargeCheck Corpus Capacity",
        "",
        "## Measured baseline",
        f"- Measured PDF pages: {page_count}",
        f"- Measured PDF size: {pdf_bytes / (1024 * 1024):.2f} MB",
        f"- Average PDF size per page: {average_page_bytes / 1024:.2f} KB",
        f"- Target corpus: {args.full_pages:,} pages",
        f"- Estimated PDF storage: {estimated_bytes / (1024 * 1024):.2f} MB",
        f"- Estimated 10x storage: {estimated_bytes * 10 / (1024 * 1024):.2f} MB",
        "",
        "## Questions to answer",
        "1. What is the estimated embedding cost for the full corpus?",
        "2. What PostgreSQL storage limit should the project plan for?",
        "3. Which estimate above is least certain, and why?",
        "4. What changes are needed for 10x corpus growth?",
        "",
        "## Known gaps",
        "- Add limitations in source coverage, document formats and measurements.",
    ]

    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "CAPACITY.md").write_text(
        "\n".join(capacity) + "\n",
        encoding="utf-8",
    )

    print(f"Files: {len(files)}")
    print(f"PDFs: {len(pdf_files)}")
    print(f"HTML files: {len(html_files)}")
    print(f"PDF pages: {page_count}")
    print(f"Total size: {total_bytes / (1024 * 1024):.2f} MB")
    print(f"Estimated {args.full_pages} page corpus: {estimated_bytes / (1024 * 1024):.2f} MB")
    print("Created DATASET.md and docs/CAPACITY.md")


if __name__ == "__main__":
    main()

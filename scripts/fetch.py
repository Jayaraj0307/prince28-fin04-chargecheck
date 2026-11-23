"""Command-line tools for fetching and registering ChargeCheck sources."""

import argparse
import asyncio
import csv
import hashlib
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from chargecheck.ingest.fetch import (
    Manifest,
    fetch_all,
    now_iso,
    read_sources,
    slug,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCES_FILE = ROOT / "data" / "sources.csv"
MANIFEST_FILE = ROOT / "data" / "manifest.jsonl"
RAW_DIR = ROOT / "data" / "raw"


def command_urls(args):
    """Download URLs listed in data/sources.csv."""
    sources = read_sources(SOURCES_FILE)

    def report(record):
        print(f"{record['status']:10} {record['source']} - {record['url']}")

    counts = asyncio.run(
        fetch_all(
            sources,
            root=ROOT,
            max_concurrency=args.max_concurrency,
            per_host_delay=args.delay,
            on_result=report,
        )
    )

    print("\nDownload summary:")
    for status, count in counts.items():
        print(f"  {status}: {count}")


def command_repo(args):
    """Download selected files from a Git repository."""
    owner, repo = args.repository.split("/", 1)
    git_url = f"https://github.com/{owner}/{repo}.git"
    source_dir = Path(args.path)
    extensions = {ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in args.ext}

    with tempfile.TemporaryDirectory() as temporary:
        checkout = Path(temporary) / "repo"

        subprocess.run(
            [
                "git",
                "clone",
                "--filter=blob:none",
                "--no-checkout",
                git_url,
                str(checkout),
            ],
            check=True,
        )

        subprocess.run(
            ["git", "-C", str(checkout), "sparse-checkout", "init", "--cone"],
            check=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(checkout),
                "sparse-checkout",
                "set",
                args.path,
            ],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(checkout), "checkout", args.ref],
            check=True,
        )

        commit = subprocess.run(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

        manifest = Manifest(MANIFEST_FILE)
        copied = 0

        for file in (checkout / source_dir).rglob("*"):
            if not file.is_file() or file.suffix.lower() not in extensions:
                continue

            relative = file.relative_to(checkout).as_posix()
            raw_path = RAW_DIR / slug(args.source) / relative
            raw_path.parent.mkdir(parents=True, exist_ok=True)

            content = file.read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            url = f"https://github.com/{owner}/{repo}/blob/{commit}/{relative}"

            previous = manifest.records.get(url)
            if (
                previous
                and previous.get("status") == "downloaded"
                and raw_path.is_file()
                and hashlib.sha256(raw_path.read_bytes()).hexdigest() == digest
            ):
                print(f"skipped    {relative}")
                continue

            raw_path.write_bytes(content)

            manifest.add(
                {
                    "url": url,
                    "source": args.source,
                    "licence": args.licence,
                    "title": file.name,
                    "path": raw_path.relative_to(ROOT).as_posix(),
                    "bytes": len(content),
                    "sha256": digest,
                    "content_type": "",
                    "http_status": None,
                    "status": "downloaded",
                    "attempts": 1,
                    "fetched_at": now_iso(),
                    "via": "git",
                    "commit": commit,
                }
            )

            copied += 1
            print(f"downloaded {relative}")

    print(f"\nFiles registered: {copied}")
    print(f"Git commit: {commit}")


def command_sitemap(args):
    """Add matching sitemap URLs to data/sources.csv."""
    response = httpx.get(args.url, timeout=30, follow_redirects=True)
    response.raise_for_status()

    root = ET.fromstring(response.content)
    urls = []

    for element in root.iter():
        if element.tag.split("}")[-1] == "loc" and element.text:
            url = element.text.strip()
            path = urlsplit(url).path

            if args.include and not any(item in path for item in args.include):
                continue
            if any(item in path for item in args.exclude):
                continue

            urls.append(url)

            if len(urls) >= args.limit:
                break

    SOURCES_FILE.parent.mkdir(parents=True, exist_ok=True)
    exists = SOURCES_FILE.exists()

    with SOURCES_FILE.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)

        if not exists or SOURCES_FILE.stat().st_size == 0:
            writer.writerow(["url", "source", "licence", "title"])

        existing_urls = set()
        if exists:
            with SOURCES_FILE.open(encoding="utf-8-sig", newline="") as old:
                lines = (line for line in old if line.strip() and not line.lstrip().startswith("#"))
                existing_urls = {(row.get("url") or "").strip() for row in csv.DictReader(lines)}

        added = 0
        for url in urls:
            if url not in existing_urls:
                writer.writerow([url, args.source, args.licence, ""])
                added += 1

    print(f"Matching sitemap URLs: {len(urls)}")
    print(f"New URLs added: {added}")
    print(f"Saved to: {SOURCES_FILE}")


def command_manual(args):
    """Register a manually downloaded file in the manifest."""
    file = Path(args.file)
    if not file.is_absolute():
        file = ROOT / file

    if not file.is_file():
        raise FileNotFoundError(f"File not found: {file}")

    try:
        relative = file.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError("Manual file must be inside the project folder.") from exc

    digest = hashlib.sha256(file.read_bytes()).hexdigest()
    manifest = Manifest(MANIFEST_FILE)

    manifest.add(
        {
            "url": args.from_url,
            "source": args.source,
            "licence": args.licence,
            "title": file.name,
            "path": relative.as_posix(),
            "bytes": file.stat().st_size,
            "sha256": digest,
            "content_type": "",
            "http_status": None,
            "status": "downloaded",
            "attempts": 1,
            "fetched_at": now_iso(),
            "via": "manual",
        }
    )

    print(f"Registered: {relative}")
    print(f"SHA-256: {digest}")


def build_parser():
    parser = argparse.ArgumentParser(description="ChargeCheck source fetching tools")
    commands = parser.add_subparsers(dest="command", required=True)

    urls = commands.add_parser("urls", help="Fetch URLs from data/sources.csv")
    urls.add_argument("--delay", type=float, default=0.5)
    urls.add_argument("--max-concurrency", type=int, default=4)
    urls.set_defaults(func=command_urls)

    repo = commands.add_parser("repo", help="Fetch selected files from a Git repo")
    repo.add_argument("repository", help="GitHub repository, OWNER/REPO")
    repo.add_argument("--path", required=True)
    repo.add_argument("--ext", nargs="+", default=[".md"])
    repo.add_argument("--source", required=True)
    repo.add_argument("--licence", required=True)
    repo.add_argument("--ref", default="HEAD")
    repo.set_defaults(func=command_repo)

    sitemap = commands.add_parser("sitemap", help="Add sitemap URLs to sources.csv")
    sitemap.add_argument("url")
    sitemap.add_argument("--include", action="append", default=[])
    sitemap.add_argument("--exclude", action="append", default=[])
    sitemap.add_argument("--limit", type=int, default=300)
    sitemap.add_argument("--source", required=True)
    sitemap.add_argument("--licence", required=True)
    sitemap.set_defaults(func=command_sitemap)

    manual = commands.add_parser("manual", help="Register a manually downloaded file")
    manual.add_argument("file")
    manual.add_argument("--from-url", required=True)
    manual.add_argument("--source", required=True)
    manual.add_argument("--licence", required=True)
    manual.set_defaults(func=command_manual)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

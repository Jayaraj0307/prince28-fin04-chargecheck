
"""Compare versioned classification prompts against a labelled test set."""

import argparse
import asyncio
import hashlib
import json
import time
from pathlib import Path

from chargecheck.config import get_settings
from chargecheck.llm.classify import accuracy, classify, find_leaks
from chargecheck.llm.gateway import LLMUnavailable, build_gateway
from chargecheck.llm.prompts import read_prompt, versions

ROOT = Path(__file__).resolve().parents[1]
TESTSET = ROOT / "eval" / "prompt_testset.jsonl"
CACHE = ROOT / "eval" / "cache" / "classify.json"
NOTES = ROOT / "NOTES.md"


def load_rows():
    rows = []
    for line in TESTSET.read_text(encoding="utf-8").splitlines():
        if not line.strip() or "TODO" in line:
            continue
        rows.append(json.loads(line))
    return rows


def cache_key(prompt, question):
    return hashlib.sha256(
        f"{prompt}\n{question}".encode("utf-8")
    ).hexdigest()


def update_notes(table):
    notes = NOTES.read_text(encoding="utf-8") if NOTES.exists() else ""
    start, end = "<!-- prompts:start -->", "<!-- prompts:end -->"
    section = f"{start}\n{table}\n{end}"

    if start in notes and end in notes:
        before = notes.split(start)[0]
        after = notes.split(end, 1)[1]
        notes = before + section + after
    else:
        notes += "\n\n" + section + "\n"

    NOTES.write_text(notes, encoding="utf-8")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rpm", type=int, default=12)
    args = parser.parse_args()

    rows = load_rows()
    prompt_dir = get_settings().prompts_dir
    names = versions(prompt_dir, "classify")

    CACHE.parent.mkdir(parents=True, exist_ok=True)
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}

    gateway = build_gateway(get_settings())
    table = [
        "| Prompt | Correct | Accuracy | Invalid | Leaks | Avg input tokens |",
        "|---|---:|---:|---:|---:|---:|",
    ]

    delay = 60 / max(args.rpm, 1)
    last_call = 0

    try:
        for name in names:
            prompt = read_prompt(prompt_dir, name)
            questions = [row["question"] for row in rows]
            leaks = find_leaks(prompt, questions)

            results = []
            invalid = 0
            total_tokens = 0

            for row in rows:
                question = row["question"]
                key = cache_key(prompt, question)

                if key in cache:
                    saved = cache[key]
                    got = saved["got"]
                    tokens = saved.get("tokens_in", 0)
                else:
                    wait = delay - (time.monotonic() - last_call)
                    if last_call and wait > 0:
                        await asyncio.sleep(wait)

                    result_label, result = await classify(
                        gateway, prompt, name, question
                    )
                    last_call = time.monotonic()
                    got = result_label
                    tokens = result.tokens_in

                    cache[key] = {
                        "got": got,
                        "tokens_in": tokens,
                    }
                    CACHE.write_text(
                        json.dumps(cache, indent=2), encoding="utf-8"
                    )

                results.append({"label": row["label"], "got": got})
                total_tokens += tokens
                invalid += got == "invalid"

            correct = sum(r["label"] == r["got"] for r in results)
            score = accuracy(results)
            avg_tokens = total_tokens / len(rows) if rows else 0

            table.append(
                f"| {name} | {correct}/{len(rows)} | "
                f"{score:.1%} | {invalid} | {len(leaks)} | "
                f"{avg_tokens:.1f} |"
            )

            print(
                f"{name}: {correct}/{len(rows)} correct, "
                f"accuracy={score:.1%}, invalid={invalid}, "
                f"leaks={len(leaks)}, avg input tokens={avg_tokens:.1f}"
            )

        update_notes("\n".join(table))
        print("\nComparison table updated in NOTES.md.")

    except LLMUnavailable as exc:
        print(f"LLM unavailable: {exc}")
    finally:
        pass


if __name__ == "__main__":
    asyncio.run(main())

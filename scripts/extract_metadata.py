"""Extract and store validated metadata for parsed ChargeCheck documents."""

import argparse
import asyncio

from chargecheck.config import get_settings
from chargecheck.db.session import make_engine, make_sessionmaker
from chargecheck.llm.extract import DocMeta, run
from chargecheck.llm.gateway import build_gateway


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract metadata from parsed ChargeCheck documents."
    )
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--rpm", type=float, default=12)
    parser.add_argument("--chars", type=int, default=6000)
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--schema", action="store_true")
    args = parser.parse_args()

    if args.limit < 0 or args.rpm <= 0 or args.chars <= 0:
        parser.error("--limit must be non-negative; --rpm and --chars must be positive")

    settings = get_settings()
    prompt_path = settings.prompts_dir / "extract_v1.md"
    prompt = prompt_path.read_text(encoding="utf-8")

    engine = make_engine(settings)
    sessionmaker = make_sessionmaker(engine)
    gateway = build_gateway(settings)

    try:
        counts = await run(
            sessionmaker,
            gateway,
            DocMeta,
            prompt,
            "extract_v1",
            limit=args.limit,
            rpm=args.rpm,
            chars=args.chars,
            retry_failed=args.retry_failed,
            native=args.schema,
        )

        print("\nExtraction summary")
        print(f"Pending: {counts['pending']}")
        print(f"Successful: {counts['ok']}")
        print(f"Failed: {counts['failed']}")
        print(f"Repaired: {counts['repaired']}")
        print(f"Input tokens: {counts['tokens_in']}")
        print(f"Output tokens: {counts['tokens_out']}")
        print(f"Total cost: ₹{counts['micro_inr'] / 1_000_000:.6f}")

    finally:
        for provider in gateway.providers:
            await provider.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

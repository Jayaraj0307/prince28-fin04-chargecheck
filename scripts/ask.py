"""Ask ChargeCheck a banking question using the configured LLM gateway."""

import argparse
import asyncio

from chargecheck.config import get_settings
from chargecheck.llm.gateway import LLMUnavailable, build_gateway


async def main() -> None:
    parser = argparse.ArgumentParser(description="Ask ChargeCheck a banking question.")
    parser.add_argument("question", help="Your banking question")
    args = parser.parse_args()

    settings = get_settings()
    prompt_path = settings.prompts_dir / "chat_system_v1.md"
    system_prompt = prompt_path.read_text(encoding="utf-8")

    gateway = build_gateway(settings)

    try:
        result = await gateway.generate(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": args.question},
            ],
            purpose="cli",
            prompt_version="chat_system_v1",
        )
        print("\nChargeCheck:")
        print(result.text)
        print(f"\nProvider: {result.provider}")
        print(f"Tokens: {result.tokens_in} in / {result.tokens_out} out")
        print(f"Cost: ₹{result.cost_inr:.6f}")
        print(f"Fallback used: {result.fallback_used}")

    except LLMUnavailable as exc:
        print(f"LLM unavailable: {exc}")

    finally:
        for provider in gateway.providers:
            await provider.close()


if __name__ == "__main__":
    asyncio.run(main())

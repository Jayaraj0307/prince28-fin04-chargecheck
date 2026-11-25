
"""Check connectivity to the configured Gemini and Groq APIs."""

import asyncio
import time

import httpx

from chargecheck.config import get_settings


async def ping(name: str, base_url: str, api_key: str, model: str) -> None:
    if not api_key:
        print(f"{name}: API key missing")
        return

    url = f"{base_url.rstrip('/')}/models"
    headers = {"Authorization": f"Bearer {api_key}"}

    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            elapsed = (time.perf_counter() - started) * 1000

        if response.is_success:
            models = response.json().get("data", [])
            available = [item.get("id") for item in models]
            configured_available = (
                model in available or f"models/{model}" in available
            )
            print(f"{name}: OK ({elapsed:.0f} ms)")
            print(f"Configured model available: {configured_available}")
        else:
            print(f"{name}: HTTP {response.status_code}")
            print(response.text[:300])

    except httpx.HTTPError as exc:
        print(f"{name}: connection error: {exc}")


async def main() -> None:
    settings = get_settings()

    await ping(
        "Gemini",
        settings.llm_primary_base_url,
        settings.gemini_api_key,
        settings.llm_primary_model,
    )
    await ping(
        "Groq",
        settings.llm_fallback_base_url,
        settings.groq_api_key,
        settings.llm_fallback_model,
    )


if __name__ == "__main__":
    asyncio.run(main())

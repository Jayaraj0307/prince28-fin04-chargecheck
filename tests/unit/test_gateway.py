
import pytest

from chargecheck.llm.gateway import (
    CircuitBreaker,
    FakeLLM,
    LLMError,
    LLMGateway,
)


@pytest.mark.asyncio
async def test_gateway_fallback():
    primary = FakeLLM(
        name="gemini",
        model="gemini-test",
        script=[
            LLMError("Gemini failed", retryable=False)
        ],
    )

    fallback = FakeLLM(
        name="groq",
        model="groq-test",
        script=["Fallback answer"],
    )

    gateway = LLMGateway(
        [primary, fallback],
        max_attempts=1,
    )

    result = await gateway.generate(
        [{"role": "user", "content": "Hello"}]
    )

    assert result.text == "Fallback answer"
    assert result.provider == "groq"
    assert result.fallback_used is True
    assert primary.calls == 1
    assert fallback.calls == 1


def test_circuit_breaker_opens():
    current_time = [0.0]

    breaker = CircuitBreaker(
        threshold=2,
        cooldown=10,
        clock=lambda: current_time[0],
    )

    assert breaker.state == "closed"

    breaker.failure()
    assert breaker.state == "closed"

    breaker.failure()
    assert breaker.state == "open"
    assert breaker.allow() is False

    current_time[0] = 11.0

    assert breaker.state == "half-open"
    assert breaker.allow() is True

    breaker.success()

    assert breaker.state == "closed"
    assert breaker.failures == 0

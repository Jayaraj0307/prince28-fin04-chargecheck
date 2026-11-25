"""Chat and LLM usage API endpoints."""

import json
from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

from chargecheck.api.deps import GatewayDep, UsageDep
from chargecheck.llm.gateway import LLMResult, LLMUnavailable

router = APIRouter(tags=["chat"])

PROMPT_VERSION = "chat_system_v1"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    stream: bool = True


def sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/chat", response_model=None)
async def chat(
    body: ChatRequest,
    request: Request,
    gateway: GatewayDep,
) -> dict | StreamingResponse:
    messages = [
        {"role": "system", "content": request.app.state.system_prompt},
        {"role": "user", "content": body.message},
    ]

    if not body.stream:
        try:
            result = await gateway.generate(
                messages,
                purpose="chat",
                prompt_version=PROMPT_VERSION,
            )
        except LLMUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        return {
            "answer": result.text,
            **{key: value for key, value in asdict(result).items() if key != "text"},
        }

    stream = gateway.stream(
        messages,
        purpose="chat",
        prompt_version=PROMPT_VERSION,
    )

    try:
        first = await anext(stream)
    except StopAsyncIteration:
        raise HTTPException(status_code=503, detail="LLM returned an empty response") from None
    except LLMUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    async def events():
        try:
            item = first
            while True:
                if isinstance(item, LLMResult):
                    yield sse_event("done", asdict(item))
                    return

                yield sse_event("delta", {"text": item})

                try:
                    item = await anext(stream)
                except StopAsyncIteration:
                    return

        except LLMUnavailable as exc:
            yield sse_event("error", {"message": str(exc)})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/usage")
async def usage(
    repo: UsageDep,
    days: Annotated[int, Query(ge=1, le=90)] = 30,
) -> dict:
    records = await repo.by_day(days)

    return {
        "days": days,
        "total_cost_inr": round(sum(row["cost_inr"] for row in records), 6),
        "calls": sum(row["calls"] for row in records),
        "daily": records,
    }

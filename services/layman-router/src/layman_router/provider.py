from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator

import httpx


FORWARDED_REQUEST_HEADERS = {
    "authorization",
    "openai-organization",
    "openai-project",
    "x-stainless-helper-method",
}
FORWARDED_RESPONSE_HEADERS = {"content-type", "openai-request-id", "x-request-id"}


@dataclass
class StreamHandle:
    client: httpx.AsyncClient
    response: httpx.Response
    iterator: AsyncIterator[bytes]
    first_chunk: bytes

    async def close(self) -> None:
        await self.response.aclose()
        await self.client.aclose()


class UpstreamProvider:
    def __init__(self, base_url: str, transport: httpx.AsyncBaseTransport | None = None, timeout_seconds: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.transport = transport
        self.timeout = httpx.Timeout(timeout_seconds, connect=min(15.0, timeout_seconds))

    @staticmethod
    def request_headers(incoming: httpx.Headers | dict[str, str]) -> dict[str, str]:
        headers = {key: value for key, value in incoming.items() if key.lower() in FORWARDED_REQUEST_HEADERS}
        headers["content-type"] = "application/json"
        return headers

    @staticmethod
    def response_headers(incoming: httpx.Headers) -> dict[str, str]:
        return {key: value for key, value in incoming.items() if key.lower() in FORWARDED_RESPONSE_HEADERS}

    async def post(self, payload: dict, headers: dict[str, str]) -> httpx.Response:
        async with httpx.AsyncClient(transport=self.transport, timeout=self.timeout) as client:
            return await client.post(f"{self.base_url}/responses", json=payload, headers=headers)

    async def stream(self, payload: dict, headers: dict[str, str]) -> StreamHandle:
        client = httpx.AsyncClient(transport=self.transport, timeout=self.timeout)
        request = client.build_request("POST", f"{self.base_url}/responses", json=payload, headers=headers)
        try:
            response = await client.send(request, stream=True)
            iterator = response.aiter_raw()
            chunks: list[bytes] = []
            size = 0
            async for chunk in iterator:
                chunks.append(chunk)
                size += len(chunk)
                joined = b"".join(chunks)
                if not response.is_success or b"\n\n" in joined or b"\r\n\r\n" in joined or size >= 65_536:
                    break
            first_chunk = b"".join(chunks)
        except BaseException:
            await client.aclose()
            raise
        return StreamHandle(client=client, response=response, iterator=iterator, first_chunk=first_chunk)

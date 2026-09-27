"""Thin httpx client for an OpenAI-compatible gateway (no SDK, no LangChain)."""
from __future__ import annotations

import logging
from typing import Any

import httpx

from core.config import settings

logger = logging.getLogger(__name__)

# Model families that reject a custom `temperature` and expect `max_completion_tokens`.
_REASONING_PREFIXES = ("gpt-5", "o1", "o3", "o4")


class LLMError(Exception):
    """Raised when the chat completion endpoint fails or returns an unusable payload."""


def _is_reasoning_model(model: str) -> bool:
    name = model.lower().split("/")[-1]
    return name.startswith(_REASONING_PREFIXES)


def is_zero_vector(vec: list[float] | None) -> bool:
    return vec is None or len(vec) == 0 or not any(vec)


class LLMService:
    """Thin wrapper around the OpenAI-compatible gateway using httpx."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        embedding_model: str | None = None,
        timeout: float | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = (base_url or settings.OPENAI_BASE_URL).rstrip("/")
        self.api_key = api_key if api_key is not None else settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_MODEL
        self.embedding_model = embedding_model or settings.EMBEDDING_MODEL
        self.embedding_dim = settings.EMBEDDING_DIM
        self.timeout = timeout or settings.LLM_TIMEOUT_SECONDS
        self._transport = transport
        self._embeddings_unavailable = False

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=self.timeout, transport=self._transport)

    def _chat_payload(
        self, messages: list[dict[str, Any]], model: str, max_tokens: int, temperature: float
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"model": model, "messages": messages}
        if _is_reasoning_model(model):
            # Reasoning models spend part of the budget on hidden reasoning tokens.
            payload["max_completion_tokens"] = max_tokens + 4000
        else:
            payload["max_tokens"] = max_tokens
            payload["temperature"] = temperature
        return payload

    async def complete(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        max_tokens: int = 2000,
        temperature: float = 0.1,
    ) -> str:
        """Call /chat/completions at OPENAI_BASE_URL and return the assistant text."""
        use_model = model or self.model
        payload = self._chat_payload(messages, use_model, max_tokens, temperature)
        url = f"{self.base_url}/chat/completions"
        async with self._client() as client:
            try:
                resp = await client.post(url, json=payload, headers=self._headers())
                if resp.status_code == 400 and "temperature" in payload and "temperature" in resp.text:
                    # Some gateways/models reject non-default temperature: retry without it.
                    payload.pop("temperature", None)
                    resp = await client.post(url, json=payload, headers=self._headers())
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                body = exc.response.text[:500]
                logger.error("LLM completion failed: HTTP %s %s", exc.response.status_code, body)
                raise LLMError(f"LLM gateway returned HTTP {exc.response.status_code}") from exc
            except httpx.HTTPError as exc:
                logger.error("LLM completion transport error: %s", exc)
                raise LLMError(f"LLM gateway unreachable: {exc.__class__.__name__}") from exc

        try:
            data = resp.json()
            content = data["choices"][0]["message"].get("content") or ""
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise LLMError("Unexpected completion payload") from exc
        if not content.strip():
            raise LLMError("Empty completion from model")
        return content

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Call /embeddings at OPENAI_BASE_URL.

        If the embedding endpoint is unavailable, return zero vectors with a warning log
        so ingestion and retrieval keep working (retrieval then falls back to keyword search).
        """
        if not texts:
            return []
        zeros = [[0.0] * self.embedding_dim for _ in texts]
        if self._embeddings_unavailable:
            return zeros

        url = f"{self.base_url}/embeddings"
        vectors: list[list[float]] = []
        batch_size = 64
        async with self._client() as client:
            for start in range(0, len(texts), batch_size):
                batch = [t[:8000] if t else " " for t in texts[start : start + batch_size]]
                try:
                    resp = await client.post(
                        url,
                        json={"model": self.embedding_model, "input": batch},
                        headers=self._headers(),
                    )
                    resp.raise_for_status()
                    data = resp.json()["data"]
                    ordered = sorted(data, key=lambda d: d.get("index", 0))
                    batch_vectors = [list(map(float, d["embedding"])) for d in ordered]
                except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
                    logger.warning(
                        "Embedding endpoint unavailable (%s); returning zero vectors. "
                        "Semantic search will fall back to keyword search.",
                        exc.__class__.__name__,
                    )
                    self._embeddings_unavailable = True
                    return zeros
                if any(len(v) != self.embedding_dim for v in batch_vectors):
                    logger.warning(
                        "Embedding dimension mismatch (expected %s); returning zero vectors.", self.embedding_dim
                    )
                    self._embeddings_unavailable = True
                    return zeros
                vectors.extend(batch_vectors)
        return vectors


_default_llm: LLMService | None = None


def get_llm_service() -> LLMService:
    global _default_llm
    if _default_llm is None:
        _default_llm = LLMService()
    return _default_llm

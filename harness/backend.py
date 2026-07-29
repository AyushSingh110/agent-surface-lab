"""Chat backend abstraction — the model is dependency-injected, hence swappable.

The runner and replay layer depend only on the `ChatBackend` protocol, never on
the Ollama client directly. That keeps the backbone swappable and, crucially,
lets tests drive the agent
loop with a scripted `FakeBackend` so the harness is testable without a live
model.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from harness.trace import Message


@dataclass
class ChatResponse:
    """A normalized backend response.

    Attributes:
        content: The assistant's text output (possibly empty).
        tool_name: Name of a requested tool call, or None.
        tool_args: Arguments for the tool call, or None.
        token_count: Prompt+completion tokens if the backend reports them, else 0.
    """

    content: str
    tool_name: str | None
    tool_args: dict[str, Any] | None
    token_count: int = 0


@runtime_checkable
class ChatBackend(Protocol):
    """Anything that can turn (messages, tools, options) into a ChatResponse."""

    @property
    def model_tag(self) -> str:
        """The model identifier logged on every trace/replay."""
        ...

    def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]],
        options: dict[str, Any],
    ) -> ChatResponse:
        """Run one chat turn and return a normalized response."""
        ...


class OllamaBackend:
    """ChatBackend backed by a local Ollama server.

    We import the `ollama` client lazily so that importing the harness (e.g. in a
    unit test that only uses FakeBackend) does not require the server to exist.
    """

    def __init__(self, model_tag: str, host: str = "http://localhost:11434") -> None:
        self._model_tag = model_tag
        self._host = host
        self._client: Any = None  # lazily constructed

    @property
    def model_tag(self) -> str:
        return self._model_tag

    def _get_client(self) -> Any:
        if self._client is None:
            import ollama  # local import: only needed for real runs

            self._client = ollama.Client(host=self._host)
        return self._client

    def _chat_with_retry(self, messages: list[Message], tools: list[dict[str, Any]],
                         options: dict[str, Any], attempts: int = 5, backoff: float = 3.0) -> Any:
        """Call the Ollama server, retrying transient network failures.

        A long local run on a memory-constrained GPU can drop the connection
        mid-request (httpx.RemoteProtocolError / connect errors) when the server
        restarts under load. Those are transient, so we back off and recreate the
        client; a genuinely bad request (any non-network error) is re-raised at once.
        """
        import time

        import httpx

        transient = (httpx.RemoteProtocolError, httpx.ConnectError, httpx.ReadError,
                     httpx.ReadTimeout, httpx.ConnectTimeout, httpx.PoolTimeout, ConnectionError)
        last: Exception | None = None
        for i in range(attempts):
            try:
                return self._get_client().chat(
                    model=self._model_tag, messages=messages, tools=tools, options=options)
            except transient as exc:
                last = exc
                self._client = None  # force a fresh client next attempt
                if i < attempts - 1:
                    time.sleep(backoff * (i + 1))  # linear backoff: 3s, 6s, 9s, 12s
        raise RuntimeError(f"Ollama chat failed after {attempts} attempts: {last}") from last

    def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]],
        options: dict[str, Any],
    ) -> ChatResponse:
        resp = self._chat_with_retry(messages, tools, options)
        msg = resp["message"]
        calls = msg.get("tool_calls") or []
        tool_name: str | None = None
        tool_args: dict[str, Any] | None = None
        if calls:
            # We execute one tool call per step to keep the trace's step semantics
            # unambiguous (one step = at most one tool action).
            fn = calls[0]["function"]
            tool_name = fn["name"]
            raw_args = fn.get("arguments", {})
            tool_args = raw_args if isinstance(raw_args, dict) else _parse_args(raw_args)
        return ChatResponse(
            content=msg.get("content", ""),
            tool_name=tool_name,
            tool_args=tool_args,
            token_count=int(resp.get("eval_count", 0) or 0) + int(resp.get("prompt_eval_count", 0) or 0),
        )


def _parse_args(raw: Any) -> dict[str, Any]:
    """Parse tool arguments that a backend may hand back as a JSON string.

    Fails loudly on unparseable arguments rather than silently substituting {}
    — a swallowed parse error here would corrupt a trace.
    """
    import json

    if isinstance(raw, dict):
        return raw
    return json.loads(raw)


class FakeBackend:
    """A scripted ChatBackend for tests: returns queued responses in order.

    It records the messages it was called with so tests can assert on the exact
    context the "model" saw — which is how we validate reconstruction.
    """

    def __init__(self, script: list[ChatResponse], model_tag: str = "fake-model") -> None:
        if not script:
            raise ValueError("FakeBackend requires a non-empty script")
        self._script = list(script)
        self._i = 0
        self._model_tag = model_tag
        self.seen_contexts: list[list[Message]] = []

    @property
    def model_tag(self) -> str:
        return self._model_tag

    def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]],
        options: dict[str, Any],
    ) -> ChatResponse:
        # Deep-copy so later mutation of the running context can't retroactively
        # change what we recorded the model as having seen.
        import copy

        self.seen_contexts.append(copy.deepcopy(messages))
        if self._i >= len(self._script):
            raise AssertionError("FakeBackend script exhausted — test asked for more turns than scripted")
        resp = self._script[self._i]
        self._i += 1
        return resp

"""Official DeepSeek API transport with streaming tool-call assembly."""
from __future__ import annotations

import json
import threading
from collections.abc import Callable
from dataclasses import dataclass

import httpx

BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-v4-pro"


class Cancelled(Exception):
    pass


class APIError(Exception):
    pass


@dataclass
class Reply:
    message: dict
    usage: dict
    finish_reason: str


class DeepSeekClient:
    def __init__(self, api_key: str, cancel: threading.Event | None = None, transport=None):
        if not api_key.strip():
            raise ValueError("Enter your DeepSeek API key.")
        self.api_key = api_key.strip()
        self.cancel = cancel or threading.Event()
        try:
            self.http = httpx.Client(base_url=BASE_URL, headers={"Authorization": f"Bearer {self.api_key}"},
                                     timeout=httpx.Timeout(60, connect=15), follow_redirects=False,
                                     trust_env=False, transport=transport)
        except FileNotFoundError as exc:
            raise APIError("The application's HTTPS certificate resources are missing. "
                           "Use the latest complete application build. No API request was sent.") from exc

    def close(self):
        self.http.close()

    @staticmethod
    def status_error(status: int) -> APIError:
        explanations = {400: "DeepSeek rejected the request format or context size.",
                        401: "The API key was rejected. Check your key in DeepSeek Platform.",
                        402: "Your DeepSeek account has insufficient balance.",
                        403: "Your account does not have access to this resource.",
                        404: "The official API endpoint or required model is unavailable.",
                        429: "DeepSeek is rate limiting requests. Try again shortly.",
                        500: "DeepSeek reported a server error.",
                        503: "DeepSeek is temporarily overloaded."}
        return APIError(explanations.get(status, f"DeepSeek returned HTTP {status}.") + f" (HTTP {status})")

    def verify(self) -> str:
        try:
            response = self.http.get("/models")
            if response.status_code != 200:
                raise self.status_error(response.status_code)
            models = {item["id"] for item in response.json().get("data", [])}
            if MODEL not in models:
                raise APIError(f"Key accepted, but {MODEL} was not listed for this account. No substitute model will be used.")
            return f"Connected · {MODEL} is available"
        except httpx.HTTPError as exc:
            raise APIError("Could not connect to the official DeepSeek API. Check your connection.") from exc

    def complete(self, messages: list[dict], tools: list[dict], on_text: Callable[[str], None] = lambda _: None,
                 on_retry: Callable[[str], None] = lambda _: None, max_tokens: int = 32768) -> Reply:
        payload = {"model": MODEL, "messages": messages, "tools": tools,
                   "thinking": {"type": "enabled"}, "reasoning_effort": "high",
                   "max_tokens": max_tokens, "stream": True, "stream_options": {"include_usage": True}}
        for attempt in range(3):
            if self.cancel.is_set():
                raise Cancelled()
            try:
                with self.http.stream("POST", "/chat/completions", json=payload) as response:
                    if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                        delay = min(20, max(1, float(response.headers.get("retry-after", 2 ** (attempt + 1)))))
                        on_retry(f"HTTP {response.status_code}; retrying in {delay:g}s ({attempt+1}/2).")
                        if self.cancel.wait(delay):
                            raise Cancelled()
                        continue
                    if response.status_code != 200:
                        raise self.status_error(response.status_code)
                    return self._assemble(response.iter_lines(), on_text)
            except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
                if self.cancel.is_set():
                    raise Cancelled() from exc
                # A dropped stream may have been billed; do not silently replay it.
                raise APIError("The API connection timed out or was interrupted. Partial project files are preserved; start a new run to retry.") from exc
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                raise APIError("DeepSeek returned an unexpected or malformed response.") from exc
        raise APIError("The API retry limit was reached.")

    def _assemble(self, lines, on_text) -> Reply:
        content, reasoning, calls, usage, finish, done = [], [], {}, {}, None, False
        received = 0
        for line in lines:
            if self.cancel.is_set():
                raise Cancelled()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                done = True
                break
            if not data:
                continue
            received += len(data)
            if received > 8_000_000:
                raise APIError("API response exceeded the 8 MB safety limit.")
            chunk = json.loads(data)
            if "error" in chunk:
                raise APIError("DeepSeek reported an error inside the response stream.")
            if chunk.get("usage"):
                usage = chunk["usage"]
            for choice in chunk.get("choices", []):
                delta = choice.get("delta", {})
                if delta.get("content"):
                    content.append(delta["content"])
                    on_text(delta["content"])
                if delta.get("reasoning_content"):
                    reasoning.append(delta["reasoning_content"])
                for call in delta.get("tool_calls", []):
                    index = call["index"]
                    if not isinstance(index, int) or index < 0 or index > 100:
                        raise APIError("Invalid tool call index.")
                    target = calls.setdefault(index, {"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
                    if call.get("id"):
                        target["id"] += call["id"]
                    for key in ("name", "arguments"):
                        target["function"][key] += call.get("function", {}).get(key) or ""
                finish = choice.get("finish_reason") or finish
        if not done or finish is None:
            raise APIError("DeepSeek's stream ended early. No partial tool calls were executed.")
        if finish == "length":
            raise APIError("The response hit its per-request token limit. No partial tool calls were executed; the agent can retry with a smaller file batch.")
        if finish not in {"stop", "tool_calls"}:
            raise APIError(f"DeepSeek stopped unexpectedly ({finish}).")
        tool_calls = [calls[k] for k in sorted(calls)]
        if any(not c["id"] or not c["function"]["name"] for c in tool_calls):
            raise APIError("DeepSeek returned an incomplete tool call.")
        if len({c["id"] for c in tool_calls}) != len(tool_calls):
            raise APIError("DeepSeek returned duplicate tool-call IDs.")
        message = {"role": "assistant", "content": "".join(content), "reasoning_content": "".join(reasoning)}
        if tool_calls:
            message["tool_calls"] = tool_calls
        return Reply(message, usage, finish)

import json
import threading

import httpx
import pytest

from codeagent.client import DeepSeekClient, APIError, Cancelled, MODEL


def test_real_https_transport_initializes_without_network():
    client = DeepSeekClient("offline-construction-no-request")
    client.close()


def test_missing_certificate_resource_has_actionable_error(monkeypatch):
    def missing(*args, **kwargs):
        raise FileNotFoundError(2, "No such file or directory")
    monkeypatch.setattr(httpx, "Client", missing)
    with pytest.raises(APIError, match="No API request was sent"):
        DeepSeekClient("never-log-this-key")


def sse(chunks, done=True):
    return "\n\n".join("data: " + json.dumps(c) for c in chunks) + ("\n\ndata: [DONE]\n\n" if done else "")


def chunk(delta, finish=None, usage=None):
    return {"choices": [{"delta": delta, "finish_reason": finish}], "usage": usage}


def test_stream_assembles_fragmented_tools_and_preserves_reasoning():
    requests = []
    body = sse([
        chunk({"reasoning_content": "reasoning fragment"}),
        chunk({"content": "Writing files."}),
        chunk({"tool_calls": [{"index": 0, "id": "call_1", "function": {"name": "write_file", "arguments": '{"path":"x.py",'}}]}),
        chunk({"tool_calls": [{"index": 0, "function": {"arguments": '"content":"x = 1"}'}}]}, "tool_calls", {"prompt_tokens": 10, "completion_tokens": 20}),
    ])
    def handle(request):
        requests.append(request)
        return httpx.Response(200, text=body, headers={"content-type": "text/event-stream"})
    client = DeepSeekClient("secret-test-value", transport=httpx.MockTransport(handle))
    visible = []
    reply = client.complete([{"role": "user", "content": "go"}], [], on_text=visible.append)
    assert reply.message["reasoning_content"] == "reasoning fragment"
    assert json.loads(reply.message["tool_calls"][0]["function"]["arguments"])["content"] == "x = 1"
    assert visible == ["Writing files."]
    assert reply.usage["completion_tokens"] == 20
    payload = json.loads(requests[0].content)
    assert payload["model"] == MODEL
    assert str(requests[0].url) == "https://api.deepseek.com/chat/completions"
    assert payload["thinking"] == {"type": "enabled"}
    client.close()


@pytest.mark.parametrize("status", [400, 401, 402, 403, 404])
def test_actionable_http_errors_do_not_disclose_body_or_key(status):
    client = DeepSeekClient("sensitive-key", transport=httpx.MockTransport(lambda _: httpx.Response(status, text="sensitive-key")))
    with pytest.raises(APIError) as error:
        client.complete([], [])
    assert str(status) in str(error.value)
    assert "sensitive-key" not in str(error.value)
    client.close()


@pytest.mark.parametrize("body", [sse([chunk({"content": "partial"})], done=False), sse([chunk({}, "length")]), "data: {invalid}\n\n"])
def test_incomplete_or_truncated_stream_never_executes_tools(body):
    client = DeepSeekClient("key", transport=httpx.MockTransport(lambda _: httpx.Response(200, text=body)))
    with pytest.raises(APIError):
        client.complete([], [])
    client.close()


def test_cancel_before_request():
    event = threading.Event()
    event.set()
    client = DeepSeekClient("key", event, transport=httpx.MockTransport(lambda _: pytest.fail("request should not be sent")))
    with pytest.raises(Cancelled):
        client.complete([], [])
    client.close()


def test_model_discovery_does_not_substitute_another_model():
    client = DeepSeekClient("key", transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"data": [{"id": "deepseek-flash"}]})))
    with pytest.raises(APIError, match="No substitute"):
        client.verify()
    client.close()

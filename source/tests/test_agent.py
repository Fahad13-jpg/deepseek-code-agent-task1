import json
import threading
from pathlib import Path

from codeagent.agent import Agent, RunConfig
from codeagent.client import Reply
from codeagent.selftest import FixtureClient
from codeagent.workspace import Workspace, new_project


def test_end_to_end_offline_fixture_with_real_python_tests(tmp_path):
    events = []
    agent = Agent(FixtureClient(), RunConfig(tmp_path, execute_tests=True), {"warnings": []}, events.append)
    result = agent.run()
    assert result["status"] == "completed"
    assert result["python_tests"]["passed"] is True
    assert "Ran 3 tests" in result["python_tests"]["output"]
    assert result["checks"]["passed"]
    root = Path(result["root"])
    assert len(result["files"]) == 4
    assert (root / ".agent" / "inputs.json").exists()
    assert (root / ".agent" / "report.json").exists()
    assert any(e["kind"] == "tool" for e in events)


def test_cancellation_is_not_reported_as_success(tmp_path):
    stop = threading.Event()
    stop.set()
    result = Agent(FixtureClient(), RunConfig(tmp_path), {}, cancel=stop).run()
    assert result["status"] == "cancelled"
    assert Path(result["root"]).is_dir()


class EmptyClient:
    api_key = "private-test-key"

    def complete(self, *args, **kwargs):
        return Reply({"role": "assistant", "content": "Done.", "reasoning_content": "private reasoning"}, {"prompt_tokens": 1}, "stop")


def test_false_completion_is_rejected_and_reasoning_not_saved(tmp_path):
    agent = Agent(EmptyClient(), RunConfig(tmp_path), {})
    report = agent.run()
    assert report["status"] == "incomplete"
    assert report["turns"] == 4
    conversation = (Path(report["root"]) / ".agent" / "conversation.json").read_text()
    assert "reasoning_content" not in conversation
    assert "private reasoning" not in conversation
    assert agent.messages[2]["reasoning_content"] == "private reasoning"


def test_tools_are_validated_and_key_redacted(tmp_path):
    agent = Agent(EmptyClient(), RunConfig(tmp_path), {})
    agent.workspace = Workspace(new_project(tmp_path, "tools"))
    assert agent.dispatch("write_file", '{"path":"../private-test-key","content":"x"}')["ok"] is False
    assert agent.dispatch("write_file", '{"path":42,"content":"x"}')["ok"] is False
    assert agent.dispatch("unknown", '{}')["ok"] is False
    assert agent.dispatch("list_files", '{"extra":"x"}')["ok"] is False
    assert agent.dispatch("list_files", '[]')["ok"] is False
    assert agent.dispatch("write_file", '{bad json')["ok"] is False


def test_budget_stops_before_another_request(tmp_path):
    result = Agent(EmptyClient(), RunConfig(tmp_path, token_budget=1), {}).run()
    assert result["status"] == "incomplete"
    assert "budget" in result["summary"].lower()


def test_default_never_executes_generated_tests(tmp_path):
    result = Agent(FixtureClient(), RunConfig(tmp_path, execute_tests=False), {}).run()
    assert result["status"] == "completed"
    assert result["python_tests"]["status"] == "disabled"


def test_actual_transport_replays_reasoning_and_matching_tool_results(tmp_path):
    import httpx
    from codeagent.client import DeepSeekClient
    from codeagent.selftest import FIXTURE
    requests = []

    def respond(request):
        payload = json.loads(request.content)
        requests.append(payload)
        if len(requests) == 1:
            calls = [{"index": i, "id": f"call-{i}", "type": "function", "function": {
                "name": "write_file", "arguments": json.dumps({"path": path, "content": text})}}
                for i, (path, text) in enumerate(FIXTURE.items())]
            delta = {"reasoning_content": "preserve-this-in-memory", "content": "Building.", "tool_calls": calls}
            finish = "tool_calls"
        else:
            assistant = next(m for m in payload["messages"] if m["role"] == "assistant")
            assert assistant["reasoning_content"] == "preserve-this-in-memory"
            observations = [m for m in payload["messages"] if m["role"] == "tool"]
            assert [m["tool_call_id"] for m in observations] == [f"call-{i}" for i in range(4)]
            assert all(json.loads(m["content"])["ok"] for m in observations)
            delta, finish = {"content": "Project files created.", "reasoning_content": "finished"}, "stop"
        chunk = {"choices": [{"delta": delta, "finish_reason": finish}], "usage": {"prompt_tokens": 10, "completion_tokens": 20}}
        return httpx.Response(200, text="data: " + json.dumps(chunk) + "\n\ndata: [DONE]\n\n")

    client = DeepSeekClient("not-a-real-key", transport=httpx.MockTransport(respond))
    try:
        report = Agent(client, RunConfig(tmp_path), {}).run()
    finally:
        client.close()
    assert report["status"] == "completed"
    assert len(requests) == 2
    assert report["usage"] == {"prompt_tokens": 20, "completion_tokens": 40}

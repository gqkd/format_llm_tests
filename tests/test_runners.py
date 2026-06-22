from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from runners.anthropic_runner import AnthropicRunner
from runners.base import RunParams
from runners.ollama_runner import OllamaRunner
from runners.openai_runner import OpenAIRunner


class TransientError(Exception):
    pass


class UnsupportedParameterError(Exception):
    pass


def test_openai_runner_parses_response_and_writes_jsonl(tmp_path: Path) -> None:
    client = FakeOpenAIClient(
        responses=[
            FakeOpenAIResponse(
                text="answer",
                input_tokens=11,
                output_tokens=3,
            )
        ]
    )
    runner = OpenAIRunner(client=client, raw_log_dir=tmp_path, clock=lambda: 100.0)

    result = runner.run(
        prompt="prompt text",
        params=RunParams(
            model="gpt-5.5",
            task_id="task-1",
            input_format="markdown",
            output_format="free_form",
            temperature=0.2,
            seed=42,
        ),
    )

    assert result.response_text == "answer"
    assert result.input_tokens == 11
    assert result.output_tokens == 3
    assert result.error is None
    assert result.params_used["model"] == "gpt-5.5"
    assert client.calls[0]["input"] == "prompt text"

    raw_event = read_only_jsonl_event(tmp_path)
    assert raw_event["model"] == "gpt-5.5"
    assert raw_event["task_id"] == "task-1"
    assert raw_event["input_format"] == "markdown"
    assert raw_event["result"]["response_text"] == "answer"


def test_logging_failure_is_recorded_in_result_instead_of_raising(tmp_path: Path) -> None:
    raw_log_file = tmp_path / "not-a-directory"
    raw_log_file.write_text("already a file", encoding="utf-8")
    client = FakeOpenAIClient([FakeOpenAIResponse(text="answer", input_tokens=1, output_tokens=1)])
    runner = OpenAIRunner(client=client, raw_log_dir=raw_log_file, clock=lambda: 1.0)

    result = runner.run(prompt="prompt", params=RunParams(model="gpt-5.5"))

    assert result.response_text == "answer"
    assert result.error is not None
    assert result.error["type"] == "FileExistsError"
    assert "raw logging failed" in result.error["message"]


def test_run_params_reject_metadata_that_overrides_reserved_runner_params() -> None:
    try:
        RunParams(model="gpt-5.5", metadata={"model": "other"})
    except ValueError as exc:
        assert "reserved" in str(exc)
    else:
        raise AssertionError("reserved metadata key was accepted")


def test_openai_runner_drops_unsupported_parameters_and_retries(tmp_path: Path) -> None:
    client = FakeOpenAIClient(
        responses=[
            UnsupportedParameterError("temperature is not supported"),
            FakeOpenAIResponse(text="answer", input_tokens=5, output_tokens=2),
        ]
    )
    sleeps: list[float] = []
    runner = OpenAIRunner(
        client=client,
        raw_log_dir=tmp_path,
        clock=lambda: 10.0,
        sleep_func=sleeps.append,
        max_retries=2,
    )

    result = runner.run(
        prompt="prompt",
        params=RunParams(model="gpt-5.5", temperature=0.7, seed=9),
    )

    assert result.error is None
    assert result.response_text == "answer"
    assert len(client.calls) == 2
    assert "temperature" in client.calls[0]
    assert "temperature" not in client.calls[1]
    assert result.params_used["dropped_params"] == ["temperature"]
    assert read_only_jsonl_event(tmp_path)["result"]["params_used"]["dropped_params"] == ["temperature"]
    assert sleeps == []


def test_openai_runner_retries_transient_errors_and_records_nonrecoverable_result(tmp_path: Path) -> None:
    client = FakeOpenAIClient(
        responses=[
            TransientError("rate limit"),
            ValueError("bad request"),
        ]
    )
    sleeps: list[float] = []
    runner = OpenAIRunner(
        client=client,
        raw_log_dir=tmp_path,
        clock=lambda: 20.0,
        sleep_func=sleeps.append,
        transient_errors=(TransientError,),
        max_retries=2,
        backoff_base_seconds=0.5,
    )

    result = runner.run(prompt="prompt", params=RunParams(model="gpt-5.4"))

    assert result.response_text == ""
    assert result.error is not None
    assert result.error["type"] == "ValueError"
    assert sleeps == [0.5]
    assert len(client.calls) == 2
    assert read_only_jsonl_event(tmp_path)["result"]["error"]["type"] == "ValueError"


def test_runner_records_dropped_parameters_when_later_attempt_fails(tmp_path: Path) -> None:
    client = FakeOpenAIClient(
        responses=[
            UnsupportedParameterError("temperature is not supported"),
            ValueError("bad request"),
        ]
    )
    runner = OpenAIRunner(client=client, raw_log_dir=tmp_path, clock=lambda: 20.0)

    result = runner.run(
        prompt="prompt",
        params=RunParams(model="gpt-5.5", temperature=0.7),
    )

    assert result.error is not None
    assert result.error["type"] == "ValueError"
    assert "temperature" not in result.params_used
    assert result.params_used["dropped_params"] == ["temperature"]


def test_openai_runner_includes_native_structured_output_schema(tmp_path: Path) -> None:
    schema = {
        "type": "object",
        "properties": {"answer": {"type": "string"}},
        "required": ["answer"],
        "additionalProperties": False,
    }
    client = FakeOpenAIClient([FakeOpenAIResponse(text='{"answer":"x"}', input_tokens=8, output_tokens=4)])
    runner = OpenAIRunner(client=client, raw_log_dir=tmp_path, clock=lambda: 1.0)

    result = runner.run(
        prompt="prompt",
        params=RunParams(model="gpt-5.5", native_output={"format": "json", "schema": schema}),
    )

    assert result.error is None
    assert client.calls[0]["text"]["format"]["schema"] == schema
    assert client.calls[0]["text"]["format"]["strict"] is True


def test_openai_runner_passes_reasoning_effort(tmp_path: Path) -> None:
    client = FakeOpenAIClient([FakeOpenAIResponse(text="answer", input_tokens=8, output_tokens=4)])
    runner = OpenAIRunner(client=client, raw_log_dir=tmp_path, clock=lambda: 1.0)

    result = runner.run(prompt="prompt", params=RunParams(model="gpt-5.5", reasoning_effort="high"))

    assert result.error is None
    assert client.calls[0]["reasoning_effort"] == "high"
    assert result.params_used["reasoning_effort"] == "high"


def test_openai_runner_records_refusal_as_error(tmp_path: Path) -> None:
    client = FakeOpenAIClient(
        [
            {
                "status": "completed",
                "output": [
                    {
                        "content": [
                            {"type": "refusal", "refusal": "I cannot comply."},
                        ]
                    }
                ],
                "usage": {"input_tokens": 4, "output_tokens": 2},
            }
        ]
    )
    runner = OpenAIRunner(client=client, raw_log_dir=tmp_path, clock=lambda: 1.0)

    result = runner.run(prompt="prompt", params=RunParams(model="gpt-5.5"))

    assert result.response_text == ""
    assert result.error is not None
    assert result.error["type"] == "ValueError"
    assert "refusal" in result.error["message"].lower()


def test_openai_runner_records_incomplete_response_as_error(tmp_path: Path) -> None:
    client = FakeOpenAIClient(
        [
            {
                "status": "incomplete",
                "incomplete_details": {"reason": "max_output_tokens"},
                "usage": {"input_tokens": 4, "output_tokens": 2},
            }
        ]
    )
    runner = OpenAIRunner(client=client, raw_log_dir=tmp_path, clock=lambda: 1.0)

    result = runner.run(prompt="prompt", params=RunParams(model="gpt-5.5"))

    assert result.error is not None
    assert result.error["type"] == "ValueError"
    assert "incomplete" in result.error["message"].lower()


def test_openai_runner_parses_dict_response_output_shape(tmp_path: Path) -> None:
    client = FakeOpenAIClient(
        [
            {
                "status": "completed",
                "output": [
                    {
                        "content": [
                            {"type": "output_text", "text": "answer"},
                        ]
                    }
                ],
                "usage": {"input_tokens": 6, "output_tokens": 2},
            }
        ]
    )
    runner = OpenAIRunner(client=client, raw_log_dir=tmp_path, clock=lambda: 1.0)

    result = runner.run(prompt="prompt", params=RunParams(model="gpt-5.5"))

    assert result.error is None
    assert result.response_text == "answer"
    assert result.input_tokens == 6
    assert result.output_tokens == 2


def test_anthropic_runner_parses_response_counts_tokens_and_writes_jsonl(tmp_path: Path) -> None:
    client = FakeAnthropicClient(
        responses=[FakeAnthropicResponse(text="answer", input_tokens=13, output_tokens=4)],
        count_tokens=17,
    )
    runner = AnthropicRunner(client=client, raw_log_dir=tmp_path, clock=lambda: 200.0)

    result = runner.run(
        prompt="prompt text",
        params=RunParams(model="claude-opus-4-8", task_id="task-a", input_format="xml"),
    )

    assert result.response_text == "answer"
    assert result.input_tokens == 17
    assert result.output_tokens == 4
    assert result.error is None
    assert client.count_token_calls[0]["messages"][0]["content"] == "prompt text"
    assert read_only_jsonl_event(tmp_path)["result"]["input_tokens"] == 17


def test_anthropic_runner_includes_strict_tool_for_native_structured_output(tmp_path: Path) -> None:
    schema = {
        "type": "object",
        "properties": {"answer": {"type": "string"}},
        "required": ["answer"],
        "additionalProperties": False,
    }
    client = FakeAnthropicClient(
        responses=[FakeAnthropicResponse(text='{"answer":"x"}', input_tokens=8, output_tokens=3)],
        count_tokens=8,
    )
    runner = AnthropicRunner(client=client, raw_log_dir=tmp_path, clock=lambda: 1.0)

    result = runner.run(
        prompt="prompt",
        params=RunParams(model="claude-sonnet-4-6", native_output={"format": "json", "schema": schema}),
    )

    assert result.error is None
    tool = client.calls[0]["tools"][0]
    assert tool["input_schema"] == schema
    assert tool["strict"] is True


def test_anthropic_runner_maps_reasoning_effort_to_thinking_budget(tmp_path: Path) -> None:
    client = FakeAnthropicClient(
        responses=[FakeAnthropicResponse(text="answer", input_tokens=8, output_tokens=3)],
        count_tokens=8,
    )
    runner = AnthropicRunner(client=client, raw_log_dir=tmp_path, clock=lambda: 1.0)

    result = runner.run(prompt="prompt", params=RunParams(model="claude-sonnet-4-6", reasoning_effort="low"))

    assert result.error is None
    assert client.calls[0]["thinking"] == {"type": "enabled", "budget_tokens": 1024}
    assert result.params_used["anthropic_thinking_budget_tokens"] == 1024


def test_anthropic_runner_extracts_tool_use_input_for_structured_output(tmp_path: Path) -> None:
    client = FakeAnthropicClient(
        responses=[
            FakeAnthropicToolUseResponse(
                tool_input={"answer": "x"},
                input_tokens=8,
                output_tokens=3,
            )
        ],
        count_tokens=8,
    )
    runner = AnthropicRunner(client=client, raw_log_dir=tmp_path, clock=lambda: 1.0)

    result = runner.run(
        prompt="prompt",
        params=RunParams(model="claude-sonnet-4-6", native_output={"format": "json", "schema": {"type": "object"}}),
    )

    assert result.error is None
    assert result.response_text == '{"answer":"x"}'


def test_ollama_runner_parses_generate_response_and_estimates_tokens(tmp_path: Path) -> None:
    client = FakeOllamaClient(
        responses=[
            {
                "response": "local answer",
                "prompt_eval_count": 12,
                "eval_count": 4,
                "model": "qwen2.5:7b-instruct-q4_K_M",
            }
        ]
    )
    runner = OllamaRunner(client=client, raw_log_dir=tmp_path, clock=lambda: 1.0)

    result = runner.run(
        prompt="prompt text",
        params=RunParams(model="qwen2.5:7b-instruct-q4_K_M", task_id="task-local", seed=7),
    )

    assert result.error is None
    assert result.response_text == "local answer"
    assert result.input_tokens == 12
    assert result.output_tokens == 4
    assert result.params_used["model_version"] == "qwen2.5:7b-instruct-q4_K_M"
    assert result.params_used["effort_not_enforced"] is True
    assert client.calls[0]["endpoint"] == "/api/generate"
    assert client.calls[0]["payload"]["stream"] is False


def read_only_jsonl_event(directory: Path) -> dict[str, Any]:
    files = list(directory.glob("*.jsonl"))
    assert len(files) == 1
    lines = files[0].read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    return json.loads(lines[0])


class FakeOpenAIClient:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []
        self.responses_api = self

    @property
    def responses(self) -> FakeOpenAIClient:
        return self.responses_api

    @responses.setter
    def responses(self, value: list[Any]) -> None:
        self._responses = value

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeOpenAIResponse:
    def __init__(self, text: str, input_tokens: int, output_tokens: int) -> None:
        self.output_text = text
        self.usage = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }


class FakeAnthropicClient:
    def __init__(self, responses: list[Any], count_tokens: int) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []
        self.count_token_calls: list[dict[str, Any]] = []
        self.messages = self
        self._count_tokens = count_tokens

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def count_tokens(self, **kwargs: Any) -> Any:
        self.count_token_calls.append(kwargs)
        return type("CountTokensResponse", (), {"input_tokens": self._count_tokens})()


class FakeAnthropicResponse:
    def __init__(self, text: str, input_tokens: int, output_tokens: int) -> None:
        self.content = [type("TextBlock", (), {"text": text})()]
        self.usage = type(
            "Usage",
            (),
            {"input_tokens": input_tokens, "output_tokens": output_tokens},
        )()


class FakeAnthropicToolUseResponse:
    def __init__(self, tool_input: dict[str, Any], input_tokens: int, output_tokens: int) -> None:
        self.content = [type("ToolUseBlock", (), {"type": "tool_use", "input": tool_input})()]
        self.usage = type(
            "Usage",
            (),
            {"input_tokens": input_tokens, "output_tokens": output_tokens},
        )()


class FakeOllamaClient:
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def post_json(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append({"endpoint": endpoint, "payload": payload})
        return self.responses.pop(0)

from __future__ import annotations

import pytest

from templating.canonical import Format, InstructionBlock, NestedRecord
from templating.prompt_builder import (
    ExperimentMode,
    InstructionPosition,
    OutputMode,
    OutputRequest,
    PromptTask,
    SectionFormats,
    build_prompt,
)


@pytest.fixture
def task() -> PromptTask:
    return PromptTask(
        task_id="nested-lookup-001",
        instructions=InstructionBlock(
            role="Answer extraction model",
            context="Use only the provided service config.",
            instructions=["Find the requested value.", "Return the answer only."],
            examples=[{"input": "resources.cpu.limit", "output": "1 core"}],
        ),
        content=NestedRecord(
            data={
                "service": "checkout",
                "resources": {
                    "cpu": {"request": "500m", "limit": "1 core"},
                    "memory": {"request": "512Mi", "limit": "1Gi"},
                },
            }
        ),
        query="What is resources.cpu.request?",
    )


def test_q_in_variants_change_only_rendered_data_wrapping(task: PromptTask) -> None:
    markdown_prompt = build_prompt(
        task,
        input_format=Format.MARKDOWN,
        experiment_mode=ExperimentMode.Q_IN,
        output_request=OutputRequest.free_form(),
    )
    xml_prompt = build_prompt(
        task,
        input_format=Format.XML,
        experiment_mode=ExperimentMode.Q_IN,
        output_request=OutputRequest.free_form(),
    )

    assert section(markdown_prompt.message, "INSTRUCTIONS") == section(xml_prompt.message, "INSTRUCTIONS")
    assert section(markdown_prompt.message, "QUERY") == section(xml_prompt.message, "QUERY")
    assert section(markdown_prompt.message, "OUTPUT_CONSTRAINT") == section(xml_prompt.message, "OUTPUT_CONSTRAINT")
    assert section(markdown_prompt.message, "DATA") != section(xml_prompt.message, "DATA")
    assert markdown_prompt.semantic_fingerprint == xml_prompt.semantic_fingerprint
    assert markdown_prompt.native_output is None
    assert xml_prompt.native_output is None


def test_q_out_variants_change_only_output_constraint(task: PromptTask) -> None:
    free_form = build_prompt(
        task,
        input_format=Format.MARKDOWN,
        experiment_mode=ExperimentMode.Q_OUT,
        output_request=OutputRequest.free_form(),
    )
    text_json = build_prompt(
        task,
        input_format=Format.MARKDOWN,
        experiment_mode=ExperimentMode.Q_OUT,
        output_request=OutputRequest.text_format(Format.JSON),
    )
    native_json = build_prompt(
        task,
        input_format=Format.MARKDOWN,
        experiment_mode=ExperimentMode.Q_OUT,
        output_request=OutputRequest.structured_native(
            Format.JSON,
            schema={
                "type": "object",
                "properties": {"answer": {"type": "string"}},
                "required": ["answer"],
                "additionalProperties": False,
            },
        ),
    )

    assert section(free_form.message, "INSTRUCTIONS") == section(text_json.message, "INSTRUCTIONS")
    assert section(free_form.message, "INSTRUCTIONS") == section(native_json.message, "INSTRUCTIONS")
    assert section(free_form.message, "DATA") == section(text_json.message, "DATA")
    assert section(free_form.message, "DATA") == section(native_json.message, "DATA")
    assert section(free_form.message, "QUERY") == section(text_json.message, "QUERY")
    assert section(free_form.message, "OUTPUT_CONSTRAINT") != section(text_json.message, "OUTPUT_CONSTRAINT")
    assert section(text_json.message, "OUTPUT_CONSTRAINT") != section(native_json.message, "OUTPUT_CONSTRAINT")
    assert free_form.semantic_fingerprint == text_json.semantic_fingerprint == native_json.semantic_fingerprint
    assert native_json.native_output == {
        "format": "json",
        "schema": {
            "type": "object",
            "properties": {"answer": {"type": "string"}},
            "required": ["answer"],
            "additionalProperties": False,
        },
    }


def test_builder_rejects_attempt_to_vary_q_in_and_q_out_together(task: PromptTask) -> None:
    with pytest.raises(ValueError, match="Q-IN and Q-OUT"):
        build_prompt(
            task,
            input_format=Format.XML,
            experiment_mode=ExperimentMode.Q_IN,
            output_request=OutputRequest.text_format(Format.JSON),
        )


def test_builder_rejects_mixed_section_formats_in_q_out_mode(task: PromptTask) -> None:
    with pytest.raises(ValueError, match="section_formats"):
        build_prompt(
            task,
            experiment_mode=ExperimentMode.Q_OUT,
            output_request=OutputRequest.text_format(Format.JSON),
            section_formats=SectionFormats(
                instructions=Format.MARKDOWN,
                data=Format.XML,
            ),
        )


def test_text_format_output_request_rejects_native_schema() -> None:
    with pytest.raises(ValueError, match="schema"):
        OutputRequest(mode=OutputMode.TEXT_FORMAT, format=Format.JSON, json_schema={"type": "object"})


def test_instruction_position_head_tail_and_both(task: PromptTask) -> None:
    head = build_prompt(task, instruction_position=InstructionPosition.HEAD).message
    tail = build_prompt(task, instruction_position=InstructionPosition.TAIL).message
    both = build_prompt(task, instruction_position=InstructionPosition.BOTH).message

    assert head.index("[[INSTRUCTIONS]]") < head.index("[[DATA")
    assert tail.index("[[DATA") < tail.index("[[INSTRUCTIONS]]")
    assert both.count("[[INSTRUCTIONS]]") == 2
    assert section(head, "INSTRUCTIONS") == section(tail, "INSTRUCTIONS")


def test_mixed_prompt_uses_independent_section_formats_without_changing_semantics(task: PromptTask) -> None:
    pure_markdown = build_prompt(task, input_format=Format.MARKDOWN)
    mixed = build_prompt(
        task,
        section_formats=SectionFormats(
            instructions=Format.MARKDOWN,
            data=Format.XML,
        ),
    )

    assert section(pure_markdown.message, "INSTRUCTIONS") == section(mixed.message, "INSTRUCTIONS")
    assert section(pure_markdown.message, "DATA") != section(mixed.message, "DATA")
    assert "<record>" in section(mixed.message, "DATA")
    assert mixed.semantic_fingerprint == pure_markdown.semantic_fingerprint


def section(message: str, name: str) -> str:
    start = message.index(f"[[{name}")
    content_start = message.index("\n", start) + 1
    end = message.index(f"[[/{name}]]", content_start)
    return message[content_start:end].strip()

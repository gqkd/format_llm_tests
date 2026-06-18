"""
Assemble benchmark prompts from canonical tasks and format choices.

Input: A canonical task, input/output experiment settings, and section placement options.

Processing: Renders only the selected prompt sections while preserving canonical task content.

Output: A prompt message plus optional native structured-output configuration.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from templating.canonical import CanonicalContent, Format, InstructionBlock, Renderer
from templating.renderers.csv import CsvRenderer
from templating.renderers.json import JsonRenderer
from templating.renderers.markdown import MarkdownRenderer
from templating.renderers.plain import PlainRenderer
from templating.renderers.toon import ToonRenderer
from templating.renderers.xml import XmlRenderer
from templating.renderers.yaml import YamlRenderer


class ExperimentMode(str, Enum):
    """Axis varied by a benchmark prompt build."""

    Q_IN = "q_in"
    Q_OUT = "q_out"


class InstructionPosition(str, Enum):
    """Where instruction content is placed relative to rendered task data."""

    HEAD = "head"
    TAIL = "tail"
    BOTH = "both"


class OutputMode(str, Enum):
    """Output constraint strategy for Q-OUT experiments."""

    FREE_FORM = "free_form"
    TEXT_FORMAT = "text_format"
    STRUCTURED_NATIVE = "structured_native"


class PromptTask(BaseModel):
    """Canonical task payload used by the prompt builder."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: str = Field(min_length=1)
    instructions: InstructionBlock
    content: CanonicalContent
    query: str = Field(min_length=1)

    @model_validator(mode="after")
    def reject_blank_query(self) -> PromptTask:
        if not self.query.strip():
            raise ValueError("query must not be blank")
        return self


class OutputRequest(BaseModel):
    """Output constraint requested for a prompt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: OutputMode
    format: Format | None = None
    json_schema: dict[str, Any] | None = None

    @classmethod
    def free_form(cls) -> OutputRequest:
        return cls(mode=OutputMode.FREE_FORM)

    @classmethod
    def text_format(cls, output_format: Format) -> OutputRequest:
        return cls(mode=OutputMode.TEXT_FORMAT, format=output_format)

    @classmethod
    def structured_native(cls, output_format: Format, schema: dict[str, Any]) -> OutputRequest:
        return cls(mode=OutputMode.STRUCTURED_NATIVE, format=output_format, json_schema=schema)

    @model_validator(mode="after")
    def validate_mode_fields(self) -> OutputRequest:
        _OUTPUT_REQUEST_VALIDATORS[self.mode](self)
        return self


class SectionFormats(BaseModel):
    """Independent section formats for mixed-prompt experiments."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    instructions: Format = Format.MARKDOWN
    data: Format = Format.MARKDOWN


class BuiltPrompt(BaseModel):
    """Prompt build result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    message: str
    native_output: dict[str, Any] | None
    semantic_fingerprint: dict[str, Any]


def _validate_free_form_request(output_request: OutputRequest) -> None:
    if output_request.format is not None or output_request.json_schema is not None:
        raise ValueError("free-form output must not include format or schema")


def _validate_text_format_request(output_request: OutputRequest) -> None:
    if output_request.format is None:
        raise ValueError("text-format output requires a format")
    if output_request.json_schema is not None:
        raise ValueError("text-format output must not include a native schema")


def _validate_structured_native_request(output_request: OutputRequest) -> None:
    if output_request.format is None or output_request.json_schema is None:
        raise ValueError("native structured output requires format and schema")


_OUTPUT_REQUEST_VALIDATORS = {
    OutputMode.FREE_FORM: _validate_free_form_request,
    OutputMode.TEXT_FORMAT: _validate_text_format_request,
    OutputMode.STRUCTURED_NATIVE: _validate_structured_native_request,
}


_RENDERERS: dict[Format, Renderer] = {
    Format.PLAIN: PlainRenderer(),
    Format.MARKDOWN: MarkdownRenderer(),
    Format.XML: XmlRenderer(),
    Format.JSON: JsonRenderer(),
    Format.YAML: YamlRenderer(),
    Format.CSV: CsvRenderer(),
    Format.TOON: ToonRenderer(),
}


def build_prompt(
    task: PromptTask,
    input_format: Format = Format.MARKDOWN,
    experiment_mode: ExperimentMode = ExperimentMode.Q_IN,
    output_request: OutputRequest | None = None,
    instruction_position: InstructionPosition = InstructionPosition.HEAD,
    section_formats: SectionFormats | None = None,
) -> BuiltPrompt:
    """Build a model prompt while varying exactly one benchmark axis."""

    output_request = output_request or OutputRequest.free_form()
    _validate_axis_isolation(experiment_mode, output_request, section_formats)

    formats = section_formats or SectionFormats(data=input_format)
    instruction_text = _render(task.instructions, formats.instructions)
    data_text = _render(task.content, formats.data)
    output_text = _render_output_constraint(output_request)

    sections = _ordered_sections(
        instruction_text=instruction_text,
        data_text=data_text,
        query_text=task.query,
        output_text=output_text,
        instruction_position=instruction_position,
        data_format=formats.data,
    )
    return BuiltPrompt(
        message="\n\n".join(sections),
        native_output=_native_output(output_request),
        semantic_fingerprint=_semantic_fingerprint(task),
    )


def _validate_axis_isolation(
    experiment_mode: ExperimentMode,
    output_request: OutputRequest,
    section_formats: SectionFormats | None,
) -> None:
    if experiment_mode is ExperimentMode.Q_IN and output_request.mode is not OutputMode.FREE_FORM:
        raise ValueError("Q-IN and Q-OUT must not vary in the same prompt build")
    if experiment_mode is ExperimentMode.Q_OUT and section_formats is not None:
        raise ValueError("section_formats cannot be used in Q-OUT mode")


def _render(content: CanonicalContent, output_format: Format) -> str:
    return _RENDERERS[output_format].render(content)


def _ordered_sections(
    *,
    instruction_text: str,
    data_text: str,
    query_text: str,
    output_text: str,
    instruction_position: InstructionPosition,
    data_format: Format,
) -> list[str]:
    instruction_section = _section("INSTRUCTIONS", instruction_text)
    data_section = _section("DATA", data_text, {"format": data_format.value})
    query_section = _section("QUERY", query_text)
    output_section = _section("OUTPUT_CONSTRAINT", output_text)

    if instruction_position is InstructionPosition.HEAD:
        return [instruction_section, data_section, query_section, output_section]
    if instruction_position is InstructionPosition.TAIL:
        return [data_section, query_section, instruction_section, output_section]
    if instruction_position is InstructionPosition.BOTH:
        return [instruction_section, data_section, query_section, instruction_section, output_section]
    raise AssertionError(f"unsupported instruction position: {instruction_position}")


def _section(name: str, content: str, attributes: dict[str, str] | None = None) -> str:
    attr_text = ""
    if attributes:
        attr_text = " " + " ".join(f'{key}="{value}"' for key, value in attributes.items())
    return f"[[{name}{attr_text}]]\n{content}\n[[/{name}]]"


def _render_output_constraint(output_request: OutputRequest) -> str:
    if output_request.mode is OutputMode.FREE_FORM:
        return "Answer freely. Keep the requested answer content unchanged."
    if output_request.mode is OutputMode.TEXT_FORMAT:
        return f"Return the answer in {output_request.format.value} format."
    if output_request.mode is OutputMode.STRUCTURED_NATIVE:
        return "Return the answer using the native structured-output schema configured for this call."
    raise AssertionError(f"unsupported output mode: {output_request.mode}")


def _native_output(output_request: OutputRequest) -> dict[str, Any] | None:
    if output_request.mode is not OutputMode.STRUCTURED_NATIVE:
        return None
    return {
        "format": output_request.format.value,
        "schema": output_request.json_schema,
    }


def _semantic_fingerprint(task: PromptTask) -> dict[str, Any]:
    return {
        "task_id": task.task_id,
        "instructions": task.instructions.model_dump(mode="json"),
        "content": task.content.model_dump(mode="json"),
        "query": task.query,
    }

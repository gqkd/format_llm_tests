"""
Generate extraction benchmark items.

Input: None.

Processing: Builds five deterministic document/schema families with field-level gold answers.

Output: A list of SuiteItem objects with canonical documents and Pydantic output schemas.
"""

from __future__ import annotations

from pydantic import BaseModel

from suites._synthetic import document, synthetic_source
from suites.base import ExperimentAxis, SuiteItem, SuiteSpec
from templating.canonical import Format


class InvoiceExtraction(BaseModel):
    invoice_id: str
    vendor: str
    amount_usd: float


class ClinicalNoteExtraction(BaseModel):
    patient_id: str
    diagnosis: str
    medication: str


class ContractExtraction(BaseModel):
    contract_id: str
    counterparty: str
    renewal_days: int


class SupportTicketExtraction(BaseModel):
    ticket_id: str
    product: str
    priority: str


class ResearchAbstractExtraction(BaseModel):
    paper_id: str
    method: str
    dataset: str


SPEC = SuiteSpec(
    name="extraction",
    axis=ExperimentAxis.Q_OUT,
    formats=(Format.JSON,),
    metric="field_f1_schema_compliance",
    description="Structured extraction from short documents with schema compliance scoring.",
)

SCHEMAS: tuple[tuple[str, type[BaseModel], tuple[str, str, str]], ...] = (
    ("invoice", InvoiceExtraction, ("invoice_id", "vendor", "amount_usd")),
    ("clinical_note", ClinicalNoteExtraction, ("patient_id", "diagnosis", "medication")),
    ("contract", ContractExtraction, ("contract_id", "counterparty", "renewal_days")),
    ("support_ticket", SupportTicketExtraction, ("ticket_id", "product", "priority")),
    ("research_abstract", ResearchAbstractExtraction, ("paper_id", "method", "dataset")),
)


def load_items() -> list[SuiteItem]:
    source = synthetic_source(
        "synthetic-extractbench",
        "Replace with ExtractBench-style documents and gold field dictionaries.",
    )
    items: list[SuiteItem] = []
    for schema_name, schema_model, fields in SCHEMAS:
        for index in range(60):
            gold = _gold_for(schema_name, index, fields)
            text = _document_text(schema_name, gold)
            item_id = f"extraction-{schema_name}-{index:03d}"
            items.append(
                SuiteItem(
                    item_id=item_id,
                    suite=SPEC,
                    content=document(item_id, f"{schema_name} synthetic document {index}", source.name, text),
                    gold_answer=gold,
                    metric=SPEC.metric,
                    dataset_source=source,
                    output_schema=schema_model,
                    metadata={"source_dataset": source.name, "schema_name": schema_name},
                )
            )
    return items


def _gold_for(schema_name: str, index: int, fields: tuple[str, str, str]) -> dict[str, object]:
    if schema_name == "invoice":
        return {fields[0]: f"INV-{index:04d}", fields[1]: f"Vendor{index % 7}", fields[2]: float(100 + index)}
    if schema_name == "clinical_note":
        return {fields[0]: f"PT-{index:04d}", fields[1]: f"condition_{index % 5}", fields[2]: f"med_{index % 4}"}
    if schema_name == "contract":
        return {fields[0]: f"CTR-{index:04d}", fields[1]: f"Counterparty{index % 9}", fields[2]: 30 + index % 60}
    if schema_name == "support_ticket":
        return {fields[0]: f"TCK-{index:04d}", fields[1]: f"Product{index % 6}", fields[2]: ("low", "medium", "high")[index % 3]}
    return {fields[0]: f"PAPER-{index:04d}", fields[1]: f"method_{index % 5}", fields[2]: f"dataset_{index % 8}"}


def _document_text(schema_name: str, gold: dict[str, object]) -> str:
    fields = "; ".join(f"{key}: {value}" for key, value in gold.items())
    return f"Synthetic {schema_name} document. Extract these fields exactly: {fields}."

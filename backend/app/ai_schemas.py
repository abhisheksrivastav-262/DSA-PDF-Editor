from __future__ import annotations
from typing import Literal, Any
from pydantic import BaseModel, Field

# Supported operations registry - strict schemas

OperationType = Literal[
    "find_text",
    "replace_text",
    "replace_all",
    "delete_text",
    "insert_text",
    "highlight_text",
    "add_annotation",
    "redact_region",
    "extract_text",
    "extract_table",
    "summarize_document",
    "rotate_page",
    "delete_page",
    "duplicate_page",
    "reorder_pages",
    "split_pdf",
    "merge_pdf",
]

class AIOperation(BaseModel):
    type: OperationType
    find: str | None = None
    replace: str | None = None
    text: str | None = None
    page: int | None = None
    pages: list[int] | None = None
    scope: Literal["document", "page", "selected"] | None = "document"
    bbox: list[float] | None = None  # [x1,y1,x2,y2]
    annotation_type: str | None = None
    content: str | None = None
    angle: int | None = None
    order: list[int] | None = None

class AIResponse(BaseModel):
    intent: str
    confidence: float = Field(ge=0, le=1)
    explanation: str
    operations: list[AIOperation]
    requires_confirmation: bool = True

# JSON schema for validation (used at runtime)
AI_RESPONSE_JSON_SCHEMA = {
    "type": "object",
    "required": ["intent", "confidence", "explanation", "operations", "requires_confirmation"],
    "properties": {
        "intent": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "explanation": {"type": "string"},
        "requires_confirmation": {"type": "boolean"},
        "operations": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["type"],
                "properties": {
                    "type": {"type": "string", "enum": [
                        "find_text","replace_text","replace_all","delete_text","insert_text",
                        "highlight_text","add_annotation","redact_region","extract_text",
                        "extract_table","summarize_document","rotate_page","delete_page",
                        "duplicate_page","reorder_pages","split_pdf","merge_pdf"
                    ]},
                    "find": {"type": "string"},
                    "replace": {"type": "string"},
                    "text": {"type": "string"},
                    "page": {"type": "integer"},
                    "pages": {"type": "array", "items": {"type": "integer"}},
                    "scope": {"type": "string"},
                    "bbox": {"type": "array", "items": {"type": "number"}},
                    "annotation_type": {"type": "string"},
                    "content": {"type": "string"},
                    "angle": {"type": "integer"},
                    "order": {"type": "array", "items": {"type": "integer"}},
                },
                "additionalProperties": True
            }
        }
    },
    "additionalProperties": False
}

ALLOWED_OPERATIONS = set(AI_RESPONSE_JSON_SCHEMA["properties"]["operations"]["items"]["properties"]["type"]["enum"])

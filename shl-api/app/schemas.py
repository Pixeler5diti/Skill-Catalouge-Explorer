"""API request/response schemas. Never change the ChatResponse structure."""
from pydantic import BaseModel, Field
from typing import List, Optional


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[Message] = Field(..., min_length=1)


class Recommendation(BaseModel):
    name: str
    url: str
    test_type: str


class ChatResponse(BaseModel):
    reply: str
    recommendations: List[Recommendation] = Field(default_factory=list)
    end_of_conversation: bool = False


# Internal types (not exposed in API)
class AssessmentEntry(BaseModel):
    entity_id: str
    name: str
    url: str
    description: str
    keys: List[str]          # e.g. ["Knowledge & Skills"]
    job_levels: List[str]
    languages: List[str]
    duration: str
    remote: str
    adaptive: str
    # Derived
    test_type: str = ""      # joined keys for display
    searchable_text: str = ""  # pre-built search doc


class Intent(BaseModel):
    label: str  # clarification|recommendation|refinement|comparison|off_topic|prompt_injection
    raw: str

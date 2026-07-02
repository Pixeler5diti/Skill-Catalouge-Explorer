"""
Behavioural regression tests for the SHL planning agent.

Each test corresponds to a conversation trace that verifies the agent's
decision-making behaviour — not just retrieval quality. Tests verify:
  - clarification timing (recs=[] when insufficient context)
  - refinement (constraints merge, not replace)
  - comparison (direct lookup, no embeddings)
  - legal refusal (no recs, no retrieval)
  - conflict detection and tradeoff description
  - finish / end_of_conversation
  - planner fast-path accuracy

All LLM calls are mocked. The catalog fixture provides a deterministic
mini-catalog for rule assertions.
"""
import json
import pytest
from unittest.mock import patch, MagicMock

from app.schemas import Message, AssessmentEntry, ChatResponse
from app.conversation.planner import (
    PlannerOutput, Conflict, detect_conflicts, plan as planner_plan,
    _fast_path,
)
from app.catalog.preprocess import preprocess_catalog


# ── Mini-catalog fixture ──────────────────────────────────────────────────────

_CATALOG_RAW = [
    {
        "entity_id": "2001",
        "name": "HIPAA Security Awareness",
        "link": "https://www.shl.com/catalog/hipaa-security/",
        "job_levels": ["Professional"],
        "languages": ["English (USA)"],
        "duration": "20 minutes",
        "status": "ok", "remote": "yes", "adaptive": "no",
        "description": "Assesses knowledge of HIPAA security rules and patient data privacy.",
        "keys": ["Knowledge & Skills"],
    },
    {
        "entity_id": "2002",
        "name": "Medical Terminology",
        "link": "https://www.shl.com/catalog/medical-terminology/",
        "job_levels": ["Professional", "Graduate"],
        "languages": ["English (USA)"],
        "duration": "15 minutes",
        "status": "ok", "remote": "yes", "adaptive": "no",
        "description": "Assesses knowledge of clinical and medical terminology.",
        "keys": ["Knowledge & Skills"],
    },
    {
        "entity_id": "2003",
        "name": "OPQ32r",
        "link": "https://www.shl.com/catalog/opq32r/",
        "job_levels": ["Manager", "Director"],
        "languages": ["English (USA)", "Spanish (Latin America)", "French (France)"],
        "duration": "25 minutes",
        "status": "ok", "remote": "yes", "adaptive": "no",
        "description": "Occupational Personality Questionnaire. Measures 32 personality traits.",
        "keys": ["Personality & Behavior"],
    },
    {
        "entity_id": "2004",
        "name": "Verify - Numerical Reasoning",
        "link": "https://www.shl.com/catalog/verify-numerical/",
        "job_levels": ["Graduate", "Manager"],
        "languages": ["English (USA)"],
        "duration": "17 minutes",
        "status": "ok", "remote": "yes", "adaptive": "yes",
        "description": "Measures numerical reasoning for finance and analytical roles.",
        "keys": ["Ability & Aptitude"],
    },
    {
        "entity_id": "2005",
        "name": "Excel Skills Assessment",
        "link": "https://www.shl.com/catalog/excel-skills/",
        "job_levels": ["Professional"],
        "languages": ["English (USA)"],
        "duration": "30 minutes",
        "status": "ok", "remote": "yes", "adaptive": "no",
        "description": "Assesses Microsoft Excel proficiency including formulas and data analysis.",
        "keys": ["Knowledge & Skills"],
    },
    {
        "entity_id": "2006",
        "name": "DSI (Dependability and Safety Instrument)",
        "link": "https://www.shl.com/catalog/dsi/",
        "job_levels": ["Entry", "Professional"],
        "languages": ["English (USA)", "Spanish (Latin America)"],
        "duration": "20 minutes",
        "status": "ok", "remote": "yes", "adaptive": "no",
        "description": "Measures safety-conscious behaviours and dependability.",
        "keys": ["Personality & Behavior"],
    },
    {
        "entity_id": "2007",
        "name": "Verbal Reasoning",
        "link": "https://www.shl.com/catalog/verbal-reasoning/",
        "job_levels": ["Graduate", "Manager"],
        "languages": ["English (USA)"],
        "duration": "19 minutes",
        "status": "ok", "remote": "yes", "adaptive": "yes",
        "description": "Measures verbal reasoning and comprehension.",
        "keys": ["Ability & Aptitude"],
    },
    {
        "entity_id": "2008",
        "name": "Java Programming Skills",
        "link": "https://www.shl.com/catalog/java-programming/",
        "job_levels": ["Professional"],
        "languages": ["English (USA)"],
        "duration": "45 minutes",
        "status": "ok", "remote": "yes", "adaptive": "no",
        "description": "Tests Java programming knowledge and best practices.",
        "keys": ["Knowledge & Skills"],
    },
]


@pytest.fixture
def catalog():
    entries, by_id, by_name = preprocess_catalog(_CATALOG_RAW)
    return entries, by_id, by_name


def _make_engine(catalog):
    entries, by_id, by_name = catalog
    mock_retriever = MagicMock()
    # Return all catalog IDs with descending scores
    mock_retriever.retrieve.return_value = [
        (eid, 1.0 - i * 0.05)
        for i, eid in enumerate(by_id.keys())
    ]
    mock_retriever.entity_ids = list(by_id.keys())
    from app.conversation.chat_engine import ChatEngine
    return ChatEngine(mock_retriever, by_id, by_name)


def _mock_llm_response(content: dict):
    """Return a mock Groq client that yields the given dict as LLM output."""
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = json.dumps(content)
    mock_resp.usage.total_tokens = 150
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_resp
    return mock_client


# ═══════════════════════════════════════════════════════════════════════════════
# TRACE 1: Vague request → clarification, no recommendations
# ═══════════════════════════════════════════════════════════════════════════════

def test_trace_vague_request_triggers_clarify(catalog):
    """A single-word or vague request must produce clarification, not recommendations."""
    messages = [Message(role="user", content="I need help")]
    entries, by_id, by_name = catalog

    with patch("app.conversation.chat_engine.extract_constraints", return_value={}), \
         patch("app.conversation.chat_engine.detect_conflicts", return_value=None), \
         patch("app.conversation.chat_engine.planner_plan",
               return_value=PlannerOutput(intent="clarify", conflict=None)), \
         patch("app.llm.groq_client.Groq") as mock_groq:

        mock_groq.return_value = _mock_llm_response({
            "reply": "What role are you hiring for?",
            "selected_ids": [],
            "end_of_conversation": False,
        })
        import app.llm.groq_client as gc
        gc._client = mock_groq.return_value

        engine = _make_engine(catalog)
        result = engine.process(messages)

    assert result.recommendations == [], "Clarification must return no recommendations"
    assert result.end_of_conversation is False
    assert len(result.reply) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# TRACE 2: Healthcare + HIPAA → HIPAA Security boosted to top
# ═══════════════════════════════════════════════════════════════════════════════

def test_trace_healthcare_hipaa_filter(catalog):
    """Healthcare + HIPAA compliance topic → HIPAA Security Assessment should be top."""
    from app.retrieval.filter import apply_domain_rules
    entries, by_id, by_name = catalog

    constraints = {
        "domain": "healthcare",
        "compliance_topics": ["HIPAA"],
        "test_types": ["knowledge"],
    }
    candidates = [(eid, 1.0) for eid in by_id.keys()]
    filtered = apply_domain_rules(candidates, constraints, by_id, conflict=None)

    top_ids = [eid for eid, _ in filtered[:3]]
    top_names = [by_id[eid].name for eid in top_ids]
    assert "HIPAA Security Awareness" in top_names, (
        f"HIPAA Security must be in top 3 for healthcare+HIPAA. Got: {top_names}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TRACE 3: Healthcare + terminology → Medical Terminology boosted
# ═══════════════════════════════════════════════════════════════════════════════

def test_trace_healthcare_terminology_filter(catalog):
    """Healthcare + terminology skill → Medical Terminology Assessment should be top."""
    from app.retrieval.filter import apply_domain_rules
    entries, by_id, by_name = catalog

    constraints = {
        "domain": "healthcare",
        "skills": ["terminology", "vocabulary"],
        "test_types": ["knowledge"],
    }
    candidates = [(eid, 1.0) for eid in by_id.keys()]
    filtered = apply_domain_rules(candidates, constraints, by_id, conflict=None)

    top_ids = [eid for eid, _ in filtered[:3]]
    top_names = [by_id[eid].name for eid in top_ids]
    assert "Medical Terminology" in top_names, (
        f"Medical Terminology must be in top 3 for healthcare+terminology. Got: {top_names}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TRACE 4: Spanish + knowledge tests → conflict detected
# ═══════════════════════════════════════════════════════════════════════════════

def test_trace_spanish_knowledge_conflict_detected(catalog):
    """Spanish + knowledge test type → conflict because no Spanish knowledge tests exist."""
    entries, by_id, _ = catalog
    constraints = {
        "language": "Spanish",
        "test_types": ["knowledge"],
    }
    conflict = detect_conflicts(constraints, list(by_id.values()))

    assert conflict is not None, "Conflict must be detected for Spanish + knowledge"
    assert conflict.type == "language_knowledge_mismatch"
    assert "English" in conflict.description
    assert "Spanish" in conflict.description
    # The conflict description should mention personality assessments available in Spanish
    assert len(conflict.available_entries) > 0, (
        "Conflict should list personality assessments available in Spanish"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TRACE 5: Conflict → tradeoff described in agent reply
# ═══════════════════════════════════════════════════════════════════════════════

def test_trace_conflict_surfaces_in_reply(catalog):
    """When a conflict is present, agent must surface the tradeoff in its reply."""
    entries, by_id, by_name = catalog
    conflict = Conflict(
        type="language_knowledge_mismatch",
        description="Knowledge assessments are only in English. OPQ32r supports Spanish.",
        available_entries=["OPQ32r"],
    )
    constraints = {"language": "Spanish", "test_types": ["knowledge"]}
    messages = [Message(role="user", content="I need knowledge tests in Spanish")]

    with patch("app.conversation.chat_engine.extract_constraints", return_value=constraints), \
         patch("app.conversation.chat_engine.detect_conflicts", return_value=conflict), \
         patch("app.conversation.chat_engine.planner_plan",
               return_value=PlannerOutput(intent="recommend", conflict=conflict)), \
         patch("app.llm.groq_client.Groq") as mock_groq:

        mock_groq.return_value = _mock_llm_response({
            "reply": (
                "Knowledge assessments are only available in English. "
                "OPQ32r supports Spanish and can form a hybrid battery."
            ),
            "selected_ids": ["2003"],
            "end_of_conversation": False,
        })
        import app.llm.groq_client as gc
        gc._client = mock_groq.return_value

        engine = _make_engine(catalog)
        result = engine.process(messages)

    assert "English" in result.reply or "Spanish" in result.reply or "hybrid" in result.reply.lower()
    assert result.end_of_conversation is False


# ═══════════════════════════════════════════════════════════════════════════════
# TRACE 6: Finance → numerical reasoning and Excel boosted
# ═══════════════════════════════════════════════════════════════════════════════

def test_trace_finance_filter_boosts_numerical_and_excel(catalog):
    """Finance domain → Numerical Reasoning and Excel should be top candidates."""
    from app.retrieval.filter import apply_domain_rules
    entries, by_id, by_name = catalog

    constraints = {
        "domain": "finance",
        "skills": ["excel", "data analysis"],
    }
    candidates = [(eid, 1.0) for eid in by_id.keys()]
    filtered = apply_domain_rules(candidates, constraints, by_id, conflict=None)

    top_ids = [eid for eid, _ in filtered[:4]]
    top_names = [by_id[eid].name for eid in top_ids]
    assert "Verify - Numerical Reasoning" in top_names or "Excel Skills Assessment" in top_names, (
        f"Finance filter must boost Numerical or Excel. Got: {top_names}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TRACE 7: Compare OPQ32r vs DSI → direct lookup, no embeddings
# ═══════════════════════════════════════════════════════════════════════════════

def test_trace_compare_direct_lookup_no_embeddings(catalog):
    """compare intent must look up assessments by name. Retriever.retrieve should NOT be called."""
    entries, by_id, by_name = catalog
    messages = [
        Message(role="user", content="Compare OPQ32r and DSI"),
    ]

    with patch("app.conversation.chat_engine.extract_constraints", return_value={}), \
         patch("app.conversation.chat_engine.detect_conflicts", return_value=None), \
         patch("app.conversation.chat_engine.planner_plan",
               return_value=PlannerOutput(intent="compare", conflict=None)), \
         patch("app.llm.groq_client.Groq") as mock_groq:

        mock_groq.return_value = _mock_llm_response({
            "reply": "OPQ32r measures personality traits; DSI measures safety behaviour.",
            "selected_ids": ["2003", "2006"],
            "end_of_conversation": False,
        })
        import app.llm.groq_client as gc
        gc._client = mock_groq.return_value

        engine = _make_engine(catalog)
        result = engine.process(messages)

    # retriever.retrieve should not have been called for pure comparison
    engine.retriever.retrieve.assert_not_called()
    assert len(result.recommendations) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# TRACE 8: Legal question → refuse, no recommendations, no retrieval
# ═══════════════════════════════════════════════════════════════════════════════

def test_trace_legal_question_refused(catalog):
    """Legal / compliance question must be refused without any retrieval."""
    messages = [Message(role="user", content="Is HIPAA legally required by law?")]
    entries, by_id, by_name = catalog

    with patch("app.conversation.chat_engine.extract_constraints",
               return_value={"compliance_topics": ["HIPAA"]}), \
         patch("app.conversation.chat_engine.detect_conflicts", return_value=None), \
         patch("app.conversation.chat_engine.planner_plan",
               return_value=PlannerOutput(intent="refuse", conflict=None)), \
         patch("app.llm.groq_client.Groq") as mock_groq:

        mock_groq.return_value = _mock_llm_response({
            "reply": "I cannot advise on legal requirements. Please consult legal counsel.",
            "selected_ids": [],
            "end_of_conversation": False,
        })
        import app.llm.groq_client as gc
        gc._client = mock_groq.return_value

        engine = _make_engine(catalog)
        result = engine.process(messages)

    assert result.recommendations == [], "Legal refusal must return no recommendations"
    engine.retriever.retrieve.assert_not_called()  # no retrieval for refuse


# ═══════════════════════════════════════════════════════════════════════════════
# TRACE 9: Refinement → constraints merged, not replaced
# ═══════════════════════════════════════════════════════════════════════════════

def test_trace_refinement_merges_constraints(catalog):
    """'Add personality' follow-up must merge with prior domain/language constraints."""
    from app.conversation.constraint_extractor import merge_constraints

    # Simulate: prior turn extracted these
    base_constraints = {
        "domain": "healthcare",
        "language": "Spanish",
        "test_types": ["cognitive"],
        "compliance_topics": ["HIPAA"],
    }
    # Latest user turn: "add personality assessments"
    delta_constraints = {
        "test_types": ["personality"],
    }

    merged = merge_constraints(base_constraints, delta_constraints)

    assert merged["domain"] == "healthcare", "Domain must survive refinement merge"
    assert merged["language"] == "Spanish", "Language must survive refinement merge"
    assert "HIPAA" in merged["compliance_topics"], "HIPAA must survive refinement merge"
    assert "cognitive" in merged["test_types"], "cognitive must be in merged test_types"
    assert "personality" in merged["test_types"], "personality must be added"


# ═══════════════════════════════════════════════════════════════════════════════
# TRACE 10: Finish / end of conversation
# ═══════════════════════════════════════════════════════════════════════════════

def test_trace_finish_ends_conversation(catalog):
    """'Thanks' / wrap-up message must set end_of_conversation=True."""
    messages = [
        Message(role="user",      content="Need assessments for a nurse"),
        Message(role="assistant", content="I recommend these assessments..."),
        Message(role="user",      content="Thank you, that's all I needed"),
    ]

    with patch("app.conversation.chat_engine.extract_constraints", return_value={}), \
         patch("app.conversation.chat_engine.detect_conflicts", return_value=None), \
         patch("app.conversation.chat_engine.planner_plan",
               return_value=PlannerOutput(intent="finish", conflict=None)):

        engine = _make_engine(catalog)
        result = engine.process(messages)

    assert result.end_of_conversation is True
    assert result.recommendations == []
    engine.retriever.retrieve.assert_not_called()


# ═══════════════════════════════════════════════════════════════════════════════
# PLANNER fast-path unit tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_fast_path_legal_keywords():
    msgs = [Message(role="user", content="Is HIPAA required by law in the US?")]
    assert _fast_path(msgs) == "refuse"


def test_fast_path_thanks():
    msgs = [Message(role="user", content="Thanks, that's all")]
    assert _fast_path(msgs) == "finish"


def test_fast_path_compare():
    msgs = [Message(role="user", content="What is the difference between OPQ32r and DSI?")]
    assert _fast_path(msgs) == "compare"


def test_fast_path_refine_with_prior_assistant():
    msgs = [
        Message(role="user",      content="Need cognitive tests for nurses"),
        Message(role="assistant", content="Here are my recommendations..."),
        Message(role="user",      content="Add personality tests as well"),
    ]
    assert _fast_path(msgs) == "refine"


def test_fast_path_returns_none_for_first_recommendation():
    msgs = [Message(role="user", content="I need assessments for a software engineer role")]
    # No prior assistant message → no refine fast-path
    result = _fast_path(msgs)
    # Should return None (no fast-path match) or compare (if vs. keyword found)
    assert result in (None, "compare", "refuse", "finish")
    assert result != "refine"  # can't refine with no prior recs


# ═══════════════════════════════════════════════════════════════════════════════
# LANGUAGE hard-filter (filter.py)
# ═══════════════════════════════════════════════════════════════════════════════

def test_language_hard_filter_removes_english_only(catalog):
    """Spanish language filter must remove English-only assessments."""
    from app.retrieval.filter import apply_domain_rules
    entries, by_id, by_name = catalog

    constraints = {"language": "Spanish", "test_types": ["personality"]}
    candidates = [(eid, 1.0) for eid in by_id.keys()]
    filtered = apply_domain_rules(candidates, constraints, by_id, conflict=None)

    remaining_ids = [eid for eid, _ in filtered]
    for eid in remaining_ids:
        entry = by_id[eid]
        langs = " ".join(entry.languages).lower()
        assert "spanish" in langs, (
            f"{entry.name} should not appear after Spanish hard-filter. "
            f"Languages: {entry.languages}"
        )


def test_language_filter_skipped_when_conflict(catalog):
    """When a conflict is present, language filter must NOT remove candidates."""
    from app.retrieval.filter import apply_domain_rules
    entries, by_id, by_name = catalog

    conflict = Conflict(
        type="language_knowledge_mismatch",
        description="No Spanish knowledge tests",
        available_entries=[],
    )
    constraints = {"language": "Spanish", "test_types": ["knowledge"]}
    candidates = [(eid, 1.0) for eid in by_id.keys()]
    filtered = apply_domain_rules(candidates, constraints, by_id, conflict=conflict)

    # Should keep all candidates (conflict = show what's available)
    assert len(filtered) == len(candidates), (
        "Language filter must not remove candidates when conflict is present"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Java skills filter
# ═══════════════════════════════════════════════════════════════════════════════

def test_java_skills_filter(catalog):
    """Java in skills/domain → Java Programming Skills assessment should be top."""
    from app.retrieval.filter import apply_domain_rules
    entries, by_id, by_name = catalog

    constraints = {
        "domain": "software",
        "skills": ["java"],
        "job_role": "java developer",
    }
    candidates = [(eid, 1.0) for eid in by_id.keys()]
    filtered = apply_domain_rules(candidates, constraints, by_id, conflict=None)

    top_ids = [eid for eid, _ in filtered[:3]]
    top_names = [by_id[eid].name for eid in top_ids]
    assert "Java Programming Skills" in top_names, (
        f"Java skills filter must boost Java Programming Skills. Got: {top_names}"
    )

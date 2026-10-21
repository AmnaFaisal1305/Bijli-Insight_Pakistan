
"""
Location: tests/test_rag.py

Purpose:
    Unit tests for the RAG Insight Agent.

Coverage:
    - Unsupported queries trigger fallback.
    - Missing LLM triggers fallback.
    - Grounded context produces structured answers.
    - Citations use retrieved document metadata.
    - Only verified Gold row IDs are returned.
    - LLM failures trigger fallback.
    - Empty LLM responses trigger fallback.

Run:
    pytest tests/test_rag.py -v
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock
import duckdb
import pytest

# Ensure repository root is on sys.path when running script directly
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.agents.insight_rag_agent import InsightAgentRAG


# ============================================================
# HELPERS
# ============================================================

def make_agent(llm_client=None, db_connection=None):
    """Create an agent without requiring a real ChromaDB server."""

    return InsightAgentRAG(
        chroma_client=None,
        db_connection=db_connection,
        llm_client=llm_client,
    )


def make_llm_client(content="### Direct Answer\nTest answer."):
    """Create a mocked Groq-compatible chat completion client."""

    client = MagicMock()

    message = MagicMock()
    message.content = content

    choice = MagicMock()
    choice.message = message

    completion = MagicMock()
    completion.choices = [choice]

    client.chat.completions.create.return_value = completion

    return client


def make_grounded_context():
    """Create representative retrieved policy evidence."""

    return {
        "is_grounded": True,
        "documents": [
            (
                "The supplied policy discusses building energy "
                "efficiency. This excerpt does not specify an "
                "AC temperature setpoint."
            )
        ],
        "metadatas": [
            {
                "title": "NEECA ECBC-2023",
                "page": 12,
                "publisher": "NEECA Pakistan",
            }
        ],
        "distances": [0.2],
        "verified_rows": [
            (
                "pk_kh_row_001",
                "2026-10-21 10:00:00",
                35.5,
            )
        ],
        "row_ids": ["pk_kh_row_001"],
    }


# ============================================================
# FALLBACK TESTS
# ============================================================

def test_rag_unsupported_query_triggers_fallback():
    """Unsupported queries must not invoke the LLM."""

    llm = make_llm_client()
    agent = make_agent(llm_client=llm)

    response = agent.synthesize_verified_advice(
        user_query="What will electricity cost in the year 2045?",
        retrieval_context={"is_grounded": False},
    )

    assert response["fallback_triggered"] is True
    assert "I don't know" in response["narrative_explanation"]
    assert response["cited_documents"] == []
    assert response["grounding_gold_row_ids"] == []
    assert response["confidence_score"] == 0.0

    llm.chat.completions.create.assert_not_called()


def test_rag_missing_llm_triggers_fallback():
    """Without an LLM, the agent must fail closed."""

    agent = make_agent(llm_client=None)
    agent.llm = None  # Isolate from environment-loaded GROQ_API_KEY

    response = agent.synthesize_verified_advice(
        user_query="Explain the policy.",
        retrieval_context=make_grounded_context(),
    )

    assert response["fallback_triggered"] is True
    assert "I don't know" in response["narrative_explanation"]
    assert response["cited_documents"] == []
    assert response["grounding_gold_row_ids"] == []


def test_rag_empty_context_triggers_fallback():
    """An empty evidence context must not produce an answer."""

    agent = make_agent(llm_client=make_llm_client())

    response = agent.synthesize_verified_advice(
        user_query="Explain the energy policy.",
        retrieval_context={
            "is_grounded": True,
            "documents": [],
            "metadatas": [],
        },
    )

    assert response["fallback_triggered"] is True
    assert response["cited_documents"] == []
    assert response["grounding_gold_row_ids"] == []


# ============================================================
# GROUNDED RESPONSE CONTRACT
# ============================================================

def test_rag_grounded_response_contract():
    """Valid evidence and a working LLM produce the expected schema."""

    llm = make_llm_client(
        "### Direct Answer\n"
        "The retrieved excerpt discusses building energy efficiency.\n\n"
        "### Limitations\n"
        "The supplied excerpt does not specify an AC setpoint."
    )

    agent = make_agent(llm_client=llm)

    response = agent.synthesize_verified_advice(
        user_query="What does this policy say about energy efficiency?",
        retrieval_context=make_grounded_context(),
    )

    assert response["fallback_triggered"] is False
    assert response["narrative_explanation"]
    assert isinstance(response["narrative_explanation"], str)

    assert len(response["cited_documents"]) == 1

    citation = response["cited_documents"][0]

    assert citation["document_title"] == "NEECA ECBC-2023"
    assert citation["section_reference"] == "Page 12"
    assert citation["publisher"] == "NEECA Pakistan"

    assert response["grounding_gold_row_ids"] == [
        "pk_kh_row_001"
    ]

    assert response["confidence_score"] == 0.0

    llm.chat.completions.create.assert_called_once()


def test_rag_grounded_context_without_verified_rows():
    """Policy synthesis can work without unrelated metric records."""

    llm = make_llm_client(
        "### Direct Answer\n"
        "The policy excerpt discusses energy efficiency."
    )

    context = make_grounded_context()
    context["verified_rows"] = []
    context["row_ids"] = []

    agent = make_agent(llm_client=llm)

    response = agent.synthesize_verified_advice(
        user_query="Summarize the policy.",
        retrieval_context=context,
    )

    assert response["fallback_triggered"] is False
    assert len(response["cited_documents"]) == 1
    assert response["grounding_gold_row_ids"] == []


# ============================================================
# CITATION CONTRACTS
# ============================================================

def test_rag_missing_source_metadata_does_not_invent_citation():
    """Incomplete metadata must not become a fabricated citation."""

    llm = make_llm_client(
        "### Direct Answer\n"
        "The retrieved text discusses energy efficiency."
    )

    context = make_grounded_context()
    context["metadatas"] = [
        {
            "page": 12,
        }
    ]

    agent = make_agent(llm_client=llm)

    response = agent.synthesize_verified_advice(
        user_query="Summarize this document.",
        retrieval_context=context,
    )

    assert response["fallback_triggered"] is False
    assert response["cited_documents"] == []


def test_rag_duplicate_citations_are_removed():
    """The same title, publisher, and page should appear once."""

    llm = make_llm_client("### Direct Answer\nSupported answer.")

    context = make_grounded_context()
    context["documents"] = [
        "Energy efficiency policy excerpt A.",
        "Energy efficiency policy excerpt B.",
    ]
    context["metadatas"] = [
        {
            "title": "NEECA ECBC-2023",
            "page": 12,
            "publisher": "NEECA Pakistan",
        },
        {
            "title": "NEECA ECBC-2023",
            "page": 12,
            "publisher": "NEECA Pakistan",
        },
    ]

    agent = make_agent(llm_client=llm)

    response = agent.synthesize_verified_advice(
        user_query="Summarize the policy.",
        retrieval_context=context,
    )

    assert response["fallback_triggered"] is False
    assert len(response["cited_documents"]) == 1


# ============================================================
# VERIFIED GOLD ROW IDS
# ============================================================

def test_only_verified_row_ids_are_returned():
    """IDs in the response must originate from verified rows."""

    llm = make_llm_client("### Direct Answer\nSupported answer.")

    context = make_grounded_context()

    # This unverified ID must not be returned merely because
    # it appears in the incoming row_ids field.
    context["row_ids"] = [
        "pk_kh_row_001",
        "invented_row_999",
    ]

    context["verified_rows"] = [
        (
            "pk_kh_row_001",
            "2026-10-21 10:00:00",
            35.5,
        )
    ]

    agent = make_agent(llm_client=llm)

    response = agent.synthesize_verified_advice(
        user_query="Summarize the available evidence.",
        retrieval_context=context,
    )

    assert response["fallback_triggered"] is False
    assert response["grounding_gold_row_ids"] == [
        "pk_kh_row_001"
    ]
    assert "invented_row_999" not in (
        response["grounding_gold_row_ids"]
    )


# ============================================================
# LLM FAILURE TESTS
# ============================================================

def test_rag_llm_exception_triggers_fallback():
    """API exceptions must not crash the caller or invent an answer."""

    llm = make_llm_client()

    llm.chat.completions.create.side_effect = RuntimeError(
        "Simulated Groq API failure"
    )

    agent = make_agent(llm_client=llm)

    response = agent.synthesize_verified_advice(
        user_query="Summarize this policy.",
        retrieval_context=make_grounded_context(),
    )

    assert response["fallback_triggered"] is True
    assert "I don't know" in response["narrative_explanation"]
    assert response["cited_documents"] == []
    assert response["grounding_gold_row_ids"] == []


def test_rag_empty_llm_response_triggers_fallback():
    """An empty model completion must not be treated as an answer."""

    llm = make_llm_client(content="")

    agent = make_agent(llm_client=llm)

    response = agent.synthesize_verified_advice(
        user_query="Summarize this policy.",
        retrieval_context=make_grounded_context(),
    )

    assert response["fallback_triggered"] is True
    assert response["cited_documents"] == []


def test_rag_explicit_llm_abstention_triggers_fallback():
    """An explicit unsupported-answer statement must abstain."""

    llm = make_llm_client(
        "I don't know based on the available verified evidence."
    )

    agent = make_agent(llm_client=llm)

    response = agent.synthesize_verified_advice(
        user_query="What is the unsupported future electricity cost?",
        retrieval_context=make_grounded_context(),
    )

    assert response["fallback_triggered"] is True
    assert response["cited_documents"] == []
    assert response["grounding_gold_row_ids"] == []


# ============================================================
# DUCKDB VERIFICATION
# ============================================================

def test_duckdb_verifies_only_existing_rows():
    """DuckDB should return existing IDs and reject unknown IDs."""

    db = duckdb.connect(":memory:")

    try:
        db.execute("""
            CREATE TABLE gold_weather_features (
                row_id VARCHAR,
                timestamp_utc TIMESTAMP,
                temperature_c DOUBLE
            )
        """)

        db.execute("""
            INSERT INTO gold_weather_features
            VALUES (
                'pk_kh_row_001',
                TIMESTAMP '2026-10-21 10:00:00',
                35.5
            )
        """)

        agent = make_agent(db_connection=db)

        rows = agent._verify_gold_rows(
            ["pk_kh_row_001", "unknown_row"]
        )

        assert len(rows) == 1
        assert rows[0][0] == "pk_kh_row_001"

    finally:
        db.close()


def test_duckdb_missing_connection_returns_no_rows():
    """Without DuckDB, no row IDs can be verified."""

    agent = make_agent(db_connection=None)

    assert agent._verify_gold_rows(["pk_kh_row_001"]) == []


# ============================================================
# RUN WITH PYTEST
# ============================================================

if __name__ == "__main__":
    raise SystemExit(
        pytest.main([__file__, "-v"])
    )


# ============================================================
# KNOWLEDGE BASE SOURCES
# ============================================================

def test_tariff_document_carries_every_slab_rate():
    from backend.pipeline.build_knowledge_base import _tariff_pages, TARIFF_CSV
    page = _tariff_pages(TARIFF_CSV)[0]
    for rate in ["16.48", "22.95", "34.26", "42.12", "48.84"]:
        assert rate in page


def test_ocr_transcription_keeps_pdf_page_numbers():
    from backend.pipeline.build_knowledge_base import _ocr_pages, KB_DIR
    pages = _ocr_pages(KB_DIR / "neeca_residential_ecbc.ocr.txt")
    assert len(pages) == 11  # the scanned PDF has 11 pages
    assert "ECBC-2023" in pages[1]  # page 2 introduces the building code


def test_ensure_knowledge_base_only_ingests_missing_sources():
    from backend.pipeline import build_knowledge_base as kb

    class FakeCollection:
        def get(self, where, limit):
            # Pretend the policy PDF is already indexed
            return {"ids": ["x"] if where["title"] == kb.POLICY_TITLE else []}

    class FakeAgent:
        collection = FakeCollection()
        ingested = []

        def ingest_pages(self, pages, doc_id, title, publisher):
            self.ingested.append(doc_id)
            return len(pages)

    agent = FakeAgent()
    added = kb.ensure_knowledge_base(agent)
    assert agent.ingested == ["neeca_residential_ecbc", "nepra_tariff_slabs_2024"]
    assert added == 11 + 1

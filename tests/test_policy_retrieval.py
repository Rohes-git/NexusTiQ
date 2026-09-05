"""Unit and integration tests for Milestone 4 Policy Retrieval & Clause Grounding."""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app import app
from src.config import Settings
from src.models import (
    ExtractedFact,
    ClaimFacts,
    PolicyRetrievalRequest,
)
from src.retrieval.policy_loader import (
    PolicyClause,
    PolicyClauseLoader,
    PolicyNotFoundError,
    InvalidPolicyError,
    DuplicateClauseError,
)
from src.retrieval.embedding_service import (
    EmbeddingService,
    MockEmbeddingService,
    EmbeddingServiceError,
    GeminiNotConfiguredError,
)
from src.retrieval.vector_index import (
    VectorIndex,
    RetrievedClause,
    EmptyIndexError,
    DimensionMismatchError,
    InvalidCacheError,
)
from src.retrieval.query_builder import QueryBuilder
from src.retrieval.grounding import GroundingService, GroundedClause, CLAUSE_FACTUAL_REASONS
from src.retrieval.policy_retriever import PolicyRetriever, PolicyRetrieverError

BASE_DIR = Path(__file__).resolve().parent.parent
POLICY_JSON_PATH = BASE_DIR / "data" / "policy" / "motor_policy.json"
client = TestClient(app)


# ── 1. Policy Clause Loader Tests ────────────────────────────────────────

def test_load_canonical_policy():
    """PolicyClauseLoader must load all 16 clauses and preserve fields."""
    loader = PolicyClauseLoader(POLICY_JSON_PATH)
    clauses = loader.load_clauses()

    assert len(clauses) == 16
    assert isinstance(clauses[0], PolicyClause)

    clause_map = {c.clause_id: c for c in clauses}
    assert "1.1" in clause_map
    assert "2.1" in clause_map
    assert "3.2" in clause_map
    assert "7.3" in clause_map

    c21 = clause_map["2.1"]
    assert c21.section == "SECTION 2 — ACCIDENTAL DAMAGE"
    assert c21.title == "Accidental Damage Coverage"
    assert "collision" in c21.text.lower()
    assert len(c21.tags) >= 1


def test_compute_policy_hash_deterministic():
    """Policy hash must be a deterministic 64-char hex SHA-256 string."""
    loader = PolicyClauseLoader(POLICY_JSON_PATH)
    h1 = loader.compute_policy_hash()
    h2 = loader.compute_policy_hash()
    assert len(h1) == 64
    assert h1 == h2


def test_loader_nonexistent_file(tmp_path):
    """Missing policy file raises PolicyNotFoundError."""
    loader = PolicyClauseLoader(tmp_path / "missing_policy.json")
    with pytest.raises(PolicyNotFoundError):
        loader.load_clauses()


def test_loader_malformed_json(tmp_path):
    """Corrupt JSON in policy raises InvalidPolicyError."""
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{ unclosed json", encoding="utf-8")
    loader = PolicyClauseLoader(bad_file)
    with pytest.raises(InvalidPolicyError):
        loader.load_clauses()


def test_loader_missing_clauses_key(tmp_path):
    """JSON missing clauses array raises InvalidPolicyError."""
    bad_file = tmp_path / "no_clauses.json"
    bad_file.write_text(json.dumps({"policy_name": "Test"}), encoding="utf-8")
    loader = PolicyClauseLoader(bad_file)
    with pytest.raises(InvalidPolicyError):
        loader.load_clauses()


def test_loader_duplicate_clause_ids(tmp_path):
    """Duplicate clause IDs raise DuplicateClauseError."""
    dup_file = tmp_path / "dup.json"
    data = {
        "clauses": [
            {"clause_id": "1.1", "section": "S1", "title": "T1", "text": "Clause 1"},
            {"clause_id": "1.1", "section": "S1", "title": "T2", "text": "Clause 2 duplicate"},
        ]
    }
    dup_file.write_text(json.dumps(data), encoding="utf-8")
    loader = PolicyClauseLoader(dup_file)
    with pytest.raises(DuplicateClauseError):
        loader.load_clauses()


# ── 2. Vector Index & Cosine Similarity Tests ────────────────────────────

def test_vector_index_search_ranking():
    """VectorIndex must calculate cosine similarity and rank results deterministically."""
    c1 = PolicyClause(clause_id="1.1", section="S1", title="T1", text="Accident damage")
    c2 = PolicyClause(clause_id="2.1", section="S2", title="T2", text="Theft total loss")
    c3 = PolicyClause(clause_id="3.1", section="S3", title="T3", text="Exclusion fraud")

    # Mock embeddings: 3 dimensions
    embeddings = [
        [1.0, 0.0, 0.0],  # Close to query [1.0, 0.0, 0.0]
        [0.0, 1.0, 0.0],  # Orthogonal
        [0.707, 0.707, 0.0],  # Moderate similarity
    ]

    index = VectorIndex()
    index.build([c1, c2, c3], embeddings, "fake_hash", "mock_model")
    assert index.is_built is True
    assert index.dimension == 3

    # Search for [1.0, 0.0, 0.0]
    results = index.search([1.0, 0.0, 0.0], top_k=3)
    assert len(results) == 3
    assert results[0].clause_id == "1.1"
    assert results[0].similarity_score == 1.0
    assert results[1].clause_id == "3.1"
    assert results[2].clause_id == "2.1"
    assert results[2].similarity_score == 0.0


def test_vector_index_top_k_limit():
    """VectorIndex top_k parameter must be strictly honored."""
    clauses = [
        PolicyClause(clause_id=f"1.{i}", section="S", title=f"T{i}", text=f"Text {i}")
        for i in range(10)
    ]
    embeddings = [[float(i), 1.0] for i in range(10)]

    index = VectorIndex()
    index.build(clauses, embeddings, "hash", "model")

    res_2 = index.search([1.0, 1.0], top_k=2)
    assert len(res_2) == 2

    res_5 = index.search([1.0, 1.0], top_k=5)
    assert len(res_5) == 5


def test_vector_index_empty_query_raises():
    """Searching unbuilt index must raise EmptyIndexError."""
    index = VectorIndex()
    with pytest.raises(EmptyIndexError):
        index.search([1.0, 0.0])


def test_vector_index_dimension_mismatch():
    """Query with wrong dimension must raise DimensionMismatchError."""
    c = PolicyClause(clause_id="1.1", section="S", title="T", text="Text")
    index = VectorIndex()
    index.build([c], [[1.0, 2.0]], "hash", "model")

    with pytest.raises(DimensionMismatchError):
        index.search([1.0, 2.0, 3.0])  # 3D query on 2D index


def test_vector_index_save_and_load(tmp_path):
    """Saving and loading vector index cache must preserve metadata and embeddings."""
    c1 = PolicyClause(clause_id="1.1", section="S1", title="Title 1", text="Text 1")
    c2 = PolicyClause(clause_id="2.1", section="S2", title="Title 2", text="Text 2")
    embeddings = [[0.6, 0.8], [0.8, 0.6]]

    index = VectorIndex()
    index.build([c1, c2], embeddings, "test_hash_123", "text-embedding-004")

    cache_file = tmp_path / "test_embeddings.json"
    index.save(cache_file)
    assert cache_file.exists()

    loaded_index = VectorIndex()
    loaded_index.load(cache_file)

    assert loaded_index.is_built is True
    assert loaded_index.policy_hash == "test_hash_123"
    assert loaded_index.embedding_model == "text-embedding-004"
    assert loaded_index.dimension == 2
    assert len(loaded_index.clauses) == 2
    assert loaded_index.is_valid_for("test_hash_123", "text-embedding-004") is True
    assert loaded_index.is_valid_for("wrong_hash", "text-embedding-004") is False
    assert loaded_index.is_valid_for("test_hash_123", "different-model") is False


# ── 3. Embedding Service Tests ───────────────────────────────────────────

def test_mock_embedding_service():
    """MockEmbeddingService generates deterministic normalized vectors."""
    mock = MockEmbeddingService(dimension=32)
    v1 = mock.embed_text("Motor accident claim")
    v2 = mock.embed_text("Motor accident claim")
    v3 = mock.embed_text("Total theft of two-wheeler")

    assert len(v1) == 32
    assert v1 == v2  # Deterministic
    assert v1 != v3  # Differentiable

    batch = mock.embed_texts(["Text A", "Text B"])
    assert len(batch) == 2
    assert len(batch[0]) == 32


def test_embedding_service_empty_text():
    """Embedding empty text raises EmbeddingServiceError."""
    mock = MockEmbeddingService()
    with pytest.raises(EmbeddingServiceError):
        mock.embed_text("")
    with pytest.raises(EmbeddingServiceError):
        mock.embed_text("   ")


def test_real_embedding_service_without_key():
    """EmbeddingService raises GeminiNotConfiguredError if API key missing."""
    service = EmbeddingService(api_key="")
    with pytest.raises(GeminiNotConfiguredError):
        service.embed_text("Sample policy text")


# ── 4. Query Construction Tests ──────────────────────────────────────────

def test_query_builder_from_extracted_facts():
    """QueryBuilder creates semantic query with incident, vehicle, dates, amounts."""
    facts = [
        ExtractedFact(field_name="incident_type", value="accident", raw_value="accident", page_number=1),
        ExtractedFact(field_name="vehicle_make", value="Hyundai", raw_value="Hyundai", page_number=1),
        ExtractedFact(field_name="vehicle_model", value="i20", raw_value="i20", page_number=1),
        ExtractedFact(field_name="vehicle_registration", value="TN01AB1234", raw_value="TN01AB1234", page_number=1),
        ExtractedFact(field_name="incident_date", value="2026-08-20", raw_value="20 Aug 2026", page_number=1),
        ExtractedFact(field_name="notification_date", value="2026-08-22", raw_value="22 Aug 2026", page_number=1),
        ExtractedFact(field_name="claimed_amount", value=78000, raw_value="₹78,000", page_number=1),
        ExtractedFact(field_name="incident_description", value="Front collision with tree.", raw_value="...", page_number=1),
    ]

    query = QueryBuilder.build_query(facts)

    assert "Accidental damage" in query
    assert "Hyundai i20" in query
    assert "TN01AB1234" in query
    assert "2026-08-20" in query
    assert "78000" in query
    assert "Front collision" in query


def test_query_builder_theft_case():
    """QueryBuilder creates theft-specific query terms."""
    facts = {
        "incident_type": "theft",
        "vehicle_make": "Honda",
        "vehicle_model": "Activa 6G",
        "claimed_amount": 72000,
    }

    query = QueryBuilder.build_query(facts)
    assert "Theft loss" in query
    assert "FIR" in query
    assert "Honda Activa 6G" in query
    assert "72000" in query


def test_query_builder_empty_or_none():
    """QueryBuilder returns safe default query when facts are empty or None."""
    q_none = QueryBuilder.build_query(None)
    assert "motor insurance" in q_none.lower()

    q_empty = QueryBuilder.build_query([])
    assert "motor insurance" in q_empty.lower()


# ── 5. Grounding Service Tests ───────────────────────────────────────────

def test_grounding_service_factual_reasons():
    """GroundingService associates factual, deterministic rationale with clauses."""
    retrieved = [
        RetrievedClause(
            clause_id="2.1",
            section="SECTION 2 — ACCIDENTAL DAMAGE",
            title="Accidental Damage Coverage",
            text="Physical damage caused by collision...",
            similarity_score=0.92,
        ),
        RetrievedClause(
            clause_id="3.2",
            section="SECTION 3 — THEFT",
            title="Theft Evidence & FIR Requirement",
            text="A theft claim must include FIR...",
            similarity_score=0.88,
        ),
    ]

    grounded = GroundingService.ground_results(retrieved)
    assert len(grounded) == 2
    assert grounded[0].clause_id == "2.1"
    assert "accidental damage" in grounded[0].reason.lower()
    assert grounded[1].clause_id == "3.2"
    assert "fir" in grounded[1].reason.lower()

    # Grounding reasons must NOT include adjudication decisions
    for g in grounded:
        assert "approve" not in g.reason.lower()
        assert "reject" not in g.reason.lower()
        assert "deny" not in g.reason.lower()


# ── 6. Policy Retriever Integration Tests (Mock Embeddings) ──────────────

def test_policy_retriever_end_to_end(tmp_path):
    """PolicyRetriever executes complete retrieval and grounding pipeline."""
    cache_file = tmp_path / "mock_policy_embeddings.json"
    embedder = MockEmbeddingService(dimension=32)
    retriever = PolicyRetriever(
        loader=PolicyClauseLoader(POLICY_JSON_PATH),
        embedder=embedder,
        cache_path=cache_file,
    )

    facts = [
        ExtractedFact(field_name="incident_type", value="accident", raw_value="accident", page_number=1),
        ExtractedFact(field_name="claimed_amount", value=78000, raw_value="78000", page_number=1),
    ]

    query, grounded = retriever.retrieve_relevant_clauses(facts, top_k=5)

    assert len(query) > 10
    assert len(grounded) == 5
    assert cache_file.exists()  # Cache should have been saved

    # Sorted by similarity descending
    scores = [g.similarity_score for g in grounded]
    assert scores == sorted(scores, reverse=True)


def test_policy_retriever_backward_compatibility(tmp_path):
    """PolicyRetriever.retrieve_clauses(ClaimFacts) returns PolicyClause list."""
    embedder = MockEmbeddingService(dimension=32)
    retriever = PolicyRetriever(
        loader=PolicyClauseLoader(POLICY_JSON_PATH),
        embedder=embedder,
        cache_path=tmp_path / "cache.json",
    )

    facts = ClaimFacts(vehicle_type="Car", claimed_amount=50000.0)
    clauses = retriever.retrieve_clauses(facts)

    assert len(clauses) == 5
    assert all(isinstance(c, PolicyClause) for c in clauses)


# ── 7. API Endpoint Tests (/api/retrieve-policy) ──────────────────────────

def test_retrieve_policy_endpoint_empty_payload():
    """POST /api/retrieve-policy with empty facts returns error response."""
    response = client.post("/api/retrieve-policy", json={"facts": []})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "No claim facts" in data["error"]


def test_retrieve_policy_endpoint_with_mock_cache(tmp_path, monkeypatch):
    """POST /api/retrieve-policy works cleanly when valid cache is present."""
    from src.retrieval import policy_retriever as pr_module

    # Pre-build a mock cache
    cache_path = tmp_path / "policy_embeddings.json"
    loader = PolicyClauseLoader(POLICY_JSON_PATH)
    clauses = loader.load_clauses()
    h = loader.compute_policy_hash()
    embedder = MockEmbeddingService(dimension=32)
    embeddings = embedder.embed_texts([f"{c.title} {c.text}" for c in clauses])

    index = VectorIndex()
    index.build(clauses, embeddings, h, "mock-model")
    index.save(cache_path)

    # Monkeypatch retriever default cache path and embedder
    orig_init = pr_module.PolicyRetriever.__init__

    def mock_init(self, *args, **kwargs):
        orig_init(
            self,
            loader=loader,
            embedder=embedder,
            cache_path=cache_path,
        )

    monkeypatch.setattr(pr_module.PolicyRetriever, "__init__", mock_init)

    payload = {
        "facts": [
            {"field_name": "incident_type", "value": "accident", "page_number": 1, "confidence": 1.0, "evidence_valid": True},
            {"field_name": "claimed_amount", "value": 78000, "page_number": 1, "confidence": 1.0, "evidence_valid": True},
        ],
        "top_k": 4,
    }

    response = client.post("/api/retrieve-policy", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert len(data["clauses"]) == 4
    assert "Accidental damage" in data["query"]
    assert all("clause_id" in c for c in data["clauses"])
    assert all("similarity_score" in c for c in data["clauses"])
    assert all("reason" in c for c in data["clauses"])

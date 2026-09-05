"""Build and cache Gemini embeddings for the ClaimLens Motor Policy.

Calculates policy hash, checks cache validity, generates dense embeddings
using the configured Gemini embedding model, and saves to local JSON index.

Usage:
    python scripts/build_policy_embeddings.py
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=BASE_DIR / ".env", override=False)
except ImportError:
    pass

from src.config import settings
from src.retrieval.policy_loader import PolicyClauseLoader
from src.retrieval.embedding_service import (
    EmbeddingService,
    GeminiNotConfiguredError,
    EmbeddingServiceError,
)
from src.retrieval.vector_index import VectorIndex, InvalidCacheError

CACHE_PATH = BASE_DIR / "data" / "policy" / "policy_embeddings.json"


def build_embeddings() -> int:
    print("=" * 50)
    print("ClaimLens Policy Embedding Builder")
    print("=" * 50)

    loader = PolicyClauseLoader()
    try:
        clauses = loader.load_clauses()
        policy_hash = loader.compute_policy_hash()
    except Exception as e:
        print(f"[FAIL] Error loading policy clauses: {e}")
        return 1

    model_name = settings.gemini_embedding_model
    print(f"Policy Clauses : {len(clauses)}")
    print(f"Policy Hash    : {policy_hash}")
    print(f"Embedding Model: {model_name}")
    print(f"Cache Path     : {CACHE_PATH}")
    print("-" * 50)

    # Check existing cache
    index = VectorIndex()
    if CACHE_PATH.exists():
        try:
            index.load(CACHE_PATH)
            if index.is_valid_for(policy_hash, model_name):
                print(f"[OK] Cache is already current ({len(clauses)} clauses indexed).")
                print(f"[OK] Embedding dimension: {index.dimension}")
                print("=" * 50)
                print("RESULT: SUCCESS (CACHE UP TO DATE)")
                return 0
            else:
                print("[INFO] Cache is outdated or model changed. Rebuilding...")
        except InvalidCacheError as e:
            print(f"[INFO] Cache invalid ({e}). Rebuilding...")

    # Validate Gemini API Key
    if not settings.gemini_configured:
        print("[FAIL] GEMINI_API_KEY is not configured in the environment.")
        print("Please set GEMINI_API_KEY to generate live policy embeddings.")
        return 1

    print("[INFO] Calling Gemini Embedding API to generate embeddings...")
    embedder = EmbeddingService()
    texts_to_embed = [
        f"{c.section}\n{c.title}\n{c.text}\nTags: {', '.join(c.tags)}"
        for c in clauses
    ]

    try:
        embeddings = embedder.embed_texts(texts_to_embed)
        print(f"[OK] Generated {len(embeddings)} embeddings.")
        if len(embeddings) != len(clauses):
            print(f"[FAIL] Embedding count mismatch: expected {len(clauses)} embeddings, got {len(embeddings)}.")
            return 1
    except GeminiNotConfiguredError as e:
        print(f"[FAIL] {e.message}")
        return 1
    except EmbeddingServiceError as e:
        print(f"[FAIL] Embedding generation error: {e.message}")
        return 1
    except Exception as e:
        print(f"[FAIL] Unexpected error: {e}")
        return 1

    # Build and save index
    try:
        index.build(clauses, embeddings, policy_hash, model_name)
        index.save(CACHE_PATH)
        print(f"[OK] Saved embeddings index to: {CACHE_PATH}")
        print(f"[OK] Index dimension: {index.dimension}")
        print("=" * 50)
        print("RESULT: SUCCESS")
        return 0
    except Exception as e:
        print(f"[FAIL] Error saving index: {e}")
        return 1


if __name__ == "__main__":
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(build_embeddings())

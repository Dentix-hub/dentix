from pathlib import Path
from unittest.mock import Mock, patch

from backend.rag.store import RealKnowledgeStore


def test_chromadb_is_embedded_and_uses_fixed_application_model():
    source = (Path(__file__).parents[1] / "rag" / "store.py").read_text(
        encoding="utf-8"
    )

    assert "chromadb.PersistentClient" in source
    assert "chromadb.HttpClient" not in source
    assert "SimpleRBACAuthorizationProvider" not in source
    assert "model_name='all-MiniLM-L6-v2'" in source


def test_caller_metadata_cannot_override_tenant_identity():
    collection = Mock()
    store = object.__new__(RealKnowledgeStore)
    store.collection = collection

    with patch("backend.rag.store.uuid.uuid4", return_value="document-id"):
        store.add(
            "clinic note",
            tenant_id=42,
            source="manual",
            metadata={"tenant_id": 99, "source": "untrusted", "category": "general"},
        )

    metadata = collection.add.call_args.kwargs["metadatas"][0]
    assert metadata["tenant_id"] == 42
    assert metadata["source"] == "manual"
    assert metadata["category"] == "general"

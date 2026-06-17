import pytest
from unittest.mock import patch

@pytest.fixture(autouse=True)
def mock_knowledge_store():
    """
    Autouse fixture to force MockKnowledgeStore and prevent any HuggingFace downloads or network calls.
    Returns a mock knowledge store with sensible empty defaults.
    """
    from backend.rag.store import MockKnowledgeStore
    mock_store = MockKnowledgeStore()
    
    # Ensure any unexpected similarity_search or insert_document methods return empty defaults
    if not hasattr(mock_store, "similarity_search"):
        mock_store.similarity_search = lambda *args, **kwargs: []
    if not hasattr(mock_store, "insert_document"):
        mock_store.insert_document = lambda *args, **kwargs: True
        
    with patch("backend.services.knowledge_service.knowledge_store", mock_store), \
         patch("backend.rag.store._get_store_instance", return_value=mock_store):
        yield mock_store

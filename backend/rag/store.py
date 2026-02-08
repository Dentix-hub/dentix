import os
import uuid
from typing import List, Dict, Optional, Any
from datetime import datetime

# Define persistence directory
PERSIST_DIRECTORY = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "rag_storage")

try:
    import chromadb
    from chromadb.utils import embedding_functions
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    print("WARNING: RAG dependencies (chromadb, sentence-transformers) not found. RAG features will be disabled.")

class KnowledgeStoreInterface:
    """Interface for KnowledgeStore to ensure consistency between Real and Mock implementations."""
    def add(self, text: str, tenant_id: int, source: str = "manual", metadata: Dict = None) -> str: pass
    def search(self, query: str, tenant_id: int, n_results: int = 2) -> List[Dict[str, Any]]: pass
    def list_all(self, tenant_id: int) -> List[Dict[str, Any]]: pass
    def delete(self, doc_id: str, tenant_id: int) -> bool: pass

class RealKnowledgeStore(KnowledgeStoreInterface):
    """
    Manages local vector database (ChromaDB) for RAG.
    Handles storage, retrieval, and management of clinic knowledge.
    """
    def __init__(self):
        # Ensure storage directory exists
        if not os.path.exists(PERSIST_DIRECTORY):
            os.makedirs(PERSIST_DIRECTORY)
            
        # Initialize Client
        self.client = chromadb.PersistentClient(path=PERSIST_DIRECTORY)
        
        # Use a lightweight, high-performance embedding model
        # all-MiniLM-L6-v2 is standard for RAG (fast CPU inference)
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        # Get or Create Collection
        self.collection = self.client.get_or_create_collection(
            name="clinic_knowledge",
            embedding_function=self.embedding_fn
        )

    def add(self, text: str, tenant_id: int, source: str = "manual", metadata: Dict = None) -> str:
        doc_id = str(uuid.uuid4())
        meta = {
            "tenant_id": tenant_id,
            "source": source,
            "created_at": datetime.now().isoformat()
        }
        if metadata:
            meta.update(metadata)
            
        self.collection.add(
            documents=[text],
            metadatas=[meta],
            ids=[doc_id]
        )
        return doc_id

    def search(self, query: str, tenant_id: int, n_results: int = 2) -> List[Dict[str, Any]]:
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where={"tenant_id": tenant_id}
        )
        formatted_results = []
        if results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                formatted_results.append({
                    "id": results["ids"][0][i],
                    "text": doc,
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if results["distances"] else 0
                })
        return formatted_results

    def list_all(self, tenant_id: int) -> List[Dict[str, Any]]:
        results = self.collection.get(where={"tenant_id": tenant_id})
        formatted_results = []
        if results["documents"]:
            for i, doc in enumerate(results["documents"]):
                formatted_results.append({
                    "id": results["ids"][i],
                    "text": doc,
                    "metadata": results["metadatas"][i]
                })
        return formatted_results

    def delete(self, doc_id: str, tenant_id: int) -> bool:
        existing = self.collection.get(ids=[doc_id], where={"tenant_id": tenant_id})
        if not existing["ids"]:
            return False
        self.collection.delete(ids=[doc_id])
        return True

class MockKnowledgeStore(KnowledgeStoreInterface):
    """Fallback store when RAG dependencies are missing."""
    def add(self, text: str, tenant_id: int, source: str = "manual", metadata: Dict = None) -> str:
        return "mock-id"
    
    def search(self, query: str, tenant_id: int, n_results: int = 2) -> List[Dict[str, Any]]:
        return []
        
    def list_all(self, tenant_id: int) -> List[Dict[str, Any]]:
        return []
        
    def delete(self, doc_id: str, tenant_id: int) -> bool:
        return True

# Singleton Factory
if RAG_AVAILABLE:
    knowledge_store = RealKnowledgeStore()
else:
    knowledge_store = MockKnowledgeStore()


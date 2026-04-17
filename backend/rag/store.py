import logging
logger = logging.getLogger(__name__)
import os
import uuid
from typing import List, Dict, Any
from datetime import datetime
PERSIST_DIRECTORY = os.path.join(os.path.dirname(os.path.dirname(os.path.
    dirname(__file__))), 'rag_storage')
try:
    import chromadb
    from chromadb.utils import embedding_functions
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    logger.info(
        'WARNING: RAG dependencies (chromadb, sentence-transformers) not found. RAG features will be disabled.'
        )


class KnowledgeStoreInterface:
    """Interface for KnowledgeStore to ensure consistency between Real and Mock implementations."""

    def add(self, text: str, tenant_id: int, source: str='manual', metadata:
        Dict=None) ->str:
        pass

    def search(self, query: str, tenant_id: int, n_results: int=2) ->List[Dict
        [str, Any]]:
        pass

    def list_all(self, tenant_id: int) ->List[Dict[str, Any]]:
        pass

    def delete(self, doc_id: str, tenant_id: int) ->bool:
        pass


class RealKnowledgeStore(KnowledgeStoreInterface):
    """
    Manages local vector database (ChromaDB) for RAG.
    Handles storage, retrieval, and management of clinic knowledge.
    """

    def __init__(self):
        if not os.path.exists(PERSIST_DIRECTORY):
            os.makedirs(PERSIST_DIRECTORY)
        self.client = chromadb.PersistentClient(path=PERSIST_DIRECTORY)
        self.embedding_fn = (embedding_functions.
            SentenceTransformerEmbeddingFunction(model_name='all-MiniLM-L6-v2')
            )
        self.collection = self.client.get_or_create_collection(name=
            'clinic_knowledge', embedding_function=self.embedding_fn)

    def add(self, text: str, tenant_id: int, source: str='manual', metadata:
        Dict=None) ->str:
        doc_id = str(uuid.uuid4())
        meta = {'tenant_id': tenant_id, 'source': source, 'created_at':
            datetime.now().isoformat()}
        if metadata:
            meta.update(metadata)
        self.collection.add(documents=[text], metadatas=[meta], ids=[doc_id])
        return doc_id

    def search(self, query: str, tenant_id: int, n_results: int=2) ->List[Dict
        [str, Any]]:
        results = self.collection.query(query_texts=[query], n_results=
            n_results, where={'tenant_id': tenant_id})
        formatted_results = []
        if results['documents']:
            for i, doc in enumerate(results['documents'][0]):
                formatted_results.append({'id': results['ids'][0][i],
                    'text': doc, 'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if results[
                    'distances'] else 0})
        return formatted_results

    def list_all(self, tenant_id: int) ->List[Dict[str, Any]]:
        results = self.collection.get(where={'tenant_id': tenant_id})
        formatted_results = []
        if results['documents']:
            for i, doc in enumerate(results['documents']):
                formatted_results.append({'id': results['ids'][i], 'text':
                    doc, 'metadata': results['metadatas'][i]})
        return formatted_results

    def delete(self, doc_id: str, tenant_id: int) ->bool:
        existing = self.collection.get(ids=[doc_id], where={'tenant_id':
            tenant_id})
        if not existing['ids']:
            return False
        self.collection.delete(ids=[doc_id])
        return True


class MockKnowledgeStore(KnowledgeStoreInterface):
    """Fallback store when RAG dependencies are missing."""

    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}

    def add(self, text: str, tenant_id: int, source: str='manual', metadata:
        Dict=None) ->str:
        doc_id = f'mock-{uuid.uuid4().hex[:8]}'
        self._store[doc_id] = {
            'text': text, 'tenant_id': tenant_id,
            'metadata': metadata or {}, 'source': source,
        }
        return doc_id

    def search(self, query: str, tenant_id: int, n_results: int=2) ->List[Dict
        [str, Any]]:
        return [
            {'id': k, 'text': v['text'], 'metadata': v['metadata'], 'distance': 0}
            for k, v in self._store.items() if v['tenant_id'] == tenant_id
        ][:n_results]

    def list_all(self, tenant_id: int) ->List[Dict[str, Any]]:
        return [
            {'id': k, 'text': v['text'], 'metadata': v['metadata']}
            for k, v in self._store.items() if v['tenant_id'] == tenant_id
        ]

    def delete(self, doc_id: str, tenant_id: int) ->bool:
        if doc_id in self._store and self._store[doc_id]['tenant_id'] == tenant_id:
            del self._store[doc_id]
            return True
        return False


_knowledge_store_instance = None


def _get_store_instance():
    """Lazy initialization for knowledge store."""
    global _knowledge_store_instance
    if _knowledge_store_instance is None:
        if RAG_AVAILABLE:
            _knowledge_store_instance = RealKnowledgeStore()
        else:
            _knowledge_store_instance = MockKnowledgeStore()
    return _knowledge_store_instance


class _KnowledgeStoreProxy:
    """Proxy that lazily initializes the real store on first use."""

    def __getattr__(self, name):
        return getattr(_get_store_instance(), name)


knowledge_store = _KnowledgeStoreProxy()

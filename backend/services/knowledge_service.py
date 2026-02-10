from typing import Dict, Any, List
from backend.rag.store import knowledge_store


class KnowledgeService:
    """
    Service for managing RAG knowledge base interactions.
    """

    def __init__(self, tenant_id: int):
        self.tenant_id = tenant_id

    def learn_info(self, text: str, category: str = "general") -> str:
        """Add info to knowledge base."""
        doc_id = knowledge_store.add(
            text=text, tenant_id=self.tenant_id, metadata={"category": category}
        )
        return doc_id

    def list_knowledge(self) -> List[Dict[str, Any]]:
        """List all knowledge for tenant."""
        return knowledge_store.list_all(self.tenant_id)

    def forget_info(self, item_id: str) -> bool:
        """Delete info from knowledge base."""
        return knowledge_store.delete(item_id, self.tenant_id)

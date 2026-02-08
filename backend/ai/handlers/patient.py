from typing import Dict, List, Any
from .base import BaseHandler
from backend.services.patient_service import PatientService
from backend.ai.adapters.patient_adapter import PatientToolAdapter

class PatientHandler(BaseHandler):
    """
    Handles patient tools via Adapter and Service.
    No direct DB access allowed here.
    """
    def __init__(self, db, user):
        super().__init__(db, user)
        self.service = PatientService(db, self.tenant_id)
        self.adapter = PatientToolAdapter(self.service)

    async def get_patient_file(self, params: Dict) -> Dict:
        """Get patient file by name."""
        return await self.adapter.get_patient_file(params)

    async def search_patients(self, params: Dict) -> Dict:
        """Search patients."""
        return await self.adapter.search_patients(params)

    async def get_patients_with_balance(self, params: Dict) -> Dict:
        """Get all patients with outstanding balance."""
        return await self.adapter.get_patients_with_balance(params)

    async def summarize_patient(self, params: Dict) -> Dict:
        """Get patient summary for AI summarization."""
        return await self.adapter.summarize_patient(params)

    async def create_patient(self, params: Dict) -> Dict:
        """Create a new patient record."""
        return await self.adapter.create_patient(params)

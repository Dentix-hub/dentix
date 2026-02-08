import sys
import os
sys.path.append(os.getcwd())

from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models import User
from backend.routers.analytics_ai import get_detailed_analytics

import asyncio
from backend.services.ai_service import AIService
from backend.routers.analytics_ai import get_detailed_analytics, ClinicStats

def test_crash():
    db = SessionLocal()
    try:
        # Get a user (tenant 1)
        user = db.query(User).first()
        if not user:
             print("No user found in DB.")
             return

        print(f"User: {user.username}, Tenant: {user.tenant_id}")
        
        # 1. Test get_detailed_analytics (Already passed, but good to keep)
        print("\n--- Testing get_detailed_analytics ---")
        details = get_detailed_analytics(db, user.tenant_id)
        print("Details retrieved successfully.")
        
        # 2. Test AIService.analyze_direct
        print("\n--- Testing AIService.analyze_direct ---")
        
        # Define mock stats
        stats = ClinicStats(
            revenue=10000.0,
            breakdown={"expenses": 2000.0, "lab_costs": 500.0, "material_costs": 1000.0},
            total_costs=3500.0,
            net_profit=6500.0,
            margin_percent=65.0
        )
        
        # Initialize Service
        service = AIService(db, user)
        
        # Build prompt (mimicking router logic)
        prompt = f"""
        Act as a senior CLINIC STRATEGIST & CFO. Analyze the following data:
        - Revenue: ${stats.revenue}
        - Net Profit: ${stats.net_profit}
        
        {details}
        """
        
        # Run async function
        try:
            response = asyncio.run(service.analyze_direct(prompt))
            print("\nAI Response Success:")
            print(response.message[:200] + "...")
        except Exception as e:
            print(f"\nCRASH in service.analyze_direct: {e}")
            import traceback
            traceback.print_exc()

    finally:
        db.close()

if __name__ == "__main__":
    test_crash()

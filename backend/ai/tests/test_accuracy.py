"""
AI Accuracy Evaluation Script
Runs the AI Agent against the Golden Dataset and calculates accuracy.
"""
import asyncio
import json
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from backend.ai.agent.core import get_agent
from backend.ai.tools.security import get_tool_risk
from backend.models import User

# Mock User and DB for Agent Context
class MockUser:
    id = 1
    username = "admin"
    tenant_id = 1
    full_name = "System Admin"

async def run_evals():
    print("🚀 Starting AI Evaluation...")
    
    # Load Golden Dataset
    with open("golden_dataset.json", "r", encoding="utf-8") as f:
        dataset = json.load(f)
    
    agent = get_agent()
    # Mock history
    history = [] 
    
    correct = 0
    total = len(dataset)
    
    print(f"📋 Loaded {total} test cases.\n")
    
    for i, case in enumerate(dataset):
        input_text = case["input"]
        expected_tool = case["expected_tool"]
        expected_risk = case.get("risk_level")
        
        print(f"[{i+1}/{total}] Input: {input_text}...", end=" ")
        
        try:
            # Process with Agent
            result = await agent.process(
                user_input=input_text,
                history=history,
                tenant_id=1,
                last_entity="Test Patient"
            )
            
            tool_used = result.get("tool")
            risk_level = get_tool_risk(tool_used) if tool_used else "UNKNOWN"
            
            # Check correctness
            tool_match = (tool_used == expected_tool)
            risk_match = (risk_level == expected_risk) if expected_risk else True
            
            if tool_match:
                print(f"✅ PASS ({tool_used})")
                correct += 1
            else:
                print(f"❌ FAIL (Got: {tool_used}, Expected: {expected_tool})")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            
    accuracy = (correct / total) * 100
    print(f"\n📊 Final Accuracy: {accuracy:.2f}%")
    
    if accuracy >= 90:
        print("✅ PASSED: System is stable.")
        sys.exit(0)
    else:
        print("❌ FAILED: Accuracy below 90%.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_evals())

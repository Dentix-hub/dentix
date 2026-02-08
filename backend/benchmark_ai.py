
import time
import asyncio
import os
from unittest.mock import MagicMock

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set explicit Start Time
start_time = time.time()

print("1. Loading Modules...")
from backend.ai.agent.core import get_agent
from backend.routers.ai import ToolExecutor
from backend.models import User

print(f"   [Done] Module Load Time: {time.time() - start_time:.4f}s")

async def benchmark():
    print("\n2. Benchmarking Components...")
    
    mock_user = User(id=1, tenant_id=1, username="bench")
    mock_db = MagicMock()
    
    # Measure ToolExecutor Init
    t0 = time.time()
    executor = ToolExecutor(mock_db, mock_user)
    t1 = time.time()
    print(f"   - ToolExecutor Init: {t1 - t0:.4f}s")
    
    # Measure Handler Access (Lazy Loading Check)
    t0 = time.time()
    _ = executor.patient
    _ = executor.clinical
    t1 = time.time()
    print(f"   - Handler Access: {t1 - t0:.4f}s")
    
    # Measure RAG Search (via Agent internal method if accessible, or public)
    # RAG is inside agent.process, hard to isolate without modifying core.
    # We will simulate a full process call but mock the LLM to isolate local overhead.
    
    agent = get_agent()
    # Mock the LLM client to return instantly
    agent._call_llm_safe = MagicMock(return_value=MagicMock(choices=[MagicMock(message=MagicMock(content='{"tool": "response", "message": "fast"}'))]))
    
    print("\n3. Benchmarking Agent Process (Local Only)...")
    t0 = time.time()
    # First Run (Cold)
    await agent.process("Hello", tenant_id=1)
    t1 = time.time()
    print(f"   - Cold Start Process: {t1 - t0:.4f}s")
    
    t0 = time.time()
    # Second Run (Warm)
    await agent.process("Hello again", tenant_id=1)
    t1 = time.time()
    print(f"   - Warm Process: {t1 - t0:.4f}s")

if __name__ == "__main__":
    asyncio.run(benchmark())

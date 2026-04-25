import asyncio
import os
import sys
import json
sys.path.append(os.getcwd())

import logging
logging.basicConfig(level=logging.DEBUG)

from backend.ai.agent.core import get_agent

async def main():
    agent = get_agent()
    try:
        res = await agent.process("مين حاجز النهاردة", tenant_id=1, user_id=1)
        with open("test_ai_output.json", "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)

        if res.get("is_soft_error") or res.get("error"):
            with open("test_ai_output.txt", "w", encoding="utf-8") as f:
                f.write("ERROR_FINAL: Payload error indicator present")
            print("Payload error! Written to test_ai_output.txt")
            sys.exit(1)

        print("Success! Wrote to test_ai_output.json")
    except Exception as e:
        with open("test_ai_output.txt", "w", encoding="utf-8") as f:
            f.write(f"ERROR_FINAL: {type(e)} {str(e)}")
        print("Error written to test_ai_output.txt")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

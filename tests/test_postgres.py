#!/usr/bin/env python3
"""Quick test for memU with PostgreSQL"""

import asyncio
import json
import tempfile
from pathlib import Path
from memu.app import MemoryService
from meow_agent.config import settings


async def main():
    print("=" * 60)
    print("Testing memU with PostgreSQL")
    print("=" * 60)
    print(f"\nDATABASE_URL: {settings.database_url}")
    print(f"Model: {settings.dashscope_model}\n")
    
    # Initialize
    print("[1/2] Initializing memU with PostgreSQL...")
    try:
        service = MemoryService(
            llm_profiles={
                "default": {
                    "api_key": settings.dashscope_api_key,
                    "base_url": settings.dashscope_base_url,
                    "chat_model": settings.dashscope_model,
                },
                "embedding": {
                    "api_key": settings.embedding_api_key,
                    "base_url": settings.embedding_base_url,
                    "embed_model": settings.embedding_model,
                }
            },
            database_config={
                "metadata_store": {
                    "provider": "postgres",
                    "dsn": settings.database_url,
                }
            }
        )
        print("✅ Initialized successfully\n")
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Memorize
    print("[2/2] Testing memorize...")
    conversation = {
        "messages": [
            {"role": "user", "content": "你好，我叫肥东"},
            {"role": "assistant", "content": "你好肥东！"},
            {"role": "user", "content": "我喜欢吃提拉米苏"},
            {"role": "assistant", "content": "好的，记住了！"},
        ]
    }
    
    temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump(conversation, temp_file, ensure_ascii=False)
    temp_file.close()
    
    try:
        result = await service.memorize(
            resource_url=temp_file.name,
            modality="conversation",
            user={"user_id": "test_postgres"}
        )
        
        items = result.get('items', [])
        print(f"✅ Memorized {len(items)} items:")
        for i, item in enumerate(items, 1):
            content = item.get('content', item.get('summary', ''))
            print(f"   {i}. [{item.get('memory_type')}] {content}")
        
        print("\n" + "=" * 60)
        print("🎉 SUCCESS! PostgreSQL persistence configured!")
        print("=" * 60)
        print("\nYou can now:")
        print("1. Run: uv run main.py")
        print("2. Your memories will persist across restarts!")
        
    except Exception as e:
        print(f"❌ Memorize failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        Path(temp_file.name).unlink()


if __name__ == "__main__":
    asyncio.run(main())

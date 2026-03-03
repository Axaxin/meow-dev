"""Minimal test for memU with LMStudio embedding."""

import asyncio
import json
import tempfile
from pathlib import Path
from memu.app import MemoryService
from meow_agent.config import settings


async def test_memu_minimal():
    """Test memU with minimal configuration."""
    
    print("=" * 60)
    print("Testing memU with LMStudio embedding")
    print("=" * 60)
    print(f"\nConfiguration:")
    print(f"  Chat: {settings.dashscope_model}")
    print(f"  Embed: {settings.embedding_model}")
    print(f"  Embed URL: {settings.embedding_base_url}")
    
    # Initialize memU
    print("\n[1/3] Initializing memU...")
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
            }
        )
        print("✅ memU initialized")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return
    
    # Create test conversation
    conversation = {
        "messages": [
            {"role": "user", "content": "你好，我叫肥东"},
            {"role": "assistant", "content": "你好肥东！"},
        ]
    }
    
    # Save to temp file
    temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump(conversation, temp_file, ensure_ascii=False)
    temp_file.close()
    
    # Test memorize
    print("\n[2/3] Testing memorize...")
    print("  (This may take 10-30 seconds...)")
    try:
        result = await asyncio.wait_for(
            service.memorize(
                resource_url=temp_file.name,
                modality="conversation",
                user={"user_id": "test"}
            ),
            timeout=60.0
        )
        
        items = result.get('items', [])
        resource_id = result.get('resource', {}).get('id', '')
        
        print(f"✅ Memorized!")
        print(f"  Resource ID: {resource_id}")
        print(f"  Items extracted: {len(items)}")
        
        if items:
            print("\n  Extracted items:")
            for i, item in enumerate(items[:5], 1):
                content = item.get('content', item.get('summary', ''))[:60]
                mem_type = item.get('memory_type', 'unknown')
                print(f"    {i}. [{mem_type}] {content}...")
        
    except asyncio.TimeoutError:
        print("❌ Memorize timeout (>60s)")
        print("   LLM may be slow or not responding")
    except Exception as e:
        print(f"❌ Memorize failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        Path(temp_file.name).unlink(missing_ok=True)
    
    # Test retrieve
    print("\n[3/3] Testing retrieve...")
    try:
        result = await asyncio.wait_for(
            service.retrieve(
                queries=[{"role": "user", "content": {"text": "用户叫什么名字"}}],
                where={"user_id": "test"}
            ),
            timeout=10.0
        )
        
        items = result.get('items', [])
        print(f"✅ Retrieved!")
        print(f"  Items found: {len(items)}")
        
        if items:
            print("\n  Retrieved items:")
            for i, item in enumerate(items[:3], 1):
                content = item.get('content', item.get('summary', ''))[:60]
                print(f"    {i}. {content}...")
        
    except asyncio.TimeoutError:
        print("❌ Retrieve timeout (>10s)")
    except Exception as e:
        print(f"❌ Retrieve failed: {e}")
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_memu_minimal())

"""Test the API with a real task prompt."""
import asyncio
import json
import os
import sys

import httpx


async def test_real_task():
    """Test API with real task prompt."""
    base_url = os.getenv("API_URL", "http://localhost:8000")
    
    task_prompt = "Go to ProductHunt, find top 5 trending AI products, and get a small summary on them"
    
    print("🚀 Testing Browserbase Orchestrator API")
    print(f"   API URL: {base_url}")
    print(f"   Task: {task_prompt}\n")
    print("=" * 80)
    print()
    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream(
                "POST",
                f"{base_url}/api/run",
                json={
                    "task_prompt": task_prompt,
                    "max_steps": 50,  # Allow more steps for complex task
                },
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    print(f"❌ Request failed: {response.status_code}")
                    print(f"   Response: {error_text.decode()}")
                    return False
                
                print("📡 Streaming live updates...\n")
                step_count = 0
                reasoning_count = 0
                screenshots_captured = 0
                
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    
                    # Handle SSE format
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            event_type = data.get("type", "unknown")
                            
                            if event_type == "reasoning":
                                reasoning_count += 1
                                print(f"🤔 [Step {data.get('step', '?')}] LLM Reasoning:")
                                print(f"   {data.get('reasoning', 'No reasoning')}")
                                print(f"   → Planning to use: {data.get('tool', 'unknown')}")
                                print()
                            
                            elif event_type == "step":
                                step_count += 1
                                tool = data.get("tool", "unknown")
                                result = data.get("result", "")
                                
                                print(f"✅ [Step {data.get('step', '?')}] Completed: {tool}")
                                if result:
                                    # Show first 200 chars of result
                                    result_preview = result[:200] + "..." if len(result) > 200 else result
                                    print(f"   Result: {result_preview}")
                                
                                if data.get("screenshot"):
                                    screenshots_captured += 1
                                    print(f"   📸 Screenshot captured ({len(data.get('screenshot', ''))} bytes)")
                                
                                if data.get("flow_state"):
                                    actions = data["flow_state"].get("actions", [])
                                    session_id = data["flow_state"].get("browserbaseSessionId", "none")
                                    starting_url = data["flow_state"].get("startingUrl", "none")
                                    print(f"   📊 FlowState: {len(actions)} actions, session: {session_id[:20]}...")
                                    if starting_url != "none":
                                        print(f"   🌐 Starting URL: {starting_url}")
                                
                                print()
                            
                            elif event_type == "complete":
                                print(f"\n🎉 Task marked as complete!")
                                print(f"   Summary: {data.get('summary', 'No summary')}")
                                print()
                            
                            elif event_type == "error":
                                print(f"\n❌ Error occurred:")
                                print(f"   {data.get('message', 'Unknown error')}")
                                print()
                                return False
                            
                            elif event_type == "final":
                                print("\n" + "=" * 80)
                                print("✅ TASK COMPLETED")
                                print("=" * 80)
                                print(f"   Cache Key: {data.get('cache_key', 'unknown')}")
                                print(f"   Summary: {data.get('summary', 'No summary')}")
                                print(f"   Total Steps: {data.get('total_steps', 0)}")
                                print(f"   Reasoning Events: {reasoning_count}")
                                print(f"   Steps Executed: {step_count}")
                                print(f"   Screenshots Captured: {screenshots_captured}")
                                
                                if data.get("flow_state"):
                                    flow_state = data["flow_state"]
                                    print(f"\n   Final FlowState:")
                                    print(f"   - Actions: {len(flow_state.get('actions', []))}")
                                    print(f"   - Session ID: {flow_state.get('browserbaseSessionId', 'none')[:30]}...")
                                    print(f"   - Starting URL: {flow_state.get('startingUrl', 'none')}")
                                
                                print()
                                return True
                        
                        except json.JSONDecodeError as e:
                            print(f"⚠️  Failed to parse JSON: {line[:100]}")
                            continue
                    
                    elif line.startswith("event: "):
                        event = line[7:].strip()
                        if event == "error":
                            print(f"\n❌ Server error event")
                            return False
                
                # If we get here, stream ended without final message
                print(f"\n⚠️  Stream ended. Processed {step_count} steps.")
                return step_count > 0
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Test cancelled by user")
        return False
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main function."""
    # Check if server is running
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:8000/")
            if response.status_code != 200:
                print("❌ API server is not responding correctly")
                print("   Start the server with: python api_server.py")
                sys.exit(1)
    except Exception:
        print("❌ API server is not running")
        print("   Start the server with: python api_server.py")
        sys.exit(1)
    
    success = await test_real_task()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())



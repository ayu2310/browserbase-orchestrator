"""Test full flow: execute task, confirm replay, and capture all responses with images."""
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

import httpx


async def test_full_flow():
    """Test complete flow: execute → confirm → replay → clear."""
    api_url = "https://browserbase-orchestrator-api.onrender.com"
    
    # Complex task
    task_prompt = "Go to Hacker News (news.ycombinator.com), find the top 3 stories, extract their titles, URLs, and point counts"
    
    print("🚀 Testing Full Flow")
    print("=" * 80)
    print(f"API URL: {api_url}")
    print(f"Task: {task_prompt}")
    print("=" * 80)
    print()
    
    # Create output directory
    output_dir = Path("test_output")
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"full_flow_test_{timestamp}.json"
    html_file = output_dir / f"full_flow_test_{timestamp}.html"
    
    all_responses = {
        "task": task_prompt,
        "timestamp": timestamp,
        "execution": {
            "events": [],
            "screenshots": [],
            "flow_state": None,
            "cache_key": None,
        },
        "replay": {
            "events": [],
            "screenshots": [],
            "flow_state": None,
        },
    }
    
    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            # ========== STEP 1: Execute Task ==========
            print("📡 Step 1: Executing task...")
            print("-" * 80)
            
            cache_key = None
            confirmation_received = False
            
            async with client.stream(
                "POST",
                f"{api_url}/api/run",
                json={
                    "task_prompt": task_prompt,
                    "max_steps": 30,
                },
                headers={"Accept": "text/event-stream"},
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    print(f"❌ Request failed: {response.status_code}")
                    print(f"Response: {error_text.decode()}")
                    return False
                
                print("✅ Connected! Streaming execution updates...\n")
                
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            event_type = data.get("type", "unknown")
                            
                            # Store event
                            event_data = {
                                "type": event_type,
                                "timestamp": datetime.now().isoformat(),
                                "data": data,
                            }
                            all_responses["execution"]["events"].append(event_data)
                            
                            if event_type == "reasoning":
                                print(f"🤔 [Step {data.get('step', '?')}] {data.get('reasoning', '')[:100]}...")
                            
                            elif event_type == "step":
                                tool = data.get("tool", "unknown")
                                print(f"✅ [Step {data.get('step', '?')}] {tool}")
                                
                                # Store screenshot if available
                                if data.get("screenshot"):
                                    screenshot_info = {
                                        "step": data.get("step"),
                                        "tool": tool,
                                        "screenshot": data.get("screenshot"),
                                        "description": f"Step {data.get('step')}: {tool}",
                                    }
                                    all_responses["execution"]["screenshots"].append(screenshot_info)
                                    print(f"   📸 Screenshot captured")
                                
                                # Store flowState
                                if data.get("flow_state"):
                                    all_responses["execution"]["flow_state"] = data["flow_state"]
                            
                            elif event_type == "final":
                                cache_key = data.get("cache_key")
                                all_responses["execution"]["cache_key"] = cache_key
                                all_responses["execution"]["flow_state"] = data.get("flow_state")
                                print(f"\n🎉 Task completed!")
                                print(f"   Cache Key: {cache_key}")
                                print(f"   Summary: {data.get('summary', '')[:200]}")
                                print(f"   Total Steps: {data.get('total_steps', 0)}")
                                # Don't break, wait for confirmation_required
                            
                            elif event_type == "confirmation_required":
                                confirmation_received = True
                                if not cache_key:
                                    cache_key = data.get("cache_key")
                                all_responses["execution"]["cache_key"] = cache_key
                                print(f"\n⏳ Confirmation required for replay")
                                print(f"   Cache Key: {cache_key}")
                                print(f"   Message: {data.get('message', '')}")
                                # Continue to receive any remaining events, then break
                            
                            elif event_type == "done":
                                # Stream ended
                                break
                            
                            elif event_type == "error":
                                print(f"\n❌ Error: {data.get('message', 'Unknown error')}")
                                return False
                        
                        except json.JSONDecodeError as e:
                            print(f"⚠️  Failed to parse JSON: {line[:100]}")
                            continue
            
            if not cache_key:
                print("\n⚠️  No cache_key received from execution")
                return False
            
            if not confirmation_received:
                print("\n⚠️  No confirmation_required event received, but proceeding with cache_key from final event")
                print(f"   Using cache_key: {cache_key}")
            
            # ========== STEP 2: Accept and Replay ==========
            print("\n" + "=" * 80)
            print("📡 Step 2: Accepting replay and executing deterministically...")
            print("-" * 80)
            
            # Use flowState from execution if available, otherwise use cache_key
            replay_payload = {"cache_key": cache_key}
            if all_responses["execution"].get("flow_state"):
                replay_payload["flow_state"] = all_responses["execution"]["flow_state"]
            
            async with client.stream(
                "POST",
                f"{api_url}/api/replay",
                json=replay_payload,
                headers={"Accept": "text/event-stream"},
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    print(f"❌ Replay request failed: {response.status_code}")
                    print(f"Response: {error_text.decode()}")
                    return False
                
                print("✅ Replay started! Streaming updates...\n")
                
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            event_type = data.get("type", "unknown")
                            
                            # Store event
                            event_data = {
                                "type": event_type,
                                "timestamp": datetime.now().isoformat(),
                                "data": data,
                            }
                            all_responses["replay"]["events"].append(event_data)
                            
                            if event_type == "replay_start":
                                print(f"🚀 {data.get('message', 'Replay started')}")
                            
                            elif event_type == "replay_action":
                                idx = data.get("action_index", "?")
                                total = data.get("total_actions", "?")
                                desc = data.get("description", "Unknown action")
                                print(f"   ▶️  [{idx}/{total}] {desc}")
                            
                            elif event_type == "replay_screenshot":
                                screenshot_info = {
                                    "message": data.get("message", "Screenshot"),
                                    "screenshot": data.get("screenshot"),
                                }
                                all_responses["replay"]["screenshots"].append(screenshot_info)
                                print(f"   📸 {data.get('message', 'Screenshot captured')}")
                            
                            elif event_type == "replay_complete":
                                all_responses["replay"]["flow_state"] = data.get("flow_state")
                                print(f"\n✅ Replay completed!")
                                print(f"   Summary: {data.get('summary', '')[:200]}")
                                break
                            
                            elif event_type == "error":
                                print(f"\n❌ Replay error: {data.get('message', 'Unknown error')}")
                                return False
                        
                        except json.JSONDecodeError as e:
                            print(f"⚠️  Failed to parse JSON: {line[:100]}")
                            continue
            
            # ========== STEP 3: Clear State ==========
            print("\n" + "=" * 80)
            print("📡 Step 3: Clearing state...")
            print("-" * 80)
            
            clear_response = await client.post(f"{api_url}/api/clear")
            if clear_response.status_code == 200:
                clear_data = clear_response.json()
                print(f"✅ {clear_data.get('message', 'State cleared')}")
            else:
                print(f"⚠️  Clear failed: {clear_response.status_code}")
            
            # ========== Save Results ==========
            print("\n" + "=" * 80)
            print("💾 Saving results...")
            print("-" * 80)
            
            # Save JSON
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(all_responses, f, indent=2, default=str)
            print(f"✅ JSON saved: {output_file}")
            
            # Create HTML viewer
            html_content = create_html_viewer(all_responses)
            with open(html_file, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"✅ HTML viewer saved: {html_file}")
            print(f"\n📂 Open {html_file} in your browser to view screenshots!")
            
            print("\n" + "=" * 80)
            print("✅ Full flow test completed successfully!")
            print("=" * 80)
            
            return True
    
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_html_viewer(responses: dict) -> str:
    """Create HTML viewer with screenshots."""
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Full Flow Test Results - {responses['timestamp']}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .section {{
            background: white;
            margin: 20px 0;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1, h2 {{
            color: #333;
        }}
        .event {{
            margin: 10px 0;
            padding: 10px;
            background: #f9f9f9;
            border-left: 3px solid #4CAF50;
            border-radius: 4px;
        }}
        .screenshot {{
            margin: 20px 0;
            padding: 15px;
            background: #fff;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
        .screenshot img {{
            max-width: 100%;
            height: auto;
            border: 1px solid #ccc;
            border-radius: 4px;
        }}
        .screenshot-info {{
            margin-top: 10px;
            color: #666;
            font-size: 0.9em;
        }}
        .timestamp {{
            color: #999;
            font-size: 0.8em;
        }}
        pre {{
            background: #f4f4f4;
            padding: 10px;
            border-radius: 4px;
            overflow-x: auto;
        }}
    </style>
</head>
<body>
    <h1>Full Flow Test Results</h1>
    <p class="timestamp">Timestamp: {responses['timestamp']}</p>
    <p><strong>Task:</strong> {responses['task']}</p>
    
    <div class="section">
        <h2>Execution Phase</h2>
        <p><strong>Cache Key:</strong> {responses['execution'].get('cache_key', 'N/A')}</p>
        <p><strong>Total Events:</strong> {len(responses['execution']['events'])}</p>
        <p><strong>Screenshots:</strong> {len(responses['execution']['screenshots'])}</p>
        
        <h3>Events</h3>
"""
    
    for event in responses['execution']['events']:
        html += f"""
        <div class="event">
            <strong>{event['type']}</strong> <span class="timestamp">({event['timestamp']})</span>
            <pre>{json.dumps(event['data'], indent=2, default=str)[:500]}</pre>
        </div>
"""
    
    html += """
        <h3>Screenshots</h3>
"""
    
    for i, screenshot in enumerate(responses['execution']['screenshots']):
        html += f"""
        <div class="screenshot">
            <div class="screenshot-info">
                <strong>Screenshot {i+1}:</strong> {screenshot.get('description', 'N/A')}
            </div>
            <img src="{screenshot.get('screenshot', '')}" alt="Screenshot {i+1}" />
        </div>
"""
    
    html += """
    </div>
    
    <div class="section">
        <h2>Replay Phase</h2>
        <p><strong>Total Events:</strong> """ + str(len(responses['replay']['events'])) + """</p>
        <p><strong>Screenshots:</strong> """ + str(len(responses['replay']['screenshots'])) + """</p>
        
        <h3>Events</h3>
"""
    
    for event in responses['replay']['events']:
        html += f"""
        <div class="event">
            <strong>{event['type']}</strong> <span class="timestamp">({event['timestamp']})</span>
            <pre>{json.dumps(event['data'], indent=2, default=str)[:500]}</pre>
        </div>
"""
    
    html += """
        <h3>Screenshots</h3>
"""
    
    for i, screenshot in enumerate(responses['replay']['screenshots']):
        html += f"""
        <div class="screenshot">
            <div class="screenshot-info">
                <strong>Screenshot {i+1}:</strong> {screenshot.get('message', 'N/A')}
            </div>
            <img src="{screenshot.get('screenshot', '')}" alt="Replay Screenshot {i+1}" />
        </div>
"""
    
    html += """
    </div>
    
    <div class="section">
        <h2>Flow State (Execution)</h2>
        <pre>""" + json.dumps(responses['execution'].get('flow_state'), indent=2, default=str) + """</pre>
    </div>
    
    <div class="section">
        <h2>Flow State (Replay)</h2>
        <pre>""" + json.dumps(responses['replay'].get('flow_state'), indent=2, default=str) + """</pre>
    </div>
    
</body>
</html>
"""
    
    return html


async def main():
    """Main function."""
    print("🧪 Full Flow Test - Execute → Replay → Clear")
    print("   This will test the complete workflow with screenshots")
    print()
    
    success = await test_full_flow()
    
    if success:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Tests completed with issues")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())


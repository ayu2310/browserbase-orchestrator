"""FastAPI server with SSE streaming for Browserbase orchestrator."""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from agent.orchestrator import OrchestratorAgent
from config import validate_config
from database import init_database

app = FastAPI(title="Browserbase Orchestrator API", version="1.0.0")

# CORS middleware for UI access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your UI domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    try:
        init_database()
        validate_config()
        print("✅ API server initialized successfully")
    except ValueError as e:
        print(f"⚠️  Configuration warning: {e}")
        print("   API will still start but may fail on requests")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "browserbase-orchestrator"}


@app.post("/api/run")
async def run_task(request: dict):
    """Run an autonomous browser automation task with live streaming."""
    task_prompt = request.get("task_prompt", "").strip()
    cache_key = request.get("cache_key")
    max_steps = request.get("max_steps", 30)

    if not task_prompt:
        raise HTTPException(status_code=400, detail="task_prompt is required")

    async def generate_stream():
        """Generate SSE stream of orchestrator updates."""
        cache_key_final = cache_key or f"flow-{uuid.uuid4().hex}"
        updates_queue = asyncio.Queue()
        error_occurred = False

        async def on_update(update: dict):
            """Callback to queue updates for streaming."""
            await updates_queue.put(update)

        try:
            # Create orchestrator with callback
            agent = OrchestratorAgent(
                task_prompt=task_prompt,
                cache_key=cache_key_final,
                mode="autonomous",
                max_steps=max_steps,
                on_update=on_update,
            )

            # Start orchestrator in background
            async def run_agent():
                try:
                    result = await agent.run()
                    # Ensure flowState is saved to database for replay
                    if result.flow_state:
                        from database import save_flow_state
                        save_flow_state(
                            cache_key=result.cache_key,
                            prompt=task_prompt,
                            flow_state=result.flow_state,
                        )
                    
                    # HARD CODE: Close session after task completion
                    try:
                        from mcp_client import MCPClient
                        mcp_client = MCPClient(cache_key=result.cache_key)
                        if result.flow_state:
                            mcp_client.hydrate(result.flow_state)
                        if mcp_client.has_active_session:
                            await mcp_client.invoke("browserbase_session_close", {})
                        await mcp_client.close()
                        await updates_queue.put({
                            "type": "session_closed",
                            "message": "Browser session closed after task completion",
                        })
                    except Exception as e:
                        # Session close failed, but continue
                        await updates_queue.put({
                            "type": "session_closed",
                            "message": f"Session close attempted: {str(e)}",
                        })
                    
                    await updates_queue.put({
                        "type": "final",
                        "cache_key": result.cache_key,
                        "summary": result.summary,
                        "total_steps": len(result.steps),
                        "flow_state": result.flow_state,  # Return flowState for deterministic replay
                        "steps": result.steps,  # Include all steps for reference
                    })
                    # Request confirmation for replay
                    await updates_queue.put({
                        "type": "confirmation_required",
                        "message": "Task completed. Do you want to replay deterministically?",
                        "cache_key": result.cache_key,
                    })
                except Exception as e:
                    await updates_queue.put({
                        "type": "error",
                        "message": str(e),
                    })
                finally:
                    # Signal completion
                    await updates_queue.put({"type": "done"})

            # Start agent in background
            agent_task = asyncio.create_task(run_agent())

            # Stream updates
            while True:
                try:
                    # Wait for update with timeout
                    update = await asyncio.wait_for(updates_queue.get(), timeout=300.0)
                    
                    if update.get("type") == "done":
                        break

                    # Send SSE event
                    yield {
                        "event": "update",
                        "data": json.dumps(update, default=str),
                    }

                    if update.get("type") == "error":
                        break
                    # Don't break on final or confirmation_required - let them both be sent

                except asyncio.TimeoutError:
                    yield {
                        "event": "error",
                        "data": json.dumps({"message": "Timeout waiting for updates"}),
                    }
                    break

            # Wait for agent to complete
            try:
                await asyncio.wait_for(agent_task, timeout=5.0)
            except asyncio.TimeoutError:
                pass

        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"message": str(e)}),
            }

    return EventSourceResponse(generate_stream())


@app.get("/api/status")
async def get_status():
    """Get API status."""
    try:
        validate_config()
        return {
            "status": "ok",
            "config_valid": True,
        }
    except ValueError as e:
        return {
            "status": "error",
            "config_valid": False,
            "error": str(e),
        }


@app.get("/api/flows")
async def list_flows(limit: int = 20):
    """List cached flow states."""
    from database import list_flow_states
    
    init_database()
    flows = list_flow_states(limit)
    return {"flows": flows}


@app.get("/api/executions")
async def list_executions(limit: int = 20):
    """List recent executions."""
    from database import list_executions
    
    init_database()
    executions = list_executions(limit)
    return {"executions": executions}


@app.post("/api/replay")
async def replay_flowstate(request: dict):
    """Replay a flowState deterministically with streaming."""
    cache_key = request.get("cache_key")
    flow_state = request.get("flow_state")  # Allow direct flowState or cache_key
    
    from database import get_flow_state
    from mcp_client import MCPClient
    from agent.orchestrator import OrchestratorAgent
    
    # Get flowState: either directly provided or from database
    if flow_state:
        # Use provided flowState directly
        if cache_key and flow_state.get("cacheKey") != cache_key:
            flow_state["cacheKey"] = cache_key
        elif not flow_state.get("cacheKey"):
            flow_state["cacheKey"] = cache_key or "replay-flow"
    elif cache_key:
        # Try to get from database
        stored = get_flow_state(cache_key)
        if not stored:
            raise HTTPException(status_code=404, detail=f"No flowState found for cache_key: {cache_key}")
        flow_state = stored["flow_state"]
    else:
        raise HTTPException(status_code=400, detail="Either cache_key or flow_state is required")
    
    async def generate_replay_stream():
        """Generate SSE stream of replay updates."""
        updates_queue = asyncio.Queue()
        
        async def on_update(update: dict):
            """Callback to queue updates for streaming."""
            await updates_queue.put(update)
        
        try:
            # Create MCP client and hydrate with stored flowState
            mcp_client = MCPClient(cache_key=cache_key)
            mcp_client.hydrate(flow_state)
            
            async def run_replay():
                try:
                    # Send replay start event
                    await updates_queue.put({
                        "type": "replay_start",
                        "message": f"Starting deterministic replay of {len(flow_state.get('actions', []))} actions",
                        "cache_key": cache_key,
                    })
                    
                    # Take screenshot before replay
                    try:
                        screenshot_result = await mcp_client.invoke("browserbase_stagehand_screenshot", {})
                        screenshot_data = _extract_screenshot(screenshot_result)
                        if screenshot_data:
                            await updates_queue.put({
                                "type": "replay_screenshot",
                                "screenshot": screenshot_data,
                                "message": "Initial state before replay",
                            })
                    except Exception:
                        pass
                    
                    # Stream action details before replay
                    actions = flow_state.get("actions", [])
                    for i, action in enumerate(actions):
                        action_data = action.get("data", {})
                        action_desc = action_data.get("description") or action_data.get("action") or f"Action {i+1}"
                        await updates_queue.put({
                            "type": "replay_action",
                            "action_index": i + 1,
                            "total_actions": len(actions),
                            "description": action_desc,
                            "action_type": action.get("type", "unknown"),
                        })
                    
                    # Execute replay using browserbase_stagehand_act with replayState
                    # Per MCP guide: replayState triggers full replay mode
                    replay_result = await mcp_client.invoke(
                        "browserbase_stagehand_act",
                        {"replayState": flow_state}
                    )
                    
                    # Extract replay response
                    replay_summary = _summarize_result(replay_result)
                    
                    # Take screenshot after replay
                    try:
                        screenshot_result = await mcp_client.invoke("browserbase_stagehand_screenshot", {})
                        screenshot_data = _extract_screenshot(screenshot_result)
                        if screenshot_data:
                            await updates_queue.put({
                                "type": "replay_screenshot",
                                "screenshot": screenshot_data,
                                "message": "Final state after replay",
                            })
                    except Exception:
                        pass
                    
                    # Extract updated flowState if returned
                    updated_flow_state = mcp_client.flow_state
                    
                    # Close session
                    try:
                        await mcp_client.invoke("browserbase_session_close", {})
                    except Exception:
                        pass
                    
                    await mcp_client.close()
                    
                    # Send completion
                    await updates_queue.put({
                        "type": "replay_complete",
                        "summary": replay_summary,
                        "flow_state": updated_flow_state,
                        "cache_key": cache_key,
                    })
                    
                except Exception as e:
                    await updates_queue.put({
                        "type": "error",
                        "message": f"Replay error: {str(e)}",
                    })
                finally:
                    await updates_queue.put({"type": "done"})
            
            # Start replay in background
            replay_task = asyncio.create_task(run_replay())
            
            # Stream updates
            while True:
                try:
                    update = await asyncio.wait_for(updates_queue.get(), timeout=300.0)
                    
                    if update.get("type") == "done":
                        break
                    
                    # Send SSE event
                    yield {
                        "event": "update",
                        "data": json.dumps(update, default=str),
                    }
                    
                    if update.get("type") in ("error", "replay_complete"):
                        break
                        
                except asyncio.TimeoutError:
                    yield {
                        "event": "error",
                        "data": json.dumps({"message": "Timeout waiting for replay updates"}),
                    }
                    break
            
            # Wait for replay to complete
            try:
                await asyncio.wait_for(replay_task, timeout=5.0)
            except asyncio.TimeoutError:
                pass
                
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"message": str(e)}),
            }
    
    return EventSourceResponse(generate_replay_stream())


def _extract_screenshot(result: dict) -> Optional[str]:
    """Extract screenshot from MCP response."""
    if not result:
        return None
    
    content = result.get("content")
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == "image":
                data = item.get("data") or item.get("image")
                if data and isinstance(data, str) and len(data) > 100:
                    return data if data.startswith("data:") else f"data:image/png;base64,{data}"
    
    raw = result.get("raw", {})
    if isinstance(raw, dict):
        screenshot = raw.get("screenshot") or raw.get("image")
        if screenshot and isinstance(screenshot, str) and len(screenshot) > 100:
            return screenshot if screenshot.startswith("data:") else f"data:image/png;base64,{screenshot}"
    
    return None


def _summarize_result(result: dict) -> str:
    """Summarize MCP response."""
    if not result:
        return "Empty response"
    
    text_chunks = []
    if "message" in result and isinstance(result["message"], str):
        text_chunks.append(result["message"])
    
    content = result.get("content")
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    text_chunks.append(str(item.get("text", "")))
                elif item.get("type") == "json":
                    try:
                        text_chunks.append(json.dumps(item.get("json"), ensure_ascii=False))
                    except (TypeError, ValueError):
                        pass
    
    if not text_chunks:
        text_chunks.append(json.dumps(result, ensure_ascii=False)[:500])
    
    summary = " ".join(chunk.strip() for chunk in text_chunks if chunk).strip()
    return summary[:800]


@app.post("/api/clear")
async def clear_state():
    """Clear all local state data (flow states and executions)."""
    from database import clear_all_data
    
    try:
        clear_all_data()
        return {
            "status": "success",
            "message": "All local state data cleared. Ready for new tasks.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing state: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    import os
    
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"🚀 Starting Browserbase Orchestrator API")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   OpenAI API Key: {'Set' if os.getenv('OPENAI_API_KEY') else 'NOT SET'}")
    print()
    
    uvicorn.run(
        "api_server:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )


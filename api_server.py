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
                    await updates_queue.put({
                        "type": "final",
                        "cache_key": result.cache_key,
                        "summary": result.summary,
                        "total_steps": len(result.steps),
                        "flow_state": result.flow_state,
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

                    if update.get("type") in ("error", "final"):
                        break

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


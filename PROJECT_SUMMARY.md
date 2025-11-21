# Browserbase Orchestrator - Project Summary

## What We're Building

An autonomous browser automation agent that:
- Uses OpenAI GPT-4o for planning and decision-making
- Integrates with Browserbase MCP server for browser automation
- Provides a REST API with Server-Sent Events (SSE) for live streaming
- Supports deterministic replay of browser actions via `flowState`
- Deployed on Render as a web service

## Architecture

- **API Server** (`api_server.py`): FastAPI server with SSE streaming
- **Orchestrator Agent** (`agent/orchestrator.py`): LLM-powered browser automation coordinator
- **MCP Client** (`mcp_client.py`): HTTP client for Browserbase MCP server
- **Database** (`database.py`): SQLite for persisting `flowState` snapshots

## Render Endpoint

**URL:** `https://browserbase-orchestrator-api.onrender.com`

### Key Endpoints

- `POST /api/run` - Execute browser automation task (SSE streaming)
  - Request: `{"task_prompt": "string", "max_steps": int}`
  - Response: SSE stream with `reasoning`, `step`, `final`, `confirmation_required` events
  
- `POST /api/replay` - Deterministically replay a `flowState` (SSE streaming)
  - Request: `{"cache_key": "string", "flow_state": {...}}`
  - Response: SSE stream with `replay_start`, `replay_action`, `replay_complete` events

- `POST /api/confirm` - Handle user acceptance/rejection of replay
  - Request: `{"cache_key": "string", "accepted": bool}`
  
- `POST /api/clear` - Clear all local state (flow states and executions)

- `GET /api/flows` - List cached flow states
- `GET /api/executions` - List recent executions

## Key Concepts

### flowState
JSON payload containing:
- `cacheKey`: Unique identifier for the flow
- `browserbaseSessionId`: Browserbase session ID for session reuse
- `startingUrl`: Initial URL navigated to
- `actions[]`: Chronological array of browser actions (only `browserbase_stagehand_act` creates actions)

### Session Management
- **One session per task**: Session created once at start via `_ensure_session()`
- **LLM cannot create sessions**: `browserbase_session_create` removed from allowed tools
- **Session lifecycle**: 
  - Created at task start
  - Stays open until user accepts/rejects replay
  - Closed after replay or rejection
  - Database cleared after replay/rejection

### Screenshots
- Automatically captured after every step
- Format: `data:image/png;base64,...`
- Extracted from MCP response `source.dataUri`
- Tool name: `browserbase_screenshot` (not `browserbase_stagehand_screenshot`)

## Environment Variables

- `OPENAI_API_KEY` - OpenAI API key (required)
- `OPENAI_MODEL` - Model to use (default: `gpt-4o`)
- `BROWSERBASE_MCP_URL` - MCP server URL (default: `https://browserbase-mcp-server.vercel.app/api/mcp`)
- `DATABASE_PATH` - SQLite database path (default: `/tmp/workflows.db`)
- `PORT` - Server port (default: `8000`)

## Deployment

- **Platform**: Render (web service)
- **Auto-deploy**: On push to `main` branch
- **Docker**: Uses `Dockerfile` with `CMD python api_server.py`
- **Blueprint**: `render.yaml` configures the service

## Important Notes

1. **Actions only from `browserbase_stagehand_act`**: Only this tool adds actions to `flowState.actions[]`
2. **flowState persistence**: Saved to database after every step
3. **Stateless MCP server**: Always pass latest `flowState` to maintain session continuity
4. **Screenshot tool**: Use `browserbase_screenshot` (correct name)
5. **Session reuse**: Pass `flowState` with `browserbaseSessionId` to reuse sessions

## Current Status

✅ Session management fixed (one session per task)  
✅ Screenshots working (captured after each step)  
✅ flowState persistence working  
✅ Database cleanup after replay/rejection  
⚠️ Actions recording: May need verification (MCP server side)

## Files

- `api_server.py` - FastAPI server with SSE endpoints
- `agent/orchestrator.py` - Orchestrator agent with LLM planner
- `mcp_client.py` - MCP server HTTP client
- `database.py` - SQLite database helpers
- `config.py` - Configuration management
- `MCP_SERVER_GUIDE.md` - Detailed MCP server documentation


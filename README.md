# Browserbase Orchestrator - Production System

An autonomous browser automation orchestrator with live streaming, built on Temporal, Browserbase MCP, and GPT-4o.

## Status

⚠️ **Currently in development** - Core functionality working, but needs testing and deployment.

## Quick Start

### Local Development

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment variables
export OPENAI_API_KEY=your_key_here

# 3. Initialize database
python init_db.py

# 4. Start API server
python api_server.py
```

### API Endpoint

**POST `/api/run`** - Run browser automation task with live streaming

```json
{
  "task_prompt": "Navigate to example.com and extract data",
  "max_steps": 30
}
```

Returns Server-Sent Events (SSE) stream with:
- `reasoning` - LLM reasoning
- `step` - Step completion with flowState and screenshot
- `complete` - Final summary
- `error` - Error messages

## Known Issues

1. **FlowState persistence** - Being fixed to ensure session reuse
2. **Observe overuse** - Agent sometimes uses observe unnecessarily
3. **Session management** - Multiple sessions being created (fixing)

## Deployment

### Render

1. Connect GitHub repo to Render
2. Use `render.yaml` configuration
3. Set environment variables:
   - `OPENAI_API_KEY`
   - `BROWSERBASE_MCP_URL` (optional)
   - `TEMPORAL_*` (if using Temporal)

See `DEPLOY.md` for details.

## Architecture

- **API Server** (`api_server.py`) - FastAPI with SSE streaming
- **Orchestrator** (`agent/orchestrator.py`) - GPT-4o planner
- **MCP Client** (`mcp_client.py`) - Browserbase MCP integration
- **Database** (`database.py`) - SQLite for flowState persistence

## Testing

```bash
# Test with real task
python test_real_task.py
```

## License

MIT

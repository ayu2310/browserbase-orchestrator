# Browserbase Orchestrator - Production Ready

Autonomous browser automation orchestrator with live streaming, built on Browserbase MCP and GPT-4o.

## 🚀 Quick Deploy to Render

**Everything is ready!** Just 3 steps:

1. **Create GitHub repo** and push:
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
   git push -u origin main
   ```

2. **Deploy on Render**:
   - Go to https://dashboard.render.com
   - Click "New +" → "Blueprint"
   - Select your repo
   - Set `OPENAI_API_KEY` environment variable
   - Click "Apply"

3. **Done!** Your API will be live at `https://browserbase-orchestrator-api.onrender.com`

See `DEPLOYMENT_STATUS.md` for detailed instructions.

## Features

- 🤖 **Autonomous Orchestration** - GPT-4o plans and executes browser tasks
- 📡 **Live Streaming** - Real-time updates via SSE (reasoning, steps, screenshots)
- 🔄 **FlowState Management** - Stateless architecture with deterministic replay
- 💾 **Session Persistence** - Automatic session management and cleanup
- ☁️ **Production Ready** - Deployed on Render, no Temporal needed

## API Usage

**POST `/api/run`** - Run browser automation task

```json
{
  "task_prompt": "Navigate to example.com and extract data",
  "max_steps": 30
}
```

Returns Server-Sent Events stream with:
- `reasoning` - LLM reasoning for each step
- `step` - Step completion with flowState and screenshot
- `complete` - Final summary
- `error` - Error messages

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variable
export OPENAI_API_KEY=your_key_here

# Start server
python api_server.py
```

## Project Structure

```
.
├── api_server.py          # FastAPI server with SSE streaming
├── agent/
│   └── orchestrator.py    # GPT-4o orchestrator agent
├── mcp_client.py          # Browserbase MCP client
├── database.py            # SQLite persistence
├── render.yaml            # Render deployment config
└── Dockerfile             # Docker configuration
```

## Documentation

- `MCP_SERVER_GUIDE.md` - Browserbase MCP server documentation

## License

MIT

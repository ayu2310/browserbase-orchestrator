# API Flow Documentation

## Complete Workflow

### 1. Initial Task Execution (`POST /api/run`)

**Request:**
```json
{
  "task_prompt": "Go to ProductHunt and extract top 5 AI products",
  "cache_key": "optional-cache-key",
  "max_steps": 30
}
```

**Response (SSE Stream):**
- `reasoning` - LLM reasoning for each step
- `step` - Step execution with result, flowState, screenshot
- `final` - Final result with flowState
- `confirmation_required` - Request for replay confirmation

**Example final event:**
```json
{
  "type": "final",
  "cache_key": "flow-abc123",
  "summary": "Task completed",
  "total_steps": 10,
  "flow_state": {
    "cacheKey": "flow-abc123",
    "browserbaseSessionId": "...",
    "startingUrl": "https://producthunt.com",
    "actions": [...]
  },
  "steps": [...]
}
```

**Confirmation request:**
```json
{
  "type": "confirmation_required",
  "message": "Task completed. Do you want to replay deterministically?",
  "cache_key": "flow-abc123"
}
```

---

### 2. Deterministic Replay (`POST /api/replay`)

**When:** After receiving `confirmation_required`, user accepts replay.

**Request:**
```json
{
  "cache_key": "flow-abc123"
}
```

**Response (SSE Stream):**
- `replay_start` - Replay initiated
- `replay_screenshot` - Screenshots before/after replay
- `replay_action` - Each action being replayed (with index, description, type)
- `replay_complete` - Replay finished with summary and updated flowState

**Example replay events:**
```json
{
  "type": "replay_start",
  "message": "Starting deterministic replay of 5 actions",
  "cache_key": "flow-abc123"
}

{
  "type": "replay_action",
  "action_index": 1,
  "total_actions": 5,
  "description": "Navigate to ProductHunt",
  "action_type": "action"
}

{
  "type": "replay_screenshot",
  "screenshot": "data:image/png;base64,...",
  "message": "Final state after replay"
}

{
  "type": "replay_complete",
  "summary": "Replayed 5 actions successfully",
  "flow_state": {...},
  "cache_key": "flow-abc123"
}
```

**How replay works (per MCP guide):**
1. Reuses `browserbaseSessionId` from flowState (maintains login state)
2. Navigates to `startingUrl`
3. Executes all actions in `actions` array sequentially
4. Self-heals if selectors break
5. Returns updated flowState

---

### 3. Clear State (`POST /api/clear`)

**When:** After replay completion or if user denies replay.

**Request:** `POST /api/clear` (no body)

**Response:**
```json
{
  "status": "success",
  "message": "All local state data cleared. Ready for new tasks."
}
```

**What it does:**
- Deletes all flow states from database
- Deletes all execution logs
- Ready for new task execution

---

## Frontend Integration Flow

### Step 1: Execute Task
```javascript
const eventSource = new EventSource('/api/run', {
  method: 'POST',
  body: JSON.stringify({
    task_prompt: "Go to ProductHunt...",
    max_steps: 30
  })
});

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'reasoning') {
    // Show LLM reasoning
  } else if (data.type === 'step') {
    // Show step execution, screenshot, flowState
  } else if (data.type === 'final') {
    // Save flowState for replay
    const flowState = data.flow_state;
  } else if (data.type === 'confirmation_required') {
    // Show confirmation dialog
    showReplayConfirmation(data.cache_key);
  }
};
```

### Step 2: Handle Confirmation
```javascript
async function confirmReplay(cacheKey) {
  const eventSource = new EventSource('/api/replay', {
    method: 'POST',
    body: JSON.stringify({ cache_key: cacheKey })
  });
  
  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'replay_start') {
      // Show replay started
    } else if (data.type === 'replay_action') {
      // Show action being replayed
      console.log(`Replaying action ${data.action_index}/${data.total_actions}: ${data.description}`);
    } else if (data.type === 'replay_screenshot') {
      // Display screenshot
      displayScreenshot(data.screenshot);
    } else if (data.type === 'replay_complete') {
      // Replay finished
      // Optionally clear state or allow new task
    }
  };
}

async function denyReplay() {
  // Clear state and allow new task
  await fetch('/api/clear', { method: 'POST' });
}
```

### Step 3: Clear State (After Replay or Denial)
```javascript
async function clearState() {
  const response = await fetch('/api/clear', { method: 'POST' });
  const result = await response.json();
  // State cleared, ready for new task
}
```

---

## Key Points

1. **flowState Structure:**
   - `cacheKey`: Unique identifier
   - `browserbaseSessionId`: Session ID for replay
   - `startingUrl`: Initial URL
   - `actions`: Array of actions to replay

2. **Deterministic Replay:**
   - Uses `browserbase_stagehand_act` with `replayState` parameter
   - Per MCP guide: automatically reuses session, navigates, executes actions
   - Self-heals if selectors break

3. **State Management:**
   - State persists in SQLite database on Render
   - Clear state after replay/denial to start fresh
   - Each task gets a unique `cache_key`

4. **Streaming:**
   - All endpoints use SSE for live updates
   - Screenshots streamed as base64 images
   - Actions streamed with descriptions and indices


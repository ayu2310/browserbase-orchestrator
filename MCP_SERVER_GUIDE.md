# Browserbase Stagehand MCP Server - User Guide

A production-ready Model Context Protocol (MCP) server for browser automation. **Fully stateless**—returns `flowState` snapshots you must persist externally for deterministic replays.

**Endpoint:** `https://browserbase-mcp-server.vercel.app/api/mcp`

---

## Core Concepts

### Stateless Architecture

**The server stores NO data.** Every tool call returns a `flowState` JSON payload. You must:
1. **Capture** `flowState` from each response
2. **Persist** it in your database
3. **Feed it back** for replays

### FlowState vs ReplayState

- **`flowState`**: Pass to tools to append new actions. Each tool returns an updated `flowState`.
- **`replayState`**: Complete `flowState` passed to `browserbase_stagehand_act` to trigger full replay mode.

### Deterministic vs Natural Language

- **Deterministic**: Use `observation` parameter (fast, reliable, replayable)
- **Natural language**: Use `action` parameter (slower, more flexible)

---

## FlowState Structure

```json
{
  "cacheKey": "f7dc1a2b-6d5e-4e0b-8c8b-8e4ef8e6da65",
  "startingUrl": "https://example.com/login",
  "browserbaseSessionId": "3c0f5158-d987-42de-9c3f-0c88683b235a",
  "actions": [
    {
      "type": "observation",
      "data": {
        "selector": "xpath=/html/body/main/div/button[1]",
        "description": "Login button",
        "method": "click",
        "arguments": []
      },
      "timestamp": 1734567890000
    }
  ]
}
```

**Fields:**
- `cacheKey`: Unique workflow identifier (auto-generated if not provided)
- `startingUrl`: Initial URL (captured by `browserbase_stagehand_navigate`)
- `browserbaseSessionId`: Session ID for login state (captured by `browserbase_session_create`)
- `actions`: Chronological array of actions (type: `"observation"` or `"action"`)

**Important:** Store the last `flowState` response—it contains all accumulated actions.

> **Session Reuse:** Always pass the freshest `flowState` back into *every* Stagehand tool (`act`, `navigate`, `observe`, `extract`, `screenshot`, `get_url`).  
> That’s how the server reattaches to the same Browserbase session for each stateless HTTP call; skipping it spins up a brand-new browser (which shows up as a blank/black dashboard).

---

## Available Tools

### `browserbase_session_create`

Creates/reuses a Browserbase session. Returns session ID in `flowState`.

**Parameters:**
- `sessionId` (optional): Existing session ID to reuse
- `flowState` (optional): Flow snapshot to update

**Example:**
```json
{
  "name": "browserbase_session_create",
  "arguments": {
    "flowState": { "cacheKey": "my-flow" }
  }
}
```

**Response:** Returns `flowState` with `browserbaseSessionId`

---

### `browserbase_stagehand_navigate`

Navigates to a URL. Captures it as `startingUrl` in `flowState`.

**Parameters:**
- `url` (required): URL to navigate to
- `flowState` (optional): Flow snapshot to update

**Example:**
```json
{
  "name": "browserbase_stagehand_navigate",
  "arguments": {
    "url": "https://example.com",
    "flowState": { "cacheKey": "my-flow", "browserbaseSessionId": "..." }
  }
}
```

**Response:** Returns `flowState` with `startingUrl`

---

### `browserbase_stagehand_observe`

Finds elements and returns deterministic selectors.

**Parameters:**
- `instruction` (required): What to find (e.g., "Find the login button")
- `returnAction` (optional): If `true`, returns actionable objects
- `flowState` (optional): Latest snapshot so the MCP server can reuse your Browserbase session

**Example:**
```json
{
  "name": "browserbase_stagehand_observe",
  "arguments": {
    "instruction": "Find the email input field",
    "returnAction": true,
    "flowState": {
      "cacheKey": "my-flow",
      "browserbaseSessionId": "abc-session-id"
    }
  }
}
```

**Response:** Array of observations with `selector`, `description`, `method`

---

### `browserbase_stagehand_act` (Two Modes)

#### Mode 1: Single Action

Execute one action and append to `flowState`.

**Parameters:**
- `observation` (optional): Deterministic action from `observe`
- `action` (optional): Natural language description
- `variables` (optional): Variables for templates
- `flowState` (optional): Flow snapshot to append to

**Example 1: Deterministic**
```json
{
  "name": "browserbase_stagehand_act",
  "arguments": {
    "observation": {
      "selector": "xpath=/html/body/form/input[1]",
      "description": "Email input",
      "method": "fill",
      "arguments": ["user@example.com"]
    },
    "flowState": { "cacheKey": "my-flow", "actions": [] }
  }
}
```

**Example 2: Natural Language**
```json
{
  "name": "browserbase_stagehand_act",
  "arguments": {
    "action": "Click the login button",
    "flowState": { "cacheKey": "my-flow", "actions": [] }
  }
}
```

**Response:** Returns `flowState` with action appended to `actions` array

#### Mode 2: Full Replay

Replay entire workflow using `replayState`.

**Parameters:**
- `replayState` (required): Complete `flowState` from your storage

**What Happens:**
1. Reuses `browserbaseSessionId` (maintains login state)
2. Navigates to `startingUrl`
3. Executes all actions in `actions` array sequentially
4. Self-heals if selectors break

**Example:**
```json
{
  "name": "browserbase_stagehand_act",
  "arguments": {
    "replayState": {
      "cacheKey": "my-flow",
      "startingUrl": "https://example.com/login",
      "browserbaseSessionId": "3c0f5158-d987-42de-9c3f-0c88683b235a",
      "actions": [
        {
          "type": "observation",
          "data": {
            "selector": "xpath=/html/body/form/input[1]",
            "description": "Email input",
            "method": "fill",
            "arguments": ["user@example.com"]
          },
          "timestamp": 1734567890000
        }
      ]
    }
  }
}
```

**Response:** Confirmation message with replay results

---

### `browserbase_list_cached_actions`

Formats `flowState` for inspection (stateless formatter).

**Parameters:**
- `flowState` (optional): Flow snapshot to format

**Response:** Human-readable summary of the flow state

---

### Standard Browserbase Tools

- `browserbase_stagehand_extract`: Extract structured data
- `browserbase_stagehand_screenshot`: Capture screenshots
- `browserbase_stagehand_get_url`: Get current URL
- `browserbase_session_close`: Close session
- `browserbase_session_list`: List active sessions

All Stagehand tools now accept an optional `flowState` argument—always include your latest snapshot so the server can attach to the same Browserbase session before running `observe`, `extract`, `screenshot`, or `get_url`.

---

## Usage Patterns

### Building a Flow

```javascript
// 1. Create session
let flowState = extractFlowState(await mcp.call('browserbase_session_create', {
  flowState: { cacheKey: 'my-flow' }
}));
await db.save('my-flow', flowState);

// 2. Navigate
flowState = extractFlowState(await mcp.call('browserbase_stagehand_navigate', {
  url: 'https://example.com',
  flowState: flowState
}));
await db.save('my-flow', flowState);

// 3. Observe
const obs = await mcp.call('browserbase_stagehand_observe', {
  instruction: 'Find the submit button',
  returnAction: true
});

// 4. Act (deterministic)
flowState = extractFlowState(await mcp.call('browserbase_stagehand_act', {
  observation: obs[0],
  flowState: flowState
}));
await db.save('my-flow', flowState); // Last flowState has everything
```

### Replaying a Flow

```javascript
// Retrieve from your database
const savedFlow = await db.get('my-flow');

// Single call replays everything
await mcp.call('browserbase_stagehand_act', {
  replayState: savedFlow
});
// Automatically: reuses session, navigates, executes all actions
```

---

## Complete Example

```javascript
// Build workflow
let flowState = extractFlowState(await mcp.call('browserbase_session_create', {
  flowState: { cacheKey: 'login-flow' }
}));

flowState = extractFlowState(await mcp.call('browserbase_stagehand_navigate', {
  url: 'https://example.com/login',
  flowState: flowState
}));

const emailObs = await mcp.call('browserbase_stagehand_observe', {
  instruction: 'Find the email input field',
  returnAction: true
});

flowState = extractFlowState(await mcp.call('browserbase_stagehand_act', {
  observation: emailObs[0],
  flowState: flowState
}));

// Save last flowState (contains all actions)
await db.save('login-flow', flowState);

// Later: Replay
const savedFlow = await db.get('login-flow');
await mcp.call('browserbase_stagehand_act', {
  replayState: savedFlow
});
```

---

## Best Practices

### 1. Always Persist Last FlowState

```javascript
// ✅ Good: Save after each call
const result = await mcp.call('browserbase_stagehand_act', { ... });
const flowState = extractFlowState(result);
await db.save(flowState.cacheKey, flowState);
```

### 2. Use Deterministic Actions for Critical Steps

```javascript
// ✅ Good: Deterministic (reliable)
const obs = await mcp.call('browserbase_stagehand_observe', {
  instruction: 'Find the login button',
  returnAction: true
});
await mcp.call('browserbase_stagehand_act', {
  observation: obs[0],
  flowState: flowState
});
```

### 3. Use Meaningful Cache Keys

```javascript
// ✅ Good
{ cacheKey: 'github-login-flow' }
{ cacheKey: 'product-search-v2' }
```

### 4. Handle Self-Healing

When replaying, if self-healing occurs, consider updating your stored `flowState`:

```javascript
const replayResult = await mcp.call('browserbase_stagehand_act', {
  replayState: savedFlow
});

if (replayResult.content[0].text.includes('Recovered via observe')) {
  // Self-healing occurred - update stored flowState
  const newFlowState = extractFlowState(replayResult);
  await db.update(savedFlow.cacheKey, newFlowState);
}
```

---

## Self-Healing

During replay, if a selector breaks, the server automatically:
1. Re-observes the page using stored description
2. Finds a similar element
3. Retries the action
4. Logs recovery in response

**Example Response:**
```
Replayed 3 actions:
Navigated to: https://example.com
Replayed action: Email input
Recovered via observe: Email input (method: fill)  ← Self-healing
Replayed action: Submit button
```

---

## Error Handling

### Missing FlowState
Server auto-generates `cacheKey` if not provided.

### Empty ReplayState
Returns error: `"replayState.actions is empty"`

### Session Reuse Failures
Continues with current session, logs warning.

---

## Multiple Navigations

**Current Limitation:** Only the last `startingUrl` is stored. For multiple navigations:

**Workaround:** Use natural language actions for navigation:
```javascript
// Navigate to site A
await mcp.call('browserbase_stagehand_navigate', {
  url: 'https://site-a.com',
  flowState: flowState
});

// Extract data
await mcp.call('browserbase_stagehand_act', {
  action: 'Extract product names',
  flowState: flowState
});

// Navigate to site B (stored as action)
await mcp.call('browserbase_stagehand_act', {
  action: 'Navigate to https://site-b.com',
  flowState: flowState
});

// Paste data
await mcp.call('browserbase_stagehand_act', {
  action: 'Paste the extracted data',
  flowState: flowState
});
```

Natural language navigation actions are stored in `actions` array and replayed correctly.

---

## Summary

✅ **Stateless**: No server storage—persist `flowState` externally  
✅ **Deterministic**: Use `observation` for reliable replays  
✅ **Self-Healing**: Automatic recovery when selectors break  
✅ **Session Persistence**: Reuse `browserbaseSessionId` for login state  
✅ **Production Ready**: Fully tested with timeout protection

**Key Point:** Store the last `flowState` response—it contains all accumulated actions and metadata needed for deterministic replay.

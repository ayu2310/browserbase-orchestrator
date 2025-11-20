# MCP Tool Instructions Analysis

## Current Status: ✅ Mostly Correct, but can be improved

## Comparison: MCP Guide vs Our Instructions

### ✅ `browserbase_session_create`
**MCP Guide:**
- `sessionId` (optional)
- `flowState` (optional)

**Our Instructions:**
- `{"flowState": {"cacheKey": "..."}}` ✅ Correct

**Note:** flowState is automatically attached by MCPClient, so this is fine.

---

### ⚠️ `browserbase_session_close`
**MCP Guide:**
- Not detailed, but accepts `flowState` (optional per guide, but REQUIRED in practice)

**Our Instructions:**
- `{"flowState": ...}` ✅ Correct (we mark as required)

---

### ✅ `browserbase_stagehand_navigate`
**MCP Guide:**
- `url` (required)
- `flowState` (optional)

**Our Instructions:**
- `{"url": "https://...", "flowState": ...}` ✅ Correct

---

### ✅ `browserbase_stagehand_observe`
**MCP Guide:**
- `instruction` (required)
- `returnAction` (optional)
- `flowState` (optional)

**Our Instructions:**
- `{"instruction": "Find the login button", "returnAction": true, "flowState": ...}` ✅ Correct

---

### ✅ `browserbase_stagehand_act`
**MCP Guide:**
- `observation` (optional)
- `action` (optional)
- `variables` (optional)
- `flowState` (optional)
- OR `replayState` (required for replay mode)

**Our Instructions:**
- `{"action": "..."}` OR `{"observation": {...}}` ✅ Correct
- Note: At least one of `action` or `observation` is needed

---

### ⚠️ `browserbase_stagehand_extract`
**MCP Guide:**
- Not detailed! Only says "Extract structured data"
- Accepts `flowState` (optional)

**Our Instructions:**
- `{"instruction": "...", "flowState": ...}` ✅ Correct (based on error analysis)
- **Issue:** Guide doesn't document this, but error shows `instruction` is REQUIRED

---

### ✅ `browserbase_stagehand_screenshot`
**MCP Guide:**
- Accepts `flowState` (optional)

**Our Instructions:**
- `{"flowState": ...}` ✅ Correct

---

### ✅ `browserbase_stagehand_get_url`
**MCP Guide:**
- Accepts `flowState` (optional)

**Our Instructions:**
- `{"flowState": ...}` ✅ Correct

---

## Key Findings

1. **flowState is automatically attached** by `MCPClient._attach_flow_state()`, so the LLM doesn't need to explicitly include it in arguments, BUT we tell it to include it for clarity.

2. **The MCP guide is incomplete** - it doesn't detail `browserbase_stagehand_extract` parameters, but we know from errors it requires `instruction`.

3. **Our instructions are mostly accurate**, but could be more explicit about:
   - flowState is automatically handled (but should still be mentioned)
   - Better examples with actual JSON structure
   - More emphasis on required vs optional parameters

## Recommendations

1. ✅ Keep current tool schemas (they're correct)
2. ⚠️ Add note that flowState is automatically attached (but still include it for clarity)
3. ✅ Add more explicit examples showing the exact JSON structure
4. ✅ Emphasize that `browserbase_stagehand_act` needs EITHER `action` OR `observation`
5. ✅ Make it clearer that `browserbase_stagehand_extract` REQUIRES `instruction` parameter


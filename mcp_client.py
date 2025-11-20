"""Low-level helper for calling Browserbase MCP tools with flowState support."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

import httpx

from config import BROWSERBASE_MCP_URL


class MCPClient:
    """Handles JSON-RPC calls to the Browserbase MCP server."""

    def __init__(self, cache_key: str, base_url: str = BROWSERBASE_MCP_URL) -> None:
        self.base_url = base_url
        self.cache_key = cache_key
        self.client = httpx.AsyncClient(timeout=120.0)
        self.flow_state: Optional[Dict[str, Any]] = None

    @property
    def has_active_session(self) -> bool:
        return bool(self.flow_state and self.flow_state.get("browserbaseSessionId"))

    def hydrate(self, flow_state: Dict[str, Any]) -> None:
        """Load an existing flowState into the client."""
        self.flow_state = flow_state

    def describe_state(self) -> str:
        """Return a concise text summary of the current flowState for prompting."""
        if not self.flow_state:
            return "No flowState yet."
        actions = self.flow_state.get("actions") or []
        starting_url = self.flow_state.get("startingUrl")
        session_id = self.flow_state.get("browserbaseSessionId")
        return (
            f"cacheKey={self.flow_state.get('cacheKey', self.cache_key)}, "
            f"startingUrl={starting_url or 'unknown'}, "
            f"actions={len(actions)}, "
            f"session={'yes' if session_id else 'no'}"
        )

    async def invoke(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Invoke an MCP tool with automatic flowState management."""
        arguments = dict(arguments or {})
        use_flow_state = True

        if tool_name == "browserbase_stagehand_act" and "replayState" in arguments:
            use_flow_state = False
        elif tool_name == "browserbase_session_create":
            arguments.setdefault("flowState", {"cacheKey": self.cache_key})
            use_flow_state = False  # already injected

        if use_flow_state:
            arguments = self._attach_flow_state(arguments)

        result = await self._call_tool(tool_name, arguments)
        self._update_flow_state(result)
        return result

    def _attach_flow_state(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Attach the latest flowState to outbound tool calls."""
        # Always use current flowState, or create minimal one with cacheKey
        flow_state = self.flow_state
        if not flow_state:
            flow_state = {"cacheKey": self.cache_key}
        else:
            # Ensure cacheKey is set
            flow_state = dict(flow_state)  # Make a copy
            flow_state["cacheKey"] = flow_state.get("cacheKey", self.cache_key)
        
        merged = dict(arguments)
        merged["flowState"] = flow_state
        return merged

    async def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the JSON-RPC request."""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }

        response = await self.client.post(
            self.base_url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
        )
        response.raise_for_status()
        if not response.content:
            raise RuntimeError(f"MCP server returned empty response ({response.status_code})")

        content_type = response.headers.get("content-type", "")
        data = self._parse_response_body(response, content_type)

        if "error" in data:
            error_msg = data["error"]
            if isinstance(error_msg, dict):
                error_msg = error_msg.get("message", error_msg)
            raise RuntimeError(f"MCP error: {error_msg}")

        result = data.get("result", data)
        if not isinstance(result, dict):
            return {"raw": result}

        result.setdefault("raw", result)
        
        # Debug: Check if flowState is in response but not being extracted
        if "flowState" not in result and isinstance(result.get("raw"), dict):
            if "flowState" in result["raw"]:
                # flowState is in raw but not extracted - this shouldn't happen but let's handle it
                result["flowState"] = result["raw"]["flowState"]
        
        return result

    def _parse_response_body(self, response: httpx.Response, content_type: str) -> Dict[str, Any]:
        """Parse JSON or SSE payloads."""
        if "text/event-stream" in content_type:
            lines = response.text.strip().split("\n")
            for line in lines:
                if line.startswith("data: "):
                    json_str = line[6:].strip()
                    if json_str:
                        return json.loads(json_str)
            raise RuntimeError("Failed to parse SSE payload from MCP server")

        try:
            return response.json()
        except json.JSONDecodeError as exc:
            preview = response.text[:400] if response.text else "<empty>"
            raise RuntimeError(
                f"MCP server returned non-JSON payload (type={content_type}): {preview}"
            ) from exc

    def _update_flow_state(self, result: Dict[str, Any]) -> None:
        """Extract flowState from the response and cache it."""
        flow_state = self._extract_flow_state(result)
        if flow_state:
            # Ensure cacheKey is preserved
            if "cacheKey" not in flow_state:
                flow_state["cacheKey"] = self.cache_key
            self.flow_state = flow_state
        # If no flowState found but we have one, keep it (some tools don't return flowState)
        elif self.flow_state:
            # Keep existing flowState but ensure cacheKey
            if "cacheKey" not in self.flow_state:
                self.flow_state["cacheKey"] = self.cache_key
        # If we still don't have flowState, create minimal one to ensure we always have something
        if not self.flow_state:
            # Create minimal flowState with cacheKey
            self.flow_state = {"cacheKey": self.cache_key}

    def _extract_flow_state(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Attempt to locate a flowState object in the MCP response."""
        # Direct flowState (check both camelCase and snake_case)
        if "flowState" in payload and isinstance(payload["flowState"], dict):
            return payload["flowState"]
        if "flow_state" in payload and isinstance(payload["flow_state"], dict):
            return payload["flow_state"]

        # Check content array
        content = payload.get("content")
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    # JSON type content
                    if item.get("type") == "json" and isinstance(item.get("json"), dict):
                        inner = item["json"]
                        if "flowState" in inner and isinstance(inner["flowState"], dict):
                            return inner["flowState"]
                    # Text type content - try to parse JSON from text
                    elif item.get("type") == "text":
                        text = item.get("text", "")
                        # Try to extract flowState from text (common in MCP responses)
                        if "flowState" in text or "flow_state" in text.lower():
                            try:
                                # Look for flowState JSON object in text
                                # Pattern 1: "flowState (persist externally): { ... }"
                                match = re.search(r'flowState[^:]*:\s*(\{.*?\})', text, re.DOTALL)
                                if not match:
                                    # Pattern 2: "flowState": { ... }
                                    match = re.search(r'["\']?flowState["\']?\s*:\s*(\{.*?\})', text, re.DOTALL)
                                if not match:
                                    # Pattern 3: Just find any JSON object after "flowState"
                                    match = re.search(r'flowState[^:]*:\s*(\{[^}]*(?:\{[^}]*\}[^}]*)*\})', text, re.DOTALL)
                                
                                if match:
                                    flow_state_str = match.group(1)
                                    # Try to parse as JSON
                                    flow_state = json.loads(flow_state_str)
                                    if isinstance(flow_state, dict):
                                        return flow_state
                            except (json.JSONDecodeError, AttributeError, ValueError) as e:
                                # If regex match fails, try to find complete JSON object
                                try:
                                    # Look for complete JSON object starting with {
                                    json_start = text.find('{')
                                    if json_start != -1:
                                        # Try to find matching closing brace
                                        brace_count = 0
                                        json_end = json_start
                                        for i, char in enumerate(text[json_start:], json_start):
                                            if char == '{':
                                                brace_count += 1
                                            elif char == '}':
                                                brace_count -= 1
                                                if brace_count == 0:
                                                    json_end = i + 1
                                                    break
                                        if brace_count == 0:
                                            json_str = text[json_start:json_end]
                                            parsed = json.loads(json_str)
                                            if isinstance(parsed, dict) and ("cacheKey" in parsed or "browserbaseSessionId" in parsed):
                                                return parsed
                                except (json.JSONDecodeError, ValueError):
                                    pass
                    # Direct flowState in item
                    elif "flowState" in item and isinstance(item["flowState"], dict):
                        return item["flowState"]

        # Check raw response
        raw = payload.get("raw")
        if isinstance(raw, dict):
            flow_state = raw.get("flowState")
            if isinstance(flow_state, dict):
                return flow_state

        # Check message field (sometimes flowState is in message text)
        message = payload.get("message", "")
        if isinstance(message, str) and "flowState" in message:
            try:
                match = re.search(r'"flowState"\s*:\s*(\{[^}]+\})', message, re.DOTALL)
                if match:
                    flow_state_str = match.group(1)
                    flow_state = json.loads(flow_state_str)
                    if isinstance(flow_state, dict):
                        return flow_state
            except (json.JSONDecodeError, AttributeError):
                pass

        return None

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()


__all__ = ["MCPClient"]


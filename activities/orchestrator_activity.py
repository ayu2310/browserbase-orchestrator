"""Temporal activity that runs the Browserbase orchestrator."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from temporalio import activity

from agent.orchestrator import OrchestratorAgent
from database import init_database, record_execution


@dataclass
class OrchestratorActivityInput:
    task_prompt: str
    cache_key: Optional[str] = None
    mode: str = "autonomous"
    max_steps: int = 30


@activity.defn
async def run_orchestrator(input: OrchestratorActivityInput) -> Dict[str, Any]:
    """Execute the orchestrator agent."""
    init_database()
    agent = OrchestratorAgent(
        task_prompt=input.task_prompt,
        cache_key=input.cache_key,
        mode=input.mode,
        max_steps=input.max_steps,
    )
    result = await agent.run()
    record_execution(
        cache_key=result.cache_key,
        prompt=input.task_prompt,
        summary=result.summary,
        history=result.steps,
        status="completed",
    )
    payload = {
        "cache_key": result.cache_key,
        "mode": result.mode,
        "summary": result.summary,
        "steps": result.steps,
        "flow_state": result.flow_state,
    }
    return payload


__all__ = ["run_orchestrator", "OrchestratorActivityInput"]




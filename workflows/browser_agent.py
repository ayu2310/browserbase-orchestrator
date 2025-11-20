"""Stateless Temporal workflow that runs the orchestrator activity."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from temporalio import workflow
from temporalio.common import RetryPolicy

from activities.orchestrator_activity import (
    OrchestratorActivityInput,
    run_orchestrator,
)


@dataclass
class WorkflowInput:
    task_prompt: str
    cache_key: str
    mode: str = "autonomous"  # or "replay"
    max_steps: int = 30


@dataclass
class WorkflowResult:
    success: bool
    cache_key: str
    mode: str
    summary: str
    steps: Any
    flow_state: Dict[str, Any] | None


@workflow.defn
class BrowserAutomationWorkflow:
    """Delegates all heavy lifting to the orchestrator activity."""

    @workflow.run
    async def run(self, input: WorkflowInput) -> WorkflowResult:
        workflow.logger.info(
            f"Starting BrowserAutomationWorkflow cache_key={input.cache_key} mode={input.mode}"
        )
        try:
            payload = await workflow.execute_activity(
                run_orchestrator,
                OrchestratorActivityInput(
                    task_prompt=input.task_prompt,
                    cache_key=input.cache_key,
                    mode=input.mode,
                    max_steps=input.max_steps,
                ),
                start_to_close_timeout=600,
                retry_policy=RetryPolicy(maximum_attempts=1),
            )
            return WorkflowResult(
                success=True,
                cache_key=payload["cache_key"],
                mode=payload["mode"],
                summary=payload["summary"],
                steps=payload["steps"],
                flow_state=payload.get("flow_state"),
            )
        except Exception as exc:
            workflow.logger.error(f"Workflow failure: {exc}")
            return WorkflowResult(
                success=False,
                cache_key=input.cache_key,
                mode=input.mode,
                summary=str(exc),
                steps=[],
                flow_state=None,
            )

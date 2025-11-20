"""Temporal worker for Browserbase orchestrator."""
import asyncio

from temporalio.client import Client
from temporalio.worker import UnsandboxedWorkflowRunner, Worker

from activities.orchestrator_activity import run_orchestrator
from config import TEMPORAL_ADDRESS, TEMPORAL_NAMESPACE, validate_config
from workflows import browser_agent


async def main():
    try:
        validate_config()
    except ValueError as exc:
        print(f"Configuration error: {exc}")
        return

    client = await Client.connect(
        target_host=TEMPORAL_ADDRESS,
        namespace=TEMPORAL_NAMESPACE,
    )

    worker = Worker(
        client,
        task_queue="browser-automation-task-queue",
        workflows=[browser_agent.BrowserAutomationWorkflow],
        activities=[run_orchestrator],
        workflow_runner=UnsandboxedWorkflowRunner(),
    )
    print("Worker started. Waiting for workflows...")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())


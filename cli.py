"""Lightweight CLI for orchestrating Browserbase workflows."""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Optional

import click
from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy

from config import TEMPORAL_ADDRESS, TEMPORAL_NAMESPACE, validate_config
from database import (
    delete_flow_state,
    init_database,
    list_executions,
    list_flow_states,
)
from workflows.browser_agent import WorkflowInput


async def get_temporal_client() -> Client:
    """Connect to Temporal using local dev, API key, or TLS."""
    from temporalio.client import ClientTlsConfig
    import os

    api_key = os.getenv("TEMPORAL_API_KEY")
    if api_key:
        return await Client.connect(
            target_host=TEMPORAL_ADDRESS,
            namespace=TEMPORAL_NAMESPACE,
            api_key=api_key,
            tls=True,
        )

    cert_path = os.getenv("TEMPORAL_TLS_CERT_PATH")
    key_path = os.getenv("TEMPORAL_TLS_KEY_PATH")
    if cert_path and key_path:
        with open(cert_path, "rb") as f:
            cert = f.read()
        with open(key_path, "rb") as f:
            key = f.read()
        tls = ClientTlsConfig(client_cert=cert, client_private_key=key)
        return await Client.connect(
            target_host=TEMPORAL_ADDRESS,
            namespace=TEMPORAL_NAMESPACE,
            tls=tls,
        )

    return await Client.connect(
        target_host=TEMPORAL_ADDRESS,
        namespace=TEMPORAL_NAMESPACE,
    )


def generate_cache_key() -> str:
    return f"flow-{uuid.uuid4().hex}"


@click.group()
def cli():
    """Temporal Browserbase orchestrator CLI."""


@cli.command()
@click.argument("task_prompt")
@click.option("--cache-key", default=None, help="Optional cache key to reuse state")
@click.option("--max-steps", default=30, show_default=True, help="Max planner iterations")
@click.option("--wait/--no-wait", default=True, show_default=True, help="Wait for workflow result")
def run(task_prompt: str, cache_key: Optional[str], max_steps: int, wait: bool):
    """Launch an autonomous orchestration run."""

    async def _run():
        init_database()
        client = await get_temporal_client()
        key = cache_key or generate_cache_key()
        workflow_input = WorkflowInput(
            task_prompt=task_prompt,
            cache_key=key,
            mode="autonomous",
            max_steps=max_steps,
        )
        handle = await client.start_workflow(
            "BrowserAutomationWorkflow",
            workflow_input,
            id=f"{key}-{uuid.uuid4().hex}",
            task_queue="browser-automation-task-queue",
            id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE,
        )
        click.echo(f"🚀 Started orchestrator workflow")
        click.echo(f"  Temporal ID: {handle.id}")
        click.echo(f"  Cache key : {key}")
        click.echo(f"  Prompt    : {task_prompt}")
        if wait:
            click.echo("⏳ Waiting for result...")
            try:
                result = await handle.result()
                click.echo(f"\n✅ Completed ({result.mode})")
                click.echo(f"Summary: {result.summary}")
                if result.flow_state:
                    click.echo("Flow state persisted for deterministic replay.")
            except Exception as exc:
                click.echo(f"\n❌ Workflow failed: {exc}")

    asyncio.run(_run())


@cli.command()
@click.argument("cache_key")
@click.option("--wait/--no-wait", default=True, show_default=True)
def replay(cache_key: str, wait: bool):
    """Replay a stored flowState using Stagehand self-healing."""

    async def _run():
        init_database()
        client = await get_temporal_client()
        workflow_input = WorkflowInput(
            task_prompt=f"Replay cache {cache_key}",
            cache_key=cache_key,
            mode="replay",
            max_steps=1,
        )
        handle = await client.start_workflow(
            "BrowserAutomationWorkflow",
            workflow_input,
            id=f"replay-{cache_key}-{uuid.uuid4().hex}",
            task_queue="browser-automation-task-queue",
            id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE,
        )
        click.echo(f"🔁 Replay started for cache_key={cache_key}")
        click.echo(f"  Temporal ID: {handle.id}")
        if wait:
            click.echo("⏳ Waiting for replay result...")
            try:
                result = await handle.result()
                click.echo(f"\n✅ Replay completed: {result.summary}")
            except Exception as exc:
                click.echo(f"\n❌ Replay failed: {exc}")

    asyncio.run(_run())


@cli.command("flows")
@click.option("--limit", default=10, show_default=True)
def list_flows(limit: int):
    """List cached flowStates."""
    init_database()
    rows = list_flow_states(limit)
    if not rows:
        click.echo("No cached flow states found.")
        return
    click.echo(f"Showing {len(rows)} cached flow states:")
    for row in rows:
        click.echo(f"- {row['cache_key']} :: {row['prompt']} (updated {row['updated_at']})")


@cli.command("executions")
@click.option("--limit", default=10, show_default=True)
def list_recent_executions(limit: int):
    """Show recent execution summaries."""
    init_database()
    rows = list_executions(limit)
    if not rows:
        click.echo("No execution history yet.")
        return
    click.echo(f"Latest {len(rows)} executions:")
    for row in rows:
        click.echo(f"- #{row['id']} [{row['status']}] cache={row['cache_key']}")
        click.echo(f"    prompt : {row['prompt']}")
        if row.get("summary"):
            click.echo(f"    summary: {row['summary']}")
        click.echo(f"    created: {row['created_at']}")


@cli.command()
@click.argument("cache_key")
def delete_flow(cache_key: str):
    """Delete a cached flowState snapshot."""
    init_database()
    delete_flow_state(cache_key)
    click.echo(f"🗑️  Deleted flow_state for cache_key={cache_key}")


if __name__ == "__main__":
    try:
        validate_config()
    except ValueError as exc:
        raise SystemExit(f"Config error: {exc}") from exc
    cli()


"""Temporal worker for browser automation workflows - cloud configuration."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

from temporalio.client import Client
from temporalio.worker import UnsandboxedWorkflowRunner, Worker

try:
    from temporalio.client import ClientTlsConfig
except ImportError:  # pragma: no cover
    ClientTlsConfig = None

from activities.orchestrator_activity import run_orchestrator
from config import (
    TEMPORAL_ADDRESS,
    TEMPORAL_NAMESPACE,
    validate_config,
)
from workflows import browser_agent


def get_auth_config():
    """Select API key or TLS credentials for Temporal Cloud."""
    api_key = os.getenv("TEMPORAL_API_KEY")
    if api_key:
        return {"api_key": api_key}

    cert_path = os.getenv("TEMPORAL_TLS_CERT_PATH")
    key_path = os.getenv("TEMPORAL_TLS_KEY_PATH")
    ca_path = os.getenv("TEMPORAL_TLS_CA_PATH")

    if cert_path and key_path and ClientTlsConfig:
        with open(cert_path, "rb") as f:
            client_cert = f.read()
        with open(key_path, "rb") as f:
            client_key = f.read()
        server_root_ca_cert = None
        if ca_path and Path(ca_path).exists():
            with open(ca_path, "rb") as f:
                server_root_ca_cert = f.read()
        return {
            "tls": ClientTlsConfig(
                client_cert=client_cert,
                client_private_key=client_key,
                server_root_ca_cert=server_root_ca_cert,
            )
        }

    return {}


async def main():
    try:
        validate_config()
    except ValueError as exc:
        print(f"Configuration error: {exc}")
        return

    auth = get_auth_config()
    try:
        if "api_key" in auth:
            client = await Client.connect(
                target_host=TEMPORAL_ADDRESS,
                namespace=TEMPORAL_NAMESPACE,
                api_key=auth["api_key"],
                tls=True,
            )
            print(f"✅ Connected to Temporal Cloud via API key ({TEMPORAL_ADDRESS})")
        elif "tls" in auth:
            client = await Client.connect(
                target_host=TEMPORAL_ADDRESS,
                namespace=TEMPORAL_NAMESPACE,
                tls=auth["tls"],
            )
            print(f"✅ Connected to Temporal Cloud via TLS ({TEMPORAL_ADDRESS})")
        else:
            client = await Client.connect(
                target_host=TEMPORAL_ADDRESS,
                namespace=TEMPORAL_NAMESPACE,
            )
            print(f"✅ Connected to Temporal at {TEMPORAL_ADDRESS}")
    except Exception as exc:  # pragma: no cover - network errors
        print(f"Failed to connect to Temporal: {exc}")
        return

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


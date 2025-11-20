"""Configuration management for the Temporal Browser Automation AI Agent."""
import os
from typing import Optional
from pathlib import Path

# Try to load from .env files if python-dotenv is available
try:
    from dotenv import load_dotenv
    base_path = Path(__file__).parent
    env_files = [
        base_path / ".env",
        base_path / "env" / ".env",
        base_path / "env" / "cloud.env",
    ]
    for path in env_files:
        if path.exists():
            load_dotenv(path, override=True)
except ImportError:
    # python-dotenv not installed, skip .env loading
    pass

# Temporal configuration
TEMPORAL_ADDRESS: str = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
TEMPORAL_NAMESPACE: str = os.getenv("TEMPORAL_NAMESPACE", "default")
TEMPORAL_API_KEY: Optional[str] = os.getenv("TEMPORAL_API_KEY")
TEMPORAL_TLS_CERT_PATH: Optional[str] = os.getenv("TEMPORAL_TLS_CERT_PATH")
TEMPORAL_TLS_KEY_PATH: Optional[str] = os.getenv("TEMPORAL_TLS_KEY_PATH")
TEMPORAL_TLS_CA_PATH: Optional[str] = os.getenv("TEMPORAL_TLS_CA_PATH")

# Gemini configuration
GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3-pro-preview")

# Browserbase MCP configuration
BROWSERBASE_MCP_URL: str = os.getenv(
    "BROWSERBASE_MCP_URL",
    "https://browserbase-mcp-server.vercel.app/api/mcp"
)

# Database configuration
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "workflows.db")

def validate_config() -> None:
    """Validate that required configuration is present."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable is required")


"""Runtime configuration loaded from environment / .env."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (next to this file)
load_dotenv(Path(__file__).parent / ".env")

MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_MODEL: str = os.getenv("MISTRAL_MODEL", "mistral-small-latest")

NEXUS_HOME: Path = Path.home() / ".nexus"
NEXUS_HOME.mkdir(parents=True, exist_ok=True)

WORKSPACE: Path = Path.home() / "nexus_workspace"
WORKSPACE.mkdir(parents=True, exist_ok=True)

DB_PATH: str = str(NEXUS_HOME / "memory.db")

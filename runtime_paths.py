"""Keep bundled resources separate from writable, upgrade-safe user state."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from scripts.install_kws_model import MODEL_NAME, REQUIRED_FILES


def resource_root() -> Path:
    return Path(__file__).resolve().parent


def user_root() -> Path:
    if not getattr(sys, "frozen", False):
        return resource_root()
    local_app_data = os.environ.get("LOCALAPPDATA")
    base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
    return base / "PersonalJarvis"


def wake_model_dir() -> Path:
    return user_root() / "models" / "kws" / MODEL_NAME


def wake_model_ready() -> bool:
    return all((wake_model_dir() / name).is_file() for name in REQUIRED_FILES)


def keywords_file() -> Path:
    return resource_root() / "models" / "kws" / "keywords.txt"

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml

from backend.app.core.config import ROOT_DIR


def load_yaml_config(name: str) -> Dict[str, Any]:
    path = ROOT_DIR / "configs" / name
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_keywords() -> List[str]:
    return list(load_yaml_config("keywords.yaml").get("keywords", []))


def load_accounts() -> List[str]:
    accounts: List[str] = []
    for file_name in ["media_accounts.yaml", "kol_accounts.yaml"]:
        data = load_yaml_config(file_name)
        for item in data.get("accounts", []):
            if isinstance(item, dict):
                accounts.append(str(item.get("handle", "")).lstrip("@"))
            elif item:
                accounts.append(str(item).lstrip("@"))
    return [account for account in accounts if account]

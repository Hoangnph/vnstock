from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


CONFIG_PATH = Path("assets/config/ssi_api_config.json")


@dataclass
class SSIAPIConfig:
    version: int
    updated_at: Optional[str]
    timezone: str
    market_close_hour_local: int
    date_format_ssi: str
    rate_limit: Dict[str, Any]
    windows: Dict[str, Any]
    pagination: Dict[str, Any]
    base_urls: Dict[str, str]
    endpoints: Dict[str, str]
    primary_sources: Dict[str, str]
    headers: Dict[str, Any]

    @staticmethod
    def load(path: Optional[Path] = None) -> "SSIAPIConfig":
        p = path or CONFIG_PATH
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return SSIAPIConfig(**data)

    def dump(self, path: Optional[Path] = None) -> None:
        p = path or CONFIG_PATH
        with p.open("w", encoding="utf-8") as f:
            json.dump(self.__dict__, f, ensure_ascii=False, indent=2)


def get_endpoint_url(cfg: SSIAPIConfig, key: str) -> str:
    if key == "stock_info":
        return f"{cfg.base_urls['iboard_api']}{cfg.endpoints['stock_info']}"
    if key == "dchart_history":
        return f"{cfg.base_urls['iboard']}{cfg.endpoints['dchart_history']}"
    raise KeyError(f"Unknown endpoint key: {key}")



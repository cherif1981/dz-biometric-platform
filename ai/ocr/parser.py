import re
from typing import Optional

import yaml


def load_patterns(config_path: str = "configs/ocr_config.yaml") -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["fields"]


def parse_fields(text: str, config_path: str = "configs/ocr_config.yaml") -> dict:
    patterns = load_patterns(config_path)
    result = {}
    for key, meta in patterns.items():
        match = re.search(meta["pattern"], text, re.IGNORECASE | re.MULTILINE)
        if match:
            result[key] = (
                match.group(1).strip() if match.groups() else match.group(0).strip()
            )
        else:
            result[key] = None
    return result
"""JSON investigation dossier generator."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


def generate_json_report(
    target: str,
    level: str,
    output_path: Path,
    **kwargs,
) -> Path:
    """Generate structured JSON report for programmatic consumption."""
    data = {
        "target": target,
        "level": level,
        "timestamp": datetime.now().isoformat(),
        "findings": {},
    }

    for k, v in kwargs.items():
        if v is not None:
            if hasattr(v, "__dataclass_fields__"):
                data["findings"][k] = asdict(v)
            elif isinstance(v, list) and v and hasattr(v[0], "__dataclass_fields__"):
                data["findings"][k] = [asdict(item) for item in v]
            else:
                data["findings"][k] = str(v)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return output_path

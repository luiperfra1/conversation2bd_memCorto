# triplets2bd/utils/io.py
from __future__ import annotations
import json
from typing import List, Tuple, Optional

Triplet = Tuple[str, str, str]

def load_triplets_from_json_str(s: str) -> List[Triplet]:
    data = json.loads(s)
    return [(str(a), str(b), str(c)) for a, b, c in data]

def load_triplets_from_file(path: str) -> List[Triplet]:
    if path.lower().endswith(".json"):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [(str(a), str(b), str(c)) for a, b, c in data]

    rows: List[Triplet] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if not raw:
                continue
            if raw.startswith("(") and raw.endswith(")"):
                raw = raw[1:-1]
            parts = [p.strip() for p in raw.split(",")]
            if len(parts) != 3:
                raise ValueError(f"Línea inválida (esperado 3 campos): {line}")
            rows.append((parts[0], parts[1], parts[2]))
    return rows
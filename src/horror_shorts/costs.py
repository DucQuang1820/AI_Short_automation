"""Ghi lại chi phí ước tính của từng video vào output/<id>/costs.json."""
import json
from pathlib import Path


class CostTracker:
    def __init__(self, cfg: dict, out: Path):
        self.prices = cfg.get("costs", {})
        self.path = out / "costs.json"
        self.items = json.loads(self.path.read_text()) if self.path.exists() else []

    def add(self, kind: str, qty: float = 1.0, note: str = ""):
        usd = round(self.prices.get(kind, 0.0) * qty, 4)
        self.items.append({"kind": kind, "qty": round(qty, 2), "usd": usd, "note": note})
        self.path.write_text(json.dumps(self.items, indent=2, ensure_ascii=False))

    @property
    def total(self) -> float:
        return round(sum(i["usd"] for i in self.items), 3)

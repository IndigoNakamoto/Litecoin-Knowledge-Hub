"""
Persistent tracking for LLM cost metrics.

This module keeps a simple on-disk snapshot of lifetime Gemini spend so that
Prometheus counters can be restored after process restarts. The snapshot path
defaults to ``backend/monitoring/data/llm_cost_totals.json`` but can be overridden
with the ``LLM_COST_SNAPSHOT_PATH`` environment variable.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Dict

SNAPSHOT_PATH_ENV = "LLM_COST_SNAPSHOT_PATH"
DEFAULT_SNAPSHOT_PATH = Path(__file__).with_name("data") / "llm_cost_totals.json"

_lock = threading.Lock()
_cache: Dict[str, Dict[str, float]] | None = None
_preloaded = False


def _get_snapshot_path() -> Path:
    custom_path = os.getenv(SNAPSHOT_PATH_ENV)
    if custom_path:
        return Path(custom_path)
    return DEFAULT_SNAPSHOT_PATH


def _load_snapshot() -> Dict[str, Dict[str, float]]:
    global _cache
    if _cache is not None:
        return _cache

    snapshot_path = _get_snapshot_path()
    if snapshot_path.exists():
        try:
            with snapshot_path.open("r", encoding="utf-8") as fh:
                _cache = json.load(fh)
        except json.JSONDecodeError:
            # Corrupted snapshot – start fresh but keep the file around.
            _cache = {}
    else:
        _cache = {}

    return _cache


def _write_snapshot(data: Dict[str, Dict[str, float]]) -> None:
    snapshot_path = _get_snapshot_path()
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = snapshot_path.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
    tmp_path.replace(snapshot_path)


def record_llm_cost(model: str, operation: str, amount: float) -> float:
    """
    Persist the lifetime total for the given LLM model/operation.

    Args:
        model: The model identifier (e.g., ``gemini-2.0-flash-lite``).
        operation: Operation label (e.g., ``generate`` or ``embed``).
        amount: Incremental cost in USD to add.

    Returns:
        The updated lifetime total for the model/operation.
    """
    if amount <= 0:
        # No-op for zero or negative adjustments.
        return get_llm_cost_total(model, operation)

    with _lock:
        data = _load_snapshot()
        model_totals = data.setdefault(model, {})
        new_total = model_totals.get(operation, 0.0) + amount
        model_totals[operation] = new_total
        _write_snapshot(data)
        return new_total


def get_llm_cost_total(model: str, operation: str) -> float:
    """Retrieve the persisted lifetime total for the given model/operation."""
    data = _load_snapshot()
    return data.get(model, {}).get(operation, 0.0)


def preload_prometheus_counters() -> None:
    """
    Seed ``llm_cost_usd_total`` counters with persisted lifetime totals.

    Should be called exactly once during application startup.
    """
    global _preloaded
    if _preloaded:
        return

    try:
        from backend.monitoring.metrics import llm_cost_usd_total
    except ImportError:
        # metrics not ready – silently skip.
        return

    with _lock:
        data = _load_snapshot()
        for model, operations in data.items():
            for operation, total in operations.items():
                if total > 0:
                    llm_cost_usd_total.labels(
                        model=model,
                        operation=operation,
                    ).inc(total)
        _preloaded = True



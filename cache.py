# -*- coding: utf-8 -*-
"""
cache.py — Cache LRU de decisiones System One.

Soporta mimo_cache_stats() — útil para detectar patrones recurrentes
que el agente OpenCode consulta antes de volver a enrutar.

El cache es:
  - Thread-safe (Lock)
  - Persistente a disco (JSONL append-only en logs/cache.jsonl)
  - Con stats que devuelven hit_rate, top_actions, entries
  - LRU aproximada (elimina la mitad más antigua cuando llena)
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from collections import Counter
from pathlib import Path
from typing import Any, Optional


class DecisionCache:
    """LRU thread-safe con persistencia JSONL."""

    def __init__(self, max_entries: int = 512):
        self.max = int(os.getenv("MIMO_CACHE_MAX", str(max_entries)))
        self._lock = threading.Lock()
        self._store: dict[str, dict[str, Any]] = {}
        self._hits = 0
        self._misses = 0
        self._path = Path(os.getenv("MIMO_CACHE_FILE", "./logs/cache.jsonl"))
        self._path.parent.mkdir(parents=True, exist_ok=True)
        # Touch para verificar permisos de escritura
        try:
            self._path.touch(exist_ok=True)
        except OSError:
            # Si no podemos escribir, cache en RAM only (mejor que romper)
            self._path = None  # type: ignore

    @staticmethod
    def _key(state: str) -> str:
        return hashlib.sha1(state.encode("utf-8")).hexdigest()

    def get(self, state: str) -> Optional[dict[str, Any]]:
        """Devuelve la decisión cacheada o None."""
        with self._lock:
            k = self._key(state)
            if k in self._store:
                self._hits += 1
                # Refrescar timestamp para LRU
                self._store[k]["_last_access"] = time.time()
                return {kk: vv for kk, vv in self._store[k].items()
                        if not kk.startswith("_")}
            self._misses += 1
            return None

    def put(self, state: str, decision: dict[str, Any]) -> None:
        """Persiste una decisión en cache RAM + JSONL."""
        with self._lock:
            # LRU: si lleno, eliminar la mitad más antigua
            if len(self._store) >= self.max:
                oldest = sorted(
                    self._store.items(),
                    key=lambda kv: kv[1].get("_last_access",
                                            kv[1].get("ts", 0)),
                )
                for k, _ in oldest[: self.max // 2]:
                    self._store.pop(k, None)

            k = self._key(state)
            entry = {**decision, "ts": time.time(), "_last_access": time.time()}
            self._store[k] = entry

            # Append a disco (no rompe si falla)
            if self._path:
                try:
                    with self._path.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(
                            {"k": k, **{kk: vv for kk, vv in entry.items()
                                        if not kk.startswith("_")}},
                            ensure_ascii=False, default=str,
                        ) + "\n")
                except OSError:
                    pass

    def stats(self) -> dict[str, Any]:
        """Devuelve métricas útiles para mimo_cache_stats()."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total) if total else 0.0
            actions = Counter(
                v.get("chosen_action") for v in self._store.values()
                if v.get("chosen_action")
            )
            plans = Counter(
                v.get("plan") for v in self._store.values()
                if v.get("plan")
            )
            return {
                "entries": len(self._store),
                "max_entries": self.max,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 4),
                "top_actions": actions.most_common(5),
                "top_plans": plans.most_common(5),
                "cache_file": str(self._path) if self._path else None,
            }

    def clear(self) -> None:
        """Vacía el cache RAM (no toca el disco)."""
        with self._lock:
            self._store.clear()
            self._hits = 0
            self._misses = 0


# Singleton — todos los procesos Python del mimo_patch comparten el mismo
_CACHE: Optional[DecisionCache] = None
_CACHE_LOCK = threading.Lock()


def get_cache() -> DecisionCache:
    global _CACHE
    if _CACHE is None:
        with _CACHE_LOCK:
            if _CACHE is None:
                _CACHE = DecisionCache()
    return _CACHE

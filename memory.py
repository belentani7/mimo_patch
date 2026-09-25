# -*- coding: utf-8 -*-
"""
memory.py — Memoria jerárquica con fallback graceful.

Implementa la política de memoria del leak de Fable 5.1:
  - Corto plazo: Redis (fallback JSONL si no hay Redis)
  - Largo plazo: PostgreSQL + pgvector (fallback JSONL si no hay PG)
  - Sensitive topics: etiquetados (health, religion) — no se persisten
  - Banking / self-harm: NUNCA persistidos

La memoria es OPCIONAL — el mimo_patch funciona sin memoria,
pero con memoria el cache es más eficiente y el contexto se mantiene.
"""
from __future__ import annotations

import json
import os
import time
import threading
from pathlib import Path
from typing import Any, Optional


# Sensitive topics (igual que gate.py SENSITIVE_TOPICS)
SENSITIVE_TOPICS_LOWER = {
    "salud", "health", "medicación", "medication",
    "religión", "religion", "religió", "faith",
    "autolesión", "self-harm", "self_harm", "suicide", "suicidio",
}

# Never persisted
NEVER_PERSIST_PATTERNS = [
    # Card numbers, IBAN, SSN, CVV
    r"\b(?:\d[ -]*?){13,16}\b",
    r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,32}\b",
    r"\b\d{3}-\d{2}-\d{4}\b",
    r"\bCVV\s*:?\s*\d{3,4}\b",
]


class MemoryStore:
    """Interface común para corto y largo plazo."""

    def get(self, key: str) -> Optional[dict[str, Any]]:
        raise NotImplementedError

    def put(self, key: str, value: dict[str, Any], topic: Optional[str] = None) -> None:
        raise NotImplementedError

    def search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        raise NotImplementedError

    def is_available(self) -> bool:
        return False


class JSONLMemory(MemoryStore):
    """Fallback en disco — siempre disponible."""

    def __init__(self, path: str):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.touch(exist_ok=True)
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[dict[str, Any]]:
        with self._lock:
            with self._path.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        if entry.get("key") == key:
                            return entry.get("value")
                    except json.JSONDecodeError:
                        continue
        return None

    def put(self, key: str, value: dict[str, Any],
            topic: Optional[str] = None) -> None:
        if _should_skip_persist(value, topic):
            return
        entry = {
            "key": key,
            "value": _sanitize_value(value),
            "topic": topic,
            "ts": time.time(),
        }
        with self._lock:
            with self._path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")

    def search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """Búsqueda simple por substring (sin embeddings)."""
        results = []
        with self._lock:
            with self._path.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        v = entry.get("value", {})
                        # Match en cualquier valor string
                        for vv in (v.values() if isinstance(v, dict) else [v]):
                            if isinstance(vv, str) and query.lower() in vv.lower():
                                results.append(entry)
                                break
                    except json.JSONDecodeError:
                        continue
        return results[:k]

    def is_available(self) -> bool:
        return True


class RedisMemory(MemoryStore):
    """Corto plazo — TTL corto (ej: 1h)."""

    def __init__(self, url: str = "redis://localhost:6379/0"):
        self._url = url
        self._redis = None
        try:
            import redis  # type: ignore
            self._redis = redis.from_url(url, decode_responses=True)
            self._redis.ping()
        except Exception:
            self._redis = None

    def get(self, key: str) -> Optional[dict[str, Any]]:
        if not self._redis:
            return None
        try:
            v = self._redis.get(f"mimo:{key}")
            return json.loads(v) if v else None
        except Exception:
            return None

    def put(self, key: str, value: dict[str, Any],
            topic: Optional[str] = None, ttl: int = 3600) -> None:
        if not self._redis or _should_skip_persist(value, topic):
            return
        try:
            self._redis.setex(
                f"mimo:{key}",
                ttl,
                json.dumps(_sanitize_value(value), ensure_ascii=False, default=str),
            )
        except Exception:
            pass

    def search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        # Redis SCAN con MATCH — devuelve keys, luego hydrate
        if not self._redis:
            return []
        results = []
        try:
            for key in self._redis.scan_iter(match="mimo:*", count=100):
                v = self._redis.get(key)
                if v:
                    entry = json.loads(v)
                    if (isinstance(entry, dict) and
                        query.lower() in json.dumps(entry,
                                                      ensure_ascii=False).lower()):
                        results.append({"key": key[5:], "value": entry})
                        if len(results) >= k:
                            break
        except Exception:
            pass
        return results

    def is_available(self) -> bool:
        return self._redis is not None


class PgVectorMemory(MemoryStore):
    """Largo plazo — PostgreSQL + pgvector para similarity search."""

    def __init__(self, dsn: str = "postgresql://localhost/mimo"):
        self._dsn = dsn
        self._conn = None
        try:
            import psycopg  # type: ignore
            self._conn = psycopg.connect(dsn)
            # Crear tabla si no existe (best-effort)
            with self._conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS mimo_memory (
                        key TEXT PRIMARY KEY,
                        value JSONB NOT NULL,
                        topic TEXT,
                        embedding VECTOR(384),
                        ts REAL NOT NULL
                    )
                """)
                self._conn.commit()
        except Exception:
            self._conn = None

    def get(self, key: str) -> Optional[dict[str, Any]]:
        if not self._conn:
            return None
        try:
            with self._conn.cursor() as cur:
                cur.execute("SELECT value FROM mimo_memory WHERE key = %s", (key,))
                row = cur.fetchone()
                return row[0] if row else None
        except Exception:
            return None

    def put(self, key: str, value: dict[str, Any],
            topic: Optional[str] = None) -> None:
        if not self._conn or _should_skip_persist(value, topic):
            return
        try:
            with self._conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO mimo_memory (key, value, topic, ts)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (key) DO UPDATE SET
                        value = EXCLUDED.value,
                        topic = EXCLUDED.topic,
                        ts = EXCLUDED.ts
                """, (
                    key,
                    json.dumps(_sanitize_value(value), ensure_ascii=False),
                    topic,
                    time.time(),
                ))
                self._conn.commit()
        except Exception:
            pass

    def search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """ILIKE search (sin embeddings — fallback si no hay pgvector)."""
        if not self._conn:
            return []
        try:
            with self._conn.cursor() as cur:
                cur.execute("""
                    SELECT key, value FROM mimo_memory
                    WHERE value::text ILIKE %s
                    ORDER BY ts DESC
                    LIMIT %s
                """, (f"%{query}%", k))
                return [{"key": r[0], "value": r[1]} for r in cur.fetchall()]
        except Exception:
            return []

    def is_available(self) -> bool:
        return self._conn is not None


# ═════════════════════════════════════════════════════════════
# Sanitización — nunca persistir banking/self-harm
# ═════════════════════════════════════════════════════════════
def _should_skip_persist(value: dict[str, Any], topic: Optional[str]) -> bool:
    """True si el value o topic contienen datos que NUNCA se persisten."""
    if topic and topic.lower() in NEVER_PERSIST_TOPICS:
        return True
    blob = json.dumps(value, ensure_ascii=False, default=str).lower()
    import re
    for pat in NEVER_PERSIST_PATTERNS:
        if re.search(pat, blob, re.IGNORECASE):
            return True
    if any(w in blob for w in ("autolesión", "suicide", "self-harm", "self_harm")):
        return True
    return False


NEVER_PERSIST_TOPICS = {"banking", "self-harm", "self_harm"}


def _sanitize_value(value: dict[str, Any]) -> dict[str, Any]:
    """Quita claves con banking/sensitive antes de persistir."""
    if not isinstance(value, dict):
        return {"_raw": str(value)[:200]}
    safe = {}
    for k, v in value.items():
        k_lower = k.lower()
        if any(w in k_lower for w in ("card", "iban", "ssn", "cvv", "password")):
            safe[k] = "[REDACTED]"
        elif isinstance(v, str) and _looks_sensitive(v):
            safe[k] = "[REDACTED]"
        else:
            safe[k] = v
    return safe


def _looks_sensitive(s: str) -> bool:
    import re
    for pat in NEVER_PERSIST_PATTERNS:
        if re.search(pat, s, re.IGNORECASE):
            return True
    return False


# ─── Singletons con fallback automático ─────────────────────
_short_term: Optional[MemoryStore] = None
_long_term: Optional[MemoryStore] = None
_init_lock = threading.Lock()


def get_short_term_memory() -> MemoryStore:
    """Devuelve Redis si está disponible, si no JSONL."""
    global _short_term
    if _short_term is None:
        with _init_lock:
            if _short_term is None:
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
                redis_mem = RedisMemory(redis_url)
                if redis_mem.is_available():
                    _short_term = redis_mem
                else:
                    _short_term = JSONLMemory("./logs/short_term.jsonl")
    return _short_term


def get_long_term_memory() -> MemoryStore:
    """Devuelve PgVectorMemory si PG está disponible, si no JSONL."""
    global _long_term
    if _long_term is None:
        with _init_lock:
            if _long_term is None:
                pg_dsn = os.getenv("PG_DSN", "postgresql://localhost/mimo")
                pg_mem = PgVectorMemory(pg_dsn)
                if pg_mem.is_available():
                    _long_term = pg_mem
                else:
                    _long_term = JSONLMemory("./logs/long_term.jsonl")
    return _long_term

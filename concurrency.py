# -*- coding: utf-8 -*-
"""
concurrency.py — Helpers de asincronía para el router.

Mimo Patch por defecto es síncrono (CLI friendly). Pero si quieres
procesar miles de estados en paralelo (ej: clasificar tickets masivamente),
estas funciones te permiten hacerlo con asyncio.

Ejemplo:
    import asyncio
    from concurrency import route_batch_async

    states = ["ticket 1", "ticket 2", ...]
    results = asyncio.run(route_batch_async(states, max_concurrency=10))
"""
from __future__ import annotations

import asyncio
from typing import Any


async def route_one_async(state: str, force_heavy: bool = False) -> dict[str, Any]:
    """Wrapper async para mimo_route — ejecuta en thread pool."""
    import functools
    from concurrent.futures import ThreadPoolExecutor
    from mimo_patch import mimo_route  # type: ignore

    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(max_workers=1) as pool:
        fn = functools.partial(mimo_route, state, force_heavy=force_heavy)
        return await loop.run_in_executor(pool, fn)


async def route_batch_async(
    states: list[str],
    max_concurrency: int = 10,
    force_heavy: bool = False,
) -> list[dict[str, Any]]:
    """
    Ejecuta mimo_route en paralelo para una lista de estados.
    Usa Semaphore para limitar concurrencia (default 10).
    """
    sem = asyncio.Semaphore(max_concurrency)
    async def _one(state: str) -> dict[str, Any]:
        async with sem:
            try:
                return await route_one_async(state, force_heavy=force_heavy)
            except Exception as e:
                return {
                    "error": f"{type(e).__name__}: {e}",
                    "plan": "NOTIFY_HUMAN",
                    "degraded": True,
                    "urgency_score": 1.0,
                }
    return await asyncio.gather(*[_one(s) for s in states])


def route_batch_sync(
    states: list[str],
    max_concurrency: int = 10,
    force_heavy: bool = False,
) -> list[dict[str, Any]]:
    """Versión síncrona de route_batch_async para CLI."""
    return asyncio.run(route_batch_async(states, max_concurrency, force_heavy))

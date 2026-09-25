# -*- coding: utf-8 -*-
"""
Tests del cache LRU.
"""
import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cache import DecisionCache


@pytest.fixture
def tmp_cache():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["MIMO_CACHE_FILE"] = os.path.join(tmp, "cache.jsonl")
        os.environ["MIMO_NOTIFY_FILE"] = os.path.join(tmp, "notify.jsonl")
        c = DecisionCache(max_entries=10)
        yield c


class TestCache:
    def test_put_and_get(self, tmp_cache):
        tmp_cache.put("state1", {"chosen_action": "apply_refund",
                                  "plan": "PROPOSE_AND_WAIT"})
        got = tmp_cache.get("state1")
        assert got is not None
        assert got["chosen_action"] == "apply_refund"
        assert got["plan"] == "PROPOSE_AND_WAIT"

    def test_miss(self, tmp_cache):
        got = tmp_cache.get("nonexistent")
        assert got is None

    def test_stats(self, tmp_cache):
        tmp_cache.put("state1", {"chosen_action": "apply_refund"})
        tmp_cache.get("state1")  # hit
        tmp_cache.get("state2")  # miss
        stats = tmp_cache.stats()
        assert stats["entries"] == 1
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert 0 < stats["hit_rate"] <= 1.0

    def test_lru_eviction(self, tmp_cache):
        # max_entries=10, metemos 12 → deben expulsar 5 (mitad)
        for i in range(12):
            tmp_cache.put(f"state{i}", {"chosen_action": "ignore_spam"})
        stats = tmp_cache.stats()
        assert stats["entries"] <= 10
        # Los primeros 5 deberían haber sido expulsados
        assert tmp_cache.get("state0") is None

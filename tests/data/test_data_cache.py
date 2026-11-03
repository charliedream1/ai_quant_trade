import uuid

import src.data.eastmoney as eastmoney
from src.data.eastmoney import EastmoneyDataSource


def test_stale_cache_enters_failure_cooldown():
    key = f"test-cooldown:{uuid.uuid4()}"
    calls = 0

    def loader():
        nonlocal calls
        calls += 1
        if calls == 1:
            return [{"value": "cached"}]
        raise RuntimeError("provider timeout")

    try:
        assert eastmoney._cached(key, 0, "test", "provider", loader)[0]["value"] == "cached"
        assert eastmoney._cached(key, 0, "test", "provider", loader)[0]["value"] == "cached"
        assert eastmoney._cached(key, 0, "test", "provider", loader)[0]["value"] == "cached"
        assert calls == 2
    finally:
        with eastmoney._CACHE_LOCK:
            eastmoney._CACHE.pop(key, None)
            eastmoney._RETRY_AFTER.pop(key, None)


def test_sector_cache_fetches_once_and_slices(monkeypatch):
    key = "sectors:industry"
    provider = EastmoneyDataSource()
    calls = []

    def loader(board: str, limit: int):
        calls.append((board, limit))
        return [{"code": str(index), "name": str(index), "change_pct": index} for index in range(limit)]

    with eastmoney._CACHE_LOCK:
        eastmoney._CACHE.pop(key, None)
        eastmoney._RETRY_AFTER.pop(key, None)
    monkeypatch.setattr(provider, "_load_sectors", loader)

    try:
        assert len(provider.sectors(limit=8)) == 8
        assert len(provider.sectors(limit=20)) == 20
        assert calls == [("industry", 100)]
    finally:
        with eastmoney._CACHE_LOCK:
            eastmoney._CACHE.pop(key, None)
            eastmoney._RETRY_AFTER.pop(key, None)

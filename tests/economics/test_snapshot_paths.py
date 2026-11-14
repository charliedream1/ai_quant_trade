"""Atomic research snapshots remain writable near the Windows legacy path boundary."""

from src.engine.economics.store import EconomicStore, digest

WINDOWS_LEGACY_PATH_LIMIT = 260


def test_snapshot_write_near_legacy_path_limit(tmp_path):
    payload = {"kind": "fixture", "value": "Unicode financial observation: 财务"}
    name = digest(payload) + ".json"
    suffix = len("/snapshots/") + len(name)
    root_length = WINDOWS_LEGACY_PATH_LIMIT - suffix - len("guard")
    padding = root_length - len(str(tmp_path)) - len("/")
    assert padding > 0, "Use a shorter scratch root for this legacy-path boundary test"
    store = EconomicStore(tmp_path / ("x" * padding))
    target = store.root / "snapshots" / name
    assert len(str(target)) < WINDOWS_LEGACY_PATH_LIMIT
    assert len(str(target)) + len("." + "x" * 32 + ".tmp") >= WINDOWS_LEGACY_PATH_LIMIT
    saved = store.save(payload)
    assert store.read(saved["snapshot_id"]) == saved

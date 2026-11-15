"""Section observers preserve normal services and publish before dependent work."""

import pytest

from src.core.panel_updates import PANEL_UPDATE, observation_ready, observe_references, panel_ready, panel_values


def test_sequential_values_publish_before_next_builder():
    events = []
    token = PANEL_UPDATE.set(lambda index, value: events.append((index, value)))

    def second():
        assert events == [(0, "table ready")]
        return "chart ready"

    try:
        result = panel_values((lambda: "table ready", second))
    finally:
        PANEL_UPDATE.reset(token)
    assert result == ("table ready", "chart ready")
    assert events[-1] == (1, "chart ready")
    assert panel_values((lambda: 3, lambda: 4)) == (3, 4)


def test_reference_observer_is_scoped_and_restored():
    events = []
    token = PANEL_UPDATE.set(lambda index, value: events.append((index, value)))
    try:
        with observe_references(2, lambda records: {"citations": records}):
            observation_ready("knowledge.references", ["declared original"])
        observation_ready("knowledge.references", ["outside scope"])
    finally:
        PANEL_UPDATE.reset(token)
    assert events == [(2, {"citations": ["declared original"]})]


def test_failed_section_retains_cumulative_completed_output():
    from src.frontend.common.callbacks import _section_call

    def load():
        panel_ready(0, {"plot": "already rendered"})
        raise ValueError("second section failed")

    updates = _section_call(load, (), {}, 2, [["chart"], ["table"]])
    next(updates)
    completed = next(updates)
    failed = next(updates)
    assert failed[0] == completed[0]
    assert "section-ready" in failed[0]["elem_classes"]
    assert "section-failed" in failed[1]["elem_classes"]
    with pytest.raises(ValueError, match="second section failed"):
        next(updates)


def test_financial_evidence_precedes_chart_from_one_snapshot(client, monkeypatch):
    from src.frontend.service import economics

    snapshot = {"snapshot_id": "declared-one", "scope": "declared period", "gaps": []}
    loads, events = [], []

    class Analysis:
        def macro(self, *args, **kwargs):
            loads.append("once")
            return snapshot

    def chart(value):
        assert value is snapshot
        assert events == [
            (0, "快照 `declared-one` · declared period"),
            (1, "table"),
            (3, snapshot),
            (4, "declared-one"),
        ]
        return "chart"

    monkeypatch.setattr(economics, "EconomicAnalysis", Analysis)
    monkeypatch.setattr(economics, "economic_table", lambda value: "table")
    monkeypatch.setattr(economics, "economic_figure", chart)
    token = PANEL_UPDATE.set(lambda index, value: events.append((index, value)))
    try:
        result = economics.EconomicUIMixin().economic_load("macro", [], "", "", "", False)
    finally:
        PANEL_UPDATE.reset(token)
    assert loads == ["once"]
    assert result[3] is snapshot
    assert events[-1] == (2, "chart")

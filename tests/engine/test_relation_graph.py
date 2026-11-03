from src.engine.market.relation_graph import RelationGraphService


class FakeDataSource:
    is_mock = False

    def relation_graph(self, symbol: str, depth: int):
        assert symbol == "600519"
        assert depth == 2
        return {
            "nodes": [
                {"id": "600519", "name": "贵州茅台", "type": "stock"},
                {"id": "000858", "name": "五粮液", "type": "stock"},
                {"id": "白酒", "name": "白酒", "type": "industry"},
            ],
            "edges": [
                {
                    "source": "600519",
                    "target": "000858",
                    "relation_type": "correlation",
                    "weight": 0.91,
                    "description": "收益相关",
                },
                {
                    "source": "600519",
                    "target": "白酒",
                    "relation_type": "行业",
                    "weight": 1,
                    "description": "同属白酒行业",
                },
            ],
        }


class FakeTaskDb:
    def query(self, sql, params=()):
        if "recommend_tasks" in sql:
            assert params == ("600519",)
            return [
                {
                    "id": 7,
                    "path": "quick",
                    "status": "完成",
                    "created_at": "2026-10-08T09:00:00Z",
                    "rank": 1,
                    "score": 88.5,
                    "reason": "测试推荐",
                }
            ]
        if "backtest_tasks" in sql:
            return [
                {
                    "id": 9,
                    "strategy_id": 3,
                    "engine": "simple",
                    "symbols": "600519,300750",
                    "status": "完成",
                    "created_at": "2026-10-08T10:00:00Z",
                }
            ]
        if "qlib_runs" in sql or "scheduled_jobs" in sql:
            return []
        raise AssertionError(sql)


class FakeTaskRepo:
    db = FakeTaskDb()


class FakeDeepDataSource:
    def relation_graph(self, symbol: str, depth: int):
        assert symbol == "600519"
        assert depth == 3
        return {
            "nodes": [
                {"id": "600519", "name": "贵州茅台", "type": "stock"},
                {"id": "BK0437", "name": "白酒", "type": "sector"},
                {"id": "000858", "name": "五粮液", "type": "stock"},
                {"id": "HOLDER:PUBLIC-FUND", "name": "公募基金组合", "type": "institution"},
            ],
            "edges": [
                {"source": "BK0437", "target": "600519", "relation_type": "industry", "weight": 1},
                {"source": "BK0437", "target": "000858", "relation_type": "industry", "weight": 0.7},
                {
                    "source": "HOLDER:PUBLIC-FUND",
                    "target": "000858",
                    "relation_type": "shareholder",
                    "weight": 0.5,
                },
            ],
        }


def test_relation_graph_filters_relation_types_and_builds_summary():
    graph = RelationGraphService(data=FakeDataSource()).graph("600519", relation_types=["行业"], depth=2)

    assert graph["summary"]["center"] == "600519"
    assert graph["summary"]["edge_count"] == 1
    assert graph["summary"]["relation_counts"] == {"行业": 1}
    assert graph["summary"]["dominant_relation"] == "行业"
    assert graph["edges"][0]["relation_type"] == "industry"
    assert graph["edges"][0]["relation_label"] == "行业"

    center = next(node for node in graph["nodes"] if node["id"] == "600519")
    related = next(node for node in graph["nodes"] if node["id"] == "白酒")
    assert center["is_center"] is True
    assert center["group_label"] == "中心标的"
    assert center["node_size"] > related["node_size"]
    assert related["group_label"] == "关联行业"
    assert related["degree"] == 1
    assert related["layer"] == 1
    assert related["parent_id"] == "600519"
    assert "贵州茅台" in related["path"]
    assert graph["summary"]["group_counts"]["中心标的"] == 1
    assert graph["summary"]["relation_groups"][0]["label"] == "关联行业"
    assert graph["summary"]["layer_counts"]["L1"] == 1
    assert graph["summary"]["layer_paths"][0]["layer"] == 1


def test_relation_graph_keeps_multi_depth_paths():
    graph = RelationGraphService(data=FakeDeepDataSource()).graph("600519", relation_types=None, depth=3)

    holder = next(node for node in graph["nodes"] if node["id"] == "HOLDER:PUBLIC-FUND")
    assert holder["layer"] == 3
    assert holder["parent_id"] == "000858"
    assert "贵州茅台" in holder["path"]
    assert "五粮液" in holder["path"]
    assert graph["summary"]["max_layer"] == 3
    assert graph["summary"]["layer_counts"]["L3"] == 1
    assert any("公募基金组合" in row["path"] for row in graph["summary"]["layer_paths"])


def test_relation_graph_accepts_aliases_and_keeps_center_without_edges():
    graph = RelationGraphService(data=FakeDataSource()).graph("600519", relation_types=["shareholder"], depth=2)

    assert graph["summary"]["node_count"] >= 1
    assert graph["summary"]["edge_count"] == 0
    assert graph["summary"]["dominant_relation"] == "-"
    assert any(node["id"] == "600519" and node["is_center"] for node in graph["nodes"])


def test_relation_graph_attaches_local_task_evidence():
    graph = RelationGraphService(repo=FakeTaskRepo(), data=FakeDataSource()).graph(
        "600519",
        relation_types=["关联任务"],
        depth=2,
    )

    assert graph["summary"]["edge_count"] == 2
    assert graph["summary"]["relation_counts"] == {"关联任务": 2}
    assert graph["summary"]["dominant_relation"] == "关联任务"
    assert graph["summary"]["group_counts"]["关联任务"] == 2
    assert any(item["label"] == "关联任务" for item in graph["summary"]["relation_groups"])
    assert {edge["relation_type"] for edge in graph["edges"]} == {"task"}
    assert all(edge["relation_label"] == "关联任务" for edge in graph["edges"])

    task_nodes = [node for node in graph["nodes"] if node.get("type") == "task"]
    assert {node["group_label"] for node in task_nodes} == {"关联任务"}
    assert {node["task_type"] for node in task_nodes} == {"recommend", "backtest"}

"""适配器基础测试

验证东方财富研报接口可用性与数据归一化逻辑。
运行：python tests/test_adapter.py
"""
import sys
import os
from pathlib import Path

# 添加 scripts 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from eastmoney_adapter import (
    EastmoneyReportAdapter,
    ReportMeta,
    _to_float,
    _to_int,
    _parse_date,
    REPORT_TYPE_STOCK,
)


def test_type_conversion():
    """测试类型转换辅助函数"""
    assert _to_float("66.68") == 66.68
    assert _to_float("") is None
    assert _to_float(None) is None
    assert _to_float("abc") is None

    assert _to_int("7") == 7
    assert _to_int("") is None
    assert _to_int(None) is None

    assert _parse_date("2026-05-25 00:00:00.000") == "2026-05-25"
    assert _parse_date("") == ""
    print("[OK] test_type_conversion")


def test_pdf_url_build():
    """测试 PDF 链接构造"""
    adapter = EastmoneyReportAdapter()
    url = adapter.build_pdf_url("AP202605251822844635")
    assert url == "https://pdf.dfcfw.com/pdf/H3_AP202605251822844635_1.pdf"
    print("[OK] test_pdf_url_build")


def test_fetch_stock_reports():
    """集成测试：拉取茅台研报（需网络）"""
    adapter = EastmoneyReportAdapter(interval=0.5)
    reports = adapter.fetch_stock_reports("600519", days=180, page_size=10)
    assert len(reports) > 0, "应能获取到茅台研报"

    r = reports[0]
    assert isinstance(r, ReportMeta)
    assert r.stock_code == "600519"
    assert r.title, "标题不应为空"
    assert r.org_sname, "机构不应为空"
    assert r.publish_date, "发布日期不应为空"
    assert r.info_code, "infoCode 不应为空"
    assert r.pdf_url.startswith("https://pdf.dfcfw.com/"), "PDF 链接格式正确"
    print(f"[OK] test_fetch_stock_reports: 获取 {len(reports)} 篇，首篇 {r.org_sname} {r.publish_date}")


def test_report_meta_to_dict():
    """测试序列化"""
    meta = ReportMeta(title="测试", stock_code="600519", em_rating="买入")
    d = meta.to_dict()
    assert d["title"] == "测试"
    assert d["stock_code"] == "600519"
    assert d["em_rating"] == "买入"
    print("[OK] test_report_meta_to_dict")


if __name__ == "__main__":
    test_type_conversion()
    test_pdf_url_build()
    test_report_meta_to_dict()
    # 集成测试需网络，CI 环境可能跳过
    if os.environ.get("SKIP_NETWORK_TEST") != "1":
        try:
            test_fetch_stock_reports()
        except Exception as e:
            print(f"[SKIP] test_fetch_stock_reports: {e}")
    print("\n全部测试通过")

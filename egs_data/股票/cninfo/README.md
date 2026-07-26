# 1. 简介

巨潮资讯网（cninfo.com.cn）是中国证监会指定的法定信息披露网站，
提供上市公司公告、年报、季报、临时公告等官方披露信息，数据权威可靠。

- 官网: http://www.cninfo.com.cn/
- API：无官方文档，但可通过 HTTP 请求调用其查询接口

优点：
* 官方指定信息披露平台，数据权威
* 覆盖所有A股上市公司
* 包含年报、季报、临时公告等完整披露信息
* 支持按公告类型、日期、公司筛选

缺点：
* 无官方 API 文档
* 接口可能随网站更新而变化
* 返回数据为公告列表，需进一步下载 PDF 获取详细内容

# 2. 接口说明

| 接口 | 用途 |
|------|------|
| /new/hisAnnouncement/query | 查询历史公告 |
| /new/disclosure/stock | 查询个股公告 |
| /new/data/szse_stock | 获取股票列表 |

# 3. 公告类型代码

| category值 | 说明 |
|------------|------|
| category_ndbg_szsh | 年度报告 |
| category_bndbg_szsh | 半年度报告 |
| category_yjdbg_szsh | 第一季度报告 |
| category_sjdbg_szsh | 第三季度报告 |
| category_yjyg_szsh | 业绩预告 |
| category_yjkb_szsh | 业绩快报 |
| category_gqjl_szsh | 股权激励 |
| category_gddj_szsh | 股东大会 |

# 4. 注意事项
* 接口为 POST 请求，参数通过 form-data 传递
* stock 参数格式：代码,交易所简称（如 601318,sh）
* 公告详情需通过 announcementId 拼接 URL 下载 PDF
* 建议调用间隔大于 1 秒

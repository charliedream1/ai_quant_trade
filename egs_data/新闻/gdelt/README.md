# 1. 简介

GDELT Project（Global Database of Events, Language, and Tone）是目前最大的
全球新闻事件数据库，由 Google Jigsaw 支持，完全免费，无需 API Key。

- 官网: https://www.gdeltproject.org/
- 数据文档: https://blog.gdeltproject.org/gdelt-2-0-our-global-world-in-realtime/
- BigQuery: https://console.cloud.google.com/marketplace/details/bigquery-public-data:gdelt

特点：
* 覆盖 1979 年至今的全球新闻事件
* 每 15 分钟更新一次
* 100+ 语言，250+ 国家
* 内置 CAMEO 事件编码（谁对谁做了什么）
* 内置 Tone 情绪分数（-100 到 +100）
* 完全免费，无需注册

# 2. 数据获取方式

## 2.1 直接下载 15 分钟切片（推荐）
- 最新文件列表: http://data.gdeltproject.org/gdeltv2/lastupdate.txt
- 数据格式: CSV（每15分钟一个文件）
- 无需 API Key

## 2.2 BigQuery 公共数据集
- 数据集: gdelt-bq.gdeltv2.gkg（GKG）、gdelt-bq.gdeltv2.events（事件）
- 免费额度: 1TB/月
- 需 GCP 账号

## 2.3 gdeltdoc Python 库
- 安装: pip install gdeltdoc
- 封装了 GDELT DOC 2.0 API

# 3. 数据表说明

## 3.1 Events 表（事件）
| 字段 | 说明 |
|------|------|
| GLOBALEVENTID | 事件唯一ID |
| SQLDATE | 事件日期 |
| Actor1Code | 行为主体代码 |
| Actor1Name | 行为主体名称 |
| Actor1CountryCode | 行为主体国家 |
| Actor2Code | 行为客体代码 |
| Actor2Name | 行为客体名称 |
| EventCode | CAMEO事件编码 |
| EventBaseCode | 事件基础编码 |
| EventRootCode | 事件根编码 |
| GoldsteinScale | 事件重要性（-10到+10） |
| ActionGeo_CountryCode | 事件发生国家 |
| AvgTone | 情绪分数（-100到+100） |

## 3.2 GKG 表（全球知识图谱）
| 字段 | 说明 |
|------|------|
| GKGRECORDID | 记录ID |
| DATE | 日期 |
| SourceCollectionIdentifier | 来源类型 |
| V2Themes | 主题标签 |
| V2Locations | 地点标签 |
| V2Persons | 人物标签 |
| V2Organizations | 机构标签 |
| V2Tone | 情绪分数 |
| DocumentIdentifier | 文档URL |

# 4. 安装

```shell
pip install gdeltdoc
```

或直接使用 requests + pandas 下载 CSV 切片。

# 5. 注意事项
* 15分钟切片文件较大（约100MB），下载需一定时间
* AvgTone > 0 表示正面情绪，< 0 表示负面情绪
* GoldsteinScale 越接近 +10 表示事件越积极（合作），越接近 -10 表示越冲突
* CAMEO 事件编码体系详见: https://www.gdeltproject.org/data/lookuptables/CAMEO.eventcodes.txt

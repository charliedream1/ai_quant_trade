# 股票自动交易员  

[**ENGLISH VERSION**](https://github.com/charliedream1/ai_quant_trade/blob/master/README_EN.md)

[![License](https://img.shields.io/badge/License-Apache%202.0-brightgreen.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python-Version](https://img.shields.io/badge/Python-3.8-brightgreen)](https://github.com/charliedream1/ai_quant_trade)

[**文档**](https://github.com/charliedream1/ai_quant_trade/tree/master/docs)
| [**数据处理**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_data)
| [**聚宽样例**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_%E8%81%9A%E5%AE%BD)

## 愿景
希望这是一个实用，可以快速部署，辅助股票实盘交易的工具，而不是一个仅限于学习和研究的平台。
- 第一阶段：丰富完善各个功能模块
- 第二阶段：可以用于部署和实盘使用
- 第三阶段：封装成一个带界面的软件，对于不会代码的人，也可以方便的获得智能推荐消息

<img src="https://github.blog/wp-content/uploads/2020/09/github-stars-logo_Color.png" alt="drawing" width="25"/>**如果喜欢本项目，请给我点个赞吧 (页面右上角的小星星)，欢迎分享到社区!**

## 核心功能
ai_quant_trade工具的目标意在提供一款集量化炒股知识、工具及实盘炒股为一体的
工具，如下特性将逐步完善并加入：

* docs: 常见炒股知识及策略
* egs_data: 数据获取及存储，包括股票信息和消息信息，及数据库使用等
* egs_mdl: 包含机器学习、深度学习、强化学习和图神经网络等的自动炒股模型，
    利用NLP进行消息面分析等，主要用于本地模拟、分析及实盘
* egs_聚宽：主要包含 [**聚宽平台**](https://www.joinquant.com/) 的
    使用样例，通过该平台可以方便的进行回测、模拟盘及实盘交易 (后续也将加入
    其它常见平台的实例)
* egs_tools: 基础知识请访问 [**ai_wiki**](https://github.com/charliedream1/ai_wiki) ，
    包括windows, linux, shell, vim, 
    markdown，python, c++,机器学习数学基础，
    leetcode(c++, python)，机器学习、
    深度学习、强化学习、图神经网络，语音识别、NLP和图像识别等基础知识
* quant_net: 包含机器学习、深度学习、强化学习和图神经网络等的自动炒股模型
    的核心算法库
* runtime：包含C++代码，用于模型的部署和实际使用，提供流式实时股票趋势预测
    等服务
* tools: 辅助工具等

## 1. [**聚宽平台**](https://www.joinquant.com/) 样例性能
聚宽平台是为量化爱好者（宽客）量身打造的云平台，提供免费股票数据获取、精准的回测功能、
高速实盘交易接口、易用的API文档、由易入难的策略库，便于快速实现和验证策略。(<font color=red>
**注：如下策略仅在所述回测段有效，没有进行详细的调优和全周期验证。另外，没有策略能保证全周期有效的，
如果实盘使用如下策略，请慎重使用**</font>)

国内其余量化平台，如优矿、米筐等，如果感兴趣，也可以自行尝试。

- 传统策略：规则或基础统计方法  
  - [**小市值+多均线量化炒股**](https://www.joinquant.com/view/community/detail/c754d315a391f39f61858dfe3275f45f) 
  2020-03-01 到 2022-03-01, ￥100000, 每天， 年化23.98%，最大回撤46.62%，胜率0.429
  - [**龙虎榜-看长做短**](https://www.joinquant.com/view/community/detail/0986c3b92578952cc22c52f0a5ea4664) 
  2022-03-25 到 2022-05-24, ￥100000, 每天， 年化895.86%%，最大回撤26.894%，胜率0.250
- 机器学习类策略：基于sklearn等工具
  - [**机器学习-动态因子选择策略**](https://www.joinquant.com/view/community/detail/f2a9d2ec6d4ad18882fa0a364fb9123d)
  2022-01-01 到 2022-06-20, ￥100000, 每天，年化32.35%，最大回撤32.35%，胜率0.625

## 讨论
欢迎在 [Github Discussions](https://github.com/charliedream1/ai_quant_trade/discussions) 中发起讨论。


## 技术支持

欢迎在 [Github Issues](https://github.com/charliedream1/ai_quant_trade/issues) 中提交问题。

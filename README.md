# 股票AI操盘手  

[**ENGLISH VERSION**](https://github.com/charliedream1/ai_quant_trade/blob/master/README_EN.md)

[![License](https://img.shields.io/badge/License-Apache%202.0-brightgreen.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python-Version](https://img.shields.io/badge/Python-3.8-brightgreen)](https://github.com/charliedream1/ai_quant_trade)

[**文档**](https://github.com/charliedream1/ai_quant_trade/tree/master/docs)
| [**数据处理**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_data)
| [**在线投研平台样例**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_online_platform)

<img src="https://github.blog/wp-content/uploads/2020/09/github-stars-logo_Color.png" alt="drawing" width="25"/>**如果喜欢本项目，或希望随时关注动态，请给我点个赞吧 (页面右上角的小星星)，欢迎分享到社区!**

## 愿景
&emsp;&emsp;希望这是一个实用，可以快速部署，辅助股票实盘交易的工具，而不是一个仅限于学习和研究的平台。
- 第一阶段：丰富完善各个功能模块
- 第二阶段：用于部署和实盘使用
- 第三阶段：封装成一个带界面的软件，对于不会代码的人，也可以便捷获取到智能推荐消息

## :fire: 新特性
&emsp;&emsp;本仓库正在从零开始构建，欢迎关注，学习并了解所有的底层和细节，才会赢！！！

* 2022.08.03： 本地回测平台初步完善，支持[**双均线策略**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_local_strategies/rules/double_ma)

## 核心功能
ai_quant_trade工具的目标意在提供一款集量化炒股知识、工具及实盘炒股为一体的
工具，如下特性将逐步完善并加入：

* docs: 常见炒股知识及策略
* egs_data: 数据获取及存储，包括股票信息和消息信息，及数据库使用等
* egs_local_strategies: 包含机器学习、深度学习、强化学习和图神经网络等的自动炒股模型，
    利用NLP进行消息面分析等，主要用于本地模拟、分析及实盘
* egs_online_platform：主要包含 [**聚宽平台**](https://www.joinquant.com/) 的
    使用样例，通过该平台可以方便的进行回测、模拟盘及实盘交易 (后续也将加入
    其它常见平台的实例)
* egs_tools: 基础知识请访问 [**ai_wiki**](https://github.com/charliedream1/ai_wiki) ，
    包括windows, linux, shell, vim, 
    markdown，python, c++,机器学习数学基础，
    leetcode(c++, python)，机器学习、
    深度学习、强化学习、图神经网络，语音识别、NLP和图像识别等基础知识
* quant_brain: 包含机器学习、深度学习、强化学习和图神经网络等的自动炒股模型
    的核心算法库
* runtime：包含C++代码，用于模型的部署和实际使用，提供流式实时股票趋势预测
    等服务
* tools: 辅助工具等

## 1. [**本地量化平台**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_local_strategies)  
可在本地可构建一套独立的量化交易系统
* 示例请查看: [egs_local_strategies](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_local_strategies)
* [详细使用教程](https://github.com/charliedream1/ai_quant_trade/tree/master/docs/%E6%9C%AC%E4%BB%93%E5%BA%93%E6%95%99%E7%A8%8B)

[回测框架](https://github.com/charliedream1/ai_quant_trade/tree/master/quant_brain/back_test)
* [数据获取(包含TusharePro)](https://github.com/charliedream1/ai_quant_trade/tree/master/quant_brain/fetch_data)
* [10项风险指标计算](https://github.com/charliedream1/ai_quant_trade/blob/master/quant_brain/back_test/risk_indicator.py)
* [K线蜡烛图交易点展示](https://github.com/charliedream1/ai_quant_trade/tree/master/tools/plots)

择时策略
- [双均线策略](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_local_strategies/rules/double_ma)

![trades_on_k_line](./img/trades_on_k_line.png)

如何使用：
1. 安装所需库
```shell
pip install requirements.txt
```
2. 查看策略文件夹下文档并运行对应实例即可

## 2. [**知识宝库**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_local_strategies)  

&emsp;&emsp;这里汇总了各种量化相关的平台、开源资源和知识。这里是一个丰富的知识仓库和导航地图。  
&emsp;&emsp;这里将汇总包括量化投资，windows, linux, shell, vim, markdown，python, c++,机器学习数学基础， 
leetcode(c++, python)，机器学习、 深度学习、强化学习、图神经网络，语音识别、NLP和图像识别等基础知识

* [量化交易与投资](https://github.com/charliedream1/ai_quant_trade/tree/master/docs/1_%E9%87%8F%E5%8C%96%E4%BA%A4%E6%98%93%E4%B8%8E%E6%8A%95%E8%B5%84)
* [python量化工具库](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_tools)
* [股票数据获取](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_data)


## 3. [**在线投研平台样例**](https://www.joinquant.com/)

&emsp;&emsp;国内量化平台，如聚宽、优矿、米筐、果仁和BigQuant等，如果感兴趣，也可以自行尝试。

&emsp;&emsp;投研平台是为量化爱好者（宽客）量身打造的云平台，提供免费股票数据获取、精准的回测功能、
高速实盘交易接口、易用的API文档、由易入难的策略库，便于快速实现和验证策略。(<font color=red>
**注：如下策略仅在所述回测段有效，没有进行详细的调优和全周期验证。另外，没有策略能保证全周期有效的，
如果实盘使用如下策略，请慎重使用**</font>)

### 3.1 [**聚宽平台**](https://www.joinquant.com/)

欢迎在聚宽平台关注我：量客攻城狮
- 具体策略详细介绍和源码请单击如下对应策略链接访问查看
- 聚宽使用介绍请查看: [egs_online_platform/聚宽_JoinQuant](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_online_platform/%E8%81%9A%E5%AE%BD_JoinQuant)  
- 该部分代码仅能在 [**聚宽平台**](https://www.joinquant.com/) 运行


1. 股票量化策略

| 策略    | 收益 | 最大回撤 |   
|:-------- |:-------:|:-------:|
| [**机器学习-动态因子选择策略**](https://www.joinquant.com/view/community/detail/f2a9d2ec6d4ad18882fa0a364fb9123d) | 12.3% | 38.93% |
| [**小市值+多均线量化炒股**](https://www.joinquant.com/view/community/detail/c754d315a391f39f61858dfe3275f45f) | 58.4% | 46.61% |
| [**龙虎榜-看长做短**](https://www.joinquant.com/view/community/detail/0986c3b92578952cc22c52f0a5ea4664) | 41.82% | 26.89% |
| [**强势股+趋势线判断+止损止盈**](https://www.joinquant.com/view/community/detail/c0390ceabdc1b3365df343490b7caf28) | 10.09% | 21.449% |


2. 股票分析研究

* [手把手教你"机器学习-动态多因子选股"(附保姆级教程) ](https://www.joinquant.com/view/community/detail/4fa769264b0bf6489b36351b43e37012)
* [龙虎榜数据筛选和过滤](https://www.joinquant.com/view/community/detail/a3a95cc7e53092aaea510d93bab9cb96)
* [概念板块数据获取和选股](https://www.joinquant.com/view/community/detail/d1bf674ad163654aa263dac859762c90)
* [详解: 股票数据获取及图形分析(附详细代码)](https://www.joinquant.com/view/community/detail/8fe84d0d25dcf1a6da72e442460cdf36)


## 讨论
欢迎在 [Github Discussions](https://github.com/charliedream1/ai_quant_trade/discussions) 中发起讨论。


## 技术支持

欢迎在 [Github Issues](https://github.com/charliedream1/ai_quant_trade/issues) 中提交问题。


## 常见问题

请查看文档[**常见问题**]()

## 引用

``` bibtex
@misc{ai_quant_trade,
  author={Yi Li},
  title={ai_quant_trade},
  year={2022},
  publisher = {GitHub},
  journal = {GitHub repository},
  howpublished = {\url{https://github.com/charliedream1/ai_quant_trade}},
}

```

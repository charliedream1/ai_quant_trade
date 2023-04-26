# 股票AI操盘手  

[**ENGLISH VERSION**](https://github.com/charliedream1/ai_quant_trade/blob/master/README_EN.md)

[![License](https://img.shields.io/badge/License-Apache%202.0-brightgreen.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python-Version](https://img.shields.io/badge/Python-3.8-brightgreen)](https://github.com/charliedream1/ai_quant_trade)

[**AI炒股教程**](https://github.com/charliedream1/ai_quant_trade/tree/master/ai_wiki)
| [**本地策略**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_trade)
| [**辅助操盘**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_aide)
| [**因子挖掘**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_alpha)
| [**文本分析**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_fin_nlp)
| [**数据处理**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_data)
| [**在线投研平台**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_online_platform)
| [**使用文档**](https://github.com/charliedream1/ai_quant_trade/tree/master/docs)

<img src="https://github.blog/wp-content/uploads/2020/09/github-stars-logo_Color.png" alt="drawing" width="25"/>**如果喜欢本项目，或希望随时关注动态，请给我点个赞吧 (页面右上角的小星星)，欢迎分享到社区!**


**股票AI操盘手**

- 一站式平台：从学习、模拟到实盘
- 炒股策略：因子挖掘、传统策略、机器学习、深度学习、强化学习、图网络、高频交易等
- 提供辅助操盘工具：辅助盯盘、股票推荐
- 实盘部署工具：C++/CPU/GPU等部署

## :newspaper: 新特性 :fire:

| **时间**    |  **特性** |  **代码路径** |   
|:-------- |:-------| :-------|
| 2023.04.09 | [**StructBERT市场情绪分析**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_fin_nlp/emotion_analysis/01_StructBert_Binary_Class) | egs_fin_nlp/emotion_analysis/01_StructBert_Binary_Class |
| 2023.03.28 | [**强化学习多股票交易：年化收益53%**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_trade/rl/a002_finRL_tutorial/a01_Stock_NeurIPS2018) | egs_trade/rl/a002_finRL/a01_Stock_NeurIPS2018 |
| 2023.02.28 | [**机器学习自动挖掘5000个因子及股票趋势预测**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_alpha/auto_alpha/tsfresh) | egs_alpha/auto_alpha/tsfresh |
| 2023.02.05 | [**上班“摸鱼炒股”神器--超隐蔽“划水致富”**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_aide/%E7%9C%8B%E7%9B%98%E7%A5%9E%E5%99%A8/v1) | egs_aide/看盘神器/v1 |
| 2023.01.01 | [**本地深度强化学习策略**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_trade/rl/a001_proto_sb3) | egs_trade/rl/a001_proto_sb3 |
| 2022.11.07 | [**Wind本地实盘模拟**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_trade/real_bid_simulate/wind) | egs_trade/real_bid_simulate/wind | 
| 2022.08.03 | [**基础回测框架 + 双均线策略**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_trade/vanilla/double_ma) | egs_trade/vanilla/double_ma |

## 目录   
* [1. 简介](#1._简介)  
* [2. 使用](#2._使用)  
* [3. 本地量化平台](#3._本地量化平台)  
    * [3.1 强化学习策略](#3.1_强化学习策略)  
    * [3.2 图网络策略](#3.2_图网络策略)  
    * [3.3 深度学习策略](#3.3_深度学习策略)  
    * [3.4 机器学习策略](#3.4_机器学习策略)  
    * [3.5 高频交易](#3.5_高频交易)  
    * [3.6 传统策略](#3.7_传统策略)  
* [4. 实盘](#4._实盘)  
    * [4.1 实盘模拟](#4.1_实盘模拟)  
* [5. 辅助操盘](#5._辅助操盘) 
* [6. 因子挖掘](#6._因子挖掘)   
* [7. 数据获取](#7._数据获取)   
* [8. 文本分析](#8._文本分析)   
* [9. AI-烹饪指南](#9.__AI-烹饪指南)  
* [10. 在线投研平台](#10._在线投研平台)  
    * [10.1 聚宽平台](#10.1_聚宽平台)  
* [打赏我](#打赏我)   
* [关注我](#关注我)   
* [讨论](#讨论)  
* [技术支持](#技术支持)  
* [常见问题](#常见问题)  
* [引用](#引用)  

## 1. 简介

1. 本系统适合的人群：
    - 机构
    - 散户
        - 有编程基础
        - 无编程基础

2. 本仓库代码结构和内容简介
    ```
    ai_quant_trade
    ├── ai_wiki (AI全栈教学知识，以Markdown, Jupyter Notebook汇总知识体系)
    │   ├── 基础：操作系统、软件编程、数学基础
    │   ├── 进阶：机器学习、深度学习、强化学习、图网络
    │   ├── 实战：量化交易与投资、模型部署
    ├── docs (本仓库使用说明文档)
    ├── egs_aide (辅助操盘工具)
    │   ├── 看盘神器 (上班“摸鱼炒股”神器--超隐蔽“划水致富”)
    ├── egs_alpha (因子库)
    ├── egs_data (数据获取及处理)
    │   ├── wind (Wind万得数据处理)
    ├── egs_fin_nlp (文本分析)
    │   ├── emotion_analysis (情感分析)
    ├── egs_online_platform (在线投研平台策略)
    │   ├── 优矿_Uqer
    │   ├── 聚宽_JoinQuant
    ├── egs_trade (本地量化炒股策略)
    │   ├── paper_trade (实盘模拟)
    │       ├── wind万得实盘模拟
    │   ├── rl (强化学习炒股)
    │   ├── vanilla (传统规则类策略)
    ├── quant_brain (核心算法库)
    ├── runtime (模型的部署和实际使用)
    ├── tools (辅助工具)
    ├── requirements.txt
    └── README.md
 
    ```
   

## 2. 使用

本仓库暂未进行封装成python包，拷贝整个项目源代码，

1. 安装所需库
    ```shell
    pip install -r requirements.txt
    ```
   
2. 查看egs策略文件夹下文档, 并运行对应实例即可

## 3. 本地量化平台

[**本地量化平台**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_trade)  

代码详细参见目录：egs_trade

可在本地可构建一套独立的量化交易系统，包含的策略：
- AI策略
    - 强化学习
    - 图网络
    - 深度学习
    - 机器学习
    - 高频交易
    - 因子挖掘
- 传统规则类策略

### 3.1 强化学习策略

&emsp;&emsp;代码详细参见目录：egs_trade/rl

&emsp;&emsp;自从2017年AlphaGo与柯洁围棋大战之后，深度强化学习大火。

&emsp;&emsp;相比于机器学习和深度学习, 强化学习是以最终目标为导向 (以交互作为目标) , 
而很多其他方法是考虑孤立的子问题 (如“股价预测”,“大盘预测”,“交易决策”等) , 这并不能直接获得交互的动作, 
比如“命令机器人炒股盈利”, 这个任务包含了“股价预测”,”大盘预测”等等, 而强化学习的目标则是“完成命令者的任务”, 
可以直接得到“炒股盈利”的一连贯动作。 

![trades_on_k_line](.README_images/强化学习.png)

1. 样例介绍：

    | **序号**    | **策略**  | **代码路径** |  **论文** |   
    |:-------- |:-------- |:-------| :-------| 
    | 1 | 原型  | egs_trade/rl/a001_proto_sb3 |  |
    | 2 | FinRL教程0-NeurIPS2018 | egs_trade/rl/a002_finRL_tutorial/a01_Stock_NeurIPS2018 | Practical Deep Reinforcement Learning Approach for Stock Trading （https://arxiv.org/abs/1811.07522） |

2. 样例回测详情

    | **序号**    | **策略**  | **市场**  | **年化收益** |  **最大回撤** |  **夏普率** | 
    |:-------- |:-------- |:-------| :-------| :-------| :-------| 
    | 1 | 原型 | 中国A股 |  |  | | 
    | 2 | FinRL教程0-NeurIPS2018 | 美股道儿琼斯30 | 53.1% | -10.4%  | 2.17 |

### 3.2 图网络策略
&emsp;&emsp;图网络可以更好的构建股票和股票之间的关系，同时关联股票、新闻、情绪等各类信息，能更好的挖掘全局关系网。

(构建中，尽请期待。。。)

### 3.3 深度学习策略
&emsp;&emsp;自从2012年AlexNet在图像分类任务上，性能碾压传统机器学习性能后，深度学习大火，
随机开启第一波人工智能热潮。其主要用于股价和大盘的预测等。

(构建中，尽请期待。。。)

### 3.4 机器学习策略
&emsp;&emsp;机器学习以统计学为基础，以其坚实的数据基础，可解性，数据依赖少，资源占用低，训练速度快，在表格任务上，
仍然可以追平深度学习等优势，任有其应用价值。

(构建中，尽请期待。。。)

### 3.5 高频交易
(构建中，尽请期待。。。)

### 3.6 传统策略
&emsp;&emsp;传统策略虽然看似昨日黄花，但其可操作性更强，仍又一定使用价值。深度学习和机器学习，往往需要配合规则使用。

1. [双均线策略](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_trade/vanilla/double_ma)
    - [详细使用教程](https://github.com/charliedream1/ai_quant_trade/tree/master/docs/%E6%9C%AC%E4%BB%93%E5%BA%93%E6%95%99%E7%A8%8B)
    
    ![trades_on_k_line](.README_images/trades_on_k_line.png)

2. [投资组合管理7节教学](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_trade/vanilla/portfolio_optimization)

## 4. 实盘
### 4.1 实盘模拟

参见目录：egs_trade/paper_trade

* [**Wind本地实盘模拟：双均线策略**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_trade/paper_trade/wind)


## 5. 辅助操盘

代码详细参见目录：egs_aide

| **序号**    | **工具**  | **代码路径** |  
|:-------- |:-------- |:-------| 
| 1 | 定制化看盘工具 | egs_aide/看盘神器/v1 |

## 6. 因子挖掘

**代码详细参见目录：egs_alpha**

### 6.1 因子挖掘

| **序号**    | **策略**  | **代码路径** |  **论文** |   
|:-------- |:-------- |:-------| :-------| 
| 1 | 机器学习自动挖掘5000个因子及股票趋势预测 | egs_alpha/auto_alpha/tsfresh |  |

### 6.2 因子库

| **序号**    | **因子库**  | 
|:-------- |:-------- |
| 1 | alpha101 | 
| 2 | stockstats | 
| 3 | ta_lib | 

## 7. 数据处理 

- 各类常见数据源使用详解
- 统一数据源接口

![](.README_images/数据源.png)


## 8. 文本分析

| **序号**    | **工具**  | **代码路径** |  
|:-------- |:-------- |:-------| 
| 1 | [**StructBERT市场情绪分析**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_fin_nlp/emotion_analysis/01_StructBert_Binary_Class) | egs_fin_nlp/emotion_analysis/01_StructBert_Binary_Class |


## 9. AI-百科全书

[**AI-百科全书**](https://github.com/charliedream1/ai_quant_trade/tree/master/ai_wiki) 

&emsp;&emsp;代码参见：ai_wiki

&emsp;&emsp;本部分代码独立同步至仓库[**AI-百科全书**](https://github.com/charliedream1/ai_wiki)

&emsp;&emsp;这里汇总了各种量化相关的平台、开源资源和知识。这里是一个丰富的知识仓库和导航地图。 
 
&emsp;&emsp;这里将汇总包括量化投资，windows, linux, shell, vim, markdown，python, c++,机器学习数学基础， 

leetcode(c++, python)，机器学习、 深度学习、强化学习、图神经网络，语音识别、NLP和图像识别等基础知识


1. 代码结构和内容简介

    ```
    ai_wiki (AI全栈教学知识，以Markdown, Jupyter Notebook汇总知识体系)
    ├── 01_系统平台 
    │   ├── 基础：常用网站、通用工具
    │   ├── 系统：Windows/Linux
    ├── 02_程序代码 
    │   ├── 编程：python, c, c++, 数据库, LeetCode
    │   ├── 实战：常用工具、常见问题汇总
    ├── 03_数学基础（程序员必备数学知识）
    ├── 04_算法原理（传统算法，优化算法，遗传算法）
    ├── 05_机器学习（资源+原理+实战）
    ├── 06_深度学习（资源+原理+实战）
    ├── 07_强化学习（资源+原理+实战）
    ├── 08_图网络（资源+原理+实战）
    ├── 09_模型部署（资源+原理+实战）
    ├── 10_实践应用
    │   ├── 01_开源平台
    │   ├── 02_音频 (语音识别、唤醒、声纹、语音合成、语音增强)
    │   ├── 03_文本处理 
    │   ├── 04_时间序列 
    │   ├── 05_图像识别 
    ├── 11_面试
    ├── 12_量化交易与投资
    └── README.md

    ```

2. 量化相关资源

   | **序号**    | **工具**  | **路径** |  
    |:-------- |:-------- |:-------| 
    | 1 | [**全网量化资源汇总**](https://github.com/charliedream1/ai_quant_trade/tree/master/ai_wiki/12_量化交易与投资/01_资源) | ai_wiki/12_量化交易与投资/01_资源 |


## 10. 在线投研平台

[**在线投研平台样例**](https://www.joinquant.com/)

&emsp;&emsp;国内量化平台，如聚宽、优矿、米筐、果仁和BigQuant等，如果感兴趣，也可以自行尝试。

&emsp;&emsp;投研平台是为量化爱好者（宽客）量身打造的云平台，提供免费股票数据获取、精准的回测功能、
高速实盘交易接口、易用的API文档、由易入难的策略库，便于快速实现和验证策略。(<font color=red>
**注：如下策略仅在所述回测段有效，没有进行详细的调优和全周期验证。另外，没有策略能保证全周期有效的，
如果实盘使用如下策略，请慎重使用**</font>)

### 10.1 聚宽平台

[**聚宽平台**](https://www.joinquant.com/)

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


## 打赏我 

您的支持是我前进的动力，即便“1毛钱”我也很开心啊，感谢您的打赏和支持 \(^o^)/

<img src=".README_images/支付宝收款码_alma_new.jpg" width = "300" height = "390" alt="图片名称1" align=center />
<img src=".README_images/微信收款码_alma_new.jpg" width = "300" height = "390" alt="图片名称2" align=center />

## 关注我

- [知乎](https://www.zhihu.com/people/yi-dui-ji-mu-zai-kuang-xiang)
- [聚宽](https://www.joinquant.com/user/d7aafd0b8b767b735bfb6f3639c81a6c)


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

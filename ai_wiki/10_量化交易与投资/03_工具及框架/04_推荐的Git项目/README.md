# 0. 简介
&emsp;&emsp;股票类相关开源库汇总。

# 1. 数据
# 1.1 收费类接口
&emsp;&emsp;仅部分免费，但数据质量相对高。

1. [JoinQuant/jqdatasdk: 简单易用的量化金融数据包(easy utility for getting financial market data of China) (github.com)](https://github.com/JoinQuant/jqdatasdk)
  * 聚宽平台数据接口
  * 仅有3个月免费试用
  * 据描述质量较好，可以实盘使用

2. Tushare [**https://tushare.pro/**](https://tushare.pro/)  
  * （*****）推荐使用
  * 质量高，使用人数多。但存在很多限制，需要收费才能获取更多的数据。

# 1.2 基于爬虫的开源库
1. akshare [https://github.com/akfamily/akshare](https://github.com/akfamily/akshare)
  * （*****）推荐使用
  * 非常完善的数据获取库，主要基于爬虫获取(目前我安装后，总是报错，尚未解决)

2. efinance [https://github.com/Micro-sheep/efinance](https://github.com/Micro-sheep/efinance)
  * （*****）推荐使用
  * 非常完善的数据获取库，主要基于爬虫获取
  * 缺点: 没有大盘指数的接口

# 1.3 基于网页API接口封装的库
1. [shidenggui/easyquotation: 实时获取新浪 / 腾讯 的免费股票行情 / 集思路的分级基金行情 (github.com)](https://github.com/shidenggui/easyquotation)
   * 3.6k星，MIT协议，纯python代码，已8个月没有更新

2. [bosspen1/stock: 股票行情数据 东方财富交易接口 股票自动交易 (github.com)](https://github.com/bosspen1/stock)
   * 主要基于Java等开发
  
# 1.4 美股数据
1. yfinance
  * （***）推荐使用 (貌似只能获取国外股票行情数据)
  * 前身是pandas_datareader，后来雅虎关闭api后，通过一些非官方方法获取数据
  * 优点是数据免费、可以获取分钟级数据

2. pandas_datareader
  - 库以失效，无法获取数据，但可获取宏观经济数据    

# 2. 回测框架
&emsp;&emsp;部分回测框架继承了数据获取功能。

# 2.1 主流开源回测框架
* [mementum/backtrader: Python Backtesting library for trading strategies (github.com)](https://github.com/mementum/backtrader)
  * 9.3k星，GPL-3.0协议，14个月没有更新
  * 文档非常详细，所有开源回测框架，首推选择，优于易用性和详尽的文档
  * 速度可以说是里面最慢的了，但是在python的事件驱动框架里又算快的了。自定义程度很高，而且不用自己造轮子，回测代码非常简洁且逻辑清晰，文档非常详细，而且有大量的例子，甚至有论坛，可以说是这几个里面对用户最友好的框架了

* [quantopian/zipline: Zipline, a Pythonic Algorithmic Trading Library (github.com)](https://github.com/quantopian/zipline)
  * 由Quantopian开源，目前国内的很多Python编程语言的在线量化回测平台都是以zipline为模板开发应用的
  * 速度很慢，用于国内市场，需要修改内部数据接口
  * 15.4k星，apache 2.0，2年未更新，文档链接已失效

# 2.2. 实盘接口
* [vnpy/vnpy: 基于Python的开源量化交易平台开发框架 (github.com)](https://github.com/vnpy/vnpy)
  * 可以实盘，丰富的各类接口，提供策略开发软件
  * 各类机构应用广泛
  * 纯中文项目，纯python开发
  * 19.1k星，MIT协议，商用友好，开发度活跃
  * 据说回测是不如backtrader的，如果有技术，可以用backtrader回测，用vnpy下单
  * 更加适合期货，以及作为实盘接口

* [shidenggui/easytrader: 提供同花顺客户端/国金/华泰客户端/雪球的基金、股票自动程序化交易以及自动打新，支持跟踪 joinquant /ricequant 模拟交易 和 实盘雪球组合, 量化交易组件 (github.com)](https://github.com/shidenggui/easytrader)
  * 主要可以跟踪聚宽实盘模拟交易，以及实盘
  * 6.7k星，MIT协议，已2年没有更新

# 2.3 国产开源框架
* [ricequant/rqalpha: A extendable, replaceable Python algorithmic backtest trading framework supporting multiple securities (github.com)](https://github.com/ricequant/rqalpha)
  * 米筐网提供免费开源框架，米筐量化平台官网：https://www.ricequant.com/welcome/
  * 包含数据获取（不确定是否包含免费数据）
  * 仅限非商用
  * 4.7k星，持续根性，值得推荐

* [fasiondog/hikyuu: Hikyuu Quant Framework 基于C++/Python的开源量化交易研究框架 (github.com)](https://github.com/fasiondog/hikyuu)
  * 2019码云最有价值项目，1.4k星，更新活跃度高，C++底层速度快，值得推荐
  * 码云地址：[Hikyuu - Quant Framework (gitee.io)](http://fasiondog.gitee.io/hikyuu/)
  * MIT协议，商用友好
  * 百万级别的K线，2秒就能跑完，缺点是基本上只支持国内的股票数据，自定义数据很困难，而且可以说是几乎没有文档

* [enzoampil/fastquant: fastquant — Backtest and optimize your trading strategies with only 3 lines of code! (github.com)](https://github.com/enzoampil/fastquant)
  * 仅支持获取US股市数据，如果使用国内数据，可能需要修改内部代码
  * 支持各类传统规则类策略，支持超参数搜索
  * 支持文本情感分析
  * MIT协议，商用友好
  * 2022.03.03最后一次更新，活跃度不高

* [zvtvz/zvt: modular quant framework. (github.com)](https://github.com/zvtvz/zvt)
  * 比较完善的回测框架，同时包含数据获取，基本面、财务、消息类数据，图标展示很完备
  * 数据源多样，同时包含免费数据源
  * MIT协议，商用友好
  * 2.1k星，持续更新中，值得推荐
  * 老代码仓已不维护，老仓库地址：https://github.com/foolcage/fooltrader

* [josephchenhk/qtrader: A Light Event-Driven Algorithmic Trading Engine (github.com)](https://github.com/josephchenhk/qtrader)
  * 轻量级的回测框架，实时绘图跟踪部分比较好

* [refraction-ray/xalpha: 基金投资管理回测引擎 (github.com)](https://github.com/refraction-ray/xalpha)
  * 基金回测框架
  * 1.3K星，MIT协议
  
# 2.4 无编程基础框架
* [bbfamily/abu: 阿布量化交易系统(股票，期权，期货，比特币，机器学习) 基于python的开源量化交易，量化投资架构 (github.com)](https://github.com/bbfamily/abu)
  * 有电脑版和手机APP，主要利用传统量化和机器学习辅助操盘，更加适合无代码基础人使用
  * 纯中文项目，纯python开发
  * 9.3k星，值得推荐
  * GPL协议，商用不友好
  * APP下载地址:  https://www.abuquant.com/download
  * 电脑浏览器访问地址: https://www.abuquant.com/
  * 量化交易之路源码地址：https://github.com/bbfamily/abu
  * 量化知识：https://blog.abuquant.com/category/lecture/
  * K线课堂https://blog.abuquant.com/category/lecture/
  
# 3. 策略平台
&emsp;&emsp;上述2中开源项目以回测框架为主，也包含了部分策略，本节项目以策略未主打，
也包含回测的功能。

# 3.1 机器学习

# 3.2. 强化学习
* [wangshub/RL-Stock: 📈 如何用深度强化学习自动炒股 (github.com)](https://github.com/wangshub/RL-Stock)
  * 只对一支股票操作，精简易懂，是一个很好的强化学习入门项目
  * 2.3k星，值得推荐
  
* [AI4Finance-Foundation/FinRL: FinRL: Financial Reinforcement Learning. Please star. 🔥 (github.com)](https://github.com/AI4Finance-Foundation/FinRL)
  * 6k星，MIT协议，有大量论文支撑，哥伦比亚大学大学中国学生开发
  * 支持各类数据源



# 3. 投资组合管理

* [tradytics/eiten: Statistical and Algorithmic Investing Strategies for Everyone (github.com)](https://github.com/tradytics/eiten)
  * 2.4k星，2年没有更新了，GPL-3.0协议，商用不友好
  * 股票投资组合管理方案值得学习借鉴
  * [Tradytics - Artificial Intelligence Driven Trading Toolkit](https://tradytics.com/)开源，该网站时国外的量化投资APP，又手机版

# 4. 全方位策略框架

* [ailabx: AI量化实验室，专注将前沿人工智能技术(深度学习/强化学习/知识图谱)应用于金融量化投资。 (gitee.com)](https://gitee.com/ailabx/ailabx)
  * Github更新较慢，且11个月没有更新，建议访问码云上的代码，地址：[ailabx/ailabx: AI量化实验室，专注将前沿人工智能技术(深度学习/强化学习/知识图谱)应用于金融量化投资。 (github.com)](https://github.com/ailabx/ailabx)
  * Github 297星，无协议声明。码云上，89星，GPL-3.0协议，商用不友好。
  * 对应公众号文章较多，量化知识覆盖面较广

# 4. 分析

* [yijixiuxin/chanlun-pro: 基于缠中说禅所讲缠论理论，以便量化分析市场行情的工具 (github.com)](https://github.com/yijixiuxin/chanlun-pro)
  * 缠论web分析项目
  * 102星，apache 2.0协议
  * 网页分析界面非常好
  * 码云地址：

# 4. 研报复现

* [hugo2046/Quantitative-analysis: 量化研究-券商金工研报复现 (github.com)](https://github.com/hugo2046/Quantitative-analysis)
  * 相对都是因子，以及传统统计类策略
  * 主要基于聚宽数据
  * 无开源协议
  * 569颗星，值得推荐

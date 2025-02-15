&emsp;&emsp;详细代码请查看：https://github.com/charliedream1/ai_quant_trade

&emsp;&emsp;文末将附上对应代码压缩文件包，以及聚宽对应代码样例。

&emsp;&emsp;如果喜欢本项目，或希望随时关注动态，请给我点个赞吧 (Github页面右上角的小星星)，欢迎分享到社区!
如果发现代码中的bug，欢迎留言或在github提交issues。

&emsp;&emsp;为什么需要本地交易平台？

&emsp;&emsp;通过在线平台确实可以帮助我们快速的获取高质量数据，
以及验证自己的策略，并得到详细的回测结果。在线平台中，现成的数
据获取和回测评估，可以节约我们大量的时间，但是使用本地平台也是不可或缺的。
本地平台主要有以下优点：

* 方便调试，以及代码管理
* 本地资源充足，在线平台资源有限，跑机器学习类模型非常吃力
* 本地平台方便定制化，不再是黑盒使用
* 隐私管理较好，方便进行实盘

&emsp;&emsp;如何在本地构建一个自己的量化交易平台。我将分成如下几章进行
讲解：
* [数据获取篇(见上一篇文章)](https://www.joinquant.com/view/community/detail/6aad770d9c9eab2b6e65f58dfd944fe8)
* 基于双均线策略的本地回测框架(本篇将重点介绍)
* 回测及风险评估指标(请关注后续的文章)
* 机器学习/深度学习类策略(请关注后续的文章)

# 1. 使用简介
## 1.1 获取代码并安装必须的python库
1. 安装所需Python包   
下载仓库代码，并通过如下命令安装所需库：
```shell
pip install requirements.txt
```

2. 风险指标计算ta_lib包安装   
其中，如果ta_lib安装不成功，可以通过如下方法进行安装：
``` sh
pip install TA-Lib
```
&emsp;&emsp;上述方法很容易出现安装错误
- 可以通过网站
[https://www.lfd.uci.edu/~gohlke/pythonlibs/](https://www.lfd.uci.edu/~gohlke/pythonlibs/)
- 按Ctrl+F搜索ta-lib，选择对应的平台安装包，离线安装
- 注意windows下和linux下的斜杠不同
``` sh
cd download
pip install .\TA_Lib-0.4.24-cp38-cp38-win_amd64.whl
```

3. 数据获取包安装   
目前本仓库采纳tushare pro进行数据获取（后续也将加入其它数据接口）
Tushare网址: [**https://tushare.pro/**](https://tushare.pro/)
安装
``` sh
pip install tushare
```
**注：如果大量调用，或需要获取更详细的信息，需要付费**
- 旧版本接口将不再维护，建议使用新接口Tushare Pro (需要注册获取token)
- 注册后在右上角用户头像--》个人主页--》获取token
- 如果没有缴费加入会员，很多接口都无法调用(每个接口调用需要的积分数，请查看接口文档)

## 1.2 运行样例程序
1. 进入策略样例列表：egs_local_strategies->rules->double_ma
2. 在conf/double_ma.yaml中配置回测条件，在stock_lst中设置待
   选择的股票，并设置回测日期
3. 配置tushare的token: 在quant_brain->fetch_data->get_tushare_data.py
   的头文件中，将“from data.private.tushare_token import tushare_token”替换
   为“tushare_token = 'xxxx'”个人申请注册的token
4. 运行回测脚本，之后在日志中可以查看风险指标，并可以得到交易K线图
```shell
python back_tester.py --debug_off --config conf/double_ma.yaml
```
5. 输出文件
* 通过tushare获取的数据将按照日期+股票代码的格式作为文件名以csv格式
  存储在data目录下。
* 绘制的交易曲线图，以及风控指标csv文件将存储在exp文件夹下。

# 2. 回测框架构
&emsp;&emsp;核心代码可以在quant_brain中进行查看。主体结构如下：
* 通过yaml配置回测条件，手工设置股票池待选股票及回测周期
* 初始化：(1) 通过tushare获取股票数据 (2) 初始化账户信息
* 回测流程：按照日期和股票双循环遍历，计算长短周期均线，获取卖出买入信号，更新账户信息
* 计算风险指标以及绘图

## 2.1 数据及选股
### 2.1.1 数据获取
&emsp;&emsp;通过tushare pro获取数据
```python

import tushare as ts
import datetime
# replace below with your token and comment my import
# tushare_token = 'xxxx'
from data.private.tushare_token import tushare_token

# initialize api
ts.set_token(tushare_token)
ts_pro = ts.pro_api()

# query date setting
# date type is year-month-day
today = datetime.date.today()
yesterday = today - datetime.timedelta(days = 1)
five_days_ago = today - datetime.timedelta(days = 5)
# change date type to YearMonthDay
yesterday = yesterday.strftime("%Y%m%d")
five_days_ago = five_days_ago.strftime("%Y%m%d")

# request data，中国平安: 601318.SH, date type require is: YearMonthDay
# api website: https://tushare.pro/document/2?doc_id=27
# !!! 警告：未复权，如果是复权请用 通用行情接口
df = ts_pro.query('daily', ts_code='601318.SH',
                    start_date=five_days_ago, end_date=yesterday)
df.head()
```

&emsp;&emsp;每一列数据的含义如下：         
| 名称 |	类型 | 描述 |
|:-------- |:-------:| ---------:|
| ts_code |str | 股票代码 |
| trade_date | str | 交易日期 |
| open | float | 开盘价 |
| high | float | 最高价 |
| low | float | 最低价 |
| close | float | 收盘价 |
| pre_close | float | 昨收价 |
| change | float | 涨跌额 |
| pct_chg | float | 涨跌幅 （未复权，如果是复权请用 通用行情接口 ）
| vol | float | 成交量 （手） |
| amount| float |成交额 （千元）|

[注：如果没有tushare的积分，大盘指数数据将无法获取，风险指标将跳过alpha和beta值的计算]

### 2.1.2 选股策略
&emsp;&emsp;当前策略采用人工选股，在conf/double_ma.yaml中配置回测条件，在stock_lst中设置待
选择的股票。（注：后续将加入更多的自动选股策略）

# 2.2 择时策略
## 2.2.1 双均线策略

&emsp;&emsp;双均线策略是一种趋势跟踪类策略，作为基础入门类策略，容易理解，不管是否采用程序代码实现，
都能快速上手使用。其原理也就是常说的通过捕捉金叉死叉信号组合来判断买点和卖点。趋势类策略一般适用于市场
环境较好的时候。

&emsp;&emsp;知识点补充：均线计算，即用特定时间段的收盘价计算平均值，作为当天的均价。在信号处理中，
也是一种滤波的手段，避免信号出现较大波动，过滤较大的跳变。

![金叉死叉指示](img均线示例图.png)

&emsp;&emsp;如上图，我们首先根据收盘价，计算2条均线，一条长周期均线（如20日，图中黄线），
一条短周期均（如10日，图中蓝线）。如果短周期均线下穿长周期均线时，则意味着当前有下跌的趋势，
此时适合卖出，即常说的死叉。反之，当短周期均线向上穿过长周期均线时，则意味着有上涨的趋势，
此时适合买入，即所谓的金叉。

&emsp;&emsp;通过pandas快速计算均值。
```python
df['ma_short'] = df['close'].rolling(window=self.test_conditions['ma_short']).mean()
df['ma_long'] = df['close'].rolling(window=self.test_conditions['ma_long']).mean()
```

&emsp;&emsp;通过双均线进行择时。
```python
if ma_short >= ma_long and not hold:
    trade_type = 'buy'
elif ma_short < ma_long and hold:
    trade_type = 'sell'
```

## 2.2.2 账户信息刷新
&emsp;&emsp;通过账户类实时刷新账户信息。
```python
class Account:
    def __init__(self, capital: int):
        # 1. dynamic changing info
        self.cash = capital  # available cash for trading
        self.total_capital = capital
        # stock id: {pos_num, price}, price for current price
        self.pos_dict = {}

        # 2. trading history log
        # historical trading of each stock
        # stock id: dataframe (detailed trading info)
        self.trade_dict = {}
        # each day's trading history (only log trading really happens)
        self.daily_trading_lst = []
        # overall trading info, make each day's trading as one
        self.pd_gather_trades = pd.DataFrame()
        # log total funds changing of each day even no trades happened on the day
        self.funds_chg_lst = []

```

# 2.2.3 其它费用计算
```shell
order_cost:
  close_tax: 0.001  # tax charged for selling
  open_commission: 0.0003  # purchase service fee
  close_commission: 0.0003  # selling service fee
  min_commission: 5  # minimum service fee for each trade
  slippage_fee: 0.0 #0.00246 # 0.00246  # fee difference between value and actual order
  # random: random pos or neg value, general: buy pos, sell neg
  slippage_type: general
  # calculate purchase number, 1 buy = 100 shares
  # minimum subscribe for 100 shares, multiple 100 is to 1 buy
  trade_lim: 100
```

# 2.3 回测评估
# 2.3.1 风险指标计算
1. 策略收益：P是账户资金在一段时间内的变化。
```shell
(Pend - Pstart) / Pstart * 100%
```

2. 年化收益：    
   如果测试周期小于1年，则是一个折算值，
   有可能比实际年化少，((1+P)^(250/n) - 1) * 100%，P是策略收益，
   n可以认为是交易日，一年250天

3. Beta：   
   衡量策略收益和基准收益的关系，常用上证指数作为基准，如果基准收益上涨1%，
   策略收益上涨1.5%，则Beta为1.5，反之为-1.5。如果市场状态良好，则越大越好，
   反之，越小越好。公式如下：
```shell
   Beta = Cov(Dp, Dm) / Var(Dm)
```
&emsp;&emsp;COV：协方差，Var：方差
   
4. Alpha:      
   非系统性风险，代表和市场波动无关的收益。比如，策略收益为20%，基准收益为10%，则Alpha为
   10%。Alpha计算公式如下：
```shell
   Alpha = Rp - [Rf + Beta * (Rm - Rf)]
```
* Rp: 策略年化收益
* Rm：基准收益
* Beta：上述3中计算的值
* Rf: 无风险利率，可以银行定期存款利率作为基准，通常设为4%。

5. Sharp率：
   表示每承担一个风险所获得的无风险收益。值越大，表示承担越多风险，收益越大。反之亦然。
   通常，该值越大越好。计算公式如下：
```shell
    Sharp Ratio = (Rp - Rf) / Sigma(p)
```
* Rp: 策略年化收益
* Rf: 无风险利率，可以银行定期存款利率作为基准，通常设为4%。
* Sigma(p): 策略收益的波动率(策略收益的年化标准差) 

6. 最大回撤：
   表示策略最大损失，该值越小越好。有些库采用正值，有些采用负值表示，都是一个意思。计算公式如下：
```shell
   max_draw_down = (Px-Py)/Px
```
&emsp;&emsp;Px, Py: 一段时间内资产的最高和最低值。

7. Sortino率：
   评估策略亏损的风险，比略越高越好。公式如下：
```shell
    Sortino Ratio = (Rp - Rf) / Sigma(d)
```
* Rp: 策略年化收益
* Rf: 无风险利率，可以银行定期存款利率作为基准，通常设为4%。
* Sigma(p): 策略下行波动率

8. 胜率：
   即获胜的概率，比如10次交易中8次是盈利的，那么胜率就是80%。

9. 盈亏比
   在一段交易时间内，如果盈利12000，亏损8000，则比率为1.5。

10. 最大连续亏损
   在一段交易时间内，连续亏损的最大值。

# 2.3.2 回测注意事项
&emsp;&emsp;回测和真是交易存在一定的差异，因此，只可能尽可能接近实际的模拟，但和真实
存在一定差异，如：
* 概率性买入失败：真实交易可能存在涨跌停导致没有买入或卖出，而回测无法很好的模拟
* 滑点：由于价格快速实时波动，导致下单和实际成交价格存在差异，回测往往采用一个固定比率模拟
* 交易值：回测往往采取一天的收盘价或者平均价作为交易价格，与实际存在差异
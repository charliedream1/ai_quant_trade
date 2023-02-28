# 简介

qstock由“Python金融量化”公众号开发，试图打造成个人量化投研分析开源库，目前包括数据获取（data）、可视化(plot)、选股(stock)和量化回测（backtest）四个模块。其中数据模块（data）数据来源于东方财富网、同花顺、新浪财经等网上公开数据，数据爬虫部分参考了现有金融数据包tushare、akshare和efinance。qstock致力于为用户提供更加简洁和规整化的金融市场数据接口。可视化模块基于plotly.express和pyecharts包，为用户提供基于web的交互图形简单操作接口；选股模块提供了同花顺的技术选股和公众号策略选股，包括RPS、MM趋势、财务指标、资金流模型等，回测模块为大家提供向量化（基于pandas）和基于事件驱动的基本框架和模型。

qstock目前在pypi官网上发布，最早开源版本为1.1.0，目前更新至1.2.0版本

读者直接在cmd或anaconda prompt上输入“pip install qstock ”进行安装，或输入“pip install -upgrade qstock”进行更新。

GitHub地址：https://github.com/tkfy920/qstock。

目前部分策略选股和策略回测功能仅供知识星球会员使用，会员可在知识星球置顶帖子上上获取qstock-1.2.1.tar.gz （强化版）安装包，进行离线安装（将离线安装包放置在工作路径上使用'pip install qstock-1.2.1.tar.gz' 进行安装）。

下面为大家介绍qstock各模块的具体调用方式和应用举例。


```python
#导入qstock模块
import qstock as qs
```

# 数据模块
# 行情交易数据接口

## 实时行情数据
获取指定市场所有标的或单个或多个证券最新行情指标
realtime_data(market='沪深A', code=None):

- market表示行情名称或列表，默认'沪深A股',
    '沪深京A':沪深京A股市场行情; '沪深A':沪深A股市场行情;'沪A':沪市A股市场行情
    '深A':深市A股市场行情;北A :北证A股市场行情;'可转债':沪深可转债市场行情;
    '期货':期货市场行情;'创业板':创业板市场行情;'美股':美股市场行情;
    '港股':港股市场行情;'中概股':中国概念股市场行情;'新股':沪深新股市场行情;
    '科创板':科创板市场行情;'沪股通' 沪股通市场行情;'深股通':深股通市场行情;
    '行业板块':行业板块市场行情;'概念板块':概念板块市场行情;
    '沪深指数':沪深系列指数市场行情;'上证指数':上证系列指数市场行情
    '深证指数':深证系列指数市场行情;'ETF' ETF基金市场行情;'LOF' LOF 基金市场行情
- code:输入单个或多个证券的list，不输入参数，默认返回某市场实时指标
  如code='中国平安'，或code='000001'，或code=['中国平安','晓程科技','东方财富']

### 某市场所有标的最新行情


```python
#获取沪深A股最新行情指标
df=qs.realtime_data()
#查看前几行
df.head()
```

```python
#获取期货最新行情指标
df=qs.realtime_data('期货')
#查看前几行
df.head()
```



```python
#获取概念板块最新行情指标
df=qs.realtime_data('概念板块')
#查看前几行
df.head()
```


```python
#获取ETF最新行情指标
df=qs.realtime_data('ETF')
#查看前几行
df.head()
```



### 个股最新行情指标
- code:输入单个或多个证券的list，不输入参数，默认返回某市场实时指标
  如code='中国平安'，或code='000001'，或code=['中国平安','晓程科技','东方财富']


```python
qs.realtime_data(code=['中国平安','300684','锂电池ETF','BK0679','上证指数'])
```



### 日内成交数据
intraday_data(code)
- code可以为股票或债券或期货或基金代码简称或代码，如晓程科技或300139,返回股票、期货、债券等的最新交易日成交情况


```python
#股票日内交易数据
df=qs.intraday_data('中国平安')
df.head()
```


```python
#基金日内交易数据
df=qs.intraday_data('有色50ETF')
df.head()
```



### 获取个股实时交易快照
stock_snapshot(code):
- 获取沪深市场股票最新行情快照，code:股票代码


```python
qs.stock_snapshot('中国平安')
```



### 实时交易盘口异动数据
获取交易日实时盘口异动数据，相当于盯盘小精灵。
realtime_change(flag=None):
- flag：盘口异动类型，默认输出全部类型的异动情况。可选：['火箭发射', '快速反弹','加速下跌', '高台跳水', '大笔买入', '大笔卖出', 
 '封涨停板','封跌停板', '打开跌停板','打开涨停板','有大买盘','有大卖盘', 
 '竞价上涨', '竞价下跌','高开5日线','低开5日线',  '向上缺口','向下缺口', 
 '60日新高','60日新低','60日大幅上涨', '60日大幅下跌']
 上述异动类型分别可使用1-22数字代替。


```python
df=qs.realtime_change('60日新高')
#查看前几行
df.head()
```



```python
#异动类型：火箭发射
df=qs.realtime_change(1)
#查看前几行
df.head()
```





## 历史行情数据

### 历史K线

获取单只或多只证券（股票、基金、债券、期货)的历史K线数据。可以根据realtime_data实时行情接口获取相应金融市场交易标的的代码或简称，用于获取其历史K线数据。
- get_data(code_list, start='19000101', end=None, freq='d', fqt=1)
    
获取股票、指数、债券、期货、基金等历史K线行情。参数说明：
- code_list输入股票list列表，如code_list=['中国平安','贵州茅台','工业富联']
，返回多只股票多期时间的面板数据
- start和end为起始和结束日期，年月日
- freq:时间频率，默认日，1 : 分钟；5 : 5 分钟；15 : 15 分钟；30 : 30 分钟；
    60 : 60 分钟；101或'D'或'd'：日；102或‘w’或'W'：周; 103或'm'或'M': 月
    注意1分钟只能获取最近5个交易日一分钟数据
- fqt:复权类型，0：不复权，1：前复权；2：后复权，默认前复权

#### 个股数据


```python
#默认日频率、前复权所有历史数据
#open：开盘价，high：最高价，low：最低价，close：收盘价
#vol：成交量，turnover：成交金额，turnover_rate:换手率
#在notebook上输入"qs.get_data?"可查看数据接口的相应参数
df=qs.get_data('601318')
df.tail()
```


```python
#个股code_list可以输入代码或简称或多个股票的list
#获取中国平安2022年9月28日至今的5分钟数据，默认前复权
df=qs.get_data('中国平安',start='20220928',freq=5)
df.tail()
```


#### 获取美股数据


```python
#获取苹果公司股票数据
df=qs.get_data('AAPL')
df.tail()
```

#### 获取期货历史K线数据


```python
df=qs.get_data('棕榈油2210')
df.tail()
```

#### 指数
注意上证指数代码'000001'与平安银行股票代码相同，
为避免代码相同引起的混乱，获取指数数据，要输入指数的中文简称或拼音缩写。
如'sh'代表'上证指数'，'sz'代表'深证综指'，'cyb'代表‘创业板指'，'zxb'代表'中小100'（原来的中小板指数），'hs300'代表'沪深300'，'sz50'代表
'上证50','zz500'代表'中证500'等等


```python
code_list=['sh','sz','cyb','zxb','hs300','sz50','zz500']
df=qs.get_data(code_list)
df
```


```python
#全球指数可参见：https://quote.eastmoney.com/center/qqzs.html
global_indexs=['道琼斯','标普500','纳斯达克','恒生指数','英国富时','法国CAC40','德国DAX',
              '日经225','韩国KOSPI','澳大利亚标普200','印度孟买SENSEX','俄罗斯RTS','加拿大S&P',
               '台湾加权','美元指数','路透CRB商品指数']
```


```python
qs.get_data(global_indexs)
```


### 多只证券的历史价格数据
获取单只或多只证券（股票、基金、债券、期货)的收盘价格dataframe

- get_price(code_list, start='19000101', end='20500101', freq='d', fqt=1)

code_list输入股票list列表
 如code_list=['中国平安','贵州茅台','工业富联']


```python
code_list=['中国平安','300684','锂电池ETF','BK0679','上证指数']
df=qs.get_price(code_list)
df.tail()
```



## 股票龙虎榜数据
- stock_billboard(start=None, end=None)

起始和结束日期默认为None，表示最新，日期格式'2021-08-21'
  


```python
df=qs.stock_billboard('20220901','20221011')
df
```

    4it [00:01,  3.98it/s]                                                                                                 
    

# 基本面数据

## 股东持股情况

### 股票前十大股东信息
- stock_holder_top10(code, n=2)
   
获取沪深市场指定股票前十大股东信息
- code : 股票代码
- n :最新 n个季度前10大流通股东公开信息


```python
df=qs.stock_holder_top10('中国平安', n=2)
#df
```

### 沪深个股股东数量
- stock_holder_num(date=None)
获取沪深A股市场公开的股东数目变化情况
- date : 默认最新的报告期,
 指定某季度如'2022-03-31','2022-06-30','2022-09-30','2022-12-31'


```python
df=qs.stock_holder_num('20220930')
#df
```

### 大股东增减持变动明细


```python
#大股东
df=qs.stock_holder_change()
df.head()
```



### 机构持股
- institute_hold(quarter = "20221")

获取新浪财经机构持股一览表
- quarter: 如'20221表示2022年一季度，
其中的 1 表示一季报; "20193", 其中的 3 表示三季报;


```python
#2022年2季度
df=qs.institute_hold('20222')
#df
```

## 主营业务
- main_business(code= "000001")
    
获取公司主营业务构成
- code: 股票代码或股票简称


```python
df=qs.main_business('丰元股份')
#df.head()
```

## 财务报表

- financial_statement(flag='业绩报表',date=None):
- flag:报表类型,默认输出业绩报表;
    '业绩报表'或'yjbb'：返回年报季报财务指标;
    '业绩快报'或'yjkb'：返回市场最新业绩快报;
    '业绩预告'或'yjyg'：返回市场最新业绩预告;
    '资产负债表'或'zcfz'：返回最新资产负债指标;
    '利润表'或'lrb'：返回最新利润表指标;
    '现金流量表'或'xjll'：返回最新现金流量表指标.
- date:报表日期，如‘20220630’，‘20220331’，默认当前最新季报（或半年报或年报）


### 业绩报表


```python
df=qs.financial_statement('业绩报表',date='20220930')
#df.head()
```
                                                                                                                         

### 业绩预告


```python
df=qs.financial_statement('yjyg')
#df.head()
```

                                                                                                                           

### 业绩快报


```python
#注意参数设置有个小bug，目前调用会报错，将在新版本中修正！
df=qs.financial_statement('yjkb')
#df.head()
```

### 资产负债表


```python
df=qs.financial_statement('资产负债表')
#查看前几行
#df.head()
```

                                                                                                                           

### 利润表


```python
df=qs.financial_statement('利润表')
#查看前几行
#df.head()
```

                                                                                                                           

### 现金流量表


```python
df=qs.financial_statement('现金流量表')
#查看前几行
#df.head()
```
                                                                                                                           

## 财务指标

### 个股基本财务指标

- stock_basics(code_list)

code_list:代码或简称，可以输入单只或多只个股的list  
如：单只个股：code_list='中国平安'；  
多只个股code_list=['晓程科技','中国平安','西部建设']  
返回：代码、名称、净利润、总市值、流通市值、所处行业、市盈率、市净率、ROE、毛利率和净利率指标


```python
code_list=['300139','中国平安','西部建设','贵州茅台','丰元股份','002432']
df=qs.stock_basics(code_list)
#df
```
    

### 个股详细财务指标
- stock_indicator(code):
   
获取个股历史报告期所有财务分析指标

    code: 股票代码或简称


```python
df=qs.stock_indicator('中国平安')
#df.head()
```
                                                                                                                           

## 每股收益预测


```python
df=qs.eps_forecast()
#df.head()
```

# 指数成分股
获取常见指数的成分股

- index_member(code)  
  code : 指数名称或者指数代码


```python
#上证50成份股
df=qs.index_member('sz50')
#查看前几行数据
#df.head()
```


```python
#沪深300成分股
#qs.index_member('hs300')
```

# 概念板块数据
获取同花顺概念板块名称、成分股、和行情数据

## 获取同花顺概念板块名称
- ths_index_name(flag='概念')
 
  flag='概念板块' or '行业板块'


```python
#行业板块名称
name_list=qs.ths_index_name('行业')
#查看5个
name_list[:5]
```


    ['种植业与林业', '养殖业', '农产品加工', '农业服务', '煤炭开采加工']



```python
#概念板块名称
name_list=qs.ths_index_name('概念')
#查看5个
name_list[:5]
```
                                                                                                                          


    ['信创', '有机硅概念', '空气能热泵', '先进封装（Chiplet）', '减速器']



## 概念板块成分股
获取同花顺概念板块成分股
注意，同花顺数据接口不太稳定，如报错过一段时间再试。
- ths_index_member(code=None)

code:输入板块行业或概念代码或简称
   


```python
#比如种植业与林业成分股
df=qs.ths_index_member('种植业与林业')
#查看前几行
#df.head()
```

                                                                                                                           
```python
#比如有机硅概念
df=qs.ths_index_member('有机硅概念')
#查看前几行
#df.head()
```

                                                                                                                           

## 概念指数行情数据
获取同花顺概念或行业板块指数行情数据(开盘、最高、最低、收盘和成交量）
- ths_index_data(code=None)
   
code:输入板块行业或概念代码或简称

```python
df=qs.ths_index_data('有机硅概念')
#df.head()
```

                                                                                                                           

# 资金流数据

## 日内资金流数据
- intraday_money(code)
 
 code : 股票、债券代码
 
 获取单只股票最新交易日的日内分钟级单子流入流出数据


```python
#注意要在交易日交易时段才能获取到相应数据
df=qs.intraday_money('中国平安')
#df.head()
```

## 历史资金流向数据
- hist_money(code)

 code : 股票、债券代码
 
 获取股票、债券、期货等的历史单子流入流出数据


```python
df=qs.hist_money('中国平安')
#df.tail()
```

## 个股n日资金流
- stock_money(code, ndays=[3, 5, 10, 20])

stock可以为股票简称或代码，如晓程科技或300139
ndays为时间周期或list，如3日、5日、10日等


```python
#默认ndays=[3, 5, 10, 20]
df=qs.stock_money('中国平安')
#df
```


```python
df=qs.stock_money('中国平安',[10,30,60])
#df.tail()
```

## 同花顺资金流数据
获取同花顺个股、行业、概念资金流数据
- ths_money(flag=None,n=None):
- flag:'个股','概念','行业'
- n=1,3,5,10,20分别表示n日资金累计净额


```python
#个股20日资金流数据
df=qs.ths_money('个股',n=20)
#df.tail()
```

    


```python
#行业板块10日资金流数据
df=qs.ths_money('行业',n=10)
#df.tail()
```


    


```python
#概念板块5日资金流数据
df=qs.ths_money('概念',n=5)
#df.tail()
```

 
    

# 北向资金
- north_money(flag=None,n=1)

- flag=None，默认返回北上资金总体每日净流入数据
- flag='行业',代表北向资金增持行业板块排行
- flag='概念',代表北向资金增持概念板块排行
- flag='个股',代表北向资金增持个股情况
- n:  代表n日排名，n可选1、3、5、10、‘M’，‘Q','Y'
即 {'1':"今日", '3':"3日",'5':"5日", '10':"10日",'M':"月", 'Q':"季", 'Y':"年"}

## 北向资金每日净流入


```python
#北向资金每日净流入数据
df=qs.north_money()
#df.tail()
```

## 北向资金增持行业板块


```python
#北向资金增持行业板块5日排名
df=qs.north_money('行业',5)
#df.tail()
```

## 北向资金增持概念板块


```python
#北向资金增持概念板块
df=qs.north_money('概念',5)
#df.tail()
```

## 北向资金增持个股情况


```python
#北向资金增持个股情况
#有个小bug，列名没有对应起来，该函数调用将报错，将在新版本中修正。
df=qs.north_money('个股',5)
#df.tail()
```

# 宏观经济指标

获取宏观经济常见指标
- macro_data(flag=None)

flag:lpr:贷款基准利率；ms：货币供应量；cpi:消费者物价指数；
    ppi:工业品出厂价格指数;pmi:采购经理人指数
    默认返回gdp数据

对应数据也可以使用相应接口，如qs.cpi()、qs.gdp()、qs.ms()、qs.ppi()、qs.pmi()、qs.lpr()可以分别获取CPI、GDP、货币供应量、PPI、PMI数据。

## GDP数据


```python
df=qs.macro_data('gdp')
#df
```

## CPI物价指数


```python
df=qs.macro_data('cpi')
#df
```

## PPI工业品出厂价格指数


```python
df=qs.macro_data('ppi')
#df
```

## pmi采购经理人指数


```python
df=qs.macro_data('pmi')
#df
```

## 货币供应量


```python
df=qs.macro_data('ms')
#df
```

## 贷款基准利率LPR


```python
df=qs.macro_data('lpr')
#df
```

# 同业拆借利率

同业拆借利率
- ib_rate(market='sh',fc=None):
- market:同业拆借市场简称，各个市场英文缩写为：
{'sh':'上海银行同业拆借市场','ch':'中国银行同业拆借市场','l':'伦敦银行同业拆借市场',
'eu':'欧洲银行同业拆借市场','hk':'香港银行同业拆借市场','s':'新加坡银行同业拆借市场'}
- fc：外币币种，输入币种的英文简称，"CNY"(人民币):,"GBP"(英镑),"EUR"(欧元) ,"USD"(美元) ,"HKD"(港币) ,"SGD"(星元) 
香港市场，fc可选：'HKD'，'USD','CNY'；新加坡市场，fc可选：'SGD','USD';伦敦市场，fc可选：'GBP','USD','EUR','JPY'；

## 上海银行同业拆借市场


```python
#默认输出上海银行同业拆借市场利率
#或输入market='sh'
df=qs.ib_rate()
#df
```
                                                                                                                         

## 中国银行同业拆借市场


```python
df=qs.ib_rate(market='ch')
#df
```                                                                                                                          

## 伦敦银行同业拆借市场


```python
#伦敦简称l，注意是英文字母‘l’(London的首字母小写)，不是数字1！
#币种可选GBP'英镑',USD'美元',EUR'欧元',JPY'日元'
df=qs.ib_rate(market='l',fc='GBP')
#df
```

                                                                                                                          

```python
#伦敦美元
df=qs.ib_rate('l','USD')
#df
```

                                                                                                                          

```python
#伦敦欧元
df=qs.ib_rate('l','EUR')
#df
```

                                                                                                                           


```python
#伦敦日元
df=qs.ib_rate('l','JPY')
#df
```

                                                                                                                           

## 欧洲银行同业拆借市场


```python
#欧元
df=qs.ib_rate('eu')
#df
```

                                                                                                                           

## 香港银行同业拆借市场


```python
#香港市场美元
df=qs.ib_rate('hk','USD')
#df
```

                                                                                                                           


```python
#香港市场港币
df=qs.ib_rate('hk','HKD')
#df
```

                                                                                                                           


```python
#香港市场人民币
df=qs.ib_rate('hk','CNY')
#df
```
                                                                                                                     

## 新加坡市场


```python
#新加坡美元利率
df=qs.ib_rate('s','usd')
#df
```

                                                                                                                           

```python
#新加坡星元利率
df=qs.ib_rate('s','SGD')
#df
```
                                                                                                                           

# 财经新闻数据

新闻资讯数据
- news_data(news_type=None,start=None,end=None,code=None):
    
- news_type:新闻类型：cctv'或'新闻联播'；
    'js'或'金十数据'；'stock' 或'个股新闻'
    不输入参数，默认输出财联社电报新闻数据。
- start:起始日期，如'20220930',不输入默认当前最新日期
- end:结束日期，如'20221001'，不输入默认当前最新日期
- stock：个股代码，个股新闻时需输入该参数

## 财联社电报新闻数据


```python
#默认参数输出财联社电报新闻数据
df=qs.news_data()
#df.tail()
```

## 市场快讯数据


```python
df=qs.news_data('js')
#df.tail()
```
    

## 新闻联播文字


```python
#参数start起始日期，end结束日期，使用默认参数输出最新日期新闻联播
df=qs.news_data('cctv',start='20221016',end='20221016')
#df.head()
```                                                                                                                          


```python
#也可以使用新闻联播数据接口获取，start和end默认为最新日期
df=qs.news_cctv(start='20221016',end='20221016')
#df.head()
```

                                                                                                                           

## 个股新闻


```python
#使用新闻统一接口
df=qs.news_data('个股',code='天瑞仪器')
#df.head()
```


```python
#使用个股新闻接口
df=qs.stock_news('天瑞仪器')
#df.head()
```

```python
import qstock as qs
from qstock import plot
```

# K线图

## 普通K线图

- kline(df, mas=5, mal=20, notebook=True,title="股票K线图")

参数说明：
- df:数据，包含open,high,low,close,volume列名的dataframe
- mas：短期均线，默认5日均线
- mal：长期均线，默认20日均线
- notebook：True代表在jupyter notebook上显示，False默认输出html，可以保存本地打开。默认为True
- title:图形标题


```python
#如果notebook不显示pyecharts的图形，在前面加上以下代码(去掉前面注释)
#from pyecharts.globals import CurrentConfig, NotebookType
#CurrentConfig.NOTEBOOK_TYPE = NotebookType.JUPYTER_NOTEBOOK
```


```python
#获取中国平安2022年至今前复权的数据
df=qs.get_data('中国平安',start='2022-06-01',end='2022-10-20')
#df.tail()
```

    100%|██████████████████████████████████████████████████████████████████████████████████| 1/1 [00:00<00:00, 1000.31it/s]
    


```python
#使用默认参数
#plot.kline(df)
```

## 修正K线图

- HA_kline(df)

参数df与前面普通k线图线图。

也叫平均K线图（Heikin-Ashi），具体原理可以参考公众号推文[《【手把手教你】使用Python对股价的Heikin Ashi蜡烛图进行可视化》](https://mp.weixin.qq.com/s?__biz=MzUyMDk1MDY2MQ==&amp;mid=2247484569&amp;idx=1&amp;sn=5e08729f109f1ed4b40323d4ffc24737&amp;chksm=f9e3c273ce944b65d5cb7ae41aa63738ae3ed41e3d0951621ced2a7b4c66cff943fab998bde1&token=292674644&lang=zh_CN#rd)。

普通K线图中往往存在很多噪声，这些噪声容易掩盖市场真实趋势的随机波动，包括价格和成交量波动。比如，对市场影响持续性较短的新闻事件，以及对技术指标和市场趋势解读等，都可能造成无意义的短期价格和交易量波动，这样的噪声会对交易者分析市场产生干扰和误导。为了减少普通K线图产生的噪声，HA蜡烛图应运而生，HA中的四个价格中，HA开盘价和HA收盘价都是经过平均计算得来，平均化的处理相当于噪声消除处理，在一定程度上消除了市场的噪声，可以更加明确地反映市场价格的走势。


```python
#plot.HA_kline(df)
```

# 树状图
- treemap(data, label, weight, value, color=['Green', 'Red', "#8b0000"])

参数说明：
- data：dataframe数据格式
- label：需要展示的列名或标签名，必须是list,如[px.Constant('股票'), '行业',  '股票名称']
    其中，'行业',  '股票名称'必须是data里的存在的列名
- weight:data里存在的列，用来显示权重
- value:data里存在的列，用来显示数值
- color：设置展示的颜色


```python
#获取东方财富行业板块实时涨跌幅数据
data=qs.realtime_data('行业板块')[['名称','涨幅']]
data['权重']=abs(data['涨幅'])
#注意去掉涨幅为0的值，否则会报错
data=data[data['涨幅']!=0]
params={'data':data,'label':['名称'],'weight':'权重','value':'涨幅'}
#plot.treemap(**params)
```


```python
#获取东方财富概念板块实时涨跌幅数据
data=qs.realtime_data('概念')[['名称','涨幅']]
data['权重']=abs(data['涨幅'])
data=data[data['涨幅']!=0]
params={'data':data,'label':['名称'],'weight':'权重','value':'涨幅'}
#plot.treemap(**params)
```

# ichimoku云图

- plot_ichimoku(df, t=9, k=26, l=30, s=52):

参数说明：
- df为dataframe数据，包含'open','high','low','close','volume‘列，索引为时间格式
- t:Tenkan-sen：转折线计算周期，默认9个交易日
- k：Kijun-sen：基准线计算周期，默认26
- l:Chikou Span：滞后跨度或延迟线计算周期，默认30天
- s:Senkou Span B：计算前导跨度B或先行上线B，默认52个交易日

Ichimoku，是一名日本报纸作家提出的，用于衡量动量以及未来价格支撑和阻力区域的技术分析指标，目前被广泛用于判断外汇、期货、股票、黄金等投资品种的趋势和动量。关于ichimoku云图的基本原理详细以参考公众号推文：[《【手把手教你】Ichimoku云图指标可视化与交易策略回测》](https://mp.weixin.qq.com/s?__biz=MzUyMDk1MDY2MQ==&amp;mid=2247486220&amp;idx=1&amp;sn=325565ed3aa01cc1cecfed9cbe1a2ae8&amp;chksm=f9e3cde6ce9444f044c43811a4af95ba779c1b13f1ba619aa2182ba316d9ded04872f5cd3473&token=292674644&lang=zh_CN#rd)


```python
df=qs.get_data('丰元股份',start='2021-03-01')
#plot.plot_ichimoku(df)
```

  
    

# 基本图形

## 折线图
- line(data=None, x=None, y=None, title=None, color=None, line_group=None, facet_col=None, legend=True):

参数：data为series或dataframe的时候，可以不输入x和y。x为x坐标轴对应数据，y为y轴坐标对应数据。

### 普通折线图


```python
#获取中国平安前复权价格数据
code='中国平安'
df=qs.get_data(code)
#plot.line(df.close,title=code+'价格走势')
```

   

### 股价分位点折线图

- stock_line(data=None, x=None, y=None, notebook=True, title=None)

参数与前面画图函数相同


```python
#plot.stock_line(df.close)
```

### 对比折线图


```python
df['ma20']=df.close.rolling(20).mean()
title='中国平安股价与20日均线'
#plot.line(df[['close','ma20']],title=title)
```


```python
#个股资金流
#plot.line(qs.stock_money('中国平安'),title='中国平安资金流')
```

全球指数累计涨幅可视化


```python
#常见的全球指数名称
global_indexs=['sh','cyb','恒生指数','道琼斯','标普500','纳斯达克','英国富时100','法国CAC40','德国DAX30','日经225','韩国KOSPI',
               '澳大利亚标普200','印度孟买SENSEX','台湾加权','俄罗斯RTS','加拿大S&P/TSX','巴西BOVESPA']
index_data=qs.get_price(global_indexs,start='2012-01-01').dropna()
#plot.line(index_data/index_data.iloc[0],title='全球指数累计涨幅(2012-2022)')
```

    
    

## 柱状图

- bar(data=None, x=None, y=None, title=None, color=None, legend=False,orientation=None, log_x=False, log_y=False, barmode='group')

参数说明：
'orientation='h'表示横向柱状图,log_x和log_y为True表示使用对数坐标，
    barmode='group'表示对比条形图,默认。为'relative'，
    如qs.bar(dd['总市值'],log_x=True,orientation='h')。


```python
#计算收益率
data=index_data.copy().dropna()
rets=data/data.shift(1)-1
rets=rets.to_period('Y')
rets=(rets.groupby(rets.index).apply(lambda x: ((1+x).cumprod()-1).iloc[-1])*100).round(2)
rets=rets.iloc[-1].sort_values(ascending=False)
```


```python
title='全球指数2022年涨跌幅'
#plot.bar(rets,title=title)
```

基于pyecharts画柱状图

- chart_bar(data=None, x=None, y=None, title=None, notebook=True, zoom=False)

x,y均为list，或者x为dataframe


```python
#plot.chart_bar(rets,title=title,zoom=True)
```

纵向柱状图
- chart_inv_bar(data=None, x=None, y=None, title=None, notebook=True, zoom=False)

x,y均为list，或者x为dataframe


```python
#plot.chart_inv_bar(rets,title=title,zoom=True)
```

## 散点图

- scatter(data=None, x=None, y=None, title=None, color=None, size=None,trend=None, legend=True, marginal_x=None, marginal_y=None)

参数说明：
color根据不同类型显示不同颜色；
size根据值大小显示散点图的大小；
trend='ols'添加回归拟合线；
marginal_x='violin',添加小提琴图；
marginal_y= 'box'，添加箱线图。


```python
data=qs.get_data('晓程科技')
#plot.scatter(data,x='close',y='volume')
```

  
    


```python
data=qs.get_data('晓程科技')
#计算收益率
data['ret']=data.close/data.close.shift(1)-1
data['weight']=data['ret'].abs()
#对换手率分类
data.loc[data.turnover_rate>20,'rr']='crazy'
data.loc[(10<data.turnover_rate)&(data.turnover_rate<20),'rr']='high'
data.loc[(5<data.turnover_rate)&(data.turnover_rate<10),'rr']='mid'
data.loc[data.turnover_rate<5,'rr']='low'
data.dropna(inplace=True)
```

    
    


```python
#plot.scatter(data,x='turnover_rate',y='close',size='weight',trend='ols',marginal_x='histogram',marginal_y='box')
```

## 饼图

- pie(data=None, x=None, y=None, color=None, title=None, legend=False, hole=None)

data为dataframe数据，value；
hole数值0-1，显示中间空心；
legend=True显示图例，默认不显示。

实例：个股主营业务占比可视化


```python
code='晓程科技'
df=qs.main_business(code)
c1=df['报告期']=='2022中期'
c2=df['分类方向']=='按产品分'
df=df[c1&c2]
#df
```


```python
#plot.pie(df.iloc[:-1],x='分类',y='营业收入(万)',title=code+'主营业务收入')
```

基于pyecharts画饼图

- chart_pie(data=None, x=None, y=None, data_pair=None, title=None, notebook=True)

参数与前面相同


```python
#plot.chart_pie(data=df.iloc[:-1],x='分类',y='营业收入(万)',title=code+'主营业务收入')
```

# 统计分布图

## 直方图

- hist(data=None, x=None, y=None, title=None, color=None, legend=False,orientation=None, log_x=False, log_y=False, barmode='group',
histnorm=None)

histnorm={1:'percent',2:'probability',3:'density',4:'probability density'}，其他参数与前面相同。


```python
#1:'percent',2:'probability',3:'density',4:'probability density'
code='晓程科技'
data=qs.get_data(code,fqt=2)
#plot.hist(data,x='close',histnorm=3,title=code+'股价直方图')
```

  
    

## 概率密度图
- hist_kde(data=None, x=None, y=None, kde=True, stat='count', figsize=(15, 7)):

直方图默认统计的是观测数，可以进行统计变化，设置stat参数。
stat可选参数：count:观测数(默认)；
 frequency:频数;density：密度;probability:概率；
 kde=True表示添加核密度曲线。
 
 其他参数与前面相同


```python
#stat可选参数：count:观测数(默认);frequency:频数;density：密度;probability:概率
#plot.hist_kde(data.close,stat='probability')
```

## 箱线图
- box(data=None, x=None, y=None, title=None, color=None, legend=False,orientation=None, log_x=False, log_y=False, boxmode=None)

参数与前面相类似。


```python
index_list=['上证指数','创业板指','沪深300','道琼斯','标普500','纳斯达克']
data=qs.get_price(index_list)
#plot.box(data.dropna())
```

    
    


```python
#获取面板数据
dd=qs.get_data(index_list)
plot.box(dd,x='name',y='close',color='name')
```

    

```python
#plot.box(dd,y='name',x='close',color='name',orientation='h')
```

## 小提琴图
- violin(data=None, x=None, y=None, title=None, color=None, legend=False,orientation=None, log_x=False, log_y=False, box=False, points=None)


```python
#plot.violin(dd,x='name',y='close',color='name',box=True)
```

小提琴是是箱线图和核密度图的集合，通过箱线思维展示数据的各个百分位点。小提琴图上的核密度图展示了数据分布的形状，分布越宽的位置表示数据越集中于该处，反之则说明该处数据分布越少。


```python
#plot.violin(dd,y='name',x='close',color='name',box=True,orientation='h')
```


```python
#plot.violin(dd.query('name=="上证指数"'),y='name',x='close',box=True,orientation='h')
```


```python
#plot.violin(dd.query('name=="道琼斯"'),y='name',x='close',box=True,orientation='h')
```

# 热力图

- chart_heatmap(x, y, v, title=None, notebook=True)


```python
sh0=qs.get_data('上证指数').close['2011':'2021']
sh=(sh0/sh0.shift(1)-1).to_period('M')
sh=sh.groupby(sh.index).apply(lambda x: ((((1+x).cumprod()-1).iloc[-1])*100).round(2))
```

    


```python
x=[str(i) for i in range(2011,2022)]
y=[str(i)+'月' for i in range(1,13)]
v= [[i,j,sh[str(2011+i)+'-'+str(1+j)]] for i in range(11) for j in range(12)]
#plot.chart_heatmap(x,y,v,title='上证指数月度收益率')
```


```python
#plot.chart_heatmap_color(x,y,v,title='上证综指月度收益率')
```

# 地图

- chart_map(data=None, x=None, y=None, data_pair=None, title=None, notebook=True)


```python
df=qs.realtime_data('地域')
df['名称']=df['名称'].apply(lambda s:s[:-2] if s.endswith('板块') else s)
#df.head()
```


```python
#地域板块最新价格指数
#plot.chart_map(df,x='名称',y='最新')
```

# 词云图


```python
#txt=qs.news_data('cctv',start='20221020',end='20221021')
```


```python
#缺失值处理，转为str格式
txt_list=''.join(list(txt.content.apply(lambda s:str(s))))
```


```python
#使用jieba处理分词并转为词云格式数据
c_data=plot.cloud_data(txt_list)
#画词云图
#plot.chart_wordcloud(c_data)
```


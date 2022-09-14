# -*- coding: utf-8 -*-
# @Author   : ly
# @Time     : 2022/6/23 22:51
# @File     : SVM动态因子选择策略.py
# @Project  : ai_quant_trade
# Copyright (c)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
策略说明：
问题：如果回测某个区间最大回撤很大，说明这个时间点选取的因子可能不合适，如何自动判断因子重要性，并选择？

因子选择：
- 基本面因子：https://www.joinquant.com/help/api/help#name:Stock
- 技术分析指标因子：https://www.joinquant.com/help/api/help#name:technicalanalysis

策略思路
1. 因子筛选：通过基本面和技术面人工选择需要使用的因子
2. 训练决策树：对长周期收益增加的打标签1，否则0。对收益进行分类。之后，按照因子的重要性，选择top的因子
3. 训练回归支持向量机：使用挑选的重要因子训练。真实市值和模型预测的市值差，找到预测和真实值差值最小的选择购买
4. 买入策略：大盘近期涨时，进行买入
5. 卖出策略：大盘跌时卖出持仓股票，或者市值低于均值，或者持仓不在购买列表中
"""
# 导入函数库
# 1. 导入系统库函数
from jqlib.technical_analysis import *
from jqdata import *

# 2. 导入其它库
import datetime
import pandas as pd
import numpy as np

from sklearn.svm import SVR
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import StandardScaler


# =======================================================
# ================== 1. 初始化函数 ======================
# 交易相关全局变量
def trade_vars():
    # （g.为全局变量）
    # 持仓数量
    g.stocknum = 3
    # 交易日计时器
    g.days = 0
    # 调仓频率
    g.refresh_rate = 10
    # 初始收益率
    g.ret = -0.01
    # 交易状态，初始不进行交易
    g.if_trade = False
    # 使用的股票池，使用沪深300
    g.ref_index_stock = '000300.XSHG'
    g.list_to_buy = []
    g.list_to_sell = []


# 初始化函数，设定基准等等
def initialize(context):
    # 交易相关全局变量
    trade_vars()

    # 1. 设定回测相关参数
    set_test_conditions(context)

    ## 2. 运行函数（reference_security为运行时间的参考标的；传入的标的只做种类区分，因此传入'000300.XSHG'或'510300.XSHG'是一样的）
    # 开盘前运行，如果模型跑不完，则设置更早的启动时间，time改为'8:00'
    run_daily(before_market_open, time='before_open', reference_security=g.ref_index_stock)
    # 开盘时运行
    run_daily(market_open, time='open', reference_security=g.ref_index_stock)
    # 收盘后运行
    run_daily(after_market_close, time='after_close', reference_security=g.ref_index_stock)


# 设定回测相关参数
def set_test_conditions(context):
    # 设定沪深300作为基准
    set_benchmark(g.ref_index_stock)
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    # 输出内容到日志 log.info()
    log.info('初始函数开始运行且全局只运行一次')

    # 过滤掉order系列API产生的比error级别低的log
    # log.set_level('order', 'error')

    # 设置滑点费用
    # set_slippage(PriceRelatedSlippage(0.00246))

    ### 股票相关设定 ###
    # 股票类每笔交易时的手续费是：买入时佣金万分之三，卖出时佣金万分之三加千分之一印花税, 每笔交易佣金最低扣5块钱
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5),
                   type='stock')


# =======================================================
# ================== 2. 开盘前运行函数 ======================
def before_market_open(context):
    # 输出运行时间
    log.info('函数运行时间(before_market_open)：' + str(context.current_dt.time()))

    # 给微信发送消息（添加模拟交易，并绑定微信生效）
    # send_message('美好的一天~')

    # 调仓日判断
    if g.days % g.refresh_rate == 0:
        g.if_trade = True  # 开始交易
        stock_lst = filter_paused_stocks(context)
        g.list_to_buy = stocks_to_buy(context, stock_lst)
        g.list_to_sell = stocks_to_sell(context, g.list_to_buy)
    g.days += 1


# 2.1 过滤停牌的股票
def filter_paused_stocks(context):
    # 使用沪深300作为股票池
    stocks = get_index_stocks(g.ref_index_stock)
    # 过滤停牌股票
    paused_stocks = []
    current_data = get_current_data()
    for i in stocks:
        paused_stocks.append(current_data[i].paused)
    log.info('停牌股票数量（%s / %s）' % (len(paused_stocks), len(stocks)))
    df_paused_stocks = pd.DataFrame({'paused_stocks': paused_stocks}, index=stocks)
    stock_lst = list(df_paused_stocks.index[df_paused_stocks.paused_stocks == False])
    log.info('过滤停牌后可选股票数量' + str(len(stock_lst)))
    return stock_lst


# 2.2 生成买入股票列表
def stocks_to_buy(context, stock_lst):
    list_to_buy = []
    today = context.current_dt
    day2 = today - datetime.timedelta(days=5)
    # 获取大盘收盘价
    hs300_clos = get_price(g.ref_index_stock, day2, today, fq='pre')['close']
    hs300_ret = hs300_clos[-1] / hs300_clos[0] - 1
    # 如果大盘收益大于设定的基准收益，则买入
    if hs300_ret > g.ret:
        factor = get_mdl(context, stock_lst)
        list_to_buy = list(factor.index[:g.stocknum])
    return list_to_buy


# 2.3 生成卖出股票列表
def stocks_to_sell(context, list_to_buy):
    list_to_sell = []
    today = context.current_dt
    day2 = today - datetime.timedelta(days=5)
    hs300_clos = get_price(g.ref_index_stock, day2, today, fq='pre')['close']
    hs300_ret = hs300_clos[-1] / hs300_clos[0] - 1
    for stock_sell in context.portfolio.positions:
        if hs300_ret <= g.ret:
            # 如果大盘收益小于等于设定的基准收益，则卖出
            list_to_sell.append(stock_sell)
        else:
            # 大盘跌时卖出持仓股票，或者市值低于均值，或者持仓不在购买列表中
            if context.portfolio.positions[stock_sell].price / \
                    context.portfolio.positions[stock_sell].avg_cost < 0.95 or \
                    stock_sell not in list_to_buy:
                list_to_sell.append(stock_sell)
    return list_to_sell


# *****************************************************
# == 2.4 模型训练和预测
def get_mdl(context, stock_lst):
    df, x, y = data_prepare(context, stock_lst)
    x1, y1 = feature_selection(df, x, y)
    mdl = train_mdl(x1, y1)
    # 找到市值与模型预测的差，并作为新的因子返回
    predict = pd.DataFrame(mdl.predict(x1),
                           # 保持和y相同的index，也就是股票的代码
                           index=y1.index,
                           # 设置一个列名，这个根据你个人爱好就好
                           columns=['市值'])
    # 使用真实的市值，减去模型预测的市值
    diff = y1 - predict  # ['市值']
    # 将两者的差存入一个数据表，index还是用股票的代码
    # diff = pd.DataFrame(diff, index = y.index, columns = ['diff'])
    # 将该数据表中的值，按生序进行排列
    diff = diff.sort_values(by='市值', ascending=True)
    return diff


# 2.4.1 机器学习模型数据准备
def data_prepare(context, stock_lst):
    # =======================
    # 1.数据准备
    #  1.1 加载基本面因子数据
    # 创建query对象，指定获取股票的代码、市值、净运营资本
    # 净债务、产权比率、股东权益比率、营收增长率、换手率、
    # 市盈率（PE）、市净率（PB）、市销率（PS）、总资产收益率因子
    q = query(valuation.code, valuation.market_cap,
              balance.total_current_assets - balance.total_current_liability,
              balance.total_liability - balance.total_assets,
              balance.total_liability / balance.equities_parent_company_owners,
              (balance.total_assets - balance.total_current_assets) / balance.total_assets,
              balance.equities_parent_company_owners / balance.total_assets,
              indicator.inc_total_revenue_year_on_year,
              valuation.turnover_ratio,
              valuation.pe_ratio,
              valuation.pb_ratio,
              valuation.ps_ratio, indicator.roa).filter(
        valuation.code.in_(stock_lst))
    # 将获得的因子值存入一个数据表
    df = get_fundamentals(q, date=None)
    # 把数据表的字段名指定为对应的因子名
    df.columns = ['code', '市值', '净营运资本',
                  '净债务', '产权比率', '非流动资产比率',
                  '股东权益比率', '营收增长率'
        , '换手率', 'PE', 'PB', 'PS', '总资产收益率']
    # 将股票代码作为数据表的index
    df.index = df.code.values
    # 使用del也可以删除列
    del df['code']

    # 主要时间点设定
    today = context.current_dt
    # 设定2个时间差，分别是50天，1天
    delta50 = datetime.timedelta(days=50)
    delta1 = datetime.timedelta(days=1)
    # 50日前作为一个历史节点
    history = today - delta50
    # 再计算昨天的日期
    yesterday = today - delta1

    # 1.2 获取最新的技术因子
    # 下面就获取股票的动量线、成交量、累计能量线、平均差、
    # 指数移动平均、移动平均、乖离率等因子
    # 时间范围都设为10天
    df['动量线'] = list(MTM(df.index, yesterday,
                         timeperiod=10, unit='1d',
                         include_now=True,
                         fq_ref_date=None).values())
    df['成交量'] = list(VOL(df.index, yesterday, M1=10,
                         unit='1d', include_now=True,
                         fq_ref_date=None)[0].values())
    df['累计能量线'] = list(OBV(df.index, check_date=yesterday,
                           timeperiod=10).values())
    df['平均差'] = list(DMA(df.index, yesterday, N1=10,
                         unit='1d', include_now=True,
                         fq_ref_date=None)[0].values())
    df['指数移动平均'] = list(EMA(df.index, yesterday, timeperiod=10,
                            unit='1d', include_now=True,
                            fq_ref_date=None).values())
    df['移动平均'] = list(MA(df.index, yesterday, timeperiod=10,
                         unit='1d', include_now=True,
                         fq_ref_date=None).values())
    df['乖离率'] = list(BIAS(df.index, yesterday, N1=10,
                          unit='1d', include_now=True,
                          fq_ref_date=None)[0].values())
    # 把数据表中的空值用0来代替
    df.fillna(0, inplace=True)
    # 获取股票前一日的收盘价
    df['close1'] = get_price(stock_lst,
                             start_date=yesterday,
                             end_date=yesterday,
                             fq='pre', panel=False)['close'].T
    # 获取股票50日前的收盘价
    df['close2'] = get_price(stock_lst,
                             start_date=history,
                             end_date=history,
                             fq='pre', panel=False)['close'].T

    # 计算出收益
    df['return'] = df['close1'] / df['close2'] - 1
    # 如果收益大于平均水平，则标记为1，否则标记为0
    df['signal'] = np.where(df['return'] < df['return'].mean(), 0, 1)
    # 把因子值作为样本的特征，所以要去掉刚刚添加的几个字段
    x = df.drop(['close1', 'close2', 'return', 'signal'], axis=1)
    # 把signal作为分类标签
    y = df['signal']
    x = x.fillna(0)
    y = y.fillna(0)
    return df, x, y


# 2.4.2 特征选择
def feature_selection(df, x, y):
    # 使用决策树模型筛选特征
    # 创建决策树分类器实例，指定random_state便于复现
    clf = DecisionTreeClassifier(random_state=1000)
    # 拟合训练集数据
    clf.fit(x, y)
    # 数据表有两个字段，分别是特征名和重要性
    # 特征名就是因子的名称
    # 重要性就是决策树给出的feature_importances_
    factor_weight = pd.DataFrame({'features': list(x.columns),
                                  'importance': clf.feature_importances_}).sort_values(
        # 这里根据重要程度降序排列，一遍遍找到重要性最高的特征
        by='importance', ascending=False)
    # 选出最重要的5个特征
    features = factor_weight['features'][:10]
    x_new = df[features]
    y_new = df['市值']
    x_new = x_new.fillna(0)
    y_new = y_new.fillna(0)
    return x_new, y_new


# 2.4.3 训练机器学习模型
def train_mdl(x, y):
    # 训练支持向量机
    svr = SVR()
    model = svr.fit(x, y)
    return model


# =======================================================
# ================== 3. 开盘时运行函数 ======================
def market_open(context):
    log.info('函数运行时间(market_open):' + str(context.current_dt.time()))
    if g.if_trade:
        sell_operation(g.list_to_sell)
        buy_operation(context, g.list_to_buy)
    g.if_trade = False


# 3.1 执行买入操作
def buy_operation(context, list_to_buy):
    if len(context.portfolio.positions) < g.stocknum:
        num = g.stocknum - len(context.portfolio.positions)
        cash = context.portfolio.cash / num
    else:
        cash = 0
        num = 0
    for stock_sell in list_to_buy[:num + 1]:
        order_target_value(stock_sell, cash)
        num = num - 1
        if num == 0:
            break


# 3.2 执行卖出操作
def sell_operation(list_to_sell):
    for stock_sell in list_to_sell:
        order_target_value(stock_sell, 0)


# =======================================================
# ================== 4. 收盘后运行函数 ======================
def after_market_close(context):
    log.info(str('函数运行时间(after_market_close):' + str(context.current_dt.time())))
    # 得到当天所有成交记录
    trades = get_trades()
    for _trade in trades.values():
        log.info('成交记录：' + str(_trade))
    log.info('一天结束')
    log.info('##############################################################')

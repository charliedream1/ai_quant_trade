# -*- coding: utf-8 -*-
# @Author   : ly
# @Time     : 2022/6/23 22:41
# @File     : 龙虎榜+均线.py
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

# 策略: 1.只做强势股 2.少即是多 3.看长做短
# 大周期看涨，小周期买入 (看上涨趋势(突破后持续关注)，30分钟或者小时突破时择时买入)
# 导入函数库
from jqdata import *


# 初始化函数，设定基准等等
def initialize(context):
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    # 输出内容到日志 log.info()
    log.info('初始函数开始运行且全局只运行一次')
    # 过滤掉order系列API产生的比error级别低的log
    # log.set_level('order', 'error')

    ### 股票相关设定 ###
    # 股票类每笔交易时的手续费是：买入时佣金万分之三，卖出时佣金万分之三加千分之一印花税, 每笔交易佣金最低扣5块钱
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5),
                   type='stock')

    # 持仓数量
    g.stocknum = 3

    # 待选择的股票列表
    g.stock_list = []  # 选股得到的股票代码

    ## 运行函数（reference_security为运行时间的参考标的；传入的标的只做种类区分，因此传入'000300.XSHG'或'510300.XSHG'是一样的）
    # 开盘前运行
    run_daily(before_market_open, time='before_open', reference_security='000300.XSHG')
    # 开盘时运行
    run_daily(market_open, time='open', reference_security='000300.XSHG')
    # 收盘后运行
    run_daily(after_market_close, time='after_close', reference_security='000300.XSHG')


## 开盘前运行函数
def before_market_open(context):
    # 输出运行时间
    log.info('函数运行时间(before_market_open)：' + str(context.current_dt.time()))

    # 给微信发送消息（添加模拟交易，并绑定微信生效）
    # send_message('美好的一天~')

    # 1. 获取龙虎榜数据列表 (获取当前日期前10日的数据)
    # 数据字典：https://www.joinquant.com/help/api/help#Stock:%E8%8E%B7%E5%8F%96%E9%BE%99%E8%99%8E%E6%A6%9C%E6%95%B0%E6%8D%AE
    df_bb = get_billboard_list(stock_list=None, end_date=context.current_dt, count=1)
    # 获取 net_value:净额(买入金额 - 卖出金额)， rank: 0 表示汇总， 1~5 对应买入金额或卖出金额排名第一到第五
    df_pos = df_bb[(df_bb['net_value'] > 0) & (df_bb['rank'] > 0)]
    # 按多列降序排序
    df_sort = df_pos.sort_values(["net_value", "total_value"], inplace=False, ascending=False)
    buylist = list(df_sort['code'])
    # 过滤停牌股票 (todo:所有股票均无法找到被当作停牌过滤)
    # buylist = filter_paused_stock(buylist)
    # log.info('buylist Num: ' + str(len(buylist)))

    # 2. 日线MA100看上涨趋势 (遍历第一步获取的股票)
    cnt = 0
    for item in buylist:
        if cnt >= g.stocknum:
            break
        # 获取股票近100个交易日的收盘价
        close_data = attribute_history(item, 100, '1d', ['close'])
        # 利用mean()函数计算出近100个交易日的平均收盘价
        MA100 = close_data['close'].mean()
        # 取得上一时间点股票的价格
        current_price = close_data['close'][-1]
        # 如果上一时间点价格高出100天平均价3%, 则加入备选股票
        if current_price > 1.03 * MA100:
            log.info('Select stock' + item)
            g.stock_list.append(item)
            cnt += 1


## 开盘时运行函数
def market_open(context):
    log.info('函数运行时间(market_open):' + str(context.current_dt.time()))
    ## 平均分配资金
    Num = g.stocknum - len(context.portfolio.positions)
    avg_cash = context.portfolio.cash / Num

    # 卖出策略
    ## 获取持仓列表
    sell_list = list(context.portfolio.positions.keys())
    # 如果有持仓，则卖出
    if len(sell_list) > 0:
        for security in sell_list:
            # 获取股票的收盘价
            close_data = get_bars(security, count=2, unit='1d', fields=['close'])
            # 取得过去5天的平均价格
            MA5 = close_data['close'].mean()
            # 取得上一时间点价格
            current_price = close_data['close'][-1]
            # 如果上一时间点价格低于五天平均价, 则空仓卖出
            if current_price < 0.95 * MA5 and context.portfolio.positions[security].closeable_amount > 0:
                # 卖出所有股票,使这只股票的最终持有量为0
                order_target(security, 0)
                # 记录这次卖出
                log.info("Selling %s" % (security))

    # 30分钟或者小时日线MA20突破时择时买入
    for security in g.stock_list:
        # 获取股票的收盘价
        close_data = get_bars(security, count=20, unit='1d', fields=['close'])
        # 取得过去20天的平均价格
        MA20 = close_data['close'].mean()
        # 取得上一时间点价格
        current_price = close_data['close'][-1]
        # 取得当前的现金
        cash = context.portfolio.available_cash

        # 如果上一时间点价格高出五天平均价1%, 则全仓买入
        if (current_price > 1.01 * MA20) and (cash > 0):
            # 记录这次买入
            log.info("价格高于均价 1%%, 买入 %s" % (security))
            # 用所有 cash 买入股票
            if cash < avg_cash:
                order_value(security, avg_cash)
            else:
                order_value(security, cash)
        # 如果上一时间点价格低于五天平均价, 则空仓卖出
        elif current_price < MA20 and context.portfolio.positions[security].closeable_amount > 0:
            # 记录这次卖出
            log.info("价格低于均价, 卖出 %s" % (security))
            # 卖出所有股票,使这只股票的最终持有量为0
            order_target(security, 0)


## 收盘后运行函数
def after_market_close(context):
    log.info(str('函数运行时间(after_market_close):' + str(context.current_dt.time())))
    # 得到当天所有成交记录
    trades = get_trades()
    for _trade in trades.values():
        log.info('成交记录：' + str(_trade))
    log.info('一天结束')
    log.info('##############################################################')


# 过滤停牌股票
def filter_paused_stock(stock_list):
    current_data = get_current_data()
    filtered_lst = []
    for stock in stock_list:
        if stock in current_data.keys() and not current_data[stock].paused:
            filtered_lst.append(stock)
    return filtered_lst


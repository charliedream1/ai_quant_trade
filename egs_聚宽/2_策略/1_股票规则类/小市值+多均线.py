import jqdata
from jqlib.technical_analysis import *


## 初始化函数，设定要操作的股票、基准等等
def initialize(context):
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # True为开启动态复权模式，使用真实价格交易
    set_option('use_real_price', True)
    # 设定成交量比例
    set_option('order_volume_ratio', 1)
    # 股票类交易手续费是：买入时佣金万分之三，卖出时佣金万分之三加千分之一印花税, 每笔交易佣金最低扣5块钱
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001, \
                             open_commission=0.0003, close_commission=0.0003, \
                             close_today_commission=0, min_commission=5), type='stock')
    # 持仓数量
    g.stocknum = 5
    # 交易日计时器
    g.days = 0
    # 调仓频率
    g.refresh_rate = 20
    # 运行函数
    run_daily(trade, 'every_bar')


def check_stocks(context):
    # 设定查询条件
    q = query(
        valuation.code,
        valuation.market_cap
    ).filter(
        valuation.market_cap.between(20, 30)
    ).order_by(
        valuation.market_cap.asc()
    )
    # 选出低市值的股票，构成buylist
    df = get_fundamentals(q)
    buylist = list(df['code'])
    # 过滤停牌股票
    buylist = filter_paused_stock(buylist)
    log.info('Total Selected Stocks Num: %d' % (len(buylist)))
    return buylist
    # return buylist[:g.stocknum]


def filter_paused_stock(stock_list):
    current_data = get_current_data()
    return [stock for stock in stock_list if not current_data[stock].paused]


def get_multi_mean_value(stock_code):
    # 设定均线
    n1 = 5
    n2 = 10
    n3 = 30
    # 获取股票的收盘价，其中df为False,表示返回值是一个字典类型，不是DataFrame类型
    close_data = attribute_history(stock_code, n3 + 2, '1d', ['close'], df=False)
    # 取得过去30个交易日的平均收盘价
    ma_n1 = close_data['close'][-n1:].mean()
    # 取得过10个交易日的平均收盘价
    ma_n2 = close_data['close'][-n2:].mean()
    # 取得过去5个交易日的平均收盘价
    ma_n3 = close_data['close'][-n3:].mean()
    # 取得上一时间点价格
    current_price = close_data['close'][-1]
    return close_data, ma_n1, ma_n2, ma_n3, current_price


def trade(context):
    ## 获取持仓列表
    sell_list = list(context.portfolio.positions.keys())
    # 如果有持仓，则卖出
    if len(sell_list) > 0:
        for stock in sell_list:
            close_data, ma_n1, ma_n2, ma_n3, current_price = get_multi_mean_value(stock)
            # 如果5日均线小于10日均线，10日均线小于30日均线, 上一时间点价格低于五天平均价2%，并且目前有头寸
            if ma_n1 < ma_n2 and ma_n2 < ma_n3 and current_price < 0.98 * ma_n1 and context.portfolio.positions[
                stock].closeable_amount > 0:
                # 全部卖出
                order_target_value(stock, 0)
                # 记录这次卖出
                log.info("Selling %s" % (stock))

    ## 分配资金
    if len(context.portfolio.positions) < g.stocknum:
        Num = g.stocknum - len(context.portfolio.positions)
        Cash = context.portfolio.cash / Num
    else:
        Cash = 0

    ## 选股
    stock_list = check_stocks(context)
    ## 买入股票
    for stock in stock_list:
        if len(context.portfolio.positions.keys()) >= g.stocknum:
            break
        close_data, ma_n1, ma_n2, ma_n3, current_price = get_multi_mean_value(stock)
        # 如果当前有余额，并且5日均线大于10日均线,10日均线大于30日均线,上一时间点价格高出五天平均价2%, 则全仓买入
        if ma_n1 > ma_n2 and ma_n2 > ma_n3 and current_price > 1.02 * ma_n1 and Cash > 0:
            # 用所有 cash 买入股票
            order_value(stock, Cash)
            # 记录这次买入
            log.info("Buying %s" % (stock))

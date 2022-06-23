def market_open(context):
    log.info('函数运行时间(market_open):'+str(context.current_dt.time()))
    security = g.security
    # 获取股票的收盘价
    close_data = attribute_history(security，5，'1d'，['close'])
    # 取得过去五天的平均价格
    MA5 = close_data['close'].mean()
    # 取得上一时间的点价格
    current_price = close_data['close'][-1]
    # 取得当前的现金
    cash = context.portfolio.available_cash
    # 如果上一时间点价格高出五天平均价1%，则全仓买入
    if current_price > 1.01*MA5:
        # 记录这次买入
        log.info("价格高于均价 1%%，买入 %s" % (security))
        # 用所有 cash 买入股票
        order_value(security，cash)
    # 如果上一时间点价格低于五天平均价，则全部卖出
    elif current_price < MA5 and context.portfolio.positions[security].closeable_amount > 0:
        # 记录这次卖出
        log.info("价格低于均价，卖出 %s" % (security))
        # 卖出所有股票,使这只股票的最终持有量为0
        order_target(security，0)

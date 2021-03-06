def initialize(context):
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 开启动态复权模式(真实价格)
    set_option('use_real_price'，True)
    # 输出内容到日志 log.info()
    log.info('初始函数开始运行且全局只运行一次')
   ### 股票相关设定 ###
    # 股票类每笔交易时的手续费是：买入时佣金万分之三，卖出时佣金万分之三加千分之一印花税，每笔交易佣金最低扣5块钱
    set_order_cost(OrderCost(close_tax=0.001，open_commission=0.0003，close_commission=0.0003，min_commission=5)，type='stock')
    ## 运行函数（reference_security为运行时间的参考标的；传入的标的只做种类区分，因此传入'000300.XSHG'或'510300.XSHG'是一样的）
      g.flag = 0 # 全局对象
      # 开盘前运行
    run_daily(before_market_open，time='before_open'，reference_security='000300.XSHG')
      # 开盘时运行
    run_daily(market_open，time='open'，reference_security='000300.XSHG')
      # 收盘后运行
    run_daily(after_market_close，time='after_close'，reference_security='000300.XSHG')

# 设置佣金印花税函数
# 股票类每笔交易时的手续费是：买入时佣金万分之三，卖出时佣金万分之三加千分之一印花税, 每笔交易佣金最低扣5块钱
set_order_cost(OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, close_commission=0.0003, close_today_commission=0, min_commission=5), type='stock')
# 对 IF/IH/IC 三个金融期货品种有效：买入时佣金万分之三，卖出时佣金万分之三加千分之一印花税, 每笔交易佣金最低扣5块钱。但需要注意卖出当日仓单时，卖出佣金为零。
set_order_cost(OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, close_commission=0.0003, close_today_commission=0, min_commission=5), type='index_futures')

# 设置滑点函数set_slippage
# 如果没有调用，回测或模拟盘时默认PriceRelatedSlippage(0.00246)，模拟下单时和真实价格的差异
# 成交价格 = 平均价格 +- 价差的一半（比如0.02元，交易时加减0.01元）
# 设为固定值
set_slippage(FixedSlippage(0.02))
# 设为百分比
set_slippage(PriceRelatedSlippage(0.002))

# 设置成交比例 order_volume_ratio
# 成交量不超过：每日成交量 * value (比例)
set_option('order_volume_ratio', value)

def handle_data(context，data):
    #获得当前回测相关时间
    year = context.current_dt.year
    month = context.current_dt.month
    day = context.current_dt.day
    hour = context.current_dt.hour
    minute = context.current_dt.minute
    second = context.current_dt.second
    #得到"年-月-日"格式
    date = context.current_dt.strftime("%Y-%m-%d")
    #得到周几
    weekday = context.current_dt.isoweekday()
    # 获取账户的持仓价值
    positions_value = context.portfolio.positions_value
    # 获取仓位subportfolios[0]的可用资金
    available_cash = context.subportfolios[0].available_cash
    # 获取subportfolios[0]中多头仓位的security的持仓成本
    hold_cost = context.subportfolios[0].long_positions[security].hold_cost

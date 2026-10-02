def handle_data(context,data):
    #获得当前回测相关时间
    #得到"年-月-日"格式
    context.current_dt.strftime("%Y-%m-%d")
    #得到周几
    context.current_dt.isoweekday()
    # 获取账户的持仓价值
    # 获取仓位subportfolios[0]的可用资金
    context.subportfolios[0].available_cash
    # 获取subportfolios[0]中多头仓位的security的持仓成本
    context.subportfolios[0].long_positions[security].hold_cost

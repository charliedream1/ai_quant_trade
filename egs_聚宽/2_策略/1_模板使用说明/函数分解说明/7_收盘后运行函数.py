def after_market_close(context):
    log.info(str('函数运行时间(after_market_close):'+str(context.current_dt.time())))
    #得到当天所有成交记录
    trades = get_trades()
    for _trade in trades.values():
        log.info('成交记录：'+str(_trade))

    # 撤销未完成的订单
    orders = get_open_orders()
    for _order in orders.values():
        cancel_order(_order)

    log.info('一天结束')
    log.info('######################################')



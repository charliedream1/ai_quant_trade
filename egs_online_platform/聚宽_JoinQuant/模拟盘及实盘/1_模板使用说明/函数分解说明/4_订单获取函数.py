#自定义每个交易日结束运行函数
def after_trading_end(context):
    #得到当天所有订单
    orders = get_orders()
    for _order in orders.values():
        log.info(_order.order_id)
    # 根据订单id查询订单
    get_orders(order_id='1517627499')
    # 查询所有标的为 000002.XSHE 的订单
    get_orders(security='000002.XSHE')
    # 查询订单状态为 OrderStatus.held 的所有订单
    get_orders(status=OrderStatus.held)
    # 查询标的为 000002.XSHE 且状态为 OrderStatus.held 的所有订单
    get_orders(security='000002.XSHE'，status=OrderStatus.held)


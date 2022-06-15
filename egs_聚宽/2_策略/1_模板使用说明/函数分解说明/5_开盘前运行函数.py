def before_market_open(context):
    # 输出运行时间
    log.info('函数运行时间(before_market_open)：'+str(context.current_dt.time()))
    # 给微信发送消息（添加模拟交易，并绑定微信生效）
    send_message('美好的一天~')
    # 要操作的股票：平安银行（g.为全局变量）
    g.security = '000001.XSHE'

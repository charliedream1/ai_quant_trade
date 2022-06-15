def weekly(context):
    print('weekly %s %s' % (context.current_dt，context.current_dt.isoweekday()))
def monthly(context):
    print('monthly %s %s' % (context.current_dt，context.current_dt.month))
def daily(context):
    print('daily %s' % context.current_dt)
def initialize(context):
    # 指定每月第一个交易日，在开盘后十分钟执行，即9:40
    run_monthly(monthly，1，'open+10m')
    # 指定每周倒数第一个交易日，在开盘前执行，即9:00
    run_weekly(weekly，-1，'before_open')
    # 指定每天收盘前10分钟运行，即14：50
    run_weekly(daily，'close - 10m')
    # 指定每天收盘后执行，即15：30
    run_daily(daily，'after_close')
    # 指定在每天的10:00运行
    run_daily(daily，'10:00')
    # 指定在每天的01:00运行
    run_daily(daily，'01:00')
    # 参照股指期货的时间每分钟运行一次，必须选择分钟回测，否则每天执行
    run_daily(daily，'every_bar'，reference_security='IF2003.CCFX')


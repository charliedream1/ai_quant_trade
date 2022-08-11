2022-06-20 09:30:00 - ERROR - Traceback (most recent call last):
  File "/tmp/jqcore/jqboson/jqboson/core/loop/loop.py", line 282, in _handle_message
    message.callback(**message.callback_data)
  File "/tmp/jqcore/jqboson/jqboson/core/dispatcher.py", line 110, in callback
    self._event_bus.emit(evt)
  File "/tmp/jqcore/jqboson/jqboson/core/bus.py", line 47, in emit
    ret.append(call(event))
  File "/tmp/jqcore/jqboson/jqboson/core/strategy.py", line 376, in _wrapper
    return cb(self._context.strategy_environment.strategy_context, **cb_kwargs)
  File "/tmp/strategy/user_code.py", line 78, in market_open
    avg_cash = context.portfolio.cash/Num
ZeroDivisionError: float division by zero
# 1. 资源

- Github (11.5k stars): https://github.com/hummingbot/hummingbot
- 文档：https://hummingbot.org/

**评价**
Hummingbot 相对其它的框架，会复杂一点，特别是开发一个新策略时。它也在不断迭代，基本每一两个月就有一个新版本发布。

# 2. 介绍

**特点**

- Hummingbot 是一款高频量化机器人，里面有大量 C++ 代码，还有基本都是 asyncio 异步操作。
- Hummingbot 是一个 Python 加密货币机器人，它提供了一些常见的高频策略，如高频做市、跨市场套利和资金费率套利等

事件机制的话，Hummingbot 中的 on_tick 不是由成交 tick 触发的，而是定时的 clock tick，如配置 1 秒、1分钟定时触发。更细粒度的时间控制，最小可设置到 0.1s。这个和 vnpy 不同，我好像记得之前有人吐槽 vn.py 不支持定时触发的能力，因此更喜欢 backtrader。

Hummingbot 的数据源基本都是 ws 实时监听得到，频繁的的获取数据，如价格、订单簿（OrderBook），不会触发交易所的频率限制。当然，下单是例外，这是主动触发的操作。

**交互模式**

- Tui 终端
- Web 端的 Dashboard：由Streamlit框架开发

# 3. 安装

**下载代码**

可以源码或Docker安装

```bash
git clone https://github.com/hummingbot/hummingbot.git
```

下载的时候常遇到网络 Timeout，可通过 --depth=1 只下载最新的文件，提升下载速度。

```bash
git clone --depth=1 https://github.com/hummingbot/hummingbot.git
```

还一个方法就是使用git镜像

```bash
git clone  https://gitclone.com/github.com/hummingbot/hummingbot.git
```

**启动应用**

进入 hummingbot 目录通过 docker 启动服务：

```bash
docker compose up -d
```

之后，用 docker attach 命令就能进到应用入口：

```bash
docker attach hummingbot
```

第一次启动，会要求你设置登陆密码，以后的每次进入 Hummingbot 终端都离不开这个密码。

补充一点，exit 退出交互模式时，整个服务都会停止，要重新 docker-compose up -d 启动，docker attach 重新登陆。如果想退出但保持运行状态，可通过 Ctrl+p + Ctrl+q 快捷键组合（保持 Ctrl 按住状态）即可退出。

**查看帮助信息**

成功登陆后，你将会进入到一个 Hummingbot 的终端，如果想查看它支持什么命令，输入 help 查看它支持的命令，这些命令提供了在终端管理机器人的能力。

常用的几个命令：
- connect，用于配置交易所连接器；
- balance，查询账户余额；
- create，创建机器人配置；
- start，运行机器人；
- stop，停止当前的机器人；
- status，监控机器人运行状态；
- history，查看机器人的历史表现；
- config，配置全局参数；

# 4. 实际操作

大概的实现流程，主要分为如下的四个步骤。

1. 连接交易所，介绍如何配置和连接交易所，查看账号的信息，如当前的账户余额；(用`connect`命令)
2. 配置启动策略，介绍配置并成功一个 Hummingbot 内置的简单做市的策略机器人；(用`balance`命令)
3. 监控运行状态，介绍如何监控运行中机器人的状态，如订单、成交、盈亏和行情等；

通过`create --script-config`选择内置策略模板

常见的几种策略:

- 基础做市（simple_pmm）：通过持续挂单捕捉买卖价差，适用于主流交易对的流动性维护。
- 跨交易所做市（simple_xemm/v2_xemm）：在一家交易所挂单，另一家对冲风险，利用交易所间价差获利。
- 时间加权（v2_twap_multiple_pairs）：将大额订单拆分为多笔小额订单，按时间均匀执行以减少市场冲击，支持多交易对。
- 成交量加权（simple_vwap）：根据市场实时成交量动态调整订单规模，降低交易滑点。
- 方向性 RSI（v2_directional_rsi）：基于 RSI 指标判断超买超卖信号，触发趋势跟踪交易。
- 资金费率套利（v2_funding_rate_arb）：通过永续合约与现货间的资金费率差异进行对冲套利。
- 控制器增强（v2_with_controllers）：这个比较复杂，可理解为总控管理多个子策略，总控负责风险控制、组合管理等。

通过 start 启动这个策略机器人，格式是 start --script 策略脚本 --conf 策略配置文件

执行 status 命令，查看机器人当前的运行状态。如果加上 --live 选项，可实时监控机器人。

如果想查看策略的表现，执行 history 查看

# 参考

[1] 通过 Hummingbot 运行一个做市机器人, https://mp.weixin.qq.com/s/i4AjKI5dAmOpkC-A9atlHA
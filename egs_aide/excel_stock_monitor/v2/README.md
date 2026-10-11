# 上班“摸鱼炒股”神器 V2--超隐蔽“划水致富”进化版

## 🤡 说些心里话，引发点共鸣

作为上班族的你，又要上班，又要炒股，是不是好心累啊~！

```
                 摸鱼词

    为什么会心累啊~~~
    还不就是像做贼一样，看股票，怕被发现吗！！！

    献上我的膝盖：摸鱼划水神器
    让领导以为你是一名从不摸鱼，好好工作的员工！！！

    哈哈哈，记得给我点赞哦，我会更有动力继续开发
    我会让你摸得更加如鱼得水，丝滑丝滑

    V2 来了，这次真的丝滑到飞起！！！
```

![](../v1/.README_images/摸鱼.png)

![](../v1/.README_images/划水.png)

上班时，你是否担心一件事，你买的股票怎么样了啊🤨？

一不小心错过了时机，痛心疾首，急得直跺脚。

![](../v1/.README_images/2_工作与炒股.png)

可是，用手机看盘实在太小啊。但用电脑看盘，被领导发现，怎么办，
悄悄看盘时，吓得我的小心扑通扑通的跳啊

![](../v1/.README_images/1_有点慌.png)

哈哈，现在好了，V2 终极解决方案来了，让我来再放大招吧。

```
       拿出神器：摸鱼炒股神器 V2
```

![](../v1/.README_images/叮当猫.png)

```
    V2 的方案：
        依然是 Excel 作为交互界面，在 Excel 里显示股票信息
        但这次，它变得更聪明、更主动、更懂你了！！！
        哈哈哈
```

展示下效果

![](../v1/.README_images/Excel股票信息.png)

## 🌟 V2 有什么不一样

V1 只是一个能刷新数据的“小玩具”，V2 把它做成了一个**真正能用的盯盘系统**：

```
1. 大盘总览        指数 + 行业板块 + 概念板块 + 涨停板，一屏看全
2. 详细行情        自选股 + 龙虎榜 + 盘口异动
3. 财经新闻        财联社电报 + 市场快讯
4. 个性定制看盘    自选股 + 自定义显示列 + 预警监控 + K线图
5. 资金情绪        北向资金 + 微博舆情 + 新闻情绪 + 股吧热门（多数据源）
6. 股票池          内置全 A 股列表 + 模糊搜索 + 下拉框选股，不用再去找代码
7. Excel 配置      在 Excel 里改配置，不用动代码，不用重启
```

最让人心动的新能力：

```
🔥 预警监控      设好涨跌幅/价格上下限，到了自动整行变红 + 弹窗提醒
🔥 K线图         在 Excel 里点个按钮就能画 K 线，带均线，不用切软件
🔥 Excel 配置    自选股、指数、刷新间隔，全在 Excel 里改，热生效
🔥 多源 fallback 主源 qstock 挂了，自动切换 akshare/东财/腾讯/网易/efinance
🔥 资金情绪      新增 Sheet，北向资金+微博舆情+新闻情绪+股吧热门一屏看全
🔥 股票池选股    内置全 A 股，输入代码/名称/拼音搜索，下拉框直接选，不用再查代码
```

从此，你乐了，机构也乐了，大家都乐了，独乐乐不如众乐乐！！！

![](../v1/.README_images/机构和韭菜.png)

好了，介绍到这里，下面开始详细介绍如何使用以及技术细节吧

## 🚀 如何使用

1. 安装依赖：

    qstock 依赖的库有些大，请使用国内镜像，会更快

    ```
       pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/ --trusted-host pypi.tuna.tsinghua.edu.cn
    ```

    主要依赖：`xlwings`（操作 Excel）、`qstock`（主行情数据源）、`akshare`/`efinance`/`requests`（备选数据源）、`mplfinance`（K线图）、`pyyaml`（配置）、`openpyxl`（生成模板）

2. 生成 Excel 模板（首次运行）：

    ```
       python main.py --generate-template
    ```

    程序会自动生成 `看盘模板.xlsx`，里面已经带好了 7 个 Sheet 和示例自选股，开箱即用。
    不再像 V1 那样需要额外准备 `全部A股信息.xlsx` 了！

3. 在 Excel 模板里填上你心仪的股票

    在“详细行情”和“个性定制看盘” Sheet 的代码列写上你想关注的股票

    **不知道代码？** 打开"股票池"Sheet，在 B1 输入关键字
    （代码片段/名称/拼音首字母，如 `600` / `平安` / `pa`），点"搜索"按钮过滤，
    从结果复制到看盘 Sheet。或者直接在"个性定制看盘"代码列点下拉框选择。

    ![](../v1/.README_images/Excel代码名称列.png)

    在“个性定制看盘” Sheet 里，还能给每只股票设置预警条件（涨跌幅上下限、价格上下限），
    留空表示不监控该指标。

4. 启动程序

    ```
       python main.py
    ```

    ![](../v1/.README_images/基金.png)

5. 想改配置？不用关程序！

    直接在 Excel 的“配置” Sheet 里改刷新间隔、自选股、指数等，
    程序会每隔 N 次刷新自动重载，热生效。

## ⛳ 原理介绍

V2 相比 V1 做了彻底的架构重构，把一个“大文件”拆成了一个**模块化的盯盘系统**。

### 整体架构

```
main.py                         主入口（加载配置 → 初始化 → 刷新循环）
  │
  ├── config.yaml               YAML 配置（默认值）
  ├── 看盘模板.xlsx              Excel 交互界面（含“配置”Sheet 热修改）
  │
  └── src/excel_monitor/
        ├── config_loader.py        配置加载（YAML → AppConfig）
        ├── core/
        │     ├── excel_manager.py      Excel 操作封装（读写/高亮/图片/按钮）
        │     ├── data_provider.py       多源数据封装（qstock 主源 + fallback）
        │     ├── backup_sources.py      备选数据源适配器（akshare/东财/腾讯/网易/efinance）
        │     ├── stock_pool.py          股票池管理（拉取/缓存/模糊搜索）
        │     ├── config_sheet_reader.py 从 Excel“配置”Sheet 读取配置
        │     └── alert_checker.py       预警检查器（纯逻辑，可测试）
        ├── sheets/
        │     ├── base.py               Sheet Handler 抽象基类
        │     ├── market_overview.py     大盘 Sheet
        │     ├── detailed_quotes.py    详细行情 Sheet
        │     ├── news_sheet.py         新闻 Sheet
        │     ├── custom_watch.py       个性定制看盘 Sheet（预警 + K线）
        │     ├── sentiment_sheet.py    资金情绪 Sheet（北向/舆情/股吧）
        │     └── stock_pool_sheet.py   股票池 Sheet（搜索 + 下拉框）
        └── utils/
              ├── kline_chart.py        K 线图绘制（mplfinance）
              └── template_generator.py Excel 模板自动生成
```

### 核心设计：Sheet Handler 模式

V2 把每个 Sheet 抽象成一个 Handler，继承自 `BaseSheet`，只需实现两个方法：

- `init()`：初始化加载（仅执行一次，如读取自选股代码）
- `refresh()`：刷新数据（每次循环调用）

```python
class BaseSheet(ABC):
    def setup(self):
        self.sheet = self.excel_mgr.get_sheet_by_name(self.name)

    @abstractmethod
    def init(self): ...

    @abstractmethod
    def refresh(self): ...
```

主循环非常简洁，而且**每个 Sheet 的刷新互相隔离**，一个挂了不会拖垮其他 Sheet：

```python
# main.py 刷新循环
while True:
    for handler in handlers:
        try:
            handler.refresh()
        except Exception as e:
            logger.error(f"Sheet '{handler.name}' 刷新失败: {e}")
    time.sleep(cfg.refresh_interval)
```

### 难点 1：Excel 在线刷新

和 V1 一样，通过 `xlwings` 实现在线刷新 Excel。V2 把这些操作封装进了 `ExcelManager`，
统一管理读写、清除、高亮、插入图片、添加按钮：

```python
class ExcelManager:
    def write_df(self, sheet, df, start_row=1, start_col=1):
        sheet.range((start_row, start_col),
                    (start_row + n_rows, start_col + n_cols - 1)).value = df

    def highlight_row(self, sheet, row, start_col=1, end_col=20,
                      color=(255, 200, 200)):
        sheet.range((row, start_col), (row, end_col)).color = color
```

如果你的 Excel 处在打开编辑状态，程序运行时，会自动打开另一个只读的副本。

### 难点 2：预警监控

这是 V2 最实用的新功能。用户在“个性定制看盘”Sheet 的预警列里填阈值，
程序每次刷新都会检查，触发后**整行变红 + 弹窗提醒**。

预警检查器是纯逻辑、无副作用的，方便单元测试：

```python
@dataclass
class AlertCondition:
    code: str
    change_pct_min: Optional[float] = None   # 涨跌幅下限
    change_pct_max: Optional[float] = None   # 涨跌幅上限
    price_min: Optional[float] = None        # 价格下限
    price_max: Optional[float] = None        # 价格上限

class AlertChecker:
    @staticmethod
    def check(condition, latest_price, change_pct) -> List[AlertResult]:
        # 涨跌幅超上限 / 低于下限 / 价格超上限 / 低于下限
        ...
```

### 难点 3：在 Excel 里画 K 线图

V2 用 `mplfinance` 绘制 K 线图，保存为图片后插入 Excel。
难点在于如何让用户“点一下按钮”就画图，这里用了**双模式触发**：

1. **VBA 宏模式**（首选）：程序启动时自动往 Excel 注入一段 VBA 宏，按钮点击即触发
2. **轮询模式**（降级）：若 VBA 注入失败（权限/格式限制），用户在 D21 单元格输入 `DRAW`，
   程序下次刷新时检测到信号自动画图

```python
vba_code = (
    'Sub DrawKLineMacro()\n'
    '    Range("D21").Value = "DRAW"\n'
    'End Sub'
)
```

画图流程：读取行号 → 取股票代码 → 拉 K 线数据 → mplfinance 绘图 → 插入图片。

### 难点 4：配置热重载

V1 的配置写死在代码里，改一下要重启。V2 支持**三层配置**：

1. `config.yaml`：默认配置
2. Excel“配置”Sheet：运行时可改，覆盖 YAML
3. 自选股/预警条件：直接在对应 Sheet 改，每隔 N 次刷新自动重载

```python
# 每隔 N 次刷新，重新从 Excel 读取股票代码和预警条件
if reload_interval > 0 and self._refresh_count % reload_interval == 0:
    self._reload_from_excel()
```

### 数据源：多源 fallback 机制

V2 借鉴 `egs_data/` 目录下多个数据源的访问方式，构建了**主源 + 备选源**的 fallback 链，
单个数据源失败时自动切换备用源，保证盯盘不中断。

- 主源：`qstock`（基于东方财富、同花顺免费接口）
- 备选源（参考 `egs_data/{akshare, eastmoney, tencent, netease, efinance}`）：
  - `akshare`：A 股实时行情、北向资金、微博舆情、新闻情绪、财联社/财新/新闻联播
  - `eastmoney`：个股资金流向、股吧热门帖子、个股新闻、K 线
  - `tencent`：实时行情、K 线（腾讯财经接口）
  - `netease`：历史 K 线（网易财经接口）
  - `efinance`：实时行情、K 线

- 东方财富免费接口可获取的数据内容有限，想获取更多信息需付费量化接口
  - 数据接口： https://data.eastmoney.com/bkzj/hy.html
- 同花顺免费接口连接不稳定，想获取更多信息需付费量化接口
  - 数据接口：http://data.10jqka.com.cn/

V2 把所有数据获取封装进 `DataProvider`，主源失败时按 fallback 链依次尝试备选源：

```python
class DataProvider:
    def get_stock_realtime(self, code_list):
        # fallback 链：qstock → akshare → tencent → eastmoney → efinance
        return self._try_with_fallback(
            primary_func=self._qstock_stock_realtime,
            fallback_chain=[
                ("akshare", self.backup.akshare_stock_realtime),
                ("tencent", self.backup.tencent_stock_realtime),
                ("eastmoney", self.backup.eastmoney_stock_realtime),
                ("efinance", self.backup.efinance_stock_realtime),
            ],
            args=(code_list,),
            name="个股行情",
        )
```

各数据源字段不统一的问题，由 `BackupSources` 内部 `rename` 映射对齐到 qstock 风格
（代码/名称/最新/涨幅…），调用方无需感知差异。备选源可通过 `config.yaml` 的
`enabled_backup_sources` 按需开关：

```yaml
# 移除某个源名即关闭该源的 fallback 能力
enabled_backup_sources: ["akshare", "eastmoney", "tencent", "netease", "efinance"]
```

### 难点 5：资金情绪 Sheet（多数据源聚合）

新增的“资金情绪”Sheet 聚合了 4 类反映市场情绪的数据，每类来自不同数据源，
**互相独立、单个失败不影响其他块写入**：

| 数据块 | 数据源 | 说明 |
|--------|--------|------|
| 北向资金 | akshare | 每日净流入、余额 |
| 微博舆情 | akshare | 散户情绪指数 |
| 新闻情绪 | akshare | 媒体情绪指数 |
| 股吧热门 | eastmoney | 散户热度帖子 |

```python
class SentimentSheet(BaseSheet):
    def refresh(self):
        df_north = self.data.get_north_money()       # akshare
        df_weibo = self.data.get_weibo_sentiment()   # akshare
        df_news = self.data.get_news_sentiment()     # akshare
        df_guba = self.data.get_guba_hot_posts(...)  # eastmoney
        # 每块独立写入，空数据跳过
```

### 难点 6：股票池选股（不用再查代码）

痛点：用户要盯某只股票，得先去财经网站查代码再填进 Excel，体验差。
方案：内置全 A 股列表 + 模糊搜索 + 下拉框，三选一都能用。

```
股票池 Sheet 布局：
  A1: 搜索关键字   B1: [输入框]   C1: [搜索按钮]   D1: [显示全部按钮]
  A2: 共 5234 只 | 当前显示 200 只
  A4: 代码  B4: 名称  C4: 市场
  A5: 000001  B5: 平安银行  C5: 深圳
  ...
```

**数据来源**：akshare `stock_info_a_code_name()`（轻量接口，仅代码+名称），
efinance 作为备选源。拉取后缓存为本地 JSON，下次启动秒加载，
缓存超过 N 天自动刷新；拉取失败时用过期缓存保底。

**模糊搜索**：支持三种匹配方式（大小写不敏感）：
- 代码前缀：`600` → 浦发银行、贵州茅台
- 名称包含：`平安` → 平安银行、中国平安
- 拼音首字母：`pa` → 平安银行、中国平安

```python
class StockPool:
    def search(self, keyword, limit=100):
        mask_code = self.df["代码"].str.startswith(kw)
        mask_name = self.df["名称"].str.contains(kw)
        mask_pinyin = self.df["拼音"].str.startswith(kw)
        return self.df[mask_code | mask_name | mask_pinyin].head(limit)
```

**下拉框**：程序启动后自动为"个性定制看盘"代码列设置 Excel 数据验证，
引用"股票池"Sheet 代码列，用户可直接点下拉箭头选择。下拉框设置失败不影响手动输入。

## 📊 V1 vs V2 更新对比

| 对比项 | V1 | V2 |
|--------|----|----|
| 代码结构 | 单文件 `main.py` | 模块化包 `excel_monitor` |
| 配置方式 | 写死在代码里 | YAML + Excel 配置 Sheet，热重载 |
| Excel 模板 | 需手动准备 + 额外 `全部A股信息.xlsx` | 一条命令自动生成，开箱即用 |
| 自选股修改 | 改代码重启 | Excel 里直接改，热生效 |
| 预警监控 | 无 | 涨跌幅/价格上下限，高亮 + 弹窗 |
| K 线图 | 无 | mplfinance 蜡烛图/OHLC，带均线，按钮触发 |
| Sheet 刷新 | 一个挂全挂 | 每个 Sheet 独立隔离，互不影响 |
| 异常处理 | 基本无 | 统一封装，日志清晰 |
| 数据源 | 单一 qstock | qstock 主源 + 5 个备选源 fallback |
| 资金情绪 | 无 | 北向资金/微博舆情/新闻情绪/股吧热门 |
| 选股方式 | 手动查代码 | 股票池模糊搜索 + 下拉框直接选 |
| 盘口异动 | 未启用 | 已启用（详细行情 Sheet） |
| 单元测试 | 无 | pytest 覆盖核心逻辑（156 项） |
| 刷新稳定性 | 偶发崩溃 | 容错强，可长时间运行 |

## 🧪 测试

V2 配套了单元测试，覆盖配置加载、预警检查、数据提供者、多源 fallback、Sheet Handler 等核心逻辑：

```
    pytest
```

测试文件说明：

```
tests/
├── test_config.py              配置加载测试
├── test_config_sheet_reader.py Excel 配置 Sheet 读取测试
├── test_data_provider.py       多源 fallback 机制 + 数据方法测试
├── test_backup_sources.py      备选数据源适配器测试（akshare/东财/腾讯/网易/efinance）
├── test_stock_pool.py          股票池拉取/缓存/模糊搜索测试
├── test_stock_pool_sheet.py    股票池 Sheet 刷新/搜索/下拉框测试
├── test_sheets.py              Sheet Handler 逻辑测试
├── test_sentiment_sheet.py     资金情绪 Sheet 刷新流程测试
├── test_empty_data_preserve.py 空数据保持原数据不变测试
└── test_e2e.py                 端到端测试（模板生成 → 刷新流程 → 预警 → K线）
```

## 🎏 最后

本文虽然提出了上班“摸鱼炒股”方案，但还请以上班为主。不过要能把副业做成主业，也是一件很了不起的事情！

- V2 已是一个**模块化、可配置、带预警、能画 K 线**的完整盯盘系统，开箱即用
- 后续会加入“人工智能”技术，给出辅助的预测结果和操盘建议，敬请期待！！！

```
    摸鱼一时爽，一直摸鱼一直爽
    但请记得：股市有风险，摸鱼需谨慎 😄
```

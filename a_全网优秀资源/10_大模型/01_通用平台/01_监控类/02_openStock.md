- Github (19.5k stars): https://github.com/Open-Dev-Society/OpenStock
- 官网： openstock-ods.vercel.app
- 协议：AGPL-3.0 license

**它的技术栈很现代，但不炫技。**

Next.js 15 App Router、React 19、TypeScript、Tailwind CSS v4。UI组件用的是shadcn/ui和Radix UI的原语，默认深色主题，适合长时间盯盘。整个项目结构清晰，对想学现代前端开发的人来说，是一个很好的参考实现。

**它的功能覆盖了个人投资者日常需要的核心场景。**

你可以在30多个交易所的股票里搜索，查看实时或延迟行情。免费层数据按提供商规则可能有延迟，但这不是OpenStock的问题，是数据源本身的规则。

你可以维护自己的自选股列表。登录之后，你关注的股票会保存在你的账户里，下次打开直接看。

它嵌入了TradingView的小部件来提供K线图、热力图和行情报价。TradingView的图表体验是行业标杆，直接嵌入比自己从头写一个图表引擎要务实得多。

**它还做了两件有意思的事，用AI把“被动看盘”变成“主动提醒”。**

一是AI生成的欢迎邮件。你注册之后，它会根据你的自选股生成一封个性化的欢迎邮件。

二是每日新闻摘要。通过Inngest工作流，它每天会推送一封基于你自选股的新闻摘要。你不用自己去翻新闻，它帮你把跟你相关的信息挑出来。

**市场数据来源是透明的。**

股票搜索、公司简介、市场新闻走的是Finnhub的API。K线图和报价走TradingView小部件。情绪分析可选Adanos，覆盖Reddit、X.com、新闻和Polymarket——如果你需要判断市场情绪，这一层可以加上。


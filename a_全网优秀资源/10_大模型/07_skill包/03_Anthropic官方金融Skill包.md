仓库地址(23.9k stars)：github.com/anthropics/financial-services

整个仓库分两层，11个端到端的Agent，和7个垂直行业的底层Skill包。

Agent那层，每一个都是自包含的，装上就能跑一整条流水线，不用先装一堆依赖。

Pitch Agent，输入可比公司、先例交易、LBO假设，直接输出一份带品牌格式的pitch deck。以前MD让你周五交pitch，你周三就得开始拉comps、跑DCF、做deck，这个流程现在被压成了一条命令。

Model Builder，DCF、LBO、三表模型直接在Excel里跑。不是导出一个表格，是Claude真的在你的xlsx文件里写公式、改单元格。

GL Reconciler，找总账break、追根溯源、走签字流程。

Earnings Reviewer，财报电话会加公告，自动更新模型，起草研报。

官方把边界划得很清楚，这些Agent是替分析师起草工作底稿的，不做投资决策，不执行交易，每一份产出都摆在那儿等人类签字。

这个定位很聪明，金融行业最敏感的是责任，能跑活但不背锅，才是To B落地最现实的姿势。

底层Skill包才是真正值得收藏的部分。

核心包financial-analysis带着所有共用建模Skill，/comps可比公司分析、/dcf估值加WACC加敏感性分析、/lbo杠杆收购模型、/3-statement-model三表模型填充，都有。

还有一个audit-xls，把分析师最痛的「老板甩过来一个十年没人维护的Excel，让你找里面到底哪个数错了」直接做成了Skill，公式追溯、硬编码检测、平衡校验一键跑。

我看到这个愣了一下，因为这个场景太真实了。

投行垂直包里有/cim信息备忘录、/buyer-list潜在买家清单、/merger-model增发摊薄分析。股票研究包里有/earnings财报点评、/initiate首次覆盖报告、/morning-note晨会纪要。私募股权包里有/ic-memo投委会备忘录、/value-creation投后100天计划加EBITDA bridge。

还有11个MCP数据连接器，Daloopa、FactSet、PitchBook、S&P Global、Morningstar、路孚特这些都在里面。
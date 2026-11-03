# Workspace GIF recordings / 工作台GIF来源

## README caption languages / README字幕语言

2026-11-02: Chinese README uses the Chinese UI and captions in `zh/`; English and Japanese READMEs share the English UI and captions in `en/`. The three English workspace GIFs were recorded anew using the application's native English setting. Visible text, input display values and placeholders in all twelve captured English states were checked for remaining Chinese. Two AI states focus on the actual composer and retrieved source table. No page text or results were replaced during capture.

2026-11-02：中文README引用`zh/`中文界面与字幕，英文和日文README共用`en/`英文界面与字幕。三段工作台英文版使用系统原生英文模式重新操作录制，12个状态的可见文字、控件显示值和占位提示均核查无中文；其中输入区和引用表两帧采用真实局部截图，未替换页面文字或结果。

| Demo | 中文字幕 / Chinese captions | English captions（English + 日本語 README） |
| --- | --- | --- |
| Navigation / 导航 | [zh/navigation.gif](zh/navigation.gif) | [en/navigation.gif](en/navigation.gif) |
| Strategy / 策略回测 | [zh/strategy-backtest.gif](zh/strategy-backtest.gif) | [en/strategy-backtest.gif](en/strategy-backtest.gif) |
| AI and knowledge / AI与知识 | [zh/ai-knowledge.gif](zh/ai-knowledge.gif) | [en/ai-knowledge.gif](en/ai-knowledge.gif) |
| Legacy monitor / 旧版看盘 | [zh/legacy-monitor.gif](zh/legacy-monitor.gif) | [en/legacy-monitor.gif](en/legacy-monitor.gif) |

Chinese workspace GIFs retain their original 5/6/6 states. The newly recorded English workspace GIFs contain 3/5/4 states. The old monitor's Chinese version preserves the original demo; its English version is a localized feature illustration with a redrawn English layout and the original chart graphic, explicitly marked as an illustration. It is not an English Excel runtime recording. Both retain 130 frames and 15 seconds. Original files remain available. The Chinese MkDocs guide mirrors the three `zh/` workspace GIFs into `docs/usage/assets/demos/`.

中文工作台保留原5/6/6状态，重新录制的英文版为3/5/4状态。旧版看盘的中文版本保留原演示；英文版本采用全英文功能示意排版及原图表图形，画面明确标记illustration，不称为英文Excel实机录制。两版旧演示均保留130帧/15秒。原文件保留；中文MkDocs三段副本使用`zh/`，摘要见manifest。

## Original recording / 原录制

Recorded on 2026-10-31 from the current `src` application with Playwright/Chromium at 1440×1000. Frames are real browser screenshots resized to 1280×889, with an external caption band. The application pixels and displayed results were not replaced. GIF encoding uses the project's Pillow13 image environment.

2026-10-31使用Playwright/Chromium操作当前src应用录制。实际页面截图下方增加步骤字幕及MOCK标记，没有替换页面内容或结果。动画为关键操作状态序列，循环播放；不是实时速度录像，字幕停留时长不能作为执行时延。

| File | Duration | Recorded actions |
| --- | --- | --- |
| [navigation.gif](navigation.gif) | 10.2s / 5 frames | Account overview, market refresh, ETF view, next curriculum chapter, collapse navigation. 总览、刷新行情、ETF、下一章、收起导航。 |
| [strategy-backtest.gif](strategy-backtest.gif) | 12.6s / 6 frames | Load graph preset, inspect/drag a node, configure and complete a backtest, inspect output and frozen parameters. 预置、节点属性/拖动、回测设置、结果和冻结参数。 |
| [ai-knowledge.gif](ai-knowledge.gif) | 12.8s / 6 frames | Upload an attachment, send a mock conversation with Enter, ask a RAG question, inspect the reference and open the Skill actions. 上传、Enter模拟对话、RAG问题/引用和Skill入口。 |

The service uses an isolated database and explicitly **mock** market/chat data. Portfolio figures come from existing test fixtures. The RAG source is a clearly identified demonstration note created in that database. No paid model calls, real native CLI sessions, broker orders or Skill-report generation were performed for these recordings. Images show workflow and presentation, not investment performance, real-world alpha effectiveness or image-understanding capability.

服务使用隔离数据库及明确标记的模拟行情/模拟回答，账户数值来自已有测试资料；知识引用来自演示笔记。录制没有调用付费模型、真实CLI或券商，没有生成Skill报告。GIF仅说明流程与展示，不能证明投资收益、Alpha效果或图片理解能力。不同后端的可用性以实际安装、认证和运行资格为准。

Frame counts, dimensions, loop metadata, complete decoding and SHA256 are checked. See [manifest.json](manifest.json) for file sizes and digests. The standalone raw screenshots, capture script and isolated runtime are temporary material retained under the project migration records until cleanup is approved.

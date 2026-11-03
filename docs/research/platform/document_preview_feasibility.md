# 网页内文件预览与外部软件集成调研

2026-10-26，Codex。状态：官方资料与当前源码复核完成；仅调研，未新增查看器、安装Office/容器或修改业务源码。以下难度为结合当前项目的工程判断，不是实测工期或版式保证。

2026-10-27实施进展：用户确认收敛为Office只读、Markdown可修改，其余支持格式预览，已按[22号设计](../../../doc/22_file_preview_markdown_design.md)接入。本文保留实施前调研事实；实际入口与配图见[文件阅读指南](../../usage/file_reader.md)，在线Office编辑和远程桌面仍未实施。

## 可行性结论

继续使用Gradio，可以在页面右侧统一展示HTML、Markdown、PDF与Word文件。只读预览的实现成本明显低于完整Office编辑器；直接把电脑上已经运行的Chrome或Word窗口放进普通网页，没有跨Windows/Linux的通用直接嵌入方式。

“后台调用软件处理文件”与“把软件的交互窗口搬进网页”是两条路线。前者可以让LibreOffice在后台转换Word，再把PDF返回网页；后者需要网页版Office服务，或远程桌面/应用画面传输。用桌面Office协议打开文件只会启动本机程序，不能由此得到网页内部的Word窗口，参见[Microsoft Office URI说明](https://learn.microsoft.com/en-us/office/client-developer/office-uri-schemes)。

## 当前系统已经具备什么

| 位置 | 当前事实 | 对后续方案的影响 |
| --- | --- | --- |
| `src/frontend/service/insights.py:_view()` | 已在有sandbox限制的iframe中展示实际HTML报告 | HTML预览已有基础，可以复用展示与状态模式 |
| `src/help_docs/ui.py:help_docs_iframe_html()` | 帮助站点已在网页内部加载 | 页面中承载独立阅读区不需要替换Gradio |
| Gradio6.16本地组件源码 | Markdown支持HTML清理；HTML支持挂载时脚本和资源加载 | 可以封装小型预览组件、按需加载本地JS，保持当前模块化结构 |
| `src/core/kb_importer.py:import_uploaded_document()` | 将解析文本保存成新的Markdown，未持久保存上传的原始DOCX/PDF字节 | 仅凭现有知识库正文无法还原原文件版式；需要新增原文件存储和元数据 |
| `src/core/kb_importer.py:_parse_docx()` | 提取段落及表格文字，不保留完整分页、图片和版式 | RAG文本提取与视觉预览需要各自保留产物；不能把文本提取成功当作Word预览成功 |

本次检查未改第三方包。Gradio官方组件实现可参考[Markdown](https://github.com/gradio-app/gradio/blob/main/gradio/components/markdown.py)及[HTML](https://github.com/gradio-app/gradio/blob/main/gradio/components/html.py)，实施时仍以本项目锁定的6.16 API为准。

## 按文件类型选择查看方式

| 文件或目标 | 推荐方式 | 难度 | 需要接受的边界 |
| --- | --- | --- | --- |
| 平台生成的HTML报告 | 复用iframe，保留交互图表所需脚本 | 低 | 外部资源、相对路径与脚本来源需要明确 |
| 上传的HTML | 隔离阅读页，静态内容默认不执行任意脚本 | 低至中 | 与可信平台报告使用不同策略，不能直接注入主页面 |
| Markdown | Gradio Markdown；图片由受控文件接口提供 | 低 | 本地相对图片路径、标题锚点及HTML片段需要处理 |
| PDF | 自托管PDF.js，统一翻页、缩放、搜索、下载 | 低至中 | 扫描PDF无文本层时，搜索与RAG仍需额外OCR；仅显示不需要OCR |
| 简单DOCX快速阅读 | 浏览器本地加载docx-preview | 中 | 支持范围受HTML排版能力约束；复杂分页、域、形状与修订需样本验证 |
| DOC/DOCX较完整的只读版式 | LibreOffice或Gotenberg转换PDF，再用PDF.js | 中 | 首次转换有等待，字体、复杂表格等可能与Microsoft Word不一致 |
| Word/Excel/PPT在线编辑 | ONLYOFFICE Docs或Collabora Online | 高于预览 | 新增文档服务、权限、保存回调、版本与冲突处理，仍需格式兼容验收 |
| 实际桌面Word或浏览器界面 | Guacamole加RDP/VNC，或受控远程浏览器会话 | 高 | 增加独立图形会话、连接生命周期与资源开销，操作/复制体验不同于本地网页 |

PDF.js是Mozilla的浏览器PDF渲染平台，官方标明Apache2.0许可，见[官方入口](https://mozilla.github.io/pdf.js/)。原生浏览器PDF查看也可作最简入口，但统一控件和跨浏览器体验更适合单独集成PDF.js；这是本项目选型判断。

docx-preview将DOCX转换为HTML，不要求安装Microsoft Office；[官方README](https://github.com/VolodymyrBaydalka/docxjs)明确其受HTML能力限制，未实现通用实时分页，域/目录也有边界，许可见[Apache2.0原文](https://github.com/VolodymyrBaydalka/docxjs/blob/master/LICENSE)。旧式DOC与DOCX不是同一种格式，不能按同一浏览器解析路径处理。

## 后台转换：优先考虑的Word阅读方案

LibreOffice官方提供Windows/Linux命令入口、无界面模式及文件转换能力，见[启动参数说明](https://help.libreoffice.org/latest/en-US/text/shared/guide/start_parameters.html)。可由项目内任务工作进程调用，独立配置用户目录、限时和并发；不能每次切换页签都重新启动转换。

如果希望转换环境独立于Python和主Web环境，可以采用[Gotenberg](https://gotenberg.dev/docs/getting-started/introduction)：它提供基于Docker的文档转换API，[官方路由](https://gotenberg.dev/docs/getting-started/routes)覆盖HTML/Markdown/网页及Office文档转PDF。其Office转换使用LibreOffice。Windows开发机需要可运行Linux容器的环境；不愿引入Docker时，可采用独立LibreOffice进程。

推荐由文件内容哈希、转换器版本及字体配置决定缓存版本。首次打开才转换，状态显示等待、处理中、完成或失败；重复打开命中缓存。PDF只读产物与原文件分别保存，转换失败保留原文件下载和具体原因。

“转换后较完整展示”不等于与桌面Word逐像素一致。需以实际中文字体、封面、页眉页脚、分页、公式、浮动图片、合并表格和研究报告样本对照。Gotenberg主项目使用MIT许可，但其镜像内LibreOffice等组件的许可、字体及更新策略应分别核对，不能把主项目许可当作所有组件的许可。

## 在线Office编辑器与微软服务

ONLYOFFICE Docs提供可嵌入的文档、表格、演示和PDF查看/编辑，支持自托管。根据[官方架构](https://api.onlyoffice.com/docs/docs-api/get-started/how-it-works)，项目仍需提供文档管理与存储，文档服务按URL取文件；编辑时再接入保存、鉴权和版本机制。嵌入一个界面只是整个集成的一部分。

其[官方仓库](https://github.com/ONLYOFFICE/DocumentServer)列出社区版AGPL3与商业版本的不同授权。结合项目此前对复制GPL代码的要求，不把社区版视作可无条件并入项目的依赖；若选择此路线，应针对最终部署和分发方式单独确认许可，本文不对项目整体许可作法律结论。

Collabora Online也可作为网页版Office候选。官方[FAQ](https://www.collaboraonline.com/faqs/)说明免费CODE是开发测试用滚动版本，不推荐用于要求稳定支持的生产环境。需评估受支持版本与相应集成，不能只因有免费镜像就视为生产方案完成。

微软路线分为不同场景：

- 文件原本就在OneDrive时，Word for the web提供[嵌入文档](https://support.microsoft.com/en-us/word/embed-a-word-document-in-your-blog)功能。已有Microsoft365文档体系时可以评估，不需要把所有场景都重新做成Office编辑器。
- SharePoint/OneDrive for Business可通过[Graph preview API](https://learn.microsoft.com/en-us/graph/api/driveitem-preview?view=graph-rest-1.0)取得短期嵌入链接；其存储范围、调用身份和访问权限不能等同于本地任意文件。
- 为自有云存储完整集成Microsoft365 for the web，官方[CSPP说明](https://learn.microsoft.com/en-us/microsoft-365/cloud-storage-partner-program/online/overview)有适用对象和WOPI要求，并非普通Microsoft365客户购买订阅后即可任意接入。

以上云方案需接受对应存储、访问和服务安排；本轮没有上传项目文件到外部预览服务。单独在服务器启动Word做无人值守COM转换不作为默认方案，微软对该模式的稳定性与支持边界有[明确说明](https://learn.microsoft.com/en-us/office/client-developer/integration/considerations-unattended-automation-office-microsoft-365-for-unattended-rpa)。

## 网页中查看网站和操作真实浏览器

平台自己的HTML页面或允许嵌入的网站，可以通过iframe显示；iframe使用当前浏览器的渲染能力，不会自动启动另一个桌面Chrome。外部网站可能拒绝iframe，相关约束见[MDN frame-ancestors](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/frame-ancestors)。跨站iframe读取受同源规则约束；修改CORS不能解除对方的frame-ancestors限制。

如果需求是让Agent登录、点击网页，并在工作台展示可操作的真实会话，则属于“远程浏览器”子系统：浏览器工作进程实际运行，网页承载其画面/输入通道，会话与账号隔离。只显示截图可以更轻，但不是持续交互浏览器，也不能宣称已同步鼠标键盘状态。

若确实要展示实际桌面Office，[Apache Guacamole](https://guacamole.apache.org/)支持HTML5客户端和RDP/VNC/SSH；配置好的Windows RDP服务器还能通过[RemoteApp](https://guacamole.apache.org/doc/gug/configuring-guacamole.html#remoteapp)只显示已发布应用。它传输的是远端应用会话，不是把访问者电脑已有Word窗口直接抓进网页；应用本身的运行许可和会话管理仍需单独处理。

## 本项目建议范围与页面形式

推荐先实现只读统一预览，继续沿用Gradio；完整Office编辑与交互远程浏览器作为两项独立后续能力。

页面上点击会话附件、项目文件或知识库原文件时，右侧打开阅读面板。顶部显示文件名、来源、类型和版本，提供适宽、全屏、下载、关闭；左侧会话和主导航继续保留。Markdown可切换正文/源码，Word可显示原文件信息及PDF阅读产物；AI引用与RAG文本仍使用现有独立提取链路。

建议实施次序：

1. 原文件保存和受控文件ID：保留原始文件、MIME、哈希、大小、上传来源与对应RAG记录；已有仅文本历史记录明确无原件，不伪造恢复。
2. 统一HTML/Markdown/PDF预览：先复用现有HTML报告，按需加载本地PDF.js，处理Markdown相对图片。
3. Word转换任务和缓存：优先PDF阅读路径，根据部署选择LibreOffice独立进程或Gotenberg；docx-preview作为简单文档快速模式候选。
4. 后续确需编辑时再接Office服务；确需网页自动操作时再接远程浏览器，会话与文件预览分开管理。

预览器可以是Gradio中的小型HTML/自定义组件，不需要重写React整站。前端资源本地固定版本，打开文件才加载；后台转换走任务队列。不要把转换器或Office服务启动加入普通导航、AI每次对话或页面初始构建，以免再次拖慢当前工作台。

## 实施前应覆盖的验收

HTML/Markdown检查中文、相对图片、交互图表、不可执行内容与明确错误状态；PDF检查分页/缩放/搜索和扫描页；Word对照上述实际中文排版样本，分别记录“内容正确”和“版式接近程度”。转换任务检查超时、损坏/加密文件、重复任务、缓存版本、并发、失败后原件可下载，以及退出后进程/端口释放。

文件访问按记录身份和权限提供，避免任意本机路径访问；上传HTML与可信图表报告分开隔离，转换进程限制资源和外部资源访问。原始内容、预览产物、RAG文本各自留存版本；页面提供拒绝/失败原因，不把下载成功或提取文本成功当作视觉预览通过。

本轮未实装上述查看器或转换服务，未测试其对本项目样本的保真度、时延、并发或安全性。将来实施前需固定实际版本并补Windows/Linux和既有功能回归；当前只读源码与官方文档调研不能替代产品验收。

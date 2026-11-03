# 模型接口与RPM控制设计

2026-11-03，Codex。状态：已按用户确认完成实施与验收，记录见本地docs/audit/model_interfaces_rpm_2026-11-03。前序已审查内容已提交为40ebd0c，未push。本轮模型接口改动留在工作区。本设计不包含实现代码。

## 目标与参考

在本平台共用模型调用链增加OpenAI SDK与LiteLLM SDK接口，并统一控制请求频率。参考imorph-voice-agent的模型工厂、请求参数适配、模型客户端和滑动窗口限流设计，结合本仓库以同步服务、Gradio回调和后台任务为主的执行方式独立适配。

已核对参考模块：src/conv_agent/model下的llm_client.py、rate_limiter.py、request_adapter.py、factory.py，以及模型重试与LiteLLM单元测试。该参考以异步客户端、每客户端限流器为基础；本仓库多处按调用新建LLMClient，需要共享配额状态，不能随对象创建重新分配RPM。

OpenAI官方普通Chat Completions及LiteLLM completion都支持统一消息输入及文本响应；SDK默认重试会影响实际请求次数，因此由平台明确关闭并集中处理。实施后已在项目环境验证OpenAI2.43.0和LiteLLM1.100.5，依赖版本与锁文件同步。

## 接口及兼容范围

保留LLMClient.complete对业务层的输入和文本、模型、用量、耗时返回契约。在模型配置增加api_backend，区分现有HTTP兼容调用、OpenAI SDK和LiteLLM SDK；历史配置缺省继续使用原HTTP路径，模型提供商标识与CLI后端选择继续各自表达。

OpenAI SDK使用普通Chat Completions生成；LiteLLM使用普通completion生成。统一适配Base URL、模型名、环境密钥引用、温度、输出预算、超时、历史、已有图片输入及显式思考参数；响应归一化后交回现有RAG、ReAct和研究服务。结构化正文继续用json_repair解析。

扩展参数通过声明的请求适配传递，禁止覆盖模型、消息、密钥、流式开关等核心字段。未配置的思考参数不主动发送，参数不支持时明确报错，不静默切模型或丢弃语义参数。已有CLI执行协议不因新增API传输而改变。

新SDK客户端继续接入当前受控HTTP目的地址校验、TLS及凭据脱敏策略，关闭环境代理自动继承和SDK自动重试；验证重定向及DNS边界，避免切换库后放宽原有安全检查。LiteLLM更广泛的供应商原生协议应按实际依赖和受控传输能力逐项验证，不仅凭安装成功承诺全部云厂商可用。

## 配置入口

系统管理的模型配置页及模型REST API新增调用接口和RPM；高级设置提供最大并发、限额时等待或快速失败及共享配额组。配置字段同时进入读取、编辑、保存和兼容迁移，平台CLI模型命令同步接受这些字段。

RPM为滚动60秒内最大实际请求数，0表示不限流。历史配置默认RPM与并发上限均为0，避免改变旧运行速度。默认等待模式遵守本次调用整体截止时间；明确关闭等待时返回可识别的本地限流错误。

缺省按模型配置共享配额；多个模型配置使用同一供应商配额时可指定同一配额组。配额组中的约束需校验一致，避免不同入口各自解释。密钥只以环境变量引用配置，限流状态和日志不保存原始密钥。

## 限流与重试

采用滚动窗口并可配置并发上限，单次实际HTTP尝试前获取许可；API、Gradio、知识库多轮检索、模型连通测试及研究调用共用入口和状态。多LLMClient实例共享控制；同项目数据库下的后台进程通过轻量SQLite状态协调RPM，不引入常驻Redis服务。只有启用限制时才访问限流状态。

等待时不持有数据库写锁或占用并发许可；排队、许可释放和进程异常清理有明确行为。取消与整体截止时间覆盖限流等待、重试退避和实际请求。异常释放在途许可，已发出的失败请求仍占用对应RPM次数。

平台统一分类429、连接/超时及可恢复服务端错误，遵守Retry-After并按配置退避；鉴权、参数和权限错误直接失败。每次重试重新受RPM约束，SDK内部重试保持关闭，避免重复放大请求量。日志及返回诊断区分调用总耗时、限流等待、请求耗时和重试次数。

## 实施范围

主要修改agent/llm_client及新增小型接口适配、限流模块；同步model_catalog、模型表兼容迁移、模型API/CLI配置和前端模型表单。默认参数放入egs下YAML，依赖按实测结果同步requirements、pyproject和uv锁；设计、使用、原理、README近期能力及周日志同步更新。

## 验收

- 用本地兼容HTTP服务截获OpenAI与LiteLLM实际SDK请求，验证参数位置、普通文本输出、用量、超时、错误及关闭自动重试。
- 验证历史配置默认行为、模型配置API/CLI与Gradio保存读取、知识库引用、研究调用与连通测试。
- 用可控时钟和并发请求验证60秒边界、重复LLMClient、共享配额组、线程/进程、重试计数、快速失败、超时、取消和异常释放；不依赖长时间sleep模拟限流。
- 保留网络安全与密钥脱敏回归，覆盖SDK的重定向、DNS和环境代理边界；检查显式参数不能注入凭据或覆盖受保护字段。
- 执行适用pytest、Ruff/format、mypy、依赖及密钥审计，记录不可消除告警和实机边界，停止本轮服务。真实供应商调用使用明确配置且有授权的模型；不以模拟模型响应冒充实际供应商验收。

## 官方接口资料

- OpenAI Python SDK：https://developers.openai.com/api/reference/python
- OpenAI普通Chat Completions：https://developers.openai.com/api/reference/python/resources/chat/subresources/completions/methods/create
- LiteLLM输入参数：https://docs.litellm.ai/docs/completion/input

已核对SDK默认重试、可配置HTTP客户端及LiteLLM的api_base、timeout、num_retries等行为。具体适配以本项目固定安装版本及HTTP集成结果为准。

实施边界补充：本轮LiteLLM1.100.5与HTTPX0.28.1通过llm可选扩展提供，和旧TDX扩展显式互斥；requirements默认安装包含模型SDK。同步网络取消在连接/读取超时或响应后检查，不宣称即时强停上游请求。

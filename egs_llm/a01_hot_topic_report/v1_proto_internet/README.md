### 智能金融报告生成全攻略：基于大模型与Web搜索的高效实现

在本文中，我们将学习如何使用 **LangChain** 框架结合 **大语言模型** 和 **网络检索工具**，自动生成金融市场行情分析报告。这是一个完整的教程，带你从了解背景到实现功能，逐步构建一个完整的分析报告生成系统。

---

### 主题介绍

在金融市场中，分析市场行情并撰写分析报告是一个日常但耗时的任务。随着大语言模型（LLM）的发展，我们可以利用其强大的自然语言处理能力，自动化这一流程。本教程的目标是构建一个系统，该系统基于用户提供的主题，从网络获取相关信息，分析后生成清晰的市场分析报告。

主要功能包括：
1. **基于关键词检索网络信息**。
2. **使用大语言模型分析信息并生成报告**。
3. **自动保存生成的报告为 Markdown 格式**。

---

### 实现逻辑

系统的实现逻辑可以概括为以下几个步骤：
1. **创建必要的目录**：确保输出文件的存储路径存在。
2. **网络信息检索**：使用 TavilySearch 工具，检索与主题相关的信息。
3. **大语言模型调用**：通过 LangChain 框架调用指定的大模型，生成报告内容。
4. **报告保存**：将生成的分析报告保存为 Markdown 格式文件。
5. **完整流程封装**：支持多个主题的批量处理，并显示处理进度。

---

### 依赖包安装

在开始之前，请确保安装以下必要的依赖包：

```bash
pip install loguru tqdm langchain-openai langchain langchain-community
```

此外，请确保：
- Python 环境为 3.8 或以上版本。
- TavilySearch API 密钥已申请并存储在文件中。
- 本地或远程大语言模型服务已配置并可用。

- Travily使用：https://python.langchain.com/v0.1/docs/integrations/tools/tavily_search/
- Travily官网：https://app.tavily.com/home

![](.README_images/travily收费情况.png)

---

### 功能拆解与代码解析

接下来，我们将代码拆分为模块化部分，逐步讲解每个功能的实现。

#### 1. **创建必要的目录**

```python
def make_dirs(*dirs):
    for i in dirs:
        if not os.path.exists(i):
            os.makedirs(i)
```

**作用**：在执行任务前，检查输出路径是否存在，若不存在则创建。

**示例调用**：
```python
output_path = '/data/output'
make_dirs(output_path)
```

---

#### 2. **清理目录内容**

```python
def clean_dirs(path: str):
    if os.path.exists(path):
        for root, dirs, files in os.walk(path, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(path)
```

**作用**：清空指定目录的内容（包括文件和子目录）。

---

#### 3. **参数类定义**

通过 `dataclass`，方便定义与传递系统所需的参数。

```python
@dataclass
class Args:
    llm_config: dict
    topic_lst: list
    travily_api_key_path: str
    search_top_k: int
    output_path: str
```

---

#### 4. **初始化大语言模型和网络检索工具**

```python
class Reporter:
    def __init__(self, args: Args):
        self.args = args

        # 初始化 TavilySearch 工具
        with open(args.travily_api_key_path, 'r') as file:
            api_key = file.read().replace('\n', '')
        os.environ['TAVILY_API_KEY'] = api_key
        self.web_search_tool = TavilySearchResults(k=args.search_top_k)

        # 初始化大语言模型
        llm_config = args.llm_config
        llm = ChatOpenAI(
            model=llm_config['llm_mdl_name'],
            openai_api_key=llm_config['llm_api_key'],
            openai_api_base=llm_config['llm_server_url'],
            max_tokens=llm_config['llm_max_tokens'],
            temperature=llm_config['llm_temperature']
        )
        prompts_report = PromptTemplate(
            template=PROMPT,
            input_variables=["doc", "topic"],
        )
        self.writer_llm = prompts_report | llm | StrOutputParser()
```

---

#### 5. **报告生成核心逻辑**

```python
def generate_report(self):
    tot_num = len(self.args.topic_lst)
    for topic in tqdm(self.args.topic_lst, total=tot_num):
        docs = self.web_search_tool.invoke({"query": topic})
        web_results = "\n---\n".join([d["content"] for d in docs])

        ret = self.writer_llm.invoke({'doc': web_results, 'topic': topic})

        # 保存报告
        out_file_path = os.path.join(self.args.output_path, f'{topic}_report.md')
        with open(out_file_path, 'w', encoding='utf-8') as f:
            f.write(ret)
    logger.info(f"Report generation finished! Output path: {self.args.output_path}")
```

**说明**：
- 使用 TavilySearch 检索网络信息。
- 调用大语言模型生成基于主题的分析报告。
- 将报告保存为 Markdown 格式。

---

#### 6. **主函数入口**

```python
def main():
    llm_config = {
        "llm_server_url": "http://localhost:8080/v1",  
        "llm_mdl_name": "Qwen2.5-7B-Instruct",
        "llm_api_key": "EMPTY",
        "llm_max_tokens": 6500,  
        "llm_max_input_tokens": 24500,
        "llm_temperature": 0,
    }
    travily_api_key_file = '/home/api_key/TavilySearchApi.txt'
    search_top_k = 10
    output_path = '/data/output'
    make_dirs(output_path)

    topic_lst = ['低空经济', '人工智能']
    args = Args(llm_config=llm_config,
                topic_lst=topic_lst,
                travily_api_key_path=travily_api_key_file,
                search_top_k=search_top_k,
                output_path=output_path)
    reporter = Reporter(args)
    reporter.generate_report()
```

---

### 效果展示

1. **生成报告目录**：
   - 报告将保存在指定的 `output_path` 中。
   - 每个主题的报告以 Markdown 文件格式保存，例如：`低空经济_report.md`。

2. **生成报告示例**：

文件内容示例（部分展示）：
```markdown
# 人工智能市场分析报告

## 市场行情概述
人工智能技术应用持续扩展，市场保持高速增长。

## 热点消息
1. 大型科技公司纷纷加码 AI 研发。
2. 自动驾驶领域取得显著突破。

## 行情走势分析
短期内市场呈现增长趋势，投资者信心较强。

## 总结
人工智能市场未来可期，但需警惕技术与伦理的平衡问题。
```

---

### 总结

通过本教程，我们学习了如何构建一个基于 LangChain 和大语言模型的金融市场行情分析报告生成系统。其主要功能包括网络信息检索、内容分析及自动报告生成。随着更强大的模型和工具的加入，系统可以进一步扩展到更多领域和应用场景。
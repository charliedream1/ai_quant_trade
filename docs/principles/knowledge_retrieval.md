# 知识库文件检索原理

Knowledge retrieval now has two independent backends: model-guided recursive
zvec-grep search and local SAG2 BM25 with evidence-driven expansion. Original
SAG is retired. The paragraphs below describe the original zvec-grep workflow;
SAG2 and its replaceable selectors are described in the final section.


知识资料以原件、Markdown正文和分块文件保存。库名映射到独立目录，目录元数据和会话沿用SQLite；问答检索通过zvec-grep的lexical模块执行文字匹配，不使用向量存储或嵌入模型。

模型先生成关键词，系统在选定库和当前会话附件中检索，再让模型判断证据是否足够；缺少证据时生成新关键词补搜。轮数是上限，默认3轮，达到上限或没有新词时停止。普通生成结果用json_repair解析，模型输出不会被当作命令执行。

检索按连续文字匹配，中英文同义词须分成两个关键词，不能拼为“回撤/drawdown”。追问会使用同库历史识别主题，再重新检索原文；历史回答不能单独满足本轮证据要求。

标题优先切分保留文档结构，5000字符是单块默认上限。检索只访问当前清单列出的分块，因此历史遗留文件不影响当前答案。引用记录文档、分块和命中行，点击后在左侧阅读器核对原件；Markdown可定位引用文字，PDF可按文字查找。

会话附件仅对所属库和会话可见。下载有大小和时间预算，扫描PDF不执行OCR。关键词匹配依赖原文用词，模型规划或生成失败会明确展示状态；有引用也仍需检查其是否支持回答。

操作说明见[知识库使用指南](../usage/knowledge.md)，存储分工见[存储说明](storage.md)。

## SAG2 evidence-driven lexical expansion

SAG2 indexes the authorized original passages with SQLite FTS5/BM25. It selects
initial candidates using the question, scores useful evidence, extracts new terms
from that evidence and recalls additional passages. Each round retains selected
seeds and scores the combined pool against the original question and context.
No offline semantic annotations, vector database or indexing-time model calls
are required. Fingerprinted indexes are derived caches, not authoritative sources.

JEV uses contextual noul evidence decisions. Embedding cosine similarity and
standard reranking can replace that scorer while preserving BM25 recall and term
expansion. Their scores are not interchangeable measures of quality. Pure BM25
is also available; it may retain weakly related passages reached through common
terms. The trace identifies the actual scorer and provider fallback reasons.

Scope is applied before corpus indexing: library, attachment session, category,
source type and single-document selection constrain every round. Providers return
scores only, and cannot create evidence text or cite other source IDs. Local
original chunks remain the citation boundary. Query-time scoring can send those
bounded authorized passages to the configured provider; pure BM25 sends none.

This portable adaptation uses Latin tokens and Chinese bigrams, not upstream's
compiled scoring extension, and does not claim upstream benchmark equivalence.
See the [official reference](https://github.com/Zleap-AI/SAG-Benchmark/tree/main/sag2)
and the [SAG2 configuration and migration guide](../usage/sag_knowledge_qa.md).

# 1. 说明

本文件最后更新时间：2025-02-15

注意：
- 环境文件更新可能存在延迟

目前我导出了环境下的全量python依赖环境供参考
- pip开头是用pip导出的
- conda开头是用conda导出的

版本：
- 带finrl的是强化学习策略对应的环境
- 不带的是其它的环境配置

目前测试环境：
- windows 10
- python 3.8
- GPU: GTX 1050 Ti (4096 M) + CUDA10.2 + cudnn8.6
- RAM: 32G
- CPU: i7-8750H

# 2. 环境导入方法

使用pip

```bash
pip install -r requirements.txt
#临时换源
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
```

使用conda

```bash
 conda install --yes --file requirements.txt
```
# 1. 简介
微软开发的AI量化投资平台，当前唯一且最完善的开源平台。不仅提供了高速存储(快于MySQL, MongoDb等)，还提供了
详细的全流程一站式服务，从数据下架、模型训练到回测。

- 论文: [Qlib : An AI-oriented Quantitative Investment Platform](https://arxiv.org/pdf/2009.11189.pdf)   
- Github:  https://github.com/microsoft/qlib
- 文档: https://qlib.readthedocs.io/en/latest/index.html

# 2. 安装
## 2.1 系统要求
- 支持windows和linux平台
- 要求python3.7或3.8 (3.9部分功能不支持)
- 如果windows，安装Microsoft C++ Build Tools (大约需要2.5G空间)    
  https://visualstudio.microsoft.com/visual-cpp-build-tools/      


- 快速安装
``` sh
pip install pyqlib
```

- 源码安装
``` sh
git clone https://github.com/microsoft/qlib.git && cd qlib
pip install .
```
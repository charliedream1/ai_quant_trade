# 1. 简介

&emsp;&emsp;笔记记录于20220902.

![qlib模块及运行流程.png](img/qlib模块及逻辑关系.png)

<center>图1 qlib模块及运行流程(出自Qlib论文)[1] </center>

![qlib运行流程.png](img/qlib运行流程.png)

<center>图2 qlib运行流程(出自最新Qlib Github)[2]</center>

Infrastructure Layer: 基础结构，包括数据服务器、模型及训练管理等

* Data Server：存储管理数据，速度很快，超过各类通用数据库
* Trainer: 控制模型训练流程

Workflow Layer:整个工作流程管理层

* Information Extractor: 提取数据用于模型训练
* Forecast Model：预测模型提供各种预测信号（包括alpha、风险等）
* Decision Generator：决策

Interface：提供用户接口，报告和执行结果

# 2. 流程控制及辅助功能

# 2.1 流程控制
```
  qlib/workflow/__init__.py
```

# 2.2 辅助功能

1. 类初始化
&emsp;&emsp;根据yaml中配置的类路径，对如数据处理类(Data Handler)、模型类、回测类、分析类
实例化对象。

```
  qlib/utils/__init__.py
```

&emsp;&emsp;函数init_instance_by_config：
* 如果是可接受类型，直接返回config
* 如果是str类型，加载pkl文件
* 通过函数get_callable_kwargs实例化对象，抽取字典中的路径及类名进行实例化

2. 数据序列化
```
   qlib/utils/serial.py
```
&emsp;&emsp;如下4中的数据加载模块，均继承此类，基于pickle或dill库加载和保存数据。

3. 全局常量  

  qlib/constant
* 可以选择数据地域，有中国/美国/台湾
* EPS = 1e-12，避免除以0

4. 嵌套字典变成无嵌套
```
   qlib/utils/__init__.py
   
   Flatten a nested dict.

    >>> flatten_dict({'a': 1, 'c': {'a': 2, 'b': {'x': 5, 'y' : 10}}, 'd': [1, 2, 3]})
    >>> {'a': 1, 'c.a': 2, 'c.b.x': 5, 'd': [1, 2, 3], 'c.b.y': 10}

    >>> flatten_dict({'a': 1, 'c': {'a': 2, 'b': {'x': 5, 'y' : 10}}, 'd': [1, 2, 3]}, sep=FLATTEN_TUPLE)
    >>> {'a': 1, ('c','a'): 2, ('c','b','x'): 5, 'd': [1, 2, 3], ('c','b','y'): 10}
```

# 3. 数据加载模块
&emsp;&emsp;qlib/data为基类，qlib.contrib.data是第三方贡献，或者改写的类。

# 3.1 数据下载

* 在qlib/constant可以选择数据地域，有中国/美国/台湾
* 通过qlib库获取数据：from qlib.tests.data import GetData
* 数据从微软官网获取：REMOTE_URL = "http://fintech.msra.cn/stock_data/downloads"
* 下载后默认存放在"~/.qlib/qlib_data/cn_data"
* 压缩包命名格式：20220701081835_qlib_data_simple_cn_1d_latest
* 之后自动解压

# 3.2. 数据加载  

&emsp;&emsp;数据初始化代码位置如下，调用其中的DatasetH类。

```
   qlib/data/dataset/__init__.py
```

&emsp;&emsp;继承关系为DatasetH -> Dataset -> Serializable(qlib/utils/serial.py）
依次继承。

* Serializable(qlib/utils/serial.py）：基于pickle或dill库加载和保存数据
* Dataset: 未重写父类，只定义了几个函数
* DatasetH
  * 将预处理函数放在参数handler中

# 3.3. 因子计算
```
  qlib.contrib.data.handler.py
```
* 通过类Alpha158，通过基本的每日量价数据，计算158个技术指标
* 类继承关系：Alpha -> DataHandlerLP  -> DataHandler -> Serializable

# 6. 模型训练
```
  qlib.contrib.model.gbdt.py
```
&emsp;&emsp;使用MSE损失函数，作为回归问题进行预测。

&emsp;&emsp;MSE衡量的是预测值和目标值的欧式距离。
而交叉熵是一个信息论的概念，交叉熵能够衡量同一个随机变量中的两个不同概率分布的差异程度，在机器学习中就表示为真实概率分布与预测概率分布之间的差异。交叉熵的值越小，模型预测效果就越好。
所以交叉熵本质上是概率问题，表征真实概率分布与预测概率分布差异，和几何上的欧氏距离无关，在回归中才有欧氏距离的说法，
而在分类问题中label的值大小在欧氏空间中是没有意义的。所以分类问题不能用mse作为损失函数。[3]

&emsp;&emsp;如果使用MSE作为分类任务，MSE（均方误差）对于每一个输出的结果都非常看重(让正确分类变大的同时，
也让错误分类变得平均)，而交叉熵只对正确分类的结果看重。



# 7. 策略及回测

# 8. 回测评估及报告

# 参考    
[1] 2022.9.20, Qlib : An AI-oriented Quantitative
Investment Platform
[2] Qlib Github: https://github.com/microsoft/qlib
[3] MSN博客，分类问题可以使用MSE(均方误差)作为损失函数吗, 
版权声明：本文为CSDN博主「我是女孩」的原创文章，遵循CC 4.0 BY-SA版权协议，转载请附上原文出处链接及本声明。
原文链接：https://blog.csdn.net/u013385018/article/details/115355701

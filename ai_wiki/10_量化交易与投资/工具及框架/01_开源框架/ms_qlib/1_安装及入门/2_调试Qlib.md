现状：
* qlib需要编译安装后才能使用
* 再qlib的原始代码目录下，运行qlib/examples/workflow_by_code.py，会
  报qlib找不到的错误

问题：那么如何进入qlib底层调试并了解运行机制呢？

解决方案：
* 新起一个项目，运行workflow_by_code.py
* 在pyCharm中，从引用的头文件进入qlib
* 在pyCharm顶部的路径中，切换到qlib的其它待调试目录中（如下图所示），
  并加入断点

![1_切换目录.png](img/1_切换目录.png)
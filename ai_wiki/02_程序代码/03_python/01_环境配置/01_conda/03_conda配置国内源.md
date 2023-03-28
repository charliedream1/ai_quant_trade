最后编辑时间：2023-02-25

# 1. 方法
## 1.1 Windows配置
- 来源：https://github.com/alibaba-damo-academy/FunASR/wiki/Windows%E7%8E%AF%E5%A2%83%E5%AE%89%E8%A3%85

点击anaconda prompt命令窗口：
运行命令： conda config --set show_channel_urls yes

查看配置文件路径：conda config --show-sources

打开user下文件 .condarc，把里面的内容替换为清华源：
```
channels:
- [http://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/pytorch/](http://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/pytorch/)
- [http://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/menpo/](http://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/menpo/)
- [http://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/bioconda/](http://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/bioconda/)
- [http://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/msys2/](http://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/msys2/)
- [http://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge/](http://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge/)
- [http://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/](http://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/)
- [http://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free/](http://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free/)
show_channel_urls: true
```

# 2. 其它信息
[转载自： https://zhuanlan.zhihu.com/p/434356947]  
发布于 2021-11-29 18:35

直接安装软件包速度太慢，经常被中断，所以需要配置国内镜像源。

1.为本地conda环境配置国内镜像源
# 中科大镜像源

conda config --add channels https://mirrors.ustc.edu.cn/anaconda/pkgs/main/
conda config --add channels https://mirrors.ustc.edu.cn/anaconda/pkgs/free/
conda config --add channels https://mirrors.ustc.edu.cn/anaconda/cloud/conda-forge/
conda config --add channels https://mirrors.ustc.edu.cn/anaconda/cloud/msys2/
conda config --add channels https://mirrors.ustc.edu.cn/anaconda/cloud/bioconda/
conda config --add channels https://mirrors.ustc.edu.cn/anaconda/cloud/menpo/
conda config --add channels https://mirrors.ustc.edu.cn/anaconda/cloud/
# 阿里镜像源

conda config --add channels https://mirrors.aliyun.com/pypi/simple/
# 豆瓣的python的源

conda config --add channels http://pypi.douban.com/simple/ 
# 显示检索路径，每次安装包时会将包源路径显示出来

conda config --set show_channel_urls yes
conda config --set always_yes True
# 显示所有镜像通道路径命令

conda config --show channels
2. 为服务器的conda环境配置国内镜像源
添加清华镜像源

conda config --add channels http://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free/win-64/
【注】使用http不是https，在后面加上win-64

3.常用操作
显示添加的源通道

conda config --show-sources
移除某一镜像源

conda config --remove channels 源名称或链接 
验证安装

为了确保正确安装了PyTorch，我们可以通过运行示例PyTorch代码来验证安装。在这里，我们将构造一个随机初始张量

在 anaconda prompt(miniconda3) 命令行或者shell中，输入：

python 
然后输入以下代码：

import torch 
x = torch.rand(5, 3) 
print(x)
输出应类似于以下内容：

tensor([[0.3380, 0.3845, 0.3217],
      [0.8337, 0.9050, 0.2650],
      [0.2979, 0.7141, 0.9069],
      [0.1449, 0.1132, 0.1375],
      [0.4675, 0.3947, 0.1426]])
此外，如果要检查 PyTorch 是否启用了 GPU和CUDA，请运行以下命令以返回是否启用了CUDA驱动程序：

import torch  
torch.cuda.is_available()
如果返回了 True， 恭喜您，成功安装了GPU版本。

# 3. 手动下载包

nvidia相关包：https://anaconda.org/nvidia/repo?type=conda&label=main

# 参考
[1] FunASR安装Wiki, https://github.com/alibaba-damo-academy/FunASR/wiki/Windows%E7%8E%AF%E5%A2%83%E5%AE%89%E8%A3%85
[2] https://blog.csdn.net/taoyu94/article/details/108150892
[3] https://www.bilibili.com/read/cv7476249
[4] https://www.jianshu.com/p/cd9b81f3e886

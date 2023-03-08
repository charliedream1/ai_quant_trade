# 1. 下载路径
* 官网：https://www.anaconda.com/products/distribution
* 历史版本：https://repo.anaconda.com/archive/

# 2. Windows下安装
![](.01_conda安装_images/conda安装1.png)
![](.01_conda安装_images/conda安装同意协议.png)
![](.01_conda安装_images/conda安装使用人.png)
![](.01_conda安装_images/conda安装路径选择.png)
注意：安装路径下建议不能有空格(conda会弹窗提示)，否则部分包可能存在使用问题
![](.01_conda安装_images/conda环境变量.png)
注意：第一项需打勾，不然找不到conda的路径
![](.01_conda安装_images/conda安装完最后.png)
![](.01_conda安装_images/conda安装_最后帮助文档连接.png)

# 3. Linux安装

```
wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh 
sh Miniconda3-latest-Linux-x86_64.sh 
source ~/.bashrc
conda create -n funasr python=3.7 #推荐python3.7
conda activate funasr
```
更多conda安装细节参考https://docs.conda.io/en/latest/miniconda.html

# 参考
[1] FunASR Linux安装，https://github.com/alibaba-damo-academy/FunASR/wiki/Linux%E7%8E%AF%E5%A2%83%E5%AE%89%E8%A3%85